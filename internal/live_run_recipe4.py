"""Live runner: Recipe 4 — Ratchet Wheel"""
import json
import pathlib
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

OUTPUT_DIR = pathlib.Path("manual_test_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    server = ParamAIToolServer(bridge_client=BridgeClient())
    print("=== LIVE: Recipe 4 — Ratchet Wheel ===")

    payload = {
        "outer_diameter_cm": 6.0,
        "thickness_cm": 0.8,
        "bore_diameter_cm": 1.0,
        "tooth_count": 10,
        "tooth_height_cm": 0.4,
        "slope_width_cm": 0.5,
        "locking_width_cm": 0.1,
        "tip_fillet_cm": 0.05,
        "output_path": str(OUTPUT_DIR / "recipe4_ratchet_wheel.stl"),
    }

    result = server.create_ratchet_wheel(payload)
    print(json.dumps(result, indent=2))

    if result.get("ok"):
        print("\n=== VERIFICATION CHECKLIST ===")
        print("1. Base cylinder: 6cm diameter x 0.8cm thick")
        print("2. Center bore: 1cm diameter through full thickness")
        print("3. 10 asymmetric teeth around outer edge")
        print("4. Teeth create SAWTOOTH outer silhouette (not smooth circle with surface bumps)")
        print("5. 0.05cm fillets on tooth tips")
        print("6. STL exported to:", payload["output_path"])

        verification = result.get("verification", {})
        final_cylindrical = verification.get("final_cylindrical_face_count")
        
        print(f"\n=== TOOTH SILHOUETTE CHECK ===")
        if final_cylindrical is not None:
            print(f"Cylindrical face count: {final_cylindrical}")
            if final_cylindrical == 1:
                print("[PASS] Only bore is cylindrical - teeth cut outer silhouette correctly!")
            elif final_cylindrical == 2:
                print("[FAIL] Outer rim still cylindrical - teeth are surface fins, not silhouette cuts!")
            else:
                print(f"[INFO] Unexpected cylindrical count: {final_cylindrical}")
        
        initial_vol = verification.get("initial_volume_cm3")
        final_vol = verification.get("final_volume_cm3")
        if initial_vol and final_vol:
            delta = initial_vol - final_vol
            print(f"\nVolume: initial={initial_vol:.2f}, final={final_vol:.2f}, removed={delta:.2f} cm³")
            if delta > 0.5:
                print("[PASS] Material removed by teeth cuts")
            else:
                print("[WARN] Little/no material removed")


if __name__ == "__main__":
    main()
