from __future__ import annotations

import math

from fusion_addin.ops.registry import OperationRegistry
from fusion_addin.state import BodyState, DesignState, SketchState
from mcp_server.schemas import _validate_extrude_operation
from mcp_server.workflows import WorkflowRegistry


def _require_finite_positive(value: float, field_name: str) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field_name} must be a finite positive number.")
    return value


def _require_finite_non_negative(value: float, field_name: str) -> float:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field_name} must be a finite non-negative number.")
    return value


def apply_fillet(state: DesignState, arguments: dict) -> dict:
    body_token = arguments.get("body_token")
    if not body_token:
        raise ValueError("body_token is required.")
    if body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")
    radius_cm = float(arguments["radius_cm"])
    _require_finite_positive(radius_cm, "radius_cm")
    # Mock: does not modify body dimensions; fillets don't change the bounding box significantly.
    return {"fillet": {"body_token": body_token, "radius_cm": radius_cm, "edge_count": 2, "fillet_applied": True}}


def apply_chamfer(state: DesignState, arguments: dict) -> dict:
    body_token = arguments.get("body_token")
    if not body_token:
        raise ValueError("body_token is required.")
    if body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")
    distance_cm = float(arguments["distance_cm"])
    _require_finite_positive(distance_cm, "distance_cm")
    # Mock: does not modify body dimensions; chamfers don't change the bounding box significantly.
    return {"chamfer": {"body_token": body_token, "distance_cm": distance_cm, "edge_count": 2, "chamfer_applied": True}}


def apply_shell(state: DesignState, arguments: dict) -> dict:
    body_token = arguments.get("body_token")
    if not body_token:
        raise ValueError("body_token is required.")
    if body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")
    wall_thickness_cm = float(arguments["wall_thickness_cm"])
    _require_finite_positive(wall_thickness_cm, "wall_thickness_cm")
    body = state.bodies[body_token]
    if wall_thickness_cm * 2.0 >= body.width_cm:
        raise ValueError("wall_thickness_cm must leave a positive inner width.")
    if wall_thickness_cm * 2.0 >= body.height_cm:
        raise ValueError("wall_thickness_cm must leave a positive inner depth.")
    if wall_thickness_cm >= body.thickness_cm:
        raise ValueError("wall_thickness_cm must be smaller than body thickness.")
    return {
        "shell": {
            "token": body_token,
            "body_token": body_token,
            "name": body.name,
            "width_cm": body.width_cm,
            "height_cm": body.height_cm,
            "thickness_cm": body.thickness_cm,
            "wall_thickness_cm": wall_thickness_cm,
            "inner_width_cm": body.width_cm - (wall_thickness_cm * 2.0),
            "inner_depth_cm": body.height_cm - (wall_thickness_cm * 2.0),
            "inner_height_cm": body.thickness_cm - wall_thickness_cm,
            "removed_face_count": 1,
            "open_face": "top",
            "shell_applied": True,
        }
    }


