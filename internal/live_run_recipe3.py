"""Live runner: Recipe 3 — Slotted Flex Panel (Living Hinge)"""
import json
import pathlib
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

OUTPUT_DIR = pathlib.Path("manual_test_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    server = ParamAIToolServer(bridge_client=BridgeClient())
    print("=== LIVE: Recipe 3 — Slotted Flex Panel ===")

    payload = {
        "panel_width_cm": 15.0,
        "panel_depth_cm": 10.0,
        "panel_thickness_cm": 0.4,
        "slot_length_cm": 8.0,
        "slot_width_cm": 0.2,
        "slot_spacing_cm": 1.0,
        "end_margin_cm": 1.0,
        "edge_fillet_radius_cm": 0.05,
        "output_path": str(OUTPUT_DIR / "recipe3_flex_panel.stl"),
    }

    result = server.create_slotted_flex_panel(payload)
    print(json.dumps(result, indent=2))

    # Verification checklist
    if result.get("ok"):
        print("\n=== VERIFICATION CHECKLIST ===")
        print("1. Panel: 15cm wide x 10cm deep x 0.4cm thick")
        print("2. 5 slots evenly spaced")
        print("3. Each slot: 8cm long x 0.2cm wide")
        print("4. Slots centered on X axis (not left-justified)")
        print("5. 0.05cm fillets on all slot edges")
        print("6. STL exported to:", payload["output_path"])

        # Calculate expected slot positions
        panel_width = 15.0
        slot_width = 0.2
        slot_spacing = 1.0
        slot_count = 5
        
        group_width = slot_count * slot_width + (slot_count - 1) * slot_spacing
        first_slot = (panel_width - group_width) / 2.0 + slot_width / 2.0
        last_slot = first_slot + (slot_count - 1) * (slot_width + slot_spacing)
        
        print(f"\n=== SLOT POSITION CHECK ===")
        print(f"Panel width: {panel_width} cm")
        print(f"Slot group width: {group_width} cm")
        print(f"Expected first slot center: {first_slot:.1f} cm")
        print(f"Expected last slot center: {last_slot:.1f} cm")
        print(f"Symmetry check: {first_slot:.1f} + {last_slot:.1f} = {first_slot + last_slot:.1f} (should be {panel_width})")
        
        verification = result.get("verification", {})
        actual_first = verification.get("first_slot_center_x_cm")
        actual_last = verification.get("last_slot_center_x_cm")
        if actual_first and actual_last:
            print(f"\nActual first slot: {actual_first:.1f} cm")
            print(f"Actual last slot: {actual_last:.1f} cm")
            if abs((actual_first + actual_last) - panel_width) < 0.1:
                print("[PASS] Slots are centered!")
            else:
                print("[FAIL] Slots are NOT centered!")


if __name__ == "__main__":
    main()
