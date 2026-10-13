"""Translate the narrow neutral plate operations through existing gated primitives.

No Fusion API imports, bridge/thread/auth changes, or changes to public MCP routing.
"""
from pathlib import Path

from cad_backends.protocol import Capabilities, Editability, Measurements, Part
from mcp_server.errors import WorkflowFailure
from mcp_server.operations import Operation, OperationMode
from mcp_server.schemas import VerificationSnapshot


class FusionPlateBackend:
    def __init__(self, server, *, evidence: str = "live_fusion_unqualified"):
        self.server = server
        self.capabilities = Capabilities(
            "fusion", evidence, frozenset({"new_body", "cut"}),
            frozenset({"body_count", "width_mm", "height_mm", "thickness_mm", "volume_mm3"}),
            frozenset({"stl"}), Editability.RECIPE,
        )

    def start_part(self, directory: Path, parameters: dict) -> Part:
        self.server.new_design("ParamAItric Utility Plate")
        scene = self.server.get_scene_info()["result"]
        if VerificationSnapshot.from_scene(scene).body_count != 0:
            raise WorkflowFailure("Design was not reset.", stage="start_part", classification="state_drift")
        return Part(directory)

    def apply(self, part: Part, operation: Operation) -> None:
        self.capabilities.require(operations=(operation.mode.value,))
        place, target = operation.placement, operation.target
        if place.plane != "xy" or place.offset_cm != 0:
            raise WorkflowFailure("Only XY plate placement is supported.", stage="placement", classification="unsupported_capability")
        if (operation.mode is OperationMode.NEW_BODY and target.profile != "rectangle") or (
            operation.mode is OperationMode.CUT and target.profile != "circle"
        ):
            raise WorkflowFailure("Only a rectangle followed by a circular cut is supported.", stage="operation", classification="unsupported_capability")
        sketch = self.server.create_sketch("xy", f"Utility stage {part.revision}")["result"]["sketch"]["token"]
        if operation.mode is OperationMode.NEW_BODY:
            self.server.draw_rectangle(target.dimensions_cm["width"], target.dimensions_cm["height"], sketch_token=sketch)
        else:
            self.server.draw_circle(center_x_cm=place.x_cm, center_y_cm=place.y_cm,
                                    radius_cm=target.dimensions_cm["radius"], sketch_token=sketch)
        profiles = self.server.list_profiles(sketch)["result"]["profiles"]
        if len(profiles) != 1:
            raise WorkflowFailure("Expected one plate stage profile.", stage="profiles", classification="verification_failed")
        kwargs = {}
        if operation.mode is OperationMode.CUT:
            kwargs = {"operation": "cut", "target_body_token": part.state["body"]}
        result = self.server.extrude_profile(profiles[0]["token"], target.extent_cm, "Utility Plate", **kwargs)
        part.state["body"] = result["result"]["body"]["token"]
        part.revision += 1

    def inspect(self, part: Part) -> Measurements:
        scene = self.server.get_scene_info()["result"]
        body = self.server.get_body_info({"body_token": part.state["body"]})["result"]
        body = body.get("body_info", body)
        facts = {"body_count": VerificationSnapshot.from_scene(scene).body_count,
                 "width_mm": body["width_cm"] * 10, "height_mm": body["height_cm"] * 10,
                 "thickness_mm": body["thickness_cm"] * 10,
                 "volume_mm3": None if body.get("volume_cm3") is None else body["volume_cm3"] * 1000,
                 "face_count": body.get("face_count"), "edge_count": body.get("edge_count")}
        return Measurements(facts, f"{self.capabilities.evidence}:bridge_readback", "Fusion default accuracy; mock values are synthetic")

    def export(self, part: Part, formats: tuple[str, ...]) -> dict[str, Path]:
        self.capabilities.require(exports=formats)
        artifacts = {}
        for fmt in formats:
            result = self.server.export_stl(part.state["body"], str(part.directory / "plate.stl"))["result"]
            artifacts[fmt] = Path(result["output_path"])
        part.artifacts.update(artifacts)
        return artifacts
