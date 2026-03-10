"""
Final live validation: McMaster-Carr Strut Channel Bracket (33125T421)
Using 'Carve from Block' CSG strategy and advanced verification.
"""
import json
import math
from urllib import request, error

BASE_URL = "http://localhost:8123"

def _send(command: str, arguments: dict) -> dict:
    payload = json.dumps({"command": command, "arguments": arguments}).encode()
    req = request.Request(
        f"{BASE_URL}/command",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except error.HTTPError as exc:
        body = exc.read().decode()
        try:
            detail = json.loads(body).get("error", body)
        except Exception:
            detail = body
        raise RuntimeError(f"{command} failed [{exc.code}]: {detail}") from None

def step(label: str, result: dict) -> dict:
    if not result.get("ok"):
        print(f"  [fail] {label}: {result.get('error')}")
        exit(1)
    print(f"  [ok] {label}")
    return result.get("result", result)

def main():
    print("Validating McMaster 33125T421 Strut Bracket...")
    
    # Dimensions (cm)
    WIDTH_CM = 8.890    # 3.5" (Overall width / Extrusion depth)
    HEIGHT_CM = 10.478  # 4.125" (Vertical leg)
    DEPTH_CM = 4.128    # 1.625" (Horizontal leg)
    THICK_CM = 0.635    # 0.25"
    HOLE_D_CM = 1.429   # 9/16"
    HOLE_R_CM = HOLE_D_CM / 2.0
    HOLE_EDGE_CM = 2.065 # 0.813"
    HOLE_SPAN_CM = 4.763 # 1.875"
    FILLET_R_CM = 0.3    # Bend radius
    TAPER_ANGLE = 12.8   # Calculated to match 3.5" -> 1.625" base
    
    OUTPUT_PATH = r"C:\Github\paramAItric\manual_test_output\live_mcmaster_bracket.stl"

    # 1. Setup
    step("new_design", _send("new_design", {"name": "McMaster 33125T421 Strut Bracket"}))

    # 2. Base L-bracket (XY plane cross-section)
    sk = step("create_sketch (L-profile)", _send("create_sketch", {"plane": "xy", "name": "L-Profile"}))
    sk_token = sk["sketch"]["token"]
    
    step("draw_l_bracket_profile", _send("draw_l_bracket_profile", {
        "width_cm": DEPTH_CM,
        "height_cm": HEIGHT_CM,
        "leg_thickness_cm": THICK_CM,
        "sketch_token": sk_token
    }))
    
    profiles = step("list_profiles", _send("list_profiles", {"sketch_token": sk_token}))
    profile_token = profiles["profiles"][0]["token"]
    
    res_extrude = step("extrude L-bracket", _send("extrude_profile", {
        "profile_token": profile_token,
        "distance_cm": WIDTH_CM,
        "body_name": "Strut Bracket",
        "operation": "new_body"
    }))
    body_token = res_extrude["body"]["token"]

    # 3. Taper Cuts (YZ plane, Front Face at X=THICK_CM)
    # Sketch-X = -Global Z, Sketch-Y = Global Y
    leg_h = HEIGHT_CM - THICK_CM
    taper_offset = math.tan(math.radians(TAPER_ANGLE)) * leg_h
    
    sk_taper = step("create_sketch (Taper)", _send("create_sketch", {
        "plane": "yz", "name": "Taper Cut", "offset_cm": THICK_CM
    }))["sketch"]["token"]
    
    # Left Triangle
    step("draw_triangle (left)", _send("draw_triangle", {
        "x1_cm": 0.0, "y1_cm": THICK_CM,
        "x2_cm": 0.0, "y2_cm": HEIGHT_CM,
        "x3_cm": -taper_offset, "y3_cm": THICK_CM,
        "sketch_token": sk_taper
    }))
    
    # Right Triangle
    step("draw_triangle (right)", _send("draw_triangle", {
        "x1_cm": -WIDTH_CM, "y1_cm": THICK_CM,
        "x2_cm": -WIDTH_CM, "y2_cm": HEIGHT_CM,
        "x3_cm": -(WIDTH_CM - taper_offset), "y3_cm": THICK_CM,
        "sketch_token": sk_taper
    }))
    
    t_profiles = step("list_profiles (taper)", _send("list_profiles", {"sketch_token": sk_taper}))
    for i, p in enumerate(t_profiles["profiles"]):
        step(f"extrude cut taper {i}", _send("extrude_profile", {
            "profile_token": p["token"],
            "distance_cm": 10.0,
            "symmetric": True,
            "body_name": "Strut Bracket",
            "operation": "cut",
            "target_body_token": body_token
        }))

    # 4. Vertical holes (YZ plane)
    sk_v = step("create_sketch (vertical holes)", _send("create_sketch", {
        "plane": "yz", "name": "Vertical Holes", "offset_cm": THICK_CM
    }))["sketch"]["token"]
    
    for label, vy in [("bottom", HOLE_EDGE_CM), ("top", HOLE_EDGE_CM + HOLE_SPAN_CM)]:
        step(f"draw_circle vert-{label}", _send("draw_circle", {
            "center_x_cm": -(WIDTH_CM / 2.0),
            "center_y_cm": vy,
            "radius_cm": HOLE_R_CM,
            "sketch_token": sk_v
        }))
        
    v_profiles = step("list_profiles (vert holes)", _send("list_profiles", {"sketch_token": sk_v}))
    for i, p in enumerate(v_profiles["profiles"]):
        step(f"extrude cut vert hole {i}", _send("extrude_profile", {
            "profile_token": p["token"],
            "distance_cm": 10.0,
            "symmetric": True,
            "body_name": "Strut Bracket",
            "operation": "cut",
            "target_body_token": body_token
        }))

    # 5. Horizontal holes (XZ plane)
    sk_h = step("create_sketch (horiz holes)", _send("create_sketch", {
        "plane": "xz", "name": "Horizontal Holes", "offset_cm": THICK_CM
    }))["sketch"]["token"]
    
    for vz in [HOLE_EDGE_CM, WIDTH_CM - HOLE_EDGE_CM]:
        step(f"draw_circle horiz", _send("draw_circle", {
            "center_x_cm": DEPTH_CM / 2.0,
            "center_y_cm": -vz,
            "radius_cm": HOLE_R_CM,
            "sketch_token": sk_h
        }))
        
    h_profiles = step("list_profiles (horiz holes)", _send("list_profiles", {"sketch_token": sk_h}))
    for i, p in enumerate(h_profiles["profiles"]):
        step(f"extrude cut horiz hole {i}", _send("extrude_profile", {
            "profile_token": p["token"],
            "distance_cm": 10.0,
            "symmetric": True,
            "body_name": "Strut Bracket",
            "operation": "cut",
            "target_body_token": body_token
        }))

    # 6. Fillet
    step("apply_fillet", _send("apply_fillet", {"body_token": body_token, "radius_cm": FILLET_R_CM}))

    # 7. Verify and Export
    res_info = step("get_body_info", _send("get_body_info", {"body_token": body_token}))
    info = res_info["body_info"]
    print(f"  Final Faces: {info['face_count']} ({info.get('face_type_counts')})")
    print(f"  Final BBox:  {info['bounding_box']}")
    
    step("export_stl", _send("export_stl", {"body_token": body_token, "output_path": OUTPUT_PATH}))
    step("convert_to_component", _send("convert_bodies_to_components", {"body_tokens": [body_token]}))

    print("\n[pass] McMaster Strut Bracket Validated!")

if __name__ == "__main__":
    main()
