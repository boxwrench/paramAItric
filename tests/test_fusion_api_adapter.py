from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from fusion_addin.ops.live_ops import FusionApiAdapter


@dataclass
class FakePoint:
    x: float
    y: float
    z: float


@dataclass
class FakeBoundingBox:
    minPoint: FakePoint
    maxPoint: FakePoint


class FakeCollection:
    def __init__(self, items: list[object] | None = None) -> None:
        self._items = items or []

    @property
    def count(self) -> int:
        return len(self._items)

    def item(self, index: int) -> object:
        return self._items[index]

    def append(self, item: object) -> None:
        self._items.append(item)

    def clear(self) -> None:
        self._items.clear()


class FakeProfile:
    def __init__(
        self,
        token: str,
        width_cm: float,
        height_cm: float,
        parent_sketch: "FakeSketch",
        *,
        shape_kind: str = "rectangle",
        metadata: dict[str, float] | None = None,
    ) -> None:
        self.entityToken = token
        self.parentSketch = parent_sketch
        self.shape_kind = shape_kind
        self.metadata = metadata or {}
        if parent_sketch.referencePlane.name == "XY Plane":
            max_point = FakePoint(width_cm, height_cm, 0)
        elif parent_sketch.referencePlane.name == "XZ Plane":
            max_point = FakePoint(width_cm, 0, height_cm)
        else:
            max_point = FakePoint(0, width_cm, height_cm)
        self.boundingBox = FakeBoundingBox(FakePoint(0, 0, 0), max_point)


class FakeSketchLines:
    def __init__(self, sketch: "FakeSketch") -> None:
        self._sketch = sketch
        self._pending_points: list[FakePoint] = []

    def addTwoPointRectangle(self, start: FakePoint, corner: FakePoint) -> None:  # noqa: N802
        width_cm = corner.x - start.x
        height_cm = corner.y - start.y
        profile = FakeProfile(
            token=f"{self._sketch.entityToken}:profile:{self._sketch.profiles.count}",
            width_cm=width_cm,
            height_cm=height_cm,
            parent_sketch=self._sketch,
            shape_kind="rectangle",
        )
        self._sketch.profiles.append(profile)
        self._sketch._design.register(profile)

    def addByTwoPoints(self, start: FakePoint, end: FakePoint) -> None:  # noqa: N802
        if getattr(self._sketch, "_pending_slot", None) is not None:
            self._sketch._pending_slot["line_count"] += 1
            if self._sketch._pending_slot["line_count"] == 2 and self._sketch._pending_slot["arc_count"] == 2:
                pending = self._sketch._pending_slot
                profile = FakeProfile(
                    token=f"{self._sketch.entityToken}:profile:{self._sketch.profiles.count}",
                    width_cm=pending["length_cm"],
                    height_cm=pending["width_cm"],
                    parent_sketch=self._sketch,
                    shape_kind="slot",
                )
                self._sketch.profiles.append(profile)
                self._sketch._design.register(profile)
                self._sketch._pending_slot = None
            return
        if not self._pending_points:
            self._pending_points.append(start)
        self._pending_points.append(end)
        if (
            len(self._pending_points) >= 7
            and end.x == self._pending_points[0].x
            and end.y == self._pending_points[0].y
            and end.z == self._pending_points[0].z
        ):
            width_cm = max(point.x for point in self._pending_points)
            height_cm = max(point.y for point in self._pending_points)
            profile = FakeProfile(
                token=f"{self._sketch.entityToken}:profile:{self._sketch.profiles.count}",
                width_cm=width_cm,
                height_cm=height_cm,
                parent_sketch=self._sketch,
                shape_kind="l_bracket",
                metadata={"leg_thickness_cm": self._pending_points[2].y},
            )
            self._sketch.profiles.append(profile)
            self._sketch._design.register(profile)
            self._pending_points = []


