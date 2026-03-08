from __future__ import annotations

from mcp_server.bridge_client import BridgeClient
from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import CommandEnvelope, CreateSpacerInput, VerificationSnapshot
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
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("spacer")

        self.new_design("Spacer Workflow")
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

        sketch = self.create_sketch(plane="xy", name=spec.sketch_name)
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token})

        self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.height_cm, sketch_token=sketch_token)
        stages.append({"stage": "draw_rectangle", "status": "completed"})

        profiles = self.list_profiles(sketch_token)["result"]["profiles"]
        if len(profiles) != 1:
            raise WorkflowFailure(
                "Spacer workflow expected exactly one profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the sketch and remove ambiguity before extrusion.",
            )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self.extrude_profile(
            profile_token=profiles[0]["token"],
            distance_cm=spec.thickness_cm,
            body_name=spec.body_name,
        )["result"]["body"]
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        scene = self.get_scene_info()["result"]
        snapshot = VerificationSnapshot.from_scene(scene)
        if snapshot.body_count != 1:
            raise WorkflowFailure(
                "Spacer workflow verification failed: expected exactly one body.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene, "stages": stages},
                next_step="Preserve the partial model and inspect body creation before retrying.",
            )
        expected_dimensions = {
            "width_cm": spec.width_cm,
            "height_cm": spec.height_cm,
            "thickness_cm": spec.thickness_cm,
        }
        actual_dimensions = {
            "width_cm": body["width_cm"],
            "height_cm": body["height_cm"],
            "thickness_cm": body["thickness_cm"],
        }
        if actual_dimensions != expected_dimensions:
            raise WorkflowFailure(
                "Spacer workflow verification failed: body dimensions do not match the requested values.",
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

        exported = self.export_stl(body["token"], spec.output_path)["result"]
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_spacer",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "verification": {
                "body_count": snapshot.body_count,
                "sketch_count": snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": body["width_cm"],
                "actual_height_cm": body["height_cm"],
                "actual_thickness_cm": body["thickness_cm"],
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _send(self, command: str, arguments: dict) -> dict:
        envelope = CommandEnvelope.build(command, arguments)
        return self.bridge_client.send(envelope)
