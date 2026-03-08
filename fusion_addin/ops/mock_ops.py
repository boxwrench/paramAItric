from __future__ import annotations

from fusion_addin.ops.registry import OperationRegistry
from fusion_addin.state import BodyState, DesignState, SketchState
from mcp_server.workflows import WorkflowRegistry


def build_registry(workflow_registry: WorkflowRegistry | None = None) -> OperationRegistry:
    registry = OperationRegistry(workflow_registry=workflow_registry)
    registry.register("new_design", new_design)
    registry.register("create_sketch", create_sketch)
    registry.register("draw_rectangle", draw_rectangle)
    registry.register("list_profiles", list_profiles)
    registry.register("extrude_profile", extrude_profile)
    registry.register("get_scene_info", get_scene_info)
    registry.register("export_stl", export_stl)
    registry.register("get_workflow_catalog", get_workflow_catalog)
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
    token = state.issue_token("sketch")
    sketch = SketchState(token=token, name=name, plane=plane)
    state.sketches[token] = sketch
    state.active_sketch_token = token
    return {"sketch": {"token": token, "name": name, "plane": plane}}


def draw_rectangle(state: DesignState, arguments: dict) -> dict:
    token = arguments.get("sketch_token") or state.active_sketch_token
    if not token or token not in state.sketches:
        raise ValueError("A valid sketch_token is required.")

    width_cm = float(arguments["width_cm"])
    height_cm = float(arguments["height_cm"])
    if width_cm <= 0 or height_cm <= 0:
        raise ValueError("Rectangle width_cm and height_cm must be positive.")

    rectangle = {"width_cm": width_cm, "height_cm": height_cm}
    state.sketches[token].rectangles.append(rectangle)
    return {
        "sketch_token": token,
        "rectangle_index": len(state.sketches[token].rectangles) - 1,
        "width_cm": width_cm,
        "height_cm": height_cm,
    }


def list_profiles(state: DesignState, arguments: dict) -> dict:
    token = arguments.get("sketch_token") or state.active_sketch_token
    if not token or token not in state.sketches:
        raise ValueError("A valid sketch_token is required.")

    profiles = []
    for index, rectangle in enumerate(state.sketches[token].rectangles):
        profiles.append(
            {
                "token": f"{token}:profile:{index}",
                "kind": "rectangle",
                "width_cm": rectangle["width_cm"],
                "height_cm": rectangle["height_cm"],
            }
        )
    return {"profiles": profiles}


def extrude_profile(state: DesignState, arguments: dict) -> dict:
    profile_token = arguments["profile_token"]
    thickness_cm = float(arguments["distance_cm"])
    body_name = arguments["body_name"]
    if thickness_cm <= 0:
        raise ValueError("distance_cm must be positive.")

    parts = profile_token.split(":")
    if len(parts) != 3 or parts[1] != "profile":
        raise ValueError("profile_token is invalid.")
    sketch_token = parts[0]
    index_text = parts[2]

    if sketch_token not in state.sketches:
        raise ValueError("Referenced sketch does not exist.")

    index = int(index_text)
    try:
        rectangle = state.sketches[sketch_token].rectangles[index]
    except IndexError as exc:
        raise ValueError("Referenced profile does not exist.") from exc

    body_token = state.issue_token("body")
    body = BodyState(
        token=body_token,
        name=body_name,
        width_cm=rectangle["width_cm"],
        height_cm=rectangle["height_cm"],
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
        }
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


def get_workflow_catalog(state: DesignState, arguments: dict) -> dict:
    _ = (state, arguments)
    return {"workflow_catalog": build_registry().workflow_catalog()}