class FakeSketchArcs:
    def __init__(self, sketch: "FakeSketch") -> None:
        self._sketch = sketch

    def addByCenterStartSweep(self, center: FakePoint, start: FakePoint, sweep: float) -> None:  # noqa: N802
        _ = (start, sweep)
        pending = getattr(self._sketch, "_pending_slot", None)
        if pending is None:
            pending = {"arc_count": 0, "line_count": 0, "centers": [], "radius_cm": 0.0}
            self._sketch._pending_slot = pending
        pending["arc_count"] += 1
        pending["centers"].append(center)
        pending["radius_cm"] = max(pending["radius_cm"], abs(start.y - center.y), abs(start.x - center.x))
        if pending["arc_count"] == 2:
            left_center = min(pending["centers"], key=lambda point: point.x)
            right_center = max(pending["centers"], key=lambda point: point.x)
            pending["length_cm"] = (right_center.x - left_center.x) + (pending["radius_cm"] * 2.0)
            pending["width_cm"] = pending["radius_cm"] * 2.0
            if pending["line_count"] == 2:
                profile = FakeProfile(
                    token=f"{self._sketch.entityToken}:profile:{self._sketch.profiles.count}",
                    width_cm=pending["length_cm"],
                    height_cm=pending["width_cm"],
                    parent_sketch=self._sketch,
                    shape_kind="slot",
                )
                self._sketch.profiles.append(profile)
                self._sketch._design.register(profile)
                self._sketch._pending_slot = None


class FakeSketchCircles:
    def __init__(self, sketch: "FakeSketch") -> None:
        self._sketch = sketch

    def addByCenterRadius(self, center: FakePoint, radius: float) -> None:  # noqa: N802
        _ = center
        diameter_cm = radius * 2.0
        profile = FakeProfile(
            token=f"{self._sketch.entityToken}:profile:{self._sketch.profiles.count}",
            width_cm=diameter_cm,
            height_cm=diameter_cm,
            parent_sketch=self._sketch,
            shape_kind="circle",
        )
        self._sketch.profiles.append(profile)
        self._sketch._design.register(profile)


class FakeSketch:
    def __init__(self, design: "FakeDesign", token: str, plane_name: str) -> None:
        self._design = design
        self.entityToken = token
        self.name = ""
        self.referencePlane = SimpleNamespace(name=plane_name)
        self.profiles = FakeCollection()
        self._pending_slot: dict[str, object] | None = None
        self.sketchCurves = SimpleNamespace(
            sketchLines=FakeSketchLines(self),
            sketchCircles=FakeSketchCircles(self),
            sketchArcs=FakeSketchArcs(self),
        )


class FakeVertex:
    def __init__(self, point: FakePoint) -> None:
        self.geometry = point


class FakeEdge:
    def __init__(self, token: str, start: FakePoint, end: FakePoint) -> None:
        self.entityToken = token
        self.startVertex = FakeVertex(start)
        self.endVertex = FakeVertex(end)


class FakeSketches:
    def __init__(self, design: "FakeDesign") -> None:
        self._design = design
        self._items = FakeCollection()

    @property
    def count(self) -> int:
        return self._items.count

    def item(self, index: int) -> object:
        return self._items.item(index)

    def add(self, plane: object) -> FakeSketch:
        token = self._design.issue_token("sketch")
        sketch = FakeSketch(design=self._design, token=token, plane_name=plane.name)
        self._items.append(sketch)
        self._design.register(sketch)
        return sketch

    def clear(self) -> None:
        self._items.clear()


class FakeBody:
    def __init__(
        self,
        token: str,
        name: str,
        width_cm: float,
        height_cm: float,
        thickness_cm: float,
        *,
        edges: list[object] | None = None,
    ) -> None:
        self.entityToken = token
        self.name = name
        self.boundingBox = FakeBoundingBox(FakePoint(0, 0, 0), FakePoint(width_cm, height_cm, thickness_cm))
        self.edges = FakeCollection(edges or [])


