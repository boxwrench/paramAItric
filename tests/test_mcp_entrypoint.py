from __future__ import annotations

import anyio

from mcp_server.mcp_entrypoint import mcp
from mcp_server.server import ParamAIToolServer
from mcp_server.tool_specs import ALL_TOOLS, INSPECTION_TOOLS, STATUS_TOOLS, WORKFLOW_TOOLS


def test_exported_mcp_tools_resolve_to_server_methods() -> None:
    server = ParamAIToolServer()

    assert len(ALL_TOOLS) == 28

    for tool_name, spec in ALL_TOOLS.items():
        method = getattr(server, spec.method, None)
        assert method is not None, f"{tool_name} points to missing method {spec.method!r}"
        assert callable(method), f"{tool_name} points to non-callable attribute {spec.method!r}"
        assert spec.description.strip(), f"{tool_name} must have a non-empty description"


def test_mcp_entrypoint_registers_expected_tool_names() -> None:
    tools = anyio.run(mcp.list_tools)
    registered_names = [tool.name for tool in tools]

    assert registered_names == list(ALL_TOOLS.keys())


def test_mcp_entrypoint_exposes_status_and_workflow_tool_shapes() -> None:
    tools = {tool.name: tool for tool in anyio.run(mcp.list_tools)}

    status_schema = tools["health"].inputSchema
    assert status_schema["properties"] == {}
    assert "required" not in status_schema

    workflow_schema = tools["create_spacer"].inputSchema
    assert workflow_schema["required"] == ["payload"]
    assert workflow_schema["properties"]["payload"]["type"] == "object"

    assert set(STATUS_TOOLS) <= set(tools)
    assert set(INSPECTION_TOOLS) <= set(tools)
    assert set(WORKFLOW_TOOLS) <= set(tools)
