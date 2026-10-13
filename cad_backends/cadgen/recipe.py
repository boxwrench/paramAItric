"""Reviewed, standalone centered_plate_v1 recipe and saved-artifact reader.

Run in a dedicated environment in a directory containing parameters.json.
There is no eval/exec or import of user-provided modules. Replay this source with
`python -I recipe.py replay`; inspect a saved revision with `... inspect`.
"""
from __future__ import annotations

import importlib.metadata
import json
import math
from pathlib import Path
import resource
import shutil
import struct
import sys

VERSIONS = {"cadgen": "0.7.14", "build123d": "0.11.1", "cadquery-ocp-novtk": "7.9.3.1.1"}


def dimensions():
    params = json.loads(Path("parameters.json").read_text())
    keys = {"width_mm", "height_mm", "thickness_mm", "hole_diameter_mm"}
    if set(params) != keys | {"recipe", "units", "datum"} or params["recipe"] != "centered_plate_v1" or params["units"] != "mm" or params["datum"] != "lower_left_xy_positive_z":
        raise ValueError("unsupported recipe metadata")
    for key in keys:
        value = params[key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 < value <= 10000:
            raise ValueError(f"invalid or excessive dimension: {key}")
    if params["hole_diameter_mm"] >= min(params["width_mm"], params["height_mm"]):
        raise ValueError("hole does not fit inside plate")
    return params


def read_facts(bd, shape):
    if len(shape.solids()) == 0:
        raise ValueError("saved STEP contains no solid geometry")
    box = shape.bounding_box()
    size = box.size
    circles = [e for e in shape.edges() if e.geom_type == bd.GeomType.CIRCLE]
    facts = {"body_count": len(shape.solids()), "valid": shape.is_valid,
             "width_mm": size.X, "height_mm": size.Y, "thickness_mm": size.Z,
             "volume_mm3": shape.volume, "area_mm2": shape.area,
             "face_count": len(shape.faces()), "edge_count": len(shape.edges())}
    # Narrow semantic query: one cylindrical bore with a circular rim at each
    # external Z datum. An analytic volume check independently rejects a blind cut.
    if len(circles) == 2:
        a, b = circles
        ca, cb = a.arc_center, b.arc_center
        same_axis = abs(ca.X - cb.X) < 1e-7 and abs(ca.Y - cb.Y) < 1e-7
        same_radius = abs(a.radius - b.radius) < 1e-7
        rims = sorted([ca.Z, cb.Z])
        through = (same_axis and same_radius and abs(rims[0] - box.min.Z) < 1e-7
                   and abs(rims[1] - box.max.Z) < 1e-7)
        facts.update({"hole_diameter_mm": a.radius * 2, "hole_center_x_mm": ca.X - box.min.X,
                      "hole_center_y_mm": ca.Y - box.min.Y, "through_hole": through})
    return facts


def run(action):
    # Bounds cover the entire process, including kernel import. No daemon builds
    # are launched, so a timeout can terminate all construction and inspection.
    resource.setrlimit(resource.RLIMIT_CPU, (45, 45))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    actual = {key: importlib.metadata.version(key) for key in VERSIONS}
    if actual != VERSIONS:
        return {"ok": False, "classification": "dependency_mismatch", "error": f"Expected {VERSIONS}, installed {actual}"}
    from cadgen import build123d as bd

    p = dimensions()
    Path("runtime.json").write_text(json.dumps({"versions": actual, "python": sys.version,
                                             "units": "mm", "stl_linear_deflection_mm": 0.01}, indent=2))
    request = json.loads(Path("request.json").read_text()) if action != "replay" else {}
    if action == "replay":
        base = bd.Box(p["width_mm"], p["height_mm"], p["thickness_mm"], align=(bd.Align.MIN,) * 3)
        bore = bd.Pos(p["width_mm"] / 2, p["height_mm"] / 2, 0) * bd.Cylinder(p["hole_diameter_mm"] / 2, p["thickness_mm"], align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        shape = base - bore
        if not bd.export_step(shape, "plate.step"):
            raise RuntimeError("STEP export failed")
        return {"ok": True, "facts": read_facts(bd, bd.import_step("plate.step"))}
    revision = request["revision"]
    if type(revision) is not int or revision not in (0, 1, 2):
        raise ValueError("invalid revision")
    path = Path(f"stage-{revision}.step")
    if action == "apply":
        width, height, thickness, radius = p["width_mm"], p["height_mm"], p["thickness_mm"], p["hole_diameter_mm"] / 2
        if revision == 0:
            expected = {"mode": "new_body", "target": {"profile": "rectangle", "dimensions_cm": {"width": width / 10, "height": height / 10}, "extent_cm": thickness / 10},
                        "placement": {"plane": "xy", "offset_cm": 0, "x_cm": 0, "y_cm": 0},
                        "expected_delta": {"body_count_delta": 1, "volume": "increase", "features_present": []}}
            shape = bd.Box(width, height, thickness, align=(bd.Align.MIN,) * 3)
        elif revision == 1:
            expected = {"mode": "cut", "target": {"profile": "circle", "dimensions_cm": {"radius": radius / 10}, "extent_cm": thickness / 10},
                        "placement": {"plane": "xy", "offset_cm": 0, "x_cm": width / 20, "y_cm": height / 20},
                        "expected_delta": {"body_count_delta": 0, "volume": "decrease", "features_present": []}}
            shape = bd.import_step(path) - bd.Pos(width / 2, height / 2, 0) * bd.Cylinder(radius, thickness, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))
        else:
            raise ValueError("no third mutation is supported")
        if request["operation"] != expected:
            raise ValueError("operation does not match validated centered-plate intent")
        if not bd.export_step(shape, f"stage-{revision + 1}.step"):
            raise RuntimeError("STEP export failed")
        return {"ok": True, "versions": actual}
    if action == "inspect":
        # Fresh process, cold native STEP parser; no generation response reused.
        return {"ok": True, "facts": read_facts(bd, bd.import_step(path))}
    if action == "export":
        if revision != 2 or not set(request["formats"]) <= {"step", "stl"}:
            raise ValueError("unsupported export")
        shape = bd.import_step(path)
        if "step" in request["formats"]:
            shutil.copyfile(path, "plate.step")
        if "stl" in request["formats"]:
            if not bd.export_stl(shape, "plate.stl", tolerance=0.01):
                raise RuntimeError("STL export failed")
            # Parse the saved binary mesh: count/length, finite vertices, bounds
            # and signed volume. A successful writer return is insufficient.
            blob = Path("plate.stl").read_bytes()
            count = struct.unpack_from("<I", blob, 80)[0]
            if count == 0 or len(blob) != 84 + 50 * count:
                raise ValueError("malformed STL output")
            vertices, volume = [], 0.0
            for offset in range(84, len(blob), 50):
                values = struct.unpack_from("<12fH", blob, offset)
                if not all(math.isfinite(x) for x in values[:12]):
                    raise ValueError("nonfinite STL coordinates")
                a, b, c = (bd.Vector(*values[i:i + 3]) for i in (3, 6, 9))
                vertices.extend((a, b, c))
                volume += a.dot(b.cross(c)) / 6
            size = [max(getattr(v, k) for v in vertices) - min(getattr(v, k) for v in vertices) for k in ("X", "Y", "Z")]
            expected_volume = shape.volume
            if any(abs(a - b) > 0.01 for a, b in zip(size, (p["width_mm"], p["height_mm"], p["thickness_mm"]))) or abs(volume - expected_volume) > expected_volume * 0.001:
                raise ValueError("STL dimensions or signed volume mismatch")
            Path("mesh-verification.json").write_text(json.dumps({"triangle_count": count, "bounds_mm": size, "volume_mm3": volume,
                                                                   "volume_relative_tolerance": 0.001, "manifold_checked": False}, indent=2))
        return {"ok": True}
    raise ValueError("unknown worker action")


if __name__ == "__main__":
    try:
        result = run(sys.argv[1])
    except Exception as exc:
        result = {"ok": False, "classification": "backend_error", "error": str(exc)}
    Path("response.json").write_text(json.dumps(result, allow_nan=False))
    raise SystemExit(0 if result["ok"] else 1)
