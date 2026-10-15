"""Cold OCCT read-back of saved SolidCraft STEP; executes in the pinned CAD venv."""
from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import sys


def verify(facts: dict, kind: str, p: dict) -> list[dict]:
    w, h, t = (p[name] for name in ("width", "height", "thickness"))
    volume = w * h * t
    if kind == "plate":
        volume -= math.pi * (p["hole_diameter"] / 2) ** 2 * t
    if kind == "bracket":
        volume = (w * p["leg"] + h * p["leg"] - p["leg"] ** 2) * t
        volume -= (1 - math.pi / 4) * p.get("fillet", 0) ** 2 * t
    expected = {"body_count": (1, 0), "valid": (True, 0), "width": (w, 0.01), "height": (h, 0.01),
                "thickness": (t, 0.01), "min_x": (0, 0.01), "min_y": (0, 0.01), "min_z": (0, 0.01),
                "volume_mm3": (volume, max(0.01, volume * 1e-6))}
    if kind == "plate":
        expected.update({"bore_diameter": (p["hole_diameter"], 0.01), "bore_x": (w / 2, 0.01),
                         "bore_y": (h / 2, 0.01), "bore_through": (True, 0)})
    if kind == "bracket":
        expected.update({"inner_corner": (True, 0), "legs_contain_material": (True, 0), "inner_void": (True, 0)})
        if p.get("fillet"):
            expected["fillet_surface"] = (True, 0)
    checks = []
    for name, (value, tolerance) in expected.items():
        actual = facts.get(name)
        passed = actual is value if isinstance(value, bool) else (
            isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isfinite(actual)
            and abs(actual - value) <= tolerance)
        checks.append({"name": name, "tier": 1 if name == "volume_mm3" else 0, "required": True,
                       "passed": passed, "actual": actual, "expected": value, "tolerance": tolerance,
                       "provenance": "exported_STEP_independent_OCCT_process"})
    return checks


def read(path: Path, kind: str, p: dict) -> dict:
    from cadgen import build123d as bd
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    shape = bd.import_step(str(path))
    solids = shape.solids()
    if not solids:
        raise ValueError("STEP contains no solid")
    box = shape.bounding_box()
    facts = {"body_count": len(solids), "valid": shape.is_valid, "width": box.size.X, "height": box.size.Y,
             "thickness": box.size.Z, "min_x": box.min.X, "min_y": box.min.Y, "min_z": box.min.Z,
             "volume_mm3": shape.volume, "area_mm2": shape.area}
    cylinders = []
    for face in shape.faces():
        surface = BRepAdaptor_Surface(face.wrapped)
        if surface.GetType() == GeomAbs_Cylinder:
            c = surface.Cylinder()
            fb = face.bounding_box()
            cylinders.append({"radius": c.Radius(), "x": c.Location().X(), "y": c.Location().Y(),
                              "axis_z": c.Axis().Direction().Z(), "min_z": fb.min.Z, "max_z": fb.max.Z})
    facts["cylinders"] = cylinders
    w, h, t = (p[name] for name in ("width", "height", "thickness"))
    if kind == "plate" and len(cylinders) == 1:
        c = cylinders[0]
        facts.update({"bore_diameter": 2 * c["radius"], "bore_x": c["x"], "bore_y": c["y"],
                      "bore_through": abs(abs(c["axis_z"]) - 1) < 1e-6 and abs(c["min_z"]) < 1e-5
                                      and abs(c["max_z"] - t) < 1e-5 and all(
                                          not solids[0].is_inside((w / 2, h / 2, z)) for z in (t / 4, 3 * t / 4))})
    if kind == "bracket":
        leg = p["leg"]
        vertices = [tuple(v.center()) for v in shape.vertices()]
        facts["inner_corner"] = all(any(math.dist(v, (leg, leg, z)) < 0.01 for v in vertices) for z in (0, t))
        facts["legs_contain_material"] = all(solids[0].is_inside(point) for point in (
            (leg / 2, h * 0.75, t / 2), (w * 0.75, leg / 2, t / 2), (leg / 2, leg / 2, t / 2)))
        facts["inner_void"] = not solids[0].is_inside(((w + leg) / 2, (h + leg) / 2, t / 2))
        r = p.get("fillet", 0)
        facts["fillet_surface"] = any(abs(c["radius"] - r) < 0.01 and abs(c["x"] - (w - r)) < 0.01
                                     and abs(c["y"] - r) < 0.01 for c in cylinders) if r else None
    checks = verify(facts, kind, p)
    return {"ok": all(c["passed"] for c in checks), "measurements": facts, "checks": checks}


def read_mesh(path: Path, p: dict, volume: float) -> dict:
    blob = path.read_bytes()
    if len(blob) < 84:
        raise ValueError("STL header missing")
    count = struct.unpack_from("<I", blob, 80)[0]
    if not count or len(blob) != 84 + count * 50:
        raise ValueError("STL triangle count/length mismatch")
    lo, hi, signed_volume = [math.inf] * 3, [-math.inf] * 3, 0.0
    for i in range(count):
        values = struct.unpack_from("<12fH", blob, 84 + 50 * i)
        if not all(math.isfinite(v) for v in values[:12]):
            raise ValueError("Nonfinite STL values")
        a, b, c = values[3:6], values[6:9], values[9:12]
        signed_volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) + a[1] * (b[2] * c[0] - b[0] * c[2]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
        for point in (a, b, c):
            lo = [min(x, y) for x, y in zip(lo, point)]
            hi = [max(x, y) for x, y in zip(hi, point)]
    dimensions = [p[key] for key in ("width", "height", "thickness")]
    if any(abs(lo[i]) > 0.01 or abs(hi[i] - dimensions[i]) > 0.01 for i in range(3)) or abs(signed_volume - volume) > max(0.01, volume * 0.001):
        raise ValueError("STL envelope or signed volume does not match verified STEP")
    return {"triangle_count": count, "bounds_min": lo, "bounds_max": hi, "signed_volume_mm3": signed_volume,
            "volume_relative_tolerance": 0.001, "manifold_self_intersection": "not_checked"}


if __name__ == "__main__":
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (45, 45))
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        result = read(Path(sys.argv[1]), sys.argv[2], json.loads(sys.argv[3]))
        if len(sys.argv) > 4:
            result["mesh"] = read_mesh(Path(sys.argv[4]), json.loads(sys.argv[3]), result["measurements"]["volume_mm3"])
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    print(json.dumps(result, allow_nan=False))
    raise SystemExit(int(not result["ok"]))
