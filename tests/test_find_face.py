"""Integration tests for find_face routing through the deterministic selector layer.

These tests exercise the full path:
  ParamAIToolServer.find_face -> _send("resolve_selector", ...) -> mock_ops.resolve_selector
  -> mcp_server.selectors.resolve -> SelectionTrace

A body is built by driving the bridge directly (no freeform session required),
then find_face is called on the ParamAIToolServer.
"""
from __future__ import annotations

import pytest

from fusion_addin.dispatcher import CommandDispatcher
from mcp_server.bridge_client import BridgeClient
from mcp_server.server import ParamAIToolServer


# ---------------------------------------------------------------------------
# Helper: build a box body via the bridge HTTP server
# ---------------------------------------------------------------------------

def _build_box_body(base_url: str) -> tuple[ParamAIToolServer, str]:
    """Start a server, create a simple extruded box, return (server, body_token)."""
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))
    server.new_design("Find Face Test")
    res_sk = server._send("create_sketch", {"plane": "xy", "name": "S1"})
    sketch_token = res_sk["result"]["sketch"]["token"]
    server._send("draw_rectangle", {"sketch_token": sketch_token, "width_cm": 10.0, "height_cm": 10.0})
    profiles = server._send("list_profiles", {"sketch_token": sketch_token})["result"]["profiles"]
    profile_token = profiles[0]["token"]
    res = server._send("extrude_profile", {
        "profile_token": profile_token,
        "distance_cm": 5.0,
        "body_name": "Test Box",
    })
    body_token = res["result"]["body"]["token"]
    return server, body_token


# ---------------------------------------------------------------------------
# Success: top face resolves via normal_axis +z
# ---------------------------------------------------------------------------

def test_find_face_top_returns_ok_and_trace(running_bridge) -> None:
    _, base_url = running_bridge
    server, body_token = _build_box_body(base_url)

    result = server.find_face({"body_token": body_token, "selector": "top"})

    assert result["ok"] is True
    assert result["selector"] == "top"
    assert result["face_token"].endswith(":face:top")
    assert result["selection_trace"]["status"] == "resolved"
    assert result["selection_trace"]["kind"] == "normal_axis"


def test_find_face_bottom_resolves(running_bridge) -> None:
    _, base_url = running_bridge
    server, body_token = _build_box_body(base_url)

    result = server.find_face({"body_token": body_token, "selector": "bottom"})

    assert result["ok"] is True
    assert result["face_token"].endswith(":face:bottom")
    assert result["selection_trace"]["status"] == "resolved"


def test_find_face_no_face_info_key(running_bridge) -> None:
    """Confirm the old face_info key is gone — callers must use selection_trace."""
    _, base_url = running_bridge
    server, body_token = _build_box_body(base_url)

    result = server.find_face({"body_token": body_token, "selector": "top"})

    assert "face_info" not in result
    assert "selection_trace" in result


# ---------------------------------------------------------------------------
# Input validation: unchanged public contract
# ---------------------------------------------------------------------------

def test_find_face_unknown_selector_raises_value_error(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    with pytest.raises(ValueError, match="selector must be one of"):
        server.find_face({"body_token": "b:body:0", "selector": "upward"})


def test_find_face_missing_body_token_raises_value_error(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    with pytest.raises(ValueError, match="body_token is required"):
        server.find_face({"selector": "top"})


# ---------------------------------------------------------------------------
# Direction-to-axis mapping: all six directions resolve
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("selector,expected_suffix", [
    ("top", ":face:top"),
    ("bottom", ":face:bottom"),
    ("left", ":face:left"),
    ("right", ":face:right"),
    ("front", ":face:front"),
    ("back", ":face:back"),
])
def test_find_face_all_directions_resolve(running_bridge, selector, expected_suffix) -> None:
    _, base_url = running_bridge
    server, body_token = _build_box_body(base_url)

    result = server.find_face({"body_token": body_token, "selector": selector})

    assert result["ok"] is True
    assert result["face_token"].endswith(expected_suffix)
    assert result["selection_trace"]["status"] == "resolved"
    assert result["selection_trace"]["kind"] == "normal_axis"
