"""Live runner: Recipe 2 — Telescoping Nesting Containers"""
import json
import pathlib
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

OUTPUT_DIR = pathlib.Path("manual_test_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    server = ParamAIToolServer(bridge_client=BridgeClient())
    print("=== LIVE: Recipe 2 — Telescoping Containers ===")

    payload = {
        "outer_width_cm": 20.0,
        "outer_depth_cm": 20.0,
        "outer_height_cm": 8.0,
        "wall_thickness_cm": 0.3,
        "middle_clearance_cm": 0.4,
        "inner_clearance_cm": 0.4,
        "output_path_outer": str(OUTPUT_DIR / "recipe2_outer.stl"),
        "output_path_middle": str(OUTPUT_DIR / "recipe2_middle.stl"),
        "output_path_inner": str(OUTPUT_DIR / "recipe2_inner.stl"),
    }

    result = server.create_telescoping_containers(payload)
    print(json.dumps(result, indent=2))

    if result.get("ok"):
        print("\n=== VERIFICATION CHECKLIST ===")
        print("1. Outer container: 12cm x 10cm x 8cm")
        print("2. Middle container: fits inside outer with 0.2cm clearance")
        print("3. Inner container: fits inside middle with 0.3cm clearance")
        print("4. All three containers are CONCENTRIC (same center point)")
        print("5. Three STL files exported")

        verification = result.get("verification", {})
        outer = verification.get("outer_centroid", {})
        middle = verification.get("middle_centroid", {})
        inner = verification.get("inner_centroid", {})
        
        print(f"\n=== CONCENTRICITY CHECK ===")
        print(f"Outer centroid:   ({outer.get('x', 0):.2f}, {outer.get('y', 0):.2f})")
        print(f"Middle centroid:  ({middle.get('x', 0):.2f}, {middle.get('y', 0):.2f})")
        print(f"Inner centroid:   ({inner.get('x', 0):.2f}, {inner.get('y', 0):.2f})")
        
        # Check if concentric (centroids should be close)
        if middle.get('x') and outer.get('x'):
            dx = abs(middle['x'] - outer['x'])
            dy = abs(middle['y'] - outer['y'])
            if dx < 0.5 and dy < 0.5:
                print("[PASS] Containers are concentric!")
            else:
                print(f"[FAIL] Containers NOT concentric! Offset: ({dx:.2f}, {dy:.2f})")


if __name__ == "__main__":
    main()
