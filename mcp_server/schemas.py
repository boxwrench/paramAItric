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
class CreateShaftCouplerInput:
    outer_diameter_cm: float
    length_cm: float
    bore_diameter_cm: float
    pin_hole_diameter_cm: float
    pin_hole_offset_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateShaftCouplerInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for shaft_coupler in the current validated scope.")
        outer_diameter_cm = _require_positive_number(payload["outer_diameter_cm"], "outer_diameter_cm")
        length_cm = _require_positive_number(payload["length_cm"], "length_cm")
        bore_diameter_cm = _require_positive_number(payload["bore_diameter_cm"], "bore_diameter_cm")
        pin_hole_diameter_cm = _require_positive_number(payload["pin_hole_diameter_cm"], "pin_hole_diameter_cm")
        pin_hole_offset_cm = _require_positive_number(payload["pin_hole_offset_cm"], "pin_hole_offset_cm")
        if bore_diameter_cm >= outer_diameter_cm:
            raise ValueError("bore_diameter_cm must be smaller than outer_diameter_cm.")
        if pin_hole_diameter_cm >= outer_diameter_cm:
            raise ValueError("pin_hole_diameter_cm must be smaller than outer_diameter_cm.")
        if pin_hole_offset_cm - pin_hole_diameter_cm / 2.0 < 0:
            raise ValueError("pin_hole_offset_cm must place the hole fully inside the coupler length.")
        if pin_hole_offset_cm + pin_hole_diameter_cm / 2.0 > length_cm:
            raise ValueError("pin_hole_offset_cm must place the hole fully inside the coupler length.")
        return cls(
            outer_diameter_cm=outer_diameter_cm,
            length_cm=length_cm,
            bore_diameter_cm=bore_diameter_cm,
            pin_hole_diameter_cm=pin_hole_diameter_cm,
            pin_hole_offset_cm=pin_hole_offset_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(
                payload.get("sketch_name", "Shaft Coupler Sketch"), "sketch_name"
            ),
            body_name=_require_non_empty_string(
                payload.get("body_name", "Shaft Coupler"), "body_name"
            ),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateProjectBoxWithStandoffsInput:
    width_cm: float
    depth_cm: float
    height_cm: float
    wall_thickness_cm: float
    standoff_diameter_cm: float
    standoff_height_cm: float
    standoff_inset_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateProjectBoxWithStandoffsInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for project_box_with_standoffs in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        depth_cm = _require_positive_number(payload["depth_cm"], "depth_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        wall_thickness_cm = _require_positive_number(payload["wall_thickness_cm"], "wall_thickness_cm")
        standoff_diameter_cm = _require_positive_number(payload["standoff_diameter_cm"], "standoff_diameter_cm")
        standoff_height_cm = _require_positive_number(payload["standoff_height_cm"], "standoff_height_cm")
        standoff_inset_cm = _require_positive_number(payload["standoff_inset_cm"], "standoff_inset_cm")
        if wall_thickness_cm * 2.0 >= width_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner width.")
        if wall_thickness_cm * 2.0 >= depth_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner depth.")
        if wall_thickness_cm >= height_cm:
            raise ValueError("wall_thickness_cm must be smaller than height_cm.")
        inner_width_cm = width_cm - wall_thickness_cm * 2.0
        inner_depth_cm = depth_cm - wall_thickness_cm * 2.0
        inner_height_cm = height_cm - wall_thickness_cm
        if standoff_height_cm >= inner_height_cm:
            raise ValueError("standoff_height_cm must be smaller than the inner cavity height.")
        standoff_radius_cm = standoff_diameter_cm / 2.0
        if standoff_inset_cm - standoff_radius_cm < 0:
            raise ValueError("standoff_inset_cm must be at least half the standoff diameter.")
        if standoff_inset_cm + standoff_radius_cm > inner_width_cm / 2.0:
            raise ValueError("standoff_inset_cm places the standoff outside the inner width.")
        if standoff_inset_cm + standoff_radius_cm > inner_depth_cm / 2.0:
            raise ValueError("standoff_inset_cm places the standoff outside the inner depth.")
        return cls(
            width_cm=width_cm,
            depth_cm=depth_cm,
            height_cm=height_cm,
            wall_thickness_cm=wall_thickness_cm,
            standoff_diameter_cm=standoff_diameter_cm,
            standoff_height_cm=standoff_height_cm,
            standoff_inset_cm=standoff_inset_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(
                payload.get("sketch_name", "Project Box Sketch"), "sketch_name"
            ),
            body_name=_require_non_empty_string(
                payload.get("body_name", "Project Box"), "body_name"
            ),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateTriangularBracketInput:
    base_width_cm: float
    height_cm: float
    thickness_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateTriangularBracketInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for triangular_bracket in the current validated scope.")
        base_width_cm = _require_positive_number(payload["base_width_cm"], "base_width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        return cls(
            base_width_cm=base_width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(
                payload.get("sketch_name", "Triangular Bracket Sketch"),
                "sketch_name",
            ),
            body_name=_require_non_empty_string(
                payload.get("body_name", "Triangular Bracket"),
                "body_name",
            ),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateLBracketWithGussetInput:
    width_cm: float
    height_cm: float
    leg_thickness_cm: float
    thickness_cm: float
    gusset_size_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateLBracketWithGussetInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane not in ("xy", "xz", "yz"):
            raise ValueError("plane must be xy, xz, or yz.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        leg_thickness_cm = _require_positive_number(payload["leg_thickness_cm"], "leg_thickness_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        gusset_size_cm = _require_positive_number(payload["gusset_size_cm"], "gusset_size_cm")
        if leg_thickness_cm >= width_cm:
            raise ValueError("leg_thickness_cm must be smaller than width_cm.")
        if leg_thickness_cm >= height_cm:
            raise ValueError("leg_thickness_cm must be smaller than height_cm.")
        # gusset must fit within the inner cavity of the L
        inner_width = width_cm - leg_thickness_cm
        inner_height = height_cm - leg_thickness_cm
        if gusset_size_cm > inner_width:
            raise ValueError(
                "gusset_size_cm must not exceed inner cavity width (width_cm - leg_thickness_cm)."
            )
        if gusset_size_cm > inner_height:
            raise ValueError(
                "gusset_size_cm must not exceed inner cavity height (height_cm - leg_thickness_cm)."
            )
        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            leg_thickness_cm=leg_thickness_cm,
            thickness_cm=thickness_cm,
            gusset_size_cm=gusset_size_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(
                payload.get("sketch_name", "L-Bracket With Gusset Sketch"),
                "sketch_name",
            ),
            body_name=_require_non_empty_string(
                payload.get("body_name", "L-Bracket With Gusset"),
                "body_name",
            ),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateCableGlandPlateInput:
    width_cm: float
    height_cm: float
    thickness_cm: float
    center_hole_diameter_cm: float
    mounting_hole_diameter_cm: float
    edge_offset_x_cm: float
    edge_offset_y_cm: float
    plane: str
    sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateCableGlandPlateInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for cable_gland_plate in the current validated scope.")
        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        center_hole_diameter_cm = _require_positive_number(payload["center_hole_diameter_cm"], "center_hole_diameter_cm")
        mounting_hole_diameter_cm = _require_positive_number(payload["mounting_hole_diameter_cm"], "mounting_hole_diameter_cm")
        edge_offset_x_cm = float(payload["edge_offset_x_cm"])
        edge_offset_y_cm = float(payload["edge_offset_y_cm"])

        center_hole_radius = center_hole_diameter_cm / 2.0
        mounting_hole_radius = mounting_hole_diameter_cm / 2.0

        # Center hole must fit within plate
        if center_hole_diameter_cm >= width_cm or center_hole_diameter_cm >= height_cm:
            raise ValueError("center_hole_diameter_cm must be smaller than plate width and height.")

        # Mounting holes must fit within plate
        mounting_hole_centers = (
            (edge_offset_x_cm, edge_offset_y_cm, "bottom_left_hole"),
            (width_cm - edge_offset_x_cm, edge_offset_y_cm, "bottom_right_hole"),
            (edge_offset_x_cm, height_cm - edge_offset_y_cm, "top_left_hole"),
            (width_cm - edge_offset_x_cm, height_cm - edge_offset_y_cm, "top_right_hole"),
        )
        if not (mounting_hole_radius < edge_offset_x_cm <= (width_cm / 2.0) - mounting_hole_radius):
            raise ValueError(
                "edge_offset_x_cm must keep both mirrored hole columns inside the sketch bounds."
            )
        if not (mounting_hole_radius < edge_offset_y_cm <= (height_cm / 2.0) - mounting_hole_radius):
            raise ValueError(
                "edge_offset_y_cm must keep both mirrored hole rows inside the sketch bounds."
            )
        for center_x_cm, center_y_cm, label in mounting_hole_centers:
            validate_rectangular_hole_position(
                width_cm=width_cm,
                height_cm=height_cm,
                hole_radius_cm=mounting_hole_radius,
                center_x_cm=center_x_cm,
                center_y_cm=center_y_cm,
                label=label,
            )

        # Center hole must not overlap any mounting hole
        plate_center_x = width_cm / 2.0
        plate_center_y = height_cm / 2.0
        min_separation = center_hole_radius + mounting_hole_radius
        for cx, cy, label in mounting_hole_centers:
            dist = ((plate_center_x - cx) ** 2 + (plate_center_y - cy) ** 2) ** 0.5
            if dist < min_separation:
                raise ValueError(
                    f"center hole overlaps {label}: increase edge offsets or reduce hole diameters."
                )

        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            center_hole_diameter_cm=center_hole_diameter_cm,
            mounting_hole_diameter_cm=mounting_hole_diameter_cm,
            edge_offset_x_cm=edge_offset_x_cm,
            edge_offset_y_cm=edge_offset_y_cm,
            plane=plane,
            sketch_name=_require_non_empty_string(
                payload.get("sketch_name", "Cable Gland Plate Sketch"),
                "sketch_name",
            ),
            body_name=_require_non_empty_string(
                payload.get("body_name", "Cable Gland Plate"),
                "body_name",
            ),
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateStrutChannelBracketInput:
    """Sheet metal L-bracket with taper and mounting holes.
    
    Models a bent sheet metal bracket with:
    - Horizontal mounting leg (full width)
    - Vertical leg with taper
    - Four through-holes (2 on horizontal, 2 on vertical)
    - Outer bend radius fillet
    """

    width_cm: float  # Overall width (extrusion length) - horizontal leg
    height_cm: float  # Vertical leg height
    depth_cm: float  # Bracket depth (perpendicular to L-profile)
    thickness_cm: float  # Sheet metal thickness
    hole_diameter_cm: float
    hole_edge_offset_cm: float  # Hole center to nearest edge
    hole_spacing_cm: float  # Center-to-center spacing for paired holes
    taper_angle_deg: float  # Taper angle for vertical leg (0 = no taper)
    bend_fillet_radius_cm: float  # Outer corner fillet radius
    plane: str
    cross_section_sketch_name: str
    taper_front_sketch_name: str
    taper_back_sketch_name: str
    horiz_hole_first_sketch_name: str
    horiz_hole_second_sketch_name: str
    vert_hole_first_sketch_name: str
    vert_hole_second_sketch_name: str
    body_name: str
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateStrutChannelBracketInput":
        output_path = _validate_export_path(payload["output_path"])
        plane = _require_non_empty_string(payload.get("plane", "xy"), "plane").lower()
        if plane != "xy":
            raise ValueError("plane must be xy for strut_channel_bracket in the current validated scope.")

        width_cm = _require_positive_number(payload["width_cm"], "width_cm")
        height_cm = _require_positive_number(payload["height_cm"], "height_cm")
        depth_cm = _require_positive_number(payload["depth_cm"], "depth_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        hole_diameter_cm = _require_positive_number(payload["hole_diameter_cm"], "hole_diameter_cm")
        hole_edge_offset_cm = _require_positive_number(payload["hole_edge_offset_cm"], "hole_edge_offset_cm")
        hole_spacing_cm = _require_positive_number(payload["hole_spacing_cm"], "hole_spacing_cm")
        taper_angle_deg = _require_non_negative_number(
            payload.get("taper_angle_deg", 0.0), "taper_angle_deg"
        )
        bend_fillet_radius_cm = _require_non_negative_number(
            payload.get("bend_fillet_radius_cm", thickness_cm * 0.5), "bend_fillet_radius_cm"
        )

        # Validation: thickness must be less than depth and height
        if thickness_cm >= depth_cm:
            raise ValueError("thickness_cm must be less than depth_cm.")
        if thickness_cm >= height_cm:
            raise ValueError("thickness_cm must be less than height_cm.")

        # Validation: hole diameter must fit within the leg dimensions
        # Horizontal leg holes go through thickness (depth_cm dimension)
        # Vertical leg holes go through thickness (depth_cm dimension)
        if hole_diameter_cm > depth_cm:
            raise ValueError("hole_diameter_cm must be less than depth_cm to fit through the leg.")

        # Validation: hole edge offset must leave room for hole + spacing
        hole_radius = hole_diameter_cm / 2.0
        min_edge_offset = hole_radius + 0.1  # Small margin
        if hole_edge_offset_cm < min_edge_offset:
            raise ValueError(f"hole_edge_offset_cm must be at least {min_edge_offset:.3f} cm (hole radius + margin).")

        # Validation: horizontal holes must fit within width
        second_hole_x = width_cm - hole_edge_offset_cm
        first_hole_x = hole_edge_offset_cm
        if second_hole_x - first_hole_x < hole_spacing_cm:
            raise ValueError("hole_spacing_cm is too large for the given width and edge offset.")

        # Validation: vertical holes must fit within height
        second_hole_y = hole_edge_offset_cm + hole_spacing_cm
        if second_hole_y + hole_radius > height_cm:
            raise ValueError("hole_spacing_cm places vertical holes outside height bounds.")

        # Validation: taper angle reasonable (0-30 degrees)
        if taper_angle_deg > 30.0:
            raise ValueError("taper_angle_deg must be 30 degrees or less.")

        return cls(
            width_cm=width_cm,
            height_cm=height_cm,
            depth_cm=depth_cm,
            thickness_cm=thickness_cm,
            hole_diameter_cm=hole_diameter_cm,
            hole_edge_offset_cm=hole_edge_offset_cm,
            hole_spacing_cm=hole_spacing_cm,
            taper_angle_deg=taper_angle_deg,
            bend_fillet_radius_cm=bend_fillet_radius_cm,
            plane=plane,
            cross_section_sketch_name=_require_non_empty_string(
                payload.get("cross_section_sketch_name", "Cross-Section Sketch"),
                "cross_section_sketch_name",
            ),
            taper_front_sketch_name=_require_non_empty_string(
                payload.get("taper_front_sketch_name", "Taper Front Sketch"),
                "taper_front_sketch_name",
            ),
            taper_back_sketch_name=_require_non_empty_string(
                payload.get("taper_back_sketch_name", "Taper Back Sketch"),
                "taper_back_sketch_name",
            ),
            horiz_hole_first_sketch_name=_require_non_empty_string(
                payload.get("horiz_hole_first_sketch_name", "Horizontal Hole Left Sketch"),
                "horiz_hole_first_sketch_name",
            ),
            horiz_hole_second_sketch_name=_require_non_empty_string(
                payload.get("horiz_hole_second_sketch_name", "Horizontal Hole Right Sketch"),
                "horiz_hole_second_sketch_name",
            ),
            vert_hole_first_sketch_name=_require_non_empty_string(
                payload.get("vert_hole_first_sketch_name", "Vertical Hole Bottom Sketch"),
                "vert_hole_first_sketch_name",
            ),
            vert_hole_second_sketch_name=_require_non_empty_string(
                payload.get("vert_hole_second_sketch_name", "Vertical Hole Top Sketch"),
                "vert_hole_second_sketch_name",
            ),
            body_name=_require_non_empty_string(
                payload.get("body_name", "Strut Channel Bracket"),
                "body_name",
            ),
            output_path=output_path,
        )


@dataclass(frozen=True)
class VerificationSnapshot:
    body_count: int
    sketch_count: int
    export_count: int
    bodies_info: list[dict] | None = None

    @classmethod
    def from_scene(cls, scene: dict) -> "VerificationSnapshot":
        bodies = scene.get("bodies", [])
        return cls(
            body_count=len(bodies),
            sketch_count=len(scene.get("sketches", [])),
            export_count=len(scene.get("exports", [])),
            bodies_info=bodies,
        )

@dataclass(frozen=True)
class StartFreeformSessionInput:
    design_name: str
    target_features: list[str] | None = None

    @classmethod
    def from_payload(cls, payload: dict) -> "StartFreeformSessionInput":
        target_features = payload.get("target_features")
        if target_features is not None:
            if not isinstance(target_features, list):
                raise ValueError("target_features must be a list of strings.")
            target_features = [str(f) for f in target_features]
            
        return cls(
            design_name=_require_non_empty_string(payload.get("design_name", "Freeform Design"), "design_name"),
            target_features=target_features
        )

@dataclass(frozen=True)
class CommitVerificationInput:
    notes: str
    expected_body_count: int | None
    expected_volume_range: list[float] | None
    resolved_features: list[str] | None = None

    @classmethod
    def from_payload(cls, payload: dict) -> "CommitVerificationInput":
        notes_val = payload.get("notes", "No notes")
        if not notes_val:
            notes_val = "No notes"
        
        expected_body_count = payload.get("expected_body_count")
        if expected_body_count is not None:
            expected_body_count = int(_require_non_negative_number(expected_body_count, "expected_body_count"))

        expected_volume_range = payload.get("expected_volume_range")
        if expected_volume_range is not None:
            if not isinstance(expected_volume_range, list) or len(expected_volume_range) != 2:
                raise ValueError("expected_volume_range must be a list of two numbers: [min, max]")
            expected_volume_range = [
                float(_require_non_negative_number(expected_volume_range[0], "expected_volume_range[0]")),
                float(_require_non_negative_number(expected_volume_range[1], "expected_volume_range[1]"))
            ]
            
        resolved_features = payload.get("resolved_features")
        if resolved_features is not None:
            if not isinstance(resolved_features, list):
                raise ValueError("resolved_features must be a list of strings.")
            resolved_features = [str(f) for f in resolved_features]

        return cls(
            notes=_require_non_empty_string(notes_val, "notes"),
            expected_body_count=expected_body_count,
            expected_volume_range=expected_volume_range,
            resolved_features=resolved_features
        )

@dataclass(frozen=True)
class EndFreeformSessionInput:
    deferred_features: list[dict[str, str]] | None = None

    @classmethod
    def from_payload(cls, payload: dict) -> "EndFreeformSessionInput":
        deferred = payload.get("deferred_features")
        if deferred is not None:
            if not isinstance(deferred, list):
                raise ValueError("deferred_features must be a list of {feature, reason} objects.")
        return cls(deferred_features=deferred)

@dataclass(frozen=True)
class ExportSessionLogInput:
    @classmethod
    def from_payload(cls, payload: dict) -> "ExportSessionLogInput":
        return cls()


@dataclass(frozen=True)
class CreateTelescopingContainersInput:
    """Three nesting rectangular containers with progressive clearances.
    
    Creates outer, middle, and inner containers that fit inside each other
    with specified clearances between each layer.
    """

    # Outer container
    outer_width_cm: float
    outer_depth_cm: float
    outer_height_cm: float
    wall_thickness_cm: float
    
    # Middle container clearance
    middle_clearance_cm: float
    
    # Inner container clearance  
    inner_clearance_cm: float
    
    # Export paths
    output_path_outer: str
    output_path_middle: str
    output_path_inner: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateTelescopingContainersInput":
        output_path_outer = _validate_export_path(payload["output_path_outer"])
        output_path_middle = _validate_export_path(payload["output_path_middle"])
        output_path_inner = _validate_export_path(payload["output_path_inner"])

        outer_width_cm = _require_positive_number(payload["outer_width_cm"], "outer_width_cm")
        outer_depth_cm = _require_positive_number(payload["outer_depth_cm"], "outer_depth_cm")
        outer_height_cm = _require_positive_number(payload["outer_height_cm"], "outer_height_cm")
        wall_thickness_cm = _require_positive_number(payload["wall_thickness_cm"], "wall_thickness_cm")
        middle_clearance_cm = _require_positive_number(payload["middle_clearance_cm"], "middle_clearance_cm")
        inner_clearance_cm = _require_positive_number(payload["inner_clearance_cm"], "inner_clearance_cm")

        # Validation: wall thickness must leave positive inner cavity for outer
        if wall_thickness_cm * 2.0 >= outer_width_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner width.")
        if wall_thickness_cm * 2.0 >= outer_depth_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner depth.")
        if wall_thickness_cm >= outer_height_cm:
            raise ValueError("wall_thickness_cm must be smaller than outer_height_cm.")

        # Validation: middle clearance must fit within outer inner cavity
        inner_width_outer = outer_width_cm - (wall_thickness_cm * 2.0)
        inner_depth_outer = outer_depth_cm - (wall_thickness_cm * 2.0)
        middle_outer_width = outer_width_cm - (middle_clearance_cm * 2.0)
        middle_outer_depth = outer_depth_cm - (middle_clearance_cm * 2.0)
        
        if middle_outer_width >= inner_width_outer:
            raise ValueError("middle_clearance_cm is too small to fit middle container inside outer.")
        if middle_outer_depth >= inner_depth_outer:
            raise ValueError("middle_clearance_cm is too small to fit middle container inside outer.")

        # Validation: inner clearance must fit within middle inner cavity
        middle_inner_width = middle_outer_width - (wall_thickness_cm * 2.0)
        middle_inner_depth = middle_outer_depth - (wall_thickness_cm * 2.0)
        inner_outer_width = middle_outer_width - (inner_clearance_cm * 2.0)
        inner_outer_depth = middle_outer_depth - (inner_clearance_cm * 2.0)
        
        # inner container must be strictly smaller than middle container's inner cavity
        # with room for at least 2*wall_thickness_cm (so shell operation works)
        min_inner_width = (wall_thickness_cm * 2.0) + 0.001  # tiny buffer
        min_inner_depth = (wall_thickness_cm * 2.0) + 0.001
        
        if inner_outer_width <= min_inner_width:
            raise ValueError("inner_clearance_cm is too large; inner container would be too small to shell.")
        if inner_outer_depth <= min_inner_depth:
            raise ValueError("inner_clearance_cm is too large; inner container would be too small to shell.")

        return cls(
            outer_width_cm=outer_width_cm,
            outer_depth_cm=outer_depth_cm,
            outer_height_cm=outer_height_cm,
            wall_thickness_cm=wall_thickness_cm,
            middle_clearance_cm=middle_clearance_cm,
            inner_clearance_cm=inner_clearance_cm,
            output_path_outer=output_path_outer,
            output_path_middle=output_path_middle,
            output_path_inner=output_path_inner,
        )


@dataclass(frozen=True)
class CreateSnapFitEnclosureInput:
    """Snap-fit enclosure box with view holes and snap-on lid.
    
    Creates a rectangular enclosure with:
    - Shell-hollowed box body with front and side view holes
    - Separate lid with snap bead ring for retention
    - Two STL exports (box and lid)
    """

    box_width_cm: float
    box_depth_cm: float
    box_height_cm: float
    wall_thickness_cm: float
    lid_height_cm: float
    snap_bead_width_cm: float
    snap_bead_height_cm: float
    clearance_cm: float
    front_hole_diameter_cm: float
    front_hole_center_z_cm: float
    side_hole_diameter_cm: float
    side_hole_center_z_cm: float
    output_path_box: str
    output_path_lid: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateSnapFitEnclosureInput":
        output_path_box = _validate_export_path(payload["output_path_box"])
        output_path_lid = _validate_export_path(payload["output_path_lid"])

        box_width_cm = _require_positive_number(payload["box_width_cm"], "box_width_cm")
        box_depth_cm = _require_positive_number(payload["box_depth_cm"], "box_depth_cm")
        box_height_cm = _require_positive_number(payload["box_height_cm"], "box_height_cm")
        wall_thickness_cm = _require_positive_number(payload["wall_thickness_cm"], "wall_thickness_cm")
        lid_height_cm = _require_positive_number(payload["lid_height_cm"], "lid_height_cm")
        snap_bead_width_cm = _require_positive_number(payload["snap_bead_width_cm"], "snap_bead_width_cm")
        snap_bead_height_cm = _require_positive_number(payload["snap_bead_height_cm"], "snap_bead_height_cm")
        clearance_cm = _require_positive_number(payload["clearance_cm"], "clearance_cm")
        front_hole_diameter_cm = _require_positive_number(payload["front_hole_diameter_cm"], "front_hole_diameter_cm")
        front_hole_center_z_cm = _require_positive_number(payload["front_hole_center_z_cm"], "front_hole_center_z_cm")
        side_hole_diameter_cm = _require_positive_number(payload["side_hole_diameter_cm"], "side_hole_diameter_cm")
        side_hole_center_z_cm = _require_positive_number(payload["side_hole_center_z_cm"], "side_hole_center_z_cm")

        # Validation: wall thickness must leave positive inner cavity
        if wall_thickness_cm * 2.0 >= box_width_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner width.")
        if wall_thickness_cm * 2.0 >= box_depth_cm:
            raise ValueError("wall_thickness_cm must leave a positive inner depth.")
        if wall_thickness_cm >= box_height_cm:
            raise ValueError("wall_thickness_cm must be smaller than box_height_cm.")

        # Validation: lid height must fit within total height
        if lid_height_cm >= box_height_cm:
            raise ValueError("lid_height_cm must be smaller than box_height_cm.")
        box_body_height_cm = box_height_cm - lid_height_cm
        if wall_thickness_cm >= box_body_height_cm:
            raise ValueError("wall_thickness_cm must be smaller than the box body height (box_height_cm - lid_height_cm).")

        # Validation: snap bead must fit within wall gap and inner cavity
        inner_width_cm = box_width_cm - (wall_thickness_cm * 2.0)
        inner_depth_cm = box_depth_cm - (wall_thickness_cm * 2.0)
        inner_height_cm = box_body_height_cm - wall_thickness_cm
        if snap_bead_width_cm >= inner_width_cm:
            raise ValueError("snap_bead_width_cm must be smaller than the inner cavity width.")
        if snap_bead_width_cm >= inner_depth_cm:
            raise ValueError("snap_bead_width_cm must be smaller than the inner cavity depth.")
        if snap_bead_height_cm >= inner_height_cm:
            raise ValueError("snap_bead_height_cm must be smaller than the inner cavity height.")

        # Validation: clearance must allow bead to fit
        bead_od_cm = snap_bead_width_cm + (clearance_cm * 2.0)
        if bead_od_cm >= inner_width_cm or bead_od_cm >= inner_depth_cm:
            raise ValueError("snap_bead_width_cm + 2*clearance_cm must fit within inner cavity.")

        # Validation: front hole must fit in front wall (XZ plane)
        # The front wall is at Y=0, spanning width in X and height in Z
        # After shell: inner cavity height is box_body_height_cm - wall_thickness_cm
        front_hole_radius_cm = front_hole_diameter_cm / 2.0
        inner_wall_height_cm = box_body_height_cm - wall_thickness_cm
        if front_hole_diameter_cm >= box_width_cm:
            raise ValueError("front_hole_diameter_cm must be smaller than box_width_cm.")
        if front_hole_diameter_cm >= inner_wall_height_cm:
            raise ValueError("front_hole_diameter_cm must be smaller than the inner wall height.")
        # Center Z must place hole fully inside wall (above floor, below top)
        if front_hole_center_z_cm <= wall_thickness_cm + front_hole_radius_cm:
            raise ValueError("front_hole_center_z_cm must place hole above the floor (wall_thickness_cm + radius).")
        if front_hole_center_z_cm >= box_body_height_cm - front_hole_radius_cm:
            raise ValueError("front_hole_center_z_cm must place hole below the box body top.")

        # Validation: side hole must fit in side wall (YZ plane)
        # The side wall is at X=0 or X=box_width, spanning depth in Y and height in Z
        side_hole_radius_cm = side_hole_diameter_cm / 2.0
        if side_hole_diameter_cm >= box_depth_cm:
            raise ValueError("side_hole_diameter_cm must be smaller than box_depth_cm.")
        if side_hole_diameter_cm >= inner_wall_height_cm:
            raise ValueError("side_hole_diameter_cm must be smaller than the inner wall height.")
        if side_hole_center_z_cm <= wall_thickness_cm + side_hole_radius_cm:
            raise ValueError("side_hole_center_z_cm must place hole above the floor.")
        if side_hole_center_z_cm >= box_body_height_cm - side_hole_radius_cm:
            raise ValueError("side_hole_center_z_cm must place hole below the box body top.")

        return cls(
            box_width_cm=box_width_cm,
            box_depth_cm=box_depth_cm,
            box_height_cm=box_height_cm,
            wall_thickness_cm=wall_thickness_cm,
            lid_height_cm=lid_height_cm,
            snap_bead_width_cm=snap_bead_width_cm,
            snap_bead_height_cm=snap_bead_height_cm,
            clearance_cm=clearance_cm,
            front_hole_diameter_cm=front_hole_diameter_cm,
            front_hole_center_z_cm=front_hole_center_z_cm,
            side_hole_diameter_cm=side_hole_diameter_cm,
            side_hole_center_z_cm=side_hole_center_z_cm,
            output_path_box=output_path_box,
            output_path_lid=output_path_lid,
        )


@dataclass(frozen=True)
class CreateSlottedFlexPanelInput:
    """Flat panel with evenly spaced rectangular slots for living hinge flexibility.
    
    Creates a rectangular panel with 5 slots cut through the thickness,
    each with filleted edges for stress relief.
    """

    panel_width_cm: float
    panel_depth_cm: float
    panel_thickness_cm: float
    slot_length_cm: float
    slot_width_cm: float
    slot_spacing_cm: float
    end_margin_cm: float
    edge_fillet_radius_cm: float
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateSlottedFlexPanelInput":
        output_path = _validate_export_path(payload["output_path"])

        panel_width_cm = _require_positive_number(payload["panel_width_cm"], "panel_width_cm")
        panel_depth_cm = _require_positive_number(payload["panel_depth_cm"], "panel_depth_cm")
        panel_thickness_cm = _require_positive_number(payload["panel_thickness_cm"], "panel_thickness_cm")
        slot_length_cm = _require_positive_number(payload["slot_length_cm"], "slot_length_cm")
        slot_width_cm = _require_positive_number(payload["slot_width_cm"], "slot_width_cm")
        slot_spacing_cm = _require_positive_number(payload["slot_spacing_cm"], "slot_spacing_cm")
        end_margin_cm = _require_positive_number(payload["end_margin_cm"], "end_margin_cm")
        edge_fillet_radius_cm = _require_positive_number(payload["edge_fillet_radius_cm"], "edge_fillet_radius_cm")

        # Validation: 5 slots with spacing must fit within panel width
        # Total width needed = 2*end_margin + 4*slot_spacing + 5*slot_width
        total_slots_width = 5 * slot_width_cm
        total_spacing_width = 4 * slot_spacing_cm
        total_required_width = (2 * end_margin_cm) + total_slots_width + total_spacing_width
        
        if total_required_width > panel_width_cm:
            raise ValueError(
                f"Panel width ({panel_width_cm}cm) insufficient for 5 slots ({slot_width_cm}cm each) "
                f"with spacing ({slot_spacing_cm}cm) and end margins ({end_margin_cm}cm each). "
                f"Required: {total_required_width}cm"
            )
        
        # Validation: slot length must fit within panel depth
        if slot_length_cm >= panel_depth_cm:
            raise ValueError("slot_length_cm must be smaller than panel_depth_cm.")
        
        # Validation: slot width must be smaller than slot spacing
        if slot_width_cm >= slot_spacing_cm:
            raise ValueError("slot_width_cm must be smaller than slot_spacing_cm for distinct slots.")
        
        # Validation: fillet radius must be reasonable for slot dimensions
        max_fillet = min(slot_width_cm, slot_length_cm) / 2.0
        if edge_fillet_radius_cm > max_fillet:
            raise ValueError(f"edge_fillet_radius_cm too large for slot dimensions. Max: {max_fillet}")
        
        # Validation: thickness must be reasonable for filleting
        if panel_thickness_cm <= edge_fillet_radius_cm * 2:
            raise ValueError("panel_thickness_cm must be greater than 2×edge_fillet_radius_cm.")

        return cls(
            panel_width_cm=panel_width_cm,
            panel_depth_cm=panel_depth_cm,
            panel_thickness_cm=panel_thickness_cm,
            slot_length_cm=slot_length_cm,
            slot_width_cm=slot_width_cm,
            slot_spacing_cm=slot_spacing_cm,
            end_margin_cm=end_margin_cm,
            edge_fillet_radius_cm=edge_fillet_radius_cm,
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateRatchetWheelInput:
    """Ratchet wheel with asymmetric teeth and center bore.
    
    Creates a cylindrical wheel with 10 asymmetric triangular teeth around
    the outer edge and a center bore. Each tooth has a gentle slope engagement
    face and a vertical locking face.
    """

    outer_diameter_cm: float
    thickness_cm: float
    bore_diameter_cm: float
    tooth_count: int
    tooth_height_cm: float
    slope_width_cm: float
    locking_width_cm: float
    tip_fillet_cm: float
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateRatchetWheelInput":
        output_path = _validate_export_path(payload["output_path"])

        outer_diameter_cm = _require_positive_number(payload["outer_diameter_cm"], "outer_diameter_cm")
        thickness_cm = _require_positive_number(payload["thickness_cm"], "thickness_cm")
        bore_diameter_cm = _require_positive_number(payload["bore_diameter_cm"], "bore_diameter_cm")
        tooth_count = int(payload["tooth_count"])
        tooth_height_cm = _require_positive_number(payload["tooth_height_cm"], "tooth_height_cm")
        slope_width_cm = _require_positive_number(payload["slope_width_cm"], "slope_width_cm")
        locking_width_cm = _require_positive_number(payload["locking_width_cm"], "locking_width_cm")
        tip_fillet_cm = _require_positive_number(payload["tip_fillet_cm"], "tip_fillet_cm")

        if tooth_count < 2:
            raise ValueError("tooth_count must be at least 2.")
        if tooth_count > 100:
            raise ValueError("tooth_count must be at most 100.")

        outer_radius = outer_diameter_cm / 2.0
        
        # Validation: bore must be smaller than outer
        if bore_diameter_cm >= outer_diameter_cm:
            raise ValueError("bore_diameter_cm must be smaller than outer_diameter_cm.")
        
        # Validation: tooth height must leave root circle
        root_radius = outer_radius - tooth_height_cm
        bore_radius = bore_diameter_cm / 2.0
        if root_radius <= bore_radius:
            raise ValueError("tooth_height_cm too large; no root circle remaining.")
        
        # Validation: tooth widths must fit within tooth angular span
        # Each tooth gets 360/tooth_count degrees
        tooth_angle_deg = 360.0 / tooth_count
        # Arc length at outer radius for one tooth
        tooth_arc_length = (tooth_angle_deg / 360.0) * (3.14159 * outer_diameter_cm)
        if slope_width_cm + locking_width_cm >= tooth_arc_length:
            raise ValueError("slope_width_cm + locking_width_cm must fit within tooth arc length.")
        
        # Validation: fillet must be reasonable
        if tip_fillet_cm >= tooth_height_cm / 2.0:
            raise ValueError("tip_fillet_cm too large for tooth_height_cm.")

        return cls(
            outer_diameter_cm=outer_diameter_cm,
            thickness_cm=thickness_cm,
            bore_diameter_cm=bore_diameter_cm,
            tooth_count=tooth_count,
            tooth_height_cm=tooth_height_cm,
            slope_width_cm=slope_width_cm,
            locking_width_cm=locking_width_cm,
            tip_fillet_cm=tip_fillet_cm,
            output_path=output_path,
        )


@dataclass(frozen=True)
class CreateWireClampInput:
    """Wire clamp with bore, tapered lead-ins, grip ribs, and split slot.
    
    Creates a clamp body with a through-bore for wire, tapered lead-in entries
    on both ends, internal grip ribs, and a longitudinal split slot for flex.
    """

    body_length_cm: float
    body_width_cm: float
    body_height_cm: float
    bore_radius_cm: float
    lead_in_depth_cm: float
    lead_in_exit_radius_cm: float
    rib_count: int
    rib_height_cm: float
    rib_width_cm: float
    rib_spacing_cm: float
    split_slot_width_cm: float
    output_path: str

    @classmethod
    def from_payload(cls, payload: dict) -> "CreateWireClampInput":
        output_path = _validate_export_path(payload["output_path"])

        body_length_cm = _require_positive_number(payload["body_length_cm"], "body_length_cm")
        body_width_cm = _require_positive_number(payload["body_width_cm"], "body_width_cm")
        body_height_cm = _require_positive_number(payload["body_height_cm"], "body_height_cm")
        bore_radius_cm = _require_positive_number(payload["bore_radius_cm"], "bore_radius_cm")
        lead_in_depth_cm = _require_positive_number(payload["lead_in_depth_cm"], "lead_in_depth_cm")
        lead_in_exit_radius_cm = _require_positive_number(payload["lead_in_exit_radius_cm"], "lead_in_exit_radius_cm")
        rib_count = int(payload["rib_count"])
        rib_height_cm = _require_positive_number(payload["rib_height_cm"], "rib_height_cm")
        rib_width_cm = _require_positive_number(payload["rib_width_cm"], "rib_width_cm")
        rib_spacing_cm = _require_positive_number(payload["rib_spacing_cm"], "rib_spacing_cm")
        split_slot_width_cm = _require_positive_number(payload["split_slot_width_cm"], "split_slot_width_cm")

        if rib_count < 1:
            raise ValueError("rib_count must be at least 1.")
        if rib_count > 20:
            raise ValueError("rib_count must be at most 20.")

        # Validation: bore must fit within body
        if bore_radius_cm >= body_width_cm / 2.0:
            raise ValueError("bore_radius_cm too large for body_width_cm.")
        if bore_radius_cm >= body_height_cm / 2.0:
            raise ValueError("bore_radius_cm too large for body_height_cm.")
        
        # Validation: lead-in must fit within body
        if lead_in_depth_cm >= body_length_cm / 2.0:
            raise ValueError("lead_in_depth_cm too large for body_length_cm.")
        
        # Validation: lead-in exit radius must be larger than bore
        if lead_in_exit_radius_cm <= bore_radius_cm:
            raise ValueError("lead_in_exit_radius_cm must be larger than bore_radius_cm.")
        if lead_in_exit_radius_cm >= body_width_cm / 2.0:
            raise ValueError("lead_in_exit_radius_cm too large for body_width_cm.")
        
        # Validation: ribs must fit within body
        total_rib_span = rib_count * rib_width_cm + (rib_count - 1) * rib_spacing_cm
        if total_rib_span >= body_length_cm:
            raise ValueError("rib_count + spacing too large for body_length_cm.")
        
        # Validation: rib height must fit within body (rib protrudes from bore)
        if bore_radius_cm + rib_height_cm >= body_width_cm / 2.0:
            raise ValueError("bore_radius_cm + rib_height_cm too large for body_width_cm.")
        
        # Validation: split slot must be reasonable
        if split_slot_width_cm >= body_width_cm:
            raise ValueError("split_slot_width_cm too large for body_width_cm.")

        return cls(
            body_length_cm=body_length_cm,
            body_width_cm=body_width_cm,
            body_height_cm=body_height_cm,
            bore_radius_cm=bore_radius_cm,
            lead_in_depth_cm=lead_in_depth_cm,
            lead_in_exit_radius_cm=lead_in_exit_radius_cm,
            rib_count=rib_count,
            rib_height_cm=rib_height_cm,
            rib_width_cm=rib_width_cm,
            rib_spacing_cm=rib_spacing_cm,
            split_slot_width_cm=split_slot_width_cm,
            output_path=output_path,
        )
