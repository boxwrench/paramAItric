from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.bridge_client import BridgeClient
from mcp_server.errors import WorkflowFailure
from mcp_server.server import ParamAIToolServer


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
