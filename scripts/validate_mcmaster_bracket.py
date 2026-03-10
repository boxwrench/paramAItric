"""
One-off live validation: McMaster-Carr Strut Channel Bracket (33125T421)

Dimensions from McMaster drawing (converted to cm):
  Horizontal leg width : 3.5"  = 8.890 cm
  Vertical leg height  : 4.125"= 10.478 cm
  Depth (extrude)      : 1.625"= 4.128 cm
  Material thickness   : 0.25" = 0.635 cm
  Hole diameter        : 0.563"= 1.430 cm  (radius 0.715 cm)
  Hole edge offset     : 0.813"= 2.065 cm
  Hole spacing         : 1.875"= 4.763 cm

Also exercises: get_body_info, get_body_faces, get_body_edges,
                convert_bodies_to_components
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from urllib import request


BASE_URL = "http://localhost:8123"
OUTPUT_PATH = str(Path.cwd() / "manual_test_output" / "live_mcmaster_bracket.stl")

# -- dimensions (cm) --
WIDTH_CM      = 8.890   # horizontal leg, total width
HEIGHT_CM     = 10.478  # vertical leg, total height
DEPTH_CM      = 4.128   # extrude depth (bracket depth)
THICK_CM      = 0.635   # material thickness
HOLE_R_CM     = 0.715   # hole radius (0.563" dia / 2)
HOLE_EDGE_CM  = 2.065   # hole center to edge offset
HOLE_SPAN_CM  = 4.763   # center-to-center hole spacing

# -- expected volume (cm³) --
# L-bracket solid = two rectangular slabs sharing a corner
_HORIZ = WIDTH_CM * THICK_CM * DEPTH_CM
_VERT  = (HEIGHT_CM - THICK_CM) * THICK_CM * DEPTH_CM
_HOLE  = math.pi * HOLE_R_CM**2 * THICK_CM          # one through-hole (all 4 cut through THICK_CM)
EXPECTED_VOLUME_CM3 = _HORIZ + _VERT - 4 * _HOLE    # subtract 4 holes
VOLUME_TOLERANCE    = 0.5                            # ±0.5 cm³ for rounding / mesh precision


def _send(command: str, arguments: dict) -> dict:
    from urllib import error as url_error
    payload = json.dumps({"command": command, "arguments": arguments}).encode()
    req = request.Request(
        f"{BASE_URL}/command",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except url_error.HTTPError as exc:
        body = exc.read().decode()
        try:
            detail = json.loads(body).get("error", body)
        except Exception:
            detail = body
        raise RuntimeError(f"{command} failed [{exc.code}]: {detail}") from None
    if not result.get("ok"):
        raise RuntimeError(f"{command} failed: {result}")
    return result


def _result(resp: dict) -> dict:
    r = resp.get("result")
    if not isinstance(r, dict):
        raise RuntimeError(f"No result in response: {resp}")
    return r


def assert_one_body(label: str) -> None:
    """Verify the design still has exactly one body after a cut."""
    resp = _send("list_design_bodies", {})
    count = _result(resp)["body_count"]
    if count != 1:
        raise RuntimeError(
            f"Body count after {label!r}: expected 1, got {count}. "
            "A cut split the body — geometry error."
        )
    print(f"  [ok] body_count=1 after {label}")


def step(label: str, resp: dict) -> dict:
    r = _result(resp)
    print(f"  [ok] {label}")
    return r


def main() -> None:
    # ------------------------------------------------------------------ health
    with request.urlopen(f"{BASE_URL}/health", timeout=5) as resp:
        health = json.loads(resp.read().decode())
    assert health.get("ok"), f"Bridge not healthy: {health}"
    print("[ok] health")

    # ---------------------------------------------------------- 1. new design
    step("new_design", _send("new_design", {"name": "McMaster 33125T421 Strut Bracket"}))

    # ---------------------------------------- 2. L-bracket base sketch + extrude
    sk = step("create_sketch (L-profile, XY)", _send("create_sketch", {
        "plane": "xy", "name": "L-Bracket Profile",
    }))
    sketch_token = sk["sketch"]["token"]

    step("draw_l_bracket_profile", _send("draw_l_bracket_profile", {
        "sketch_token": sketch_token,
        "width_cm": WIDTH_CM,
        "height_cm": HEIGHT_CM,
        "leg_thickness_cm": THICK_CM,
    }))

    profiles = step("list_profiles", _send("list_profiles", {"sketch_token": sketch_token}))
    profile_token = profiles["profiles"][0]["token"]

    body_resp = step("extrude L-bracket", _send("extrude_profile", {
        "profile_token": profile_token,
        "distance_cm": DEPTH_CM,
        "body_name": "Strut Channel Bracket",
        "operation": "new_body",
    }))
    body_token = body_resp["body"]["token"]

    # ----------------------------- 3. Horizontal leg holes (XZ plane, no offset)
    # XZ plane at Y=0 (bottom face of horizontal leg). Cut fires in +Y through THICK_CM.
    # Hole centers (XZ sketch coords): x=world-X, y=world-Z
    #   Left:  x=HOLE_EDGE_CM,             z=DEPTH_CM/2
    #   Right: x=WIDTH_CM-HOLE_EDGE_CM,    z=DEPTH_CM/2
    # One sketch per hole so each cut is independent.
    # On XZ plane sketches: sketch-Y is NEGATED relative to world-Z.
    # (observed: negative sketch-Y → positive global Z, per shaft_coupler validation)
    # So to place hole at world-Z = DEPTH_CM/2, use sketch center_y = -(DEPTH_CM/2).
    z_center_sketch = -(DEPTH_CM / 2.0)

    for label, hx in [
        ("horiz-left",  HOLE_EDGE_CM),
        ("horiz-right", WIDTH_CM - HOLE_EDGE_CM),
    ]:
        sk_h = step(f"create_sketch ({label})", _send("create_sketch", {
            "plane": "xz", "name": f"Hole {label}",
        }))
        sk_h_token = sk_h["sketch"]["token"]
        step(f"draw_circle {label}", _send("draw_circle", {
            "sketch_token": sk_h_token,
            "center_x_cm": hx,
            "center_y_cm": z_center_sketch,
            "radius_cm": HOLE_R_CM,
        }))
        profiles_h = step(f"list_profiles ({label})", _send("list_profiles", {"sketch_token": sk_h_token}))
        step(f"extrude cut {label}", _send("extrude_profile", {
            "profile_token": profiles_h["profiles"][0]["token"],
            "distance_cm": THICK_CM,
            "body_name": "Strut Channel Bracket",
            "operation": "cut",
            "target_body_token": body_token,
        }))
        assert_one_body(label)

    # ----------------------------- 4. Vertical leg holes (YZ plane, +X cut)
    # The vertical leg is 0.635cm thick in X (X: 0 → THICK_CM).
    # Holes go THROUGH the X-thickness — not the depth.
    # YZ plane convention:
    #   sketch-X → world-Y (positive)
    #   sketch-Y → world-Z (positive, YZ viewed from +X)
    # Fusion's YZ plane normal points in -X. Extrude fires in -X from the sketch plane.
    # Vertical leg is at X=0 → THICK_CM. To cut through it, place the sketch at
    # X=THICK_CM (offset_cm=THICK_CM) so the -X extrude travels from X=THICK_CM back to X=0.

    for label, vy in [
        ("vert-bottom", HOLE_EDGE_CM),
        ("vert-top",    HOLE_EDGE_CM + HOLE_SPAN_CM),
    ]:
        sk_v = step(f"create_sketch ({label})", _send("create_sketch", {
            "plane": "yz", "name": f"Hole {label}",
            "offset_cm": 0.0,
        }))
        sk_v_token = sk_v["sketch"]["token"]
        step(f"draw_circle {label}", _send("draw_circle", {
            "sketch_token": sk_v_token,
            "center_x_cm": -(DEPTH_CM / 2.0),
            "center_y_cm": vy,
            "radius_cm": HOLE_R_CM,
        }))
        profiles_v = step(f"list_profiles ({label})", _send("list_profiles", {"sketch_token": sk_v_token}))
        step(f"extrude cut {label}", _send("extrude_profile", {
            "profile_token": profiles_v["profiles"][0]["token"],
            "distance_cm": THICK_CM,
            "body_name": "Strut Channel Bracket",
            "operation": "cut",
            "target_body_token": body_token,
        }))
        assert_one_body(label)

    # ---------------------------------------- 5. Export STL
    step("export_stl", _send("export_stl", {
        "body_token": body_token,
        "output_path": OUTPUT_PATH,
    }))

    # ---------------------------------------- 6. Inspect — get_body_info + volume/bbox assert
    body_info_resp = step("get_body_info", _send("get_body_info", {"body_token": body_token}))
    info = body_info_resp["body_info"]
    vol = info.get("volume_cm3")
    print(f"     face_count={info.get('face_count')}  edge_count={info.get('edge_count')}  "
          + (f"volume_cm3={vol:.4f}" if vol else "volume_cm3=N/A"))
    # Volume assertion
    if vol is not None:
        delta = abs(vol - EXPECTED_VOLUME_CM3)
        if delta > VOLUME_TOLERANCE:
            raise RuntimeError(
                f"Volume mismatch: got {vol:.4f} cm3, expected {EXPECTED_VOLUME_CM3:.4f} cm3 "
                f"(delta={delta:.4f}, tolerance={VOLUME_TOLERANCE}). Geometry error."
            )
        print(f"     [ok] volume {vol:.4f} cm3 within {VOLUME_TOLERANCE} cm3 of expected {EXPECTED_VOLUME_CM3:.4f}")
    # Bounding-box assertion — bracket must still span its full designed extents
    bb = info.get("bounding_box", {})
    bb_x = bb.get("max_x", 0) - bb.get("min_x", 0)
    bb_y = bb.get("max_y", 0) - bb.get("min_y", 0)
    bb_z = bb.get("max_z", 0) - bb.get("min_z", 0)
    for axis, actual, expected in [("X", bb_x, WIDTH_CM), ("Y", bb_y, HEIGHT_CM), ("Z", bb_z, DEPTH_CM)]:
        if abs(actual - expected) > 0.05:
            raise RuntimeError(
                f"Bounding box {axis}-extent mismatch: got {actual:.4f}, expected {expected:.4f}. "
                "A fragment or misplaced cut is likely."
            )
    print(f"     [ok] bounding box {bb_x:.3f} x {bb_y:.3f} x {bb_z:.3f} cm")

    # ---------------------------------------- 7. Inspect — get_body_faces
    faces_resp = step("get_body_faces", _send("get_body_faces", {"body_token": body_token}))
    faces = faces_resp["body_faces"]
    face_types = {}
    for f in faces:
        t = f.get("type", "unknown")
        face_types[t] = face_types.get(t, 0) + 1
    print(f"     faces: {len(faces)} total — {face_types}")

    # ---------------------------------------- 8. Inspect — get_body_edges
    edges_resp = step("get_body_edges", _send("get_body_edges", {"body_token": body_token}))
    edges = edges_resp["body_edges"]
    edge_types = {}
    for e in edges:
        t = e.get("type", "unknown")
        edge_types[t] = edge_types.get(t, 0) + 1
    print(f"     edges: {len(edges)} total — {edge_types}")

    # ---------------------------------------- 9. convert_bodies_to_components
    comp_resp = step("convert_bodies_to_components", _send("convert_bodies_to_components", {
        "body_tokens": [body_token],
        "component_names": ["Strut Channel Bracket"],
    }))
    comps = comp_resp["components"]
    assert len(comps) == 1
    comp_token = comps[0]["component_token"]
    print(f"     component_token={comp_token}  name={comps[0]['component_name']!r}")

    print()
    print(f"[pass] Strut Channel Bracket")
    print(f"       STL -> {OUTPUT_PATH}")
    print(f"       faces={len(faces)}  edges={len(edges)}  volume={vol:.4f} cm3  components=1")


if __name__ == "__main__":
    main()