def combine_bodies(state: DesignState, arguments: dict) -> dict:
    target_body_token = arguments.get("target_body_token")
    tool_body_token = arguments.get("tool_body_token")
    if not target_body_token:
        raise ValueError("target_body_token is required.")
    if not tool_body_token:
        raise ValueError("tool_body_token is required.")
    if target_body_token == tool_body_token:
        raise ValueError("tool_body_token must reference a different body.")
    if target_body_token not in state.bodies or tool_body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")

    target_body = state.bodies[target_body_token]
    tool_body = state.bodies[tool_body_token]
    if target_body.plane != tool_body.plane:
        raise ValueError("combine_bodies currently requires bodies on the same plane.")

    combined_min_offset_cm = min(target_body.offset_cm, tool_body.offset_cm)
    combined_max_offset_cm = max(
        target_body.offset_cm + target_body.thickness_cm,
        tool_body.offset_cm + tool_body.thickness_cm,
    )
    target_body.width_cm = max(target_body.width_cm, tool_body.width_cm)
    target_body.height_cm = max(target_body.height_cm, tool_body.height_cm)
    target_body.thickness_cm = combined_max_offset_cm - combined_min_offset_cm
    target_body.offset_cm = combined_min_offset_cm
    del state.bodies[tool_body_token]

    return {
        "body": {
            "token": target_body.token,
            "body_token": target_body.token,
            "name": target_body.name,
            "width_cm": target_body.width_cm,
            "height_cm": target_body.height_cm,
            "thickness_cm": target_body.thickness_cm,
            "plane": target_body.plane,
            "offset_cm": target_body.offset_cm,
            "tool_body_token": tool_body_token,
            "join_applied": True,
        }
    }


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
    registry.register("get_body_info", get_body_info)
    registry.register("get_body_faces", get_body_faces)
    registry.register("get_body_edges", get_body_edges)
    registry.register("export_stl", export_stl)
    registry.register("apply_fillet", apply_fillet)
    registry.register("apply_chamfer", apply_chamfer)
    registry.register("apply_shell", apply_shell)
    registry.register("combine_bodies", combine_bodies)

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
    target_body_token = arguments.get("target_body_token")
    _require_finite_positive(thickness_cm, "distance_cm")

    profile_bounds = None
    profile_sketch = None
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
        profile_sketch = sketch
        break

    if profile_bounds is None or profile_sketch is None:
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
        if target_body_token is not None:
            if target_body_token not in state.bodies:
                raise ValueError("target_body_token must reference an existing body.")
            existing_body = state.bodies[target_body_token]
        else:
            existing_body = next(iter(state.bodies.values()))
        return {
            "body": {
                "token": existing_body.token,
                "name": existing_body.name,
                "width_cm": existing_body.width_cm,
                "height_cm": existing_body.height_cm,
                "thickness_cm": existing_body.thickness_cm,
                "plane": existing_body.plane,
                "offset_cm": existing_body.offset_cm,
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
        plane=profile_sketch.plane,
        offset_cm=profile_sketch.offset_cm,
    )
    state.bodies[body_token] = body
    return {
        "body": {
            "token": body_token,
            "name": body_name,
            "width_cm": body.width_cm,
            "height_cm": body.height_cm,
            "thickness_cm": body.thickness_cm,
            "plane": body.plane,
            "offset_cm": body.offset_cm,
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


def get_body_info(state: DesignState, arguments: dict) -> dict:
    body_token = arguments["body_token"]
    if body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")
    body = state.bodies[body_token]
    return {
        "body_info": {
            "body_token": body_token,
            "name": body.name,
            "width_cm": body.width_cm,
            "height_cm": body.height_cm,
            "thickness_cm": body.thickness_cm,
            "bounding_box": {
                "min_x": 0.0,
                "min_y": 0.0,
                "min_z": 0.0,
                "max_x": body.width_cm,
                "max_y": body.height_cm,
                "max_z": body.thickness_cm,
            },
            "face_count": 6,
            "edge_count": 12,
            "volume_cm3": body.width_cm * body.height_cm * body.thickness_cm,
        },
    }


def get_body_faces(state: DesignState, arguments: dict) -> dict:
    body_token = arguments["body_token"]
    if body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")
    body = state.bodies[body_token]
    return {
        "body_faces": [
            {
                "token": f"{body_token}:face:bottom",
                "type": "planar",
                "normal_vector": {"x": 0.0, "y": 0.0, "z": -1.0},
                "area_cm2": body.width_cm * body.height_cm,
                "bounding_box": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "min_z": 0.0,
                    "max_x": body.width_cm,
                    "max_y": body.height_cm,
                    "max_z": 0.0,
                },
            },
            {
                "token": f"{body_token}:face:top",
                "type": "planar",
                "normal_vector": {"x": 0.0, "y": 0.0, "z": 1.0},
                "area_cm2": body.width_cm * body.height_cm,
                "bounding_box": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "min_z": body.thickness_cm,
                    "max_x": body.width_cm,
                    "max_y": body.height_cm,
                    "max_z": body.thickness_cm,
                },
            },
            {
                "token": f"{body_token}:face:left",
                "type": "planar",
                "normal_vector": {"x": -1.0, "y": 0.0, "z": 0.0},
                "area_cm2": body.height_cm * body.thickness_cm,
                "bounding_box": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "min_z": 0.0,
                    "max_x": 0.0,
                    "max_y": body.height_cm,
                    "max_z": body.thickness_cm,
                },
            },
            {
                "token": f"{body_token}:face:right",
                "type": "planar",
                "normal_vector": {"x": 1.0, "y": 0.0, "z": 0.0},
                "area_cm2": body.height_cm * body.thickness_cm,
                "bounding_box": {
                    "min_x": body.width_cm,
                    "min_y": 0.0,
                    "min_z": 0.0,
                    "max_x": body.width_cm,
                    "max_y": body.height_cm,
                    "max_z": body.thickness_cm,
                },
            },
            {
                "token": f"{body_token}:face:front",
                "type": "planar",
                "normal_vector": {"x": 0.0, "y": -1.0, "z": 0.0},
                "area_cm2": body.width_cm * body.thickness_cm,
                "bounding_box": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "min_z": 0.0,
                    "max_x": body.width_cm,
                    "max_y": 0.0,
                    "max_z": body.thickness_cm,
                },
            },
            {
                "token": f"{body_token}:face:back",
                "type": "planar",
                "normal_vector": {"x": 0.0, "y": 1.0, "z": 0.0},
                "area_cm2": body.width_cm * body.thickness_cm,
                "bounding_box": {
                    "min_x": 0.0,
                    "min_y": body.height_cm,
                    "min_z": 0.0,
                    "max_x": body.width_cm,
                    "max_y": body.height_cm,
                    "max_z": body.thickness_cm,
                },
            },
        ]
    }


