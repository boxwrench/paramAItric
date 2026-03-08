from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.bridge_client import BridgeClient, BridgeTimeoutError
from mcp_server.errors import WorkflowFailure
from mcp_server.server import ParamAIToolServer
from mcp_server.schemas import CommandEnvelope


def test_create_spacer_workflow_exports_stl(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_workflow_exports_stl.stl"

    result = server.create_spacer(
        {
            "width_cm": 2.0,
            "height_cm": 1.0,
            "thickness_cm": 0.5,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["verification"]["body_count"] == 1
    assert result["verification"]["actual_width_cm"] == 2.0
    assert result["retry_policy"] == "none"
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_spacer_stops_on_bad_input(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_stops_on_bad_input.stl"

    try:
        server.create_spacer(
            {
                "width_cm": -2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(output_path),
            }
        )
    except ValueError as exc:
        assert "width_cm" in str(exc)
    else:
        raise AssertionError("Expected validation failure.")


def test_create_spacer_preserves_partial_result_on_verification_failure(running_bridge, monkeypatch, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_preserves_partial_result.stl"

    original_extrude = server.extrude_profile

    def bad_extrude(profile_token: str, distance_cm: float, body_name: str) -> dict:
        result = original_extrude(profile_token, distance_cm, body_name)
        result["result"]["body"]["width_cm"] = 999.0
        return result

    monkeypatch.setattr(server, "extrude_profile", bad_extrude)

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_spacer(
            {
                "width_cm": 2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "verify_dimensions"
    assert failure.classification == "verification_failed"
    assert failure.partial_result["expected"]["width_cm"] == 2.0


def test_create_spacer_wraps_bridge_failure_in_workflow_failure(running_bridge, monkeypatch) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_wraps_bridge_failure.stl"

    def bridge_down() -> dict:
        raise RuntimeError("Fusion bridge is not reachable.")

    monkeypatch.setattr(server, "get_scene_info", bridge_down)

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_spacer(
            {
                "width_cm": 2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "verify_clean_state"
    assert failure.classification == "bridge_error"
    assert failure.partial_result["stages"] == [{"stage": "new_design", "status": "completed"}]
    assert "Fusion bridge is not reachable." in str(failure)


def test_create_bracket_workflow_exports_stl(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_bracket_workflow_exports_stl.stl"

    result = server.create_bracket(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.75,
            "leg_thickness_cm": 0.5,
            "plane": "xz",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_bracket"
    assert result["workflow_basis"]["name"] == "bracket"
    assert result["verification"]["body_count"] == 1
    assert result["verification"]["actual_width_cm"] == 4.0
    assert result["verification"]["actual_height_cm"] == 2.0
    assert result["verification"]["actual_thickness_cm"] == 0.75
    assert result["verification"]["sketch_plane"] == "xz"
    assert result["verification"]["leg_thickness_cm"] == 0.5
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_l_bracket_profile",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_mounting_bracket_workflow_selects_outer_profile(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_mounting_bracket_workflow_exports_stl.stl"

    result = server.create_mounting_bracket(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.75,
            "leg_thickness_cm": 0.5,
            "hole_diameter_cm": 0.4,
            "hole_center_x_cm": 0.25,
            "hole_center_y_cm": 1.5,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_mounting_bracket"
    assert result["workflow_basis"]["name"] == "mounting_bracket"
    assert result["verification"]["actual_width_cm"] == 4.0
    assert result["verification"]["actual_height_cm"] == 2.0
    assert result["verification"]["actual_thickness_cm"] == 0.75
    assert result["verification"]["hole_diameter_cm"] == 0.4
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_l_bracket_profile",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_two_hole_mounting_bracket_workflow_exports_stl(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_two_hole_mounting_bracket_workflow.stl"

    result = server.create_two_hole_mounting_bracket(
        {
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
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_two_hole_mounting_bracket"
    assert result["workflow_basis"]["name"] == "two_hole_mounting_bracket"
    assert result["verification"]["hole_count"] == 2
    assert [stage["stage"] for stage in result["stages"]] == [
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
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_bridge_command_error_surfaces_as_runtime_error(running_bridge) -> None:
    """A bad command through the bridge raises RuntimeError, not a silent failure."""
    _, base_url = running_bridge
    client = BridgeClient(base_url)
    with pytest.raises(RuntimeError, match="Bridge command failed"):
        client.send(CommandEnvelope.build("draw_rectangle", {"sketch_token": "bad", "width_cm": 1.0, "height_cm": 1.0}))


def test_workflow_failure_includes_partial_state_on_dirty_scene(running_bridge, monkeypatch) -> None:
    """WorkflowFailure on state_drift carries the scene snapshot in partial_result.

    The verify_clean_state check fires when get_scene_info reports bodies after new_design.
    We simulate that by patching get_scene_info to return a dirty scene on the first call.
    """
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_dirty_state.stl"

    original_get_scene_info = server.get_scene_info
    call_count = [0]

    def dirty_scene_once() -> dict:
        call_count[0] += 1
        if call_count[0] == 1:
            return {"result": {"design_name": "stale", "bodies": [{"token": "b1"}], "sketches": [], "exports": []}}
        return original_get_scene_info()

    monkeypatch.setattr(server, "get_scene_info", dirty_scene_once)

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_spacer(
            {
                "width_cm": 2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "verify_clean_state"
    assert failure.classification == "state_drift"
    assert "scene" in failure.partial_result


def test_create_mounting_bracket_wraps_export_bridge_failure(running_bridge, monkeypatch) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_mounting_bracket_bridge_failure.stl"

    def fail_export(body_token: str, output_path: str) -> dict:  # noqa: ARG001
        raise RuntimeError("Bridge command failed: export unavailable")

    monkeypatch.setattr(server, "export_stl", fail_export)

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_mounting_bracket(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 0.25,
                "hole_center_y_cm": 1.5,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "export_stl"
    assert failure.classification == "bridge_error"
    assert failure.partial_result["body"]["name"] == "Mounting Bracket"
    assert failure.partial_result["stages"][-1]["stage"] == "verify_geometry"


def test_create_spacer_wraps_bridge_timeout_in_workflow_failure(running_bridge, monkeypatch) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_wraps_bridge_timeout.stl"

    def bridge_timeout() -> dict:
        raise BridgeTimeoutError("Fusion bridge request timed out.")

    monkeypatch.setattr(server, "get_scene_info", bridge_timeout)

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_spacer(
            {
                "width_cm": 2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "verify_clean_state"
    assert failure.classification == "timeout"
    assert failure.partial_result["stages"] == [{"stage": "new_design", "status": "completed"}]
    assert "timed out" in str(failure)