class FakeExtrudeFeatures:
    def __init__(self, design: "FakeDesign") -> None:
        self._design = design

    def addSimple(self, profile: FakeProfile, distance: object, operation: object) -> object:  # noqa: N802
        _ = operation
        if profile.parentSketch.referencePlane.name == "XY Plane":
            width_cm = profile.boundingBox.maxPoint.x - profile.boundingBox.minPoint.x
            height_cm = profile.boundingBox.maxPoint.y - profile.boundingBox.minPoint.y
            max_point = FakePoint(width_cm, height_cm, distance.value)
        elif profile.parentSketch.referencePlane.name == "XZ Plane":
            width_cm = profile.boundingBox.maxPoint.x - profile.boundingBox.minPoint.x
            height_cm = profile.boundingBox.maxPoint.z - profile.boundingBox.minPoint.z
            max_point = FakePoint(width_cm, distance.value, height_cm)
        else:
            width_cm = profile.boundingBox.maxPoint.y - profile.boundingBox.minPoint.y
            height_cm = profile.boundingBox.maxPoint.z - profile.boundingBox.minPoint.z
            max_point = FakePoint(distance.value, width_cm, height_cm)
        thickness_cm = distance.value
        token = self._design.issue_token("body")
        body = FakeBody(
            token=token,
            name="Body",
            width_cm=width_cm,
            height_cm=height_cm,
            thickness_cm=thickness_cm,
            edges=self._build_edges(token, profile, thickness_cm),
        )
        body.boundingBox = FakeBoundingBox(FakePoint(0, 0, 0), max_point)
        self._design.rootComponent.bRepBodies.append(body)
        self._design.register(body)
        return SimpleNamespace(bodies=FakeCollection([body]))

    def _build_edges(self, token: str, profile: FakeProfile, thickness_cm: float) -> list[object]:
        if profile.shape_kind == "l_bracket":
            leg_thickness_cm = profile.metadata["leg_thickness_cm"]
            profile_points = [
                (0.0, 0.0),
                (profile.boundingBox.maxPoint.x, 0.0),
                (profile.boundingBox.maxPoint.x, leg_thickness_cm),
                (leg_thickness_cm, leg_thickness_cm),
                (leg_thickness_cm, profile.boundingBox.maxPoint.y),
                (0.0, profile.boundingBox.maxPoint.y),
            ]
        else:
            profile_points = [
                (0.0, 0.0),
                (profile.boundingBox.maxPoint.x, 0.0),
                (profile.boundingBox.maxPoint.x, profile.boundingBox.maxPoint.y),
                (0.0, profile.boundingBox.maxPoint.y),
            ]

        edges = []
        for index, (axis_a, axis_b) in enumerate(profile_points):
            start = FakePoint(axis_a, axis_b, 0.0)
            end = FakePoint(axis_a, axis_b, thickness_cm)
            edges.append(FakeEdge(f"{token}:edge:{index}", start, end))
        return edges


class FakeObjectCollection:
    def __init__(self) -> None:
        self.items: list[object] = []

    def add(self, item: object) -> None:
        self.items.append(item)


class FakeFilletInput:
    def __init__(self) -> None:
        self.edge_sets: list[tuple[FakeObjectCollection, object, bool]] = []

    def addConstantRadiusEdgeSet(self, edges: FakeObjectCollection, radius: object, is_tangent_chain: bool) -> None:  # noqa: N802
        self.edge_sets.append((edges, radius, is_tangent_chain))


class FakeFilletFeatures:
    def __init__(self, design: "FakeDesign") -> None:
        self._design = design
        self.last_input: FakeFilletInput | None = None

    def createInput(self) -> FakeFilletInput:  # noqa: N802
        self.last_input = FakeFilletInput()
        return self.last_input

    def add(self, fillet_input: FakeFilletInput) -> object:
        if not fillet_input.edge_sets:
            raise RuntimeError("fillet edge set required")
        return SimpleNamespace()


