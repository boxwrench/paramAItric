from __future__ import annotations

import math

from fusion_addin.ops.registry import OperationRegistry
from fusion_addin.state import BodyState, DesignState, SketchState
from mcp_server.schemas import _validate_extrude_operation
from mcp_server.workflows import WorkflowRegistry


def _require_finite_positive(value: float, field_name: str) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field_name} must be a finite positive number.")


def _require_finite_non_negative(value: float, field_name: str) -> float:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field_name} must be a finite non-negative number.")


def apply_fillet(state: DesignState, arguments: dict) -> dict:
    body_token = arguments.get("body_token")
    if not body_token:
        raise ValueError("body_token is required.")
    if body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")
    radius_cm = float(arguments["radius_cm"])
    _require_finite_positive(radius_cm, "radius_cm")
    # Mock: does not modify body dimensions; fillets don't change the bounding box significantly.
    return {"body_token": body_token, "radius_cm": radius_cm, "fillet_applied": True}


def build_registry(workflow_registry: WorkflowRegistry | None = None) -> OperationRegistry:
    registry = OperationRegistry(workflow_registry=workflow_registry)
    registry.register("new_design", new_design)
    registry.register("create_sketch", create_sketch)
    registry.register("draw_rectangle", draw_rectangle)
    registry.register("draw_rectangle_at", draw_rectangle_at)
    registry.register("draw_l_bracket_profile", draw_l_bracket_profile)
    registry.register("draw_slot", draw_slot)
    registry.register("draw_circle", draw_circle)
    registry.register("list_profiles", list_profiles)
    registry.register("extrude_profile", extrude_profile)
    registry.register("get_scene_info", get_scene_info)
    registry.register("export_stl", export_stl)
    registry.register("apply_fillet", apply_fillet)

    def _get_workflow_catalog(state: DesignState, arguments: dict) -> dict:
        _ = (state, arguments)
        return {"workflow_catalog": registry.workflow_catalog()}

    registry.register("get_workflow_catalog", _get_workflow_catalog)
    return registry


def new_design(state: DesignState, arguments: dict) -> dict:
    state.design_name = arguments.get("name", "ParamAItric Design")
    state.sketches.clear()
    state.bodies.clear()
    state.exports.clear()
    state.active_sketch_token = None
    return {"design_name": state.design_name}


def create_sketch(state: DesignState, arguments: dict) -> dict:
    plane = arguments["plane"]
    name = arguments["name"]
    offset_cm = _require_finite_non_negative(float(arguments.get("offset_cm", 0.0)), "offset_cm")
    token = state.issue_token("sketch")
    sketch = SketchState(token=token, name=name, plane=plane, offset_cm=offset_cm)
    state.sketches[token] = sketch
    state.active_sketch_token = token
    return {"sketch": {"token": token, "name": name, "plane": plane, "offset_cm": offset_cm}}


def draw_rectangle(state: DesignState, arguments: dict) -> dict:
    token = arguments.get("sketch_token") or state.active_sketch_token
    if not token or token not in state.sketches:
        raise ValueError("A valid sketch_token is required.")

    width_cm = float(arguments["width_cm"])
    height_cm = float(arguments["height_cm"])
    _require_finite_positive(width_cm, "width_cm")
    _require_finite_positive(height_cm, "height_cm")

    profile_bounds = {"width_cm": width_cm, "height_cm": height_cm}
    state.sketches[token].profile_bounds.append(profile_bounds)
    return {
        "sketch_token": token,
        "rectangle_index": len(state.sketches[token].profile_bounds) - 1,
        "width_cm": width_cm,
        "height_cm": height_cm,
    }


