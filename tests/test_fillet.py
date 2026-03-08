"""Fillet prep contract tests.

These tests define the expected mock behavior for apply_fillet and validate
the filleted_bracket workflow stage sequence. The live_ops fillet implementation
(adsk.fusion.FilletFeatures) will be built separately; this file pins the
contract the mock must satisfy so the workflow layer can be wired up first.

Mock contract (fusion_addin/ops/mock_ops.apply_fillet):
- Valid body_token + positive radius_cm -> succeeds, returns fillet_applied=True
- Nonexistent body_token -> ValueError
- Missing body_token -> ValueError
- Zero/negative radius_cm -> ValueError

filleted_bracket workflow:
- Registered in build_default_registry()
- Has duplicate verify_geometry stages (position-based matching handles this)
- extension_of=("bracket",)
"""
from __future__ import annotations

import pytest

from fusion_addin.dispatcher import CommandDispatcher
from fusion_addin.workflows import WorkflowRuntime
from mcp_server.workflows import build_default_registry


# ---------------------------------------------------------------------------
# Helper: set up a dispatcher with one extruded body
# ---------------------------------------------------------------------------

def _setup_with_body(d: CommandDispatcher) -> str:
    """Create a design with one rectangular body; return body_token."""
    d.submit("new_design", {"name": "Fillet Test"})
    sketch_token = d.submit("create_sketch", {"plane": "xy", "name": "s"})[
        "result"
    ]["sketch"]["token"]
    d.submit(
        "draw_rectangle",
        {"sketch_token": sketch_token, "width_cm": 3.0, "height_cm": 2.0},
    )
    profiles = d.submit("list_profiles", {"sketch_token": sketch_token})[
        "result"
    ]["profiles"]
    body = d.submit(
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 0.5,
            "body_name": "Bracket",
        },
    )["result"]["body"]
    return body["token"]


# ---------------------------------------------------------------------------
# apply_fillet: success cases
# ---------------------------------------------------------------------------

def test_apply_fillet_valid_body_and_radius() -> None:
    d = CommandDispatcher()
    body_token = _setup_with_body(d)
    result = d.submit("apply_fillet", {"body_token": body_token, "radius_cm": 0.1})
    assert result["ok"] is True
    assert result["result"]["fillet_applied"] is True
    assert result["result"]["body_token"] == body_token
    assert result["result"]["radius_cm"] == pytest.approx(0.1)


def test_apply_fillet_returns_correct_radius() -> None:
    d = CommandDispatcher()
    body_token = _setup_with_body(d)
    result = d.submit("apply_fillet", {"body_token": body_token, "radius_cm": 0.25})
    assert result["result"]["radius_cm"] == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# apply_fillet: error cases
# ---------------------------------------------------------------------------

def test_apply_fillet_nonexistent_body_raises() -> None:
    d = CommandDispatcher()
    d.submit("new_design", {"name": "Empty"})
    with pytest.raises(ValueError, match="does not exist"):
        d.submit("apply_fillet", {"body_token": "body-999", "radius_cm": 0.1})


def test_apply_fillet_missing_body_token_raises() -> None:
    d = CommandDispatcher()
    d.submit("new_design", {"name": "Empty"})
    with pytest.raises((ValueError, KeyError)):
        d.submit("apply_fillet", {"radius_cm": 0.1})


def test_apply_fillet_zero_radius_raises() -> None:
    d = CommandDispatcher()
    body_token = _setup_with_body(d)
    with pytest.raises(ValueError, match="finite positive"):
        d.submit("apply_fillet", {"body_token": body_token, "radius_cm": 0.0})


def test_apply_fillet_negative_radius_raises() -> None:
    d = CommandDispatcher()
    body_token = _setup_with_body(d)
    with pytest.raises(ValueError, match="finite positive"):
        d.submit("apply_fillet", {"body_token": body_token, "radius_cm": -0.5})


# ---------------------------------------------------------------------------
# filleted_bracket: workflow registry
# ---------------------------------------------------------------------------

FILLETED_BRACKET_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_l_bracket_profile",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",   # first check: body exists
    "apply_fillet",
    "verify_geometry",   # second check: body still valid after fillet
    "export_stl",
)


def test_filleted_bracket_registered_in_default_registry() -> None:
    registry = build_default_registry()
    workflow = registry.get("filleted_bracket")
    assert workflow.name == "filleted_bracket"
    assert "fillet" in workflow.intent.lower()
    assert "bracket" in workflow.extension_of


def test_filleted_bracket_stage_tuple_matches_expected() -> None:
    registry = build_default_registry()
    assert registry.get("filleted_bracket").stages == FILLETED_BRACKET_STAGES


def test_filleted_bracket_extension_of_bracket() -> None:
    registry = build_default_registry()
    assert registry.get("filleted_bracket").extension_of == ("bracket",)


def test_filleted_bracket_full_sequence_records_successfully() -> None:
    """Duplicate verify_geometry stages are safe via position-based matching."""
    session = WorkflowRuntime(build_default_registry()).start("filleted_bracket")
    for stage in FILLETED_BRACKET_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(FILLETED_BRACKET_STAGES)


def test_filleted_bracket_out_of_order_raises() -> None:
    """Jumping from new_design straight to apply_fillet is rejected."""
    session = WorkflowRuntime(build_default_registry()).start("filleted_bracket")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("apply_fillet")


def test_filleted_bracket_skipping_first_verify_geometry_raises() -> None:
    """After extrude_profile, the next required stage is verify_geometry (first)."""
    session = WorkflowRuntime(build_default_registry()).start("filleted_bracket")
    for stage in (
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_l_bracket_profile",
        "list_profiles",
        "extrude_profile",
    ):
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("apply_fillet")
