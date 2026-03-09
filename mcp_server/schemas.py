from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir

from mcp_server.geometry_utils import (
    validate_hole_position,
    validate_rectangular_hole_position,
    validate_rectangle_placement,
    validate_slot_hole_clearance,
    validate_slot_position,
)


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _require_positive_number(value: object, field_name: str) -> float:
    if not isinstance(value, (int, float)) or float(value) <= 0:
        raise ValueError(f"{field_name} must be a positive number.")
    return float(value)


def _require_non_negative_number(value: object, field_name: str) -> float:
    if not isinstance(value, (int, float)) or float(value) < 0:
        raise ValueError(f"{field_name} must be a non-negative number.")
    return float(value)


def _is_within(destination: Path, root: Path) -> bool:
    try:
        destination.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_export_path(output_path: object) -> str:
    output_path = _require_non_empty_string(output_path, "output_path")
    destination = Path(output_path).expanduser().resolve(strict=False)
    if not destination.suffix:
        raise ValueError("output_path must include a file extension.")
    if "manual_test_output" in destination.parts:
        return str(destination)
    if _is_within(destination, Path(gettempdir()).resolve(strict=False)):
        return str(destination)
    raise ValueError("output_path must stay inside an allowlisted export directory.")


_VALID_EXTRUDE_OPERATIONS = frozenset({"new_body", "cut"})


def _validate_extrude_operation(value: object) -> str:
    """Return a validated extrude operation string.

    Accepts None (defaults to "new_body") or an explicit "new_body" / "cut"
    string.  Any other value raises ValueError so callers can surface the error
    before sending the command to the bridge.
    """
    if value is None:
        return "new_body"
    if isinstance(value, str) and value in _VALID_EXTRUDE_OPERATIONS:
        return value
    raise ValueError(
        f"operation must be one of: {', '.join(sorted(_VALID_EXTRUDE_OPERATIONS))}."
    )


@dataclass(frozen=True)
class CommandEnvelope:
    command: str
    arguments: dict

    @classmethod
    def build(cls, command: str, arguments: dict | None = None) -> "CommandEnvelope":
        return cls(command=_require_non_empty_string(command, "command"), arguments=arguments or {})


