from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.bridge_client import BridgeClient
from mcp_server.schemas import (
    CommandEnvelope,
    CreateBracketInput,
    CreateFilletedBracketInput,
    CreateCounterboredPlateInput,
    CreateFourHoleMountingPlateInput,
    CreateLidForBoxInput,
    CreateMountingBracketInput,
    CreateOpenBoxBodyInput,
    CreatePlateWithHoleInput,
    CreateRecessedMountInput,
    CreateSlottedMountInput,
    CreateSlottedMountingPlateInput,
    CreateSpacerInput,
    CreateTwoHolePlateInput,
    CreateTwoHoleMountingBracketInput,
)


def test_create_spacer_requires_positive_dimensions(tmp_path) -> None:
    with pytest.raises(ValueError):
        CreateSpacerInput.from_payload(
            {
                "width_cm": 0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(tmp_path / "bad.stl"),
            }
        )


def test_bridge_reports_missing_server() -> None:
    client = BridgeClient("http://127.0.0.1:1")
    with pytest.raises(RuntimeError, match="not reachable"):
        client.health()


def test_command_requires_name() -> None:
    with pytest.raises(ValueError):
        CommandEnvelope.build("", {})


def test_create_spacer_rejects_output_path_outside_allowlist() -> None:
    outside = Path.cwd().parent / "outside.stl"
    with pytest.raises(ValueError, match="allowlisted"):
        CreateSpacerInput.from_payload(
            {
                "width_cm": 1.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(outside),
            }
        )


def test_export_path_rejects_paths_outside_allowed_roots() -> None:
    for bad_path in [
        "C:/Windows/System32/evil.stl",
        "/etc/passwd.stl",
        str(Path.home() / "Documents" / "evil.stl"),
    ]:
        with pytest.raises(ValueError, match="allowlisted"):
            CreateSpacerInput.from_payload(
                {
                    "width_cm": 1.0,
                    "height_cm": 1.0,
                    "thickness_cm": 0.5,
                    "output_path": bad_path,
                }
            )


def test_create_bracket_requires_supported_plane_and_positive_dimensions(tmp_path) -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_bracket_validation.stl"
    with pytest.raises(ValueError, match="plane"):
        CreateBracketInput.from_payload(
            {
                "width_cm": 2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "plane": "front",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="height_cm"):
        CreateBracketInput.from_payload(
            {
                "width_cm": 2.0,
                "height_cm": 0.0,
                "thickness_cm": 0.5,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="leg_thickness_cm"):
        CreateBracketInput.from_payload(
            {
                "width_cm": 2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "leg_thickness_cm": 2.0,
                "output_path": str(output_path),
            }
        )


def test_create_filleted_bracket_requires_valid_fillet_radius() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_filleted_bracket_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateFilletedBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "fillet_radius_cm": 0.2,
                "plane": "front",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="leg_thickness_cm"):
        CreateFilletedBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 5.0,
                "fillet_radius_cm": 0.2,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="fillet_radius_cm"):
        CreateFilletedBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "fillet_radius_cm": 0.3,  # >= leg_thickness_cm / 2 = 0.25
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="fillet_radius_cm"):
        CreateFilletedBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.3,
                "leg_thickness_cm": 0.5,
                "fillet_radius_cm": 0.2,  # >= thickness_cm / 2 = 0.15
                "output_path": str(output_path),
            }
        )

    valid = CreateFilletedBracketInput.from_payload(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.75,
            "leg_thickness_cm": 0.5,
            "fillet_radius_cm": 0.2,
            "output_path": str(output_path),
        }
    )
    assert valid.fillet_radius_cm == 0.2
    assert valid.plane == "xy"


def test_create_mounting_bracket_requires_xy_and_hole_inside_leg() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_mounting_bracket_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateMountingBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 0.25,
                "hole_center_y_cm": 1.5,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )


def test_create_two_hole_mounting_bracket_requires_xy_and_valid_second_hole() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_two_hole_mounting_bracket_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateTwoHoleMountingBracketInput.from_payload(
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
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="second_hole"):
        CreateTwoHoleMountingBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "first_hole_center_x_cm": 0.25,
                "first_hole_center_y_cm": 1.5,
                "second_hole_center_x_cm": 1.5,
                "second_hole_center_y_cm": 1.5,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="overlap"):
        CreateTwoHoleMountingBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "first_hole_center_x_cm": 0.25,
                "first_hole_center_y_cm": 0.25,
                "second_hole_center_x_cm": 0.26,
                "second_hole_center_y_cm": 0.26,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="hole center"):
        CreateMountingBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 1.5,
                "hole_center_y_cm": 1.5,
                "output_path": str(output_path),
            }
        )


def test_create_plate_with_hole_requires_xy_and_hole_inside_bounds() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_plate_with_hole_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreatePlateWithHoleInput.from_payload(
            {
                "width_cm": 3.0,
                "height_cm": 2.0,
                "thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 1.0,
                "hole_center_y_cm": 0.5,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )


def test_create_counterbored_plate_requires_valid_counterbore_geometry() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_counterbored_plate_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateCounterboredPlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.5,
                "thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 2.0,
                "hole_center_y_cm": 1.25,
                "counterbore_diameter_cm": 0.8,
                "counterbore_depth_cm": 0.2,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="counterbore_diameter_cm"):
        CreateCounterboredPlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.5,
                "thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 2.0,
                "hole_center_y_cm": 1.25,
                "counterbore_diameter_cm": 0.4,
                "counterbore_depth_cm": 0.2,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="counterbore_depth_cm"):
        CreateCounterboredPlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.5,
                "thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 2.0,
                "hole_center_y_cm": 1.25,
                "counterbore_diameter_cm": 0.8,
                "counterbore_depth_cm": 0.5,
                "output_path": str(output_path),
            }
        )


def test_create_two_hole_plate_requires_xy_and_valid_edge_offset() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_two_hole_plate_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateTwoHolePlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.4,
                "edge_offset_x_cm": 0.75,
                "hole_center_y_cm": 1.0,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )


def test_create_four_hole_mounting_plate_requires_xy_and_valid_edge_offsets() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_four_hole_mounting_plate_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateFourHoleMountingPlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 3.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.4,
                "edge_offset_x_cm": 0.6,
                "edge_offset_y_cm": 0.7,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="edge_offset_x_cm"):
        CreateFourHoleMountingPlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 3.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.8,
                "edge_offset_x_cm": 1.7,
                "edge_offset_y_cm": 0.7,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="edge_offset_y_cm"):
        CreateFourHoleMountingPlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 3.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.8,
                "edge_offset_x_cm": 0.7,
                "edge_offset_y_cm": 1.2,
                "output_path": str(output_path),
            }
        )


def test_create_slotted_mounting_plate_requires_xy_and_clear_centered_slot() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_slotted_mounting_plate_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateSlottedMountingPlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 3.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.4,
                "edge_offset_x_cm": 0.6,
                "edge_offset_y_cm": 0.7,
                "slot_length_cm": 1.5,
                "slot_width_cm": 0.5,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="slot_length_cm"):
        CreateSlottedMountingPlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 3.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.4,
                "edge_offset_x_cm": 0.6,
                "edge_offset_y_cm": 0.7,
                "slot_length_cm": 0.5,
                "slot_width_cm": 0.5,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="bottom_left_hole overlaps the centered slot envelope"):
        CreateSlottedMountingPlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 3.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.8,
                "edge_offset_x_cm": 1.4,
                "edge_offset_y_cm": 1.1,
                "slot_length_cm": 1.5,
                "slot_width_cm": 0.6,
                "output_path": str(output_path),
            }
        )


