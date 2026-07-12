"""MCP transport entrypoint for ParamAItric.

Thin host-facing layer: instantiates ParamAIToolServer and registers MCP tools
from tool_specs.ALL_TOOLS. All validation, workflow logic, and Fusion bridge
communication remain in server.py.

Usage (stdio transport for Claude Desktop):
    python -m mcp_server.mcp_entrypoint

Claude Desktop config (claude_desktop_config.json):
    {
        "mcpServers": {
            "paramaitric": {
                "command": "python",
                "args": ["-m", "mcp_server.mcp_entrypoint"],
                "cwd": "<path-to-repo>"
            }
        }
    }
"""
from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
import sys

from mcp.server.fastmcp import FastMCP

from mcp_server.errors import error_from_exception
from mcp_server.schema_generation import tool_input_schema
from mcp_server.unit_normalization import (
    normalize_workflow_units as _normalize_workflow_units,
)
from mcp_server.prompt_specs import PROMPTS, tool_name_for_profile
from mcp_server.server import ParamAIToolServer
from mcp_server.tool_specs import ALL_TOOLS
from mcp_server.runtime_profiles import load_runtime_profile, RuntimeProfileError
import mcp_server.runtime_info as runtime_info

# Determine if running doctor
is_doctor = len(sys.argv) > 1 and sys.argv[1] == "doctor"

profile_name = os.environ.get("PARAMAITRIC_PROFILE")
if not is_doctor:
    for i, arg in enumerate(sys.argv):
        if arg == "--profile" and i + 1 < len(sys.argv):
            profile_name = sys.argv[i + 1]
            break
    # Strip --profile <name> from sys.argv so it doesn't interfere with FastMCP's CLI runner
    new_argv = []
    skip = False
    for arg in sys.argv:
        if skip:
            skip = False
            continue
        if arg == "--profile":
            skip = True
            continue
        new_argv.append(arg)
    sys.argv = new_argv

active_profile = None
if profile_name:
    try:
        active_profile = load_runtime_profile(profile_name)
        runtime_info.ACTIVE_PROFILE_NAME = active_profile.profile
        runtime_info.ACTIVE_PROFILE_EXPORT_DIR = str(active_profile.export_directory)
        runtime_info.ACTIVE_PROFILE_CAD_ENDPOINT = active_profile.cad_endpoint
    except RuntimeProfileError as exc:
        err = {
            "ok": False,
            "classification": "validation_error",
            "stage": "startup",
            "error": str(exc),
            "recoverable": False,
            "next_step": "Check the profile name or file contents and try again.",
            "partial_result": {}
        }
        print(json.dumps(err), file=sys.stderr)
        sys.exit(1)

mcp = FastMCP("ParamAItric")
_server = ParamAIToolServer()


