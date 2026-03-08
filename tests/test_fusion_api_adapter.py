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
    def __init__(self, token: str, width_cm: float, height_cm: float, parent_sketch: "FakeSketch") -> None:
        self.entityToken = token
        self.parentSketch = parent_sketch
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

    def addTwoPointRectangle(self, start: FakePoint, corner: FakePoint) -> None:  # noqa: N802
        width_cm = corner.x - start.x
        height_cm = corner.y - start.y
        profile = FakeProfile(
            token=f"{self._sketch.entityToken}:profile:{self._sketch.profiles.count}",
            width_cm=width_cm,
            height_cm=height_cm,
            parent_sketch=self._sketch,
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
        self.sketchCurves = SimpleNamespace(sketchLines=FakeSketchLines(self))


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
    def __init__(self, token: str, name: str, width_cm: float, height_cm: float, thickness_cm: float) -> None:
        self.entityToken = token
        self.name = name
        self.boundingBox = FakeBoundingBox(FakePoint(0, 0, 0), FakePoint(width_cm, height_cm, thickness_cm))


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
        body = FakeBody(token=token, name="Body", width_cm=width_cm, height_cm=height_cm, thickness_cm=thickness_cm)
        body.boundingBox = FakeBoundingBox(FakePoint(0, 0, 0), max_point)
        self._design.rootComponent.bRepBodies.append(body)
        self._design.register(body)
        return SimpleNamespace(bodies=FakeCollection([body]))


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
        self.features = SimpleNamespace(extrudeFeatures=FakeExtrudeFeatures(design))

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


class FakeApp:
    def __init__(self) -> None:
        self.activeDocument = SimpleNamespace(name="Current")
        self.activeProduct = FakeDesign()
        self.documents = FakeDocuments(self)


class TestFusionApiAdapter(FusionApiAdapter):
    def _load_adsk(self) -> tuple[object, object]:
        core = SimpleNamespace(
            DocumentTypes=SimpleNamespace(FusionDesignDocumentType="fusion"),
            Point3D=SimpleNamespace(create=lambda x, y, z: FakePoint(x, y, z)),
            ValueInput=SimpleNamespace(createByReal=lambda value: SimpleNamespace(value=value)),
        )
        fusion = SimpleNamespace(
            Design=SimpleNamespace(cast=lambda product: product),
            FeatureOperations=SimpleNamespace(NewBodyFeatureOperation="new_body"),
        )
        return core, fusion


def test_fusion_api_adapter_runs_spacer_sequence(tmp_path) -> None:
    app = FakeApp()
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Spacer Workflow")
    sketch = adapter.create_sketch("xy", "Spacer Sketch")
    rectangle = adapter.draw_rectangle(sketch["token"], 2.0, 1.0)
    profiles = adapter.list_profiles(sketch["token"])
    body = adapter.extrude_profile(profiles[0]["token"], 0.5, "Spacer")
    scene = adapter.get_scene_info()
    exported = adapter.export_stl(body["token"], str(tmp_path / "spacer.stl"))

    assert rectangle["rectangle_index"] == 0
    assert profiles[0]["width_cm"] == 2.0
    assert body["thickness_cm"] == 0.5
    assert scene["design_name"] == "Spacer Workflow"
    assert scene["sketches"][0]["plane"] == "xy"
    assert scene["bodies"][0]["name"] == "Spacer"
    assert scene["exports"] == []
    assert exported["output_path"].endswith("spacer.stl")
    assert Path(exported["output_path"]).exists()
    assert adapter.get_scene_info()["exports"] == [exported["output_path"]]


def test_fusion_api_adapter_normalizes_real_plane_names_and_reports_xz_dimensions(tmp_path) -> None:
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


def test_fusion_api_adapter_new_design_does_not_rename_root_component() -> None:
    app = FakeApp()
    app.activeProduct = FakeDesign(reject_root_name_changes=True)
    adapter = TestFusionApiAdapter(app=app, ui=object(), design=app.activeProduct)

    adapter.new_design("Spacer Workflow")

    assert app.activeDocument.name == "Spacer Workflow"


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


def test_fusion_api_adapter_rejects_missing_profile_and_export_extension(tmp_path) -> None:
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
        adapter.export_stl(body.entityToken, str(tmp_path / "no_extension"))
    except ValueError as exc:
        assert "file extension" in str(exc)
    else:
        raise AssertionError("Expected missing export extension to fail.")
