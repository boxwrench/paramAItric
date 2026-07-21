"""SA-3: cad_inspect must be genuinely read-only, and guided prompts must only
name tools that actually exist under the active tool_profile.

Covers:
- cad_inspect (server.inspect_design) permits each read-only inspection
  operation and rejects convert_bodies_to_components, a mutation.
- The direct convert_bodies_to_components tool still works under the full
  profile and remains in ALL_TOOLS.
- Prompt text rendered under a profile only names tools registered under
  that same profile (guided vs. full).
- A guided spacer build works end-to-end through the cad_* facade, using the
  mock HTTP bridge so the test does not require a live Fusion connection.
"""
from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

import anyio
import pytest

import mcp_server.mcp_entrypoint
import mcp_server.runtime_info as runtime_info
from mcp_server.bridge_client import BridgeClient
from mcp_server.mcp_entrypoint import call_tool
from mcp_server.server import ParamAIToolServer
from mcp_server.tool_specs import ALL_TOOLS, INSPECTION_TOOLS, UTILITY_TOOLS

READ_ONLY_INSPECTION_OPS = (
    "list_design_bodies",
    "get_body_info",
    "get_body_faces",
    "get_body_edges",
    "find_face",
)


def _build_spacer(server: ParamAIToolServer, output_path: Path) -> dict:
    return server.create_spacer(
        {
            "width_cm": 3.0,
            "height_cm": 2.0,
            "thickness_cm": 0.5,
            "output_path": str(output_path),
        }
    )


# ---------------------------------------------------------------------------
# Task 1: cad_inspect allowlist
# ---------------------------------------------------------------------------


def test_inspection_tools_excludes_convert_bodies_to_components() -> None:
    assert "convert_bodies_to_components" not in INSPECTION_TOOLS
    assert "convert_bodies_to_components" in UTILITY_TOOLS
    assert "convert_bodies_to_components" in ALL_TOOLS
    assert set(READ_ONLY_INSPECTION_OPS) == set(INSPECTION_TOOLS)