def get_body_edges(state: DesignState, arguments: dict) -> dict:
    body_token = arguments["body_token"]
    if body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")
    body = state.bodies[body_token]
    return {
        "body_edges": [
            {
                "token": f"{body_token}:edge:bottom_front",
                "type": "linear",
                "start_point": {"x": 0.0, "y": 0.0, "z": 0.0},
                "end_point": {"x": body.width_cm, "y": 0.0, "z": 0.0},
                "length_cm": body.width_cm,
            },
            {
                "token": f"{body_token}:edge:bottom_right",
                "type": "linear",
                "start_point": {"x": body.width_cm, "y": 0.0, "z": 0.0},
                "end_point": {"x": body.width_cm, "y": body.height_cm, "z": 0.0},
                "length_cm": body.height_cm,
            },
            {
                "token": f"{body_token}:edge:bottom_back",
                "type": "linear",
                "start_point": {"x": body.width_cm, "y": body.height_cm, "z": 0.0},
                "end_point": {"x": 0.0, "y": body.height_cm, "z": 0.0},
                "length_cm": body.width_cm,
            },
            {
                "token": f"{body_token}:edge:bottom_left",
                "type": "linear",
                "start_point": {"x": 0.0, "y": body.height_cm, "z": 0.0},
                "end_point": {"x": 0.0, "y": 0.0, "z": 0.0},
                "length_cm": body.height_cm,
            },
            {
                "token": f"{body_token}:edge:top_front",
                "type": "linear",
                "start_point": {"x": 0.0, "y": 0.0, "z": body.thickness_cm},
                "end_point": {"x": body.width_cm, "y": 0.0, "z": body.thickness_cm},
                "length_cm": body.width_cm,
            },
            {
                "token": f"{body_token}:edge:top_right",
                "type": "linear",
                "start_point": {"x": body.width_cm, "y": 0.0, "z": body.thickness_cm},
                "end_point": {"x": body.width_cm, "y": body.height_cm, "z": body.thickness_cm},
                "length_cm": body.height_cm,
            },
            {
                "token": f"{body_token}:edge:top_back",
                "type": "linear",
                "start_point": {"x": body.width_cm, "y": body.height_cm, "z": body.thickness_cm},
                "end_point": {"x": 0.0, "y": body.height_cm, "z": body.thickness_cm},
                "length_cm": body.width_cm,
            },
            {
                "token": f"{body_token}:edge:top_left",
                "type": "linear",
                "start_point": {"x": 0.0, "y": body.height_cm, "z": body.thickness_cm},
                "end_point": {"x": 0.0, "y": 0.0, "z": body.thickness_cm},
                "length_cm": body.height_cm,
            },
            {
                "token": f"{body_token}:edge:front_left_vertical",
                "type": "linear",
                "start_point": {"x": 0.0, "y": 0.0, "z": 0.0},
                "end_point": {"x": 0.0, "y": 0.0, "z": body.thickness_cm},
                "length_cm": body.thickness_cm,
            },
            {
                "token": f"{body_token}:edge:front_right_vertical",
                "type": "linear",
                "start_point": {"x": body.width_cm, "y": 0.0, "z": 0.0},
                "end_point": {"x": body.width_cm, "y": 0.0, "z": body.thickness_cm},
                "length_cm": body.thickness_cm,
            },
            {
                "token": f"{body_token}:edge:back_right_vertical",
                "type": "linear",
                "start_point": {"x": body.width_cm, "y": body.height_cm, "z": 0.0},
                "end_point": {"x": body.width_cm, "y": body.height_cm, "z": body.thickness_cm},
                "length_cm": body.thickness_cm,
            },
            {
                "token": f"{body_token}:edge:back_left_vertical",
                "type": "linear",
                "start_point": {"x": 0.0, "y": body.height_cm, "z": 0.0},
                "end_point": {"x": 0.0, "y": body.height_cm, "z": body.thickness_cm},
                "length_cm": body.thickness_cm,
            },
        ]
    }


def export_stl(state: DesignState, arguments: dict) -> dict:
    body_token = arguments["body_token"]
    if body_token not in state.bodies:
        raise ValueError("Referenced body does not exist.")
    output_path = state.export(arguments["output_path"])
    return {"body_token": body_token, "output_path": output_path}
