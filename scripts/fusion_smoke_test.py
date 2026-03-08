from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib import error, request


WORKFLOW_CONFIG = {
    "spacer": {
        "design_name": "Fusion Live Smoke Test",
        "sketch_name": "Smoke Sketch",
        "body_name": "Smoke Spacer",
        "output_path": "manual_test_output/live_smoke_spacer.stl",
        "draw_command": "draw_rectangle",
    },
    "bracket": {
        "design_name": "Fusion Live Bracket Smoke Test",
        "sketch_name": "Bracket Smoke Sketch",
        "body_name": "Smoke Bracket",
        "output_path": "manual_test_output/live_smoke_bracket.stl",
        "draw_command": "draw_l_bracket_profile",
    },
}


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


def _require_close(actual: object, expected: float, field_name: str, tolerance: float = 1e-9) -> None:
    try:
        number = float(actual)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{field_name} was not numeric: {actual!r}.") from exc
    if abs(number - expected) > tolerance:
        raise RuntimeError(f"{field_name} mismatch: expected {expected}, got {number}.")


def _require_scene_matches(scene: dict, plane: str, width_cm: float, height_cm: float, thickness_cm: float, body_name: str) -> None:
    result = scene.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Bridge response did not include a result object.")

    sketches = result.get("sketches")
    if not isinstance(sketches, list) or len(sketches) != 1:
        raise RuntimeError(f"Expected exactly one sketch in scene info, found {0 if not isinstance(sketches, list) else len(sketches)}.")
    sketch = sketches[0]
    if sketch.get("plane") != plane:
        raise RuntimeError(f"Sketch plane mismatch: expected {plane!r}, got {sketch.get('plane')!r}.")

    bodies = result.get("bodies")
    if not isinstance(bodies, list) or len(bodies) != 1:
        raise RuntimeError(f"Expected exactly one body in scene info, found {0 if not isinstance(bodies, list) else len(bodies)}.")
    body = bodies[0]
    if body.get("name") != body_name:
        raise RuntimeError(f"Body name mismatch: expected {body_name!r}, got {body.get('name')!r}.")
    _require_close(body.get("width_cm"), width_cm, "body.width_cm")
    _require_close(body.get("height_cm"), height_cm, "body.height_cm")
    _require_close(body.get("thickness_cm"), thickness_cm, "body.thickness_cm")


def _require_profile_matches(profile: dict, width_cm: float, height_cm: float) -> None:
    _require_close(profile.get("width_cm"), width_cm, "profile.width_cm")
    _require_close(profile.get("height_cm"), height_cm, "profile.height_cm")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the narrow ParamAItric Fusion bridge smoke test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8123", help="Fusion bridge base URL.")
    parser.add_argument(
        "--workflow",
        default="spacer",
        choices=tuple(WORKFLOW_CONFIG.keys()),
        help="Named workflow to validate.",
    )
    parser.add_argument(
        "--output-path",
        default=None,
        help="Where the exported STL should be written.",
    )
    parser.add_argument("--plane", default="xy", choices=("xy", "xz", "yz"), help="Sketch plane for the smoke test.")
    parser.add_argument("--width-cm", type=float, default=2.0, help="Rectangle width in cm.")
    parser.add_argument("--height-cm", type=float, default=1.0, help="Rectangle height in cm.")
    parser.add_argument("--thickness-cm", type=float, default=0.5, help="Extrusion thickness in cm.")
    parser.add_argument(
        "--leg-thickness-cm",
        type=float,
        default=None,
        help="L-bracket leg thickness in cm. Defaults to thickness-cm for the bracket workflow.",
    )
    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    workflow = args.workflow
    workflow_config = WORKFLOW_CONFIG[workflow]
    output_path_arg = args.output_path or workflow_config["output_path"]
    output_path = Path(output_path_arg).resolve(strict=False)
    leg_thickness_cm = args.leg_thickness_cm if args.leg_thickness_cm is not None else args.thickness_cm

    try:
        health = _health(base_url)
        _print_step("health", health)
        if health.get("mode") != "live":
            raise RuntimeError(f"Expected live mode, got {health.get('mode')!r}.")

        new_design = _send(
            base_url,
            "new_design",
            {"name": workflow_config["design_name"], "workflow_name": workflow},
        )
        _print_step("new_design", new_design)

        clean_scene = _send(
            base_url,
            "get_scene_info",
            {"workflow_name": workflow, "workflow_stage": "verify_clean_state"},
        )
        _print_step("get_scene_info.verify_clean_state", clean_scene)

        sketch = _send(
            base_url,
            "create_sketch",
            {"plane": args.plane, "name": workflow_config["sketch_name"], "workflow_name": workflow},
        )
        _print_step("create_sketch", sketch)
        sketch_token = _require_result_item(sketch, "sketch")["token"]

        draw_arguments = {
            "sketch_token": sketch_token,
            "width_cm": args.width_cm,
            "height_cm": args.height_cm,
            "workflow_name": workflow,
        }
        if workflow_config["draw_command"] == "draw_l_bracket_profile":
            draw_arguments["leg_thickness_cm"] = leg_thickness_cm
        profile = _send(
            base_url,
            workflow_config["draw_command"],
            draw_arguments,
        )
        _print_step(workflow_config["draw_command"], profile)

        profiles = _send(
            base_url,
            "list_profiles",
            {"sketch_token": sketch_token, "workflow_name": workflow},
        )
        _print_step("list_profiles", profiles)
        found_profiles = profiles["result"]["profiles"]
        if len(found_profiles) != 1:
            raise RuntimeError(f"Expected exactly one profile, found {len(found_profiles)}.")
        _require_profile_matches(found_profiles[0], args.width_cm, args.height_cm)
        profile_token = found_profiles[0]["token"]

        body = _send(
            base_url,
            "extrude_profile",
            {
                "profile_token": profile_token,
                "distance_cm": args.thickness_cm,
                "body_name": workflow_config["body_name"],
                "workflow_name": workflow,
            },
        )
        _print_step("extrude_profile", body)
        body_token = _require_result_item(body, "body")["token"]

        scene = _send(
            base_url,
            "get_scene_info",
            {"workflow_name": workflow, "workflow_stage": "verify_geometry"},
        )
        _print_step("get_scene_info.verify_geometry", scene)
        _require_scene_matches(
            scene,
            plane=args.plane,
            width_cm=args.width_cm,
            height_cm=args.height_cm,
            thickness_cm=args.thickness_cm,
            body_name=workflow_config["body_name"],
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        exported = _send(
            base_url,
            "export_stl",
            {
                "body_token": body_token,
                "output_path": str(output_path),
                "workflow_name": workflow,
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