def test_create_slotted_mount_requires_xy_and_slot_inside_bounds() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_slotted_mount_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateSlottedMountInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.4,
                "slot_length_cm": 1.5,
                "slot_width_cm": 0.5,
                "slot_center_x_cm": 2.0,
                "slot_center_y_cm": 1.0,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="slot_length_cm"):
        CreateSlottedMountInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.4,
                "slot_length_cm": 0.5,
                "slot_width_cm": 0.5,
                "slot_center_x_cm": 2.0,
                "slot_center_y_cm": 1.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="slot_center_x_cm"):
        CreateSlottedMountInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.4,
                "slot_length_cm": 1.5,
                "slot_width_cm": 0.5,
                "slot_center_x_cm": 0.5,
                "slot_center_y_cm": 1.0,
                "output_path": str(output_path),
            }
        )
    with pytest.raises(ValueError, match="edge_offset_x_cm"):
        CreateTwoHolePlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.8,
                "edge_offset_x_cm": 1.7,
                "hole_center_y_cm": 1.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="first_hole_center_y_cm"):
        CreateTwoHolePlateInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.4,
                "edge_offset_x_cm": 0.75,
                "hole_center_y_cm": 0.1,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="hole_center_x_cm"):
        CreatePlateWithHoleInput.from_payload(
            {
                "width_cm": 3.0,
                "height_cm": 2.0,
                "thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 0.1,
                "hole_center_y_cm": 0.5,
                "output_path": str(output_path),
            }
        )


def test_create_open_box_body_requires_xy_and_valid_wall_floor_thickness() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_open_box_body_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateOpenBoxBodyInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "height_cm": 2.0,
                "wall_thickness_cm": 0.3,
                "floor_thickness_cm": 0.3,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="inner cavity width"):
        CreateOpenBoxBodyInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "height_cm": 2.0,
                "wall_thickness_cm": 2.0,
                "floor_thickness_cm": 0.3,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="floor_thickness_cm"):
        CreateOpenBoxBodyInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "height_cm": 2.0,
                "wall_thickness_cm": 0.3,
                "floor_thickness_cm": 2.0,
                "output_path": str(output_path),
            }
        )


def test_create_lid_for_box_requires_xy_and_valid_rim_geometry() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_lid_for_box_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateLidForBoxInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "lid_thickness_cm": 0.2,
                "rim_depth_cm": 0.4,
                "wall_thickness_cm": 0.3,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="rim opening width"):
        CreateLidForBoxInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "lid_thickness_cm": 0.2,
                "rim_depth_cm": 0.4,
                "wall_thickness_cm": 2.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="rim opening depth"):
        CreateLidForBoxInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "lid_thickness_cm": 0.2,
                "rim_depth_cm": 0.4,
                "wall_thickness_cm": 1.5,
                "output_path": str(output_path),
            }
        )


def test_create_recessed_mount_requires_valid_recess_bounds() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_recessed_mount_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateRecessedMountInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.5,
                "thickness_cm": 0.5,
                "recess_width_cm": 2.0,
                "recess_height_cm": 1.0,
                "recess_depth_cm": 0.2,
                "recess_origin_x_cm": 0.5,
                "recess_origin_y_cm": 0.5,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="recess_depth_cm"):
        CreateRecessedMountInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.5,
                "thickness_cm": 0.5,
                "recess_width_cm": 2.0,
                "recess_height_cm": 1.0,
                "recess_depth_cm": 0.5,
                "recess_origin_x_cm": 0.5,
                "recess_origin_y_cm": 0.5,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="recess_origin_x_cm"):
        CreateRecessedMountInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.5,
                "thickness_cm": 0.5,
                "recess_width_cm": 2.0,
                "recess_height_cm": 1.0,
                "recess_depth_cm": 0.2,
                "recess_origin_x_cm": 2.5,
                "recess_origin_y_cm": 0.5,
                "output_path": str(output_path),
            }
        )