@dataclass(frozen=True)
class CreateSpacerInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateSpacerInput":
        output_path = _validate_export_path(payload["output_path"])
        return cls(
            width_cm=_require_positive_number(payload["width_cm"], "width_cm"),
            height_cm=_require_positive_number(payload["height_cm"], "height_cm"),
            thickness_cm=_require_positive_number(payload["thickness_cm"], "thickness_cm"),
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Spacer Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Spacer"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateCylinderInput:
    diameter_cm: float
    height_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateCylinderInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for cylinder in the current validated scope.")
        return cls(
            diameter_cm=_require_positive_number(payload["diameter_cm"], "diameter_cm"),
            height_cm=_require_positive_number(payload["height_cm"], "height_cm"),
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Cylinder Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Cylinder"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateTubeInput:
    outer_diameter_cm: float
    inner_diameter_cm: float
    height_cm: float
    plane: str
    sketch_name: str
    bore_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateTubeInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for tube in the current validated scope.")
        outer_diameter_cm = _require_positive_number(payload["outer_diameter_cm"], "outer_diameter_cm")
        inner_diameter_cm = _require_positive_number(payload["inner_diameter_cm"], "inner_diameter_cm")
        if inner_diameter_cm >= outer_diameter_cm:
            raise ValueError("inner_diameter_cm must be smaller than outer_diameter_cm.")
        return cls(
            outer_diameter_cm=outer_diameter_cm,
            inner_diameter_cm=inner_diameter_cm,
            height_cm=_require_positive_number(payload["height_cm"], "height_cm"),
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Tube Sketch"), "sketch_name"),
            bore_sketch_name=_require_non_empty_string(payload.get("bore_sketch_name", "Tube Bore Sketch"), "bore_sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Tube"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateRevolveInput:
    base_diameter_cm: float
    top_diameter_cm: float
    height_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateRevolveInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for revolve in the current validated scope.")
        base_diameter_cm = _require_positive_number(payload["base_diameter_cm"], "base_diameter_cm")
        top_diameter_cm = _require_positive_number(payload["top_diameter_cm"], "top_diameter_cm")
        return cls(
            base_diameter_cm=base_diameter_cm,
            top_diameter_cm=top_diameter_cm,
            height_cm=_require_positive_number(payload["height_cm"], "height_cm"),
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Revolve Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Revolved Solid"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateTaperedKnobBlankInput:
    base_diameter_cm: float
    top_diameter_cm: float
    height_cm: float
    stem_socket_diameter_cm: float
    plane: str
    sketch_name: str
    socket_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateTaperedKnobBlankInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for tapered_knob_blank in the current validated scope.")
        base_diameter_cm = _require_positive_number(payload["base_diameter_cm"], "base_diameter_cm")
        top_diameter_cm = _require_positive_number(payload["top_diameter_cm"], "top_diameter_cm")
        stem_socket_diameter_cm = _require_positive_number(payload["stem_socket_diameter_cm"], "stem_socket_diameter_cm")
        if top_diameter_cm > base_diameter_cm:
            raise ValueError("top_diameter_cm must be less than or equal to base_diameter_cm for tapered_knob_blank.")
        if stem_socket_diameter_cm >= min(base_diameter_cm, top_diameter_cm):
            raise ValueError("stem_socket_diameter_cm must be smaller than the narrowest knob diameter.")
        return cls(
            base_diameter_cm=base_diameter_cm,
            top_diameter_cm=top_diameter_cm,
            height_cm=_require_positive_number(payload["height_cm"], "height_cm"),
            stem_socket_diameter_cm=stem_socket_diameter_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Knob Profile Sketch"), "sketch_name"),
            socket_sketch_name=_require_non_empty_string(payload.get("socket_sketch_name", "Stem Socket Sketch"), "socket_sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Tapered Knob Blank"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateFlangedBushingInput:
    shaft_outer_diameter_cm: float
    shaft_length_cm: float
    flange_outer_diameter_cm: float
    flange_thickness_cm: float
    bore_diameter_cm: float
    plane: str
    sketch_name: str
    flange_sketch_name: str
    bore_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateFlangedBushingInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for flanged_bushing in the current validated scope.")
        shaft_outer_diameter_cm = _require_positive_number(payload["shaft_outer_diameter_cm"], "shaft_outer_diameter_cm")
        shaft_length_cm = _require_positive_number(payload["shaft_length_cm"], "shaft_length_cm")
        flange_outer_diameter_cm = _require_positive_number(payload["flange_outer_diameter_cm"], "flange_outer_diameter_cm")
        flange_thickness_cm = _require_positive_number(payload["flange_thickness_cm"], "flange_thickness_cm")
        bore_diameter_cm = _require_positive_number(payload["bore_diameter_cm"], "bore_diameter_cm")

        if flange_outer_diameter_cm <= shaft_outer_diameter_cm:
            raise ValueError("flange_outer_diameter_cm must be greater than shaft_outer_diameter_cm.")
        if flange_thickness_cm >= shaft_length_cm:
            raise ValueError("flange_thickness_cm must be smaller than shaft_length_cm.")
        if bore_diameter_cm >= shaft_outer_diameter_cm:
            raise ValueError("bore_diameter_cm must be smaller than shaft_outer_diameter_cm.")

        return cls(
            shaft_outer_diameter_cm=shaft_outer_diameter_cm,
            shaft_length_cm=shaft_length_cm,
            flange_outer_diameter_cm=flange_outer_diameter_cm,
            flange_thickness_cm=flange_thickness_cm,
            bore_diameter_cm=bore_diameter_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Bushing Profile Sketch"), "sketch_name"),
            flange_sketch_name=_require_non_empty_string(payload.get("flange_sketch_name", "Flange Sketch"), "flange_sketch_name"),
            bore_sketch_name=_require_non_empty_string(payload.get("bore_sketch_name", "Bore Sketch"), "bore_sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Flanged Bushing"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreatePipeClampHalfInput:
    clamp_width_cm: float
    clamp_length_cm: float
    clamp_height_cm: float
    pipe_outer_diameter_cm: float
    bolt_hole_diameter_cm: float
    bolt_hole_edge_offset_x_cm: float
    bolt_hole_center_y_cm: float
    plane: str
    sketch_name: str
    channel_sketch_name: str
    first_hole_sketch_name: str
    second_hole_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreatePipeClampHalfInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for pipe_clamp_half in the current validated scope.")

        clamp_width_cm = _require_positive_number(payload["clamp_width_cm"], "clamp_width_cm")
        clamp_length_cm = _require_positive_number(payload["clamp_length_cm"], "clamp_length_cm")
        clamp_height_cm = _require_positive_number(payload["clamp_height_cm"], "clamp_height_cm")
        pipe_outer_diameter_cm = _require_positive_number(payload["pipe_outer_diameter_cm"], "pipe_outer_diameter_cm")
        bolt_hole_diameter_cm = _require_positive_number(payload["bolt_hole_diameter_cm"], "bolt_hole_diameter_cm")
        bolt_hole_edge_offset_x_cm = _require_positive_number(payload["bolt_hole_edge_offset_x_cm"], "bolt_hole_edge_offset_x_cm")
        bolt_hole_center_y_cm = _require_positive_number(payload["bolt_hole_center_y_cm"], "bolt_hole_center_y_cm")

        pipe_radius_cm = pipe_outer_diameter_cm / 2.0
        bolt_hole_radius_cm = bolt_hole_diameter_cm / 2.0

        if pipe_radius_cm >= clamp_width_cm / 2.0:
            raise ValueError("pipe_outer_diameter_cm must leave side walls in clamp_width_cm.")
        if pipe_radius_cm >= clamp_height_cm:
            raise ValueError("pipe_outer_diameter_cm must leave bottom material in clamp_height_cm.")
        if bolt_hole_edge_offset_x_cm <= bolt_hole_radius_cm or bolt_hole_edge_offset_x_cm >= (clamp_width_cm / 2.0) - bolt_hole_radius_cm:
            raise ValueError("bolt_hole_edge_offset_x_cm must keep both mirrored bolt holes inside the clamp footprint.")
        if bolt_hole_center_y_cm <= bolt_hole_radius_cm or bolt_hole_center_y_cm >= clamp_length_cm - bolt_hole_radius_cm:
            raise ValueError("bolt_hole_center_y_cm must keep the bolt holes inside the clamp length bounds.")

        hole_channel_clearance_cm = (clamp_width_cm / 2.0) - bolt_hole_edge_offset_x_cm
        if hole_channel_clearance_cm <= pipe_radius_cm + bolt_hole_radius_cm:
            raise ValueError("bolt holes must stay clear of the pipe saddle cut.")

        return cls(
            clamp_width_cm=clamp_width_cm,
            clamp_length_cm=clamp_length_cm,
            clamp_height_cm=clamp_height_cm,
            pipe_outer_diameter_cm=pipe_outer_diameter_cm,
            bolt_hole_diameter_cm=bolt_hole_diameter_cm,
            bolt_hole_edge_offset_x_cm=bolt_hole_edge_offset_x_cm,
            bolt_hole_center_y_cm=bolt_hole_center_y_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Pipe Clamp Half Sketch"), "sketch_name"),
            channel_sketch_name=_require_non_empty_string(payload.get("channel_sketch_name", "Pipe Saddle Sketch"), "channel_sketch_name"),
            first_hole_sketch_name=_require_non_empty_string(payload.get("first_hole_sketch_name", "First Bolt Hole Sketch"), "first_hole_sketch_name"),
            second_hole_sketch_name=_require_non_empty_string(payload.get("second_hole_sketch_name", "Second Bolt Hole Sketch"), "second_hole_sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Pipe Clamp Half"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateTHandleWithSquareSocketInput:
    tee_width_cm: float
    tee_depth_cm: float
    tee_thickness_cm: float
    stem_length_cm: float
    square_socket_width_cm: float
    socket_clearance_per_side_cm: float
    socket_depth_cm: float
    top_chamfer_distance_cm: float
    plane: str
    stem_sketch_name: str
    tee_sketch_name: str
    socket_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateTHandleWithSquareSocketInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for t_handle_with_square_socket in the current validated scope.")
        tee_width_cm = _require_positive_number(payload["tee_width_cm"], "tee_width_cm")
        tee_depth_cm = _require_positive_number(payload["tee_depth_cm"], "tee_depth_cm")
        tee_thickness_cm = _require_positive_number(payload.get("tee_thickness_cm", tee_depth_cm), "tee_thickness_cm")
        stem_length_cm = _require_positive_number(payload["stem_length_cm"], "stem_length_cm")
        square_socket_width_cm = _require_positive_number(payload["square_socket_width_cm"], "square_socket_width_cm")
        socket_clearance_per_side_cm = _require_non_negative_number(
            payload.get("socket_clearance_per_side_cm", 0.0),
            "socket_clearance_per_side_cm",
        )
        socket_depth_cm = _require_positive_number(payload.get("socket_depth_cm", stem_length_cm), "socket_depth_cm")
        top_chamfer_distance_cm = _require_positive_number(
            payload.get("top_chamfer_distance_cm", min(tee_depth_cm, tee_thickness_cm) * 0.125),
            "top_chamfer_distance_cm",
        )
        if square_socket_width_cm >= tee_depth_cm:
            raise ValueError("square_socket_width_cm must be smaller than tee_depth_cm.")
        effective_square_socket_width_cm = square_socket_width_cm + (socket_clearance_per_side_cm * 2.0)
        if effective_square_socket_width_cm >= tee_depth_cm:
            raise ValueError("socket_clearance_per_side_cm expands the socket beyond tee_depth_cm.")
        if socket_depth_cm > stem_length_cm:
            raise ValueError("socket_depth_cm must be less than or equal to stem_length_cm.")
        if top_chamfer_distance_cm >= min(tee_depth_cm, tee_thickness_cm) / 2.0:
            raise ValueError("top_chamfer_distance_cm must leave a positive top face on the tee.")
        return cls(
            tee_width_cm=tee_width_cm,
            tee_depth_cm=tee_depth_cm,
            tee_thickness_cm=tee_thickness_cm,
            stem_length_cm=stem_length_cm,
            square_socket_width_cm=square_socket_width_cm,
            socket_clearance_per_side_cm=socket_clearance_per_side_cm,
            socket_depth_cm=socket_depth_cm,
            top_chamfer_distance_cm=top_chamfer_distance_cm,
            plane=plane,
            stem_sketch_name=_require_non_empty_string(payload.get("stem_sketch_name", "T Handle Stem Sketch"), "stem_sketch_name"),
            tee_sketch_name=_require_non_empty_string(payload.get("tee_sketch_name", "T Handle Tee Sketch"), "tee_sketch_name"),
            socket_sketch_name=_require_non_empty_string(payload.get("socket_sketch_name", "Square Socket Sketch"), "socket_sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "T Handle With Square Socket"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateTubeMountingPlateInput:
    width_cm: float
    height_cm: float
    plate_thickness_cm: float
    hole_diameter_cm: float
    edge_offset_y_cm: float
    tube_outer_diameter_cm: float
    tube_inner_diameter_cm: float
    tube_height_cm: float
    plane: str
    sketch_name: str
    first_hole_sketch_name: str
    second_hole_sketch_name: str
    tube_sketch_name: str
    bore_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateTubeMountingPlateInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for tube_mounting_plate in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        plate_thickness_cm = _require_positive_number(payload["plate_thickness_cm"], "plate_thickness_cm")
        hole_diameter_cm = _require_positive_number(payload["hole_diameter_cm"], "hole_diameter_cm")
        edge_offset_y_cm = _require_positive_number(payload["edge_offset_y_cm"], "edge_offset_y_cm")
        tube_outer_diameter_cm = _require_positive_number(payload["tube_outer_diameter_cm"], "tube_outer_diameter_cm")
        tube_inner_diameter_cm = _require_positive_number(payload["tube_inner_diameter_cm"], "tube_inner_diameter_cm")
        tube_height_cm = _require_positive_number(payload["tube_height_cm"], "tube_height_cm")
        if tube_inner_diameter_cm >= tube_outer_diameter_cm:
            raise ValueError("tube_inner_diameter_cm must be smaller than tube_outer_diameter_cm.")

        hole_radius_cm = hole_diameter_cm / 2.0
        tube_outer_radius_cm = tube_outer_diameter_cm / 2.0
        if hole_radius_cm >= width_cm / 2.0:
            raise ValueError("hole_diameter_cm must leave material on both plate side edges.")
        if edge_offset_y_cm <= hole_radius_cm or edge_offset_y_cm >= (height_cm / 2.0) - hole_radius_cm:
            raise ValueError("edge_offset_y_cm must keep both mounting holes inside the plate bounds.")
        if tube_outer_radius_cm >= width_cm / 2.0 or tube_outer_radius_cm >= height_cm / 2.0:
            raise ValueError("tube_outer_diameter_cm must fit within the plate footprint.")
        hole_centerline_clearance_cm = (height_cm / 2.0) - edge_offset_y_cm
        if hole_centerline_clearance_cm <= hole_radius_cm + tube_outer_radius_cm:
            raise ValueError("mounting holes must stay clear of the centered tube footprint.")

        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            plate_thickness_cm=plate_thickness_cm,
            hole_diameter_cm=hole_diameter_cm,
            edge_offset_y_cm=edge_offset_y_cm,
            tube_outer_diameter_cm=tube_outer_diameter_cm,
            tube_inner_diameter_cm=tube_inner_diameter_cm,
            tube_height_cm=tube_height_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Tube Mounting Plate Sketch"), "sketch_name"),
            first_hole_sketch_name=_require_non_empty_string(payload.get("first_hole_sketch_name", "Upper Hole Sketch"), "first_hole_sketch_name"),
            second_hole_sketch_name=_require_non_empty_string(payload.get("second_hole_sketch_name", "Lower Hole Sketch"), "second_hole_sketch_name"),
            tube_sketch_name=_require_non_empty_string(payload.get("tube_sketch_name", "Tube Outer Sketch"), "tube_sketch_name"),
            bore_sketch_name=_require_non_empty_string(payload.get("bore_sketch_name", "Tube Bore Sketch"), "bore_sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Tube Mounting Plate"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateBracketInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    leg_thickness_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateBracketInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane not in {"xy", "xz", "yz"}:
            raise ValueError("plane must be one of: xy, xz, yz.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        leg_thickness_cm = _require_positive_number(payload.get("leg_thickness_cm", thickness_cm), "leg_thickness_cm")
        if leg_thickness_cm >= width_cm or leg_thickness_cm >= height_cm:
            raise ValueError("leg_thickness_cm must be smaller than width_cm and height_cm.")
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            leg_thickness_cm=leg_thickness_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Bracket Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Bracket"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateFilletedBracketInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    leg_thickness_cm: float
    fillet_radius_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateFilletedBracketInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane not in {"xy", "xz", "yz"}:
            raise ValueError("plane must be one of: xy, xz, yz.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        leg_thickness_cm = _require_positive_number(payload.get("leg_thickness_cm", thickness_cm), "leg_thickness_cm")
        if leg_thickness_cm >= width_cm or leg_thickness_cm >= height_cm:
            raise ValueError("leg_thickness_cm must be smaller than width_cm and height_cm.")
        fillet_radius_cm = _require_positive_number(payload["fillet_radius_cm"], "fillet_radius_cm")
        if fillet_radius_cm >= leg_thickness_cm / 2:
            raise ValueError("fillet_radius_cm must be less than half of leg_thickness_cm.")
        if fillet_radius_cm >= thickness_cm / 2:
            raise ValueError("fillet_radius_cm must be less than half of thickness_cm.")
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            leg_thickness_cm=leg_thickness_cm,
            fillet_radius_cm=fillet_radius_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Filleted Bracket Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Filleted Bracket"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateChamferedBracketInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    leg_thickness_cm: float
    chamfer_distance_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateChamferedBracketInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane not in {"xy", "xz", "yz"}:
            raise ValueError("plane must be one of: xy, xz, yz.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        leg_thickness_cm = _require_positive_number(payload.get("leg_thickness_cm", thickness_cm), "leg_thickness_cm")
        if leg_thickness_cm >= width_cm or leg_thickness_cm >= height_cm:
            raise ValueError("leg_thickness_cm must be smaller than width_cm and height_cm.")
        chamfer_distance_cm = _require_positive_number(payload["chamfer_distance_cm"], "chamfer_distance_cm")
        if chamfer_distance_cm >= leg_thickness_cm / 2:
            raise ValueError("chamfer_distance_cm must be less than half of leg_thickness_cm.")
        if chamfer_distance_cm >= thickness_cm / 2:
            raise ValueError("chamfer_distance_cm must be less than half of thickness_cm.")
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            leg_thickness_cm=leg_thickness_cm,
            chamfer_distance_cm=chamfer_distance_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Chamfered Bracket Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Chamfered Bracket"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateMountingBracketInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    leg_thickness_cm: float
    hole_diameter_cm: float
    hole_center_x_cm: float
    hole_center_y_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateMountingBracketInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for mounting_bracket in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        leg_thickness_cm = _require_positive_number(payload.get("leg_thickness_cm", thickness_cm), "leg_thickness_cm")
        if leg_thickness_cm >= width_cm or leg_thickness_cm >= height_cm:
            raise ValueError("leg_thickness_cm must be smaller than width_cm and height_cm.")
        hole_diameter_cm = _require_positive_number(payload["hole_diameter_cm"], "hole_diameter_cm")
        hole_center_x_cm = float(payload["hole_center_x_cm"])
        hole_center_y_cm = float(payload["hole_center_y_cm"])
        hole_radius_cm = hole_diameter_cm / 2.0
        if not (hole_radius_cm < hole_center_x_cm < width_cm - hole_radius_cm):
            raise ValueError("hole_center_x_cm must keep the hole inside the sketch bounds.")
        if not (hole_radius_cm < hole_center_y_cm < height_cm - hole_radius_cm):
            raise ValueError("hole_center_y_cm must keep the hole inside the sketch bounds.")
        in_vertical_leg = hole_center_x_cm + hole_radius_cm <= leg_thickness_cm
        in_horizontal_leg = hole_center_y_cm - hole_radius_cm <= leg_thickness_cm
        if not (in_vertical_leg or in_horizontal_leg):
            raise ValueError("hole center must land fully inside one L-bracket leg.")
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            leg_thickness_cm=leg_thickness_cm,
            hole_diameter_cm=hole_diameter_cm,
            hole_center_x_cm=hole_center_x_cm,
            hole_center_y_cm=hole_center_y_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Mounting Bracket Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Mounting Bracket"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateTwoHoleMountingBracketInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    leg_thickness_cm: float
    hole_diameter_cm: float
    first_hole_center_x_cm: float
    first_hole_center_y_cm: float
    second_hole_center_x_cm: float
    second_hole_center_y_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateTwoHoleMountingBracketInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for two_hole_mounting_bracket in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        leg_thickness_cm = _require_positive_number(payload.get("leg_thickness_cm", thickness_cm), "leg_thickness_cm")
        if leg_thickness_cm >= width_cm or leg_thickness_cm >= height_cm:
            raise ValueError("leg_thickness_cm must be smaller than width_cm and height_cm.")
        hole_diameter_cm = _require_positive_number(payload["hole_diameter_cm"], "hole_diameter_cm")
        first_hole_center_x_cm = float(payload["first_hole_center_x_cm"])
        first_hole_center_y_cm = float(payload["first_hole_center_y_cm"])
        second_hole_center_x_cm = float(payload["second_hole_center_x_cm"])
        second_hole_center_y_cm = float(payload["second_hole_center_y_cm"])
        hole_radius_cm = hole_diameter_cm / 2.0
        validate_hole_position(
            width_cm,
            height_cm,
            leg_thickness_cm,
            hole_radius_cm,
            first_hole_center_x_cm,
            first_hole_center_y_cm,
            "first_hole",
        )
        validate_hole_position(
            width_cm,
            height_cm,
            leg_thickness_cm,
            hole_radius_cm,
            second_hole_center_x_cm,
            second_hole_center_y_cm,
            "second_hole",
        )
        distance = math.hypot(
            second_hole_center_x_cm - first_hole_center_x_cm,
            second_hole_center_y_cm - first_hole_center_y_cm,
        )
        if distance < 2.0 * hole_radius_cm:
            raise ValueError("The two holes overlap; increase the distance between hole centers or reduce hole_diameter_cm.")
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            leg_thickness_cm=leg_thickness_cm,
            hole_diameter_cm=hole_diameter_cm,
            first_hole_center_x_cm=first_hole_center_x_cm,
            first_hole_center_y_cm=first_hole_center_y_cm,
            second_hole_center_x_cm=second_hole_center_x_cm,
            second_hole_center_y_cm=second_hole_center_y_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Two-Hole Mounting Bracket Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Two-Hole Mounting Bracket"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateTwoHolePlateInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    hole_diameter_cm: float
    edge_offset_x_cm: float
    hole_center_y_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateTwoHolePlateInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for two_hole_plate in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        hole_diameter_cm = _require_positive_number(payload["hole_diameter_cm"], "hole_diameter_cm")
        edge_offset_x_cm = float(payload["edge_offset_x_cm"])
        hole_center_y_cm = float(payload["hole_center_y_cm"])
        hole_radius_cm = hole_diameter_cm / 2.0
        if not (hole_radius_cm < edge_offset_x_cm <= (width_cm / 2.0) - hole_radius_cm):
            raise ValueError(
                "edge_offset_x_cm must keep both mirrored holes inside the sketch bounds and leave room for both holes."
            )
        validate_rectangular_hole_position(
            width_cm=width_cm,
            height_cm=height_cm,
            hole_radius_cm=hole_radius_cm,
            center_x_cm=edge_offset_x_cm,
            center_y_cm=hole_center_y_cm,
            label="first_hole",
        )
        validate_rectangular_hole_position(
            width_cm=width_cm,
            height_cm=height_cm,
            hole_radius_cm=hole_radius_cm,
            center_x_cm=width_cm - edge_offset_x_cm,
            center_y_cm=hole_center_y_cm,
            label="second_hole",
        )
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            hole_diameter_cm=hole_diameter_cm,
            edge_offset_x_cm=edge_offset_x_cm,
            hole_center_y_cm=hole_center_y_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Two-Hole Plate Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Two-Hole Plate"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateFourHoleMountingPlateInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    hole_diameter_cm: float
    edge_offset_x_cm: float
    edge_offset_y_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateFourHoleMountingPlateInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for four_hole_mounting_plate in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        hole_diameter_cm = _require_positive_number(payload["hole_diameter_cm"], "hole_diameter_cm")
        edge_offset_x_cm = float(payload["edge_offset_x_cm"])
        edge_offset_y_cm = float(payload["edge_offset_y_cm"])
        hole_radius_cm = hole_diameter_cm / 2.0
        if not (hole_radius_cm < edge_offset_x_cm <= (width_cm / 2.0) - hole_radius_cm):
            raise ValueError(
                "edge_offset_x_cm must keep both mirrored hole columns inside the sketch bounds and leave room for both columns."
            )
        if not (hole_radius_cm < edge_offset_y_cm <= (height_cm / 2.0) - hole_radius_cm):
            raise ValueError(
                "edge_offset_y_cm must keep both mirrored hole rows inside the sketch bounds and leave room for both rows."
            )
        hole_centers = (
            (edge_offset_x_cm, edge_offset_y_cm, "bottom_left_hole"),
            (width_cm - edge_offset_x_cm, edge_offset_y_cm, "bottom_right_hole"),
            (edge_offset_x_cm, height_cm - edge_offset_y_cm, "top_left_hole"),
            (width_cm - edge_offset_x_cm, height_cm - edge_offset_y_cm, "top_right_hole"),
        )
        for center_x_cm, center_y_cm, label in hole_centers:
            validate_rectangular_hole_position(
                width_cm=width_cm,
                height_cm=height_cm,
                hole_radius_cm=hole_radius_cm,
                center_x_cm=center_x_cm,
                center_y_cm=center_y_cm,
                label=label,
            )
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            hole_diameter_cm=hole_diameter_cm,
            edge_offset_x_cm=edge_offset_x_cm,
            edge_offset_y_cm=edge_offset_y_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(
                payload.get("sketch_name", "Four-Hole Mounting Plate Sketch"),
                "sketch_name",
            ),
            body_name=_require_non_empty_string(
                payload.get("body_name", "Four-Hole Mounting Plate"),
                "body_name",
            ),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateSlottedMountingPlateInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    hole_diameter_cm: float
    edge_offset_x_cm: float
    edge_offset_y_cm: float
    slot_length_cm: float
    slot_width_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateSlottedMountingPlateInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for slotted_mounting_plate in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        hole_diameter_cm = _require_positive_number(payload["hole_diameter_cm"], "hole_diameter_cm")
        edge_offset_x_cm = float(payload["edge_offset_x_cm"])
        edge_offset_y_cm = float(payload["edge_offset_y_cm"])
        slot_length_cm = _require_positive_number(payload["slot_length_cm"], "slot_length_cm")
        slot_width_cm = _require_positive_number(payload["slot_width_cm"], "slot_width_cm")
        if slot_length_cm <= slot_width_cm:
            raise ValueError("slot_length_cm must be greater than slot_width_cm.")
        hole_radius_cm = hole_diameter_cm / 2.0
        if not (hole_radius_cm < edge_offset_x_cm <= (width_cm / 2.0) - hole_radius_cm):
            raise ValueError(
                "edge_offset_x_cm must keep both mirrored hole columns inside the sketch bounds and leave room for both columns."
            )
        if not (hole_radius_cm < edge_offset_y_cm <= (height_cm / 2.0) - hole_radius_cm):
            raise ValueError(
                "edge_offset_y_cm must keep both mirrored hole rows inside the sketch bounds and leave room for both rows."
            )
        slot_center_x_cm = width_cm / 2.0
        slot_center_y_cm = height_cm / 2.0
        validate_slot_position(
            width_cm=width_cm,
            height_cm=height_cm,
            slot_length_cm=slot_length_cm,
            slot_width_cm=slot_width_cm,
            center_x_cm=slot_center_x_cm,
            center_y_cm=slot_center_y_cm,
        )
        hole_centers = (
            (edge_offset_x_cm, edge_offset_y_cm, "bottom_left_hole"),
            (width_cm - edge_offset_x_cm, edge_offset_y_cm, "bottom_right_hole"),
            (edge_offset_x_cm, height_cm - edge_offset_y_cm, "top_left_hole"),
            (width_cm - edge_offset_x_cm, height_cm - edge_offset_y_cm, "top_right_hole"),
        )
        for center_x_cm, center_y_cm, label in hole_centers:
            validate_rectangular_hole_position(
                width_cm=width_cm,
                height_cm=height_cm,
                hole_radius_cm=hole_radius_cm,
                center_x_cm=center_x_cm,
                center_y_cm=center_y_cm,
                label=label,
            )
            validate_slot_hole_clearance(
                hole_center_x_cm=center_x_cm,
                hole_center_y_cm=center_y_cm,
                hole_radius_cm=hole_radius_cm,
                slot_center_x_cm=slot_center_x_cm,
                slot_center_y_cm=slot_center_y_cm,
                slot_length_cm=slot_length_cm,
                slot_width_cm=slot_width_cm,
                label=label,
            )
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            hole_diameter_cm=hole_diameter_cm,
            edge_offset_x_cm=edge_offset_x_cm,
            edge_offset_y_cm=edge_offset_y_cm,
            slot_length_cm=slot_length_cm,
            slot_width_cm=slot_width_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(
                payload.get("sketch_name", "Slotted Mounting Plate Sketch"),
                "sketch_name",
            ),
            body_name=_require_non_empty_string(
                payload.get("body_name", "Slotted Mounting Plate"),
                "body_name",
            ),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateSlottedMountInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    slot_length_cm: float
    slot_width_cm: float
    slot_center_x_cm: float
    slot_center_y_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateSlottedMountInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for slotted_mount in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        slot_length_cm = _require_positive_number(payload["slot_length_cm"], "slot_length_cm")
        slot_width_cm = _require_positive_number(payload["slot_width_cm"], "slot_width_cm")
        if slot_length_cm <= slot_width_cm:
            raise ValueError("slot_length_cm must be greater than slot_width_cm.")
        slot_center_x_cm = float(payload["slot_center_x_cm"])
        slot_center_y_cm = float(payload["slot_center_y_cm"])
        validate_slot_position(
            width_cm=width_cm,
            height_cm=height_cm,
            slot_length_cm=slot_length_cm,
            slot_width_cm=slot_width_cm,
            center_x_cm=slot_center_x_cm,
            center_y_cm=slot_center_y_cm,
        )
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            slot_length_cm=slot_length_cm,
            slot_width_cm=slot_width_cm,
            slot_center_x_cm=slot_center_x_cm,
            slot_center_y_cm=slot_center_y_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Slotted Mount Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Slotted Mount"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateCounterboredPlateInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    hole_diameter_cm: float
    hole_center_x_cm: float
    hole_center_y_cm: float
    counterbore_diameter_cm: float
    counterbore_depth_cm: float
    plane: str
    sketch_name: str
    hole_sketch_name: str
    counterbore_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateCounterboredPlateInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for counterbored_plate in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        hole_diameter_cm = _require_positive_number(payload["hole_diameter_cm"], "hole_diameter_cm")
        counterbore_diameter_cm = _require_positive_number(payload["counterbore_diameter_cm"], "counterbore_diameter_cm")
        counterbore_depth_cm = _require_positive_number(payload["counterbore_depth_cm"], "counterbore_depth_cm")
        if counterbore_diameter_cm <= hole_diameter_cm:
            raise ValueError("counterbore_diameter_cm must be greater than hole_diameter_cm.")
        if counterbore_depth_cm >= thickness_cm:
            raise ValueError("counterbore_depth_cm must be smaller than thickness_cm.")
        hole_center_x_cm = float(payload["hole_center_x_cm"])
        hole_center_y_cm = float(payload["hole_center_y_cm"])
        validate_rectangular_hole_position(
            width_cm=width_cm,
            height_cm=height_cm,
            hole_radius_cm=hole_diameter_cm / 2.0,
            center_x_cm=hole_center_x_cm,
            center_y_cm=hole_center_y_cm,
            label="hole",
        )
        validate_rectangular_hole_position(
            width_cm=width_cm,
            height_cm=height_cm,
            hole_radius_cm=counterbore_diameter_cm / 2.0,
            center_x_cm=hole_center_x_cm,
            center_y_cm=hole_center_y_cm,
            label="counterbore",
        )
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            hole_diameter_cm=hole_diameter_cm,
            hole_center_x_cm=hole_center_x_cm,
            hole_center_y_cm=hole_center_y_cm,
            counterbore_diameter_cm=counterbore_diameter_cm,
            counterbore_depth_cm=counterbore_depth_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Counterbored Plate Sketch"), "sketch_name"),
            hole_sketch_name=_require_non_empty_string(payload.get("hole_sketch_name", "Hole Sketch"), "hole_sketch_name"),
            counterbore_sketch_name=_require_non_empty_string(
                payload.get("counterbore_sketch_name", "Counterbore Sketch"),
                "counterbore_sketch_name",
            ),
            body_name=_require_non_empty_string(payload.get("body_name", "Counterbored Plate"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreatePlateWithHoleInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    hole_diameter_cm: float
    hole_center_x_cm: float
    hole_center_y_cm: float
    plane: str
    sketch_name: str
    hole_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreatePlateWithHoleInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for plate_with_hole in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        hole_diameter_cm = _require_positive_number(payload["hole_diameter_cm"], "hole_diameter_cm")
        hole_center_x_cm = float(payload["hole_center_x_cm"])
        hole_center_y_cm = float(payload["hole_center_y_cm"])
        hole_radius_cm = hole_diameter_cm / 2.0
        validate_rectangular_hole_position(
            width_cm=width_cm,
            height_cm=height_cm,
            hole_radius_cm=hole_radius_cm,
            center_x_cm=hole_center_x_cm,
            center_y_cm=hole_center_y_cm,
            label="hole",
        )
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            hole_diameter_cm=hole_diameter_cm,
            hole_center_x_cm=hole_center_x_cm,
            hole_center_y_cm=hole_center_y_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Plate Sketch"), "sketch_name"),
            hole_sketch_name=_require_non_empty_string(payload.get("hole_sketch_name", "Hole Sketch"), "hole_sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Plate"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateRecessedMountInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    recess_width_cm: float
    recess_height_cm: float
    recess_depth_cm: float
    recess_origin_x_cm: float
    recess_origin_y_cm: float
    plane: str
    sketch_name: str
    recess_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateRecessedMountInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for recessed_mount in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        recess_width_cm = _require_positive_number(payload["recess_width_cm"], "recess_width_cm")
        recess_height_cm = _require_positive_number(payload["recess_height_cm"], "recess_height_cm")
        recess_depth_cm = _require_positive_number(payload["recess_depth_cm"], "recess_depth_cm")
        if recess_depth_cm >= thickness_cm:
            raise ValueError("recess_depth_cm must be smaller than thickness_cm.")
        recess_origin_x_cm = float(payload["recess_origin_x_cm"])
        recess_origin_y_cm = float(payload["recess_origin_y_cm"])
        validate_rectangle_placement(
            outer_width_cm=width_cm,
            outer_height_cm=height_cm,
            inner_width_cm=recess_width_cm,
            inner_height_cm=recess_height_cm,
            origin_x_cm=recess_origin_x_cm,
            origin_y_cm=recess_origin_y_cm,
            label="recess",
        )
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            recess_width_cm=recess_width_cm,
            recess_height_cm=recess_height_cm,
            recess_depth_cm=recess_depth_cm,
            recess_origin_x_cm=recess_origin_x_cm,
            recess_origin_y_cm=recess_origin_y_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Recessed Mount Sketch"), "sketch_name"),
            recess_sketch_name=_require_non_empty_string(payload.get("recess_sketch_name", "Recess Sketch"), "recess_sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Recessed Mount"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateSimpleEnclosureInput:
    width_cm: float
    depth_cm: float
    height_cm: float
    wall_thickness_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateSimpleEnclosureInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for simple_enclosure in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        depth_cm = _require_positive_number(payload["depth_cm"], "depth_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        wall_thickness_cm = _require_positive_number(payload["wall_thickness_cm"], "wall_thickness_cm")
        if wall_thickness_cm * 2.0 >= width_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner width.")
        if wall_thickness_cm * 2.0 >= depth_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner depth.")
        if wall_thickness_cm >= height_cm:
            raise ValueError("wall_thickness_cm must be smaller than height_cm.")
        return cls(
            width_cm=width_cm,
            depth_cm=depth_cm,
            height_cm=height_cm,
            wall_thickness_cm=wall_thickness_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Simple Enclosure Sketch"), "sketch_name"),
            body_name=_require_non_empty_string(payload.get("body_name", "Simple Enclosure"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateOpenBoxBodyInput:
    width_cm: float
    depth_cm: float
    height_cm: float
    wall_thickness_cm: float
    floor_thickness_cm: float
    plane: str
    sketch_name: str
    cavity_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateOpenBoxBodyInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for open_box_body in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        depth_cm = _require_positive_number(payload["depth_cm"], "depth_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        wall_thickness_cm = _require_positive_number(payload["wall_thickness_cm"], "wall_thickness_cm")
        floor_thickness_cm = _require_positive_number(payload["floor_thickness_cm"], "floor_thickness_cm")
        if wall_thickness_cm * 2.0 >= width_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner cavity width.")
        if wall_thickness_cm * 2.0 >= depth_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner cavity depth.")
        if floor_thickness_cm >= height_cm:
            raise ValueError("floor_thickness_cm must be smaller than height_cm.")
        return cls(
            width_cm=width_cm,
            depth_cm=depth_cm,
            height_cm=height_cm,
            wall_thickness_cm=wall_thickness_cm,
            floor_thickness_cm=floor_thickness_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Open Box Body Sketch"), "sketch_name"),
            cavity_sketch_name=_require_non_empty_string(
                payload.get("cavity_sketch_name", "Cavity Sketch"),
                "cavity_sketch_name",
            ),
            body_name=_require_non_empty_string(payload.get("body_name", "Open Box Body"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateLidForBoxInput:
    width_cm: float
    depth_cm: float
    lid_thickness_cm: float
    rim_depth_cm: float
    wall_thickness_cm: float
    plane: str
    sketch_name: str
    rim_cut_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateLidForBoxInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for lid_for_box in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        depth_cm = _require_positive_number(payload["depth_cm"], "depth_cm")
        lid_thickness_cm = _require_positive_number(payload["lid_thickness_cm"], "lid_thickness_cm")
        rim_depth_cm = _require_positive_number(payload["rim_depth_cm"], "rim_depth_cm")
        wall_thickness_cm = _require_positive_number(payload["wall_thickness_cm"], "wall_thickness_cm")
        if wall_thickness_cm * 2.0 >= width_cm:
            raise ValueError("wall_thickness_cm must leave a positive rim opening width.")
        if wall_thickness_cm * 2.0 >= depth_cm:
            raise ValueError("wall_thickness_cm must leave a positive rim opening depth.")
        return cls(
            width_cm=width_cm,
            depth_cm=depth_cm,
            lid_thickness_cm=lid_thickness_cm,
            rim_depth_cm=rim_depth_cm,
            wall_thickness_cm=wall_thickness_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(payload.get("sketch_name", "Lid Sketch"), "sketch_name"),
            rim_cut_sketch_name=_require_non_empty_string(
                payload.get("rim_cut_sketch_name", "Rim Cut Sketch"),
                "rim_cut_sketch_name",
            ),
            body_name=_require_non_empty_string(payload.get("body_name", "Box Lid"), "body_name"),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateBoxWithLidInput:
    width_cm: float
    depth_cm: float
    box_height_cm: float
    wall_thickness_cm: float
    floor_thickness_cm: float
    lid_thickness_cm: float
    rim_depth_cm: float
    clearance_cm: float
    output_path_box: str
    output_path_lid: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateBoxWithLidInput":
        output_path_box = _validate_export_path(payload["output_path_box"])
        output_path_lid = _validate_export_path(payload["output_path_lid"])
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        depth_cm = _require_positive_number(payload["depth_cm"], "depth_cm")
        box_height_cm = _require_positive_number(payload["box_height_cm"], "box_height_cm")
        wall_thickness_cm = _require_positive_number(payload["wall_thickness_cm"], "wall_thickness_cm")
        floor_thickness_cm = _require_positive_number(payload["floor_thickness_cm"], "floor_thickness_cm")
        lid_thickness_cm = _require_positive_number(payload["lid_thickness_cm"], "lid_thickness_cm")
        rim_depth_cm = _require_positive_number(payload["rim_depth_cm"], "rim_depth_cm")
        clearance_cm = _require_positive_number(payload["clearance_cm"], "clearance_cm")
        if wall_thickness_cm * 2.0 >= width_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner cavity width.")
        if wall_thickness_cm * 2.0 >= depth_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner cavity depth.")
        if floor_thickness_cm >= box_height_cm:
            raise ValueError("floor_thickness_cm must be smaller than box_height_cm.")
        if rim_depth_cm >= box_height_cm - floor_thickness_cm:
            raise ValueError("rim_depth_cm must be smaller than the box cavity height.")
        if clearance_cm >= wall_thickness_cm:
            raise ValueError("clearance_cm must be smaller than wall_thickness_cm so the rim wall has positive thickness.")
        return cls(
            width_cm=width_cm,
            depth_cm=depth_cm,
            box_height_cm=box_height_cm,
            wall_thickness_cm=wall_thickness_cm,
            floor_thickness_cm=floor_thickness_cm,
            lid_thickness_cm=lid_thickness_cm,
            rim_depth_cm=rim_depth_cm,
            clearance_cm=clearance_cm,
            output_path_box=output_path_box,
            output_path_lid=output_path_lid,
        )


@dataclass(frozen=True)
class VerificationSnapshot:
    body_count: int
    sketch_count: int
    export_count: int

    @classmethod
    def from_scene(cls, scene: dict) -> "VerificationSnapshot":
        return cls(
            body_count=len(scene.get("bodies", [])),
            sketch_count=len(scene.get("sketches", [])),
            export_count=len(scene.get("exports", [])),
        )
