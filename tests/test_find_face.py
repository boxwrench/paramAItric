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


# ---------------------------------------------------------------------------
# Failure path: the selector layer must fail closed, and find_face must
# translate an ok:False resolve_selector response into a raised ValueError
# that surfaces the trace reason (core.py find_face lines 400-404).
#
# find_face's own query is fixed to normal_axis/expect=one, which cannot go
# ambiguous or empty against the mock's six-axis box. So we cover the failure
# path two ways:
#   1. a GENUINE end-to-end ambiguity through the real bridge + resolver
#      (largest_planar ties on the box's equal-area top/bottom faces), proving
#      the structured-failure payload actually flows through command dispatch;
#   2. find_face's interpretation of an ok:False response, by stubbing _send —
#      the only honest way to drive its fixed-axis failure branch.
# ---------------------------------------------------------------------------

def test_resolve_selector_ambiguous_fails_closed_end_to_end(running_bridge) -> None:
    """A real largest_planar tie through the bridge returns a structured ok:False, not a wrong pick."""
    _, base_url = running_bridge
    server, body_token = _build_box_body(base_url)

    response = server._send("resolve_selector", {
        "target": "face",
        "kind": "largest_planar",
        "scope": {"body_token": body_token},
        "expect": "one",
    })
    result = response.get("result", response)

    assert result["ok"] is False
    # The command empties top-level tokens so a caller cannot accidentally use one.
    assert result["tokens"] == []
    trace = result["selection_trace"]
    assert trace["status"] == "ambiguous"
    # The box's top and bottom planar faces share the largest area -> a real tie.
    assert trace["candidate_count"] == 2
    # The trace deliberately retains the un-disambiguated candidates as a diagnostic.
    assert trace["resolved_count"] == 2
    assert len(trace["resolved_tokens"]) == 2


def test_find_face_translates_not_ok_into_failclosed_value_error(running_bridge, monkeypatch) -> None:
    """When resolve_selector reports not-ok, find_face raises and surfaces the trace reason."""
    server = ParamAIToolServer(bridge_client=BridgeClient(running_bridge[1]))

    not_ok = {"result": {
        "ok": False,
        "tokens": [],
        "selection_trace": {
            "status": "ambiguous",
            "reason": "Ambiguous: 2 candidates for kind='normal_axis' params={'axis': '+z'}",
            "candidate_count": 2,
            "resolved_count": 0,
        },
    }}
    monkeypatch.setattr(server, "_send", lambda command, arguments: not_ok)

    with pytest.raises(ValueError, match="could not resolve a single 'top' face"):
        server.find_face({"body_token": "b:body:0", "selector": "top"})


def test_find_face_failure_message_includes_underlying_reason(running_bridge, monkeypatch) -> None:
    """The selector layer's reason string is propagated into find_face's error."""
    server = ParamAIToolServer(bridge_client=BridgeClient(running_bridge[1]))

    not_ok = {"result": {
        "ok": False,
        "tokens": [],
        "selection_trace": {
            "status": "empty",
            "reason": "No candidates found for kind='normal_axis' params={'axis': '+x'}",
        },
    }}
    monkeypatch.setattr(server, "_send", lambda command, arguments: not_ok)

    with pytest.raises(ValueError, match="No candidates found"):
        server.find_face({"body_token": "b:body:0", "selector": "right"})


def test_find_face_not_ok_without_trace_reports_unknown(running_bridge, monkeypatch) -> None:
    """A not-ok response missing its trace still fails closed, reporting 'unknown'."""
    server = ParamAIToolServer(bridge_client=BridgeClient(running_bridge[1]))

    monkeypatch.setattr(server, "_send", lambda command, arguments: {"result": {"ok": False}})

    with pytest.raises(ValueError, match="unknown"):
        server.find_face({"body_token": "b:body:0", "selector": "left"})
