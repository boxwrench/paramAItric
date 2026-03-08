from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from fusion_addin.ops.registry import OperationRegistry
from fusion_addin.state import BodyState, DesignState, SketchState
from fusion_addin.workflows import WorkflowRuntime, WorkflowSession
from mcp_server.workflows import WorkflowRegistry


class FusionAdapter(Protocol):
    def new_design(self, name: str) -> None: ...

    def create_sketch(self, plane: str, name: str) -> dict: ...

    def draw_rectangle(self, sketch_token: str, width_cm: float, height_cm: float) -> dict: ...

    def list_profiles(self, sketch_token: str) -> list[dict]: ...

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str) -> dict: ...

    def get_scene_info(self) -> dict: ...

    def export_stl(self, body_token: str, output_path: str) -> dict: ...


@dataclass
class FusionExecutionContext:
    adapter: FusionAdapter


@dataclass
class FusionApiAdapter:
    app: object
    ui: object
    design: object
    exports: list[str] | None = None
    sketch_planes: dict[str, str] | None = None
    body_planes: dict[str, str] | None = None

    def new_design(self, name: str) -> None:
        name = self._require_non_empty_string(name, "name")
        adsk_core, adsk_fusion = self._load_adsk()

        documents = getattr(self.app, "documents", None)
        if documents is not None and hasattr(documents, "add"):
            document_type = getattr(adsk_core.DocumentTypes, "FusionDesignDocumentType")
            documents.add(document_type)
            self.design = self._require_design(
                adsk_fusion.Design.cast(getattr(self.app, "activeProduct", None)),
                "Fusion did not expose an active design after creating a new document.",
            )

        active_document = getattr(self.app, "activeDocument", None)
        if active_document is not None and hasattr(active_document, "name"):
            active_document.name = name

        self._exports().clear()
        self._sketch_planes().clear()
        self._body_planes().clear()

    def create_sketch(self, plane: str, name: str) -> dict:
        name = self._require_non_empty_string(name, "name")
        normalized_plane = self._normalize_plane_name(plane)
        root_component = self._root_component()
        sketch = root_component.sketches.add(self._construction_plane(root_component, normalized_plane))
        sketch.name = name
        token = self._entity_token(sketch)
        self._sketch_planes()[token] = normalized_plane
        return {"token": token, "name": sketch.name, "plane": normalized_plane}

    def draw_rectangle(self, sketch_token: str, width_cm: float, height_cm: float) -> dict:
        adsk_core, _ = self._load_adsk()
        width_cm = self._require_positive_number(width_cm, "width_cm")
        height_cm = self._require_positive_number(height_cm, "height_cm")
        sketch = self._resolve_entity(sketch_token, "sketch")
        lines = sketch.sketchCurves.sketchLines
        origin = adsk_core.Point3D.create(0, 0, 0)
        corner = adsk_core.Point3D.create(width_cm, height_cm, 0)
        lines.addTwoPointRectangle(origin, corner)
        return {
            "sketch_token": sketch_token,
            "rectangle_index": self._profile_count(sketch) - 1,
            "width_cm": width_cm,
            "height_cm": height_cm,
        }

    def list_profiles(self, sketch_token: str) -> list[dict]:
        sketch = self._resolve_entity(sketch_token, "sketch")
        plane = self._sketch_plane(sketch)
        profiles = []
        for profile in self._iter_collection(sketch.profiles):
            width_cm, height_cm = self._planar_dimensions(profile.boundingBox, plane)
            profiles.append(
                {
                    "token": self._entity_token(profile),
                    "kind": "profile",
                    "width_cm": width_cm,
                    "height_cm": height_cm,
                }
            )
        return profiles

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str) -> dict:
        adsk_core, adsk_fusion = self._load_adsk()
        distance_cm = self._require_positive_number(distance_cm, "distance_cm")
        body_name = self._require_non_empty_string(body_name, "body_name")
        root_component = self._root_component()
        profile = self._resolve_entity(profile_token, "profile")
        plane = self._profile_plane(profile)
        distance = adsk_core.ValueInput.createByReal(distance_cm)
        feature = root_component.features.extrudeFeatures.addSimple(
            profile,
            distance,
            adsk_fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        body = self._first_item(feature.bodies, "extrude result body")
        body.name = body_name
        body_token = self._entity_token(body)
        self._body_planes()[body_token] = plane
        width_cm, height_cm, thickness_cm = self._body_dimensions(body.boundingBox, plane)
        return {
            "token": body_token,
            "name": body.name,
            "width_cm": width_cm,
            "height_cm": height_cm,
            "thickness_cm": thickness_cm,
        }

    def get_scene_info(self) -> dict:
        self._sync_design_from_app()
        root_component = self._root_component()
        active_document = getattr(self.app, "activeDocument", None)
        design_name = getattr(active_document, "name", getattr(root_component, "name", "ParamAItric Design"))
        bodies = []
        for body in self._iter_collection(root_component.bRepBodies):
            body_token = self._entity_token(body)
            plane = self._body_planes().get(body_token, self._infer_plane_from_body(body.boundingBox))
            width_cm, height_cm, thickness_cm = self._body_dimensions(body.boundingBox, plane)
            bodies.append(
                {
                    "token": body_token,
                    "name": getattr(body, "name", ""),
                    "width_cm": width_cm,
                    "height_cm": height_cm,
                    "thickness_cm": thickness_cm,
                }
            )
        return {
            "design_name": design_name,
            "sketches": [
                {
                    "token": self._entity_token(sketch),
                    "name": getattr(sketch, "name", ""),
                    "plane": self._sketch_plane(sketch),
                }
                for sketch in self._iter_collection(root_component.sketches)
            ],
            "bodies": bodies,
            "exports": list(self._exports()),
        }

    def export_stl(self, body_token: str, output_path: str) -> dict:
        output_path = self._require_non_empty_string(output_path, "output_path")
        destination = Path(output_path)
        if not destination.suffix:
            raise ValueError("output_path must include a file extension.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        body = self._resolve_entity(body_token, "body")
        export_manager = self._require_value(getattr(self.design, "exportManager", None), "Fusion export manager not available.")
        options = export_manager.createSTLExportOptions(body, str(destination))
        export_manager.execute(options)
        self._exports().append(str(destination))
        return {"body_token": body_token, "output_path": str(destination)}

    def _load_adsk(self) -> tuple[Any, Any]:
        import adsk.core  # type: ignore[import-not-found]
        import adsk.fusion  # type: ignore[import-not-found]

        return adsk.core, adsk.fusion

    def _exports(self) -> list[str]:
        if self.exports is None:
            self.exports = []
        return self.exports

    def _sketch_planes(self) -> dict[str, str]:
        if self.sketch_planes is None:
            self.sketch_planes = {}
        return self.sketch_planes

    def _body_planes(self) -> dict[str, str]:
        if self.body_planes is None:
            self.body_planes = {}
        return self.body_planes

    def _sync_design_from_app(self) -> None:
        active_product = getattr(self.app, "activeProduct", None)
        if active_product is not None:
            self.design = active_product

    def _root_component(self) -> Any:
        return self._require_value(getattr(self.design, "rootComponent", None), "Fusion root component not available.")

    def _construction_plane(self, root_component: Any, plane: str) -> Any:
        plane_map = {
            "xy": "xYConstructionPlane",
            "xz": "xZConstructionPlane",
            "yz": "yZConstructionPlane",
        }
        try:
            attribute = plane_map[self._normalize_plane_name(plane)]
        except KeyError as exc:
            raise ValueError(f"Unsupported sketch plane: {plane}") from exc
        return self._require_value(getattr(root_component, attribute, None), f"Fusion plane '{plane}' is not available.")

    def _resolve_entity(self, token: str, entity_kind: str) -> Any:
        finder = getattr(self.design, "findEntityByToken", None)
        if finder is None:
            raise RuntimeError("Fusion design does not support entity token lookup.")

        found = finder(token)
        if found is None:
            raise ValueError(f"Referenced {entity_kind} does not exist.")
        if isinstance(found, tuple):
            found = found[0]
        if isinstance(found, list):
            if not found:
                raise ValueError(f"Referenced {entity_kind} does not exist.")
            return found[0]
        if hasattr(found, "count") and hasattr(found, "item"):
            if found.count < 1:
                raise ValueError(f"Referenced {entity_kind} does not exist.")
            return found.item(0)
        return found

    def _entity_token(self, entity: Any) -> str:
        return self._require_value(getattr(entity, "entityToken", None), "Fusion entity does not expose an entity token.")

    def _bounding_box_dimensions(self, bounding_box: Any) -> tuple[float, float, float]:
        min_point = self._require_value(getattr(bounding_box, "minPoint", None), "Fusion bounding box is missing minPoint.")
        max_point = self._require_value(getattr(bounding_box, "maxPoint", None), "Fusion bounding box is missing maxPoint.")
        return (
            float(max_point.x - min_point.x),
            float(max_point.y - min_point.y),
            float(max_point.z - min_point.z),
        )

    def _iter_collection(self, collection: Any) -> list[Any]:
        if hasattr(collection, "count") and hasattr(collection, "item"):
            return [collection.item(index) for index in range(collection.count)]
        return list(collection)

    def _first_item(self, collection: Any, entity_kind: str) -> Any:
        items = self._iter_collection(collection)
        if not items:
            raise RuntimeError(f"Fusion did not return a {entity_kind}.")
        return items[0]

    def _profile_count(self, sketch: Any) -> int:
        profiles = getattr(sketch, "profiles", None)
        return len(self._iter_collection(profiles))

    def _sketch_plane(self, sketch: Any) -> str:
        token = getattr(sketch, "entityToken", None)
        if isinstance(token, str):
            plane = self._sketch_planes().get(token)
            if plane is not None:
                return plane
        plane = getattr(sketch, "referencePlane", None)
        plane_name = getattr(plane, "name", None)
        return self._normalize_plane_name(plane_name)

    def _profile_plane(self, profile: Any) -> str:
        parent_sketch = getattr(profile, "parentSketch", None)
        if parent_sketch is not None:
            return self._sketch_plane(parent_sketch)
        return self._infer_plane_from_profile(profile.boundingBox)

    def _planar_dimensions(self, bounding_box: Any, plane: str) -> tuple[float, float]:
        x_dim, y_dim, z_dim = self._bounding_box_dimensions(bounding_box)
        if plane == "xy":
            return x_dim, y_dim
        if plane == "xz":
            return x_dim, z_dim
        if plane == "yz":
            return y_dim, z_dim
        raise ValueError(f"Unsupported sketch plane: {plane}")

    def _body_dimensions(self, bounding_box: Any, plane: str) -> tuple[float, float, float]:
        x_dim, y_dim, z_dim = self._bounding_box_dimensions(bounding_box)
        if plane == "xy":
            return x_dim, y_dim, z_dim
        if plane == "xz":
            return x_dim, z_dim, y_dim
        if plane == "yz":
            return y_dim, z_dim, x_dim
        raise ValueError(f"Unsupported sketch plane: {plane}")

    def _infer_plane_from_profile(self, bounding_box: Any) -> str:
        x_dim, y_dim, z_dim = self._bounding_box_dimensions(bounding_box)
        zero_axes = [axis for axis, value in (("x", x_dim), ("y", y_dim), ("z", z_dim)) if abs(value) < 1e-9]
        if "z" in zero_axes:
            return "xy"
        if "y" in zero_axes:
            return "xz"
        if "x" in zero_axes:
            return "yz"
        raise RuntimeError("Could not infer profile plane from Fusion bounding box.")

    def _infer_plane_from_body(self, bounding_box: Any) -> str:
        x_dim, y_dim, z_dim = self._bounding_box_dimensions(bounding_box)
        dims = {"x": x_dim, "y": y_dim, "z": z_dim}
        normal_axis = min(dims, key=dims.get)
        if normal_axis == "z":
            return "xy"
        if normal_axis == "y":
            return "xz"
        return "yz"

    def _normalize_plane_name(self, plane_name: Any) -> str:
        if not isinstance(plane_name, str):
            return "unknown"
        normalized = "".join(character.lower() for character in plane_name if character.isalpha())
        plane_aliases = {
            "xy": "xy",
            "xyplane": "xy",
            "xysketchplane": "xy",
            "xz": "xz",
            "xzplane": "xz",
            "xzsketchplane": "xz",
            "yz": "yz",
            "yzplane": "yz",
            "yzsketchplane": "yz",
        }
        return plane_aliases.get(normalized, "unknown")

    def _require_design(self, design: Any, message: str) -> Any:
        if design is None:
            raise RuntimeError(message)
        return design

    def _require_value(self, value: Any, message: str) -> Any:
        if value is None:
            raise RuntimeError(message)
        return value

    def _require_positive_number(self, value: Any, field_name: str) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a positive number.") from exc
        if number <= 0:
            raise ValueError(f"{field_name} must be a positive number.")
        return number

    def _require_non_empty_string(self, value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string.")
        return value


def build_registry(
    workflow_registry: WorkflowRegistry | None = None,
    execution_context: FusionExecutionContext | None = None,
) -> OperationRegistry:
    if execution_context is None:
        raise ValueError("execution_context with a Fusion adapter is required for live ops.")

    registry = OperationRegistry(workflow_registry=workflow_registry)
    runtime = WorkflowRuntime(registry.workflow_registry)
    stage_sessions: dict[str, WorkflowSession] = {}

    def session_for(arguments: dict) -> WorkflowSession | None:
        workflow_name = arguments.get("workflow_name")
        if not workflow_name:
            return None
        if workflow_name not in stage_sessions:
            stage_sessions[workflow_name] = runtime.start(workflow_name)
        return stage_sessions[workflow_name]

    registry.register(
        "new_design",
        lambda state, arguments: new_design(state, arguments, execution_context.adapter, session_for(arguments)),
    )
    registry.register(
        "create_sketch",
        lambda state, arguments: create_sketch(state, arguments, execution_context.adapter, session_for(arguments)),
    )
    registry.register(
        "draw_rectangle",
        lambda state, arguments: draw_rectangle(state, arguments, execution_context.adapter, session_for(arguments)),
    )
    registry.register(
        "list_profiles",
        lambda state, arguments: list_profiles(state, arguments, execution_context.adapter, session_for(arguments)),
    )
    registry.register(
        "extrude_profile",
        lambda state, arguments: extrude_profile(state, arguments, execution_context.adapter, session_for(arguments)),
    )
    registry.register(
        "get_scene_info",
        lambda state, arguments: get_scene_info(state, arguments, execution_context.adapter, session_for(arguments)),
    )
    registry.register(
        "export_stl",
        lambda state, arguments: export_stl(state, arguments, execution_context.adapter, session_for(arguments)),
    )
    registry.register(
        "get_workflow_catalog",
        lambda state, arguments: _workflow_catalog(state, arguments, registry),
    )
    return registry


def _workflow_catalog(state: DesignState, arguments: dict, registry: OperationRegistry) -> dict:
    _ = (state, arguments)
    return {"workflow_catalog": registry.workflow_catalog()}


def _record_stage(session: WorkflowSession | None, stage: str) -> None:
    if session is not None:
        session.record(stage)


def new_design(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    name = arguments.get("name", "ParamAItric Design")
    _record_stage(session, "new_design")
    adapter.new_design(name)
    state.design_name = name
    state.sketches.clear()
    state.bodies.clear()
    state.exports.clear()
    state.active_sketch_token = None
    return {"design_name": name}


def create_sketch(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "create_sketch")
    sketch = adapter.create_sketch(arguments["plane"], arguments["name"])
    token = sketch["token"]
    state.sketches[token] = SketchState(token=token, name=sketch["name"], plane=sketch["plane"])
    state.active_sketch_token = token
    return {"sketch": sketch}


def draw_rectangle(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "draw_rectangle")
    sketch_token = arguments.get("sketch_token") or state.active_sketch_token
    if not sketch_token:
        raise ValueError("A valid sketch_token is required.")
    result = adapter.draw_rectangle(sketch_token, float(arguments["width_cm"]), float(arguments["height_cm"]))
    state.sketches[sketch_token].rectangles.append(
        {"width_cm": result["width_cm"], "height_cm": result["height_cm"]}
    )
    return result


def list_profiles(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "list_profiles")
    sketch_token = arguments.get("sketch_token") or state.active_sketch_token
    if not sketch_token:
        raise ValueError("A valid sketch_token is required.")
    profiles = adapter.list_profiles(sketch_token)
    return {"profiles": profiles}


def extrude_profile(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "extrude_profile")
    body = adapter.extrude_profile(
        arguments["profile_token"],
        float(arguments["distance_cm"]),
        arguments["body_name"],
    )
    token = body["token"]
    state.bodies[token] = BodyState(
        token=token,
        name=body["name"],
        width_cm=body["width_cm"],
        height_cm=body["height_cm"],
        thickness_cm=body["thickness_cm"],
    )
    return {"body": body}


def get_scene_info(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    if session is not None:
        stage = arguments.get("workflow_stage")
        if stage == "verify_clean_state":
            _record_stage(session, "verify_clean_state")
        elif stage == "verify_geometry":
            _record_stage(session, "verify_geometry")
    scene = adapter.get_scene_info()
    state.design_name = scene["design_name"]
    state.exports = list(scene.get("exports", []))
    return scene


def export_stl(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "export_stl")
    output = adapter.export_stl(arguments["body_token"], arguments["output_path"])
    state.exports.append(output["output_path"])
    return output


class RecordingFakeFusionAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.design_name = "ParamAItric Design"
        self.sketches: dict[str, dict] = {}
        self.bodies: dict[str, dict] = {}
        self.exports: list[str] = []
        self.next_id = 1

    def new_design(self, name: str) -> None:
        self.calls.append(("new_design", {"name": name}))
        self.design_name = name
        self.sketches.clear()
        self.bodies.clear()
        self.exports.clear()

    def create_sketch(self, plane: str, name: str) -> dict:
        token = self._token("sketch")
        sketch = {"token": token, "name": name, "plane": plane, "rectangles": []}
        self.calls.append(("create_sketch", {"plane": plane, "name": name}))
        self.sketches[token] = sketch
        return {"token": token, "name": name, "plane": plane}

    def draw_rectangle(self, sketch_token: str, width_cm: float, height_cm: float) -> dict:
        self.calls.append(
            (
                "draw_rectangle",
                {"sketch_token": sketch_token, "width_cm": width_cm, "height_cm": height_cm},
            )
        )
        self.sketches[sketch_token]["rectangles"].append({"width_cm": width_cm, "height_cm": height_cm})
        return {
            "sketch_token": sketch_token,
            "rectangle_index": len(self.sketches[sketch_token]["rectangles"]) - 1,
            "width_cm": width_cm,
            "height_cm": height_cm,
        }

    def list_profiles(self, sketch_token: str) -> list[dict]:
        self.calls.append(("list_profiles", {"sketch_token": sketch_token}))
        return [
            {
                "token": f"{sketch_token}:profile:{index}",
                "kind": "rectangle",
                "width_cm": rectangle["width_cm"],
                "height_cm": rectangle["height_cm"],
            }
            for index, rectangle in enumerate(self.sketches[sketch_token]["rectangles"])
        ]

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str) -> dict:
        self.calls.append(
            (
                "extrude_profile",
                {"profile_token": profile_token, "distance_cm": distance_cm, "body_name": body_name},
            )
        )
        sketch_token, _, profile_index = profile_token.split(":")
        rectangle = self.sketches[sketch_token]["rectangles"][int(profile_index)]
        token = self._token("body")
        body = {
            "token": token,
            "name": body_name,
            "width_cm": rectangle["width_cm"],
            "height_cm": rectangle["height_cm"],
            "thickness_cm": distance_cm,
        }
        self.bodies[token] = body
        return body

    def get_scene_info(self) -> dict:
        self.calls.append(("get_scene_info", {}))
        return {
            "design_name": self.design_name,
            "sketches": [
                {"token": sketch["token"], "name": sketch["name"], "plane": sketch["plane"]}
                for sketch in self.sketches.values()
            ],
            "bodies": list(self.bodies.values()),
            "exports": list(self.exports),
        }

    def export_stl(self, body_token: str, output_path: str) -> dict:
        self.calls.append(("export_stl", {"body_token": body_token, "output_path": output_path}))
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("fake fusion stl export\n", encoding="ascii")
        self.exports.append(str(destination))
        return {"body_token": body_token, "output_path": str(destination)}

    def _token(self, prefix: str) -> str:
        token = f"{prefix}-{self.next_id}"
        self.next_id += 1
        return token
