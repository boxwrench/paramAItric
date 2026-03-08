from __future__ import annotations

from mcp_server.bridge_client import BridgeClient
from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import CommandEnvelope, CreateBracketInput, CreateSpacerInput, VerificationSnapshot
from mcp_server.workflows import WorkflowRegistry, build_default_registry


class ParamAIToolServer:
    def __init__(
        self,
        bridge_client: BridgeClient | None = None,
        workflow_registry: WorkflowRegistry | None = None,
    ) -> None:
        self.bridge_client = bridge_client or BridgeClient()
        self.workflow_registry = workflow_registry or build_default_registry()

    def health(self) -> dict:
        return self.bridge_client.health()

    def get_workflow_catalog(self) -> list[dict]:
        return self.bridge_client.workflow_catalog()

    def new_design(self, name: str = "ParamAItric Design") -> dict:
        return self._send("new_design", {"name": name})

    def create_sketch(self, plane: str, name: str) -> dict:
        return self._send("create_sketch", {"plane": plane, "name": name})

    def draw_rectangle(self, width_cm: float, height_cm: float, sketch_token: str | None = None) -> dict:
        arguments = {"width_cm": width_cm, "height_cm": height_cm}
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_rectangle", arguments)

    def list_profiles(self, sketch_token: str) -> dict:
        return self._send("list_profiles", {"sketch_token": sketch_token})

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str) -> dict:
        return self._send(
            "extrude_profile",
            {"profile_token": profile_token, "distance_cm": distance_cm, "body_name": body_name},
        )

    def get_scene_info(self) -> dict:
        return self._send("get_scene_info", {})

    def export_stl(self, body_token: str, output_path: str) -> dict:
        return self._send("export_stl", {"body_token": body_token, "output_path": output_path})

    def create_spacer(self, payload: dict) -> dict:
        spec = CreateSpacerInput.from_payload(payload)
        return self._create_rectangular_prism_workflow(
            workflow_name="spacer",
            workflow_call_name="create_spacer",
            design_name="Spacer Workflow",
            sketch_plane="xy",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            width_cm=spec.width_cm,
            height_cm=spec.height_cm,
            thickness_cm=spec.thickness_cm,
            output_path=spec.output_path,
        )

    def create_bracket(self, payload: dict) -> dict:
        spec = CreateBracketInput.from_payload(payload)
        return self._create_rectangular_prism_workflow(
            workflow_name="bracket",
            workflow_call_name="create_bracket",
            design_name="Bracket Workflow",
            sketch_plane=spec.plane,
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            width_cm=spec.width_cm,
            height_cm=spec.height_cm,
            thickness_cm=spec.thickness_cm,
            output_path=spec.output_path,
        )

    def _send(self, command: str, arguments: dict) -> dict:
        envelope = CommandEnvelope.build(command, arguments)
        return self.bridge_client.send(envelope)

    def _create_rectangular_prism_workflow(
        self,
        workflow_name: str,
        workflow_call_name: str,
        design_name: str,
        sketch_plane: str,
        sketch_name: str,
        body_name: str,
        width_cm: float,
        height_cm: float,
        thickness_cm: float,
        output_path: str,
    ) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get(workflow_name)
        workflow_label = workflow_name.capitalize()

        self.new_design(design_name)
        stages.append({"stage": "new_design", "status": "completed"})

        initial_scene = self.get_scene_info()["result"]
        initial_snapshot = VerificationSnapshot.from_scene(initial_scene)
        if initial_snapshot.body_count != 0 or initial_snapshot.export_count != 0:
            raise WorkflowFailure(
                "Workflow did not start from a clean design state.",
                stage="verify_clean_state",
                classification="state_drift",
                partial_result={"scene": initial_scene, "stages": stages},
                next_step="Inspect the design reset path before attempting another workflow.",
            )
        stages.append(
            {
                "stage": "verify_clean_state",
                "status": "completed",
                "snapshot": initial_snapshot.__dict__,
            }
        )

        sketch = self.create_sketch(plane=sketch_plane, name=sketch_name)
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": sketch_token,
                "plane": sketch_plane,
            }
        )

        self.draw_rectangle(width_cm=width_cm, height_cm=height_cm, sketch_token=sketch_token)
        stages.append({"stage": "draw_rectangle", "status": "completed"})

        profiles = self.list_profiles(sketch_token)["result"]["profiles"]
        if len(profiles) != 1:
            raise WorkflowFailure(
                f"{workflow_label} workflow expected exactly one profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the sketch and remove ambiguity before extrusion.",
            )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self.extrude_profile(
            profile_token=profiles[0]["token"],
            distance_cm=thickness_cm,
            body_name=body_name,
        )["result"]["body"]
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        scene = self.get_scene_info()["result"]
        snapshot = VerificationSnapshot.from_scene(scene)
        if snapshot.body_count != 1:
            raise WorkflowFailure(
                f"{workflow_label} workflow verification failed: expected exactly one body.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene, "stages": stages},
                next_step="Preserve the partial model and inspect body creation before retrying.",
            )
        expected_dimensions = {
            "width_cm": width_cm,
            "height_cm": height_cm,
            "thickness_cm": thickness_cm,
        }
        actual_dimensions = {
            "width_cm": body["width_cm"],
            "height_cm": body["height_cm"],
            "thickness_cm": body["thickness_cm"],
        }
        if actual_dimensions != expected_dimensions:
            raise WorkflowFailure(
                f"{workflow_label} workflow verification failed: body dimensions do not match the requested values.",
                stage="verify_dimensions",
                classification="verification_failed",
                partial_result={"body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect the profile selection and extrusion distance before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": snapshot.__dict__,
                "dimensions": actual_dimensions,
            }
        )

        exported = self.export_stl(body["token"], output_path)["result"]
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": workflow_call_name,
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "verification": {
                "body_count": snapshot.body_count,
                "sketch_count": snapshot.sketch_count,
                "expected_width_cm": width_cm,
                "expected_height_cm": height_cm,
                "expected_thickness_cm": thickness_cm,
                "actual_width_cm": body["width_cm"],
                "actual_height_cm": body["height_cm"],
                "actual_thickness_cm": body["thickness_cm"],
                "sketch_plane": sketch_plane,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }
