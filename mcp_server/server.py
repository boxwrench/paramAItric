from __future__ import annotations

from mcp_server.bridge_client import BridgeClient
from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CommandEnvelope,
    CreateBracketInput,
    CreateMountingBracketInput,
    CreateSpacerInput,
    CreateTwoHoleMountingBracketInput,
    VerificationSnapshot,
)
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

    def draw_l_bracket_profile(
        self,
        width_cm: float,
        height_cm: float,
        leg_thickness_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        arguments = {
            "width_cm": width_cm,
            "height_cm": height_cm,
            "leg_thickness_cm": leg_thickness_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_l_bracket_profile", arguments)

    def draw_circle(
        self,
        center_x_cm: float,
        center_y_cm: float,
        radius_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        arguments = {
            "center_x_cm": center_x_cm,
            "center_y_cm": center_y_cm,
            "radius_cm": radius_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_circle", arguments)

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
        return self._create_l_bracket_workflow(
            workflow_name="bracket",
            workflow_call_name="create_bracket",
            design_name="Bracket Workflow",
            sketch_plane=spec.plane,
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            width_cm=spec.width_cm,
            height_cm=spec.height_cm,
            leg_thickness_cm=spec.leg_thickness_cm,
            thickness_cm=spec.thickness_cm,
            output_path=spec.output_path,
        )

    def create_mounting_bracket(self, payload: dict) -> dict:
        spec = CreateMountingBracketInput.from_payload(payload)
        return self._create_mounting_bracket_workflow(spec)

    def create_two_hole_mounting_bracket(self, payload: dict) -> dict:
        spec = CreateTwoHoleMountingBracketInput.from_payload(payload)
        return self._create_mounting_bracket_workflow(
            spec=spec,
            workflow_name="two_hole_mounting_bracket",
            workflow_call_name="create_two_hole_mounting_bracket",
            design_name="Two-Hole Mounting Bracket Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            hole_centers=(
                (spec.first_hole_center_x_cm, spec.first_hole_center_y_cm),
                (spec.second_hole_center_x_cm, spec.second_hole_center_y_cm),
            ),
        )

    def _send(self, command: str, arguments: dict) -> dict:
        envelope = CommandEnvelope.build(command, arguments)
        return self.bridge_client.send(envelope)

    def _bridge_step(
        self,
        *,
        stage: str,
        stages: list[dict],
        action,
        partial_result: dict | None = None,
        next_step: str | None = None,
    ):
        try:
            return action()
        except WorkflowFailure:
            raise
        except RuntimeError as exc:
            payload = {"stages": list(stages)}
            if partial_result:
                payload.update(partial_result)
            raise WorkflowFailure(
                f"Workflow bridge call failed during {stage}: {exc}",
                stage=stage,
                classification="bridge_error",
                partial_result=payload,
                next_step=next_step or "Inspect bridge health and the last successful stage before retrying.",
            ) from exc

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

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design(design_name))
        stages.append({"stage": "new_design", "status": "completed"})

        initial_scene = self._bridge_step(
            stage="verify_clean_state",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
        )
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

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=sketch_plane, name=sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": sketch_token,
                "plane": sketch_plane,
            }
        )

        self._bridge_step(
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=width_cm, height_cm=height_cm, sketch_token=sketch_token),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                f"{workflow_label} workflow expected exactly one profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the sketch and remove ambiguity before extrusion.",
            )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=profiles[0]["token"],
                distance_cm=thickness_cm,
                body_name=body_name,
            )["result"]["body"],
            partial_result={"profile_token": profiles[0]["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
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

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], output_path)["result"],
            partial_result={"body": body},
        )
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

    def _create_l_bracket_workflow(
        self,
        workflow_name: str,
        workflow_call_name: str,
        design_name: str,
        sketch_plane: str,
        sketch_name: str,
        body_name: str,
        width_cm: float,
        height_cm: float,
        leg_thickness_cm: float,
        thickness_cm: float,
        output_path: str,
    ) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get(workflow_name)
        workflow_label = workflow_name.capitalize()

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design(design_name))
        stages.append({"stage": "new_design", "status": "completed"})

        initial_scene = self._bridge_step(
            stage="verify_clean_state",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
        )
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

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=sketch_plane, name=sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": sketch_token,
                "plane": sketch_plane,
            }
        )

        self._bridge_step(
            stage="draw_l_bracket_profile",
            stages=stages,
            action=lambda: self.draw_l_bracket_profile(
                width_cm=width_cm,
                height_cm=height_cm,
                leg_thickness_cm=leg_thickness_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append(
            {
                "stage": "draw_l_bracket_profile",
                "status": "completed",
                "leg_thickness_cm": leg_thickness_cm,
            }
        )

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                f"{workflow_label} workflow expected exactly one profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the sketch and remove ambiguity before extrusion.",
            )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=profiles[0]["token"],
                distance_cm=thickness_cm,
                body_name=body_name,
            )["result"]["body"],
            partial_result={"profile_token": profiles[0]["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
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

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], output_path)["result"],
            partial_result={"body": body},
        )
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
                "leg_thickness_cm": leg_thickness_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_mounting_bracket_workflow(
        self,
        spec: CreateMountingBracketInput | CreateTwoHoleMountingBracketInput,
        workflow_name: str = "mounting_bracket",
        workflow_call_name: str = "create_mounting_bracket",
        design_name: str = "Mounting Bracket Workflow",
        sketch_name: str | None = None,
        body_name: str | None = None,
        hole_centers: tuple[tuple[float, float], ...] | None = None,
    ) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get(workflow_name)
        if sketch_name is None:
            sketch_name = spec.sketch_name
        if body_name is None:
            body_name = spec.body_name
        if hole_centers is None:
            hole_centers = ((spec.hole_center_x_cm, spec.hole_center_y_cm),)

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design(design_name))
        stages.append({"stage": "new_design", "status": "completed"})

        initial_scene = self._bridge_step(
            stage="verify_clean_state",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
        )
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

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": sketch_token,
                "plane": spec.plane,
            }
        )

        self._bridge_step(
            stage="draw_l_bracket_profile",
            stages=stages,
            action=lambda: self.draw_l_bracket_profile(
                width_cm=spec.width_cm,
                height_cm=spec.height_cm,
                leg_thickness_cm=spec.leg_thickness_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_l_bracket_profile", "status": "completed"})

        for hole_index, (center_x_cm, center_y_cm) in enumerate(hole_centers, start=1):
            self._bridge_step(
                stage="draw_circle",
                stages=stages,
                action=lambda center_x_cm=center_x_cm, center_y_cm=center_y_cm: self.draw_circle(
                    center_x_cm=center_x_cm,
                    center_y_cm=center_y_cm,
                    radius_cm=spec.hole_diameter_cm / 2.0,
                    sketch_token=sketch_token,
                ),
                partial_result={"sketch_token": sketch_token, "hole_index": hole_index},
            )
            stages.append(
                {
                    "stage": "draw_circle",
                    "status": "completed",
                    "hole_index": hole_index,
                    "hole_diameter_cm": spec.hole_diameter_cm,
                }
            )

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=spec.width_cm,
            expected_height_cm=spec.height_cm,
            workflow_label="Mounting bracket",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name=body_name,
            )["result"]["body"],
            partial_result={"profile_token": selected_profile["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
        snapshot = VerificationSnapshot.from_scene(scene)
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
        if snapshot.body_count != 1 or actual_dimensions != expected_dimensions:
            raise WorkflowFailure(
                "Mounting bracket workflow verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect profile selection and hole placement before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": snapshot.__dict__,
                "dimensions": actual_dimensions,
            }
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], spec.output_path)["result"],
            partial_result={"body": body},
        )
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
                "expected_width_cm": spec.width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": body["width_cm"],
                "actual_height_cm": body["height_cm"],
                "actual_thickness_cm": body["thickness_cm"],
                "sketch_plane": spec.plane,
                "leg_thickness_cm": spec.leg_thickness_cm,
                "hole_diameter_cm": spec.hole_diameter_cm,
                "hole_count": len(hole_centers),
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _select_profile_by_dimensions(
        self,
        profiles: list[dict],
        expected_width_cm: float,
        expected_height_cm: float,
        workflow_label: str,
        stages: list[dict],
    ) -> dict:
        matches = [
            profile
            for profile in profiles
            if self._close(profile.get("width_cm"), expected_width_cm)
            and self._close(profile.get("height_cm"), expected_height_cm)
        ]
        if len(matches) != 1:
            raise WorkflowFailure(
                f"{workflow_label} workflow could not determine the intended outer profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected_width_cm": expected_width_cm,
                    "expected_height_cm": expected_height_cm,
                    "stages": stages,
                },
                next_step="Inspect the sketch profile set before extrusion.",
        )
        return matches[0]

    def _close(self, actual: object, expected: float, tolerance: float = 1e-9) -> bool:
        try:
            number = float(actual)
        except (TypeError, ValueError):
            return False
        return abs(number - expected) <= tolerance
