from __future__ import annotations

from pathlib import Path
from urllib import error

import pytest

from mcp_server import bridge_client as bridge_client_module
from mcp_server.bridge_client import BridgeClient
from mcp_server.schemas import (
    CommandEnvelope,
    CreateBoxWithLidInput,
    CreateBracketInput,
    CreateCableGlandPlateInput,
    CreateChamferedBracketInput,
    CreateCylinderInput,
    CreateFlangedBushingInput,
    CreatePipeClampHalfInput,
    CreateRevolveInput,
    CreateFilletedBracketInput,
    CreateCounterboredPlateInput,
    CreateFourHoleMountingPlateInput,
    CreateLidForBoxInput,
    CreateMountingBracketInput,
    CreateOpenBoxBodyInput,
    CreatePlateWithHoleInput,
    CreateProjectBoxWithStandoffsInput,
    CreateShaftCouplerInput,
    CreateRecessedMountInput,
    CreateSimpleEnclosureInput,
    CreateSlottedMountInput,
    CreateSlottedMountingPlateInput,
    CreateSpacerInput,
    CreateTHandleWithSquareSocketInput,
    CreateTaperedKnobBlankInput,
    CreateTubeInput,
    CreateTubeMountingPlateInput,
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


def test_bridge_reports_missing_server(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(ConnectionRefusedError("actively refused"))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
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


def test_create_cylinder_requires_xy_and_positive_dimensions() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_cylinder_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateCylinderInput.from_payload(
            {
                "diameter_cm": 2.0,
                "height_cm": 3.0,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="diameter_cm"):
        CreateCylinderInput.from_payload(
            {
                "diameter_cm": 0.0,
                "height_cm": 3.0,
                "output_path": str(output_path),
            }
        )

    valid = CreateCylinderInput.from_payload(
        {
            "diameter_cm": 2.0,
            "height_cm": 3.0,
            "output_path": str(output_path),
        }
    )
    assert valid.diameter_cm == 2.0
    assert valid.height_cm == 3.0
    assert valid.plane == "xy"


def test_create_tube_mounting_plate_requires_xy_clearance_and_valid_tube_dimensions() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_tube_mounting_plate_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateTubeMountingPlateInput.from_payload(
            {
                "width_cm": 6.0,
                "height_cm": 10.0,
                "plate_thickness_cm": 0.5,
                "hole_diameter_cm": 0.5,
                "edge_offset_y_cm": 1.5,
                "tube_outer_diameter_cm": 2.0,
                "tube_inner_diameter_cm": 1.2,
                "tube_height_cm": 3.0,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="tube_inner_diameter_cm"):
        CreateTubeMountingPlateInput.from_payload(
            {
                "width_cm": 6.0,
                "height_cm": 10.0,
                "plate_thickness_cm": 0.5,
                "hole_diameter_cm": 0.5,
                "edge_offset_y_cm": 1.5,
                "tube_outer_diameter_cm": 2.0,
                "tube_inner_diameter_cm": 2.0,
                "tube_height_cm": 3.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="clear of the centered tube footprint"):
        CreateTubeMountingPlateInput.from_payload(
            {
                "width_cm": 6.0,
                "height_cm": 6.0,
                "plate_thickness_cm": 0.5,
                "hole_diameter_cm": 1.0,
                "edge_offset_y_cm": 2.0,
                "tube_outer_diameter_cm": 2.5,
                "tube_inner_diameter_cm": 1.5,
                "tube_height_cm": 3.0,
                "output_path": str(output_path),
            }
        )

    valid = CreateTubeMountingPlateInput.from_payload(
        {
            "width_cm": 6.0,
            "height_cm": 10.0,
            "plate_thickness_cm": 0.5,
            "hole_diameter_cm": 0.5,
            "edge_offset_y_cm": 1.5,
            "tube_outer_diameter_cm": 2.0,
            "tube_inner_diameter_cm": 1.2,
            "tube_height_cm": 3.0,
            "output_path": str(output_path),
        }
    )
    assert valid.plane == "xy"
    assert valid.body_name == "Tube Mounting Plate"


def test_create_tube_requires_xy_and_valid_bore_geometry() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_tube_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateTubeInput.from_payload(
            {
                "outer_diameter_cm": 2.0,
                "inner_diameter_cm": 1.0,
                "height_cm": 3.0,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="inner_diameter_cm"):
        CreateTubeInput.from_payload(
            {
                "outer_diameter_cm": 2.0,
                "inner_diameter_cm": 2.0,
                "height_cm": 3.0,
                "output_path": str(output_path),
            }
        )

    valid = CreateTubeInput.from_payload(
        {
            "outer_diameter_cm": 2.0,
            "inner_diameter_cm": 1.2,
            "height_cm": 3.0,
            "output_path": str(output_path),
        }
    )
    assert valid.plane == "xy"
    assert valid.body_name == "Tube"


def test_create_revolve_requires_xy_and_positive_diameters() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_revolve_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateRevolveInput.from_payload(
            {
                "base_diameter_cm": 3.0,
                "top_diameter_cm": 2.0,
                "height_cm": 2.5,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="top_diameter_cm"):
        CreateRevolveInput.from_payload(
            {
                "base_diameter_cm": 3.0,
                "top_diameter_cm": 0.0,
                "height_cm": 2.5,
                "output_path": str(output_path),
            }
        )

    valid = CreateRevolveInput.from_payload(
        {
            "base_diameter_cm": 3.0,
            "top_diameter_cm": 2.0,
            "height_cm": 2.5,
            "output_path": str(output_path),
        }
    )
    assert valid.plane == "xy"
    assert valid.body_name == "Revolved Solid"


def test_create_tapered_knob_blank_requires_xy_taper_and_socket_clearance() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_tapered_knob_blank_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateTaperedKnobBlankInput.from_payload(
            {
                "base_diameter_cm": 4.0,
                "top_diameter_cm": 3.0,
                "height_cm": 2.5,
                "stem_socket_diameter_cm": 1.0,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="top_diameter_cm"):
        CreateTaperedKnobBlankInput.from_payload(
            {
                "base_diameter_cm": 3.0,
                "top_diameter_cm": 3.5,
                "height_cm": 2.5,
                "stem_socket_diameter_cm": 1.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="narrowest knob diameter"):
        CreateTaperedKnobBlankInput.from_payload(
            {
                "base_diameter_cm": 4.0,
                "top_diameter_cm": 2.0,
                "height_cm": 2.5,
                "stem_socket_diameter_cm": 2.0,
                "output_path": str(output_path),
            }
        )

    valid = CreateTaperedKnobBlankInput.from_payload(
        {
            "base_diameter_cm": 4.0,
            "top_diameter_cm": 2.5,
            "height_cm": 2.5,
            "stem_socket_diameter_cm": 1.0,
            "output_path": str(output_path),
        }
    )
    assert valid.plane == "xy"
    assert valid.body_name == "Tapered Knob Blank"


def test_create_flanged_bushing_requires_xy_and_valid_interface_dimensions() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_flanged_bushing_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateFlangedBushingInput.from_payload(
            {
                "shaft_outer_diameter_cm": 2.0,
                "shaft_length_cm": 3.0,
                "flange_outer_diameter_cm": 3.0,
                "flange_thickness_cm": 0.6,
                "bore_diameter_cm": 1.0,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="flange_outer_diameter_cm"):
        CreateFlangedBushingInput.from_payload(
            {
                "shaft_outer_diameter_cm": 2.0,
                "shaft_length_cm": 3.0,
                "flange_outer_diameter_cm": 2.0,
                "flange_thickness_cm": 0.6,
                "bore_diameter_cm": 1.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="bore_diameter_cm"):
        CreateFlangedBushingInput.from_payload(
            {
                "shaft_outer_diameter_cm": 2.0,
                "shaft_length_cm": 3.0,
                "flange_outer_diameter_cm": 3.0,
                "flange_thickness_cm": 0.6,
                "bore_diameter_cm": 2.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="flange_thickness_cm"):
        CreateFlangedBushingInput.from_payload(
            {
                "shaft_outer_diameter_cm": 2.0,
                "shaft_length_cm": 3.0,
                "flange_outer_diameter_cm": 3.0,
                "flange_thickness_cm": 3.0,
                "bore_diameter_cm": 1.0,
                "output_path": str(output_path),
            }
        )

    valid = CreateFlangedBushingInput.from_payload(
        {
            "shaft_outer_diameter_cm": 2.0,
            "shaft_length_cm": 3.0,
            "flange_outer_diameter_cm": 3.0,
            "flange_thickness_cm": 0.6,
            "bore_diameter_cm": 1.0,
            "output_path": str(output_path),
        }
    )
    assert valid.plane == "xy"
    assert valid.body_name == "Flanged Bushing"


def test_create_pipe_clamp_half_requires_xy_and_valid_hole_channel_clearances() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_pipe_clamp_half_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreatePipeClampHalfInput.from_payload(
            {
                "clamp_width_cm": 6.0,
                "clamp_length_cm": 8.0,
                "clamp_height_cm": 2.0,
                "pipe_outer_diameter_cm": 2.5,
                "bolt_hole_diameter_cm": 0.6,
                "bolt_hole_edge_offset_x_cm": 1.0,
                "bolt_hole_center_y_cm": 4.0,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="bottom material"):
        CreatePipeClampHalfInput.from_payload(
            {
                "clamp_width_cm": 6.0,
                "clamp_length_cm": 8.0,
                "clamp_height_cm": 1.0,
                "pipe_outer_diameter_cm": 2.2,
                "bolt_hole_diameter_cm": 0.6,
                "bolt_hole_edge_offset_x_cm": 1.0,
                "bolt_hole_center_y_cm": 4.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="bolt_hole_edge_offset_x_cm"):
        CreatePipeClampHalfInput.from_payload(
            {
                "clamp_width_cm": 6.0,
                "clamp_length_cm": 8.0,
                "clamp_height_cm": 2.0,
                "pipe_outer_diameter_cm": 2.0,
                "bolt_hole_diameter_cm": 0.6,
                "bolt_hole_edge_offset_x_cm": 0.1,
                "bolt_hole_center_y_cm": 4.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="bolt holes must stay clear of the pipe saddle cut"):
        CreatePipeClampHalfInput.from_payload(
            {
                "clamp_width_cm": 6.0,
                "clamp_length_cm": 8.0,
                "clamp_height_cm": 2.0,
                "pipe_outer_diameter_cm": 2.8,
                "bolt_hole_diameter_cm": 0.8,
                "bolt_hole_edge_offset_x_cm": 1.8,
                "bolt_hole_center_y_cm": 4.0,
                "output_path": str(output_path),
            }
        )

    valid = CreatePipeClampHalfInput.from_payload(
        {
            "clamp_width_cm": 6.0,
            "clamp_length_cm": 8.0,
            "clamp_height_cm": 2.0,
            "pipe_outer_diameter_cm": 2.4,
            "bolt_hole_diameter_cm": 0.6,
            "bolt_hole_edge_offset_x_cm": 1.0,
            "bolt_hole_center_y_cm": 4.0,
            "output_path": str(output_path),
        }
    )
    assert valid.plane == "xy"
    assert valid.body_name == "Pipe Clamp Half"


def test_create_t_handle_with_square_socket_requires_xy_and_socket_clearance() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_t_handle_with_square_socket_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateTHandleWithSquareSocketInput.from_payload(
            {
                "tee_width_cm": 12.7,
                "tee_depth_cm": 5.08,
                "stem_length_cm": 5.08,
                "square_socket_width_cm": 1.905,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="square_socket_width_cm"):
        CreateTHandleWithSquareSocketInput.from_payload(
            {
                "tee_width_cm": 12.7,
                "tee_depth_cm": 5.08,
                "stem_length_cm": 5.08,
                "square_socket_width_cm": 5.08,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="socket_depth_cm"):
        CreateTHandleWithSquareSocketInput.from_payload(
            {
                "tee_width_cm": 12.7,
                "tee_depth_cm": 5.08,
                "stem_length_cm": 5.08,
                "square_socket_width_cm": 1.905,
                "socket_depth_cm": 5.5,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="socket_clearance_per_side_cm"):
        CreateTHandleWithSquareSocketInput.from_payload(
            {
                "tee_width_cm": 12.7,
                "tee_depth_cm": 5.08,
                "stem_length_cm": 5.08,
                "square_socket_width_cm": 1.905,
                "socket_clearance_per_side_cm": -0.01,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="socket_clearance_per_side_cm"):
        CreateTHandleWithSquareSocketInput.from_payload(
            {
                "tee_width_cm": 12.7,
                "tee_depth_cm": 5.08,
                "stem_length_cm": 5.08,
                "square_socket_width_cm": 4.0,
                "socket_clearance_per_side_cm": 0.6,
                "output_path": str(output_path),
            }
        )

    valid = CreateTHandleWithSquareSocketInput.from_payload(
        {
            "tee_width_cm": 12.7,
            "tee_depth_cm": 5.08,
            "stem_length_cm": 5.08,
            "square_socket_width_cm": 1.905,
            "output_path": str(output_path),
        }
    )
    assert valid.plane == "xy"
    assert valid.tee_thickness_cm == 5.08
    assert valid.socket_clearance_per_side_cm == pytest.approx(0.0)
    assert valid.top_chamfer_distance_cm == pytest.approx(0.635)

    valid_with_clearance = CreateTHandleWithSquareSocketInput.from_payload(
        {
            "tee_width_cm": 12.7,
            "tee_depth_cm": 5.08,
            "stem_length_cm": 5.08,
            "square_socket_width_cm": 1.905,
            "socket_clearance_per_side_cm": 0.05,
            "output_path": str(output_path),
        }
    )
    assert valid_with_clearance.socket_clearance_per_side_cm == pytest.approx(0.05)


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


def test_create_chamfered_bracket_requires_valid_chamfer_distance() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_chamfered_bracket_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateChamferedBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "chamfer_distance_cm": 0.2,
                "plane": "front",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="leg_thickness_cm"):
        CreateChamferedBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 5.0,
                "chamfer_distance_cm": 0.2,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="chamfer_distance_cm"):
        CreateChamferedBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "chamfer_distance_cm": 0.3,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="chamfer_distance_cm"):
        CreateChamferedBracketInput.from_payload(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.3,
                "leg_thickness_cm": 0.5,
                "chamfer_distance_cm": 0.2,
                "output_path": str(output_path),
            }
        )

    valid = CreateChamferedBracketInput.from_payload(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.75,
            "leg_thickness_cm": 0.5,
            "chamfer_distance_cm": 0.2,
            "output_path": str(output_path),
        }
    )
    assert valid.chamfer_distance_cm == 0.2
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


def test_create_simple_enclosure_requires_xy_and_valid_shell_thickness() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_create_simple_enclosure_validation.stl"

    with pytest.raises(ValueError, match="plane"):
        CreateSimpleEnclosureInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "height_cm": 2.0,
                "wall_thickness_cm": 0.3,
                "plane": "xz",
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="inner width"):
        CreateSimpleEnclosureInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "height_cm": 2.0,
                "wall_thickness_cm": 2.0,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="inner depth"):
        CreateSimpleEnclosureInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "height_cm": 2.0,
                "wall_thickness_cm": 1.5,
                "output_path": str(output_path),
            }
        )

    with pytest.raises(ValueError, match="height_cm"):
        CreateSimpleEnclosureInput.from_payload(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "height_cm": 0.3,
                "wall_thickness_cm": 0.3,
                "output_path": str(output_path),
            }
        )

    valid = CreateSimpleEnclosureInput.from_payload(
        {
            "width_cm": 4.0,
            "depth_cm": 3.0,
            "height_cm": 2.0,
            "wall_thickness_cm": 0.3,
            "output_path": str(output_path),
        }
    )
    assert valid.wall_thickness_cm == pytest.approx(0.3)
    assert valid.plane == "xy"


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


def test_create_box_with_lid_requires_valid_clearance() -> None:
    output_path_box = Path.cwd() / "manual_test_output" / "test_box_with_lid_box_validation.stl"
    output_path_lid = Path.cwd() / "manual_test_output" / "test_box_with_lid_lid_validation.stl"
    base = {
        "width_cm": 6.0,
        "depth_cm": 4.0,
        "box_height_cm": 3.0,
        "wall_thickness_cm": 0.3,
        "floor_thickness_cm": 0.3,
        "lid_thickness_cm": 0.2,
        "rim_depth_cm": 0.5,
        "clearance_cm": 0.05,
        "output_path_box": str(output_path_box),
        "output_path_lid": str(output_path_lid),
    }

    # clearance >= wall_thickness rejected
    with pytest.raises(ValueError, match="clearance_cm"):
        CreateBoxWithLidInput.from_payload({**base, "clearance_cm": 0.3})

    # clearance must be positive
    with pytest.raises(ValueError, match="clearance_cm"):
        CreateBoxWithLidInput.from_payload({**base, "clearance_cm": 0.0})

    # wall_thickness too large for box width
    with pytest.raises(ValueError, match="inner cavity width"):
        CreateBoxWithLidInput.from_payload({**base, "wall_thickness_cm": 3.0})

    # floor_thickness >= box_height rejected
    with pytest.raises(ValueError, match="floor_thickness_cm"):
        CreateBoxWithLidInput.from_payload({**base, "floor_thickness_cm": 3.0})

    # rim_depth >= cavity height rejected
    with pytest.raises(ValueError, match="rim_depth_cm"):
        CreateBoxWithLidInput.from_payload({**base, "rim_depth_cm": 2.8})

    # valid round-trip
    valid = CreateBoxWithLidInput.from_payload(base)
    assert valid.clearance_cm == pytest.approx(0.05)
    assert valid.width_cm == 6.0


def test_create_project_box_with_standoffs_validates_geometry() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_project_box_standoffs_validation.stl"
    base = {
        "width_cm": 8.0,
        "depth_cm": 6.0,
        "height_cm": 3.0,
        "wall_thickness_cm": 0.3,
        "standoff_diameter_cm": 0.5,
        "standoff_height_cm": 1.5,
        "standoff_inset_cm": 0.5,
        "output_path": str(output_path),
    }

    # plane must be xy
    with pytest.raises(ValueError, match="plane"):
        CreateProjectBoxWithStandoffsInput.from_payload({**base, "plane": "xz"})

    # wall too thick for width
    with pytest.raises(ValueError, match="inner width"):
        CreateProjectBoxWithStandoffsInput.from_payload({**base, "wall_thickness_cm": 4.0})

    # wall too thick for depth
    with pytest.raises(ValueError, match="inner depth"):
        CreateProjectBoxWithStandoffsInput.from_payload({**base, "wall_thickness_cm": 3.0})

    # wall >= height
    with pytest.raises(ValueError, match="height_cm"):
        CreateProjectBoxWithStandoffsInput.from_payload({**base, "wall_thickness_cm": 3.0, "width_cm": 100.0, "depth_cm": 100.0})

    # standoff taller than inner cavity
    with pytest.raises(ValueError, match="standoff_height_cm"):
        CreateProjectBoxWithStandoffsInput.from_payload({**base, "standoff_height_cm": 5.0})

    # standoff inset too small (< radius)
    with pytest.raises(ValueError, match="standoff_inset_cm must be at least"):
        CreateProjectBoxWithStandoffsInput.from_payload({**base, "standoff_inset_cm": 0.1})

    # standoff inset too large (outside inner width)
    with pytest.raises(ValueError, match="outside the inner width"):
        CreateProjectBoxWithStandoffsInput.from_payload({**base, "standoff_inset_cm": 4.0})

    # valid round-trip
    valid = CreateProjectBoxWithStandoffsInput.from_payload(base)
    assert valid.width_cm == 8.0
    assert valid.standoff_diameter_cm == 0.5
    assert valid.standoff_inset_cm == 0.5
    assert valid.plane == "xy"


def test_create_shaft_coupler_validates_geometry() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_shaft_coupler_validation.stl"
    base = {
        "outer_diameter_cm": 2.5,
        "length_cm": 5.0,
        "bore_diameter_cm": 0.8,
        "pin_hole_diameter_cm": 0.4,
        "pin_hole_offset_cm": 2.5,
        "output_path": str(output_path),
    }

    # plane must be xy
    with pytest.raises(ValueError, match="plane"):
        CreateShaftCouplerInput.from_payload({**base, "plane": "xz"})

    # bore >= outer diameter
    with pytest.raises(ValueError, match="bore_diameter_cm"):
        CreateShaftCouplerInput.from_payload({**base, "bore_diameter_cm": 2.5})

    # pin hole >= outer diameter
    with pytest.raises(ValueError, match="pin_hole_diameter_cm"):
        CreateShaftCouplerInput.from_payload({**base, "pin_hole_diameter_cm": 3.0})

    # pin hole extends past coupler end (offset too large)
    with pytest.raises(ValueError, match="pin_hole_offset_cm"):
        CreateShaftCouplerInput.from_payload({**base, "pin_hole_offset_cm": 4.9})

    # pin hole extends past coupler start (offset too small)
    with pytest.raises(ValueError, match="pin_hole_offset_cm"):
        CreateShaftCouplerInput.from_payload({**base, "pin_hole_offset_cm": 0.1})

    # valid round-trip
    valid = CreateShaftCouplerInput.from_payload(base)
    assert valid.outer_diameter_cm == 2.5
    assert valid.bore_diameter_cm == 0.8
    assert valid.pin_hole_offset_cm == 2.5
    assert valid.plane == "xy"


def test_create_cable_gland_plate_validates_geometry() -> None:
    output_path = Path.cwd() / "manual_test_output" / "test_cable_gland_plate_validation.stl"
    base = {
        "width_cm": 10.0,
        "height_cm": 8.0,
        "thickness_cm": 0.4,
        "center_hole_diameter_cm": 3.0,
        "mounting_hole_diameter_cm": 0.5,
        "edge_offset_x_cm": 1.0,
        "edge_offset_y_cm": 1.0,
        "output_path": str(output_path),
    }

    with pytest.raises(ValueError, match="plane"):
        CreateCableGlandPlateInput.from_payload({**base, "plane": "xz"})

    # center hole too large for width
    with pytest.raises(ValueError, match="center_hole_diameter_cm"):
        CreateCableGlandPlateInput.from_payload({**base, "center_hole_diameter_cm": 10.0})

    # center hole too large for height
    with pytest.raises(ValueError, match="center_hole_diameter_cm"):
        CreateCableGlandPlateInput.from_payload({**base, "center_hole_diameter_cm": 8.0})

    # mounting hole x offset places column too close to center
    with pytest.raises(ValueError, match="edge_offset_x_cm"):
        CreateCableGlandPlateInput.from_payload({**base, "edge_offset_x_cm": 5.2})

    # center hole overlaps a mounting hole (small plate, large center hole, mounting holes near center)
    with pytest.raises(ValueError, match="overlaps"):
        CreateCableGlandPlateInput.from_payload({
            "width_cm": 4.0, "height_cm": 4.0, "thickness_cm": 0.4,
            "center_hole_diameter_cm": 2.5, "mounting_hole_diameter_cm": 0.4,
            "edge_offset_x_cm": 1.5, "edge_offset_y_cm": 1.5,
            "output_path": str(output_path),
        })

    # valid round-trip
    valid = CreateCableGlandPlateInput.from_payload(base)
    assert valid.width_cm == 10.0
    assert valid.height_cm == 8.0
    assert valid.center_hole_diameter_cm == 3.0
    assert valid.mounting_hole_diameter_cm == 0.5
    assert valid.plane == "xy"