class FakeExportManager:
    def createSTLExportOptions(self, body: FakeBody, output_path: str) -> object:  # noqa: N802
        return SimpleNamespace(body=body, output_path=output_path)

    def execute(self, options: object) -> None:
        output_path = Path(options.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("fake stl\n", encoding="ascii")


class FakeRootComponent:
    def __init__(self, design: "FakeDesign", reject_name_changes: bool = False) -> None:
        self._name = "Root"
        self._reject_name_changes = reject_name_changes
        self.xYConstructionPlane = SimpleNamespace(name="XY Plane")
        self.xZConstructionPlane = SimpleNamespace(name="XZ Plane")
        self.yZConstructionPlane = SimpleNamespace(name="YZ Plane")
        self.sketches = FakeSketches(design)
        self.bRepBodies = FakeCollection()
        self.features = SimpleNamespace(
            extrudeFeatures=FakeExtrudeFeatures(design),
            filletFeatures=FakeFilletFeatures(design),
        )

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if self._reject_name_changes:
            raise RuntimeError("root component name cannot be changed")
        self._name = value


class FakeDesign:
    def __init__(self, reject_root_name_changes: bool = False) -> None:
        self.rootComponent = FakeRootComponent(self, reject_name_changes=reject_root_name_changes)
        self.exportManager = FakeExportManager()
        self._next_id = 1
        self._entities: dict[str, object] = {}

    def issue_token(self, prefix: str) -> str:
        token = f"{prefix}-{self._next_id}"
        self._next_id += 1
        return token

    def register(self, entity: object) -> None:
        self._entities[entity.entityToken] = entity

    def findEntityByToken(self, token: str) -> list[object]:  # noqa: N802
        entity = self._entities.get(token)
        return [] if entity is None else [entity]


class FakeDocuments:
    def __init__(self, app: "FakeApp") -> None:
        self._app = app

    def add(self, document_type: object) -> object:
        _ = document_type
        document = SimpleNamespace(name="Untitled")
        design = FakeDesign()
        self._app.activeDocument = document
        self._app.activeProduct = design
        return document


class FakeVector:
    def __init__(self) -> None:
        self.objectType = "adsk::core::BaseVector"


class FakeApp:
    def __init__(self) -> None:
        self.activeDocument = SimpleNamespace(name="Current")
        self.activeProduct = FakeDesign()
        self.documents = FakeDocuments(self)


class TestFusionApiAdapter(FusionApiAdapter):
    def _load_adsk(self) -> tuple[object, object]:
        core = SimpleNamespace(
            DocumentTypes=SimpleNamespace(FusionDesignDocumentType="fusion"),
            ObjectCollection=SimpleNamespace(create=lambda: FakeObjectCollection()),
            Point3D=SimpleNamespace(create=lambda x, y, z: FakePoint(x, y, z)),
            ValueInput=SimpleNamespace(createByReal=lambda value: SimpleNamespace(value=value)),
        )
        fusion = SimpleNamespace(
            Design=SimpleNamespace(cast=lambda product: product),
            FeatureOperations=SimpleNamespace(NewBodyFeatureOperation="new_body"),
        )
        return core, fusion


def test_fusion_api_adapter_runs_spacer_sequence() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)
    output_path = Path.cwd() / "manual_test_output" / "adapter_spacer_test.stl"

    adapter.new_design("Spacer Workflow")
    sketch = adapter.create_sketch("xy", "Spacer Sketch")
    rectangle = adapter.draw_rectangle(sketch["token"], 2.0, 1.0)
    profiles = adapter.list_profiles(sketch["token"])
    body = adapter.extrude_profile(profiles[0]["token"], 0.5, "Spacer")
    scene = adapter.get_scene_info()
    exported = adapter.export_stl(body["token"], str(output_path))

    assert rectangle["rectangle_index"] == 0
    assert profiles[0]["width_cm"] == 2.0
    assert body["thickness_cm"] == 0.5
    assert scene["design_name"] == "Spacer Workflow"
    assert scene["sketches"][0]["plane"] == "xy"
    assert scene["bodies"][0]["name"] == "Spacer"
    assert scene["exports"] == []
    assert exported["output_path"].endswith("adapter_spacer_test.stl")
    assert Path(exported["output_path"]).exists()
    assert adapter.get_scene_info()["exports"] == [exported["output_path"]]


