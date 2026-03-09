from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from threading import get_ident
from typing import Any, Protocol

from fusion_addin.ops.registry import OperationRegistry
from fusion_addin.state import BodyState, DesignState, SketchState
from fusion_addin.workflows import WorkflowRuntime, WorkflowSession
from mcp_server.schemas import _validate_extrude_operation
from mcp_server.workflows import WorkflowRegistry


class FusionAdapter(Protocol):
    def new_design(self, name: str) -> None: ...

    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict: ...

    def draw_rectangle(self, sketch_token: str, width_cm: float, height_cm: float) -> dict: ...

    def draw_rectangle_at(
        self,
        sketch_token: str,
        origin_x_cm: float,
        origin_y_cm: float,
        width_cm: float,
        height_cm: float,
    ) -> dict: ...

    def draw_l_bracket_profile(
        self,
        sketch_token: str,
        width_cm: float,
        height_cm: float,
        leg_thickness_cm: float,
    ) -> dict: ...

    def draw_slot(
        self,
        sketch_token: str,
        center_x_cm: float,
        center_y_cm: float,
        length_cm: float,
        width_cm: float,
    ) -> dict: ...

    def draw_circle(
        self,
        sketch_token: str,
        center_x_cm: float,
        center_y_cm: float,
        radius_cm: float,
    ) -> dict: ...

    def list_profiles(self, sketch_token: str) -> list[dict]: ...

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, operation: str = "new_body") -> dict: ...

    def apply_fillet(self, body_token: str, radius_cm: float) -> dict: ...

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
    sketch_profile_bounds: dict[str, list[dict[str, object]]] | None = None
    body_planes: dict[str, str] | None = None
    entity_cache: dict[str, object] | None = None
    main_thread_id: int | None = None

    def __post_init__(self) -> None:
        if self.main_thread_id is None:
            self.main_thread_id = get_ident()

    def new_design(self, name: str) -> None:
        self._ensure_main_thread()
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
        self._sketch_profile_bounds().clear()
        self._body_planes().clear()
        self._entity_cache().clear()

    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:
        self._ensure_main_thread()
        name = self._require_non_empty_string(name, "name")
        normalized_plane = self._normalize_plane_name(plane)
        root_component = self._root_component()
        sketch = root_component.sketches.add(
            self._construction_plane(root_component, normalized_plane, offset_cm=offset_cm)
        )
        sketch.name = name
        token = self._entity_token(sketch)
        self._entity_cache()[token] = sketch
        self._sketch_planes()[token] = normalized_plane
        self._sketch_profile_bounds()[token] = []
        result = {"token": token, "name": sketch.name, "plane": normalized_plane}
        if offset_cm is not None:
            result["offset_cm"] = float(offset_cm)
        return result

    def draw_rectangle(self, sketch_token: str, width_cm: float, height_cm: float) -> dict:
        self._ensure_main_thread()
        adsk_core, _ = self._load_adsk()
        width_cm = self._require_positive_number(width_cm, "width_cm")
        height_cm = self._require_positive_number(height_cm, "height_cm")
        sketch = self._resolve_entity(sketch_token, "sketch")
        lines = sketch.sketchCurves.sketchLines
        origin = adsk_core.Point3D.create(0, 0, 0)
        corner = adsk_core.Point3D.create(width_cm, height_cm, 0)
        lines.addTwoPointRectangle(origin, corner)
        self._record_profile_bounds(sketch_token, width_cm, height_cm, shape_kind="rectangle")
        return {
            "sketch_token": sketch_token,
            "rectangle_index": self._profile_count(sketch) - 1,
            "width_cm": width_cm,
            "height_cm": height_cm,
        }

    def draw_rectangle_at(
        self,
        sketch_token: str,
        origin_x_cm: float,
        origin_y_cm: float,
        width_cm: float,
        height_cm: float,
    ) -> dict:
        self._ensure_main_thread()
        adsk_core, _ = self._load_adsk()
        origin_x_cm = float(origin_x_cm)
        origin_y_cm = float(origin_y_cm)
        width_cm = self._require_positive_number(width_cm, "width_cm")
        height_cm = self._require_positive_number(height_cm, "height_cm")
        sketch = self._resolve_entity(sketch_token, "sketch")
        lines = sketch.sketchCurves.sketchLines
        origin = adsk_core.Point3D.create(origin_x_cm, origin_y_cm, 0)
        corner = adsk_core.Point3D.create(origin_x_cm + width_cm, origin_y_cm + height_cm, 0)
        lines.addTwoPointRectangle(origin, corner)
        self._record_profile_bounds(sketch_token, width_cm, height_cm, shape_kind="rectangle")
        return {
            "sketch_token": sketch_token,
            "rectangle_index": self._profile_count(sketch) - 1,
            "origin_x_cm": origin_x_cm,
            "origin_y_cm": origin_y_cm,
            "width_cm": width_cm,
            "height_cm": height_cm,
        }

    def draw_l_bracket_profile(
        self,
        sketch_token: str,
        width_cm: float,
        height_cm: float,
        leg_thickness_cm: float,
    ) -> dict:
        self._ensure_main_thread()
        adsk_core, _ = self._load_adsk()
        width_cm = self._require_positive_number(width_cm, "width_cm")
        height_cm = self._require_positive_number(height_cm, "height_cm")
        leg_thickness_cm = self._require_positive_number(leg_thickness_cm, "leg_thickness_cm")
        if leg_thickness_cm >= width_cm or leg_thickness_cm >= height_cm:
            raise ValueError("leg_thickness_cm must be smaller than width_cm and height_cm.")
        sketch = self._resolve_entity(sketch_token, "sketch")
        lines = sketch.sketchCurves.sketchLines
        points = (
            adsk_core.Point3D.create(0, 0, 0),
            adsk_core.Point3D.create(width_cm, 0, 0),
            adsk_core.Point3D.create(width_cm, leg_thickness_cm, 0),
            adsk_core.Point3D.create(leg_thickness_cm, leg_thickness_cm, 0),
            adsk_core.Point3D.create(leg_thickness_cm, height_cm, 0),
            adsk_core.Point3D.create(0, height_cm, 0),
        )
        for start, end in zip(points, points[1:] + points[:1]):
            lines.addByTwoPoints(start, end)
        self._record_profile_bounds(sketch_token, width_cm, height_cm, shape_kind="l_bracket")
        return {
            "sketch_token": sketch_token,
            "profile_index": self._profile_count(sketch) - 1,
            "width_cm": width_cm,
            "height_cm": height_cm,
            "leg_thickness_cm": leg_thickness_cm,
        }

    def draw_circle(
        self,
        sketch_token: str,
        center_x_cm: float,
        center_y_cm: float,
        radius_cm: float,
    ) -> dict:
        self._ensure_main_thread()
        adsk_core, _ = self._load_adsk()
        center_x_cm = float(center_x_cm)
        center_y_cm = float(center_y_cm)
        radius_cm = self._require_positive_number(radius_cm, "radius_cm")
        sketch = self._resolve_entity(sketch_token, "sketch")
        circles = getattr(sketch.sketchCurves, "sketchCircles", None)
        if circles is None or not hasattr(circles, "addByCenterRadius"):
            raise RuntimeError("Fusion sketch circles are not available.")
        center = adsk_core.Point3D.create(center_x_cm, center_y_cm, 0)
        circles.addByCenterRadius(center, radius_cm)
        return {
            "sketch_token": sketch_token,
            "circle_index": self._profile_count(sketch) - 1,
            "center_x_cm": center_x_cm,
            "center_y_cm": center_y_cm,
            "radius_cm": radius_cm,
        }

    def draw_slot(
        self,
        sketch_token: str,
        center_x_cm: float,
        center_y_cm: float,
        length_cm: float,
        width_cm: float,
    ) -> dict:
        self._ensure_main_thread()
        adsk_core, _ = self._load_adsk()
        center_x_cm = float(center_x_cm)
        center_y_cm = float(center_y_cm)
        length_cm = self._require_positive_number(length_cm, "length_cm")
        width_cm = self._require_positive_number(width_cm, "width_cm")
        if length_cm <= width_cm:
            raise ValueError("length_cm must be greater than width_cm for a slot.")
        sketch = self._resolve_entity(sketch_token, "sketch")
        lines = sketch.sketchCurves.sketchLines
        arcs = getattr(sketch.sketchCurves, "sketchArcs", None)
        if arcs is None or not hasattr(arcs, "addByCenterStartSweep"):
            raise RuntimeError("Fusion sketch arcs are not available.")
        radius_cm = width_cm / 2.0
        half_straight_cm = (length_cm / 2.0) - radius_cm
        left_center_x_cm = center_x_cm - half_straight_cm
        right_center_x_cm = center_x_cm + half_straight_cm
        top_y_cm = center_y_cm + radius_cm
        bottom_y_cm = center_y_cm - radius_cm
        top_left = adsk_core.Point3D.create(left_center_x_cm, top_y_cm, 0)
        top_right = adsk_core.Point3D.create(right_center_x_cm, top_y_cm, 0)
        bottom_right = adsk_core.Point3D.create(right_center_x_cm, bottom_y_cm, 0)
        bottom_left = adsk_core.Point3D.create(left_center_x_cm, bottom_y_cm, 0)
        arcs.addByCenterStartSweep(
            adsk_core.Point3D.create(right_center_x_cm, center_y_cm, 0),
            top_right,
            3.141592653589793,
        )
        arcs.addByCenterStartSweep(
            adsk_core.Point3D.create(left_center_x_cm, center_y_cm, 0),
            bottom_left,
            3.141592653589793,
        )
        lines.addByTwoPoints(top_left, top_right)
        lines.addByTwoPoints(bottom_right, bottom_left)
        self._record_profile_bounds(sketch_token, length_cm, width_cm, shape_kind="slot")
        return {
            "sketch_token": sketch_token,
            "slot_index": self._profile_count(sketch) - 1,
            "center_x_cm": center_x_cm,
            "center_y_cm": center_y_cm,
            "length_cm": length_cm,
            "width_cm": width_cm,
        }

    def list_profiles(self, sketch_token: str) -> list[dict]:
        self._ensure_main_thread()
        sketch = self._resolve_entity(sketch_token, "sketch")
        plane = self._sketch_plane(sketch)
        profiles = []
        recorded_profile_bounds = self._sketch_profile_bounds().get(sketch_token, [])
        for index, profile in enumerate(self._iter_collection(sketch.profiles)):
            profile_token = self._entity_token(profile)
            self._entity_cache()[profile_token] = profile
            width_cm, height_cm = self._profile_dimensions(profile, plane)
            recorded_profile = recorded_profile_bounds[index] if index < len(recorded_profile_bounds) else None
            if plane != "xy" and height_cm < 1e-9 and recorded_profile is not None:
                width_cm = float(recorded_profile["width_cm"])
                height_cm = float(recorded_profile["height_cm"])
            elif plane == "xy" and recorded_profile is not None and recorded_profile.get("shape_kind") == "slot":
                expected_width_cm = float(recorded_profile["width_cm"])
                expected_height_cm = float(recorded_profile["height_cm"])
                if self._slot_profile_dimensions_collapsed(
                    measured_width_cm=width_cm,
                    measured_height_cm=height_cm,
                    expected_width_cm=expected_width_cm,
                    expected_height_cm=expected_height_cm,
                ):
                    width_cm = expected_width_cm
                    height_cm = expected_height_cm
            profiles.append(
                {
                    "token": profile_token,
                    "kind": "profile",
                    "width_cm": width_cm,
                    "height_cm": height_cm,
                }
            )
        if plane == "xy":
            recorded_slot_profiles = [
                profile_bounds
                for profile_bounds in recorded_profile_bounds
                if profile_bounds.get("shape_kind") == "slot"
            ]
            for recorded_slot in recorded_slot_profiles:
                expected_width_cm = float(recorded_slot["width_cm"])
                expected_height_cm = float(recorded_slot["height_cm"])
                if any(
                    abs(float(profile["width_cm"]) - expected_width_cm) <= 1e-9
                    and abs(float(profile["height_cm"]) - expected_height_cm) <= 1e-9
                    for profile in profiles
                ):
                    continue
                matching_candidates = [
                    profile
                    for profile in profiles
                    if self._slot_profile_dimensions_collapsed(
                        measured_width_cm=float(profile["width_cm"]),
                        measured_height_cm=float(profile["height_cm"]),
                        expected_width_cm=expected_width_cm,
                        expected_height_cm=expected_height_cm,
                    )
                ]
                if len(matching_candidates) == 1:
                    matching_candidates[0]["width_cm"] = expected_width_cm
                    matching_candidates[0]["height_cm"] = expected_height_cm
        return profiles

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, operation: str = "new_body") -> dict:
        self._ensure_main_thread()
        adsk_core, adsk_fusion = self._load_adsk()
        distance_cm = self._require_positive_number(distance_cm, "distance_cm")
        body_name = self._require_non_empty_string(body_name, "body_name")
        operation = _validate_extrude_operation(operation)
        root_component = self._root_component()
        profile = self._resolve_entity(profile_token, "profile")
        plane = self._profile_plane(profile)
        distance = adsk_core.ValueInput.createByReal(distance_cm)

        if operation == "cut":
            extrude_input = root_component.features.extrudeFeatures.createInput(
                profile,
                adsk_fusion.FeatureOperations.CutFeatureOperation,
            )
            extrude_input.setDistanceExtent(False, distance)
            try:
                feature = root_component.features.extrudeFeatures.add(extrude_input)
            except Exception as exc:
                raise RuntimeError("Cut extrusion did not intersect any existing body.") from exc
            # Cut modifies an existing body; return the first body touched by the feature.
            body = self._first_item(feature.bodies, "cut extrude result body")
            body_token = self._entity_token(body)
            self._entity_cache()[body_token] = body
            width_cm, height_cm, thickness_cm = self._body_dimensions(body.boundingBox, plane)
            return {
                "token": body_token,
                "name": body.name,
                "width_cm": width_cm,
                "height_cm": height_cm,
                "thickness_cm": thickness_cm,
                "operation": "cut",
            }

        # operation == "new_body" (default)
        feature = root_component.features.extrudeFeatures.addSimple(
            profile,
            distance,
            adsk_fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        body = self._first_item(feature.bodies, "extrude result body")
        body.name = body_name
        body_token = self._entity_token(body)
        self._entity_cache()[body_token] = body
        self._body_planes()[body_token] = plane
        width_cm, height_cm, thickness_cm = self._body_dimensions(body.boundingBox, plane)
        return {
            "token": body_token,
            "name": body.name,
            "width_cm": width_cm,
            "height_cm": height_cm,
            "thickness_cm": thickness_cm,
            "operation": "new_body",
        }

    def apply_fillet(self, body_token: str, radius_cm: float) -> dict:
        self._ensure_main_thread()
        adsk_core, _ = self._load_adsk()
        radius_cm = self._require_positive_number(radius_cm, "radius_cm")
        body = self._resolve_entity(body_token, "body")
        fillet_features = self._require_value(
            getattr(self._root_component().features, "filletFeatures", None),
            "Fusion fillet features are not available.",
        )
        plane = self._body_planes().get(body_token, self._infer_plane_from_body(body.boundingBox))
        edges = self._select_interior_fillet_edges(body, plane)

        edge_collection = adsk_core.ObjectCollection.create()
        for edge in edges:
            edge_collection.add(edge)
        fillet_input = fillet_features.createInput()
        fillet_input.addConstantRadiusEdgeSet(
            edge_collection,
            adsk_core.ValueInput.createByReal(radius_cm),
            True,
        )
        try:
            fillet_features.add(fillet_input)
        except Exception as exc:
            raise RuntimeError("Fillet operation failed.") from exc

        width_cm, height_cm, thickness_cm = self._body_dimensions(body.boundingBox, plane)
        self._entity_cache()[body_token] = body
        return {
            "body_token": body_token,
            "name": body.name,
            "width_cm": width_cm,
            "height_cm": height_cm,
            "thickness_cm": thickness_cm,
            "radius_cm": radius_cm,
            "edge_count": len(edges),
            "fillet_applied": True,
        }

    def get_scene_info(self) -> dict:
        self._ensure_main_thread()
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
        self._ensure_main_thread()
        output_path = self._require_non_empty_string(output_path, "output_path")
        destination = self._validate_export_path(output_path)
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

    def _sketch_profile_bounds(self) -> dict[str, list[dict[str, object]]]:
        if self.sketch_profile_bounds is None:
            self.sketch_profile_bounds = {}
        return self.sketch_profile_bounds

    def _record_profile_bounds(
        self,
        sketch_token: str,
        width_cm: float,
        height_cm: float,
        *,
        shape_kind: str,
    ) -> None:
        self._sketch_profile_bounds().setdefault(sketch_token, []).append(
            {"width_cm": width_cm, "height_cm": height_cm, "shape_kind": shape_kind}
        )

    def _entity_cache(self) -> dict[str, object]:
        if self.entity_cache is None:
            self.entity_cache = {}
        return self.entity_cache

    def _ensure_main_thread(self) -> None:
        if self.main_thread_id is None:
            self.main_thread_id = get_ident()
        if get_ident() != self.main_thread_id:
            raise RuntimeError("Fusion API mutation must execute on the Fusion main thread.")

    def _sync_design_from_app(self) -> None:
        active_product = getattr(self.app, "activeProduct", None)
        if active_product is not None:
            self.design = active_product

    def _root_component(self) -> Any:
        return self._require_value(getattr(self.design, "rootComponent", None), "Fusion root component not available.")

    def _construction_plane(self, root_component: Any, plane: str, offset_cm: float | None = None) -> Any:
        plane_map = {
            "xy": "xYConstructionPlane",
            "xz": "xZConstructionPlane",
            "yz": "yZConstructionPlane",
        }
        try:
            attribute = plane_map[self._normalize_plane_name(plane)]
        except KeyError as exc:
            raise ValueError(f"Unsupported sketch plane: {plane}") from exc
        base_plane = self._require_value(
            getattr(root_component, attribute, None),
            f"Fusion plane '{plane}' is not available.",
        )
        if offset_cm is None:
            return base_plane
        offset_cm = float(offset_cm)
        if offset_cm < 0:
            raise ValueError("offset_cm must be a non-negative number.")
        if abs(offset_cm) < 1e-9:
            return base_plane
        adsk_core, _ = self._load_adsk()
        construction_planes = self._require_value(
            getattr(root_component, "constructionPlanes", None),
            "Fusion construction planes are not available.",
        )
        create_input = self._require_value(
            getattr(construction_planes, "createInput", None),
            "Fusion construction planes do not support createInput().",
        )
        plane_input = create_input()
        set_by_offset = self._require_value(
            getattr(plane_input, "setByOffset", None),
            "Fusion construction plane input does not support setByOffset().",
        )
        set_by_offset(base_plane, adsk_core.ValueInput.createByReal(offset_cm))
        add_plane = self._require_value(
            getattr(construction_planes, "add", None),
            "Fusion construction planes do not support add().",
        )
        return add_plane(plane_input)

    def _resolve_entity(self, token: str, entity_kind: str) -> Any:
        cached = self._entity_cache().get(token)
        if cached is not None and self._matches_entity_kind(cached, entity_kind):
            return cached

        finder = getattr(self.design, "findEntityByToken", None)
        if finder is None:
            raise RuntimeError("Fusion design does not support entity token lookup.")

        found = finder(token)
        if found is None:
            raise ValueError(f"Referenced {entity_kind} does not exist.")
        for candidate in self._candidate_entities(found):
            resolved = getattr(candidate, "nativeObject", None) or candidate
            if self._matches_entity_kind(resolved, entity_kind):
                self._entity_cache()[token] = resolved
                return resolved
        raise ValueError(f"Referenced {entity_kind} does not exist.")

    def _entity_token(self, entity: Any) -> str:
        return self._require_value(getattr(entity, "entityToken", None), "Fusion entity does not expose an entity token.")

    def _candidate_entities(self, found: Any) -> list[Any]:
        if isinstance(found, tuple):
            candidates: list[Any] = []
            for item in found:
                candidates.extend(self._candidate_entities(item))
            return candidates
        if isinstance(found, list):
            return list(found)
        if hasattr(found, "count") and hasattr(found, "item"):
            return [found.item(index) for index in range(found.count)]
        return [found]

    def _matches_entity_kind(self, entity: Any, entity_kind: str) -> bool:
        if entity_kind == "sketch":
            return hasattr(entity, "sketchCurves") and hasattr(entity, "profiles")
        if entity_kind == "profile":
            return hasattr(entity, "parentSketch") and hasattr(entity, "boundingBox")
        if entity_kind == "body":
            return hasattr(entity, "boundingBox") and hasattr(entity, "name")
        return True

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

    def _profile_dimensions(self, profile: Any, plane: str) -> tuple[float, float]:
        x_dim, y_dim, z_dim = self._bounding_box_dimensions(profile.boundingBox)
        width_cm, height_cm = self._planar_dimensions(profile.boundingBox, plane)

        # Real Fusion profile bounding boxes on non-XY sketches can report sketch-local
        # XY extents even when the sketch itself sits on XZ or YZ. Prefer the plane-aware
        # world mapping when it is populated, but fall back to sketch-local extents when
        # that mapping collapses an expected dimension to zero.
        if plane in {"xz", "yz"} and height_cm < 1e-9 and y_dim > 1e-9:
            return x_dim, y_dim
        return width_cm, height_cm

    def _slot_profile_dimensions_collapsed(
        self,
        *,
        measured_width_cm: float,
        measured_height_cm: float,
        expected_width_cm: float,
        expected_height_cm: float,
        tolerance: float = 1e-9,
    ) -> bool:
        return (
            expected_width_cm > expected_height_cm + tolerance
            and measured_width_cm + tolerance < expected_width_cm
            and abs(measured_height_cm - expected_height_cm) <= tolerance
        )

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

    def _select_interior_fillet_edges(self, body: Any, plane: str) -> list[Any]:
        edges = self._iter_collection(getattr(body, "edges", None))
        if not edges:
            raise RuntimeError("Referenced body does not expose any edges for filleting.")

        normal_axis, cross_axes = self._plane_axes(plane)
        bounds = self._bounding_box_axis_bounds(body.boundingBox)
        selected_edges = []
        for edge in edges:
            endpoints = self._edge_endpoints(edge)
            if endpoints is None:
                continue
            start_point, end_point = endpoints
            if not self._edge_parallel_to_axis(start_point, end_point, normal_axis):
                continue
            if any(
                self._point_is_on_boundary(getattr(start_point, axis), bounds[axis])
                for axis in cross_axes
            ):
                continue
            selected_edges.append(edge)

        if selected_edges:
            return selected_edges
        raise RuntimeError("Fillet operation could not identify any interior bracket edges to round.")

    def _plane_axes(self, plane: str) -> tuple[str, tuple[str, str]]:
        if plane == "xy":
            return "z", ("x", "y")
        if plane == "xz":
            return "y", ("x", "z")
        if plane == "yz":
            return "x", ("y", "z")
        raise ValueError(f"Unsupported sketch plane: {plane}")

    def _bounding_box_axis_bounds(self, bounding_box: Any) -> dict[str, tuple[float, float]]:
        min_point = self._require_value(getattr(bounding_box, "minPoint", None), "Fusion bounding box is missing minPoint.")
        max_point = self._require_value(getattr(bounding_box, "maxPoint", None), "Fusion bounding box is missing maxPoint.")
        return {
            "x": (float(min_point.x), float(max_point.x)),
            "y": (float(min_point.y), float(max_point.y)),
            "z": (float(min_point.z), float(max_point.z)),
        }

    def _edge_endpoints(self, edge: Any) -> tuple[Any, Any] | None:
        start_vertex = getattr(edge, "startVertex", None)
        end_vertex = getattr(edge, "endVertex", None)
        start_point = getattr(start_vertex, "geometry", None)
        end_point = getattr(end_vertex, "geometry", None)
        if start_point is None or end_point is None:
            return None
        return start_point, end_point

    def _edge_parallel_to_axis(self, start_point: Any, end_point: Any, axis: str, tolerance: float = 1e-9) -> bool:
        deltas = {
            "x": abs(float(end_point.x) - float(start_point.x)),
            "y": abs(float(end_point.y) - float(start_point.y)),
            "z": abs(float(end_point.z) - float(start_point.z)),
        }
        return deltas[axis] > tolerance and all(
            deltas[other_axis] <= tolerance
            for other_axis in ("x", "y", "z")
            if other_axis != axis
        )

    def _point_is_on_boundary(self, value: float, bounds: tuple[float, float], tolerance: float = 1e-9) -> bool:
        lower_bound, upper_bound = bounds
        return abs(value - lower_bound) <= tolerance or abs(value - upper_bound) <= tolerance

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

    def _validate_export_path(self, output_path: str) -> Path:
        destination = Path(output_path).expanduser().resolve(strict=False)
        if not destination.suffix:
            raise ValueError("output_path must include a file extension.")
        if self._is_allowed_export_path(destination):
            return destination
        raise ValueError("output_path must stay inside an allowlisted export directory.")

    def _is_allowed_export_path(self, destination: Path) -> bool:
        if "manual_test_output" in destination.parts:
            return True
        temp_root = Path(gettempdir()).resolve(strict=False)
        return self._is_within(destination, temp_root)

    def _is_within(self, destination: Path, root: Path) -> bool:
        try:
            destination.relative_to(root)
        except ValueError:
            return False
        return True


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
        command_name = arguments.get("_command_name")
        if workflow_name not in stage_sessions or command_name == "new_design":
            stage_sessions[workflow_name] = runtime.start(workflow_name)
        return stage_sessions[workflow_name]

    registry.register(
        "new_design",
        lambda state, arguments: new_design(
            state,
            {**arguments, "_command_name": "new_design"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "new_design"}),
        ),
    )
    registry.register(
        "create_sketch",
        lambda state, arguments: create_sketch(
            state,
            {**arguments, "_command_name": "create_sketch"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "create_sketch"}),
        ),
    )
    registry.register(
        "draw_rectangle",
        lambda state, arguments: draw_rectangle(
            state,
            {**arguments, "_command_name": "draw_rectangle"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "draw_rectangle"}),
        ),
    )
    registry.register(
        "draw_rectangle_at",
        lambda state, arguments: draw_rectangle_at(
            state,
            {**arguments, "_command_name": "draw_rectangle_at"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "draw_rectangle_at"}),
        ),
    )
    registry.register(
        "draw_l_bracket_profile",
        lambda state, arguments: draw_l_bracket_profile(
            state,
            {**arguments, "_command_name": "draw_l_bracket_profile"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "draw_l_bracket_profile"}),
        ),
    )
    registry.register(
        "draw_slot",
        lambda state, arguments: draw_slot(
            state,
            {**arguments, "_command_name": "draw_slot"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "draw_slot"}),
        ),
    )
    registry.register(
        "draw_circle",
        lambda state, arguments: draw_circle(
            state,
            {**arguments, "_command_name": "draw_circle"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "draw_circle"}),
        ),
    )
    registry.register(
        "list_profiles",
        lambda state, arguments: list_profiles(
            state,
            {**arguments, "_command_name": "list_profiles"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "list_profiles"}),
        ),
    )
    registry.register(
        "extrude_profile",
        lambda state, arguments: extrude_profile(
            state,
            {**arguments, "_command_name": "extrude_profile"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "extrude_profile"}),
        ),
    )
    registry.register(
        "get_scene_info",
        lambda state, arguments: get_scene_info(
            state,
            {**arguments, "_command_name": "get_scene_info"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "get_scene_info"}),
        ),
    )
    registry.register(
        "apply_fillet",
        lambda state, arguments: apply_fillet(
            state,
            {**arguments, "_command_name": "apply_fillet"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "apply_fillet"}),
        ),
    )
    registry.register(
        "export_stl",
        lambda state, arguments: export_stl(
            state,
            {**arguments, "_command_name": "export_stl"},
            execution_context.adapter,
            session_for({**arguments, "_command_name": "export_stl"}),
        ),
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
    sketch = adapter.create_sketch(arguments["plane"], arguments["name"], arguments.get("offset_cm"))
    token = sketch["token"]
    state.sketches[token] = SketchState(
        token=token,
        name=sketch["name"],
        plane=sketch["plane"],
        offset_cm=float(sketch.get("offset_cm", 0.0)),
    )
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
    state.sketches[sketch_token].profile_bounds.append(
        {"width_cm": result["width_cm"], "height_cm": result["height_cm"]}
    )
    return result


def draw_rectangle_at(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "draw_rectangle_at")
    sketch_token = arguments.get("sketch_token") or state.active_sketch_token
    if not sketch_token:
        raise ValueError("A valid sketch_token is required.")
    result = adapter.draw_rectangle_at(
        sketch_token,
        float(arguments["origin_x_cm"]),
        float(arguments["origin_y_cm"]),
        float(arguments["width_cm"]),
        float(arguments["height_cm"]),
    )
    state.sketches[sketch_token].profile_bounds.append(
        {"width_cm": result["width_cm"], "height_cm": result["height_cm"]}
    )
    return result


def draw_l_bracket_profile(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "draw_l_bracket_profile")
    sketch_token = arguments.get("sketch_token") or state.active_sketch_token
    if not sketch_token:
        raise ValueError("A valid sketch_token is required.")
    result = adapter.draw_l_bracket_profile(
        sketch_token,
        float(arguments["width_cm"]),
        float(arguments["height_cm"]),
        float(arguments["leg_thickness_cm"]),
    )
    state.sketches[sketch_token].profile_bounds.append(
        {"width_cm": result["width_cm"], "height_cm": result["height_cm"]}
    )
    return result


def draw_circle(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "draw_circle")
    sketch_token = arguments.get("sketch_token") or state.active_sketch_token
    if not sketch_token:
        raise ValueError("A valid sketch_token is required.")
    result = adapter.draw_circle(
        sketch_token,
        float(arguments["center_x_cm"]),
        float(arguments["center_y_cm"]),
        float(arguments["radius_cm"]),
    )
    state.sketches[sketch_token].circles.append(
        {
            "center_x_cm": result["center_x_cm"],
            "center_y_cm": result["center_y_cm"],
            "radius_cm": result["radius_cm"],
            "diameter_cm": result["radius_cm"] * 2.0,
        }
    )
    return result


def draw_slot(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "draw_slot")
    sketch_token = arguments.get("sketch_token") or state.active_sketch_token
    if not sketch_token:
        raise ValueError("A valid sketch_token is required.")
    result = adapter.draw_slot(
        sketch_token,
        float(arguments["center_x_cm"]),
        float(arguments["center_y_cm"]),
        float(arguments["length_cm"]),
        float(arguments["width_cm"]),
    )
    state.sketches[sketch_token].profile_bounds.append(
        {"width_cm": result["length_cm"], "height_cm": result["width_cm"]}
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
    sketch = state.sketches.get(sketch_token)
    if sketch is not None:
        _normalize_profile_dimensions_from_sketch_state(profiles, sketch)
    return {"profiles": profiles}


def extrude_profile(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "extrude_profile")
    operation = _validate_extrude_operation(arguments.get("operation"))
    body = adapter.extrude_profile(
        arguments["profile_token"],
        float(arguments["distance_cm"]),
        arguments["body_name"],
        operation,
    )
    token = body["token"]
    if operation == "new_body":
        state.bodies[token] = BodyState(
            token=token,
            name=body["name"],
            width_cm=body["width_cm"],
            height_cm=body["height_cm"],
            thickness_cm=body["thickness_cm"],
        )
    # For cut, the body already exists in state; no new entry needed.
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


def apply_fillet(
    state: DesignState,
    arguments: dict,
    adapter: FusionAdapter,
    session: WorkflowSession | None,
) -> dict:
    _record_stage(session, "apply_fillet")
    body_token = arguments["body_token"]
    result = adapter.apply_fillet(body_token, float(arguments["radius_cm"]))
    body_state = state.bodies.get(body_token)
    if body_state is not None:
        body_state.width_cm = result["width_cm"]
        body_state.height_cm = result["height_cm"]
        body_state.thickness_cm = result["thickness_cm"]
    return {"fillet": result}


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


def _normalize_profile_dimensions_from_sketch_state(profiles: list[dict], sketch: SketchState) -> None:
    if sketch.plane == "xy":
        return
    if len(profiles) != len(sketch.profile_bounds):
        return
    for profile, profile_bounds in zip(profiles, sketch.profile_bounds):
        try:
            profile_height = float(profile.get("height_cm", 0.0))
        except (TypeError, ValueError):
            profile_height = 0.0
        if profile_height >= 1e-9:
            continue
        profile["width_cm"] = profile_bounds["width_cm"]
        profile["height_cm"] = profile_bounds["height_cm"]


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

    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:
        token = self._token("sketch")
        sketch = {
            "token": token,
            "name": name,
            "plane": plane,
            "offset_cm": 0.0 if offset_cm is None else float(offset_cm),
            "profile_bounds": [],
            "circles": [],
        }
        arguments = {"plane": plane, "name": name}
        if offset_cm is not None:
            arguments["offset_cm"] = float(offset_cm)
        self.calls.append(("create_sketch", arguments))
        self.sketches[token] = sketch
        return {"token": token, "name": name, "plane": plane, "offset_cm": sketch["offset_cm"]}

    def draw_rectangle(self, sketch_token: str, width_cm: float, height_cm: float) -> dict:
        self.calls.append(
            (
                "draw_rectangle",
                {"sketch_token": sketch_token, "width_cm": width_cm, "height_cm": height_cm},
            )
        )
        self.sketches[sketch_token]["profile_bounds"].append({"width_cm": width_cm, "height_cm": height_cm})
        return {
            "sketch_token": sketch_token,
            "rectangle_index": len(self.sketches[sketch_token]["profile_bounds"]) - 1,
            "width_cm": width_cm,
            "height_cm": height_cm,
        }

    def draw_rectangle_at(
        self,
        sketch_token: str,
        origin_x_cm: float,
        origin_y_cm: float,
        width_cm: float,
        height_cm: float,
    ) -> dict:
        self.calls.append(
            (
                "draw_rectangle_at",
                {
                    "sketch_token": sketch_token,
                    "origin_x_cm": origin_x_cm,
                    "origin_y_cm": origin_y_cm,
                    "width_cm": width_cm,
                    "height_cm": height_cm,
                },
            )
        )
        self.sketches[sketch_token]["profile_bounds"].append({"width_cm": width_cm, "height_cm": height_cm})
        return {
            "sketch_token": sketch_token,
            "rectangle_index": len(self.sketches[sketch_token]["profile_bounds"]) - 1,
            "origin_x_cm": origin_x_cm,
            "origin_y_cm": origin_y_cm,
            "width_cm": width_cm,
            "height_cm": height_cm,
        }

    def draw_l_bracket_profile(
        self,
        sketch_token: str,
        width_cm: float,
        height_cm: float,
        leg_thickness_cm: float,
    ) -> dict:
        self.calls.append(
            (
                "draw_l_bracket_profile",
                {
                    "sketch_token": sketch_token,
                    "width_cm": width_cm,
                    "height_cm": height_cm,
                    "leg_thickness_cm": leg_thickness_cm,
                },
            )
        )
        self.sketches[sketch_token]["profile_bounds"].append({"width_cm": width_cm, "height_cm": height_cm})
        return {
            "sketch_token": sketch_token,
            "profile_index": len(self.sketches[sketch_token]["profile_bounds"]) - 1,
            "width_cm": width_cm,
            "height_cm": height_cm,
            "leg_thickness_cm": leg_thickness_cm,
        }

    def draw_circle(
        self,
        sketch_token: str,
        center_x_cm: float,
        center_y_cm: float,
        radius_cm: float,
    ) -> dict:
        self.calls.append(
            (
                "draw_circle",
                {
                    "sketch_token": sketch_token,
                    "center_x_cm": center_x_cm,
                    "center_y_cm": center_y_cm,
                    "radius_cm": radius_cm,
                },
            )
        )
        self.sketches[sketch_token]["circles"].append(
            {
                "center_x_cm": center_x_cm,
                "center_y_cm": center_y_cm,
                "radius_cm": radius_cm,
                "diameter_cm": radius_cm * 2.0,
            }
        )
        return {
            "sketch_token": sketch_token,
            "circle_index": len(self.sketches[sketch_token]["circles"]) - 1,
            "center_x_cm": center_x_cm,
            "center_y_cm": center_y_cm,
            "radius_cm": radius_cm,
        }

    def draw_slot(
        self,
        sketch_token: str,
        center_x_cm: float,
        center_y_cm: float,
        length_cm: float,
        width_cm: float,
    ) -> dict:
        self.calls.append(
            (
                "draw_slot",
                {
                    "sketch_token": sketch_token,
                    "center_x_cm": center_x_cm,
                    "center_y_cm": center_y_cm,
                    "length_cm": length_cm,
                    "width_cm": width_cm,
                },
            )
        )
        self.sketches[sketch_token]["profile_bounds"].append({"width_cm": length_cm, "height_cm": width_cm})
        return {
            "sketch_token": sketch_token,
            "slot_index": len(self.sketches[sketch_token]["profile_bounds"]) - 1,
            "center_x_cm": center_x_cm,
            "center_y_cm": center_y_cm,
            "length_cm": length_cm,
            "width_cm": width_cm,
        }

    def list_profiles(self, sketch_token: str) -> list[dict]:
        self.calls.append(("list_profiles", {"sketch_token": sketch_token}))
        profiles = [
            {
                "token": f"{sketch_token}:profile:{index}",
                "kind": "profile",
                "width_cm": profile_bounds["width_cm"],
                "height_cm": profile_bounds["height_cm"],
            }
            for index, profile_bounds in enumerate(self.sketches[sketch_token]["profile_bounds"])
        ]
        circle_offset = len(profiles)
        profiles.extend(
            {
                "token": f"{sketch_token}:profile:{circle_offset + index}",
                "kind": "profile",
                "width_cm": circle["diameter_cm"],
                "height_cm": circle["diameter_cm"],
            }
            for index, circle in enumerate(self.sketches[sketch_token]["circles"])
        )
        return profiles

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, operation: str = "new_body") -> dict:
        self.calls.append(
            (
                "extrude_profile",
                {"profile_token": profile_token, "distance_cm": distance_cm, "body_name": body_name, "operation": operation},
            )
        )
        sketch_token, _, profile_index = profile_token.split(":")
        profile_items = [
            *self.sketches[sketch_token]["profile_bounds"],
            *(
                {"width_cm": circle["diameter_cm"], "height_cm": circle["diameter_cm"]}
                for circle in self.sketches[sketch_token]["circles"]
            ),
        ]
        profile_bounds = profile_items[int(profile_index)]
        if operation == "cut":
            # Mock cut: return the first existing body (same contract as mock_ops).
            if not self.bodies:
                raise ValueError("cut operation requires at least one existing body to cut into.")
            existing_body = next(iter(self.bodies.values()))
            return {**existing_body, "operation": "cut"}
        token = self._token("body")
        body = {
            "token": token,
            "name": body_name,
            "width_cm": profile_bounds["width_cm"],
            "height_cm": profile_bounds["height_cm"],
            "thickness_cm": distance_cm,
            "operation": "new_body",
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

    def apply_fillet(self, body_token: str, radius_cm: float) -> dict:
        self.calls.append(("apply_fillet", {"body_token": body_token, "radius_cm": radius_cm}))
        if body_token not in self.bodies:
            raise ValueError("Referenced body does not exist.")
        if radius_cm <= 0:
            raise ValueError("radius_cm must be a positive number.")
        body = self.bodies[body_token]
        return {
            "body_token": body_token,
            "name": body["name"],
            "width_cm": body["width_cm"],
            "height_cm": body["height_cm"],
            "thickness_cm": body["thickness_cm"],
            "radius_cm": radius_cm,
            "edge_count": 1,
            "fillet_applied": True,
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
