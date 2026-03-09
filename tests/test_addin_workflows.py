from __future__ import annotations

from pathlib import Path

import pytest

from fusion_addin.ops.live_ops import FusionExecutionContext, RecordingFakeFusionAdapter, build_registry
from fusion_addin.state import DesignState
from fusion_addin.workflows import WorkflowRuntime


def test_workflow_runtime_uses_shared_registry() -> None:
    runtime = WorkflowRuntime()
    session = runtime.start("spacer")

    assert session.workflow_name == "spacer"
    assert session.allowed_stages[0] == "new_design"
    assert "verify_geometry" in session.allowed_stages


def test_workflow_runtime_rejects_unknown_stage() -> None:
    runtime = WorkflowRuntime()
    session = runtime.start("spacer")

    with pytest.raises(ValueError, match="not part of workflow"):
        session.record("create_thread")


def test_workflow_runtime_enforces_order() -> None:
    runtime = WorkflowRuntime()
    session = runtime.start("spacer")

    with pytest.raises(ValueError, match="out of order"):
        session.record("create_sketch")


def test_live_registry_runs_spacer_stage_sequence() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()
    output_path = Path.cwd() / "manual_test_output" / "workflow_spacer_test.stl"

    registry.execute(state, "new_design", {"name": "Spacer Workflow", "workflow_name": "spacer"})
    registry.execute(state, "get_scene_info", {"workflow_name": "spacer", "workflow_stage": "verify_clean_state"})
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Spacer Sketch", "workflow_name": "spacer"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": sketch_token,
            "width_cm": 2.0,
            "height_cm": 1.0,
            "workflow_name": "spacer",
        },
    )
    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "spacer"},
    )["profiles"]
    body = registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 0.5,
            "body_name": "Spacer",
            "workflow_name": "spacer",
        },
    )["body"]
    scene = registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "spacer", "workflow_stage": "verify_geometry"},
    )
    exported = registry.execute(
        state,
        "export_stl",
        {
            "body_token": body["token"],
            "output_path": str(output_path),
            "workflow_name": "spacer",
        },
    )

    assert scene["bodies"][0]["name"] == "Spacer"
    assert exported["output_path"].endswith("workflow_spacer_test.stl")
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "export_stl",
    ]


def test_live_registry_restarts_workflow_session_on_new_design() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "First Workflow", "workflow_name": "spacer"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "spacer", "workflow_stage": "verify_clean_state"},
    )
    registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "First Sketch", "workflow_name": "spacer"},
    )

    restarted = registry.execute(state, "new_design", {"name": "Second Workflow", "workflow_name": "spacer"})

    assert restarted["design_name"] == "Second Workflow"


class CollapsedNonXyProfileAdapter(RecordingFakeFusionAdapter):
    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:
        return super().create_sketch("xz", name, offset_cm)

    def list_profiles(self, sketch_token: str) -> list[dict]:
        profiles = super().list_profiles(sketch_token)
        profiles[0]["height_cm"] = 0.0
        return profiles


def test_live_registry_repairs_collapsed_non_xy_profile_dimensions() -> None:
    adapter = CollapsedNonXyProfileAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "XZ Workflow", "workflow_name": "spacer"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "spacer", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xz", "name": "XZ Sketch", "workflow_name": "spacer"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": sketch_token,
            "width_cm": 2.0,
            "height_cm": 1.0,
            "workflow_name": "spacer",
        },
    )

    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "spacer"},
    )["profiles"]

    assert profiles[0]["width_cm"] == 2.0
    assert profiles[0]["height_cm"] == 1.0


def test_live_registry_runs_bracket_l_profile_stage_sequence() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()
    output_path = Path.cwd() / "manual_test_output" / "workflow_bracket_test.stl"

    registry.execute(state, "new_design", {"name": "Bracket Workflow", "workflow_name": "bracket"})
    registry.execute(state, "get_scene_info", {"workflow_name": "bracket", "workflow_stage": "verify_clean_state"})
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xz", "name": "Bracket Sketch", "workflow_name": "bracket"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_l_bracket_profile",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 2.0,
            "leg_thickness_cm": 0.5,
            "workflow_name": "bracket",
        },
    )
    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "bracket"},
    )["profiles"]
    body = registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 0.75,
            "body_name": "Bracket",
            "workflow_name": "bracket",
        },
    )["body"]
    scene = registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "bracket", "workflow_stage": "verify_geometry"},
    )
    exported = registry.execute(
        state,
        "export_stl",
        {
            "body_token": body["token"],
            "output_path": str(output_path),
            "workflow_name": "bracket",
        },
    )

    assert scene["bodies"][0]["name"] == "Bracket"
    assert exported["output_path"].endswith("workflow_bracket_test.stl")
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_l_bracket_profile",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "export_stl",
    ]


def test_live_registry_supports_circle_stage_for_mounting_bracket() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Mounting Bracket Workflow", "workflow_name": "mounting_bracket"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "mounting_bracket", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Mounting Bracket Sketch", "workflow_name": "mounting_bracket"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_l_bracket_profile",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 2.0,
            "leg_thickness_cm": 0.5,
            "workflow_name": "mounting_bracket",
        },
    )
    registry.execute(
        state,
        "draw_circle",
        {
            "sketch_token": sketch_token,
            "center_x_cm": 0.25,
            "center_y_cm": 1.5,
            "radius_cm": 0.2,
            "workflow_name": "mounting_bracket",
        },
    )

    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "mounting_bracket"},
    )["profiles"]

    assert len(profiles) == 2
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_l_bracket_profile",
        "draw_circle",
        "list_profiles",
    ]


def test_live_registry_supports_two_circle_stages_for_two_hole_mounting_bracket() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Two-Hole Mounting Bracket Workflow", "workflow_name": "two_hole_mounting_bracket"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "two_hole_mounting_bracket", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Two-Hole Mounting Bracket Sketch", "workflow_name": "two_hole_mounting_bracket"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_l_bracket_profile",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 2.0,
            "leg_thickness_cm": 0.5,
            "workflow_name": "two_hole_mounting_bracket",
        },
    )
    registry.execute(
        state,
        "draw_circle",
        {
            "sketch_token": sketch_token,
            "center_x_cm": 0.25,
            "center_y_cm": 1.5,
            "radius_cm": 0.2,
            "workflow_name": "two_hole_mounting_bracket",
        },
    )
    registry.execute(
        state,
        "draw_circle",
        {
            "sketch_token": sketch_token,
            "center_x_cm": 1.5,
            "center_y_cm": 0.25,
            "radius_cm": 0.2,
            "workflow_name": "two_hole_mounting_bracket",
        },
    )

    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "two_hole_mounting_bracket"},
    )["profiles"]

    assert len(profiles) == 3
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_l_bracket_profile",
        "draw_circle",
        "draw_circle",
        "list_profiles",
    ]


def test_live_registry_supports_two_circle_stages_for_two_hole_plate() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Two-Hole Plate Workflow", "workflow_name": "two_hole_plate"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "two_hole_plate", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Two-Hole Plate Sketch", "workflow_name": "two_hole_plate"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 2.0,
            "workflow_name": "two_hole_plate",
        },
    )
    registry.execute(
        state,
        "draw_circle",
        {
            "sketch_token": sketch_token,
            "center_x_cm": 0.75,
            "center_y_cm": 1.0,
            "radius_cm": 0.2,
            "workflow_name": "two_hole_plate",
        },
    )
    registry.execute(
        state,
        "draw_circle",
        {
            "sketch_token": sketch_token,
            "center_x_cm": 3.25,
            "center_y_cm": 1.0,
            "radius_cm": 0.2,
            "workflow_name": "two_hole_plate",
        },
    )

    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "two_hole_plate"},
    )["profiles"]

    assert len(profiles) == 3
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "draw_circle",
        "draw_circle",
        "list_profiles",
    ]


def test_live_registry_supports_four_circle_stages_for_four_hole_mounting_plate() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Four-Hole Mounting Plate Workflow", "workflow_name": "four_hole_mounting_plate"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "four_hole_mounting_plate", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Four-Hole Mounting Plate Sketch", "workflow_name": "four_hole_mounting_plate"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 3.0,
            "workflow_name": "four_hole_mounting_plate",
        },
    )
    for center_x_cm, center_y_cm in ((0.6, 0.7), (3.4, 0.7), (0.6, 2.3), (3.4, 2.3)):
        registry.execute(
            state,
            "draw_circle",
            {
                "sketch_token": sketch_token,
                "center_x_cm": center_x_cm,
                "center_y_cm": center_y_cm,
                "radius_cm": 0.2,
                "workflow_name": "four_hole_mounting_plate",
            },
        )

    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "four_hole_mounting_plate"},
    )["profiles"]

    assert len(profiles) == 5
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "list_profiles",
    ]


def test_live_registry_supports_four_circle_plus_slot_stages_for_slotted_mounting_plate() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Slotted Mounting Plate Workflow", "workflow_name": "slotted_mounting_plate"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "slotted_mounting_plate", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Slotted Mounting Plate Sketch", "workflow_name": "slotted_mounting_plate"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 3.0,
            "workflow_name": "slotted_mounting_plate",
        },
    )
    for center_x_cm, center_y_cm in ((0.6, 0.7), (3.4, 0.7), (0.6, 2.3), (3.4, 2.3)):
        registry.execute(
            state,
            "draw_circle",
            {
                "sketch_token": sketch_token,
                "center_x_cm": center_x_cm,
                "center_y_cm": center_y_cm,
                "radius_cm": 0.2,
                "workflow_name": "slotted_mounting_plate",
            },
        )
    registry.execute(
        state,
        "draw_slot",
        {
            "sketch_token": sketch_token,
            "center_x_cm": 2.0,
            "center_y_cm": 1.5,
            "length_cm": 1.5,
            "width_cm": 0.5,
            "workflow_name": "slotted_mounting_plate",
        },
    )

    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "slotted_mounting_plate"},
    )["profiles"]

    assert len(profiles) == 6
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "draw_slot",
        "list_profiles",
    ]


def test_live_registry_supports_slot_stage_for_slotted_mount() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Slotted Mount Workflow", "workflow_name": "slotted_mount"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "slotted_mount", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Slotted Mount Sketch", "workflow_name": "slotted_mount"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 2.0,
            "workflow_name": "slotted_mount",
        },
    )
    registry.execute(
        state,
        "draw_slot",
        {
            "sketch_token": sketch_token,
            "center_x_cm": 2.0,
            "center_y_cm": 1.0,
            "length_cm": 1.5,
            "width_cm": 0.5,
            "workflow_name": "slotted_mount",
        },
    )

    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "slotted_mount"},
    )["profiles"]

    assert len(profiles) == 2
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "draw_slot",
        "list_profiles",
    ]


def test_live_registry_supports_offset_rectangle_stage_for_recessed_mount() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Recessed Mount Workflow", "workflow_name": "recessed_mount"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "recessed_mount", "workflow_stage": "verify_clean_state"},
    )
    base_sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Recessed Mount Sketch", "workflow_name": "recessed_mount"},
    )
    base_sketch_token = base_sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": base_sketch_token,
            "width_cm": 4.0,
            "height_cm": 2.5,
            "workflow_name": "recessed_mount",
        },
    )
    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": base_sketch_token, "workflow_name": "recessed_mount"},
    )["profiles"]
    body = registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 0.5,
            "body_name": "Recessed Mount",
            "workflow_name": "recessed_mount",
        },
    )["body"]
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "recessed_mount", "workflow_stage": "verify_geometry"},
    )
    recess_sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Recess Sketch", "workflow_name": "recessed_mount"},
    )
    recess_sketch_token = recess_sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle_at",
        {
            "sketch_token": recess_sketch_token,
            "origin_x_cm": 1.0,
            "origin_y_cm": 0.75,
            "width_cm": 2.0,
            "height_cm": 1.0,
            "workflow_name": "recessed_mount",
        },
    )

    recess_profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": recess_sketch_token, "workflow_name": "recessed_mount"},
    )["profiles"]

    assert body["name"] == "Recessed Mount"
    assert len(recess_profiles) == 1
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle_at",
        "list_profiles",
    ]


def test_live_registry_supports_offset_plane_cavity_stage_for_open_box_body() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Open Box Body Workflow", "workflow_name": "open_box_body"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "open_box_body", "workflow_stage": "verify_clean_state"},
    )
    base_sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Open Box Body Sketch", "workflow_name": "open_box_body"},
    )
    base_sketch_token = base_sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": base_sketch_token,
            "width_cm": 4.0,
            "height_cm": 3.0,
            "workflow_name": "open_box_body",
        },
    )
    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": base_sketch_token, "workflow_name": "open_box_body"},
    )["profiles"]
    registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 2.0,
            "body_name": "Open Box Body",
            "workflow_name": "open_box_body",
        },
    )
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "open_box_body", "workflow_stage": "verify_geometry"},
    )
    cavity_sketch = registry.execute(
        state,
        "create_sketch",
        {
            "plane": "xy",
            "name": "Cavity Sketch",
            "offset_cm": 0.4,
            "workflow_name": "open_box_body",
        },
    )
    cavity_sketch_token = cavity_sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle_at",
        {
            "sketch_token": cavity_sketch_token,
            "origin_x_cm": 0.3,
            "origin_y_cm": 0.3,
            "width_cm": 3.4,
            "height_cm": 2.4,
            "workflow_name": "open_box_body",
        },
    )

    cavity_profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": cavity_sketch_token, "workflow_name": "open_box_body"},
    )["profiles"]

    assert len(cavity_profiles) == 1
    assert cavity_sketch["sketch"]["offset_cm"] == 0.4
    assert adapter.calls[7] == ("create_sketch", {"plane": "xy", "name": "Cavity Sketch", "offset_cm": 0.4})


def test_live_registry_supports_apply_shell_stage_for_simple_enclosure() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Simple Enclosure Workflow", "workflow_name": "simple_enclosure"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "simple_enclosure", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Simple Enclosure Sketch", "workflow_name": "simple_enclosure"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 3.0,
            "workflow_name": "simple_enclosure",
        },
    )
    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "simple_enclosure"},
    )["profiles"]
    body = registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 2.0,
            "body_name": "Simple Enclosure",
            "workflow_name": "simple_enclosure",
        },
    )["body"]
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "simple_enclosure", "workflow_stage": "verify_geometry"},
    )

    shell = registry.execute(
        state,
        "apply_shell",
        {
            "body_token": body["token"],
            "wall_thickness_cm": 0.3,
            "workflow_name": "simple_enclosure",
        },
    )["shell"]
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "simple_enclosure", "workflow_stage": "verify_geometry"},
    )

    assert shell["body_token"] == body["token"]
    assert shell["shell_applied"] is True
    assert shell["inner_width_cm"] == pytest.approx(3.4)
    assert shell["inner_depth_cm"] == pytest.approx(2.4)
    assert shell["inner_height_cm"] == pytest.approx(1.7)
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "apply_shell",
        "get_scene_info",
    ]


def test_live_registry_runs_cylinder_stage_sequence() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()
    output_path = Path.cwd() / "manual_test_output" / "workflow_cylinder_test.stl"

    registry.execute(state, "new_design", {"name": "Cylinder Workflow", "workflow_name": "cylinder"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "cylinder", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Cylinder Sketch", "workflow_name": "cylinder"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_circle",
        {
            "sketch_token": sketch_token,
            "center_x_cm": 1.0,
            "center_y_cm": 1.0,
            "radius_cm": 1.0,
            "workflow_name": "cylinder",
        },
    )
    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "cylinder"},
    )["profiles"]
    body = registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 3.0,
            "body_name": "Cylinder",
            "workflow_name": "cylinder",
        },
    )["body"]
    scene = registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "cylinder", "workflow_stage": "verify_geometry"},
    )
    exported = registry.execute(
        state,
        "export_stl",
        {
            "body_token": body["token"],
            "output_path": str(output_path),
            "workflow_name": "cylinder",
        },
    )

    assert scene["bodies"][0]["width_cm"] == 2.0
    assert scene["bodies"][0]["height_cm"] == 2.0
    assert scene["bodies"][0]["thickness_cm"] == 3.0
    assert exported["output_path"].endswith("workflow_cylinder_test.stl")
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "export_stl",
    ]


def test_live_registry_runs_tube_mounting_plate_join_sequence() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()
    output_path = Path.cwd() / "manual_test_output" / "workflow_tube_mounting_plate_test.stl"

    registry.execute(state, "new_design", {"name": "Tube Mounting Plate Workflow", "workflow_name": "tube_mounting_plate"})
    registry.execute(state, "get_scene_info", {"workflow_name": "tube_mounting_plate", "workflow_stage": "verify_clean_state"})
    base_sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Tube Mounting Plate Sketch", "workflow_name": "tube_mounting_plate"},
    )
    base_sketch_token = base_sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {"sketch_token": base_sketch_token, "width_cm": 6.0, "height_cm": 10.0, "workflow_name": "tube_mounting_plate"},
    )
    base_profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": base_sketch_token, "workflow_name": "tube_mounting_plate"},
    )["profiles"]
    base_body = registry.execute(
        state,
        "extrude_profile",
        {"profile_token": base_profiles[0]["token"], "distance_cm": 0.5, "body_name": "Tube Mounting Plate", "workflow_name": "tube_mounting_plate"},
    )["body"]
    registry.execute(state, "get_scene_info", {"workflow_name": "tube_mounting_plate", "workflow_stage": "verify_geometry"})

    for hole_name, hole_y in (("Upper Hole Sketch", 1.5), ("Lower Hole Sketch", 8.5)):
        hole_sketch = registry.execute(
            state,
            "create_sketch",
            {"plane": "xy", "name": hole_name, "workflow_name": "tube_mounting_plate"},
        )
        hole_sketch_token = hole_sketch["sketch"]["token"]
        registry.execute(
            state,
            "draw_circle",
            {"sketch_token": hole_sketch_token, "center_x_cm": 3.0, "center_y_cm": hole_y, "radius_cm": 0.25, "workflow_name": "tube_mounting_plate"},
        )
        hole_profiles = registry.execute(
            state,
            "list_profiles",
            {"sketch_token": hole_sketch_token, "workflow_name": "tube_mounting_plate"},
        )["profiles"]
        registry.execute(
            state,
            "extrude_profile",
            {
                "profile_token": hole_profiles[0]["token"],
                "distance_cm": 0.5,
                "body_name": "hole",
                "operation": "cut",
                "target_body_token": base_body["token"],
                "workflow_name": "tube_mounting_plate",
            },
        )
        registry.execute(state, "get_scene_info", {"workflow_name": "tube_mounting_plate", "workflow_stage": "verify_geometry"})

    tube_sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Tube Outer Sketch", "offset_cm": 0.5, "workflow_name": "tube_mounting_plate"},
    )
    tube_sketch_token = tube_sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_circle",
        {"sketch_token": tube_sketch_token, "center_x_cm": 3.0, "center_y_cm": 5.0, "radius_cm": 1.0, "workflow_name": "tube_mounting_plate"},
    )
    tube_profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": tube_sketch_token, "workflow_name": "tube_mounting_plate"},
    )["profiles"]
    tube_body = registry.execute(
        state,
        "extrude_profile",
        {"profile_token": tube_profiles[0]["token"], "distance_cm": 3.0, "body_name": "Tube Sleeve", "workflow_name": "tube_mounting_plate"},
    )["body"]
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "tube_mounting_plate", "workflow_stage": "verify_geometry"},
    )
    combined_body = registry.execute(
        state,
        "combine_bodies",
        {"target_body_token": base_body["token"], "tool_body_token": tube_body["token"], "workflow_name": "tube_mounting_plate"},
    )["body"]
    registry.execute(state, "get_scene_info", {"workflow_name": "tube_mounting_plate", "workflow_stage": "verify_geometry"})

    bore_sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Tube Bore Sketch", "offset_cm": 0.5, "workflow_name": "tube_mounting_plate"},
    )
    bore_sketch_token = bore_sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_circle",
        {"sketch_token": bore_sketch_token, "center_x_cm": 3.0, "center_y_cm": 5.0, "radius_cm": 0.6, "workflow_name": "tube_mounting_plate"},
    )
    bore_profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": bore_sketch_token, "workflow_name": "tube_mounting_plate"},
    )["profiles"]
    registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": bore_profiles[0]["token"],
            "distance_cm": 3.0,
            "body_name": "bore",
            "operation": "cut",
            "target_body_token": combined_body["token"],
            "workflow_name": "tube_mounting_plate",
        },
    )
    scene = registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "tube_mounting_plate", "workflow_stage": "verify_geometry"},
    )
    exported = registry.execute(
        state,
        "export_stl",
        {"body_token": combined_body["token"], "output_path": str(output_path), "workflow_name": "tube_mounting_plate"},
    )

    assert scene["bodies"][0]["width_cm"] == 6.0
    assert scene["bodies"][0]["height_cm"] == 10.0
    assert scene["bodies"][0]["thickness_cm"] == 3.5
    assert exported["output_path"].endswith("workflow_tube_mounting_plate_test.stl")
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "combine_bodies",
        "get_scene_info",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "export_stl",
    ]


