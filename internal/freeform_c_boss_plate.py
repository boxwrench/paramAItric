"""
Freeform C - Stepped Boss Plate

Recipe harness for the freeform benchmark corpus.
This script is not the architecture spec.
See `internal/freeform-architecture.md` for the freeform session contract.
"""
from mcp_server.server import ParamAIToolServer

def main():
    server = ParamAIToolServer()
    print("=== STARTING FREEFORM C: STEPPED BOSS PLATE ===")
    
    # 1. Start Session
    manifest = ["Base plate", "4 corner holes", "Central boss cylinder", "Boss bore", "Top chamfer"]
    server.start_freeform_session({
        "design_name": "FM-C Stepped Boss Plate",
        "target_features": manifest
    })
    
    # 2. Base Plate
    res_sk = server.create_sketch(plane="xy", name="Base Plate")
    sk_base = res_sk["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Base sketch created.", "expected_body_count": 0})
    server.draw_rectangle(width_cm=10.0, height_cm=8.0, sketch_token=sk_base)
    prof_base = server.list_profiles(sketch_token=sk_base)["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "Base profile drawn.", "expected_body_count": 0})
    res_ext = server.extrude_profile(profile_token=prof_base, distance_cm=0.4, body_name="Boss Plate")
    body_token = res_ext["result"]["body"]["token"]
    server.commit_verification({"notes": "Base plate extruded.", "expected_body_count": 1, "resolved_features": ["Base plate"]})
    print("[+] FEATURE RESOLVED: Base plate")

    # 3. Corner Holes
    sk_holes_res = server.create_sketch(plane="xy", name="Corner Holes", offset_cm=0.4)
    sk_holes = sk_holes_res["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Hole sketch created.", "expected_body_count": 1})
    for i, (hx, hy) in enumerate([(1,1), (9,1), (1,7), (9,7)]):
        server.draw_circle(center_x_cm=hx, center_y_cm=hy, radius_cm=0.3, sketch_token=sk_holes)
        server.commit_verification({"notes": f"Circle {i+1} drawn.", "expected_body_count": 1})
    h_profs = server.list_profiles(sketch_token=sk_holes)["result"]["profiles"]
    for i, p in enumerate(h_profs):
        server.extrude_profile(profile_token=p["token"], distance_cm=1.0, operation="cut", target_body_token=body_token, body_name="Boss Plate")
        server.commit_verification({"notes": f"Hole {i+1} cut.", "expected_body_count": 1, "resolved_features": ["4 corner holes"] if i == len(h_profs)-1 else None})
    print("[+] FEATURE RESOLVED: 4 corner holes")

    # 4. Central Boss Cylinder
    sk_boss_res = server.create_sketch(plane="xy", name="Boss", offset_cm=0.4)
    sk_boss = sk_boss_res["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Boss sketch created.", "expected_body_count": 1})
    server.draw_circle(center_x_cm=5.0, center_y_cm=4.0, radius_cm=1.5, sketch_token=sk_boss)
    prof_boss = server.list_profiles(sketch_token=sk_boss)["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "Boss circle drawn.", "expected_body_count": 1})
    res_boss_ext = server.extrude_profile(profile_token=prof_boss, distance_cm=1.0, body_name="Boss Protrusion")
    boss_token = res_boss_ext["result"]["body"]["token"]
    server.commit_verification({"notes": "Boss cylinder extruded.", "expected_body_count": 2})
    server.combine_bodies(target_body_token=body_token, tool_body_token=boss_token)
    server.commit_verification({"notes": "Boss combined. Volume UP.", "expected_body_count": 1, "resolved_features": ["Central boss cylinder"]})
    print("[+] FEATURE RESOLVED: Central boss cylinder")

    # 5. Boss Bore
    sk_bore_res = server.create_sketch(plane="xy", name="Bore", offset_cm=1.4)
    sk_bore = sk_bore_res["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Bore sketch created.", "expected_body_count": 1})
    server.draw_circle(center_x_cm=5.0, center_y_cm=4.0, radius_cm=0.75, sketch_token=sk_bore)
    prof_bore = server.list_profiles(sketch_token=sk_bore)["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "Bore circle drawn.", "expected_body_count": 1})
    server.extrude_profile(profile_token=prof_bore, distance_cm=2.0, operation="cut", target_body_token=body_token, body_name="Boss Plate")
    server.commit_verification({"notes": "Boss bored. Volume DOWN.", "expected_body_count": 1, "resolved_features": ["Boss bore"]})
    print("[+] FEATURE RESOLVED: Boss bore")

    # 6. Final Compliance Audit with Deferral
    print("\n--- FINAL COMPLIANCE AUDIT ---")
    # Deferring Top chamfer because the tool is currently hardcoded for brackets.
    end_res = server.end_freeform_session({
        "deferred_features": [
            {"feature": "Top chamfer", "reason": "apply_chamfer tool is currently hardcoded for bracket geometry."}
        ]
    })
    
    if end_res["ok"]:
        print("[+] AUDIT PASSED (with Deferral): Resolved all possible features.")
        server.export_stl(body_token=body_token, output_path="manual_test_output/fm_c_boss.stl")
        print("[+] Model Exported.")
    else:
        print(f"[-] AUDIT FAILED: {end_res.get('error')}")

    print("=== SESSION ENDED ===")

if __name__ == "__main__":
    main()
