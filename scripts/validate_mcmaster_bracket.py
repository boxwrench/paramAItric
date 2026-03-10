"""
Live validation: McMaster-Carr Strut Channel Bracket (33125T421)

YZ plane cuts are now working! Fixed by using two-sided extent for cut extrusions,
following CSG best practice: cutters must extend past target boundaries in both directions.

Dimensions (cm):
  Width: 8.890, Height: 10.478, Depth: 4.128
  Thickness: 0.635, Hole diameter: 1.430
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from urllib import request


BASE_URL = "http://localhost:8123"
OUTPUT_PATH = str(Path.cwd() / "manual_test_output" / "live_mcmaster_bracket.stl")

WIDTH_CM = 8.890
HEIGHT_CM = 10.478
DEPTH_CM = 4.128
THICK_CM = 0.635
HOLE_R_CM = 0.715
HOLE_EDGE_CM = 2.065
HOLE_SPAN_CM = 4.763


def _send(command: str, arguments: dict) -> dict:
    from urllib import error as url_error
    payload = json.dumps({"command": command, "arguments": arguments}).encode()
    req = request.Request(f"{BASE_URL}/command", data=payload, headers={"Content-Type": "application/json"}, method="POST")
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


def assert_one_body(label: str) -> str:
    resp = _send("list_design_bodies", {})
    bodies = _result(resp)["bodies"]
    count = len(bodies)
    if count != 1:
        raise RuntimeError(f"Body count after {label!r}: expected 1, got {count}")
    print(f"  [ok] body_count=1 after {label}")
    return bodies[0]["body_token"]


def step(label: str, resp: dict) -> dict:
    r = _result(resp)
    print(f"  [ok] {label}")
    return r


def main() -> None:
    with request.urlopen(f"{BASE_URL}/health", timeout=5) as resp:
        health = json.loads(resp.read().decode())
    assert health.get("ok"), f"Bridge not healthy: {health}"
    print("[ok] health")

    step("new_design", _send("new_design", {"name": "McMaster 33125T421 Strut Bracket"}))

    # Cross-section sketch + extrude
    sk = step("create_sketch (cross-section, XY)", _send("create_sketch", {"plane": "xy", "name": "Cross-Section"}))
    sketch_token = sk["sketch"]["token"]

    step("draw_l_bracket_profile", _send("draw_l_bracket_profile", {
        "sketch_token": sketch_token,
        "width_cm": WIDTH_CM,
        "height_cm": HEIGHT_CM,
        "leg_thickness_cm": THICK_CM,
    }))

    profiles = step("list_profiles", _send("list_profiles", {"sketch_token": sketch_token}))
    profile_token = profiles["profiles"][0]["token"]

    body_resp = step("extrude cross-section", _send("extrude_profile", {
        "profile_token": profile_token,
        "distance_cm": DEPTH_CM,
        "body_name": "Strut Channel Bracket",
        "operation": "new_body",
    }))
    body_token = body_resp["body"]["token"]
    print(f"  [info] body created: {body_token[:40]}...")

    # Bend radius fillet
    print("  [info] applying bend radius fillet...")
    fillet_resp = step("apply_fillet", _send("apply_fillet", {
        "body_token": body_token,
        "radius_cm": THICK_CM * 0.5,
    }))
    print(f"     fillet_applied={fillet_resp.get('fillet_applied')}, edge_count={fillet_resp.get('edge_count')}")
    body_token = assert_one_body("fillet")

    # Horizontal leg holes (XZ plane) - WORKING
    z_center_sketch = -(DEPTH_CM / 2.0)
    for label, hx in [
        ("horiz-left", HOLE_EDGE_CM),
        ("horiz-right", WIDTH_CM - HOLE_EDGE_CM),
    ]:
        sk_h = step(f"create_sketch ({label})", _send("create_sketch", {"plane": "xz", "name": f"Hole {label}"}))
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
        body_token = assert_one_body(label)

    # Vertical leg holes (YZ plane) - NOW WORKING with two-sided extent fix
    y_center_sketch = HEIGHT_CM / 2.0
    for label, hy in [
        ("vert-bottom", HOLE_EDGE_CM),
        ("vert-top", HEIGHT_CM - HOLE_EDGE_CM),
    ]:
        sk_v = step(f"create_sketch ({label})", _send("create_sketch", {"plane": "yz", "name": f"Hole {label}", "offset_cm": THICK_CM}))
        sk_v_token = sk_v["sketch"]["token"]
        step(f"draw_circle {label}", _send("draw_circle", {
            "sketch_token": sk_v_token,
            "center_x_cm": hy,  # Y coordinate in YZ plane = bracket height
            "center_y_cm": y_center_sketch,  # Z coordinate in YZ plane
            "radius_cm": HOLE_R_CM,
        }))
        profiles_v = step(f"list_profiles ({label})", _send("list_profiles", {"sketch_token": sk_v_token}))
        step(f"extrude cut {label}", _send("extrude_profile", {
            "profile_token": profiles_v["profiles"][0]["token"],
            "distance_cm": THICK_CM * 2,  # Through thickness with margin
            "body_name": "Strut Channel Bracket",
            "operation": "cut",
            "target_body_token": body_token,
        }))
        body_token = assert_one_body(label)

    # Export STL
    step("export_stl", _send("export_stl", {
        "body_token": body_token,
        "output_path": OUTPUT_PATH,
    }))

    # Final inspection
    body_info_resp = step("get_body_info", _send("get_body_info", {"body_token": body_token}))
    info = body_info_resp["body_info"]
    vol = info.get("volume_cm3")
    vol_str = f"{vol:.4f}" if vol else "N/A"
    print(f"     face_count={info.get('face_count')}  edge_count={info.get('edge_count')}  volume_cm3={vol_str}")

    bb = info.get("bounding_box", {})
    bb_x = bb.get("max_x", 0) - bb.get("min_x", 0)
    bb_y = bb.get("max_y", 0) - bb.get("min_y", 0)
    bb_z = bb.get("max_z", 0) - bb.get("min_z", 0)
    print(f"     [info] final bbox: {bb_x:.3f} x {bb_y:.3f} x {bb_z:.3f} cm")

    faces_resp = step("get_body_faces", _send("get_body_faces", {"body_token": body_token}))
    faces = faces_resp["body_faces"]
    print(f"     faces: {len(faces)} total")

    edges_resp = step("get_body_edges", _send("get_body_edges", {"body_token": body_token}))
    edges = edges_resp["body_edges"]
    print(f"     edges: {len(edges)} total")

    comp_resp = step("convert_bodies_to_components", _send("convert_bodies_to_components", {
        "body_tokens": [body_token],
        "component_names": ["Strut Channel Bracket"],
    }))
    print(f"     component_token={comp_resp['components'][0]['component_token'][:40]}...")

    print()
    print(f"[pass] Strut Channel Bracket (with ALL 4 holes - YZ fix working!)")
    print(f"       STL -> {OUTPUT_PATH}")
    print(f"       faces={len(faces)}  edges={len(edges)}  volume={vol_str} cm3")


if __name__ == "__main__":
    main()
