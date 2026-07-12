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
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from mcp_server.errors import error_from_exception
from mcp_server.schema_generation import tool_input_schema
from mcp_server.unit_normalization import (
    normalize_workflow_units as _normalize_workflow_units,
)
from mcp_server.prompt_specs import PROMPTS
from mcp_server.server import ParamAIToolServer
from mcp_server.tool_specs import ALL_TOOLS

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
    method = getattr(server, method_name)
    sig = inspect.signature(method)
    try:
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

    if tool_name in {"getting_started", "health", "workflow_catalog"}:
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


for _name, _spec in ALL_TOOLS.items():
    _make_tool(_name, _spec)
    _schema = tool_input_schema(_name, _spec.method)
    if _schema is not None:
        mcp._tool_manager._tools[_name].parameters = _schema


@mcp.prompt(name="cad_status", description=PROMPTS["cad_status"].description)
def cad_status() -> str:
    return (
        "Use the ParamAItric MCP server to check CAD readiness.\n\n"
        "Call the `health` tool and summarize:\n"
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
    return (
        "Use the ParamAItric MCP server to inspect the available validated CAD workflows.\n\n"
        "Call `workflow_catalog`, then present a concise summary of the workflow names and their "
        "intended use. If the user already described a part, identify the closest matching workflow "
        "and mention any obvious gaps or ambiguity."
    )


@mcp.prompt(name="cad_request", description=PROMPTS["cad_request"].description)
def cad_request(request: str) -> str:
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
        "- Call `recommend_workflow` with their description to find the best validated workflow. "
        "Propose the top candidate in plain language and wait for confirmation.\n\n"
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
        "- Call `health` first. Confirm the reported backend is ready, then check the workflow "
        "catalog for the needed workflow and capabilities for any required operations. Otherwise "
        "follow its backend-specific hint or recovery guidance, then retry.\n"
        "- Call the single best create_* tool. Do not invent unsupported operations or "
        "parameters. If nothing fits, say so plainly and describe the closest supported shapes.\n"
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