def test_fusion_api_adapter_normalizes_real_plane_names_and_reports_xz_dimensions() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Bracket Workflow")
    sketch = adapter.create_sketch("xz", "Bracket Sketch")
    adapter.draw_rectangle(sketch["token"], 4.0, 2.0)
    profiles = adapter.list_profiles(sketch["token"])
    body = adapter.extrude_profile(profiles[0]["token"], 0.75, "Bracket")
    scene = adapter.get_scene_info()

    assert sketch["plane"] == "xz"
    assert scene["sketches"][0]["plane"] == "xz"
    assert profiles[0]["width_cm"] == 4.0
    assert profiles[0]["height_cm"] == 2.0
    assert body["width_cm"] == 4.0
    assert body["height_cm"] == 2.0
    assert body["thickness_cm"] == 0.75
    assert scene["bodies"][0]["width_cm"] == 4.0
    assert scene["bodies"][0]["height_cm"] == 2.0
    assert scene["bodies"][0]["thickness_cm"] == 0.75


def test_fusion_api_adapter_draws_l_bracket_profile() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Bracket Workflow")
    sketch = adapter.create_sketch("xy", "Bracket Sketch")
    profile = adapter.draw_l_bracket_profile(sketch["token"], 4.0, 2.0, 0.5)
    profiles = adapter.list_profiles(sketch["token"])
    body = adapter.extrude_profile(profiles[0]["token"], 0.75, "Bracket")

    assert profile["profile_index"] == 0
    assert profiles[0]["width_cm"] == 4.0
    assert profiles[0]["height_cm"] == 2.0
    assert body["width_cm"] == 4.0
    assert body["height_cm"] == 2.0


def test_fusion_api_adapter_draws_circle_profile() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Mounting Bracket Workflow")
    sketch = adapter.create_sketch("xy", "Mounting Bracket Sketch")
    adapter.draw_l_bracket_profile(sketch["token"], 4.0, 2.0, 0.5)
    circle = adapter.draw_circle(sketch["token"], 0.25, 1.5, 0.2)
    profiles = adapter.list_profiles(sketch["token"])

    assert circle["circle_index"] == 1
    assert len(profiles) == 2
    assert profiles[1]["width_cm"] == 0.4
    assert profiles[1]["height_cm"] == 0.4


def test_fusion_api_adapter_draws_slot_profile() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Slotted Mount Workflow")
    sketch = adapter.create_sketch("xy", "Slotted Mount Sketch")
    adapter.draw_rectangle(sketch["token"], 4.0, 2.0)
    slot = adapter.draw_slot(sketch["token"], 2.0, 1.0, 1.5, 0.5)
    profiles = adapter.list_profiles(sketch["token"])

    assert slot["slot_index"] == 1
    assert len(profiles) == 2
    assert profiles[1]["width_cm"] == 1.5
    assert profiles[1]["height_cm"] == 0.5


def test_fusion_api_adapter_draws_offset_rectangle_profile() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Recessed Mount Workflow")
    sketch = adapter.create_sketch("xy", "Recess Sketch")
    rectangle = adapter.draw_rectangle_at(sketch["token"], 1.0, 0.75, 2.0, 1.0)
    profiles = adapter.list_profiles(sketch["token"])

    assert rectangle["rectangle_index"] == 0
    assert rectangle["origin_x_cm"] == 1.0
    assert rectangle["origin_y_cm"] == 0.75
    assert profiles[0]["width_cm"] == 2.0
    assert profiles[0]["height_cm"] == 1.0


