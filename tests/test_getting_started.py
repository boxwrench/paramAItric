from __future__ import annotations

from pathlib import Path

import anyio

from mcp_server.mcp_entrypoint import mcp
from mcp_server.server import ParamAIToolServer
from mcp_server.tool_specs import STATUS_TOOLS


class StubBridge:
    def __init__(self, health_result: dict | None = None, error: Exception | None = None):
        self.health_result = health_result
        self.error = error

    def health(self) -> dict:
        if self.error is not None:
            raise self.error
        assert self.health_result is not None
        return self.health_result


def test_getting_started_explains_live_mode_and_first_actions() -> None:
    server = ParamAIToolServer(
        bridge_client=StubBridge({"ok": True, "status": "ready", "mode": "live"})
    )

    result = server.getting_started()

    assert result["ok"] is True
    assert result["bridge_reachable"] is True
    assert result["mode"] == "live"
    assert "real geometry" in result["mode_explanation"]
    assert Path(result["default_export_folder"]).name == "ParamAItric Exports"
    assert len(result["first_prompts"]) == 2
    assert all(prompt.endswith((".", "?")) for prompt in result["first_prompts"])


def test_getting_started_explains_mock_mode() -> None:
    server = ParamAIToolServer(
        bridge_client=StubBridge({"ok": True, "status": "ready", "mode": "mock"})
    )

    result = server.getting_started()

    assert result["bridge_reachable"] is True
    assert result["mode"] == "mock"
    assert "safe practice environment" in result["mode_explanation"]
    assert "without changing a real Fusion 360 design" in result["mode_explanation"]


def test_getting_started_turns_unreachable_bridge_into_setup_guidance() -> None:
    server = ParamAIToolServer(bridge_client=StubBridge(error=RuntimeError("offline")))

    result = server.getting_started()

    assert result["ok"] is True
    assert result["bridge_reachable"] is False
    assert result["status"] == "setup_needed"
    assert result["mode"] == "unavailable"
    assert "Open Fusion 360" in result["next_step"]
    assert "Add-Ins" in result["next_step"]


def test_getting_started_is_registered_as_a_zero_argument_status_tool() -> None:
    assert STATUS_TOOLS["getting_started"].method == "getting_started"
    tools = {tool.name: tool for tool in anyio.run(mcp.list_tools)}

    schema = tools["getting_started"].inputSchema
    assert schema["properties"] == {}
    assert "required" not in schema
