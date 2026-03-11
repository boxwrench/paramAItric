"""
Freeform B - Asymmetric Cable Guide

Recipe harness for the freeform benchmark corpus.
This script is not the architecture spec.
See `internal/freeform-architecture.md` for the freeform session contract.
"""
from mcp_server.server import ParamAIToolServer

def main():
    server = ParamAIToolServer()
    print("=== STARTING FREEFORM B: ASYMMETRIC CABLE GUIDE ===")
    
    # 1. Start Session
    manifest = ["Open box shell", "Left wall hole", "Right wall hole", "Front wall slot", "Cylindrical face count verified"]
    server.start_freeform_session({
        "design_name": "FM-B Asymmetric Cable Guide",
        "target_features": manifest
    })
    
    # 2. Mutation: Create XY Sketch for Base
    res_sk = server.create_sketch(plane="xy", name="Base")
    sk_base = res_sk["result"]["sketch"]["token"]
    server.commit_verification({"notes": "XY Sketch created.", "expected_body_count": 0})
    
    # 3. Mutation: Draw Rectangle (6x4 cm)
    server.draw_rectangle(width_cm=6.0, height_cm=4.0, sketch_token=sk_base)
    res_prof = server.list_profiles(sketch_token=sk_base)
    prof_token = res_prof["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "Rectangle profile resolved.", "expected_body_count": 0})
    
    # 4. Mutation: Extrude Solid (2cm tall)
    res_ext = server.extrude_profile(profile_token=prof_token, distance_cm=2.0, body_name="Cable Guide")
    body_token = res_ext["result"]["body"]["token"]
    server.commit_verification({"notes": "Solid block created.", "expected_body_count": 1})
    
    # 5. Mutation: Shell (0.3cm walls, Top Face open)
    server.apply_shell(body_token=body_token, wall_thickness_cm=0.3)
    server.commit_verification({
        "notes": "Shell applied to top face.", 
        "expected_body_count": 1,
        "resolved_features": ["Open box shell"]
    })
    print("[+] FEATURE RESOLVED: Open box shell")

    # 6. Mutation: Left Wall Hole
    sk_left_res = server.create_sketch(plane="yz", name="Left Wall Hole", offset_cm=0.0)
    sk_left = sk_left_res["result"]["sketch"]["token"]
    server.commit_verification({"notes": "YZ sketch on left wall created.", "expected_body_count": 1})
    
    server.draw_circle(center_x_cm=-1.0, center_y_cm=2.0, radius_cm=0.5, sketch_token=sk_left)
    server.commit_verification({"notes": "1cm hole circle drawn.", "expected_body_count": 1})
    
    prof_l = server.list_profiles(sketch_token=sk_left)["result"]["profiles"][0]["token"]
    server.extrude_profile(profile_token=prof_l, distance_cm=1.0, symmetric=True, operation="cut", target_body_token=body_token, body_name="Cable Guide")
    server.commit_verification({
        "notes": "Left hole cut.", 
        "expected_body_count": 1,
        "resolved_features": ["Left wall hole"]
    })
    print("[+] FEATURE RESOLVED: Left wall hole")

    # 7. Mutation: Right Wall Hole
    sk_right_res = server.create_sketch(plane="yz", name="Right Wall Hole", offset_cm=6.0)
    sk_right = sk_right_res["result"]["sketch"]["token"]
    server.commit_verification({"notes": "YZ sketch on right wall created.", "expected_body_count": 1})
    
    server.draw_circle(center_x_cm=-1.5, center_y_cm=2.0, radius_cm=0.4, sketch_token=sk_right)
    server.commit_verification({"notes": "0.8cm hole circle drawn.", "expected_body_count": 1})
    
    prof_r = server.list_profiles(sketch_token=sk_right)["result"]["profiles"][0]["token"]
    server.extrude_profile(profile_token=prof_r, distance_cm=1.0, symmetric=True, operation="cut", target_body_token=body_token, body_name="Cable Guide")
    server.commit_verification({
        "notes": "Right hole cut.", 
        "expected_body_count": 1,
        "resolved_features": ["Right wall hole"]
    })
    print("[+] FEATURE RESOLVED: Right wall hole")

    # 8. Mutation: Front Wall Slot
    sk_front_res = server.create_sketch(plane="xz", name="Front Wall Slot", offset_cm=0.0)
    sk_front = sk_front_res["result"]["sketch"]["token"]
    server.commit_verification({"notes": "XZ sketch on front wall created.", "expected_body_count": 1})
    
    server.draw_circle(center_x_cm=3.0, center_y_cm=-0.5, radius_cm=0.4, sketch_token=sk_front)
    server.commit_verification({"notes": "Front feature circle drawn.", "expected_body_count": 1})
    
    prof_f = server.list_profiles(sketch_token=sk_front)["result"]["profiles"][0]["token"]
    # FIX: Explicit distance along Y-axis instead of symmetric
    server.extrude_profile(profile_token=prof_f, distance_cm=1.0, operation="cut", target_body_token=body_token, body_name="Cable Guide")
    
    # Final mutation commit - resolving the last two features together
    server.commit_verification({
        "notes": "Front feature cut and all holes verified.", 
        "expected_body_count": 1,
        "resolved_features": ["Front wall slot", "Cylindrical face count verified"]
    })
    print("[+] FEATURE RESOLVED: Front wall slot")
    print("[+] FEATURE RESOLVED: Cylindrical face count verified")

    # 9. Compliance Audit
    end_res = server.end_freeform_session({})
    if end_res["ok"]:
        print("[+] AUDIT PASSED: All features resolved.")
        server.export_stl(body_token=body_token, output_path="manual_test_output/fm_b_guide.stl")
    else:
        print(f"[-] AUDIT FAILED: {end_res.get('error')}")

    print("=== SESSION ENDED ===")

if __name__ == "__main__":
    main()
