"""
Freeform A - Custom Panel Mount Bracket

Recipe harness for the freeform benchmark corpus.
This script is not the architecture spec.
See `internal/freeform-architecture.md` for the freeform session contract.
"""
from mcp_server.server import ParamAIToolServer

def main():
    server = ParamAIToolServer()
    print("=== STARTING FREEFORM A: CUSTOM PANEL MOUNT BRACKET ===")
    
    # 1. Start Session
    manifest = ["L-profile body", "2 vertical leg holes", "2 horizontal leg holes", "inner bend fillet"]
    server.start_freeform_session({
        "design_name": "FM-A Custom Panel Mount Bracket",
        "target_features": manifest
    })
    print("[1] Session Started with Manifest.")

    # 2. Mutation: Create XY Sketch
    res_sk = server.create_sketch(plane="xy", name="Cross Section")
    sk_token = res_sk["result"]["sketch"]["token"]
    server.commit_verification({"notes": "XY Sketch created.", "expected_body_count": 0})
    print("[2] XY Sketch Created & Verified.")

    # 3. Mutation: Draw L-Profile
    # Leg1 (Horiz) = 14.0, Leg2 (Vert) = 9.0, Thick = 0.35
    server.draw_l_bracket_profile(width_cm=14.0, height_cm=9.0, leg_thickness_cm=0.35, sketch_token=sk_token)
    res_prof = server.list_profiles(sk_token)
    prof_token = res_prof["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "L-Profile profile resolved.", "expected_body_count": 0})
    print("[3] L-Profile Geometry Drawn & Verified.")

    # 4. Mutation: Extrude to full width (5.0 cm)
    res_ext = server.extrude_profile(profile_token=prof_token, distance_cm=5.0, body_name="Panel Bracket")
    body_token = res_ext["result"]["body"]["token"]
    
    # [VERIFY] L-profile body
    info = server.get_body_info({"body_token": body_token})["result"]["body_info"]
    server.commit_verification({
        "notes": "L-profile body verified: 14x9x5cm.",
        "expected_body_count": 1,
        "resolved_features": ["L-profile body"]
    })
    print("[4] FEATURE RESOLVED: L-profile body")

    # 5. Mutation: Vertical Holes (YZ Plane at X=0.35)
    sk_v_holes_res = server.create_sketch(plane="yz", name="Vertical Holes", offset_cm=0.35)
    sk_v_holes = sk_v_holes_res["result"]["sketch"]["token"]
    server.commit_verification({"notes": "YZ Vertical holes sketch created.", "expected_body_count": 1})
    
    # Mutation: Draw Circle 1
    server.draw_circle(center_x_cm=-2.0, center_y_cm=4.5, radius_cm=0.2, sketch_token=sk_v_holes)
    server.commit_verification({"notes": "Circle 1 drawn.", "expected_body_count": 1})

    # Mutation: Draw Circle 2
    server.draw_circle(center_x_cm=-3.0, center_y_cm=4.5, radius_cm=0.2, sketch_token=sk_v_holes)
    server.commit_verification({"notes": "Circle 2 drawn.", "expected_body_count": 1})

    # Mutation: Cut Holes
    v_profs = server.list_profiles(sk_v_holes)["result"]["profiles"]
    # We can only cut one profile per mutation in freeform if we want strict logging, 
    # but since they are in one sketch, we can loop if we verify each.
    for i, p in enumerate(v_profs):
        server.extrude_profile(profile_token=p["token"], distance_cm=1.0, symmetric=True, operation="cut", target_body_token=body_token, body_name="Panel Bracket")
        server.commit_verification({
            "notes": f"Vertical hole {i+1} cut.", 
            "expected_body_count": 1,
            "resolved_features": ["2 vertical leg holes"] if i == len(v_profs)-1 else None
        })
    print("[5] FEATURE RESOLVED: 2 vertical leg holes")

    # 6. Mutation: Horizontal Holes (XZ Plane at Y=0.35)
    sk_h_holes_res = server.create_sketch(plane="xz", name="Horizontal Holes", offset_cm=0.35)
    sk_h_holes = sk_h_holes_res["result"]["sketch"]["token"]
    server.commit_verification({"notes": "XZ Horizontal holes sketch created.", "expected_body_count": 1})

    # Mutation: Draw Circle 1
    server.draw_circle(center_x_cm=1.5, center_y_cm=-2.5, radius_cm=0.2, sketch_token=sk_h_holes)
    server.commit_verification({"notes": "Circle 1 drawn.", "expected_body_count": 1})

    # Mutation: Draw Circle 2
    server.draw_circle(center_x_cm=12.5, center_y_cm=-2.5, radius_cm=0.2, sketch_token=sk_h_holes)
    server.commit_verification({"notes": "Circle 2 drawn.", "expected_body_count": 1})

    # Mutation: Cut Holes
    h_profs = server.list_profiles(sk_h_holes)["result"]["profiles"]
    for i, p in enumerate(h_profs):
        server.extrude_profile(profile_token=p["token"], distance_cm=1.0, symmetric=True, operation="cut", target_body_token=body_token, body_name="Panel Bracket")
        server.commit_verification({
            "notes": f"Horizontal hole {i+1} cut.", 
            "expected_body_count": 1,
            "resolved_features": ["2 horizontal leg holes"] if i == len(h_profs)-1 else None
        })
    print("[6] FEATURE RESOLVED: 2 horizontal leg holes")

    # 7. Mutation: Inner Bend Fillet
    server.apply_fillet(body_token=body_token, radius_cm=0.3)
    server.commit_verification({
        "notes": "Fillet applied.", 
        "expected_body_count": 1, 
        "resolved_features": ["inner bend fillet"]
    })
    print("[7] FEATURE RESOLVED: inner bend fillet")

    # 8. Final Compliance Audit
    print("\n--- FINAL COMPLIANCE AUDIT ---")
    end_res = server.end_freeform_session({})
    if end_res["ok"]:
        print("[+] AUDIT PASSED: All features resolved.")
        server.export_stl(body_token=body_token, output_path="manual_test_output/fm_a_bracket.stl")
        print("[+] Model Exported.")
    else:
        print(f"[-] AUDIT FAILED: {end_res.get('error')}")

    print("=== SESSION ENDED ===")

if __name__ == "__main__":
    main()
