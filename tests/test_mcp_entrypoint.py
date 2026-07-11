from __future__ import annotations

import anyio

from fusion_addin.ops.mock_ops import build_registry as build_fusion_registry
from mcp_server.mcp_entrypoint import mcp
from mcp_server.server import ParamAIToolServer
from mcp_server.tool_specs import (
    ALL_TOOLS,
    FREEFORM_SESSION_TOOLS,
    INSPECTION_TOOLS,
    STATUS_TOOLS,
    WORKFLOW_TOOLS,
)
from mcp_server.workflow_availability import EXPERIMENTAL_WORKFLOWS
from mcp_server.workflow_registry import build_default_registry


def test_exported_mcp_tools_resolve_to_server_methods() -> None:
    server = ParamAIToolServer()

    category_tool_names = [
        *STATUS_TOOLS,
        *INSPECTION_TOOLS,
        *FREEFORM_SESSION_TOOLS,
        *WORKFLOW_TOOLS,
    ]
    assert len(category_tool_names) == len(set(category_tool_names))
    assert list(ALL_TOOLS) == category_tool_names

    for tool_name, spec in ALL_TOOLS.items():
        method = getattr(server, spec.method, None)
        assert method is not None, f"{tool_name} points to missing method {spec.method!r}"
        assert callable(method), f"{tool_name} points to non-callable attribute {spec.method!r}"
        assert spec.description.strip(), f"{tool_name} must have a non-empty description"


def test_default_workflow_tools_match_available_fusion_catalog() -> None:
    advertised_workflows = {
        tool_name.removeprefix("create_") for tool_name in WORKFLOW_TOOLS
    }
    default_registry_workflows = {
        workflow.name for workflow in build_default_registry().list()
    }
    fusion_catalog_workflows = {
        workflow["name"] for workflow in build_fusion_registry().workflow_catalog()
    }

    assert advertised_workflows == default_registry_workflows
    assert advertised_workflows == fusion_catalog_workflows
    assert advertised_workflows.isdisjoint(EXPERIMENTAL_WORKFLOWS)


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
