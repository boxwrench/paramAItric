from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _require_positive_number(value: object, field_name: str) -> float:
    if not isinstance(value, (int, float)) or float(value) <= 0:
        raise ValueError(f"{field_name} must be a positive number.")
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
        _validate_hole_position(
            width_cm,
            height_cm,
            leg_thickness_cm,
            hole_radius_cm,
            first_hole_center_x_cm,
            first_hole_center_y_cm,
            "first_hole",
        )
        _validate_hole_position(
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
        _validate_rectangular_hole_position(
            width_cm=width_cm,
            height_cm=height_cm,
            hole_radius_cm=hole_radius_cm,
            center_x_cm=edge_offset_x_cm,
            center_y_cm=hole_center_y_cm,
            label="first_hole",
        )
        _validate_rectangular_hole_position(
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
            _validate_rectangular_hole_position(
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
        _validate_slot_position(
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
        _validate_rectangular_hole_position(
            width_cm=width_cm,
            height_cm=height_cm,
            hole_radius_cm=hole_diameter_cm / 2.0,
            center_x_cm=hole_center_x_cm,
            center_y_cm=hole_center_y_cm,
            label="hole",
        )
        _validate_rectangular_hole_position(
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
        _validate_rectangular_hole_position(
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
        _validate_rectangle_placement(
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


def _validate_hole_position(
    width_cm: float,
    height_cm: float,
    leg_thickness_cm: float,
    hole_radius_cm: float,
    center_x_cm: float,
    center_y_cm: float,
    label: str,
) -> None:
    if not (hole_radius_cm < center_x_cm < width_cm - hole_radius_cm):
        raise ValueError(f"{label}_center_x_cm must keep the hole inside the sketch bounds.")
    if not (hole_radius_cm < center_y_cm < height_cm - hole_radius_cm):
        raise ValueError(f"{label}_center_y_cm must keep the hole inside the sketch bounds.")
    in_vertical_leg = center_x_cm + hole_radius_cm <= leg_thickness_cm
    in_horizontal_leg = center_y_cm - hole_radius_cm <= leg_thickness_cm
    if not (in_vertical_leg or in_horizontal_leg):
        raise ValueError(f"{label} center must land fully inside one L-bracket leg.")


def _validate_rectangular_hole_position(
    *,
    width_cm: float,
    height_cm: float,
    hole_radius_cm: float,
    center_x_cm: float,
    center_y_cm: float,
    label: str,
) -> None:
    if not (hole_radius_cm < center_x_cm < width_cm - hole_radius_cm):
        raise ValueError(f"{label}_center_x_cm must keep the hole inside the sketch bounds.")
    if not (hole_radius_cm < center_y_cm < height_cm - hole_radius_cm):
        raise ValueError(f"{label}_center_y_cm must keep the hole inside the sketch bounds.")


def _validate_slot_position(
    *,
    width_cm: float,
    height_cm: float,
    slot_length_cm: float,
    slot_width_cm: float,
    center_x_cm: float,
    center_y_cm: float,
) -> None:
    half_length_cm = slot_length_cm / 2.0
    half_width_cm = slot_width_cm / 2.0
    if not (half_length_cm < center_x_cm < width_cm - half_length_cm):
        raise ValueError("slot_center_x_cm must keep the slot inside the sketch bounds.")
    if not (half_width_cm < center_y_cm < height_cm - half_width_cm):
        raise ValueError("slot_center_y_cm must keep the slot inside the sketch bounds.")


def _validate_rectangle_placement(
    *,
    outer_width_cm: float,
    outer_height_cm: float,
    inner_width_cm: float,
    inner_height_cm: float,
    origin_x_cm: float,
    origin_y_cm: float,
    label: str,
) -> None:
    if origin_x_cm <= 0 or origin_y_cm <= 0:
        raise ValueError(f"{label}_origin_x_cm and {label}_origin_y_cm must keep the rectangle inside the sketch bounds.")
    if origin_x_cm + inner_width_cm >= outer_width_cm:
        raise ValueError(f"{label}_origin_x_cm must keep the rectangle inside the sketch bounds.")
    if origin_y_cm + inner_height_cm >= outer_height_cm:
        raise ValueError(f"{label}_origin_y_cm must keep the rectangle inside the sketch bounds.")