def test_fusion_api_adapter_falls_back_to_recorded_slot_length_for_collapsed_xy_profile() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Collapsed Slot Fallback Workflow")
    sketch = adapter.create_sketch("xy", "Collapsed Slot Sketch")
    adapter.draw_rectangle(sketch["token"], 4.0, 2.0)
    adapter.draw_slot(sketch["token"], 2.0, 1.0, 1.5, 0.5)

    stored_sketch = app.activeProduct.findEntityByToken(sketch["token"])[0]
    slot_profile = stored_sketch.profiles.item(1)
    slot_profile.boundingBox = FakeBoundingBox(FakePoint(0, 0, 0), FakePoint(1.0, 0.5, 0.0))

    profiles = adapter.list_profiles(sketch["token"])

    assert profiles[1]["width_cm"] == 1.5
    assert profiles[1]["height_cm"] == 0.5


def test_fusion_api_adapter_applies_fillet_to_existing_body() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Filleted Bracket Workflow")
    sketch = adapter.create_sketch("xy", "Bracket Sketch")
    adapter.draw_l_bracket_profile(sketch["token"], 4.0, 2.0, 0.5)
    body = adapter.extrude_profile(adapter.list_profiles(sketch["token"])[0]["token"], 0.75, "Bracket")

    fillet = adapter.apply_fillet(body["token"], 0.2)

    assert fillet["body_token"] == body["token"]
    assert fillet["radius_cm"] == 0.2
    assert fillet["edge_count"] == 1
    assert fillet["fillet_applied"] is True
    edge_set, _, _ = app.activeProduct.rootComponent.features.filletFeatures.last_input.edge_sets[0]
    assert len(edge_set.items) == 1
    assert edge_set.items[0].entityToken.endswith(":edge:3")


def test_fusion_api_adapter_rejects_fillet_for_missing_body() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    try:
        adapter.apply_fillet("missing-body", 0.2)
    except ValueError as exc:
        assert "body" in str(exc)
    else:
        raise AssertionError("Expected missing body to fail.")


def test_fusion_api_adapter_rejects_fillet_when_no_interior_bracket_edge_exists() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Rectangle Workflow")
    sketch = adapter.create_sketch("xy", "Rectangle Sketch")
    adapter.draw_rectangle(sketch["token"], 4.0, 2.0)
    body = adapter.extrude_profile(adapter.list_profiles(sketch["token"])[0]["token"], 0.75, "Rectangle")

    try:
        adapter.apply_fillet(body["token"], 0.2)
    except RuntimeError as exc:
        assert "interior bracket edges" in str(exc)
    else:
        raise AssertionError("Expected rectangle fillet selection to fail.")


def test_fusion_api_adapter_falls_back_to_sketch_local_profile_dimensions_for_xz() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Local Profile Box Workflow")
    sketch = adapter.create_sketch("xz", "Local Profile Sketch")
    adapter.draw_rectangle(sketch["token"], 2.0, 1.0)

    stored_sketch = app.activeProduct.findEntityByToken(sketch["token"])[0]
    profile = stored_sketch.profiles.item(0)
    profile.boundingBox = FakeBoundingBox(FakePoint(0, 0, 0), FakePoint(2.0, 1.0, 0.0))

    profiles = adapter.list_profiles(sketch["token"])

    assert profiles[0]["width_cm"] == 2.0
    assert profiles[0]["height_cm"] == 1.0


def test_fusion_api_adapter_falls_back_to_recorded_rectangle_dimensions_for_collapsed_non_xy_profile() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Recorded Rectangle Fallback Workflow")
    sketch = adapter.create_sketch("xz", "Recorded Rectangle Sketch")
    adapter.draw_rectangle(sketch["token"], 2.0, 1.0)

    stored_sketch = app.activeProduct.findEntityByToken(sketch["token"])[0]
    profile = stored_sketch.profiles.item(0)
    profile.boundingBox = FakeBoundingBox(FakePoint(0, 0, 0), FakePoint(2.0, 0.0, 0.0))

    profiles = adapter.list_profiles(sketch["token"])

    assert profiles[0]["width_cm"] == 2.0
    assert profiles[0]["height_cm"] == 1.0


