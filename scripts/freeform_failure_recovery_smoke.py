"""Run a failure-path freeform smoke that validates rollback and recovery.

This script intentionally submits a bad hard-gate assertion for a known-good
extrusion result, confirms the commit is rejected with failed verification
signals, then inspects the body, submits the corrected assertion, and closes
the session cleanly.
"""

from __future__ import annotations

import argparse
import json
import sys

from mcp_server.bridge_client import BridgeClient
from mcp_server.server import ParamAIToolServer


def _print_signals(label: str, result: dict) -> None:
    print(f"[ok] {label}")
    print(json.dumps(result["verification_signals"], indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run freeform failure recovery smoke workflow.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8123", help="Fusion bridge base URL.")
    args = parser.parse_args()

    server = ParamAIToolServer(bridge_client=BridgeClient(args.base_url))

    try:
        server.start_freeform_session({
            "design_name": "Failure Recovery Smoke",
            "target_features": ["Base plate", "Recovery after bad assertion"],
        })

        sketch = server.create_sketch(plane="xy", name="Recovery Plate")
        sketch_token = sketch["result"]["sketch"]["token"]
        sketch_commit = server.commit_verification({
            "notes": "Recovery plate sketch created.",
            "expected_body_count": 0,
        })
        _print_signals("plate sketch verification", sketch_commit)

        server.draw_rectangle(width_cm=5.0, height_cm=5.0, sketch_token=sketch_token)
        profile_commit = server.commit_verification({
            "notes": "Recovery plate profile drawn.",
            "expected_body_count": 0,
            "expected_body_count_delta": 0,
            "expected_volume_delta_sign": "unchanged",
        })
        _print_signals("plate profile verification", profile_commit)

        profile_token = server.list_profiles(sketch_token=sketch_token)["result"]["profiles"][0]["token"]
        plate = server.extrude_profile(profile_token=profile_token, distance_cm=0.5, body_name="Recovery Plate")
        plate_token = plate["result"]["body"]["token"]
        failed_commit = server.commit_verification({
            "notes": "Intentional bad assertion after plate extrusion.",
            "expected_body_count": 99,
            "expected_body_count_delta": 1,
            "expected_volume_delta_sign": "increase",
        })
        if failed_commit.get("ok") is not False:
            raise RuntimeError("Bad assertion unexpectedly passed.")
        _print_signals("intentional failure captured", failed_commit)
        failed = [
            signal
            for signal in failed_commit["verification_signals"]
            if signal["signal"] == "expected_body_count" and signal["status"] == "fail"
        ]
        if not failed:
            raise RuntimeError("Failure payload did not include failed expected_body_count signal.")

        body_info = server.get_body_info({"body_token": plate_token})
        info = body_info["result"]["body_info"]
        if info["body_token"] != plate_token:
            raise RuntimeError("Inspection returned an unexpected body token after failure.")
        print("[ok] inspection after failure")
        print(json.dumps(info, indent=2))

        recovered_commit = server.commit_verification({
            "notes": "Corrected assertion after plate extrusion.",
            "expected_body_count": 1,
            "expected_body_count_delta": 1,
            "expected_volume_delta_sign": "increase",
            "resolved_features": ["Base plate", "Recovery after bad assertion"],
        })
        _print_signals("recovery verification", recovered_commit)

        end_res = server.end_freeform_session({})
        if not end_res.get("ok"):
            raise RuntimeError(f"Compliance audit failed: {end_res}")

        print("[ok] Freeform failure recovery smoke passed.")
        return 0
    except Exception as exc:  # pragma: no cover - smoke script path
        print(f"[error] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
