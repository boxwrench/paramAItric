from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib import error, request


def _send(base_url: str, command: str, arguments: dict) -> dict:
    payload = json.dumps({"command": command, "arguments": arguments}).encode("utf-8")
    req = request.Request(
        f"{base_url}/command",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _health(base_url: str) -> dict:
    with request.urlopen(f"{base_url}/health", timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _print_step(name: str, payload: dict) -> None:
    print(f"[ok] {name}")
    print(json.dumps(payload, indent=2, sort_keys=True))


def _require_result_item(response: dict, key: str) -> dict:
    result = response.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Bridge response did not include a result object.")
    item = result.get(key)
    if not isinstance(item, dict):
        raise RuntimeError(f"Bridge response did not include result.{key}.")
    return item


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the narrow ParamAItric Fusion bridge smoke test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8123", help="Fusion bridge base URL.")
    parser.add_argument(
        "--output-path",
        default="manual_test_output/live_smoke_spacer.stl",
        help="Where the exported STL should be written.",
    )
    parser.add_argument("--plane", default="xy", choices=("xy", "xz", "yz"), help="Sketch plane for the smoke test.")
    parser.add_argument("--width-cm", type=float, default=2.0, help="Rectangle width in cm.")
    parser.add_argument("--height-cm", type=float, default=1.0, help="Rectangle height in cm.")
    parser.add_argument("--thickness-cm", type=float, default=0.5, help="Extrusion thickness in cm.")
    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    output_path = Path(args.output_path).resolve(strict=False)

    try:
        health = _health(base_url)
        _print_step("health", health)
        if health.get("mode") != "live":
            raise RuntimeError(f"Expected live mode, got {health.get('mode')!r}.")

        new_design = _send(base_url, "new_design", {"name": "Fusion Live Smoke Test", "workflow_name": "spacer"})
        _print_step("new_design", new_design)

        clean_scene = _send(
            base_url,
            "get_scene_info",
            {"workflow_name": "spacer", "workflow_stage": "verify_clean_state"},
        )
        _print_step("get_scene_info.verify_clean_state", clean_scene)

        sketch = _send(
            base_url,
            "create_sketch",
            {"plane": args.plane, "name": "Smoke Sketch", "workflow_name": "spacer"},
        )
        _print_step("create_sketch", sketch)
        sketch_token = _require_result_item(sketch, "sketch")["token"]

        rectangle = _send(
            base_url,
            "draw_rectangle",
            {
                "sketch_token": sketch_token,
                "width_cm": args.width_cm,
                "height_cm": args.height_cm,
                "workflow_name": "spacer",
            },
        )
        _print_step("draw_rectangle", rectangle)

        profiles = _send(
            base_url,
            "list_profiles",
            {"sketch_token": sketch_token, "workflow_name": "spacer"},
        )
        _print_step("list_profiles", profiles)
        found_profiles = profiles["result"]["profiles"]
        if len(found_profiles) != 1:
            raise RuntimeError(f"Expected exactly one profile, found {len(found_profiles)}.")
        profile_token = found_profiles[0]["token"]

        body = _send(
            base_url,
            "extrude_profile",
            {
                "profile_token": profile_token,
                "distance_cm": args.thickness_cm,
                "body_name": "Smoke Spacer",
                "workflow_name": "spacer",
            },
        )
        _print_step("extrude_profile", body)
        body_token = _require_result_item(body, "body")["token"]

        scene = _send(
            base_url,
            "get_scene_info",
            {"workflow_name": "spacer", "workflow_stage": "verify_geometry"},
        )
        _print_step("get_scene_info.verify_geometry", scene)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        exported = _send(
            base_url,
            "export_stl",
            {
                "body_token": body_token,
                "output_path": str(output_path),
                "workflow_name": "spacer",
            },
        )
        _print_step("export_stl", exported)
        return 0
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        print(f"[error] HTTP {exc.code}: {detail}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
