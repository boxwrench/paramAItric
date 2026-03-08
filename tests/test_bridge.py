from __future__ import annotations

from mcp_server.bridge_client import BridgeClient
from mcp_server.schemas import CommandEnvelope


def test_bridge_health_endpoint(running_bridge) -> None:
    _, base_url = running_bridge
    client = BridgeClient(base_url)
    health = client.health()
    assert health["ok"] is True
    assert health["status"] == "ready"
    assert health["mode"] == "mock"
    assert any(workflow["name"] == "spacer" for workflow in health["workflow_catalog"])


def test_bridge_runs_single_command(running_bridge) -> None:
    _, base_url = running_bridge
    client = BridgeClient(base_url)
    result = client.send(CommandEnvelope.build("new_design", {"name": "Smoke Test"}))
    assert result["ok"] is True
    assert result["result"]["design_name"] == "Smoke Test"
