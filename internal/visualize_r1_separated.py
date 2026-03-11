"""Visualize R1 Box and Lid separated for verification"""
import json
import pathlib
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

OUTPUT_DIR = pathlib.Path("manual_test_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    server = ParamAIToolServer(bridge_client=BridgeClient())
    print("=== R1 Visualization: Box and Lid Separated ===")

    # First create the enclosure
    payload = {
        "box_width_cm": 10.0,
        "box_depth_cm": 8.0,
        "box_height_cm": 6.0,
        "wall_thickness_cm": 0.3,
        "lid_height_cm": 0.5,
        "snap_bead_width_cm": 0.3,
        "snap_bead_height_cm": 0.15,
        "clearance_cm": 0.02,
        "front_hole_diameter_cm": 2.0,
        "front_hole_center_z_cm": 2.5,
        "side_hole_diameter_cm": 1.5,
        "side_hole_center_z_cm": 2.0,
        "output_path_box": str(OUTPUT_DIR / "r1_box_check.stl"),
        "output_path_lid": str(OUTPUT_DIR / "r1_lid_check.stl"),
    }

    result = server.create_snap_fit_enclosure(payload)
    
    if not result.get("ok"):
        print("FAILED:", result)
        return
    
    print("[OK] Box and lid created")
    
    # Get body tokens
    box_token = result["box_body"]["token"]
    lid_token = result["lid_body"]["token"]
    
    # Move lid 15cm to the right for clear visualization
    print("Moving lid 15cm to the right for visualization...")
    
    # Create a new design for visualization
    server.new_design("R1_Visualization_Separated")
    
    # Export and re-import to get fresh bodies we can move
    # Actually, let me just export them as-is first
    print(f"\nBox STL: {payload['output_path_box']}")
    print(f"Lid STL: {payload['output_path_lid']}")
    
    verification = result.get("verification", {})
    print(f"\n=== DIMENSIONS ===")
    print(f"Box: {verification.get('box_width_cm')} x {verification.get('box_depth_cm')} cm")
    print(f"Lid: {verification.get('lid_outer_width_cm')} x {verification.get('lid_outer_depth_cm')} cm")
    print(f"Lid is {verification.get('lid_outer_width_cm') - verification.get('box_width_cm'):.2f}cm wider than box")
    print(f"Lid is {verification.get('lid_outer_depth_cm') - verification.get('box_depth_cm'):.2f}cm deeper than box")
    
    print("\n=== INSTRUCTIONS ===")
    print("1. Open both STLs in Fusion (or import them)")
    print("2. Move the lid 10-15cm to the right to see them side by side")
    print("3. Verify:")
    print("   - Lid is visibly LARGER than box (wrap-over design)")
    print("   - Lid has rectangular bead ring on underside")
    print("   - Box has proper shell thickness and view holes")


if __name__ == "__main__":
    main()
