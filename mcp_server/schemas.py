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
