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
# filleted_bracket
# ---------------------------------------------------------------------------

FILLETED_BRACKET_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_l_bracket_profile",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "apply_fillet",
    "verify_geometry",
    "export_stl",
)


def test_filleted_bracket_full_sequence_records_successfully() -> None:
    session = runtime().start("filleted_bracket")
    for stage in FILLETED_BRACKET_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(FILLETED_BRACKET_STAGES)


def test_filleted_bracket_requires_apply_fillet_after_first_verify() -> None:
    session = runtime().start("filleted_bracket")
    session.record("new_design")
    session.record("verify_clean_state")
    session.record("create_sketch")
    session.record("draw_l_bracket_profile")
    session.record("list_profiles")
    session.record("extrude_profile")
    session.record("verify_geometry")
    with pytest.raises(ValueError, match="out of order"):
        session.record("export_stl")


def test_filleted_bracket_unknown_stage_raises() -> None:
    session = runtime().start("filleted_bracket")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("draw_circle")


# ---------------------------------------------------------------------------
# chamfered_bracket
# ---------------------------------------------------------------------------

CHAMFERED_BRACKET_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_l_bracket_profile",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "apply_chamfer",
    "verify_geometry",
    "export_stl",
)


def test_chamfered_bracket_full_sequence_records_successfully() -> None:
    session = runtime().start("chamfered_bracket")
    for stage in CHAMFERED_BRACKET_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(CHAMFERED_BRACKET_STAGES)


def test_chamfered_bracket_requires_apply_chamfer_after_first_verify() -> None:
    session = runtime().start("chamfered_bracket")
    session.record("new_design")
    session.record("verify_clean_state")
    session.record("create_sketch")
    session.record("draw_l_bracket_profile")
    session.record("list_profiles")
    session.record("extrude_profile")
    session.record("verify_geometry")
    with pytest.raises(ValueError, match="out of order"):
        session.record("export_stl")


def test_chamfered_bracket_unknown_stage_raises() -> None:
    session = runtime().start("chamfered_bracket")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("draw_circle")


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


# ---------------------------------------------------------------------------
# four_hole_mounting_plate
# ---------------------------------------------------------------------------

FOUR_HOLE_MOUNTING_PLATE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "draw_circle",
    "draw_circle",
    "draw_circle",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_four_hole_mounting_plate_full_sequence_records_successfully() -> None:
    session = runtime().start("four_hole_mounting_plate")
    for stage in FOUR_HOLE_MOUNTING_PLATE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(FOUR_HOLE_MOUNTING_PLATE_STAGES)


def test_four_hole_mounting_plate_all_circles_recorded_in_order() -> None:
    session = runtime().start("four_hole_mounting_plate")
    for stage in ("new_design", "verify_clean_state", "create_sketch", "draw_rectangle"):
        session.record(stage)
    for _ in range(4):
        session.record("draw_circle")
    assert session.completed_stages.count("draw_circle") == 4


def test_four_hole_mounting_plate_skipping_fourth_circle_raises() -> None:
    session = runtime().start("four_hole_mounting_plate")
    for stage in (
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
    ):
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("list_profiles")


# ---------------------------------------------------------------------------
# slotted_mounting_plate
# ---------------------------------------------------------------------------

SLOTTED_MOUNTING_PLATE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "draw_circle",
    "draw_circle",
    "draw_circle",
    "draw_circle",
    "draw_slot",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_slotted_mounting_plate_full_sequence_records_successfully() -> None:
    session = runtime().start("slotted_mounting_plate")
    for stage in SLOTTED_MOUNTING_PLATE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(SLOTTED_MOUNTING_PLATE_STAGES)


def test_slotted_mounting_plate_requires_slot_after_four_circles() -> None:
    session = runtime().start("slotted_mounting_plate")
    for stage in (
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
    ):
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("list_profiles")


def test_slotted_mounting_plate_unknown_stage_raises() -> None:
    session = runtime().start("slotted_mounting_plate")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("apply_fillet")


# ---------------------------------------------------------------------------
# counterbored_plate
# ---------------------------------------------------------------------------

COUNTERBORED_PLATE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_counterbored_plate_full_sequence_records_successfully() -> None:
    session = runtime().start("counterbored_plate")
    for stage in COUNTERBORED_PLATE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(COUNTERBORED_PLATE_STAGES)


def test_counterbored_plate_accepts_both_circle_stages_in_order() -> None:
    session = runtime().start("counterbored_plate")
    for stage in COUNTERBORED_PLATE_STAGES[:9]:
        session.record(stage)
    for stage in COUNTERBORED_PLATE_STAGES[9:14]:
        session.record(stage)
    assert session.completed_stages.count("draw_circle") == 2


def test_counterbored_plate_skipping_second_cut_verification_raises() -> None:
    session = runtime().start("counterbored_plate")
    for stage in COUNTERBORED_PLATE_STAGES[:16]:
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("export_stl")


# ---------------------------------------------------------------------------
# recessed_mount
# ---------------------------------------------------------------------------

RECESSED_MOUNT_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_rectangle_at",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_recessed_mount_full_sequence_records_successfully() -> None:
    session = runtime().start("recessed_mount")
    for stage in RECESSED_MOUNT_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(RECESSED_MOUNT_STAGES)


def test_recessed_mount_requires_draw_rectangle_at_before_second_list_profiles() -> None:
    session = runtime().start("recessed_mount")
    for stage in RECESSED_MOUNT_STAGES[:8]:
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
# cylinder
# ---------------------------------------------------------------------------

CYLINDER_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_cylinder_full_sequence_records_successfully() -> None:
    session = runtime().start("cylinder")
    for stage in CYLINDER_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(CYLINDER_STAGES)


def test_cylinder_out_of_order_raises() -> None:
    session = runtime().start("cylinder")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("extrude_profile")


def test_cylinder_unknown_stage_raises() -> None:
    session = runtime().start("cylinder")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("apply_shell")


# ---------------------------------------------------------------------------
# tube
# ---------------------------------------------------------------------------

TUBE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_tube_full_sequence_records_successfully() -> None:
    session = runtime().start("tube")
    for stage in TUBE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(TUBE_STAGES)


def test_tube_requires_bore_cut_after_outer_body() -> None:
    session = runtime().start("tube")
    for stage in TUBE_STAGES[:7]:
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("export_stl")


def test_tube_unknown_stage_raises() -> None:
    session = runtime().start("tube")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("apply_shell")


# ---------------------------------------------------------------------------
# revolve
# ---------------------------------------------------------------------------

REVOLVE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_revolve_profile",
    "list_profiles",
    "revolve_profile",
    "verify_geometry",
    "export_stl",
)


def test_revolve_full_sequence_records_successfully() -> None:
    session = runtime().start("revolve")
    for stage in REVOLVE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(REVOLVE_STAGES)


def test_revolve_out_of_order_raises() -> None:
    session = runtime().start("revolve")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("revolve_profile")


def test_revolve_unknown_stage_raises() -> None:
    session = runtime().start("revolve")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("draw_circle")


# ---------------------------------------------------------------------------
# tapered_knob_blank
# ---------------------------------------------------------------------------

TAPERED_KNOB_BLANK_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_revolve_profile",
    "list_profiles",
    "revolve_profile",
    "verify_geometry",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_tapered_knob_blank_full_sequence_records_successfully() -> None:
    session = runtime().start("tapered_knob_blank")
    for stage in TAPERED_KNOB_BLANK_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(TAPERED_KNOB_BLANK_STAGES)


def test_tapered_knob_blank_requires_socket_cut_before_export() -> None:
    session = runtime().start("tapered_knob_blank")
    for stage in TAPERED_KNOB_BLANK_STAGES[:7]:
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("export_stl")


def test_tapered_knob_blank_unknown_stage_raises() -> None:
    session = runtime().start("tapered_knob_blank")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("apply_shell")


# ---------------------------------------------------------------------------
# t_handle_with_square_socket
# ---------------------------------------------------------------------------

T_HANDLE_WITH_SQUARE_SOCKET_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle_at",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_rectangle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "combine_bodies",
    "verify_geometry",
    "create_sketch",
    "draw_rectangle_at",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "apply_chamfer",
    "verify_geometry",
    "export_stl",
)


def test_t_handle_with_square_socket_full_sequence_records_successfully() -> None:
    session = runtime().start("t_handle_with_square_socket")
    for stage in T_HANDLE_WITH_SQUARE_SOCKET_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(T_HANDLE_WITH_SQUARE_SOCKET_STAGES)


def test_t_handle_with_square_socket_requires_combine_before_socket_cut() -> None:
    session = runtime().start("t_handle_with_square_socket")
    for stage in T_HANDLE_WITH_SQUARE_SOCKET_STAGES[:14]:
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("extrude_profile")


def test_t_handle_with_square_socket_unknown_stage_raises() -> None:
    session = runtime().start("t_handle_with_square_socket")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("draw_circle")


# ---------------------------------------------------------------------------
# tube_mounting_plate
# ---------------------------------------------------------------------------

TUBE_MOUNTING_PLATE_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "combine_bodies",
    "verify_geometry",
    "create_sketch",
    "draw_circle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
)


def test_tube_mounting_plate_full_sequence_records_successfully() -> None:
    session = runtime().start("tube_mounting_plate")
    for stage in TUBE_MOUNTING_PLATE_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(TUBE_MOUNTING_PLATE_STAGES)


def test_tube_mounting_plate_requires_combine_before_final_cut_verify() -> None:
    session = runtime().start("tube_mounting_plate")
    for stage in TUBE_MOUNTING_PLATE_STAGES[:22]:
        session.record(stage)
    with pytest.raises(ValueError, match="out of order"):
        session.record("verify_geometry")


def test_tube_mounting_plate_unknown_stage_raises() -> None:
    session = runtime().start("tube_mounting_plate")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("apply_shell")


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
    "apply_shell",
    "verify_geometry",
    "export_stl",
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
        session.record("apply_fillet")


def test_simple_enclosure_duplicate_stage_raises() -> None:
    session = runtime().start("simple_enclosure")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("new_design")


# ---------------------------------------------------------------------------
# box_with_lid
# ---------------------------------------------------------------------------

BOX_WITH_LID_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_rectangle",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_rectangle_at",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_rectangle_at",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "create_sketch",
    "draw_rectangle_at",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "export_stl",
    "export_stl",
)


def test_box_with_lid_full_sequence_records_successfully() -> None:
    session = runtime().start("box_with_lid")
    for stage in BOX_WITH_LID_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(BOX_WITH_LID_STAGES)


def test_box_with_lid_requires_box_base_before_cavity() -> None:
    session = runtime().start("box_with_lid")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("draw_rectangle_at")


def test_box_with_lid_unknown_stage_raises() -> None:
    session = runtime().start("box_with_lid")
    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("apply_fillet")


# ---------------------------------------------------------------------------
# Cross-workflow: unknown workflow name raises
# ---------------------------------------------------------------------------

def test_unknown_workflow_name_raises() -> None:
    rt = runtime()
    with pytest.raises(KeyError):
        rt.start("nonexistent_workflow")
