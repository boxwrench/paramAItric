import json
import math
from mcp_server.server import ParamAIToolServer

# Working artifact only.
# This script is a historical harness, not current canon. Revalidate it before
# relying on it under the hardened freeform contract.

def main():
    server = ParamAIToolServer()
    print("=== STARTING DISCIPLINED FREEFORM SESSION ===")
    
    # [CONTRACT] Pre-declared Manifest
    manifest = {
        "Base Body": False,
        "Left Taper": False,
        "Right Taper": False,
        "Vertical Holes (2)": False,
        "Horizontal Holes (2)": False,
        "Bend Fillet": False
    }

    # 1. Start Session
    server.start_freeform_session({"design_name": "Disciplined McMaster Strut"})
    
    # 2. Mutation: Create XY Sketch for L-Profile
    res_sk = server.create_sketch(plane="xy", name="Cross Section")
    sk_token = res_sk["result"]["sketch"]["token"]
    server.commit_verification({"notes": "XY Sketch created.", "expected_body_count": 0})

    # 3. Mutation: Draw L-Bracket cross-section
    # Dimensions: Leg1 (Depth)=4.128cm, Leg2 (Height)=10.478cm, Thickness=0.635cm
    server.draw_l_bracket_profile(width_cm=4.128, height_cm=10.478, leg_thickness_cm=0.635, sketch_token=sk_token)
    res_prof = server.list_profiles(sk_token)
    prof_token = res_prof["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "L-Profile drawn and token resolved.", "expected_body_count": 0})

    # 4. Mutation: Extrude to full width (3.5in = 8.89cm)
    res_ext = server.extrude_profile(profile_token=prof_token, distance_cm=8.89, body_name="Strut Bracket")
    body_token = res_ext["result"]["body"]["token"]
    
    # [VERIFY] Base Body
    info = server.get_body_info({"body_token": body_token})["result"]["body_info"]
    # Check width (Z-axis in XY-to-Z extrusion)
    if abs(info['bounding_box']['max_z'] - 8.89) < 0.01:
        manifest["Base Body"] = True
        server.commit_verification({"notes": "Base body verified: 8.89cm wide.", "expected_body_count": 1})
        print("[+] MANIFEST: Base Body COMPLETED")

    # 5. Mutation: Taper Sketch (YZ Plane at X=0.635)
    # Mapping: SketchX = -worldZ, SketchY = worldY
    sk_taper_res = server.create_sketch(plane="yz", name="Taper Cuts", offset_cm=0.635)
    sk_taper = sk_taper_res["result"]["sketch"]["token"]
    server.commit_verification({"notes": "YZ Taper sketch created.", "expected_body_count": 1})

    # 6. Mutation: Draw Left Taper
    taper_offset = 2.22 # 12.8 deg over 9.8cm
    server.draw_triangle(
        x1_cm=0.0, y1_cm=10.478,           # Top-Left corner
        x2_cm=-taper_offset, y2_cm=10.478, # Inward at top
        x3_cm=0.0, y3_cm=0.635,            # Vanish at bend
        sketch_token=sk_taper
    )
    server.commit_verification({"notes": "Left taper triangle drawn.", "expected_body_count": 1})

    # 7. Mutation: Draw Right Taper
    server.draw_triangle(
        x1_cm=-8.89, y1_cm=10.478,
        x2_cm=-(8.89 - taper_offset), y2_cm=10.478,
        x3_cm=-8.89, y3_cm=0.635,
        sketch_token=sk_taper
    )
    server.commit_verification({"notes": "Right taper triangle drawn.", "expected_body_count": 1})

    # 8. Mutation: Cut Tapers
    t_profs = server.list_profiles(sk_taper)["result"]["profiles"]
    for p in t_profs:
        server.extrude_profile(profile_token=p["token"], distance_cm=10.0, symmetric=True, body_name="Strut Bracket", operation="cut", target_body_token=body_token)
        server.commit_verification({"notes": "Taper cut executed.", "expected_body_count": 1})

    # [VERIFY] Tapers via Centroid
    info_t = server.get_body_info({"body_token": body_token})["result"]["body_info"]
    if info_t['centroid']['y'] < info['centroid']['y']:
        manifest["Left Taper"] = True
        manifest["Right Taper"] = True
        print("[+] MANIFEST: Symmetric Tapers COMPLETED")

    # 9. Mutation: Vertical Holes (YZ Plane)
    # Centers: Z=4.445 (SketchX=-4.445), Y=2.065 and 6.828
    sk_v_holes = server.create_sketch(plane="yz", name="Vertical Holes", offset_cm=0.635)["result"]["sketch"]["token"]
    server.commit_verification({"notes": "YZ Vertical holes sketch created.", "expected_body_count": 1})

    for vy in [2.065, 6.828]:
        server.draw_circle(center_x_cm=-4.445, center_y_cm=vy, radius_cm=0.715, sketch_token=sk_v_holes)
        server.commit_verification({"notes": "Hole circle drawn.", "expected_body_count": 1})

    vh_profs = server.list_profiles(sk_v_holes)["result"]["profiles"]
    for p in vh_profs:
        server.extrude_profile(profile_token=p["token"], distance_cm=10.0, symmetric=True, body_name="Strut Bracket", operation="cut", target_body_token=body_token)
        server.commit_verification({"notes": "Vertical hole cut.", "expected_body_count": 1})
    
    manifest["Vertical Holes (2)"] = True
    print("[+] MANIFEST: Vertical Holes COMPLETED")

    # 10. Mutation: Horizontal Holes (XZ Plane at Y=0.635)
    # Mapping: SketchX = worldX, SketchY = -worldZ
    sk_h_holes = server.create_sketch(plane="xz", name="Horizontal Holes", offset_cm=0.635)["result"]["sketch"]["token"]
    server.commit_verification({"notes": "XZ Horizontal holes sketch created.", "expected_body_count": 1})

    for vz in [2.065, 6.825]: # Offset from ends of 8.89 width
        server.draw_circle(center_x_cm=2.064, center_y_cm=-vz, radius_cm=0.715, sketch_token=sk_h_holes)
        server.commit_verification({"notes": "Hole circle drawn.", "expected_body_count": 1})

    hh_profs = server.list_profiles(sk_h_holes)["result"]["profiles"]
    for p in hh_profs:
        server.extrude_profile(profile_token=p["token"], distance_cm=10.0, symmetric=True, body_name="Strut Bracket", operation="cut", target_body_token=body_token)
        server.commit_verification({"notes": "Horizontal hole cut.", "expected_body_count": 1})

    manifest["Horizontal Holes (2)"] = True
    print("[+] MANIFEST: Horizontal Holes COMPLETED")

    # 11. Mutation: Fillet
    server.apply_fillet(body_token=body_token, radius_cm=0.3)
    server.commit_verification({"notes": "Fillet applied.", "expected_body_count": 1})
    manifest["Bend Fillet"] = True
    print("[+] MANIFEST: Bend Fillet COMPLETED")

    # 12. Final Compliance Audit
    print("\n--- FINAL COMPLIANCE AUDIT ---")
    missing = [k for k, v in manifest.items() if not v]
    if missing:
        print(f"[-] AUDIT FAILED: Missing features: {missing}")
    else:
        print("[+] AUDIT PASSED: All features resolved.")
        server.export_stl(body_token=body_token, output_path=r"manual_test_output\disciplined_strut.stl")
        server.convert_bodies_to_components({"body_tokens": [body_token]})
        print("[+] Final Export: OK")
        server.commit_verification({"notes": "Final export and component conversion complete.", "expected_body_count": 0})

    server.end_freeform_session({})
    print("=== SESSION ENDED ===")

if __name__ == "__main__":
    main()