def test_cad_inspect_permits_each_read_only_operation(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    spacer = _build_spacer(server, tmp_path / "spacer.stl")
    body_token = spacer["body"]["token"]

    res = server.inspect_design({"operation": "list_design_bodies", "parameters": {}})
    assert res["ok"] is True

    res = server.inspect_design(
        {"operation": "get_body_info", "parameters": {"body_token": body_token}}
    )
    assert res["ok"] is True

    res = server.inspect_design(
        {"operation": "get_body_faces", "parameters": {"body_token": body_token}}
    )
    assert res["ok"] is True

    res = server.inspect_design(
        {"operation": "get_body_edges", "parameters": {"body_token": body_token}}
    )
    assert res["ok"] is True

    res = server.inspect_design(
        {
            "operation": "find_face",
            "parameters": {"body_token": body_token, "selector": "top"},
        }
    )
    assert res["ok"] is True


def test_cad_inspect_rejects_convert_bodies_to_components(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    spacer = _build_spacer(server, tmp_path / "spacer_reject.stl")
    body_token = spacer["body"]["token"]

    with pytest.raises(ValueError, match="Unknown inspection operation"):
        server.inspect_design(
            {
                "operation": "convert_bodies_to_components",
                "parameters": {"body_tokens": [body_token]},
            }
        )


def test_direct_convert_bodies_to_components_still_works_in_full_profile(
    running_bridge, tmp_path
) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    spacer = _build_spacer(server, tmp_path / "spacer_convert.stl")
    body_token = spacer["body"]["token"]

    spec = ALL_TOOLS["convert_bodies_to_components"]
    result = call_tool(server, spec.method, {"body_tokens": [body_token]})
    assert result["ok"] is True
    assert result["result"]["count"] == 1


# ---------------------------------------------------------------------------
# Task 2: prompt-to-tool contract, per profile
# ---------------------------------------------------------------------------

_BACKTICKED_IDENTIFIER = re.compile(r"`([a-z][a-z0-9_]*)`")


def _reload_entrypoint() -> None:
    importlib.reload(runtime_info)
    importlib.reload(mcp_server.mcp_entrypoint)


@pytest.fixture(autouse=True)
def _restore_mcp_entrypoint(monkeypatch):
    old_argv = list(sys.argv)
    yield
    monkeypatch.delenv("PARAMAITRIC_PROFILE", raising=False)
    sys.argv = old_argv
    _reload_entrypoint()


@pytest.mark.parametrize(
    "profile_name",
    ["claude-fusion", "lemonade-cuda-fusion"],
)
def test_prompt_tool_references_exist_under_profile(profile_name, monkeypatch) -> None:
    monkeypatch.setenv("PARAMAITRIC_PROFILE", profile_name)
    _reload_entrypoint()

    tools = anyio.run(mcp_server.mcp_entrypoint.mcp.list_tools)
    registered_names = {tool.name for tool in tools}

    rendered_prompts = [
        mcp_server.mcp_entrypoint.cad_status(),
        mcp_server.mcp_entrypoint.cad_list_workflows(),
        mcp_server.mcp_entrypoint.cad_request("Replace a broken clip"),
    ]

    named_tools: set[str] = set()
    for text in rendered_prompts:
        named_tools |= set(_BACKTICKED_IDENTIFIER.findall(text))

    assert named_tools, "expected at least one backticked tool name in the rendered prompts"
    missing = named_tools - registered_names
    assert not missing, (
        f"prompts rendered under profile {profile_name!r} name tools that are not "
        f"registered under that profile: {sorted(missing)}"
    )


def test_guided_prompt_references_cad_inspect_for_verification_only(monkeypatch) -> None:
    monkeypatch.setenv("PARAMAITRIC_PROFILE", "lemonade-cuda-fusion")
    _reload_entrypoint()

    request_prompt = mcp_server.mcp_entrypoint.cad_request("Replace a broken clip")
    assert "`cad_health`" in request_prompt
    assert "`cad_recommend_workflow`" in request_prompt
    assert "`cad_get_requirements`" in request_prompt
    assert "`cad_build`" in request_prompt
    assert "`cad_inspect`" in request_prompt
    assert "read-only" in request_prompt
    # The guided facade must never suggest calling full-profile tool names.
    assert "`health`" not in request_prompt
    assert "`recommend_workflow`" not in request_prompt
    assert "create_*" not in request_prompt


# ---------------------------------------------------------------------------
# Task 2: guided end-to-end build, driven through the facade
# ---------------------------------------------------------------------------


def test_guided_spacer_build_end_to_end_through_facade(monkeypatch, running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    monkeypatch.setenv("PARAMAITRIC_PROFILE", "lemonade-cuda-fusion")
    _reload_entrypoint()

    # Point the freshly-reloaded module's server at the local mock bridge
    # instead of the profile's configured (unreachable in tests) endpoint.
    mcp_server.mcp_entrypoint._server = ParamAIToolServer(BridgeClient(base_url))

    tools = anyio.run(mcp_server.mcp_entrypoint.mcp.list_tools)
    registered_names = {tool.name for tool in tools}
    assert registered_names == {
        "cad_health",
        "cad_recommend_workflow",
        "cad_get_requirements",
        "cad_build",
        "cad_inspect",
    }

    health_res = mcp_server.mcp_entrypoint._call_tool("health", {})
    assert health_res.get("ok", True) is not False

    requirements_res = mcp_server.mcp_entrypoint._call_tool(
        "get_workflow_requirements", {"workflow": "spacer"}
    )
    assert "width_cm" in requirements_res.get("properties", {})

    output_path = tmp_path / "guided_spacer.stl"
    build_res = mcp_server.mcp_entrypoint._call_tool(
        "build_workflow",
        {
            "workflow": "spacer",
            "parameters": {
                "width_cm": 3.0,
                "height_cm": 2.0,
                "thickness_cm": 0.5,
                "output_path": str(output_path),
            },
        },
    )
    assert build_res.get("ok") is True
    body_token = build_res["body"]["token"]

    inspect_res = mcp_server.mcp_entrypoint._call_tool(
        "inspect_design",
        {"operation": "list_design_bodies", "parameters": {}},
    )
    assert inspect_res.get("ok") is True
    assert isinstance(inspect_res.get("result", {}).get("bodies"), list)

    inspect_body_res = mcp_server.mcp_entrypoint._call_tool(
        "inspect_design",
        {"operation": "get_body_info", "parameters": {"body_token": body_token}},
    )
    assert inspect_body_res.get("ok") is True

    # The mutating utility op must remain unreachable through the guided facade.
    with pytest.raises(ValueError, match="Unknown inspection operation"):
        mcp_server.mcp_entrypoint._server.inspect_design(
            {
                "operation": "convert_bodies_to_components",
                "parameters": {"body_tokens": [body_token]},
            }
        )
