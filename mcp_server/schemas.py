from __future__ import annotations

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
