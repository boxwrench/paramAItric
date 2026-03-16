"""Cut extrusion contract tests.

These tests define the expected mock behavior for the `operation` parameter on
extrude_profile.  The actual live_ops Fusion implementation will be built
separately; this file pins the contract that the mock must satisfy so that the
workflow layer can be wired up before the live path exists.

Schema contract (mcp_server/schemas._validate_extrude_operation):
- None or missing -> "new_body" (backward-compatible default)
- "new_body"      -> accepted
- "cut"           -> accepted
- anything else   -> ValueError

Mock-ops contract (fusion_addin/ops/mock_ops.extrude_profile):
- operation="new_body" (default) behaves exactly as before
- operation="cut" with an existing body succeeds and returns that body's token
- operation="cut" with no existing body raises ValueError
- operation="<unknown>" raises ValueError via the schema validator

plate_with_hole workflow (mcp_server/workflows):
- Registered with 13 stages including duplicate create_sketch, list_profiles,
  extrude_profile, and verify_geometry names.
- WorkflowSession.record() uses position-based matching
  (allowed_stages[len(completed_stages)]) so duplicate names are safe.
  The two_hole_mounting_bracket workflow already relies on this for its two
  "draw_circle" stages; plate_with_hole follows the same pattern.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from fusion_addin.dispatcher import CommandDispatcher
from fusion_addin.state import DesignState
from fusion_addin.workflows import WorkflowRuntime
from mcp_server.schemas import _validate_extrude_operation
from mcp_server.workflow_registry import build_default_registry


# ---------------------------------------------------------------------------
# Schema validator: _validate_extrude_operation
# ---------------------------------------------------------------------------

def test_validate_extrude_operation_none_returns_new_body() -> None:
    assert _validate_extrude_operation(None) == "new_body"


def test_validate_extrude_operation_explicit_new_body() -> None:
    assert _validate_extrude_operation("new_body") == "new_body"


def test_validate_extrude_operation_cut() -> None:
    assert _validate_extrude_operation("cut") == "cut"


def test_validate_extrude_operation_unknown_raises() -> None:
    with pytest.raises(ValueError, match="operation must be one of"):
        _validate_extrude_operation("slice")


def test_validate_extrude_operation_empty_string_raises() -> None:
    with pytest.raises(ValueError, match="operation must be one of"):
        _validate_extrude_operation("")


def test_validate_extrude_operation_non_string_raises() -> None:
    with pytest.raises(ValueError, match="operation must be one of"):
        _validate_extrude_operation(1)


# ---------------------------------------------------------------------------
# Mock-ops via CommandDispatcher: operation="new_body" (default behavior)
# ---------------------------------------------------------------------------

def _setup(d: CommandDispatcher) -> tuple[str, str]:
    """Set up a sketch with one rectangle profile; return (sketch_token, profile_token)."""
    d.submit("new_design", {"name": "Cut Extrusion Test"})
    sketch_token = d.submit("create_sketch", {"plane": "xy", "name": "s"})["result"]["sketch"]["token"]
    d.submit("draw_rectangle", {"sketch_token": sketch_token, "width_cm": 4.0, "height_cm": 2.0})
    profiles = d.submit("list_profiles", {"sketch_token": sketch_token})["result"]["profiles"]
    return sketch_token, profiles[0]["token"]


def test_extrude_new_body_operation_explicit(tmp_path) -> None:
    """operation='new_body' works identically to the default."""
    d = CommandDispatcher()
    _, profile_token = _setup(d)

    result = d.submit("extrude_profile", {
        "profile_token": profile_token,
        "distance_cm": 0.5,
        "body_name": "Plate",
        "operation": "new_body",
    })

    assert result["ok"] is True
    body = result["result"]["body"]
    assert body["name"] == "Plate"
    assert result["result"]["operation"] == "new_body"


def test_extrude_new_body_operation_omitted_is_default(tmp_path) -> None:
    """Omitting operation= is backward-compatible: behaves as new_body."""
    d = CommandDispatcher()
    _, profile_token = _setup(d)

    result = d.submit("extrude_profile", {
        "profile_token": profile_token,
        "distance_cm": 0.5,
        "body_name": "Plate",
    })

    assert result["ok"] is True
    # The response now includes operation="new_body"
    assert result["result"]["operation"] == "new_body"


# ---------------------------------------------------------------------------
# Mock-ops via CommandDispatcher: operation="cut"
# ---------------------------------------------------------------------------

def test_extrude_cut_operation_on_existing_body() -> None:
    """cut operation with an existing body succeeds; returns that body's token."""
    d = CommandDispatcher()
    _, profile_token = _setup(d)

    # Create the base body first
    base = d.submit("extrude_profile", {
        "profile_token": profile_token,
        "distance_cm": 0.5,
        "body_name": "Plate",
    })["result"]["body"]

    # Now draw a circle and cut through it
    sketch_token = d.submit("create_sketch", {"plane": "xy", "name": "hole_sketch"})["result"]["sketch"]["token"]
    d.submit("draw_circle", {
        "sketch_token": sketch_token,
        "center_x_cm": 0.5,
        "center_y_cm": 0.5,
        "radius_cm": 0.1,
    })
    hole_profiles = d.submit("list_profiles", {"sketch_token": sketch_token})["result"]["profiles"]

    cut_result = d.submit("extrude_profile", {
        "profile_token": hole_profiles[0]["token"],
        "distance_cm": 0.5,
        "body_name": "hole",
        "operation": "cut",
    })

    assert cut_result["ok"] is True
    assert cut_result["result"]["operation"] == "cut"
    # Mock returns the existing body's token, not a new one
    assert cut_result["result"]["body"]["token"] == base["token"]