def draw_rectangle_at(state: DesignState, arguments: dict) -> dict:
    token = arguments.get("sketch_token") or state.active_sketch_token
    if not token or token not in state.sketches:
        raise ValueError("A valid sketch_token is required.")

    origin_x_cm = float(arguments["origin_x_cm"])
    origin_y_cm = float(arguments["origin_y_cm"])
    if not math.isfinite(origin_x_cm) or not math.isfinite(origin_y_cm):
        raise ValueError("origin_x_cm and origin_y_cm must be finite numbers.")
    width_cm = float(arguments["width_cm"])
    height_cm = float(arguments["height_cm"])
    _require_finite_positive(width_cm, "width_cm")
    _require_finite_positive(height_cm, "height_cm")

    profile_bounds = {"width_cm": width_cm, "height_cm": height_cm}
    state.sketches[token].profile_bounds.append(profile_bounds)
    return {
        "sketch_token": token,
        "rectangle_index": len(state.sketches[token].profile_bounds) - 1,
        "origin_x_cm": origin_x_cm,
        "origin_y_cm": origin_y_cm,
        "width_cm": width_cm,
        "height_cm": height_cm,
    }


def draw_l_bracket_profile(state: DesignState, arguments: dict) -> dict:
    token = arguments.get("sketch_token") or state.active_sketch_token
    if not token or token not in state.sketches:
        raise ValueError("A valid sketch_token is required.")

    width_cm = float(arguments["width_cm"])
    height_cm = float(arguments["height_cm"])
    leg_thickness_cm = float(arguments["leg_thickness_cm"])
    _require_finite_positive(width_cm, "width_cm")
    _require_finite_positive(height_cm, "height_cm")
    _require_finite_positive(leg_thickness_cm, "leg_thickness_cm")
    if leg_thickness_cm >= width_cm or leg_thickness_cm >= height_cm:
        raise ValueError("leg_thickness_cm must be smaller than width_cm and height_cm.")

    profile_bounds = {"width_cm": width_cm, "height_cm": height_cm}
    state.sketches[token].profile_bounds.append(profile_bounds)
    return {
        "sketch_token": token,
        "profile_index": len(state.sketches[token].profile_bounds) - 1,
        "width_cm": width_cm,
        "height_cm": height_cm,
        "leg_thickness_cm": leg_thickness_cm,
    }


def draw_circle(state: DesignState, arguments: dict) -> dict:
    token = arguments.get("sketch_token") or state.active_sketch_token
    if not token or token not in state.sketches:
        raise ValueError("A valid sketch_token is required.")

    center_x_cm = float(arguments["center_x_cm"])
    center_y_cm = float(arguments["center_y_cm"])
    radius_cm = float(arguments["radius_cm"])
    if not math.isfinite(center_x_cm) or not math.isfinite(center_y_cm):
        raise ValueError("center_x_cm and center_y_cm must be finite numbers.")
    _require_finite_positive(radius_cm, "radius_cm")

    circle = {
        "center_x_cm": center_x_cm,
        "center_y_cm": center_y_cm,
        "radius_cm": radius_cm,
        "diameter_cm": radius_cm * 2.0,
    }
    state.sketches[token].circles.append(circle)
    return {
        "sketch_token": token,
        "circle_index": len(state.sketches[token].circles) - 1,
        "center_x_cm": center_x_cm,
        "center_y_cm": center_y_cm,
        "radius_cm": radius_cm,
    }


def draw_slot(state: DesignState, arguments: dict) -> dict:
    token = arguments.get("sketch_token") or state.active_sketch_token
    if not token or token not in state.sketches:
        raise ValueError("A valid sketch_token is required.")

    center_x_cm = float(arguments["center_x_cm"])
    center_y_cm = float(arguments["center_y_cm"])
    length_cm = float(arguments["length_cm"])
    width_cm = float(arguments["width_cm"])
    if not math.isfinite(center_x_cm) or not math.isfinite(center_y_cm):
        raise ValueError("center_x_cm and center_y_cm must be finite numbers.")
    _require_finite_positive(length_cm, "length_cm")
    _require_finite_positive(width_cm, "width_cm")
    if length_cm <= width_cm:
        raise ValueError("length_cm must be greater than width_cm for a slot.")

    profile_bounds = {"width_cm": length_cm, "height_cm": width_cm}
    state.sketches[token].profile_bounds.append(profile_bounds)
    return {
        "sketch_token": token,
        "slot_index": len(state.sketches[token].profile_bounds) - 1,
        "center_x_cm": center_x_cm,
        "center_y_cm": center_y_cm,
        "length_cm": length_cm,
        "width_cm": width_cm,
    }


