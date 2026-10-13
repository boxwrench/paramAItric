"""Product-owned centered plate intent, replay and provenance-aware gates.

Shared by the internal proof runner and the configured guided Utility runtime.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import tempfile

from cad_backends.protocol import Measurements, PlateBackend
from mcp_server.errors import WorkflowFailure
from mcp_server.operations import ExpectedDelta, Operation, OperationMode, Placement, Target, VolumeDelta
from mcp_server.schemas import CreatePlateWithHoleInput


@dataclass(frozen=True)
class CenteredPlate:
    width_mm: float = 80.0
    height_mm: float = 60.0
    thickness_mm: float = 5.0
    hole_diameter_mm: float = 10.0

    def __post_init__(self):
        for name, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= 10000:
                raise ValueError(f"{name} must be a finite positive number up to 10000 mm")
        if self.hole_diameter_mm >= min(self.width_mm, self.height_mm):
            raise ValueError("hole must fit strictly inside the plate")

    def parameters(self) -> dict:
        return {"recipe": "centered_plate_v1", "units": "mm", "datum": "lower_left_xy_positive_z", **asdict(self)}

    def legacy_payload(self, output: Path) -> dict:
        payload = {
            "width_cm": self.width_mm / 10, "height_cm": self.height_mm / 10,
            "thickness_cm": self.thickness_mm / 10, "hole_diameter_cm": self.hole_diameter_mm / 10,
            "hole_center_x_cm": self.width_mm / 20, "hole_center_y_cm": self.height_mm / 20,
            "plane": "xy", "output_path": str(output),
        }
        # Preserve the existing plate schema's dimensional/placement/path rules.
        CreatePlateWithHoleInput.from_payload(payload)
        return payload

    def operations(self) -> tuple[Operation, Operation]:
        return (
            Operation(OperationMode.NEW_BODY,
                      Target("rectangle", {"width": self.width_mm / 10, "height": self.height_mm / 10}, self.thickness_mm / 10),
                      Placement("xy"), ExpectedDelta(1, VolumeDelta.INCREASE)),
            Operation(OperationMode.CUT,
                      Target("circle", {"radius": self.hole_diameter_mm / 20}, self.thickness_mm / 10),
                      Placement("xy", x_cm=self.width_mm / 20, y_cm=self.height_mm / 20),
                      ExpectedDelta(0, VolumeDelta.DECREASE)),
        )


def verify_plate(spec: CenteredPlate, observed: Measurements, *, hole: bool, full: bool) -> list[dict]:
    """Missing/invalid required facts fail closed. Topology counts stay diagnostic."""
    facts = observed.facts
    expected = {
        "body_count": (1, 0),
        "width_mm": (spec.width_mm, 0.01), "height_mm": (spec.height_mm, 0.01),
        "thickness_mm": (spec.thickness_mm, 0.01),
    }
    if full:
        expected["valid"] = (True, 0)
        if hole:
            expected.update({
                "hole_diameter_mm": (spec.hole_diameter_mm, 0.01),
                "hole_center_x_mm": (spec.width_mm / 2, 0.01),
                "hole_center_y_mm": (spec.height_mm / 2, 0.01),
                "through_hole": (True, 0),
            })
    signals = []
    for name, (value, tolerance) in expected.items():
        actual = facts.get(name)
        if isinstance(value, bool):
            passed = actual is value
        else:
            passed = (isinstance(actual, (int, float)) and not isinstance(actual, bool)
                      and math.isfinite(actual) and abs(actual - value) <= tolerance)
        signals.append({"name": name, "tier": 0, "passed": passed, "actual": actual,
                        "expected": value, "tolerance": tolerance,
                        "provenance": observed.provenance, "accuracy": observed.accuracy})
    # Required end-state audit for the controlled exact-kernel proof. Fusion's
    # current default-accuracy physical properties remain audit-only observations.
    volume = spec.width_mm * spec.height_mm * spec.thickness_mm
    if hole:
        volume -= math.pi * (spec.hole_diameter_mm / 2) ** 2 * spec.thickness_mm
    actual = facts.get("volume_mm3")
    volume_passed = (isinstance(actual, (int, float)) and not isinstance(actual, bool)
                     and math.isfinite(actual) and abs(actual - volume) <= max(0.01, volume * 1e-6))
    signals.append({"name": "volume_mm3", "tier": 1, "required": full,
                    "passed": volume_passed, "actual": actual, "expected": volume,
                    "provenance": observed.provenance, "accuracy": observed.accuracy})
    for name in ("face_count", "edge_count", "area_mm2"):
        signals.append({"name": name, "tier": 2, "actual": facts.get(name),
                        "provenance": observed.provenance, "accuracy": observed.accuracy})
    failed = [s for s in signals if (s["tier"] == 0 or s.get("required")) and not s["passed"]]
    if failed:
        raise WorkflowFailure("Plate geometry did not meet required checks.", stage="verify_geometry",
                              classification="verification_failed", partial_result={"verification_signals": signals},
                              next_step="Inspect the retained revision; no next mutation or export was accepted.")
    return signals


def build_plate(backend: PlateBackend, spec: CenteredPlate, output_root: Path,
                *, full_geometry: bool = True, formats: tuple[str, ...] = ("step", "stl")) -> dict:
    required = {"body_count", "width_mm", "height_mm", "thickness_mm"}
    if full_geometry:
        required |= {"valid", "volume_mm3", "hole_diameter_mm", "hole_center_x_mm", "hole_center_y_mm", "through_hole"}
    backend.capabilities.require(operations=("new_body", "cut"), measurements=required, exports=formats)
    root = Path(output_root).resolve()
    # User-visible output rules are shared with the existing server.
    spec.legacy_payload(root / "plate.stl")
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="plate-", dir=root))
    parameters = spec.parameters()
    (directory / "parameters.json").write_text(json.dumps(parameters, indent=2) + "\n")
    part = backend.start_part(directory, parameters)
    signals = []
    previous_count = 0
    previous_volume = 0.0
    for index, operation in enumerate(spec.operations()):
        try:
            backend.apply(part, operation)
            observed = backend.inspect(part)
            stage_signals = verify_plate(spec, observed, hole=index == 1, full=full_geometry)
            signals += [{**s, "revision": part.revision} for s in stage_signals]
            actual_count = observed.facts["body_count"]
            if actual_count - previous_count != operation.expected_delta.body_count_delta:
                raise WorkflowFailure("Unexpected body-count delta.", stage="verify_delta", classification="verification_failed")
            previous_count = actual_count
            if full_geometry:
                actual_volume = observed.facts["volume_mm3"]
                direction = VolumeDelta.INCREASE if actual_volume > previous_volume else VolumeDelta.DECREASE if actual_volume < previous_volume else VolumeDelta.UNCHANGED
                failures = operation.expected_delta.check(body_count_delta=operation.expected_delta.body_count_delta,
                                                           volume=direction, features=())
                if failures:
                    raise WorkflowFailure("Operation delta failed.", stage="verify_delta", classification="verification_failed",
                                          partial_result={"failures": failures})
                previous_volume = actual_volume
        except WorkflowFailure as exc:
            exc.partial_result.update({"directory": str(directory), "revision": part.revision})
            raise
        # Commit is implicit only after required stage verification passed.
    artifacts = backend.export(part, formats)
    report = {
        "ok": True, "recipe": parameters, "backend": backend.capabilities.name,
        "evidence": backend.capabilities.evidence, "editability": backend.capabilities.editability.value,
        "directory": str(directory), "artifacts": {k: str(v) for k, v in artifacts.items()},
        "verification_signals": signals, "measurements": observed.facts,
        "recipe_sha256": hashlib.sha256((directory / "parameters.json").read_bytes()).hexdigest(),
        "artifact_sha256": {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in artifacts.items()},
        "full_geometry": full_geometry,
    }
    # Geometry evidence is a staging record, never revision acceptance. The
    # guided runtime publishes verification.json at its atomic commit point.
    report["acceptance"] = "geometry_verified"
    (directory / "geometry-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def regenerate_plate(backend: PlateBackend, previous: dict, changes: dict, output_root: Path, **kwargs) -> dict:
    params = previous["recipe"]
    spec = CenteredPlate(**{key: params[key] for key in CenteredPlate.__dataclass_fields__})
    # replace rejects unknown parameters, and __post_init__ revalidates all values.
    result = build_plate(backend, replace(spec, **changes), output_root, **kwargs)
    result["previous_revision"] = previous["directory"]
    Path(result["directory"], "geometry-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
