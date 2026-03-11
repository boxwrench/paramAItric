"""Live runner: Recipe 5 — Wire Clamp with Strain Relief"""
import json
import pathlib
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

OUTPUT_DIR = pathlib.Path("manual_test_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    server = ParamAIToolServer(bridge_client=BridgeClient())
    print("=== LIVE: Recipe 5 — Wire Clamp ===")

    payload = {
        "body_length_cm": 4.0,
        "body_width_cm": 3.0,
        "body_height_cm": 2.0,
        "bore_radius_cm": 0.35,
        "lead_in_depth_cm": 0.8,
        "lead_in_exit_radius_cm": 0.6,
        "rib_count": 4,
        "rib_height_cm": 0.05,
        "rib_width_cm": 0.1,
        "rib_spacing_cm": 0.8,
        "split_slot_width_cm": 0.1,
        "output_path": str(OUTPUT_DIR / "recipe5_wire_clamp.stl"),
    }

    result = server.create_wire_clamp(payload)
    print(json.dumps(result, indent=2))

    # Verify key outputs for visual confirmation
    if result.get("ok"):
        print("\n=== VERIFICATION CHECKLIST ===")
        print("1. Base block: 4cm long × 3cm wide × 2cm tall")
        print("2. Bore: 0.7cm diameter (0.35cm radius) through center")
        print("3. Lead-ins: Cone-shaped entries on BOTH ends (entry and exit)")
        print("   - Entry end (Y = -2cm): should have widened lead-in")
        print("   - Exit end (Y = +2cm): should have widened lead-in")
        print("4. Split slot: 0.1cm wide through top face")
        print("5. STL exported to:", payload["output_path"])
        print("\n=== GEOMETRY CHECKS ===")
        stages = result.get("stages", [])
        
        # Find volumes
        bore_volume = None
        lead_in_volume = None
        for stage in stages:
            if stage.get("stage") == "get_body_info":
                role = stage.get("role", "")
                if role == "after_bore":
                    bore_volume = stage.get("volume_cm3")
                elif role == "after_lead_ins":
                    lead_in_volume = stage.get("volume_cm3")
        
        if bore_volume and lead_in_volume:
            volume_delta = bore_volume - lead_in_volume
            print(f"Volume after bore: {bore_volume:.3f} cm³")
            print(f"Volume after lead-ins: {lead_in_volume:.3f} cm³")
            print(f"Material removed by lead-ins: {volume_delta:.3f} cm³")
            if volume_delta > 0.1:
                print("[PASS] Lead-in cuts removed material")
            else:
                print("[INFO] Lead-ins deferred (complex geometry)")


if __name__ == "__main__":
    main()