def _collect_export_paths(value: object, found: list[str]) -> None:
    """Recursively collect exported STL paths from a workflow result."""
    if isinstance(value, str):
        if value.lower().endswith(".stl") and value not in found:
            found.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            _collect_export_paths(item, found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _collect_export_paths(item, found)


def _open_folder_commands(directory: str) -> dict[str, str]:
    """Per-OS shell commands that would open `directory` in the file browser.

    This is data only, meant for the host AI to relay to the user (or offer
    to run on their behalf via its own shell tool). This module never spawns
    the command itself.
    """
    return {
        "windows": f'explorer "{directory}"',
        "macos": f'open "{directory}"',
        "linux": f'xdg-open "{directory}"',
    }


def _attach_export_summary(result: dict) -> dict:
    """Add a plain-language next step when a workflow exported STL files.

    Novice users often don't know what to do after a part is created; this
    gives the host model a consistent, user-facing hand-off message, plus the
    export folder(s) and a per-OS "open this folder" command the host AI can
    relay (never executed by this module).
    """
    if not isinstance(result, dict) or result.get("ok") is False:
        return result
    exports: list[str] = []
    _collect_export_paths(result, exports)
    if exports:
        listing = "; ".join(exports)
        result.setdefault(
            "user_next_step",
            (
                f"Tell the user their printable file is ready at: {listing}. "
                "Next step: open it in a slicer (e.g. Cura, PrusaSlicer, Bambu Studio, "
                "or the printer's own software) to prepare it for 3D printing. "
                "State the exact folder so they can find the file."
            ),
        )
        export_folders = sorted({str(Path(path).parent) for path in exports})
        result.setdefault("export_folders", export_folders)
        result.setdefault(
            "open_folder_commands",
            {folder: _open_folder_commands(folder) for folder in export_folders},
        )
        result.setdefault(
            "open_folder_note",
            "These are suggested commands to open the export folder in the system "
            "file browser (Windows: explorer, macOS: open, Linux: xdg-open). Relay "
            "them to the user or offer to run the one matching their OS -- do not "
            "run one without their go-ahead.",
        )
    return result


def call_tool(server: ParamAIToolServer, method_name: str, payload: dict) -> dict:
    """Invoke a server method by name, normalizing any failure into the structured error envelope.

    This is the host-boundary dispatcher shared between MCP stdio transport and evaluation runner.
    """
    try:
        if method_name == "build_workflow":
            # For build_workflow, we need to normalize the nested parameters
            workflow = payload.get("workflow", "")
            if not isinstance(workflow, str) or not workflow.strip():
                raise ValueError("workflow must be a non-empty string.")
            
            w_name = workflow.strip()
            if not w_name.startswith("create_"):
                w_name = f"create_{w_name}"
                
            from mcp_server.tool_specs import WORKFLOW_TOOLS
            if w_name not in WORKFLOW_TOOLS:
                raise ValueError(f"Unknown workflow '{workflow}' or workflow is not allowed in build.")
                
            underlying_method_name = WORKFLOW_TOOLS[w_name].method
            underlying_method = getattr(server, underlying_method_name)
            
            # Normalize the nested 'parameters'
            normalized_parameters = _normalize_workflow_units(payload.get("parameters", {}))
            
            # Now call the underlying method on server with normalized parameters
            underlying_sig = inspect.signature(underlying_method)
            if "payload" in underlying_sig.parameters:
                res = underlying_method(normalized_parameters)
            else:
                res = underlying_method(**normalized_parameters)
            return _attach_export_summary(res)

        method = getattr(server, method_name)
        sig = inspect.signature(method)
        if method_name.startswith('create_'):
            payload = _normalize_workflow_units(payload)
        if method_name in {"getting_started", "health", "get_workflow_catalog"}:
            return method()

        # If the method expects a 'payload' argument, pass the dict as is
        if "payload" in sig.parameters:
            return _attach_export_summary(method(payload))

        # Otherwise, unpack the payload as keyword arguments
        return _attach_export_summary(method(**payload))
    except Exception as exc:  # noqa: BLE001 - host boundary: always return a structured error, never a traceback
        return error_from_exception(exc)


def _call_tool(method_name: str, payload: dict) -> dict:
    return call_tool(_server, method_name, payload)


def _make_tool(tool_name: str, spec) -> None:
    """Register one MCP tool dynamically."""
    method_name = spec.method
    description = spec.description

    if tool_name in {"getting_started", "health", "workflow_catalog", "cad_health"}:
        @mcp.tool(name=tool_name, description=description)
        def _status_tool() -> dict:
            return _call_tool(method_name, {})
        # Rename to avoid closure collision
        _status_tool.__name__ = tool_name
    else:
        @mcp.tool(name=tool_name, description=description)
        def _workflow_tool(payload: dict) -> dict:
            return _call_tool(method_name, payload)
        _workflow_tool.__name__ = tool_name


from mcp_server.tool_specs import ToolSpec

GUIDED_TOOLS: dict[str, ToolSpec] = {
    "cad_health": ToolSpec(
        method="health",
        description=(
            "Check the configured CAD backend and report its identity, ParamAItric version, operating mode, "
            "capabilities, and workflow count."
        )
    ),
    "cad_recommend_workflow": ToolSpec(
        method="recommend_workflow",
        description=(
            "Map a fuzzy natural-language part description to ranked workflow candidates, each with "
            "realistic starting dimensions (example_params) and honest boundaries (not_for)."
        )
    ),
    "cad_get_requirements": ToolSpec(
        method="get_workflow_requirements",
        description="Return the precise parameter schema for a selected workflow."
    ),
    "cad_build": ToolSpec(
        method="build_workflow",
        description="Execute a specific CAD workflow by name with the given parameters."
    ),
    "cad_inspect": ToolSpec(
        method="inspect_design",
        description="Inspect design geometry using a specific inspection operation and parameters."
    ),
}

registered_tools = ALL_TOOLS
if active_profile and active_profile.tool_profile == "guided":
    registered_tools = GUIDED_TOOLS

for _name, _spec in registered_tools.items():
    _make_tool(_name, _spec)
    _schema = tool_input_schema(_name, _spec.method)
    if _schema is not None:
        mcp._tool_manager._tools[_name].parameters = _schema


# Prompt rendering is profile-aware: prompt bodies are written once against
# the full tool surface and `_t(...)` rewrites each named tool to the
# facade name that actually exists under the active tool_profile (see
# prompt_specs.tool_name_for_profile). This keeps prompt prose in one place
# instead of forking per profile.
_TOOL_PROFILE = active_profile.tool_profile if active_profile else "full"
_GUIDED = _TOOL_PROFILE == "guided"


def _t(full_profile_tool_name: str) -> str:
    """Resolve a full-profile tool identifier for the active tool_profile."""
    return tool_name_for_profile(full_profile_tool_name, _TOOL_PROFILE)


@mcp.prompt(name="cad_status", description=PROMPTS["cad_status"].description)
def cad_status() -> str:
    return (
        "Use the ParamAItric MCP server to check CAD readiness.\n\n"
        f"Call the `{_t('health')}` tool and summarize:\n"
        "- the configured CAD backend and ParamAItric version\n"
        "- whether it is reachable and ready\n"
        "- the reported operating mode\n"
        "- the capabilities relevant to the user's next step\n"
        "- the available workflow count\n"
        "- any hint or workflow details that matter to the next step\n\n"
        "If health fails, explain the failure briefly and follow the returned recovery guidance. "
        "Do not assume which CAD backend the user configured."
    )


@mcp.prompt(name="cad_list_workflows", description=PROMPTS["cad_list_workflows"].description)
def cad_list_workflows() -> str:
    if _GUIDED:
        call_instruction = (
            f"Call `{_t('workflow_catalog')}` with the user's part description, then present the "
            "ranked workflow candidates and their intended use."
        )
    else:
        call_instruction = (
            f"Call `{_t('workflow_catalog')}`, then present a concise summary of the workflow "
            "names and their intended use."
        )
    return (
        "Use the ParamAItric MCP server to inspect the available validated CAD workflows.\n\n"
        f"{call_instruction} If the user already described a part, identify the closest matching "
        "workflow and mention any obvious gaps or ambiguity."
    )


@mcp.prompt(name="cad_request", description=PROMPTS["cad_request"].description)
def cad_request(request: str) -> str:
    if _GUIDED:
        build_steps = (
            f"- Call `{_t('health')}` first. Confirm the reported backend is ready; otherwise "
            "follow its backend-specific hint or recovery guidance, then retry.\n"
            f"- Call `{_t('get_workflow_requirements')}` for the chosen workflow to get its exact "
            "parameter schema before building.\n"
            f"- Call `{_t('create_*')}` with the workflow name and parameters. Do not invent "
            "unsupported operations or parameters. If nothing fits, say so plainly and describe "
            "the closest supported shapes.\n"
            f"- If you need to verify existing geometry before or after building, use "
            f"`{_t('list_design_bodies')}` for read-only inspection only — it cannot mutate the design.\n"
        )
    else:
        build_steps = (
            f"- Call `{_t('health')}` first. Confirm the reported backend is ready, then check the "
            "workflow catalog for the needed workflow and capabilities for any required "
            "operations. Otherwise follow its backend-specific hint or recovery guidance, then "
            "retry.\n"
            f"- Call the single best {_t('create_*')} tool. Do not invent unsupported operations "
            "or parameters. If nothing fits, say so plainly and describe the closest supported "
            "shapes.\n"
        )
    return (
        "Use the ParamAItric MCP server for this CAD request:\n"
        f"{request}\n\n"
        "Assume the user has little or no experience with AI, CAD, or 3D printing. Your job is "
        "to get them from 'I need this part' to a printable STL file with as little friction as "
        "possible. Be warm and plain-spoken; never use CAD jargon without explaining it.\n\n"
        "Step 1 — Understand the part:\n"
        "- Ask what the part is for and what it attaches to or fits into. A photo description, "
        "the appliance model, or 'it's a clip that broke off my dishwasher rack' is all useful.\n"
        "- If their AI app accepts images, invite them to attach a clear photo of the removed "
        "part beside a ruler, or flat on grid paper. Include a top view and a side view when "
        "thickness matters. Never ask them to place a ruler near live electrical parts, moving "
        "machinery, or anything hot; have them remove the part first only when safe.\n"
        "- Treat dimensions inferred from a photo as rough estimates, not precision measurements. "
        "State each estimate and ask the user to confirm it with a ruler or calipers before using it.\n"
        f"- Call `{_t('recommend_workflow')}` with their description to find the best validated "
        "workflow. Propose the top candidate in plain language and wait for confirmation.\n\n"
        "Step 2 — Get measurements (do not skip):\n"
        "- Guide them to measure the original part or the space it fits: a ruler works; calipers "
        "are better if they have them. Ask for only one measurement at a time, beginning with "
        "the dimension that controls fit (such as a hole diameter or mating width), then request "
        "only the remaining dimensions required by the selected workflow.\n"
        "- Accept measurements in whatever unit they use. Tool inputs are centimeters: 10 mm = "
        "1 cm, 1 inch = 2.54 cm. Show the converted values and confirm before building.\n"
        "- For parts that must fit around or into something, suggest adding clearance: about "
        "0.02-0.04 cm (0.2-0.4 mm) on holes and sockets is a good 3D-printing default.\n\n"
        "Step 3 — Build:\n"
        f"{build_steps}"
        "- If they don't care where the file goes, pass a bare filename like 'part.stl' — it "
        "saves to Documents/ParamAItric Exports. Desktop and Downloads also work.\n\n"
        "Step 4 — Hand off:\n"
        "- Report whether verification passed, the exact folder and filename of the STL, and "
        "the next step: open the file in a slicer (Cura, PrusaSlicer, Bambu Studio, or their "
        "printer's software) to print it.\n"
        "- If a step fails, explain what happened in plain language and offer one concrete fix "
        "at a time — never a wall of troubleshooting."
    )


def main() -> None:
    """Run the ParamAItric MCP server over its default stdio transport."""
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "doctor":
        from mcp_server.doctor import run_doctor
        sys.exit(run_doctor(sys.argv[2:]))
    else:
        mcp.run()


if __name__ == "__main__":
    main()