def test_live_registry_supports_rim_cut_stage_for_lid_for_box() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Lid For Box Workflow", "workflow_name": "lid_for_box"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "lid_for_box", "workflow_stage": "verify_clean_state"},
    )
    lid_sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Lid Sketch", "workflow_name": "lid_for_box"},
    )
    lid_sketch_token = lid_sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {
            "sketch_token": lid_sketch_token,
            "width_cm": 4.0,
            "height_cm": 3.0,
            "workflow_name": "lid_for_box",
        },
    )
    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": lid_sketch_token, "workflow_name": "lid_for_box"},
    )["profiles"]
    registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 0.6,
            "body_name": "Box Lid",
            "workflow_name": "lid_for_box",
        },
    )
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "lid_for_box", "workflow_stage": "verify_geometry"},
    )
    rim_cut_sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Rim Cut Sketch", "workflow_name": "lid_for_box"},
    )
    rim_cut_sketch_token = rim_cut_sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle_at",
        {
            "sketch_token": rim_cut_sketch_token,
            "origin_x_cm": 0.3,
            "origin_y_cm": 0.3,
            "width_cm": 3.4,
            "height_cm": 2.4,
            "workflow_name": "lid_for_box",
        },
    )

    rim_cut_profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": rim_cut_sketch_token, "workflow_name": "lid_for_box"},
    )["profiles"]

    assert len(rim_cut_profiles) == 1
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle_at",
        "list_profiles",
    ]


def test_live_registry_supports_apply_fillet_stage_for_filleted_bracket() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Filleted Bracket Workflow", "workflow_name": "filleted_bracket"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "filleted_bracket", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Filleted Bracket Sketch", "workflow_name": "filleted_bracket"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_l_bracket_profile",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 2.0,
            "leg_thickness_cm": 0.5,
            "workflow_name": "filleted_bracket",
        },
    )
    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "filleted_bracket"},
    )["profiles"]
    body = registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 0.75,
            "body_name": "Filleted Bracket",
            "workflow_name": "filleted_bracket",
        },
    )["body"]
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "filleted_bracket", "workflow_stage": "verify_geometry"},
    )

    fillet = registry.execute(
        state,
        "apply_fillet",
        {
            "body_token": body["token"],
            "radius_cm": 0.2,
            "workflow_name": "filleted_bracket",
        },
    )["fillet"]

    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "filleted_bracket", "workflow_stage": "verify_geometry"},
    )

    assert fillet["body_token"] == body["token"]
    assert fillet["fillet_applied"] is True
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_l_bracket_profile",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "apply_fillet",
        "get_scene_info",
    ]