def test_fusion_api_adapter_new_design_does_not_rename_root_component() -> None:
    app = FakeApp()
    app.activeProduct = FakeDesign(reject_root_name_changes=True)
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Spacer Workflow")

    assert app.activeDocument.name == "Spacer Workflow"


def test_fusion_api_adapter_resolves_expected_entity_from_mixed_token_matches() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)
    sketch = adapter.create_sketch("xy", "Sketch")
    real_find = app.activeProduct.findEntityByToken

    def mixed_find(token: str) -> list[object]:
        entities = real_find(token)
        if token == sketch["token"]:
            return [FakeVector(), *entities]
        return entities

    app.activeProduct.findEntityByToken = mixed_find  # type: ignore[method-assign]

    rectangle = adapter.draw_rectangle(sketch["token"], 2.0, 1.0)

    assert rectangle["rectangle_index"] == 0


def test_fusion_api_adapter_uses_cached_sketch_when_token_lookup_misses() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)
    sketch = adapter.create_sketch("xy", "Sketch")

    app.activeProduct.findEntityByToken = lambda token: []  # type: ignore[method-assign]

    rectangle = adapter.draw_rectangle(sketch["token"], 2.0, 1.0)

    assert rectangle["rectangle_index"] == 0


def test_fusion_api_adapter_rejects_calls_off_main_thread() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)
    adapter.main_thread_id = -1

    try:
        adapter.create_sketch("xy", "Sketch")
    except RuntimeError as exc:
        assert "main thread" in str(exc)
    else:
        raise AssertionError("Expected off-main-thread call to fail.")


def test_fusion_api_adapter_rejects_unknown_plane() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    try:
        adapter.create_sketch("front", "Bad Sketch")
    except ValueError as exc:
        assert "Unsupported sketch plane" in str(exc)
    else:
        raise AssertionError("Expected unsupported plane to fail.")


def test_fusion_api_adapter_rejects_non_positive_rectangle_dimensions() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)
    sketch = adapter.create_sketch("xy", "Sketch")

    try:
        adapter.draw_rectangle(sketch["token"], 0, 1.0)
    except ValueError as exc:
        assert "width_cm" in str(exc)
    else:
        raise AssertionError("Expected non-positive width to fail.")


def test_fusion_api_adapter_rejects_invalid_slot_dimensions() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)
    sketch = adapter.create_sketch("xy", "Sketch")

    try:
        adapter.draw_slot(sketch["token"], 2.0, 1.0, 0.5, 0.5)
    except ValueError as exc:
        assert "length_cm" in str(exc)
    else:
        raise AssertionError("Expected invalid slot dimensions to fail.")


def test_fusion_api_adapter_rejects_missing_profile_and_export_extension() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    try:
        adapter.extrude_profile("missing-profile", 0.5, "Spacer")
    except ValueError as exc:
        assert "profile" in str(exc)
    else:
        raise AssertionError("Expected missing profile to fail.")

    body = FakeBody(token="body-999", name="Spacer", width_cm=2.0, height_cm=1.0, thickness_cm=0.5)
    app.activeProduct.register(body)

    try:
        adapter.export_stl(body.entityToken, str(Path.cwd() / "manual_test_output" / "no_extension"))
    except ValueError as exc:
        assert "file extension" in str(exc)
    else:
        raise AssertionError("Expected missing export extension to fail.")


def test_fusion_api_adapter_rejects_export_outside_allowlist() -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)
    body = FakeBody(token="body-1000", name="Spacer", width_cm=2.0, height_cm=1.0, thickness_cm=0.5)
    app.activeProduct.register(body)

    try:
        adapter.export_stl(body.entityToken, str(Path.cwd().parent / "outside.stl"))
    except ValueError as exc:
        assert "allowlisted" in str(exc)
    else:
        raise AssertionError("Expected export outside allowlist to fail.")
