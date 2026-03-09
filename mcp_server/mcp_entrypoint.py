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

from mcp.server.fastmcp import FastMCP

from mcp_server.errors import WorkflowFailure
from mcp_server.server import ParamAIToolServer
from mcp_server.tool_specs import ALL_TOOLS

mcp = FastMCP("ParamAItric")
_server = ParamAIToolServer()


def _call_tool(method_name: str, payload: dict) -> dict:
    """Invoke a server method by name, converting WorkflowFailure to a structured error dict."""
    method = getattr(_server, method_name)
    try:
        if method_name in {"health", "get_workflow_catalog"}:
            return method()
        return method(payload)
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


if __name__ == "__main__":
    mcp.run()
