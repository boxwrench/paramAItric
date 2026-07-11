"""Live Fusion validation for the valve_handle workflow chain.

Run after reloading the add-in (Stop -> Run) so the new draw_polygon op is loaded.

Three stages, each independently meaningful:
  1. Bare draw_polygon probe: hex prism on XY, volume-checked against the
     analytic value V = (3*sqrt(3)/2) * R^2 * h.
  2. valve_handle hex socket build (test dimensions from the pytest suite).
  3. valve_handle square socket build with set-screw hole.

Real Chemtrol/MA611AF dimensions stay out of this script on purpose: both spec
YAMLs still read `stem_across_flats_cm: 0.0  # MEASURE THIS` and the MA611AF
file documents why guessed dimensions produce fictional geometry. Swap in
measured values via --stem-width-cm/--stem-depth-cm once calipers happen.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from urllib import request, error

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mcp_server.bridge_client import BridgeClient  # noqa: E402
from mcp_server.server import ParamAIToolServer  # noqa: E402

BASE_URL = "http://127.0.0.1:8123"
OUTPUT_DIR = REPO_ROOT / "manual_test_output"


def _send(command: str, arguments: dict) -> dict:
    payload = json.dumps({"command": command, "arguments": arguments}).encode()
    req = request.Request(
        f"{BASE_URL}/command",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except error.HTTPError as exc:
        body = exc.read().decode()
        try:
            detail = json.loads(body).get("error", body)
        except Exception:
            detail = body
        raise RuntimeError(f"{command} failed [{exc.code}]: {detail}") from None


def step(label: str, result: dict) -> dict:
    if not result.get("ok"):
        print(f"  [fail] {label}: {result.get('error')}")
        raise SystemExit(1)
    print(f"  [ok] {label}")
    return result.get("result", result)


def probe_draw_polygon() -> None:
    """Hex prism: R=1.0 circumradius, h=0.5. Analytic volume 1.2990 cm^3."""
    print("\n=== Stage 1: bare draw_polygon probe (hex prism) ===")
    radius_cm = 1.0
    height_cm = 0.5
    step("new_design", _send("new_design", {"name": "Polygon Probe"}))
    sk = step("create_sketch (xy)", _send("create_sketch", {"plane": "xy", "name": "Hex"}))
    sk_token = sk["sketch"]["token"]
    step("draw_polygon hex R=1.0", _send("draw_polygon", {
        "sketch_token": sk_token,
        "center_x_cm": 0.0,
        "center_y_cm": 0.0,
        "radius_cm": radius_cm,
        "num_sides": 6,
    }))
    profiles = step("list_profiles", _send("list_profiles", {"sketch_token": sk_token}))
    profile_token = profiles["profiles"][0]["token"]
    ext = step("extrude 0.5", _send("extrude_profile", {
        "profile_token": profile_token,
        "distance_cm": height_cm,
        "body_name": "HexPrism",
        "operation": "new_body",
    }))
    info = step("get_body_info", _send("get_body_info", {"body_token": ext["body"]["token"]}))
    volume = info["body_info"]["volume_cm3"]
    expected = (3.0 * math.sqrt(3.0) / 2.0) * radius_cm**2 * height_cm
    delta = abs(volume - expected)
    print(f"  volume: {volume:.4f} cm^3 (analytic {expected:.4f}, delta {delta:.4f})")
    if delta > 0.01:
        print("  [fail] hex prism volume does not match analytic value")
        raise SystemExit(1)
    print("  [pass] draw_polygon produces a true regular hexagon")


def build_valve_handle(server: ParamAIToolServer, label: str, payload: dict) -> None:
    print(f"\n=== {label} ===")
    result = server.create_valve_handle(payload)
    if not result.get("ok"):
        print(f"  [fail] workflow: {json.dumps(result, indent=2)}")
        raise SystemExit(1)
    stages = [s["stage"] for s in result["stages"]]
    print(f"  stages: {', '.join(stages)}")
    export_path = Path(result["export"]["file_path"])
    if not export_path.exists():
        print(f"  [fail] STL missing: {export_path}")
        raise SystemExit(1)
    print(f"  [pass] STL exported: {export_path} ({export_path.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stem-width-cm", type=float, default=None,
                        help="Measured across-flats; overrides test dimensions")
    parser.add_argument("--stem-depth-cm", type=float, default=None)
    parser.add_argument("--socket-type", choices=["hex", "square", "round_flat"], default=None)
    args = parser.parse_args()

    health = json.loads(request.urlopen(f"{BASE_URL}/health", timeout=10).read())
    print(f"bridge: {health['status']} mode={health['mode']}")

    probe_draw_polygon()

    server = ParamAIToolServer(BridgeClient(BASE_URL))

    if args.stem_width_cm:
        # Measured-dimensions path: single build with real values.
        build_valve_handle(server, "Measured valve handle", {
            "stem_width_cm": args.stem_width_cm,
            "stem_depth_cm": args.stem_depth_cm or 2.0,
            "socket_type": args.socket_type or "square",
            "lever_length_cm": 8.0,
            "lever_thickness_cm": 1.0,
            "lever_width_cm": 2.0,
            "fillet_radius_cm": 0.3,
            "output_path": str(OUTPUT_DIR / "measured_valve_handle.stl"),
        })
        return

    build_valve_handle(server, "Stage 2: hex-socket valve handle (test dims)", {
        "stem_width_cm": 1.0,
        "stem_depth_cm": 2.0,
        "socket_type": "hex",
        "lever_length_cm": 8.0,
        "lever_thickness_cm": 1.0,
        "lever_width_cm": 2.0,
        "fillet_radius_cm": 0.3,
        "output_path": str(OUTPUT_DIR / "live_valve_handle_hex.stl"),
    })
    build_valve_handle(server, "Stage 3: square-socket valve handle + set screw", {
        "stem_width_cm": 0.8,
        "stem_depth_cm": 1.5,
        "socket_type": "square",
        "lever_length_cm": 6.0,
        "lever_thickness_cm": 0.8,
        "lever_width_cm": 1.5,
        "fillet_radius_cm": 0.2,
        "set_screw_diameter_cm": 0.4,
        "output_path": str(OUTPUT_DIR / "live_valve_handle_square.stl"),
    })
    print("\n[pass] valve_handle live validation complete")


if __name__ == "__main__":
    main()
