"""Workflow stage enforcement tests.

Covers WorkflowRuntime.start() and WorkflowSession.record() for every
registered workflow. Verifies ordering rules, out-of-sequence rejection,
and unknown-stage rejection.
"""
from __future__ import annotations

import pytest

from fusion_addin.workflows import WorkflowRuntime
from mcp_server.workflows import build_default_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def runtime() -> WorkflowRuntime:
    return WorkflowRuntime(build_default_registry())


def full_sequence(workflow_name: str) -> tuple[str, ...]:
    return build_default_registry().get(workflow_name).stages


# ---------------------------------------------------------------------------
# spacer
# ---------------------------------------------------------------------------

SPACER_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_spacer_full_sequence_records_successfully() -> None:
    session = runtime().start("spacer")
    for stage in SPACER_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(SPACER_STAGES)


def test_spacer_out_of_order_raises() -> None:
    session = runtime().start("spacer")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("export_stl")


def test_spacer_unknown_stage_raises() -> None:
    session = runtime().start("spacer")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("draw_l_bracket_profile")


def test_spacer_duplicate_stage_raises() -> None:
    """Recording new_design twice should fail because the second time it is out of order."""
    session = runtime().start("spacer")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("new_design")


# ---------------------------------------------------------------------------
# bracket
# ---------------------------------------------------------------------------

BRACKET_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_l_bracket_profile",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_bracket_full_sequence_records_successfully() -> None:
    session = runtime().start("bracket")
    for stage in BRACKET_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(BRACKET_STAGES)


def test_bracket_out_of_order_raises() -> None:
    session = runtime().start("bracket")
    session.record("new_design")
    session.record("verify_clean_state")
    with pytest.raises(ValueError, match="out of order"):
        session.record("extrude_profile")


def test_bracket_unknown_stage_raises() -> None:
    session = runtime().start("bracket")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("draw_circle")


def test_bracket_duplicate_stage_raises() -> None:
    session = runtime().start("bracket")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("new_design")


# ---------------------------------------------------------------------------
# mounting_bracket
# ---------------------------------------------------------------------------

MOUNTING_BRACKET_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_l_bracket_profile",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_mounting_bracket_full_sequence_records_successfully() -> None:
    session = runtime().start("mounting_bracket")
    for stage in MOUNTING_BRACKET_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(MOUNTING_BRACKET_STAGES)


def test_mounting_bracket_out_of_order_raises() -> None:
    session = runtime().start("mounting_bracket")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("draw_circle")


def test_mounting_bracket_unknown_stage_raises() -> None:
    session = runtime().start("mounting_bracket")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("loft_profiles")


def test_mounting_bracket_duplicate_stage_raises() -> None:
    session = runtime().start("mounting_bracket")
    # advance to draw_circle
    for stage in ("new_design", "verify_clean_state", "create_sketch", "draw_l_bracket_profile"):
        session.record(stage)
    session.record("draw_circle")
    # draw_circle only appears once in mounting_bracket — recording it again is out of order
    with pytest.raises(ValueError, match="out of order"):
        session.record("draw_circle")


# ---------------------------------------------------------------------------
# two_hole_mounting_bracket
# ---------------------------------------------------------------------------

TWO_HOLE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_l_bracket_profile",
    "draw_circle",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_two_hole_mounting_bracket_full_sequence_records_successfully() -> None:
    session = runtime().start("two_hole_mounting_bracket")
    for stage in TWO_HOLE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(TWO_HOLE_STAGES)


def test_two_hole_mounting_bracket_both_circles_recorded_in_order() -> None:
    """Both draw_circle stages must be accepted in sequence."""
    session = runtime().start("two_hole_mounting_bracket")
    for stage in ("new_design", "verify_clean_state", "create_sketch", "draw_l_bracket_profile"):
        session.record(stage)
    session.record("draw_circle")  # first circle — index 4
    session.record("draw_circle")  # second circle — index 5
    assert session.completed_stages.count("draw_circle") == 2


def test_two_hole_mounting_bracket_skipping_first_circle_raises() -> None:
    session = runtime().start("two_hole_mounting_bracket")
    for stage in ("new_design", "verify_clean_state", "create_sketch", "draw_l_bracket_profile"):
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("list_profiles")


def test_two_hole_mounting_bracket_out_of_order_raises() -> None:
    session = runtime().start("two_hole_mounting_bracket")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("create_sketch")


def test_two_hole_mounting_bracket_unknown_stage_raises() -> None:
    session = runtime().start("two_hole_mounting_bracket")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("draw_spline")


# ---------------------------------------------------------------------------
# two_hole_plate
# ---------------------------------------------------------------------------

TWO_HOLE_PLATE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "draw_circle",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_two_hole_plate_full_sequence_records_successfully() -> None:
    session = runtime().start("two_hole_plate")
    for stage in TWO_HOLE_PLATE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(TWO_HOLE_PLATE_STAGES)


def test_two_hole_plate_both_circles_recorded_in_order() -> None:
    session = runtime().start("two_hole_plate")
    for stage in ("new_design", "verify_clean_state", "create_sketch", "draw_rectangle"):
        session.record(stage)
    session.record("draw_circle")
    session.record("draw_circle")
    assert session.completed_stages.count("draw_circle") == 2


def test_two_hole_plate_skipping_second_circle_raises() -> None:
    session = runtime().start("two_hole_plate")
    for stage in ("new_design", "verify_clean_state", "create_sketch", "draw_rectangle", "draw_circle"):
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("list_profiles")


def test_two_hole_plate_unknown_stage_raises() -> None:
    session = runtime().start("two_hole_plate")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("apply_fillet")


# ---------------------------------------------------------------------------
# slotted_mount
# ---------------------------------------------------------------------------

SLOTTED_MOUNT_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "draw_slot",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_slotted_mount_full_sequence_records_successfully() -> None:
    session = runtime().start("slotted_mount")
    for stage in SLOTTED_MOUNT_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(SLOTTED_MOUNT_STAGES)


def test_slotted_mount_out_of_order_raises() -> None:
    session = runtime().start("slotted_mount")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("draw_slot")


def test_slotted_mount_unknown_stage_raises() -> None:
    session = runtime().start("slotted_mount")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("draw_circle")


# ---------------------------------------------------------------------------
# simple_enclosure
# ---------------------------------------------------------------------------

SIMPLE_ENCLOSURE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
)


def test_simple_enclosure_full_sequence_records_successfully() -> None:
    session = runtime().start("simple_enclosure")
    for stage in SIMPLE_ENCLOSURE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(SIMPLE_ENCLOSURE_STAGES)


def test_simple_enclosure_out_of_order_raises() -> None:
    session = runtime().start("simple_enclosure")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("extrude_profile")


def test_simple_enclosure_unknown_stage_raises() -> None:
    session = runtime().start("simple_enclosure")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("export_stl")


def test_simple_enclosure_duplicate_stage_raises() -> None:
    session = runtime().start("simple_enclosure")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("new_design")


# ---------------------------------------------------------------------------
# Cross-workflow: unknown workflow name raises
# ---------------------------------------------------------------------------

def test_unknown_workflow_name_raises() -> None:
    rt = runtime()
    with pytest.raises(KeyError):
        rt.start("nonexistent_workflow")
