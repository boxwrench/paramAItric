"""Run Freeform C as a live verification-trust smoke path.

This is a real benchmark-style recipe, not a minimal synthetic smoke.
It exercises:

- hard-gate body-count assertions
- hard-gate body-count delta assertions
- hard-gate volume-delta-sign assertions
- audit-style volume observations

The recipe stops before the deferred top chamfer and ends the session with an
explicit deferral, matching the current validated scope.
"""

from __future__ import annotations

import argparse
import json
import sys

from mcp_server.bridge_client import BridgeClient
from mcp_server.server import ParamAIToolServer


def _print_commit(label: str, commit_res: dict) -> None:
    print(f"[ok] {label}")
    print(json.dumps(commit_res["verification_signals"], indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Freeform C verification-trust smoke workflow.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8123", help="Fusion bridge base URL.")
    args = parser.parse_args()

    server = ParamAIToolServer(bridge_client=BridgeClient(args.base_url))

    try:
        manifest = [
            "Base plate",
            "4 corner holes",
            "Central boss cylinder",
            "Boss bore",
            "Top chamfer",
        ]
        server.start_freeform_session({
            "design_name": "FM-C Verification Smoke",
            "target_features": manifest,
        })

        base_sketch = server.create_sketch(plane="xy", name="Base Plate")
        base_sketch_token = base_sketch["result"]["sketch"]["token"]
        commit = server.commit_verification({
            "notes": "Base sketch created.",
            "expected_body_count": 0,
        })
        _print_commit("base sketch verification", commit)

        server.draw_rectangle(width_cm=10.0, height_cm=8.0, sketch_token=base_sketch_token)
        base_profile = server.list_profiles(sketch_token=base_sketch_token)["result"]["profiles"][0]["token"]
        commit = server.commit_verification({
            "notes": "Base profile drawn.",
            "expected_body_count": 0,
            "expected_body_count_delta": 0,
            "expected_volume_delta_sign": "unchanged",
        })
        _print_commit("base profile verification", commit)

        plate = server.extrude_profile(profile_token=base_profile, distance_cm=0.4, body_name="Boss Plate")
        plate_token = plate["result"]["body"]["token"]
        commit = server.commit_verification({
            "notes": "Base plate extruded.",
            "expected_body_count": 1,
            "expected_body_count_delta": 1,
            "expected_volume_delta_sign": "increase",
            "resolved_features": ["Base plate"],
        })
        _print_commit("base plate verification", commit)

        hole_sketch = server.create_sketch(plane="xy", name="Corner Holes", offset_cm=0.4)
        hole_sketch_token = hole_sketch["result"]["sketch"]["token"]
        commit = server.commit_verification({
            "notes": "Hole sketch created.",
            "expected_body_count": 1,
            "expected_body_count_delta": 0,
        })
        _print_commit("hole sketch verification", commit)

        for idx, (hx, hy) in enumerate([(1.0, 1.0), (9.0, 1.0), (1.0, 7.0), (9.0, 7.0)], start=1):
            server.draw_circle(center_x_cm=hx, center_y_cm=hy, radius_cm=0.3, sketch_token=hole_sketch_token)
            commit = server.commit_verification({
                "notes": f"Hole circle {idx} drawn.",
                "expected_body_count": 1,
                "expected_body_count_delta": 0,
                "expected_volume_delta_sign": "unchanged",
            })
            _print_commit(f"hole circle {idx} verification", commit)

        hole_profiles = server.list_profiles(sketch_token=hole_sketch_token)["result"]["profiles"]
        for idx, profile in enumerate(hole_profiles, start=1):
            server.extrude_profile(
                profile_token=profile["token"],
                distance_cm=1.0,
                operation="cut",
                target_body_token=plate_token,
                body_name="Boss Plate",
            )
            commit = server.commit_verification({
                "notes": f"Hole {idx} cut.",
                "expected_body_count": 1,
                "expected_body_count_delta": 0,
                "expected_volume_delta_sign": "decrease",
                "resolved_features": ["4 corner holes"] if idx == len(hole_profiles) else None,
            })
            _print_commit(f"hole {idx} cut verification", commit)

        boss_sketch = server.create_sketch(plane="xy", name="Boss", offset_cm=0.4)
        boss_sketch_token = boss_sketch["result"]["sketch"]["token"]
        commit = server.commit_verification({
            "notes": "Boss sketch created.",
            "expected_body_count": 1,
            "expected_body_count_delta": 0,
        })
        _print_commit("boss sketch verification", commit)

        server.draw_circle(center_x_cm=5.0, center_y_cm=4.0, radius_cm=1.5, sketch_token=boss_sketch_token)
        boss_profile = server.list_profiles(sketch_token=boss_sketch_token)["result"]["profiles"][0]["token"]
        commit = server.commit_verification({
            "notes": "Boss circle drawn.",
            "expected_body_count": 1,
            "expected_body_count_delta": 0,
            "expected_volume_delta_sign": "unchanged",
        })
        _print_commit("boss circle verification", commit)

        boss = server.extrude_profile(profile_token=boss_profile, distance_cm=1.0, body_name="Boss Protrusion")
        boss_token = boss["result"]["body"]["token"]
        commit = server.commit_verification({
            "notes": "Boss cylinder extruded.",
            "expected_body_count": 2,
            "expected_body_count_delta": 1,
            "expected_volume_delta_sign": "increase",
        })
        _print_commit("boss body verification", commit)

        server.combine_bodies(target_body_token=plate_token, tool_body_token=boss_token)
        commit = server.commit_verification({
            "notes": "Boss combined.",
            "expected_body_count": 1,
            "expected_body_count_delta": -1,
            "expected_volume_delta_sign": "unchanged",
            "resolved_features": ["Central boss cylinder"],
        })
        _print_commit("boss combine verification", commit)

        bore_sketch = server.create_sketch(plane="xy", name="Bore", offset_cm=1.4)
        bore_sketch_token = bore_sketch["result"]["sketch"]["token"]
        commit = server.commit_verification({
            "notes": "Bore sketch created.",
            "expected_body_count": 1,
            "expected_body_count_delta": 0,
        })
        _print_commit("bore sketch verification", commit)

        server.draw_circle(center_x_cm=5.0, center_y_cm=4.0, radius_cm=0.75, sketch_token=bore_sketch_token)
        bore_profile = server.list_profiles(sketch_token=bore_sketch_token)["result"]["profiles"][0]["token"]
        commit = server.commit_verification({
            "notes": "Bore circle drawn.",
            "expected_body_count": 1,
            "expected_body_count_delta": 0,
            "expected_volume_delta_sign": "unchanged",
        })
        _print_commit("bore circle verification", commit)

        server.extrude_profile(
            profile_token=bore_profile,
            distance_cm=2.0,
            operation="cut",
            target_body_token=plate_token,
            body_name="Boss Plate",
        )
        commit = server.commit_verification({
            "notes": "Boss bore cut.",
            "expected_body_count": 1,
            "expected_body_count_delta": 0,
            "expected_volume_delta_sign": "decrease",
            "resolved_features": ["Boss bore"],
        })
        _print_commit("boss bore verification", commit)

        end_res = server.end_freeform_session({
            "deferred_features": [
                {
                    "feature": "Top chamfer",
                    "reason": "apply_chamfer is not yet validated for this boss geometry path.",
                }
            ]
        })
        if not end_res.get("ok"):
            raise RuntimeError(f"Compliance audit failed: {end_res}")

        print("[ok] Freeform C verification smoke passed.")
        return 0
    except Exception as exc:  # pragma: no cover - smoke script path
        print(f"[error] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
