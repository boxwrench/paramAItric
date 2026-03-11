import json
from mcp_server.server import ParamAIToolServer

def main():
    server = ParamAIToolServer()
    print("=== STARTING OFFICIAL MACRO VALIDATION ===")

    # 1. Official Open Box (Recipe 1 equivalent)
    print("\n--- Running: open_box_body ---")
    res1 = server.create_open_box_body({
        "width_cm": 10.0, "depth_cm": 8.0, "height_cm": 6.0,
        "wall_thickness_cm": 0.3, "floor_thickness_cm": 0.4,
        "body_name": "Official Enclosure Box",
        "output_path": r"manual_test_output\official_recipe_1_box.stl"
    })
    print(f"Result: {res1.get('ok')}")

    # 2. Official Cable Gland Plate (The "Cable Box" fix)
    print("\n--- Running: cable_gland_plate ---")
    res2 = server.create_cable_gland_plate({
        "width_cm": 6.0, "height_cm": 4.0, "thickness_cm": 0.3,
        "center_hole_diameter_cm": 1.5, "mounting_hole_diameter_cm": 0.4,
        "edge_offset_x_cm": 0.5, "edge_offset_y_cm": 0.5,
        "body_name": "Official Gland Plate",
        "output_path": r"manual_test_output\official_cable_gland.stl"
    })
    print(f"Result: {res2.get('ok')}")

    # 3. Official Slotted Mounting Plate (Recipe 3 equivalent)
    print("\n--- Running: slotted_mounting_plate ---")
    res3 = server.create_slotted_mounting_plate({
        "width_cm": 15.0, "height_cm": 10.0, "thickness_cm": 0.4,
        "hole_diameter_cm": 0.5, "edge_offset_x_cm": 1.0, "edge_offset_y_cm": 1.0,
        "slot_length_cm": 8.0, "slot_width_cm": 0.2,
        "body_name": "Official Slotted Plate",
        "output_path": r"manual_test_output\official_slotted_plate.stl"
    })
    print(f"Result: {res3.get('ok')}")

    # 4. Official Strut Channel Bracket (The Final Boss)
    print("\n--- Running: strut_channel_bracket ---")
    res4 = server.create_strut_channel_bracket({
        "width_cm": 8.89, "height_cm": 10.478, "depth_cm": 4.128, "thickness_cm": 0.635,
        "hole_diameter_cm": 1.43, "hole_edge_offset_cm": 2.064, "hole_spacing_cm": 4.762,
        "taper_angle_deg": 12.8,
        "body_name": "Official Strut Bracket",
        "output_path": r"manual_test_output\official_mcmaster_strut.stl"
    })
    print(f"Result: {res4.get('ok')}")

    print("\n=== OFFICIAL VALIDATION COMPLETE ===")

if __name__ == "__main__":
    main()
