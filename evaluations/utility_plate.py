"""Explicit backend proof runner, separate from the 17 server contract fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import time

from evaluations.runner.metadata import ReproducibilityMetadata, utc_timestamp
from mcp_server.errors import error_from_exception
from mcp_server.utility_plate import CenteredPlate, build_plate, regenerate_plate


def compare_measurements(reference: dict, candidate: dict) -> dict:
    """Missing facts are unavailable, never an inferred geometry-equivalence pass."""
    checks = {}
    for key in ("body_count", "width_mm", "height_mm", "thickness_mm", "volume_mm3",
                "hole_diameter_mm", "hole_center_x_mm", "hole_center_y_mm", "through_hole", "valid"):
        a, b = reference.get(key), candidate.get(key)
        if a is None or b is None:
            checks[key] = "unavailable"
        elif isinstance(a, bool) or key == "body_count":
            checks[key] = "match" if a == b else "mismatch"
        else:
            tolerance = max(0.01, abs(a) * 1e-6) if key == "volume_mm3" else 0.01
            checks[key] = "match" if math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance else "mismatch"
    status = "mismatch" if "mismatch" in checks.values() else "incomplete" if "unavailable" in checks.values() else "match"
    return {"status": status, "checks": checks, "dimension_tolerance_mm": 0.01, "volume_relative_tolerance": 1e-6}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("cadgen", "fusion"), default="cadgen")
    parser.add_argument("--python", type=Path, help="Dedicated pinned CAD worker Python")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8123")
    args = parser.parse_args()
    if args.backend == "cadgen":
        if not args.python:
            parser.error("--python is required for cadgen")
        from cad_backends.cadgen import CadgenPlateBackend
        backend = CadgenPlateBackend(args.python, args.output_root)
        options = {"full_geometry": True, "formats": ("step", "stl")}
    else:
        from cad_backends.fusion import FusionPlateBackend
        from mcp_server.bridge_client import BridgeClient
        from mcp_server.server import ParamAIToolServer
        backend = FusionPlateBackend(ParamAIToolServer(BridgeClient(args.endpoint)))
        options = {"full_geometry": False, "formats": ("stl",)}
    # Reuse the fixture's normalized dimensions, not an independent example spec.
    fixture = Path(__file__).with_name("cases") / "plate_centered_hole_success.json"
    case = json.loads(fixture.read_text())
    p = case["arguments"]
    spec = CenteredPlate(p["width_cm"] * 10, p["height_cm"] * 10, p["thickness_cm"] * 10, p["hole_diameter_cm"] * 10)
    start = time.perf_counter()
    report = {"case_id": case["id"], "timestamp": utc_timestamp(), "backend": backend.capabilities.name,
              "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
              "metadata": ReproducibilityMetadata.capture(case["id"], model="none", tool_profile="internal_utility_plate",
                           inference_backend="none", hardware=platform.platform() + "/" + platform.machine()).to_dict()}
    try:
        initial = build_plate(backend, spec, args.output_root, **options)
        edited = regenerate_plate(backend, initial, {"width_mm": 100}, args.output_root, **options)
        report.update({"status": "pass" if options["full_geometry"] else "limited_reference",
                       "initial": initial, "edited": edited})
    except Exception as exc:
        report.update({"status": "fail", "failure": error_from_exception(exc)})
    report["elapsed_seconds"] = time.perf_counter() - start
    report["source_sha256"] = {str(p.relative_to(Path(__file__).resolve().parents[1])): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [Path(__file__), Path(__file__).parents[1] / "mcp_server/utility_plate.py",
                                         Path(__file__).parents[1] / "cad_backends/cadgen/recipe.py",
                                         Path(__file__).parents[1] / "cad_backends/cadgen/adapter.py"]}
    if args.backend == "cadgen":
        report["worker_runtime"] = (
            json.loads(Path(report["initial"]["directory"], "runtime.json").read_text())
            if report.get("initial") else None
        )
    args.output_root.mkdir(parents=True, exist_ok=True)
    path = args.output_root / "smoke.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "report": str(path), "elapsed_seconds": report["elapsed_seconds"]}))
    return int(report["status"] == "fail")


if __name__ == "__main__":
    raise SystemExit(main())
