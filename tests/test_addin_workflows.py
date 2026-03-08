from __future__ import annotations

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


def test_live_registry_runs_spacer_stage_sequence(tmp_path) -> None:
    adapter = RecordingFakeFusionAdapter()
    registry = build_registry(execution_context=FusionExecutionContext(adapter=adapter))
    state = DesignState()

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
            "output_path": str(tmp_path / "spacer.stl"),
            "workflow_name": "spacer",
        },
    )

    assert scene["bodies"][0]["name"] == "Spacer"
    assert exported["output_path"].endswith("spacer.stl")
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
