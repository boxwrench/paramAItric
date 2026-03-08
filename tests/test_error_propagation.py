"""End-to-end error propagation tests.

Covers the full error chain from mock-ops failure through HTTP bridge,
BridgeClient, and MCP workflow layer for all registered workflow types.

Scenarios not already covered by test_workflow.py:
- Bridge errors and timeouts at early / mid workflow stages
- Bracket-specific stages (draw_l_bracket_profile, list_profiles)
- Mounting-bracket draw_circle failures with partial hole progress
- Two-hole draw_circle failure on the second hole specifically
- A single real-wire test that exercises the genuine HTTP 400 path
  (dispatcher fails → bridge returns 400 → BridgeClient raises RuntimeError
  → _bridge_step wraps as WorkflowFailure) rather than a Python-level inject.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.bridge_client import BridgeClient, BridgeTimeoutError
from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import CommandEnvelope
from mcp_server.server import ParamAIToolServer


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class InterceptingBridgeClient:
    """Wraps a real BridgeClient, intercepting named commands with a callable.

    Interceptors receive (envelope, client, call_count) and must either return
    a result dict or raise.  call_count is per-command, starting at 1.
    """

    def __init__(self, base_url: str, interceptors: dict) -> None:
        self._client = BridgeClient(base_url)
        self._interceptors = interceptors
        self._call_counts: dict[str, int] = {}

    def health(self) -> dict:
        return self._client.health()

    def send(self, envelope: CommandEnvelope) -> dict:
        command = envelope.command
        self._call_counts[command] = self._call_counts.get(command, 0) + 1
        interceptor = self._interceptors.get(command)
        if interceptor is not None:
            return interceptor(
                envelope=envelope,
                client=self._client,
                call_count=self._call_counts[command],
            )
        return self._client.send(envelope)


def _raise_error(message: str):
    def _interceptor(*, envelope, client, call_count):
        _ = (envelope, client, call_count)
        raise RuntimeError(message)
    return _interceptor


def _raise_timeout(*, envelope, client, call_count):
    _ = (envelope, client, call_count)
    raise BridgeTimeoutError("Fusion bridge request timed out.")


# ---------------------------------------------------------------------------
# Shared payload fixtures
# ---------------------------------------------------------------------------

_SPACER_PAYLOAD = {
    "width_cm": 2.0,
    "height_cm": 1.0,
    "thickness_cm": 0.5,
    "output_path": str(Path.cwd() / "manual_test_output" / "error_prop_spacer.stl"),
}

_BRACKET_PAYLOAD = {
    "width_cm": 4.0,
    "height_cm": 2.0,
    "thickness_cm": 0.75,
    "leg_thickness_cm": 0.5,
    "plane": "xy",
    "output_path": str(Path.cwd() / "manual_test_output" / "error_prop_bracket.stl"),
}

_MOUNTING_BRACKET_PAYLOAD = {
    "width_cm": 4.0,
    "height_cm": 2.0,
    "thickness_cm": 0.75,
    "leg_thickness_cm": 0.5,
    "hole_diameter_cm": 0.4,
    "hole_center_x_cm": 0.25,
    "hole_center_y_cm": 1.5,
    "plane": "xy",
    "output_path": str(Path.cwd() / "manual_test_output" / "error_prop_mounting_bracket.stl"),
}

_TWO_HOLE_PAYLOAD = {
    "width_cm": 4.0,
    "height_cm": 2.0,
    "thickness_cm": 0.75,
    "leg_thickness_cm": 0.5,
    "hole_diameter_cm": 0.4,
    "first_hole_center_x_cm": 0.25,
    "first_hole_center_y_cm": 1.5,
    "second_hole_center_x_cm": 1.5,
    "second_hole_center_y_cm": 0.25,
    "plane": "xy",
    "output_path": str(Path.cwd() / "manual_test_output" / "error_prop_two_hole.stl"),
}


# ---------------------------------------------------------------------------
# Spacer: bridge errors at early and mid stages
# ---------------------------------------------------------------------------

def test_spacer_wraps_bridge_error_at_create_sketch(running_bridge) -> None:
    """Bridge error at create_sketch wraps as WorkflowFailure with correct stage."""
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"create_sketch": _raise_error("sketch service unavailable")},
        )
    )

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_spacer(_SPACER_PAYLOAD)

    failure = exc_info.value
    assert failure.stage == "create_sketch"
    assert failure.classification == "bridge_error"
    # new_design completed before failure
    completed_stages = [s["stage"] for s in failure.partial_result["stages"]]
    assert "new_design" in completed_stages
    assert "create_sketch" not in completed_stages


def test_spacer_wraps_bridge_error_at_draw_rectangle(running_bridge) -> None:
    """Bridge error at draw_rectangle wraps as WorkflowFailure; create_sketch stage recorded."""
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"draw_rectangle": _raise_error("geometry kernel error")},
        )
    )

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_spacer(_SPACER_PAYLOAD)

    failure = exc_info.value
    assert failure.stage == "draw_rectangle"
    assert failure.classification == "bridge_error"
    completed_stages = [s["stage"] for s in failure.partial_result["stages"]]
    assert "create_sketch" in completed_stages
    assert "draw_rectangle" not in completed_stages


def test_spacer_wraps_timeout_at_extrude_profile(running_bridge) -> None:
    """Timeout at extrude_profile wraps as WorkflowFailure('timeout'); partial stages include list_profiles."""
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"extrude_profile": _raise_timeout},
        )
    )

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_spacer(_SPACER_PAYLOAD)

    failure = exc_info.value
    assert failure.stage == "extrude_profile"
    assert failure.classification == "timeout"
    assert "timed out" in str(failure)
    completed_stages = [s["stage"] for s in failure.partial_result["stages"]]
    assert "list_profiles" in completed_stages
    assert "extrude_profile" not in completed_stages


# ---------------------------------------------------------------------------
# Bracket: bracket-specific stage coverage
# ---------------------------------------------------------------------------

def test_bracket_wraps_bridge_error_at_draw_l_bracket_profile(running_bridge) -> None:
    """Bridge error at draw_l_bracket_profile wraps correctly in bracket workflow."""
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"draw_l_bracket_profile": _raise_error("l-bracket kernel error")},
        )
    )

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_bracket(_BRACKET_PAYLOAD)

    failure = exc_info.value
    assert failure.stage == "draw_l_bracket_profile"
    assert failure.classification == "bridge_error"
    completed_stages = [s["stage"] for s in failure.partial_result["stages"]]
    assert "create_sketch" in completed_stages
    assert "draw_l_bracket_profile" not in completed_stages


def test_bracket_wraps_timeout_at_list_profiles(running_bridge) -> None:
    """Timeout at list_profiles wraps as WorkflowFailure('timeout') in bracket workflow."""
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"list_profiles": _raise_timeout},
        )
    )

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_bracket(_BRACKET_PAYLOAD)

    failure = exc_info.value
    assert failure.stage == "list_profiles"
    assert failure.classification == "timeout"
    completed_stages = [s["stage"] for s in failure.partial_result["stages"]]
    assert "draw_l_bracket_profile" in completed_stages


# ---------------------------------------------------------------------------
# Mounting bracket: draw_circle failure
# ---------------------------------------------------------------------------

def test_mounting_bracket_wraps_bridge_error_at_draw_circle(running_bridge) -> None:
    """Bridge error at draw_circle wraps correctly; partial_result includes hole_index."""
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"draw_circle": _raise_error("circle arc failed")},
        )
    )

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_mounting_bracket(_MOUNTING_BRACKET_PAYLOAD)

    failure = exc_info.value
    assert failure.stage == "draw_circle"
    assert failure.classification == "bridge_error"
    assert failure.partial_result.get("hole_index") == 1
    completed_stages = [s["stage"] for s in failure.partial_result["stages"]]
    assert "draw_l_bracket_profile" in completed_stages


# ---------------------------------------------------------------------------
# Two-hole mounting bracket: second hole failure and mid-workflow timeout
# ---------------------------------------------------------------------------

def test_two_hole_mounting_bracket_wraps_bridge_error_at_second_draw_circle(running_bridge) -> None:
    """Bridge error on the second draw_circle fails at draw_circle; first hole already recorded."""
    _, base_url = running_bridge

    def _fail_second_circle(*, envelope, client, call_count):
        if call_count == 2:
            raise RuntimeError("second circle draw failed")
        return client.send(envelope)

    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"draw_circle": _fail_second_circle},
        )
    )

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_two_hole_mounting_bracket(_TWO_HOLE_PAYLOAD)

    failure = exc_info.value
    assert failure.stage == "draw_circle"
    assert failure.classification == "bridge_error"
    # First hole was recorded; second was not
    circle_stages = [s for s in failure.partial_result["stages"] if s["stage"] == "draw_circle"]
    assert len(circle_stages) == 1
    assert circle_stages[0]["hole_index"] == 1


def test_two_hole_mounting_bracket_wraps_timeout_at_extrude(running_bridge) -> None:
    """Timeout at extrude_profile in two_hole workflow; both circles appear in partial stages."""
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"extrude_profile": _raise_timeout},
        )
    )

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_two_hole_mounting_bracket(_TWO_HOLE_PAYLOAD)

    failure = exc_info.value
    assert failure.stage == "extrude_profile"
    assert failure.classification == "timeout"
    completed_stages = [s["stage"] for s in failure.partial_result["stages"]]
    assert completed_stages.count("draw_circle") == 2


# ---------------------------------------------------------------------------
# Real-wire: genuine HTTP 400 from mock-ops → RuntimeError → WorkflowFailure
# ---------------------------------------------------------------------------

class _RealWireFailingClient:
    """Delegates to a real BridgeClient for all commands except one.

    At the intercepted command, sends a deliberately malformed request to the
    real HTTP bridge so the failure originates from a genuine HTTP 400 response,
    exercising the full chain:
      mock-ops raises → HTTP bridge returns 400 → BridgeClient raises RuntimeError
      → _bridge_step wraps as WorkflowFailure
    """

    def __init__(self, real_client: BridgeClient, fail_on: str) -> None:
        self._client = real_client
        self._fail_on = fail_on

    def health(self) -> dict:
        return self._client.health()

    def send(self, envelope: CommandEnvelope) -> dict:
        if envelope.command == self._fail_on:
            # Send a real extrude_profile with an invalid token to get a real HTTP 400.
            # The mock-ops extrude_profile handler validates the token format
            # ("sketch-N:profile:M") and raises ValueError for anything else,
            # which the HTTP bridge surfaces as a 400 error response.
            bad = CommandEnvelope.build(
                "extrude_profile",
                {
                    "profile_token": "not-a-valid:token-format",
                    "distance_cm": 0.5,
                    "body_name": "x",
                },
            )
            return self._client.send(bad)  # raises RuntimeError from the real 400
        return self._client.send(envelope)


def test_real_wire_operation_failure_propagates_as_workflow_failure(running_bridge) -> None:
    """A real mock-ops failure (real HTTP 400) surfaces as WorkflowFailure at workflow layer.

    This exercises the complete four-layer chain without any Python-level injection:
      1. dispatcher — real mock-ops handler raises ValueError on invalid token
      2. HTTP bridge — returns a real 400 error response
      3. BridgeClient — raises RuntimeError("Bridge command failed: ...")
      4. MCP workflow (_bridge_step) — wraps RuntimeError as WorkflowFailure
    """
    _, base_url = running_bridge
    real_client = BridgeClient(base_url)
    server = ParamAIToolServer(_RealWireFailingClient(real_client, fail_on="draw_rectangle"))

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_spacer(_SPACER_PAYLOAD)

    failure = exc_info.value
    assert failure.stage == "draw_rectangle"
    assert failure.classification == "bridge_error"
    # The RuntimeError message from BridgeClient is embedded in the WorkflowFailure message.
    assert "Bridge command failed" in str(failure)
    completed_stages = [s["stage"] for s in failure.partial_result["stages"]]
    assert "create_sketch" in completed_stages