def list_profiles(state: DesignState, arguments: dict) -> dict:
    token = arguments.get("sketch_token") or state.active_sketch_token
    if not token or token not in state.sketches:
        raise ValueError("A valid sketch_token is required.")

    sketch = state.sketches[token]
    profile_items = [
        *sketch.profile_bounds,
        *(
            {"width_cm": circle["diameter_cm"], "height_cm": circle["diameter_cm"]}
            for circle in sketch.circles
        ),
    ]
    while len(sketch.profile_tokens) < len(profile_items):
        sketch.profile_tokens.append(state.issue_token("profile"))

    profiles = []
    for index, profile_bounds in enumerate(sketch.profile_bounds):
        profiles.append(
            {
                "token": sketch.profile_tokens[index],
                "kind": "profile",
                "width_cm": profile_bounds["width_cm"],
                "height_cm": profile_bounds["height_cm"],
            }
        )
    circle_offset = len(profiles)
    for index, circle in enumerate(sketch.circles):
        profiles.append(
            {
                "token": sketch.profile_tokens[circle_offset + index],
                "kind": "profile",
                "width_cm": circle["diameter_cm"],
                "height_cm": circle["diameter_cm"],
            }
        )
    return {"profiles": profiles}


def extrude_profile(state: DesignState, arguments: dict) -> dict:
    profile_token = arguments["profile_token"]
    thickness_cm = float(arguments["distance_cm"])
    body_name = arguments["body_name"]
    operation = _validate_extrude_operation(arguments.get("operation"))
    _require_finite_positive(thickness_cm, "distance_cm")

    profile_bounds = None
    for sketch in state.sketches.values():
        try:
            index = sketch.profile_tokens.index(profile_token)
        except ValueError:
            continue
        profile_items = [
            *sketch.profile_bounds,
            *(
                {"width_cm": circle["diameter_cm"], "height_cm": circle["diameter_cm"]}
                for circle in sketch.circles
            ),
        ]
        try:
            profile_bounds = profile_items[index]
        except IndexError as exc:
            raise ValueError("Referenced profile does not exist.") from exc
        break

    if profile_bounds is None:
        raise ValueError("profile_token is invalid.")

    if operation == "cut":
        # Mock cut: requires at least one existing body to cut into.
        # The real live_ops implementation will perform a Fusion cut extrusion;
        # the mock simply validates preconditions and returns a success payload.
        if not state.bodies:
            raise ValueError(
                "cut operation requires at least one existing body to cut into."
            )
        # Return the first body's token — cut modifies an existing body.
        existing_body = next(iter(state.bodies.values()))
        return {
            "body": {
                "token": existing_body.token,
                "name": existing_body.name,
                "width_cm": existing_body.width_cm,
                "height_cm": existing_body.height_cm,
                "thickness_cm": existing_body.thickness_cm,
            },
            "operation": "cut",
        }

    # operation == "new_body" (default)
    body_token = state.issue_token("body")
    body = BodyState(
        token=body_token,
        name=body_name,
        width_cm=profile_bounds["width_cm"],
        height_cm=profile_bounds["height_cm"],
        thickness_cm=thickness_cm,
    )
    state.bodies[body_token] = body
    return {
        "body": {
            "token": body_token,
            "name": body_name,
            "width_cm": body.width_cm,
            "height_cm": body.height_cm,
            "thickness_cm": body.thickness_cm,
        },
        "operation": "new_body",
    }


def get_scene_info(state: DesignState, arguments: dict) -> dict:
    _ = arguments
    return {
        "design_name": state.design_name,
        "sketches": [
            {"token": sketch.token, "name": sketch.name, "plane": sketch.plane}
            for sketch in state.sketches.values()
        ],
        "bodies": [
            {
                "token": body.token,
                "name": body.name,
                "width_cm": body.width_cm,
                "height_cm": body.height_cm,
                "thickness_cm": body.thickness_cm,
            }
            for body in state.bodies.values()
        ],
        "exports": list(state.exports),
    }


def export_stl(state: DesignState, arguments: dict) -> dict:
    body_token = arguments["body_token"]
    if body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")
    output_path = state.export(arguments["output_path"])
    return {"body_token": body_token, "output_path": output_path}
