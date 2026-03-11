"""Live runner: Recipe 1 — Snap-Fit Enclosure with View Holes"""
import json
import pathlib
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

OUTPUT_DIR = pathlib.Path("manual_test_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    server = ParamAIToolServer(bridge_client=BridgeClient())
    print("=== LIVE: Recipe 1 — Snap-Fit Enclosure ===")

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
        "output_path_box": str(OUTPUT_DIR / "recipe1_box.stl"),
        "output_path_lid": str(OUTPUT_DIR / "recipe1_lid.stl"),
    }

    result = server.create_snap_fit_enclosure(payload)
    print(json.dumps(result, indent=2))

    if result.get("ok"):
        print("\n=== VERIFICATION CHECKLIST ===")
        print("1. Box: 10cm x 8cm x 5.5cm tall (6cm - 0.5cm lid)")
        print("2. Lid: WRAPS OVER box like a cap (larger than box)")
        print("3. Snap bead: On lid UNDERSIDE (catches box inner rim)")
        print("4. Front view hole: 2cm diameter at 2.5cm from bottom")
        print("5. Side view hole: 1.5cm diameter at 2.0cm from bottom")
        print("6. Two STL files exported")

        verification = result.get("verification", {})
        box_width = verification.get("box_width_cm", 0)
        box_depth = verification.get("box_depth_cm", 0)
        lid_width = verification.get("lid_outer_width_cm", 0)
        lid_depth = verification.get("lid_outer_depth_cm", 0)
        
        print(f"\n=== LID FITMENT CHECK ===")
        print(f"Box dimensions: {box_width}cm x {box_depth}cm")
        print(f"Lid dimensions: {lid_width}cm x {lid_depth}cm")
        
        if lid_width > box_width and lid_depth > box_depth:
            print("[PASS] Lid is larger than box - wrap-over cap design!")
        else:
            print("[FAIL] Lid should be larger than box!")
        
        expected_lid_width = box_width + (0.3 * 2) + 0.02  # box + 2*wall + clearance
        print(f"\nExpected lid width: ~{expected_lid_width:.2f}cm")
        print(f"Actual lid width: {lid_width:.2f}cm")


if __name__ == "__main__":
    main()