def test_extrude_cut_operation_when_no_body_raises() -> None:
    """cut operation with no existing bodies raises ValueError — nothing to cut into."""
    d = CommandDispatcher()
    _, profile_token = _setup(d)

    with pytest.raises(ValueError, match="cut operation requires at least one existing body"):
        d.submit("extrude_profile", {
            "profile_token": profile_token,
            "distance_cm": 0.5,
            "body_name": "hole",
            "operation": "cut",
        })


def test_extrude_invalid_operation_raises() -> None:
    """An unknown operation string raises ValueError before hitting the CAD logic."""
    d = CommandDispatcher()
    _, profile_token = _setup(d)

    with pytest.raises(ValueError, match="operation must be one of"):
        d.submit("extrude_profile", {
            "profile_token": profile_token,
            "distance_cm": 0.5,
            "body_name": "x",
            "operation": "bevel",
        })


# ---------------------------------------------------------------------------
# plate_with_hole: workflow registry and stage ordering
# ---------------------------------------------------------------------------

PLATE_WITH_HOLE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",    # first sketch
    "draw_rectangle",
    "list_profiles",    # first listing
    "extrude_profile",  # new_body
    "verify_geometry",  # first geometry check
    "create_sketch",    # second sketch
    "draw_circle",
    "list_profiles",    # second listing
    "extrude_profile",  # cut
    "verify_geometry",  # second geometry check
    "export_stl",
)


def test_plate_with_hole_registered_in_default_registry() -> None:
    registry = build_default_registry()
    workflow = registry.get("plate_with_hole")
    assert workflow.name == "plate_with_hole"
    assert "cut" in workflow.intent.lower()
    assert workflow.extension_of == ("spacer", "mounting_bracket")


def test_plate_with_hole_stage_tuple_matches_expected() -> None:
    registry = build_default_registry()
    assert registry.get("plate_with_hole").stages == PLATE_WITH_HOLE_STAGES


def test_plate_with_hole_full_sequence_records_successfully() -> None:
    """WorkflowSession.record() handles duplicate stage names via position-based matching.

    plate_with_hole has two each of: create_sketch, list_profiles,
    extrude_profile, verify_geometry.  This is intentional and safe because
    record() checks allowed_stages[len(completed_stages)], not set membership.
    The two_hole_mounting_bracket workflow already relies on the same mechanism
    for its two 'draw_circle' stages.
    """
    session = WorkflowRuntime(build_default_registry()).start("plate_with_hole")
    for stage in PLATE_WITH_HOLE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(PLATE_WITH_HOLE_STAGES)


def test_plate_with_hole_out_of_order_raises() -> None:
    """Jumping from new_design straight to draw_rectangle is rejected."""
    session = WorkflowRuntime(build_default_registry()).start("plate_with_hole")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("draw_rectangle")


def test_plate_with_hole_skipping_second_create_sketch_raises() -> None:
    """After the first verify_geometry, the next required stage is create_sketch (second)."""
    session = WorkflowRuntime(build_default_registry()).start("plate_with_hole")
    for stage in (
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
    ):
        session.record(stage)
    # Trying to go straight to draw_circle should be rejected
    with pytest.raises(ValueError, match="out of order"):
        session.record("draw_circle")


def test_plate_with_hole_unknown_stage_raises() -> None:
    session = WorkflowRuntime(build_default_registry()).start("plate_with_hole")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("draw_l_bracket_profile")


def test_plate_with_hole_extension_of_includes_spacer_and_mounting_bracket() -> None:
    registry = build_default_registry()
    workflow = registry.get("plate_with_hole")
    assert "spacer" in workflow.extension_of
    assert "mounting_bracket" in workflow.extension_of
