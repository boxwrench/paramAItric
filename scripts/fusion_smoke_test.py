from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib import error, request


WORKFLOW_CONFIG = {
    "counterbored_plate": {
        "design_name": "Fusion Live Counterbored Plate Smoke Test",
        "sketch_name": "Counterbored Plate Sketch",
        "body_name": "Smoke Counterbored Plate",
        "output_path": "manual_test_output/live_smoke_counterbored_plate.stl",
        "draw_command": "draw_rectangle",
    },
    "plate_with_hole": {
        "design_name": "Fusion Live Plate With Hole Smoke Test",
        "sketch_name": "Plate Sketch",
        "body_name": "Smoke Plate",
        "output_path": "manual_test_output/live_smoke_plate_with_hole.stl",
        "draw_command": "draw_rectangle",
    },
    "recessed_mount": {
        "design_name": "Fusion Live Recessed Mount Smoke Test",
        "sketch_name": "Recessed Mount Sketch",
        "body_name": "Smoke Recessed Mount",
        "output_path": "manual_test_output/live_smoke_recessed_mount.stl",
        "draw_command": "draw_rectangle",
    },
    "two_hole_plate": {
        "design_name": "Fusion Live Two-Hole Plate Smoke Test",
        "sketch_name": "Two-Hole Plate Smoke Sketch",
        "body_name": "Smoke Two-Hole Plate",
        "output_path": "manual_test_output/live_smoke_two_hole_plate.stl",
        "draw_command": "draw_rectangle",
    },
    "slotted_mount": {
        "design_name": "Fusion Live Slotted Mount Smoke Test",
        "sketch_name": "Slotted Mount Smoke Sketch",
        "body_name": "Smoke Slotted Mount",
        "output_path": "manual_test_output/live_smoke_slotted_mount.stl",
        "draw_command": "draw_rectangle",
    },
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
    "filleted_bracket": {
        "design_name": "Fusion Live Filleted Bracket Smoke Test",
        "sketch_name": "Filleted Bracket Smoke Sketch",
        "body_name": "Smoke Filleted Bracket",
        "output_path": "manual_test_output/live_smoke_filleted_bracket.stl",
        "draw_command": "draw_l_bracket_profile",
    },
    "mounting_bracket": {
        "design_name": "Fusion Live Mounting Bracket Smoke Test",
        "sketch_name": "Mounting Bracket Smoke Sketch",
        "body_name": "Smoke Mounting Bracket",
        "output_path": "manual_test_output/live_smoke_mounting_bracket.stl",
        "draw_command": "draw_l_bracket_profile",
    },
    "two_hole_mounting_bracket": {
        "design_name": "Fusion Live Two-Hole Mounting Bracket Smoke Test",
        "sketch_name": "Two-Hole Mounting Bracket Smoke Sketch",
        "body_name": "Smoke Two-Hole Mounting Bracket",
        "output_path": "manual_test_output/live_smoke_two_hole_mounting_bracket.stl",
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


def _require_fillet_matches(fillet: dict, *, radius_cm: float, expected_edge_count: int) -> None:
    _require_close(fillet.get("radius_cm"), radius_cm, "fillet.radius_cm")
    edge_count = fillet.get("edge_count")
    if edge_count != expected_edge_count:
        raise RuntimeError(f"fillet.edge_count mismatch: expected {expected_edge_count}, got {edge_count}.")


def _require_hole_profiles(profiles: list[dict], *, hole_diameter_cm: float, expected_hole_count: int) -> None:
    hole_matches = []
    for profile in profiles:
        try:
            _require_profile_matches(profile, hole_diameter_cm, hole_diameter_cm)
        except RuntimeError:
            continue
        hole_matches.append(profile)
    if len(hole_matches) != expected_hole_count:
        raise RuntimeError(
            f"Expected exactly {expected_hole_count} hole profile matches at diameter {hole_diameter_cm}, found {len(hole_matches)}."
        )


def _matching_profiles(profiles: list[dict], *, width_cm: float, height_cm: float) -> list[dict]:
    matches = []
    for profile in profiles:
        try:
            _require_profile_matches(profile, width_cm, height_cm)
        except RuntimeError:
            continue
        matches.append(profile)
    return matches


def _select_outer_profile(profiles: list[dict], width_cm: float, height_cm: float) -> dict:
    matches = []
    for profile in profiles:
        try:
            _require_profile_matches(profile, width_cm, height_cm)
        except RuntimeError:
            continue
        matches.append(profile)
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one outer profile match, found {len(matches)}.")
    return matches[0]


def _require_workflow_exposed(health: dict, workflow: str) -> None:
    catalog = health.get("workflow_catalog")
    if not isinstance(catalog, list) or not catalog:
        return
    exposed = {
        entry.get("name")
        for entry in catalog
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    if workflow not in exposed:
        available = ", ".join(sorted(exposed))
        raise RuntimeError(
            f"Workflow {workflow!r} is not exposed by the loaded live add-in. "
            f"Reload the Fusion add-in from the current repo state. Available workflows: {available}."
        )


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
    parser.add_argument("--hole-diameter-cm", type=float, default=None, help="Mounting hole diameter in cm (plate_with_hole default: 0.4).")
    parser.add_argument("--hole-center-x-cm", type=float, default=None, help="Mounting hole center X in cm (plate_with_hole default: 1.0).")
    parser.add_argument("--hole-center-y-cm", type=float, default=None, help="Mounting hole center Y in cm (plate_with_hole default: 0.5).")
    parser.add_argument("--second-hole-center-x-cm", type=float, default=None, help="Second mounting hole center X in cm.")
    parser.add_argument("--second-hole-center-y-cm", type=float, default=None, help="Second mounting hole center Y in cm.")
    parser.add_argument("--edge-offset-x-cm", type=float, default=None, help="Mirrored hole center offset from the left/right edges in cm for two_hole_plate.")
    parser.add_argument("--slot-length-cm", type=float, default=None, help="Slot overall length in cm for slotted_mount.")
    parser.add_argument("--slot-width-cm", type=float, default=None, help="Slot overall width in cm for slotted_mount.")
    parser.add_argument("--slot-center-x-cm", type=float, default=None, help="Slot center X in cm for slotted_mount.")
    parser.add_argument("--slot-center-y-cm", type=float, default=None, help="Slot center Y in cm for slotted_mount.")
    parser.add_argument("--counterbore-diameter-cm", type=float, default=None, help="Counterbore diameter in cm for counterbored_plate.")
    parser.add_argument("--counterbore-depth-cm", type=float, default=None, help="Counterbore depth in cm for counterbored_plate.")
    parser.add_argument("--recess-width-cm", type=float, default=None, help="Rectangular recess width in cm for recessed_mount.")
    parser.add_argument("--recess-height-cm", type=float, default=None, help="Rectangular recess height in cm for recessed_mount.")
    parser.add_argument("--recess-depth-cm", type=float, default=None, help="Rectangular recess depth in cm for recessed_mount.")
    parser.add_argument("--recess-origin-x-cm", type=float, default=None, help="Rectangular recess left-edge origin X in cm for recessed_mount.")
    parser.add_argument("--recess-origin-y-cm", type=float, default=None, help="Rectangular recess bottom-edge origin Y in cm for recessed_mount.")
    parser.add_argument("--fillet-radius-cm", type=float, default=0.2, help="Fillet radius in cm for filleted_bracket.")
    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    workflow = args.workflow
    workflow_config = WORKFLOW_CONFIG[workflow]
    output_path_arg = args.output_path or workflow_config["output_path"]
    output_path = Path(output_path_arg).resolve(strict=False)
    leg_thickness_cm = args.leg_thickness_cm if args.leg_thickness_cm is not None else args.thickness_cm
    hole_diameter_cm = args.hole_diameter_cm
    hole_center_x_cm = args.hole_center_x_cm
    hole_center_y_cm = args.hole_center_y_cm
    second_hole_center_x_cm = args.second_hole_center_x_cm
    second_hole_center_y_cm = args.second_hole_center_y_cm

    try:
        health = _health(base_url)
        _print_step("health", health)
        if health.get("mode") != "live":
            raise RuntimeError(f"Expected live mode, got {health.get('mode')!r}.")
        _require_workflow_exposed(health, workflow)

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

        if workflow in {"mounting_bracket", "two_hole_mounting_bracket", "two_hole_plate"}:
            if workflow == "mounting_bracket":
                if hole_diameter_cm is None or hole_center_x_cm is None or hole_center_y_cm is None:
                    raise RuntimeError(
                        "mounting_bracket smoke test requires --hole-diameter-cm, --hole-center-x-cm, and --hole-center-y-cm."
                    )
                hole_centers = ((hole_center_x_cm, hole_center_y_cm),)
            elif workflow == "two_hole_mounting_bracket":
                if (
                    hole_diameter_cm is None
                    or hole_center_x_cm is None
                    or hole_center_y_cm is None
                    or second_hole_center_x_cm is None
                    or second_hole_center_y_cm is None
                ):
                    raise RuntimeError(
                        "two_hole_mounting_bracket smoke test requires --hole-diameter-cm, --hole-center-x-cm, --hole-center-y-cm, --second-hole-center-x-cm, and --second-hole-center-y-cm."
                    )
                hole_centers = (
                    (hole_center_x_cm, hole_center_y_cm),
                    (second_hole_center_x_cm, second_hole_center_y_cm),
                )
            else:
                if hole_diameter_cm is None or hole_center_y_cm is None or args.edge_offset_x_cm is None:
                    raise RuntimeError(
                        "two_hole_plate smoke test requires --hole-diameter-cm, --hole-center-y-cm, and --edge-offset-x-cm."
                    )
                hole_centers = (
                    (args.edge_offset_x_cm, hole_center_y_cm),
                    (args.width_cm - args.edge_offset_x_cm, hole_center_y_cm),
                )
            for hole_index, (center_x_cm, center_y_cm) in enumerate(hole_centers, start=1):
                circle = _send(
                    base_url,
                    "draw_circle",
                    {
                        "sketch_token": sketch_token,
                        "center_x_cm": center_x_cm,
                        "center_y_cm": center_y_cm,
                        "radius_cm": hole_diameter_cm / 2.0,
                        "workflow_name": workflow,
                    },
                )
                step_name = "draw_circle" if hole_index == 1 else f"draw_circle.{hole_index}"
                _print_step(step_name, circle)
        elif workflow == "slotted_mount":
            if (
                args.slot_length_cm is None
                or args.slot_width_cm is None
                or args.slot_center_x_cm is None
                or args.slot_center_y_cm is None
            ):
                raise RuntimeError(
                    "slotted_mount smoke test requires --slot-length-cm, --slot-width-cm, --slot-center-x-cm, and --slot-center-y-cm."
                )
            slot = _send(
                base_url,
                "draw_slot",
                {
                    "sketch_token": sketch_token,
                    "center_x_cm": args.slot_center_x_cm,
                    "center_y_cm": args.slot_center_y_cm,
                    "length_cm": args.slot_length_cm,
                    "width_cm": args.slot_width_cm,
                    "workflow_name": workflow,
                },
            )
            _print_step("draw_slot", slot)

        profiles = _send(
            base_url,
            "list_profiles",
            {"sketch_token": sketch_token, "workflow_name": workflow},
        )
        _print_step("list_profiles", profiles)
        found_profiles = profiles["result"]["profiles"]
        if workflow in {"mounting_bracket", "two_hole_mounting_bracket", "two_hole_plate"}:
            expected_hole_count = 1 if workflow == "mounting_bracket" else 2
            _require_hole_profiles(
                found_profiles,
                hole_diameter_cm=hole_diameter_cm,
                expected_hole_count=expected_hole_count,
            )
            profile_token = _select_outer_profile(found_profiles, args.width_cm, args.height_cm)["token"]
        elif workflow == "slotted_mount":
            slot_matches = _matching_profiles(
                found_profiles,
                width_cm=args.slot_length_cm,
                height_cm=args.slot_width_cm,
            )
            if len(slot_matches) != 1:
                raise RuntimeError(
                    f"Expected exactly one slot profile match at {args.slot_length_cm} x {args.slot_width_cm}, found {len(slot_matches)}."
                )
            profile_token = _select_outer_profile(found_profiles, args.width_cm, args.height_cm)["token"]
        else:
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

        if workflow == "filleted_bracket":
            fillet = _send(
                base_url,
                "apply_fillet",
                {
                    "body_token": body_token,
                    "radius_cm": args.fillet_radius_cm,
                    "workflow_name": workflow,
                },
            )
            _print_step("apply_fillet", fillet)
            _require_fillet_matches(
                _require_result_item(fillet, "fillet"),
                radius_cm=args.fillet_radius_cm,
                expected_edge_count=1,
            )
            post_fillet_scene = _send(
                base_url,
                "get_scene_info",
                {"workflow_name": workflow, "workflow_stage": "verify_geometry"},
            )
            _print_step("get_scene_info.verify_geometry.post_fillet", post_fillet_scene)
            _require_scene_matches(
                post_fillet_scene,
                plane=args.plane,
                width_cm=args.width_cm,
                height_cm=args.height_cm,
                thickness_cm=args.thickness_cm,
                body_name=workflow_config["body_name"],
            )

        if workflow in {"plate_with_hole", "counterbored_plate"}:
            # Second sketch: circle for the through-hole, on the same XY construction plane.
            # The cut extrusion intersects the base plate because the circle is positioned
            # within the plate's XY bounds and the cut distance matches the plate thickness.
            pwh_hole_diameter_cm = args.hole_diameter_cm if args.hole_diameter_cm is not None else 0.4
            pwh_hole_center_x_cm = args.hole_center_x_cm if args.hole_center_x_cm is not None else 1.0
            pwh_hole_center_y_cm = args.hole_center_y_cm if args.hole_center_y_cm is not None else 0.5

            hole_sketch = _send(
                base_url,
                "create_sketch",
                {"plane": args.plane, "name": "Hole Sketch", "workflow_name": workflow},
            )
            _print_step("create_sketch.hole", hole_sketch)
            hole_sketch_token = _require_result_item(hole_sketch, "sketch")["token"]

            hole_circle = _send(
                base_url,
                "draw_circle",
                {
                    "sketch_token": hole_sketch_token,
                    "center_x_cm": pwh_hole_center_x_cm,
                    "center_y_cm": pwh_hole_center_y_cm,
                    "radius_cm": pwh_hole_diameter_cm / 2.0,
                    "workflow_name": workflow,
                },
            )
            _print_step("draw_circle.hole", hole_circle)

            hole_profiles = _send(
                base_url,
                "list_profiles",
                {"sketch_token": hole_sketch_token, "workflow_name": workflow},
            )
            _print_step("list_profiles.hole", hole_profiles)
            found_hole_profiles = hole_profiles["result"]["profiles"]
            if len(found_hole_profiles) != 1:
                raise RuntimeError(f"Expected exactly one hole profile, found {len(found_hole_profiles)}.")
            _require_profile_matches(found_hole_profiles[0], pwh_hole_diameter_cm, pwh_hole_diameter_cm)
            hole_profile_token = found_hole_profiles[0]["token"]

            cut_body = _send(
                base_url,
                "extrude_profile",
                {
                    "profile_token": hole_profile_token,
                    "distance_cm": args.thickness_cm,
                    "body_name": "hole",
                    "operation": "cut",
                    "workflow_name": workflow,
                },
            )
            _print_step("extrude_profile.cut", cut_body)
            body_token = _require_result_item(cut_body, "body")["token"]

            post_cut_scene = _send(
                base_url,
                "get_scene_info",
                {"workflow_name": workflow, "workflow_stage": "verify_geometry"},
            )
            _print_step("get_scene_info.verify_geometry.post_cut", post_cut_scene)
            post_cut_bodies = post_cut_scene.get("result", {}).get("bodies", [])
            if len(post_cut_bodies) != 1:
                raise RuntimeError(f"Expected exactly 1 body after cut, found {len(post_cut_bodies)}.")

            if workflow == "counterbored_plate":
                if args.counterbore_diameter_cm is None or args.counterbore_depth_cm is None:
                    raise RuntimeError(
                        "counterbored_plate smoke test requires --counterbore-diameter-cm and --counterbore-depth-cm."
                    )
                counterbore_sketch = _send(
                    base_url,
                    "create_sketch",
                    {"plane": args.plane, "name": "Counterbore Sketch", "workflow_name": workflow},
                )
                _print_step("create_sketch.counterbore", counterbore_sketch)
                counterbore_sketch_token = _require_result_item(counterbore_sketch, "sketch")["token"]

                counterbore_circle = _send(
                    base_url,
                    "draw_circle",
                    {
                        "sketch_token": counterbore_sketch_token,
                        "center_x_cm": pwh_hole_center_x_cm,
                        "center_y_cm": pwh_hole_center_y_cm,
                        "radius_cm": args.counterbore_diameter_cm / 2.0,
                        "workflow_name": workflow,
                    },
                )
                _print_step("draw_circle.counterbore", counterbore_circle)

                counterbore_profiles = _send(
                    base_url,
                    "list_profiles",
                    {"sketch_token": counterbore_sketch_token, "workflow_name": workflow},
                )
                _print_step("list_profiles.counterbore", counterbore_profiles)
                found_counterbore_profiles = counterbore_profiles["result"]["profiles"]
                if len(found_counterbore_profiles) != 1:
                    raise RuntimeError(f"Expected exactly one counterbore profile, found {len(found_counterbore_profiles)}.")
                _require_profile_matches(
                    found_counterbore_profiles[0],
                    args.counterbore_diameter_cm,
                    args.counterbore_diameter_cm,
                )
                counterbore_profile_token = found_counterbore_profiles[0]["token"]

                counterbore_cut_body = _send(
                    base_url,
                    "extrude_profile",
                    {
                        "profile_token": counterbore_profile_token,
                        "distance_cm": args.counterbore_depth_cm,
                        "body_name": "counterbore",
                        "operation": "cut",
                        "workflow_name": workflow,
                    },
                )
                _print_step("extrude_profile.counterbore_cut", counterbore_cut_body)
                body_token = _require_result_item(counterbore_cut_body, "body")["token"]

                post_counterbore_scene = _send(
                    base_url,
                    "get_scene_info",
                    {"workflow_name": workflow, "workflow_stage": "verify_geometry"},
                )
                _print_step("get_scene_info.verify_geometry.post_counterbore", post_counterbore_scene)
                post_counterbore_bodies = post_counterbore_scene.get("result", {}).get("bodies", [])
                if len(post_counterbore_bodies) != 1:
                    raise RuntimeError(f"Expected exactly 1 body after counterbore cut, found {len(post_counterbore_bodies)}.")

        if workflow == "recessed_mount":
            if (
                args.recess_width_cm is None
                or args.recess_height_cm is None
                or args.recess_depth_cm is None
                or args.recess_origin_x_cm is None
                or args.recess_origin_y_cm is None
            ):
                raise RuntimeError(
                    "recessed_mount smoke test requires --recess-width-cm, --recess-height-cm, --recess-depth-cm, --recess-origin-x-cm, and --recess-origin-y-cm."
                )
            recess_sketch = _send(
                base_url,
                "create_sketch",
                {"plane": args.plane, "name": "Recess Sketch", "workflow_name": workflow},
            )
            _print_step("create_sketch.recess", recess_sketch)
            recess_sketch_token = _require_result_item(recess_sketch, "sketch")["token"]

            recess_rectangle = _send(
                base_url,
                "draw_rectangle_at",
                {
                    "sketch_token": recess_sketch_token,
                    "origin_x_cm": args.recess_origin_x_cm,
                    "origin_y_cm": args.recess_origin_y_cm,
                    "width_cm": args.recess_width_cm,
                    "height_cm": args.recess_height_cm,
                    "workflow_name": workflow,
                },
            )
            _print_step("draw_rectangle_at.recess", recess_rectangle)

            recess_profiles = _send(
                base_url,
                "list_profiles",
                {"sketch_token": recess_sketch_token, "workflow_name": workflow},
            )
            _print_step("list_profiles.recess", recess_profiles)
            found_recess_profiles = recess_profiles["result"]["profiles"]
            if len(found_recess_profiles) != 1:
                raise RuntimeError(f"Expected exactly one recess profile, found {len(found_recess_profiles)}.")
            _require_profile_matches(found_recess_profiles[0], args.recess_width_cm, args.recess_height_cm)
            recess_profile_token = found_recess_profiles[0]["token"]

            recess_cut_body = _send(
                base_url,
                "extrude_profile",
                {
                    "profile_token": recess_profile_token,
                    "distance_cm": args.recess_depth_cm,
                    "body_name": "recess",
                    "operation": "cut",
                    "workflow_name": workflow,
                },
            )
            _print_step("extrude_profile.recess_cut", recess_cut_body)
            body_token = _require_result_item(recess_cut_body, "body")["token"]

            post_recess_scene = _send(
                base_url,
                "get_scene_info",
                {"workflow_name": workflow, "workflow_stage": "verify_geometry"},
            )
            _print_step("get_scene_info.verify_geometry.post_recess", post_recess_scene)
            post_recess_bodies = post_recess_scene.get("result", {}).get("bodies", [])
            if len(post_recess_bodies) != 1:
                raise RuntimeError(f"Expected exactly 1 body after recess cut, found {len(post_recess_bodies)}.")

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
