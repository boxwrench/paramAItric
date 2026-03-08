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
    def create_sketch(self, plane: str, name: str) -> dict:
        return super().create_sketch("xz", name)

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
