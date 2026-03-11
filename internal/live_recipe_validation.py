import json
import math
from mcp_server.server import ParamAIToolServer

def main():
    server = ParamAIToolServer()
    print("=== STARTING MASTER LIVE RECIPE VALIDATION ===")

    # -------------------------------------------------------------------------
    # Recipe 1: Snap-Fit Enclosure (Box Part)
    # -------------------------------------------------------------------------
    print("\n--- Recipe 1: Snap-Fit Enclosure ---")
    server.start_freeform_session({"design_name": "Recipe 1 - Enclosure", "target_features": ["Box Solid", "Open-Top Shell", "Front Hole", "Side Hole"]})
    
    sk_base = server.create_sketch(plane="xy", name="Base")["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Sketch created.", "expected_body_count": 0})
    server.draw_rectangle(width_cm=10.0, height_cm=8.0, sketch_token=sk_base)
    server.commit_verification({"notes": "Rect drawn.", "expected_body_count": 0})
    prof_token = server.list_profiles(sketch_token=sk_base)["result"]["profiles"][0]["token"]
    res_ext = server.extrude_profile(profile_token=prof_token, distance_cm=6.0, body_name="Project Box")
    box_token = res_ext["result"]["body"]["token"]
    server.commit_verification({"notes": "Box solid.", "expected_body_count": 1, "resolved_features": ["Box Solid"]})
    
    server.apply_shell(body_token=box_token, wall_thickness_cm=0.3)
    server.commit_verification({"notes": "Shelled.", "expected_body_count": 1, "resolved_features": ["Open-Top Shell"]})
    
    sk_front = server.create_sketch(plane="xz", name="Front Hole", offset_cm=0.0)["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Front sketch.", "expected_body_count": 1})
    server.draw_circle(center_x_cm=5.0, center_y_cm=-1.5, radius_cm=1.0, sketch_token=sk_front)
    server.commit_verification({"notes": "Circle drawn.", "expected_body_count": 1})
    prof_f = server.list_profiles(sketch_token=sk_front)["result"]["profiles"][0]["token"]
    server.extrude_profile(profile_token=prof_f, distance_cm=1.0, operation="cut", target_body_token=box_token, body_name="Project Box")
    server.commit_verification({"notes": "Front hole cut.", "expected_body_count": 1, "resolved_features": ["Front Hole"]})
    
    sk_side = server.create_sketch(plane="yz", name="Side Hole", offset_cm=10.0)["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Side sketch.", "expected_body_count": 1})
    server.draw_circle(center_x_cm=-1.5, center_y_cm=4.0, radius_cm=0.75, sketch_token=sk_side)
    server.commit_verification({"notes": "Circle drawn.", "expected_body_count": 1})
    prof_s = server.list_profiles(sketch_token=sk_side)["result"]["profiles"][0]["token"]
    server.extrude_profile(profile_token=prof_s, distance_cm=1.0, operation="cut", target_body_token=box_token, body_name="Project Box")
    server.commit_verification({"notes": "Side hole cut.", "expected_body_count": 1, "resolved_features": ["Side Hole"]})
    
    server.export_stl(body_token=box_token, output_path=r"manual_test_output\recipe_1_enclosure.stl")
    server.end_freeform_session({})
    print("[ok] Recipe 1 Complete.")

    # -------------------------------------------------------------------------
    # Recipe 2: Telescoping Containers
    # -------------------------------------------------------------------------
    print("\n--- Recipe 2: Telescoping Containers ---")
    res2 = server.create_telescoping_containers({
        "outer_width_cm": 12.0, "outer_depth_cm": 10.0, "outer_height_cm": 8.0,
        "wall_thickness_cm": 0.3, "middle_clearance_cm": 0.8, "inner_clearance_cm": 0.8,
        "output_path_outer": r"manual_test_output\recipe_2_outer.stl",
        "output_path_middle": r"manual_test_output\recipe_2_middle.stl",
        "output_path_inner": r"manual_test_output\recipe_2_inner.stl"
    })
    if res2["ok"]:
        print("[ok] Recipe 2 Complete (3 Bodies).")

    # -------------------------------------------------------------------------
    # Recipe 3: Slotted Flex Panel
    # -------------------------------------------------------------------------
    print("\n--- Recipe 3: Slotted Flex Panel ---")
    server.start_freeform_session({"design_name": "Recipe 3 - Flex Panel", "target_features": ["Solid Panel", "5 Slots Cut"]})
    
    sk_base = server.create_sketch(plane="xy", name="Base")["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Base sketch.", "expected_body_count": 0})
    server.draw_rectangle(width_cm=15.0, height_cm=10.0, sketch_token=sk_base)
    server.commit_verification({"notes": "Rect drawn.", "expected_body_count": 0})
    prof_base = server.list_profiles(sketch_token=sk_base)["result"]["profiles"][0]["token"]
    res_ext = server.extrude_profile(profile_token=prof_base, distance_cm=0.4, body_name="Flex Panel")
    panel_token = res_ext["result"]["body"]["token"]
    server.commit_verification({"notes": "Panel solid.", "expected_body_count": 1, "resolved_features": ["Solid Panel"]})
    
    sk_slots = server.create_sketch(plane="xy", name="Slots", offset_cm=0.4)["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Slots sketch.", "expected_body_count": 1})
    for i in range(5):
        server.draw_rectangle_at(origin_x_cm=1.0 + (i * 2.5), origin_y_cm=1.0, width_cm=0.2, height_cm=8.0, sketch_token=sk_slots)
        # Note: No commit needed for draw_rectangle_at (it is a sketch tool)
        
    s_profs = server.list_profiles(sketch_token=sk_slots)["result"]["profiles"]
    for i, p in enumerate(s_profs):
        server.extrude_profile(profile_token=p["token"], distance_cm=1.0, operation="cut", target_body_token=panel_token, body_name="Flex Panel")
        server.commit_verification({
            "notes": f"Slot {i+1} cut.", 
            "expected_body_count": 1,
            "resolved_features": ["5 Slots Cut"] if i == len(s_profs)-1 else None
        })
        
    server.export_stl(body_token=panel_token, output_path=r"manual_test_output\recipe_3_flex_panel.stl")
    server.end_freeform_session({})
    print("[ok] Recipe 3 Complete.")

    # -------------------------------------------------------------------------
    # Recipe 4: Ratchet Wheel
    # -------------------------------------------------------------------------
    print("\n--- Recipe 4: Ratchet Wheel ---")
    server.start_freeform_session({"design_name": "Recipe 4 - Ratchet", "target_features": ["Wheel Solid", "Center Bore"]})
    
    sk_wheel = server.create_sketch(plane="xy", name="Wheel")["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Sketch created.", "expected_body_count": 0})
    server.draw_circle(center_x_cm=0, center_y_cm=0, radius_cm=3.0, sketch_token=sk_wheel)
    server.commit_verification({"notes": "Wheel circle drawn.", "expected_body_count": 0})
    
    prof_wheel = server.list_profiles(sketch_token=sk_wheel)["result"]["profiles"][0]["token"]
    res_ext = server.extrude_profile(profile_token=prof_wheel, distance_cm=0.8, body_name="Ratchet Wheel")
    wheel_token = res_ext["result"]["body"]["token"]
    server.commit_verification({"notes": "Wheel solid.", "expected_body_count": 1, "resolved_features": ["Wheel Solid"]})
    
    sk_bore = server.create_sketch(plane="xy", name="Bore", offset_cm=0.8)["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Bore sketch.", "expected_body_count": 1})
    server.draw_circle(center_x_cm=0, center_y_cm=0, radius_cm=0.5, sketch_token=sk_bore)
    server.commit_verification({"notes": "Bore drawn.", "expected_body_count": 1})
    
    prof_bore = server.list_profiles(sketch_token=sk_bore)["result"]["profiles"][0]["token"]
    server.extrude_profile(profile_token=prof_bore, distance_cm=1.0, operation="cut", target_body_token=wheel_token, body_name="Ratchet Wheel")
    server.commit_verification({"notes": "Bore cut.", "expected_body_count": 1, "resolved_features": ["Center Bore"]})
    
    server.export_stl(body_token=wheel_token, output_path=r"manual_test_output\recipe_4_ratchet.stl")
    server.end_freeform_session({})
    print("[ok] Recipe 4 Complete.")

    print("\n=== MASTER LIVE VALIDATION COMPLETE ===")

if __name__ == "__main__":
    main()