def test_live_registry_supports_apply_chamfer_stage_for_chamfered_bracket() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Chamfered Bracket Workflow", "workflow_name": "chamfered_bracket"})
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "chamfered_bracket", "workflow_stage": "verify_clean_state"},
    )
    sketch = registry.execute(
        state,
        "create_sketch",
        {"plane": "xy", "name": "Chamfered Bracket Sketch", "workflow_name": "chamfered_bracket"},
    )
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_l_bracket_profile",
        {
            "sketch_token": sketch_token,
            "width_cm": 4.0,
            "height_cm": 2.0,
            "leg_thickness_cm": 0.5,
            "workflow_name": "chamfered_bracket",
        },
    )
    profiles = registry.execute(
        state,
        "list_profiles",
        {"sketch_token": sketch_token, "workflow_name": "chamfered_bracket"},
    )["profiles"]
    body = registry.execute(
        state,
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 0.75,
            "body_name": "Chamfered Bracket",
            "workflow_name": "chamfered_bracket",
        },
    )["body"]
    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "chamfered_bracket", "workflow_stage": "verify_geometry"},
    )

    chamfer = registry.execute(
        state,
        "apply_chamfer",
        {
            "body_token": body["token"],
            "distance_cm": 0.2,
            "workflow_name": "chamfered_bracket",
        },
    )["chamfer"]

    registry.execute(
        state,
        "get_scene_info",
        {"workflow_name": "chamfered_bracket", "workflow_stage": "verify_geometry"},
    )

    assert chamfer["body_token"] == body["token"]
    assert chamfer["chamfer_applied"] is True
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_l_bracket_profile",
        "list_profiles",
        "extrude_profile",
        "get_scene_info",
        "apply_chamfer",
        "get_scene_info",
    ]


def test_live_registry_supports_get_body_faces_inspection() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Body Faces Inspection"})
    sketch = registry.execute(state, "create_sketch", {"plane": "xy", "name": "Inspection Sketch"})
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {"sketch_token": sketch_token, "width_cm": 3.0, "height_cm": 2.0},
    )
    profile_token = registry.execute(state, "list_profiles", {"sketch_token": sketch_token})["profiles"][0]["token"]
    body = registry.execute(
        state,
        "extrude_profile",
        {"profile_token": profile_token, "distance_cm": 0.5, "body_name": "Inspection Body"},
    )["body"]

    faces = registry.execute(state, "get_body_faces", {"body_token": body["token"]})["body_faces"]

    assert len(faces) == 6
    assert faces[0]["token"].startswith(body["token"])
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "get_body_faces",
    ]


def test_live_registry_supports_get_body_edges_inspection() -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

    registry.execute(state, "new_design", {"name": "Body Edges Inspection"})
    sketch = registry.execute(state, "create_sketch", {"plane": "xy", "name": "Inspection Sketch"})
    sketch_token = sketch["sketch"]["token"]
    registry.execute(
        state,
        "draw_rectangle",
        {"sketch_token": sketch_token, "width_cm": 3.0, "height_cm": 2.0},
    )
    profile_token = registry.execute(state, "list_profiles", {"sketch_token": sketch_token})["profiles"][0]["token"]
    body = registry.execute(
        state,
        "extrude_profile",
        {"profile_token": profile_token, "distance_cm": 0.5, "body_name": "Inspection Body"},
    )["body"]

    edges = registry.execute(state, "get_body_edges", {"body_token": body["token"]})["body_edges"]

    assert len(edges) == 12
    assert edges[0]["token"].startswith(body["token"])
    assert [call[0] for call in adapter.calls] == [
        "new_design",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "get_body_edges",
    ]
