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
from mcp.server.fastmcp import FastMCP

from mcp_server.errors import WorkflowFailure
from mcp_server.prompt_specs import PROMPTS
from mcp_server.server import ParamAIToolServer
from mcp_server.tool_specs import ALL_TOOLS

mcp = FastMCP("ParamAItric")
_server = ParamAIToolServer()


def _call_tool(method_name: str, payload: dict) -> dict:
    """Invoke a server method by name, converting WorkflowFailure to a structured error dict."""
    method = getattr(_server, method_name)
    sig = inspect.signature(method)
    try:
        if method_name in {"health", "get_workflow_catalog"}:
            return method()
        
        # If the method expects a 'payload' argument, pass the dict as is
        if "payload" in sig.parameters:
            return method(payload)
            
        # Otherwise, unpack the payload as keyword arguments
        return method(**payload)
    except WorkflowFailure as exc:
        return {
            "ok": False,
            "error": str(exc),
            "stage": exc.stage,
            "classification": exc.classification,
            "next_step": exc.next_step,
            "partial_result": exc.partial_result,
        }
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "classification": "validation_error"}


def _make_tool(tool_name: str, spec) -> None:
    """Register one MCP tool dynamically."""
    method_name = spec.method
    description = spec.description

    if tool_name in {"health", "workflow_catalog"}:
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


@mcp.prompt(name="cad_status", description=PROMPTS["cad_status"].description)
def cad_status() -> str:
    return (
        "Use the ParamAItric MCP server to check CAD readiness.\n\n"
        "Call the `health` tool and summarize:\n"
        "- whether the Fusion bridge is reachable\n"
        "- the reported mode\n"
        "- whether the status is ready\n"
        "- any workflow catalog details that matter to the next step\n\n"
        "If health fails, explain the failure briefly and tell the user to start Fusion 360 "
        "and the ParamAItric add-in."
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
        "Operating rules:\n"
        "- Start by calling `health` unless the user explicitly wants offline guidance only.\n"
        "- If the request is asking what workflows exist, call `workflow_catalog` and summarize it.\n"
        "- Prefer the single best validated workflow tool for the request.\n"
        "- Do not invent unsupported geometry operations or parameters.\n"
        "- If the request is ambiguous or outside the validated workflow surface, ask one focused follow-up question.\n"
        "- After running a workflow, summarize what was created, whether verification passed, and any export paths returned."
    )


if __name__ == "__main__":
    mcp.run()
