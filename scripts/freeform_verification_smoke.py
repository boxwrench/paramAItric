"""Run a narrow freeform verification smoke path.

This script is intentionally small:

1. start a freeform session
2. create and verify a sketch
3. draw and verify a rectangle
4. print the returned verification signal tiers

It is useful for checking the verification trust surface against a running
bridge without relying on the larger smoke runner.
"""

from __future__ import annotations

import argparse
import json
import sys

from mcp_server.bridge_client import BridgeClient
from mcp_server.server import ParamAIToolServer


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a narrow freeform verification smoke workflow.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8123", help="Fusion bridge base URL.")
    args = parser.parse_args()

    server = ParamAIToolServer(bridge_client=BridgeClient(args.base_url))

    try:
        server.start_freeform_session({
            "design_name": "Freeform Verification Smoke",
            "target_features": ["base sketch", "base profile"],
        })

        sketch = server.create_sketch(plane="xy", name="Smoke Sketch")
        sketch_token = sketch["result"]["sketch"]["token"]
        first_commit = server.commit_verification({
            "notes": "Sketch created.",
            "expected_body_count": 0,
            "resolved_features": ["base sketch"],
        })

        server.draw_rectangle(width_cm=5.0, height_cm=3.0, sketch_token=sketch_token)
        second_commit = server.commit_verification({
            "notes": "Rectangle drawn.",
            "expected_body_count": 0,
            "expected_body_count_delta": 0,
            "expected_volume_delta_sign": "unchanged",
            "resolved_features": ["base profile"],
        })

        print("[ok] Freeform verification smoke passed.")
        print(json.dumps({
            "first_commit_signals": first_commit["verification_signals"],
            "second_commit_signals": second_commit["verification_signals"],
        }, indent=2))
        server.end_freeform_session({})
        return 0
    except Exception as exc:  # pragma: no cover - smoke script path
        print(f"[error] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
