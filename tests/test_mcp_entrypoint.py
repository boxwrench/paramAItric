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
    UTILITY_TOOLS,
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
        *UTILITY_TOOLS,
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


def test_mcp_entrypoint_prompts_are_unique_and_complete() -> None:
    prompts = {prompt.name: prompt for prompt in anyio.run(mcp.list_prompts)}
    assert "cad_status" in prompts
    assert "cad_list_workflows" in prompts
    assert "cad_request" in prompts

    # Prompt list length check
    assert len(prompts) == 3

    from mcp_server.mcp_entrypoint import cad_request
    prompt_text = cad_request("test_part")
    assert "Step 1" in prompt_text
    assert "Step 2" in prompt_text
    assert "Step 3" in prompt_text
    assert "Step 4" in prompt_text


def test_fastmcp_internal_tool_manager_compatibility() -> None:
    # Ensure mcp._tool_manager and its tools parameter dictionary exists
    assert hasattr(mcp, "_tool_manager")
    assert hasattr(mcp._tool_manager, "_tools")
    assert isinstance(mcp._tool_manager._tools, dict)
    for tool_name in mcp._tool_manager._tools:
        tool = mcp._tool_manager._tools[tool_name]
        assert hasattr(tool, "parameters")


def test_workflow_schema_coverage_and_fidelity() -> None:
    tools = {tool.name: tool for tool in anyio.run(mcp.list_tools)}

    for tool_name in WORKFLOW_TOOLS:
        assert tool_name in tools, f"Workflow tool {tool_name} was not registered"
        schema = tools[tool_name].inputSchema
        
        # Must have required payload envelope
        assert schema.get("type") == "object"
        assert schema.get("required") == ["payload"]
        
        payload_schema = schema["properties"]["payload"]
        assert payload_schema["type"] == "object"
        assert payload_schema["additionalProperties"] is False
        assert payload_schema["properties"]

    # Pin representative numeric bounds, enums, defaults, and unit metadata on create_spacer
    spacer_payload = tools["create_spacer"].inputSchema["properties"]["payload"]
    properties = spacer_payload["properties"]
    required = spacer_payload["required"]

    # Verify required fields
    assert required == ["width_cm", "height_cm", "thickness_cm", "output_path"]

    # Verify unit selector enums and defaults
    assert "units" in properties
    assert properties["units"]["type"] == "string"
    assert properties["units"]["enum"] == ["cm", "mm", "in"]
    assert properties["units"]["default"] == "cm"

    # Verify numeric bounds & metadata
    assert "width_cm" in properties
    width_prop = properties["width_cm"]
    assert width_prop["type"] == "number"
    assert width_prop["exclusiveMinimum"] == 0
    assert width_prop["x-unit-selector"] == "units"

    # Verify string defaults
    assert "sketch_name" in properties
    assert properties["sketch_name"]["type"] == "string"
    assert properties["sketch_name"]["default"] == "Spacer Sketch"



