from __future__ import annotations

from mcp_server.bridge_client import BridgeCancelledError, BridgeClient, BridgeTimeoutError
from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CommandEnvelope,
    CreateBoxWithLidInput,
    CreateBracketInput,
    CreateCableGlandPlateInput,
    CreateLBracketWithGussetInput,
    CreateTriangularBracketInput,
    CreateChamferedBracketInput,
    CreateFlangedBushingInput,
    CreatePipeClampHalfInput,
    CreateCylinderInput,
    CreateRevolveInput,
    CreateFilletedBracketInput,
    CreateCounterboredPlateInput,
    CreateFourHoleMountingPlateInput,
    CreateSlottedMountingPlateInput,
    CreateLidForBoxInput,
    CreateMountingBracketInput,
    CreateOpenBoxBodyInput,
    CreatePlateWithHoleInput,
    CreateProjectBoxWithStandoffsInput,
    CreateShaftCouplerInput,
    CreateRecessedMountInput,
    CreateSimpleEnclosureInput,
    CreateSlottedMountInput,
    CreateSpacerInput,
    CreateTHandleWithSquareSocketInput,
    CreateTaperedKnobBlankInput,
    CreateTubeInput,
    CreateTubeMountingPlateInput,
    CreateTwoHolePlateInput,
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

    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:
        arguments = {"plane": plane, "name": name}
        if offset_cm is not None:
            arguments["offset_cm"] = offset_cm
        return self._send("create_sketch", arguments)

    def draw_rectangle(self, width_cm: float, height_cm: float, sketch_token: str | None = None) -> dict:
        arguments = {"width_cm": width_cm, "height_cm": height_cm}
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_rectangle", arguments)

    def draw_rectangle_at(
        self,
        origin_x_cm: float,
        origin_y_cm: float,
        width_cm: float,
        height_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        arguments = {
            "origin_x_cm": origin_x_cm,
            "origin_y_cm": origin_y_cm,
            "width_cm": width_cm,
            "height_cm": height_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_rectangle_at", arguments)

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

    def draw_revolve_profile(
        self,
        base_diameter_cm: float,
        top_diameter_cm: float,
        height_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        arguments = {
            "base_diameter_cm": base_diameter_cm,
            "top_diameter_cm": top_diameter_cm,
            "height_cm": height_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_revolve_profile", arguments)

    def draw_slot(
        self,
        center_x_cm: float,
        center_y_cm: float,
        length_cm: float,
        width_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        arguments = {
            "center_x_cm": center_x_cm,
            "center_y_cm": center_y_cm,
            "length_cm": length_cm,
            "width_cm": width_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_slot", arguments)

    def draw_triangle(
        self,
        x1_cm: float,
        y1_cm: float,
        x2_cm: float,
        y2_cm: float,
        x3_cm: float,
        y3_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        arguments = {
            "x1_cm": x1_cm,
            "y1_cm": y1_cm,
            "x2_cm": x2_cm,
            "y2_cm": y2_cm,
            "x3_cm": x3_cm,
            "y3_cm": y3_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_triangle", arguments)

    def list_profiles(self, sketch_token: str) -> dict:
        return self._send("list_profiles", {"sketch_token": sketch_token})

    def extrude_profile(
        self,
        profile_token: str,
        distance_cm: float,
        body_name: str,
        operation: str = "new_body",
        target_body_token: str | None = None,
    ) -> dict:
        arguments = {
            "profile_token": profile_token,
            "distance_cm": distance_cm,
            "body_name": body_name,
            "operation": operation,
        }
        if target_body_token:
            arguments["target_body_token"] = target_body_token
        return self._send("extrude_profile", arguments)

    def revolve_profile(
        self,
        profile_token: str,
        body_name: str,
        axis: str = "y",
        angle_deg: float = 360.0,
    ) -> dict:
        return self._send(
            "revolve_profile",
            {
                "profile_token": profile_token,
                "body_name": body_name,
                "axis": axis,
                "angle_deg": angle_deg,
            },
        )

    def get_scene_info(self) -> dict:
        return self._send("get_scene_info", {})

    def list_design_bodies(self, payload: dict | None = None) -> dict:
        return self._send("list_design_bodies", {})

    def get_body_info(self, payload: dict) -> dict:
        body_token = payload.get("body_token")
        if not body_token or not isinstance(body_token, str):
            raise ValueError("body_token must be a non-empty string.")
        return self._send("get_body_info", {"body_token": body_token})

    def get_body_faces(self, payload: dict) -> dict:
        body_token = payload.get("body_token")
        if not body_token or not isinstance(body_token, str):
            raise ValueError("body_token must be a non-empty string.")
        return self._send("get_body_faces", {"body_token": body_token})

    def get_body_edges(self, payload: dict) -> dict:
        body_token = payload.get("body_token")
        if not body_token or not isinstance(body_token, str):
            raise ValueError("body_token must be a non-empty string.")
        return self._send("get_body_edges", {"body_token": body_token})

    def export_stl(self, body_token: str, output_path: str) -> dict:
        return self._send("export_stl", {"body_token": body_token, "output_path": output_path})

    def apply_fillet(self, body_token: str, radius_cm: float) -> dict:
        return self._send("apply_fillet", {"body_token": body_token, "radius_cm": radius_cm})

    def apply_chamfer(self, body_token: str, distance_cm: float, edge_selection: str | None = None) -> dict:
        arguments = {"body_token": body_token, "distance_cm": distance_cm}
        if edge_selection is not None:
            arguments["edge_selection"] = edge_selection
        return self._send("apply_chamfer", arguments)

    def apply_shell(self, body_token: str, wall_thickness_cm: float) -> dict:
        return self._send("apply_shell", {"body_token": body_token, "wall_thickness_cm": wall_thickness_cm})

    def combine_bodies(self, target_body_token: str, tool_body_token: str) -> dict:
        return self._send(
            "combine_bodies",
            {"target_body_token": target_body_token, "tool_body_token": tool_body_token},
        )

    def convert_bodies_to_components(self, payload: dict) -> dict:
        body_tokens = payload.get("body_tokens")
        if not isinstance(body_tokens, list) or not body_tokens:
            raise ValueError("body_tokens must be a non-empty list of strings.")
        if not all(isinstance(t, str) and t for t in body_tokens):
            raise ValueError("All body_tokens entries must be non-empty strings.")
        args: dict = {"body_tokens": body_tokens}
        component_names = payload.get("component_names")
        if component_names is not None:
            if not isinstance(component_names, list):
                raise ValueError("component_names must be a list.")
            args["component_names"] = component_names
        return self._send("convert_bodies_to_components", args)

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

    def create_cylinder(self, payload: dict) -> dict:
        spec = CreateCylinderInput.from_payload(payload)
        return self._create_cylinder_workflow(spec)

    def create_tube(self, payload: dict) -> dict:
        spec = CreateTubeInput.from_payload(payload)
        return self._create_tube_workflow(spec)

    def create_revolve(self, payload: dict) -> dict:
        spec = CreateRevolveInput.from_payload(payload)
        return self._create_revolve_workflow(spec)

    def create_tapered_knob_blank(self, payload: dict) -> dict:
        spec = CreateTaperedKnobBlankInput.from_payload(payload)
        return self._create_tapered_knob_blank_workflow(spec)

    def create_flanged_bushing(self, payload: dict) -> dict:
        spec = CreateFlangedBushingInput.from_payload(payload)
        return self._create_flanged_bushing_workflow(spec)

    def create_shaft_coupler(self, payload: dict) -> dict:
        spec = CreateShaftCouplerInput.from_payload(payload)
        return self._create_shaft_coupler_workflow(spec)

    def create_pipe_clamp_half(self, payload: dict) -> dict:
        spec = CreatePipeClampHalfInput.from_payload(payload)
        return self._create_pipe_clamp_half_workflow(spec)

    def create_tube_mounting_plate(self, payload: dict) -> dict:
        spec = CreateTubeMountingPlateInput.from_payload(payload)
        return self._create_tube_mounting_plate_workflow(spec)

    def create_t_handle_with_square_socket(self, payload: dict) -> dict:
        spec = CreateTHandleWithSquareSocketInput.from_payload(payload)
        return self._create_t_handle_with_square_socket_workflow(spec)

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

    def create_filleted_bracket(self, payload: dict) -> dict:
        spec = CreateFilletedBracketInput.from_payload(payload)
        return self._create_filleted_bracket_workflow(spec)

    def create_chamfered_bracket(self, payload: dict) -> dict:
        spec = CreateChamferedBracketInput.from_payload(payload)
        return self._create_chamfered_bracket_workflow(spec)

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

    def create_two_hole_plate(self, payload: dict) -> dict:
        spec = CreateTwoHolePlateInput.from_payload(payload)
        return self._create_two_hole_plate_workflow(spec)

    def create_slotted_mount(self, payload: dict) -> dict:
        spec = CreateSlottedMountInput.from_payload(payload)
        return self._create_slotted_mount_workflow(spec)

    def create_counterbored_plate(self, payload: dict) -> dict:
        spec = CreateCounterboredPlateInput.from_payload(payload)
        return self._create_counterbored_plate_workflow(spec)

    def create_four_hole_mounting_plate(self, payload: dict) -> dict:
        spec = CreateFourHoleMountingPlateInput.from_payload(payload)
        return self._create_four_hole_mounting_plate_workflow(spec)

    def create_slotted_mounting_plate(self, payload: dict) -> dict:
        spec = CreateSlottedMountingPlateInput.from_payload(payload)
        return self._create_slotted_mounting_plate_workflow(spec)

    def create_recessed_mount(self, payload: dict) -> dict:
        spec = CreateRecessedMountInput.from_payload(payload)
        return self._create_recessed_mount_workflow(spec)

    def create_simple_enclosure(self, payload: dict) -> dict:
        spec = CreateSimpleEnclosureInput.from_payload(payload)
        return self._create_simple_enclosure_workflow(spec)

    def create_open_box_body(self, payload: dict) -> dict:
        spec = CreateOpenBoxBodyInput.from_payload(payload)
        return self._create_open_box_body_workflow(spec)

    def create_lid_for_box(self, payload: dict) -> dict:
        spec = CreateLidForBoxInput.from_payload(payload)
        return self._create_lid_for_box_workflow(spec)

    def create_project_box_with_standoffs(self, payload: dict) -> dict:
        spec = CreateProjectBoxWithStandoffsInput.from_payload(payload)
        return self._create_project_box_with_standoffs_workflow(spec)

    def create_box_with_lid(self, payload: dict) -> dict:
        spec = CreateBoxWithLidInput.from_payload(payload)
        return self._create_box_with_lid_workflow(spec)

    def create_cable_gland_plate(self, payload: dict) -> dict:
        spec = CreateCableGlandPlateInput.from_payload(payload)
        return self._create_cable_gland_plate_workflow(spec)

    def create_triangular_bracket(self, payload: dict) -> dict:
        spec = CreateTriangularBracketInput.from_payload(payload)
        return self._create_triangular_bracket_workflow(spec)

    def create_l_bracket_with_gusset(self, payload: dict) -> dict:
        spec = CreateLBracketWithGussetInput.from_payload(payload)
        return self._create_l_bracket_with_gusset_workflow(spec)

    def create_plate_with_hole(self, payload: dict) -> dict:
        spec = CreatePlateWithHoleInput.from_payload(payload)
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("plate_with_hole")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Plate With Hole Workflow"))
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
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
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
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.height_cm, sketch_token=sketch_token),
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
                "Plate with hole workflow expected exactly one base profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the base plate sketch before extrusion.",
            )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=profiles[0]["token"],
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": profiles[0]["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"], "operation": "new_body"})

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
                "Plate with hole base-body verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect profile selection and base extrusion before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": snapshot.__dict__,
                "dimensions": actual_dimensions,
                "operation": "new_body",
            }
        )

        hole_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.hole_sketch_name),
        )
        hole_sketch_token = hole_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": hole_sketch_token,
                "plane": spec.plane,
                "sketch_role": "hole",
            }
        )

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=spec.hole_center_x_cm,
                center_y_cm=spec.hole_center_y_cm,
                radius_cm=spec.hole_diameter_cm / 2.0,
                sketch_token=hole_sketch_token,
            ),
            partial_result={"sketch_token": hole_sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "hole_diameter_cm": spec.hole_diameter_cm})

        hole_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(hole_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": hole_sketch_token},
        )
        selected_hole_profile = self._select_profile_by_dimensions(
            hole_profiles,
            expected_width_cm=spec.hole_diameter_cm,
            expected_height_cm=spec.hole_diameter_cm,
            workflow_label="Plate with hole",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(hole_profiles), "profile_role": "hole"})

        cut_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_hole_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name="hole",
                operation="cut",
                target_body_token=body["token"],
            )["result"]["body"],
            partial_result={"profile_token": selected_hole_profile["token"], "body": body},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": cut_body["token"], "operation": "cut"})

        post_cut_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": cut_body},
        )
        post_cut_snapshot = VerificationSnapshot.from_scene(post_cut_scene)
        post_cut_dimensions = {
            "width_cm": cut_body["width_cm"],
            "height_cm": cut_body["height_cm"],
            "thickness_cm": cut_body["thickness_cm"],
        }
        if post_cut_snapshot.body_count != 1 or post_cut_dimensions != expected_dimensions:
            raise WorkflowFailure(
                "Plate with hole cut verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": post_cut_scene, "body": cut_body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect the hole sketch and cut intersection before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": post_cut_snapshot.__dict__,
                "dimensions": post_cut_dimensions,
                "operation": "cut",
            }
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(cut_body["token"], spec.output_path)["result"],
            partial_result={"body": cut_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_plate_with_hole",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": cut_body,
            "verification": {
                "body_count": post_cut_snapshot.body_count,
                "sketch_count": post_cut_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": cut_body["width_cm"],
                "actual_height_cm": cut_body["height_cm"],
                "actual_thickness_cm": cut_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "hole_diameter_cm": spec.hole_diameter_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_counterbored_plate_workflow(self, spec: CreateCounterboredPlateInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("counterbored_plate")

        base_body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="counterbored_plate",
            design_name="Counterbored Plate Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.height_cm,
            thickness_cm=spec.thickness_cm,
        )

        through_hole_body, through_hole_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="counterbored_plate",
            sketch_name=spec.hole_sketch_name,
            circle_diameter_cm=spec.hole_diameter_cm,
            center_x_cm=spec.hole_center_x_cm,
            center_y_cm=spec.hole_center_y_cm,
            cut_depth_cm=spec.thickness_cm,
            body=base_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.height_cm,
                "thickness_cm": spec.thickness_cm,
            },
            profile_role="through_hole",
            operation_label="through_hole_cut",
        )

        counterbored_body, counterbore_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="counterbored_plate",
            sketch_name=spec.counterbore_sketch_name,
            circle_diameter_cm=spec.counterbore_diameter_cm,
            center_x_cm=spec.hole_center_x_cm,
            center_y_cm=spec.hole_center_y_cm,
            cut_depth_cm=spec.counterbore_depth_cm,
            body=through_hole_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.height_cm,
                "thickness_cm": spec.thickness_cm,
            },
            profile_role="counterbore",
            operation_label="counterbore_cut",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(counterbored_body["token"], spec.output_path)["result"],
            partial_result={"body": counterbored_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_counterbored_plate",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": counterbored_body,
            "verification": {
                "body_count": counterbore_snapshot.body_count,
                "sketch_count": counterbore_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": counterbored_body["width_cm"],
                "actual_height_cm": counterbored_body["height_cm"],
                "actual_thickness_cm": counterbored_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "hole_diameter_cm": spec.hole_diameter_cm,
                "counterbore_diameter_cm": spec.counterbore_diameter_cm,
                "counterbore_depth_cm": spec.counterbore_depth_cm,
                "hole_center_x_cm": spec.hole_center_x_cm,
                "hole_center_y_cm": spec.hole_center_y_cm,
                "base_body_count": base_snapshot.body_count,
                "post_hole_body_count": through_hole_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_recessed_mount_workflow(self, spec: CreateRecessedMountInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("recessed_mount")

        base_body, _ = self._create_base_plate_body(
            stages=stages,
            workflow_name="recessed_mount",
            design_name="Recessed Mount Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.height_cm,
            thickness_cm=spec.thickness_cm,
        )

        recessed_body, recess_snapshot = self._run_rectangle_cut_stage(
            stages=stages,
            workflow_name="recessed_mount",
            sketch_name=spec.recess_sketch_name,
            origin_x_cm=spec.recess_origin_x_cm,
            origin_y_cm=spec.recess_origin_y_cm,
            width_cm=spec.recess_width_cm,
            height_cm=spec.recess_height_cm,
            cut_depth_cm=spec.recess_depth_cm,
            body=base_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.height_cm,
                "thickness_cm": spec.thickness_cm,
            },
            profile_role="recess",
            operation_label="recess_cut",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(recessed_body["token"], spec.output_path)["result"],
            partial_result={"body": recessed_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_recessed_mount",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": recessed_body,
            "verification": {
                "body_count": recess_snapshot.body_count,
                "sketch_count": recess_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": recessed_body["width_cm"],
                "actual_height_cm": recessed_body["height_cm"],
                "actual_thickness_cm": recessed_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "recess_width_cm": spec.recess_width_cm,
                "recess_height_cm": spec.recess_height_cm,
                "recess_depth_cm": spec.recess_depth_cm,
                "recess_origin_x_cm": spec.recess_origin_x_cm,
                "recess_origin_y_cm": spec.recess_origin_y_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_open_box_body_workflow(self, spec: CreateOpenBoxBodyInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("open_box_body")
        cavity_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        cavity_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        cavity_depth_cut_cm = spec.height_cm - spec.floor_thickness_cm

        base_body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="open_box_body",
            design_name="Open Box Body Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.depth_cm,
            thickness_cm=spec.height_cm,
        )

        open_box_body, cavity_snapshot = self._run_rectangle_cut_stage(
            stages=stages,
            workflow_name="open_box_body",
            sketch_name=spec.cavity_sketch_name,
            origin_x_cm=spec.wall_thickness_cm,
            origin_y_cm=spec.wall_thickness_cm,
            width_cm=cavity_width_cm,
            height_cm=cavity_depth_cm,
            cut_depth_cm=cavity_depth_cut_cm,
            body=base_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.depth_cm,
                "thickness_cm": spec.height_cm,
            },
            profile_role="cavity",
            operation_label="cavity_cut",
            sketch_offset_cm=spec.floor_thickness_cm,
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(open_box_body["token"], spec.output_path)["result"],
            partial_result={"body": open_box_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_open_box_body",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": open_box_body,
            "verification": {
                "body_count": cavity_snapshot.body_count,
                "sketch_count": cavity_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_depth_cm": spec.depth_cm,
                "expected_height_cm": spec.height_cm,
                "actual_width_cm": open_box_body["width_cm"],
                "actual_depth_cm": open_box_body["height_cm"],
                "actual_height_cm": open_box_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "wall_thickness_cm": spec.wall_thickness_cm,
                "floor_thickness_cm": spec.floor_thickness_cm,
                "cavity_width_cm": cavity_width_cm,
                "cavity_depth_cm": cavity_depth_cm,
                "base_body_count": base_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_simple_enclosure_workflow(self, spec: CreateSimpleEnclosureInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("simple_enclosure")
        inner_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        inner_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        inner_height_cm = spec.height_cm - spec.wall_thickness_cm

        body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="simple_enclosure",
            design_name="Simple Enclosure Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.depth_cm,
            thickness_cm=spec.height_cm,
        )

        shell = self._bridge_step(
            stage="apply_shell",
            stages=stages,
            action=lambda: self.apply_shell(
                body_token=body["token"],
                wall_thickness_cm=spec.wall_thickness_cm,
            )["result"]["shell"],
            partial_result={"body": body},
        )
        self._verify_shell_result(
            shell=shell,
            stages=stages,
            expected_body=body,
            expected_wall_thickness_cm=spec.wall_thickness_cm,
            expected_inner_width_cm=inner_width_cm,
            expected_inner_depth_cm=inner_depth_cm,
            expected_inner_height_cm=inner_height_cm,
        )
        stages.append(
            {
                "stage": "apply_shell",
                "status": "completed",
                "wall_thickness_cm": spec.wall_thickness_cm,
                "removed_face_count": shell["removed_face_count"],
                "open_face": shell["open_face"],
            }
        )

        shell_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=shell,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.depth_cm,
                "thickness_cm": spec.height_cm,
            },
            failure_message="Simple enclosure shell verification failed.",
            next_step="Inspect the top-face shell operation before retrying.",
            operation_label="shell",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(shell["body_token"], spec.output_path)["result"],
            partial_result={"body": shell},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_simple_enclosure",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": shell,
            "verification": {
                "body_count": shell_snapshot.body_count,
                "sketch_count": shell_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_depth_cm": spec.depth_cm,
                "expected_height_cm": spec.height_cm,
                "actual_width_cm": shell["width_cm"],
                "actual_depth_cm": shell["height_cm"],
                "actual_height_cm": shell["thickness_cm"],
                "wall_thickness_cm": spec.wall_thickness_cm,
                "inner_width_cm": shell["inner_width_cm"],
                "inner_depth_cm": shell["inner_depth_cm"],
                "inner_height_cm": shell["inner_height_cm"],
                "open_face": shell["open_face"],
                "removed_face_count": shell["removed_face_count"],
                "base_body_count": base_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_shaft_coupler_workflow(self, spec: CreateShaftCouplerInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("shaft_coupler")

        # --- step 1: outer cylinder ---
        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Shaft Coupler Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token, "plane": spec.plane})

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=0.0, center_y_cm=0.0,
                radius_cm=spec.outer_diameter_cm / 2.0,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "profile_role": "outer_cylinder", "diameter_cm": spec.outer_diameter_cm})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=spec.outer_diameter_cm,
            expected_height_cm=spec.outer_diameter_cm,
            workflow_label="Shaft coupler",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "profile_role": "outer_cylinder"})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=spec.length_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": selected_profile["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"], "operation": "new_body"})

        self._verify_body_against_expected_dimensions(
            stages=stages,
            body=body,
            expected_dimensions={
                "width_cm": spec.outer_diameter_cm,
                "height_cm": spec.outer_diameter_cm,
                "thickness_cm": spec.length_cm,
            },
            failure_message="Shaft coupler outer cylinder verification failed.",
            next_step="Inspect the outer cylinder sketch and extrusion before retrying.",
            operation_label="new_body",
        )

        # --- step 2: cross-pin hole BEFORE bore (XZ plane at Y=0) ---
        # Pin hole is cut while the cylinder is still solid so the profile at the
        # cylinder center sits inside material. The XZ default extrude direction
        # (+Y) passes through the half of the cylinder from Y=0 to Y=+radius.
        # On the XZ sketch: X maps to global X, negative sketch-Y maps to
        # positive global Z (observed in pipe_clamp_half live validation).
        pinned_body, pin_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="shaft_coupler",
            sketch_name="Cross Pin Hole Sketch",
            circle_diameter_cm=spec.pin_hole_diameter_cm,
            center_x_cm=0.0,
            center_y_cm=-spec.pin_hole_offset_cm,
            cut_depth_cm=spec.outer_diameter_cm,
            body=body,
            expected_dimensions={
                "width_cm": spec.outer_diameter_cm,
                "height_cm": spec.outer_diameter_cm,
                "thickness_cm": spec.length_cm,
            },
            profile_role="cross_pin_hole",
            operation_label="pin_hole_cut",
            sketch_plane="xz",
        )

        # --- step 3: axial bore cut ---
        bored_body, bore_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="shaft_coupler",
            sketch_name="Axial Bore Sketch",
            circle_diameter_cm=spec.bore_diameter_cm,
            center_x_cm=0.0,
            center_y_cm=0.0,
            cut_depth_cm=spec.length_cm,
            body=pinned_body,
            expected_dimensions={
                "width_cm": spec.outer_diameter_cm,
                "height_cm": spec.outer_diameter_cm,
                "thickness_cm": spec.length_cm,
            },
            profile_role="axial_bore",
            operation_label="bore_cut",
        )

        # --- step 4: export ---
        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(bored_body["token"], spec.output_path)["result"],
            partial_result={"body": bored_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_shaft_coupler",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": bored_body,
            "verification": {
                "body_count": bore_snapshot.body_count,
                "actual_outer_diameter_cm": bored_body["width_cm"],
                "actual_length_cm": bored_body["thickness_cm"],
                "outer_diameter_cm": spec.outer_diameter_cm,
                "length_cm": spec.length_cm,
                "bore_diameter_cm": spec.bore_diameter_cm,
                "pin_hole_diameter_cm": spec.pin_hole_diameter_cm,
                "pin_hole_offset_cm": spec.pin_hole_offset_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_project_box_with_standoffs_workflow(self, spec: CreateProjectBoxWithStandoffsInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("project_box_with_standoffs")
        inner_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        inner_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        inner_height_cm = spec.height_cm - spec.wall_thickness_cm

        # --- step 1: outer solid ---
        body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="project_box_with_standoffs",
            design_name="Project Box With Standoffs Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.depth_cm,
            thickness_cm=spec.height_cm,
        )

        # --- step 2: shell (remove top face) ---
        shell = self._bridge_step(
            stage="apply_shell",
            stages=stages,
            action=lambda: self.apply_shell(
                body_token=body["token"],
                wall_thickness_cm=spec.wall_thickness_cm,
            )["result"]["shell"],
            partial_result={"body": body},
        )
        # Normalize: shell result uses body_token; add token alias for downstream consistency
        shell["token"] = shell["body_token"]
        self._verify_shell_result(
            shell=shell,
            stages=stages,
            expected_body=body,
            expected_wall_thickness_cm=spec.wall_thickness_cm,
            expected_inner_width_cm=inner_width_cm,
            expected_inner_depth_cm=inner_depth_cm,
            expected_inner_height_cm=inner_height_cm,
        )
        stages.append(
            {
                "stage": "apply_shell",
                "status": "completed",
                "wall_thickness_cm": spec.wall_thickness_cm,
                "removed_face_count": shell["removed_face_count"],
                "open_face": shell["open_face"],
            }
        )

        shell_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=shell,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.depth_cm,
                "thickness_cm": spec.height_cm,
            },
            failure_message="Project box shell verification failed.",
            next_step="Inspect the top-face shell operation before retrying.",
            operation_label="shell",
        )

        # --- step 3: four corner standoffs ---
        # draw_rectangle draws from (0,0) to (width, depth), so the box center in sketch
        # coordinates is at (width_cm/2, depth_cm/2), NOT at the origin.
        # Standoff centers must be offset by this box center to land inside the inner cavity.
        # Standoffs are sketched on the base XY plane (Z=0, no offset) and extruded
        # with height = wall_thickness + standoff_height so they penetrate through
        # the floor material — guaranteeing a real intersection for combine_bodies.
        standoff_total_height_cm = spec.wall_thickness_cm + spec.standoff_height_cm
        box_center_x = spec.width_cm / 2.0
        box_center_y = spec.depth_cm / 2.0
        half_inner_w = inner_width_cm / 2.0
        half_inner_d = inner_depth_cm / 2.0
        standoff_positions = [
            (box_center_x - half_inner_w + spec.standoff_inset_cm, box_center_y - half_inner_d + spec.standoff_inset_cm),
            (box_center_x + half_inner_w - spec.standoff_inset_cm, box_center_y - half_inner_d + spec.standoff_inset_cm),
            (box_center_x - half_inner_w + spec.standoff_inset_cm, box_center_y + half_inner_d - spec.standoff_inset_cm),
            (box_center_x + half_inner_w - spec.standoff_inset_cm, box_center_y + half_inner_d - spec.standoff_inset_cm),
        ]

        current_body = shell
        for i, (cx, cy) in enumerate(standoff_positions, start=1):
            standoff_body, current_body = self._create_standoff_and_combine(
                stages=stages,
                shell_body=current_body,
                standoff_index=i,
                center_x_cm=cx,
                center_y_cm=cy,
                diameter_cm=spec.standoff_diameter_cm,
                height_cm=standoff_total_height_cm,
                floor_offset_cm=None,
                expected_outer_dimensions={
                    "width_cm": spec.width_cm,
                    "height_cm": spec.depth_cm,
                    "thickness_cm": spec.height_cm,
                },
            )

        # --- step 4: export ---
        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(current_body["token"], spec.output_path)["result"],
            partial_result={"body": current_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_project_box_with_standoffs",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": current_body,
            "verification": {
                "body_count": 1,
                "expected_width_cm": spec.width_cm,
                "expected_depth_cm": spec.depth_cm,
                "expected_height_cm": spec.height_cm,
                "actual_width_cm": current_body["width_cm"],
                "actual_depth_cm": current_body["height_cm"],
                "actual_height_cm": current_body["thickness_cm"],
                "wall_thickness_cm": spec.wall_thickness_cm,
                "inner_width_cm": inner_width_cm,
                "inner_depth_cm": inner_depth_cm,
                "inner_height_cm": inner_height_cm,
                "standoff_count": 4,
                "standoff_diameter_cm": spec.standoff_diameter_cm,
                "standoff_height_cm": spec.standoff_height_cm,
                "standoff_inset_cm": spec.standoff_inset_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_standoff_and_combine(
        self,
        *,
        stages: list[dict],
        shell_body: dict,
        standoff_index: int,
        center_x_cm: float,
        center_y_cm: float,
        diameter_cm: float,
        height_cm: float,
        floor_offset_cm: float | None,
        expected_outer_dimensions: dict[str, float],
    ) -> tuple[dict, dict]:
        """Create one standoff post and combine it into the shell body.

        Returns (standoff_body, combined_body).
        """
        sketch_name = f"Standoff {standoff_index} Sketch"
        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(
                plane="xy", name=sketch_name, offset_cm=floor_offset_cm,
            ),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": sketch_token,
                "plane": "xy",
                "offset_cm": floor_offset_cm,
                "sketch_role": f"standoff_{standoff_index}",
            }
        )

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=center_x_cm,
                center_y_cm=center_y_cm,
                radius_cm=diameter_cm / 2.0,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append(
            {
                "stage": "draw_circle",
                "status": "completed",
                "profile_role": f"standoff_{standoff_index}",
                "diameter_cm": diameter_cm,
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
            expected_width_cm=diameter_cm,
            expected_height_cm=diameter_cm,
            workflow_label="Project box with standoffs",
            stages=stages,
        )
        stages.append(
            {
                "stage": "list_profiles",
                "status": "completed",
                "profile_count": len(profiles),
                "profile_role": f"standoff_{standoff_index}",
            }
        )

        standoff_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=height_cm,
                body_name=f"Standoff {standoff_index}",
            )["result"]["body"],
            partial_result={"profile_token": selected_profile["token"]},
        )
        stages.append(
            {
                "stage": "extrude_profile",
                "status": "completed",
                "body_token": standoff_body["token"],
                "operation": "new_body",
                "profile_role": f"standoff_{standoff_index}",
            }
        )

        # Verify the standoff exists as a separate body before combining
        pre_combine_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"shell_body": shell_body, "standoff_body": standoff_body},
        )
        pre_combine_snapshot = VerificationSnapshot.from_scene(pre_combine_scene)
        if pre_combine_snapshot.body_count < 2:
            raise WorkflowFailure(
                f"Standoff {standoff_index} extrusion did not produce a separate body.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": pre_combine_scene, "stages": stages},
                next_step="Inspect the standoff sketch and extrusion before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": pre_combine_snapshot.__dict__,
                "operation": f"standoff_{standoff_index}_new_body",
            }
        )

        # Combine standoff into shell body
        combined_body = self._bridge_step(
            stage="combine_bodies",
            stages=stages,
            action=lambda: self.combine_bodies(
                target_body_token=shell_body["token"],
                tool_body_token=standoff_body["token"],
            )["result"]["body"],
            partial_result={"target_body": shell_body, "tool_body": standoff_body},
        )
        if combined_body["token"] != shell_body["token"]:
            raise WorkflowFailure(
                f"Standoff {standoff_index} combine returned an unexpected body token.",
                stage="combine_bodies",
                classification="verification_failed",
                partial_result={"combined_body": combined_body, "expected_body": shell_body, "stages": stages},
                next_step="Inspect target-body selection before retrying the body combine.",
            )
        stages.append(
            {
                "stage": "combine_bodies",
                "status": "completed",
                "body_token": combined_body["token"],
                "tool_body_token": standoff_body["token"],
                "standoff_index": standoff_index,
            }
        )

        # Verify after combine — outer dimensions should be unchanged
        combined_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=combined_body,
            expected_dimensions=expected_outer_dimensions,
            failure_message=f"Standoff {standoff_index} combine verification failed.",
            next_step="Inspect standoff placement and body combine before retrying.",
            operation_label=f"standoff_{standoff_index}_combine",
        )

        return standoff_body, combined_body

    def _create_lid_for_box_workflow(self, spec: CreateLidForBoxInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("lid_for_box")
        rim_opening_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        rim_opening_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        total_height_cm = spec.lid_thickness_cm + spec.rim_depth_cm

        base_body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="lid_for_box",
            design_name="Lid For Box Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.depth_cm,
            thickness_cm=total_height_cm,
        )

        lid_body, rim_snapshot = self._run_rectangle_cut_stage(
            stages=stages,
            workflow_name="lid_for_box",
            sketch_name=spec.rim_cut_sketch_name,
            origin_x_cm=spec.wall_thickness_cm,
            origin_y_cm=spec.wall_thickness_cm,
            width_cm=rim_opening_width_cm,
            height_cm=rim_opening_depth_cm,
            cut_depth_cm=spec.rim_depth_cm,
            body=base_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.depth_cm,
                "thickness_cm": total_height_cm,
            },
            profile_role="rim_opening",
            operation_label="rim_cut",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(lid_body["token"], spec.output_path)["result"],
            partial_result={"body": lid_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_lid_for_box",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": lid_body,
            "verification": {
                "body_count": rim_snapshot.body_count,
                "sketch_count": rim_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_depth_cm": spec.depth_cm,
                "expected_height_cm": total_height_cm,
                "actual_width_cm": lid_body["width_cm"],
                "actual_depth_cm": lid_body["height_cm"],
                "actual_height_cm": lid_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "lid_thickness_cm": spec.lid_thickness_cm,
                "rim_depth_cm": spec.rim_depth_cm,
                "wall_thickness_cm": spec.wall_thickness_cm,
                "rim_opening_width_cm": rim_opening_width_cm,
                "rim_opening_depth_cm": rim_opening_depth_cm,
                "base_body_count": base_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_box_with_lid_workflow(self, spec: CreateBoxWithLidInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("box_with_lid")

        cavity_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        cavity_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        cavity_cut_depth_cm = spec.box_height_cm - spec.floor_thickness_cm
        lid_total_height_cm = spec.lid_thickness_cm + spec.rim_depth_cm
        # Cap lid: outer dims extend beyond box exterior by wall + clearance on each side
        lid_width_cm = spec.width_cm + (spec.wall_thickness_cm * 2.0) + (spec.clearance_cm * 2.0)
        lid_depth_cm = spec.depth_cm + (spec.wall_thickness_cm * 2.0) + (spec.clearance_cm * 2.0)
        # Rim cut opening: slightly larger than box exterior so lid slides over it
        rim_opening_width_cm = spec.width_cm + (spec.clearance_cm * 2.0)
        rim_opening_depth_cm = spec.depth_cm + (spec.clearance_cm * 2.0)
        # Centering offsets: lid must be centered over box, not flush at (0,0)
        lid_origin_x_cm = -(spec.wall_thickness_cm + spec.clearance_cm)
        lid_origin_y_cm = -(spec.wall_thickness_cm + spec.clearance_cm)
        rim_origin_x_cm = -spec.clearance_cm
        rim_origin_y_cm = -spec.clearance_cm

        # --- setup ---
        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Box With Lid Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        # --- box base ---
        box_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Box Outer Sketch"),
        )
        box_sketch_token = box_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": box_sketch_token, "role": "box_base"})

        self._bridge_step(
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.depth_cm, sketch_token=box_sketch_token),
        )
        stages.append({"stage": "draw_rectangle", "status": "completed", "role": "box_base"})

        box_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(box_sketch_token)["result"]["profiles"],
        )
        box_base_profile = self._select_profile_by_dimensions(
            box_profiles,
            expected_width_cm=spec.width_cm,
            expected_height_cm=spec.depth_cm,
            workflow_label="Box with lid",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(box_profiles), "role": "box_base"})

        box_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=box_base_profile["token"],
                distance_cm=spec.box_height_cm,
                body_name="Box Body",
            )["result"]["body"],
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": box_body["token"], "role": "box_base"})

        box_base_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"box_body": box_body},
        )
        box_base_snapshot = VerificationSnapshot.from_scene(box_base_scene)
        if box_base_snapshot.body_count != 1:
            raise WorkflowFailure(
                "Box base extrusion produced unexpected body count.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": box_base_scene, "stages": stages},
                next_step="Inspect the box sketch and extrusion before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": box_base_snapshot.__dict__, "role": "box_base"})

        # --- box cavity cut ---
        cavity_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Box Cavity Sketch", offset_cm=spec.floor_thickness_cm),
        )
        cavity_sketch_token = cavity_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": cavity_sketch_token, "role": "cavity"})

        self._bridge_step(
            stage="draw_rectangle_at",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=spec.wall_thickness_cm,
                origin_y_cm=spec.wall_thickness_cm,
                width_cm=cavity_width_cm,
                height_cm=cavity_depth_cm,
                sketch_token=cavity_sketch_token,
            ),
        )
        stages.append({"stage": "draw_rectangle_at", "status": "completed", "role": "cavity"})

        cavity_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(cavity_sketch_token)["result"]["profiles"],
        )
        cavity_profile = self._select_profile_by_dimensions(
            cavity_profiles,
            expected_width_cm=cavity_width_cm,
            expected_height_cm=cavity_depth_cm,
            workflow_label="Box with lid",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(cavity_profiles), "role": "cavity"})

        box_body_after_cut = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=cavity_profile["token"],
                distance_cm=cavity_cut_depth_cm,
                body_name="cavity",
                operation="cut",
                target_body_token=box_body["token"],
            )["result"]["body"],
            partial_result={"box_body": box_body},
        )
        if box_body_after_cut["token"] != box_body["token"]:
            raise WorkflowFailure(
                "Box cavity cut returned an unexpected body token.",
                stage="extrude_profile",
                classification="verification_failed",
                partial_result={"box_body": box_body_after_cut, "expected_body": box_body, "stages": stages},
                next_step="Inspect cut-body targeting before retrying the box cavity cut.",
            )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": box_body_after_cut["token"], "role": "cavity_cut"})

        cavity_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"box_body": box_body_after_cut},
        )
        cavity_snapshot = VerificationSnapshot.from_scene(cavity_scene)
        if cavity_snapshot.body_count != 1:
            raise WorkflowFailure(
                "Box cavity cut produced unexpected body count.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": cavity_scene, "stages": stages},
                next_step="Inspect the cavity sketch and cut depth before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": cavity_snapshot.__dict__, "role": "cavity_cut"})

        # --- lid base (new_body in same design) ---
        lid_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Lid Outer Sketch"),
        )
        lid_sketch_token = lid_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": lid_sketch_token, "role": "lid_base"})

        self._bridge_step(
            stage="draw_rectangle_at",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=lid_origin_x_cm,
                origin_y_cm=lid_origin_y_cm,
                width_cm=lid_width_cm,
                height_cm=lid_depth_cm,
                sketch_token=lid_sketch_token,
            ),
        )
        stages.append({"stage": "draw_rectangle_at", "status": "completed", "role": "lid_base"})

        lid_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(lid_sketch_token)["result"]["profiles"],
        )
        lid_base_profile = self._select_profile_by_dimensions(
            lid_profiles,
            expected_width_cm=lid_width_cm,
            expected_height_cm=lid_depth_cm,
            workflow_label="Box with lid",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(lid_profiles), "role": "lid_base"})

        lid_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=lid_base_profile["token"],
                distance_cm=lid_total_height_cm,
                body_name="Lid Body",
                operation="new_body",
            )["result"]["body"],
            partial_result={"box_body": box_body_after_cut},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": lid_body["token"], "role": "lid_base"})

        lid_base_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"box_body": box_body_after_cut, "lid_body": lid_body},
        )
        lid_base_snapshot = VerificationSnapshot.from_scene(lid_base_scene)
        if lid_base_snapshot.body_count != 2:
            raise WorkflowFailure(
                f"Lid base extrusion expected 2 bodies in design, got {lid_base_snapshot.body_count}.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": lid_base_scene, "stages": stages},
                next_step="Inspect the lid sketch and extrusion operation. Ensure new_body is used.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": lid_base_snapshot.__dict__, "role": "lid_base"})

        # --- lid rim cut ---
        rim_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Lid Rim Sketch"),
        )
        rim_sketch_token = rim_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": rim_sketch_token, "role": "rim"})

        self._bridge_step(
            stage="draw_rectangle_at",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=rim_origin_x_cm,
                origin_y_cm=rim_origin_y_cm,
                width_cm=rim_opening_width_cm,
                height_cm=rim_opening_depth_cm,
                sketch_token=rim_sketch_token,
            ),
        )
        stages.append({"stage": "draw_rectangle_at", "status": "completed", "role": "rim"})

        rim_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(rim_sketch_token)["result"]["profiles"],
        )
        rim_profile = self._select_profile_by_dimensions(
            rim_profiles,
            expected_width_cm=rim_opening_width_cm,
            expected_height_cm=rim_opening_depth_cm,
            workflow_label="Box with lid",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(rim_profiles), "role": "rim"})

        lid_body_after_rim = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=rim_profile["token"],
                distance_cm=spec.rim_depth_cm,
                body_name="rim",
                operation="cut",
                target_body_token=lid_body["token"],
            )["result"]["body"],
            partial_result={"box_body": box_body_after_cut, "lid_body": lid_body},
        )
        if lid_body_after_rim["token"] != lid_body["token"]:
            raise WorkflowFailure(
                "Lid rim cut returned an unexpected body token.",
                stage="extrude_profile",
                classification="verification_failed",
                partial_result={"lid_body": lid_body_after_rim, "expected_body": lid_body, "stages": stages},
                next_step="Inspect cut-body targeting before retrying the lid rim cut.",
            )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": lid_body_after_rim["token"], "role": "rim_cut"})

        rim_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"box_body": box_body_after_cut, "lid_body": lid_body_after_rim},
        )
        rim_snapshot = VerificationSnapshot.from_scene(rim_scene)
        if rim_snapshot.body_count != 2:
            raise WorkflowFailure(
                f"Lid rim cut expected 2 bodies in design, got {rim_snapshot.body_count}.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": rim_scene, "stages": stages},
                next_step="Inspect the rim cut — it may have cut the box body or merged bodies unexpectedly.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": rim_snapshot.__dict__, "role": "rim_cut"})

        # --- export both ---
        exported_box = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(box_body_after_cut["token"], spec.output_path_box)["result"],
            partial_result={"box_body": box_body_after_cut},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported_box["output_path"], "role": "box"})

        exported_lid = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(lid_body_after_rim["token"], spec.output_path_lid)["result"],
            partial_result={"lid_body": lid_body_after_rim},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported_lid["output_path"], "role": "lid"})

        return {
            "ok": True,
            "workflow": "create_box_with_lid",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "box_body": box_body_after_cut,
            "lid_body": lid_body_after_rim,
            "verification": {
                "body_count": rim_snapshot.body_count,
                "box_width_cm": spec.width_cm,
                "box_depth_cm": spec.depth_cm,
                "box_height_cm": spec.box_height_cm,
                "cavity_width_cm": cavity_width_cm,
                "cavity_depth_cm": cavity_depth_cm,
                "lid_width_cm": lid_width_cm,
                "lid_depth_cm": lid_depth_cm,
                "lid_total_height_cm": lid_total_height_cm,
                "rim_opening_width_cm": rim_opening_width_cm,
                "rim_opening_depth_cm": rim_opening_depth_cm,
                "rim_depth_cm": spec.rim_depth_cm,
                "wall_thickness_cm": spec.wall_thickness_cm,
                "clearance_cm": spec.clearance_cm,
            },
            "export_box": exported_box,
            "export_lid": exported_lid,
            "stages": stages,
            "retry_policy": "none",
        }

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
        except BridgeTimeoutError as exc:
            payload = {"stages": list(stages)}
            if partial_result:
                payload.update(partial_result)
            raise WorkflowFailure(
                f"Workflow bridge call timed out during {stage}: {exc}",
                stage=stage,
                classification="timeout",
                partial_result=payload,
                next_step=next_step or "Retry after checking whether Fusion is busy or the configured bridge timeout is too aggressive.",
            ) from exc
        except BridgeCancelledError as exc:
            payload = {"stages": list(stages)}
            if partial_result:
                payload.update(partial_result)
            raise WorkflowFailure(
                f"Workflow bridge call was cancelled during {stage}: {exc}",
                stage=stage,
                classification="cancelled",
                partial_result=payload,
                next_step=next_step or "Confirm whether the workflow was intentionally cancelled before retrying.",
            ) from exc
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

    def _create_revolved_body(
        self,
        *,
        stages: list[dict],
        workflow_name: str,
        design_name: str,
        sketch_name: str,
        body_name: str,
        base_diameter_cm: float,
        top_diameter_cm: float,
        height_cm: float,
        expected_dimensions: dict[str, float],
    ) -> tuple[dict, VerificationSnapshot]:
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name=sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token, "plane": "xy"})

        self._bridge_step(
            stage="draw_revolve_profile",
            stages=stages,
            action=lambda: self.draw_revolve_profile(
                base_diameter_cm=base_diameter_cm,
                top_diameter_cm=top_diameter_cm,
                height_cm=height_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append(
            {
                "stage": "draw_revolve_profile",
                "status": "completed",
                "base_diameter_cm": base_diameter_cm,
                "top_diameter_cm": top_diameter_cm,
                "height_cm": height_cm,
            }
        )

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        revolved_profile = self._select_revolve_profile_by_dimensions(
            profiles,
            expected_width_cm=max(base_diameter_cm, top_diameter_cm),
            expected_height_cm=height_cm,
            workflow_label=workflow_name.replace("_", " ").capitalize(),
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "profile_role": "revolve"})

        revolved_body = self._bridge_step(
            stage="revolve_profile",
            stages=stages,
            action=lambda: self.revolve_profile(
                profile_token=revolved_profile["token"],
                body_name=body_name,
            )["result"]["body"],
            partial_result={"profile_token": revolved_profile["token"]},
        )
        self._verify_revolve_body(
            revolve_body=revolved_body,
            stages=stages,
            expected_body_name=body_name,
            expected_base_diameter_cm=base_diameter_cm,
            expected_top_diameter_cm=top_diameter_cm,
            expected_height_cm=height_cm,
        )
        stages.append(
            {
                "stage": "revolve_profile",
                "status": "completed",
                "body_token": revolved_body["token"],
                "base_diameter_cm": revolved_body["base_diameter_cm"],
                "top_diameter_cm": revolved_body["top_diameter_cm"],
                "height_cm": revolved_body["axial_height_cm"],
                "axis": revolved_body["axis"],
            }
        )

        snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=revolved_body,
            expected_dimensions=expected_dimensions,
            failure_message=f"{workflow_name.replace('_', ' ').capitalize()} revolve verification failed.",
            next_step="Inspect the revolved profile and revolve axis before retrying.",
            operation_label="revolve",
        )
        return revolved_body, snapshot

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

    def _create_cylinder_workflow(self, spec: CreateCylinderInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("cylinder")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Cylinder Workflow"))
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
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
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

        radius_cm = spec.diameter_cm / 2.0
        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=radius_cm,
                center_y_cm=radius_cm,
                radius_cm=radius_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "diameter_cm": spec.diameter_cm})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                "Cylinder workflow expected exactly one profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the circle sketch and remove ambiguity before extrusion.",
            )
        profile = profiles[0]
        expected_profile_dimensions = {
            "width_cm": spec.diameter_cm,
            "height_cm": spec.diameter_cm,
        }
        actual_profile_dimensions = {
            "width_cm": profile["width_cm"],
            "height_cm": profile["height_cm"],
        }
        if actual_profile_dimensions != expected_profile_dimensions:
            raise WorkflowFailure(
                "Cylinder workflow profile verification failed.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected": expected_profile_dimensions,
                    "stages": stages,
                },
                next_step="Inspect the circle radius and selected profile before extrusion.",
            )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=profile["token"],
                distance_cm=spec.height_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": profile["token"]},
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
                "Cylinder workflow verification failed: expected exactly one body.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene, "stages": stages},
                next_step="Preserve the partial model and inspect body creation before retrying.",
            )
        expected_dimensions = {
            "width_cm": spec.diameter_cm,
            "height_cm": spec.diameter_cm,
            "thickness_cm": spec.height_cm,
        }
        actual_dimensions = {
            "width_cm": body["width_cm"],
            "height_cm": body["height_cm"],
            "thickness_cm": body["thickness_cm"],
        }
        if actual_dimensions != expected_dimensions:
            raise WorkflowFailure(
                "Cylinder workflow verification failed: body dimensions do not match the requested values.",
                stage="verify_dimensions",
                classification="verification_failed",
                partial_result={"body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect the circle profile and extrusion distance before retrying.",
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
            "workflow": "create_cylinder",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "verification": {
                "body_count": snapshot.body_count,
                "sketch_count": snapshot.sketch_count,
                "expected_diameter_cm": spec.diameter_cm,
                "expected_height_cm": spec.height_cm,
                "actual_diameter_cm": body["width_cm"],
                "actual_secondary_diameter_cm": body["height_cm"],
                "actual_height_cm": body["thickness_cm"],
                "sketch_plane": spec.plane,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_tube_workflow(self, spec: CreateTubeInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("tube")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Tube Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token, "plane": spec.plane})

        outer_radius_cm = spec.outer_diameter_cm / 2.0
        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=outer_radius_cm,
                center_y_cm=outer_radius_cm,
                radius_cm=outer_radius_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "diameter_cm": spec.outer_diameter_cm, "profile_role": "outer"})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                "Tube workflow expected exactly one outer profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the outer circle sketch before extrusion.",
            )
        outer_profile = profiles[0]
        if not self._close(outer_profile.get("width_cm"), spec.outer_diameter_cm) or not self._close(
            outer_profile.get("height_cm"), spec.outer_diameter_cm
        ):
            raise WorkflowFailure(
                "Tube workflow outer profile verification failed.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected": {"width_cm": spec.outer_diameter_cm, "height_cm": spec.outer_diameter_cm},
                    "stages": stages,
                },
                next_step="Inspect the outer circle radius before extrusion.",
            )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "profile_role": "outer"})

        outer_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=outer_profile["token"],
                distance_cm=spec.height_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": outer_profile["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": outer_body["token"], "operation": "new_body"})

        outer_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=outer_body,
            expected_dimensions={
                "width_cm": spec.outer_diameter_cm,
                "height_cm": spec.outer_diameter_cm,
                "thickness_cm": spec.height_cm,
            },
            failure_message="Tube workflow outer-body verification failed.",
            next_step="Inspect the outer circle profile and extrusion distance before retrying.",
            operation_label="outer_body",
        )

        tube_body, tube_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="tube",
            sketch_name=spec.bore_sketch_name,
            circle_diameter_cm=spec.inner_diameter_cm,
            center_x_cm=outer_radius_cm,
            center_y_cm=outer_radius_cm,
            cut_depth_cm=spec.height_cm,
            body=outer_body,
            expected_dimensions={
                "width_cm": spec.outer_diameter_cm,
                "height_cm": spec.outer_diameter_cm,
                "thickness_cm": spec.height_cm,
            },
            profile_role="tube_bore",
            operation_label="tube_bore_cut",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(tube_body["token"], spec.output_path)["result"],
            partial_result={"body": tube_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_tube",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": tube_body,
            "verification": {
                "body_count": tube_snapshot.body_count,
                "sketch_count": tube_snapshot.sketch_count,
                "outer_diameter_cm": spec.outer_diameter_cm,
                "inner_diameter_cm": spec.inner_diameter_cm,
                "height_cm": spec.height_cm,
                "actual_outer_diameter_cm": tube_body["width_cm"],
                "actual_secondary_outer_diameter_cm": tube_body["height_cm"],
                "actual_height_cm": tube_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "outer_body_snapshot_body_count": outer_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_revolve_workflow(self, spec: CreateRevolveInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("revolve")
        max_diameter_cm = max(spec.base_diameter_cm, spec.top_diameter_cm)
        expected_dimensions = {
            "width_cm": max_diameter_cm,
            "height_cm": spec.height_cm,
            "thickness_cm": max_diameter_cm,
        }

        revolved_body, revolve_snapshot = self._create_revolved_body(
            stages=stages,
            workflow_name="revolve",
            design_name="Revolve Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            base_diameter_cm=spec.base_diameter_cm,
            top_diameter_cm=spec.top_diameter_cm,
            height_cm=spec.height_cm,
            expected_dimensions=expected_dimensions,
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(revolved_body["token"], spec.output_path)["result"],
            partial_result={"body": revolved_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_revolve",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": revolved_body,
            "verification": {
                "body_count": revolve_snapshot.body_count,
                "sketch_count": revolve_snapshot.sketch_count,
                "base_diameter_cm": spec.base_diameter_cm,
                "top_diameter_cm": spec.top_diameter_cm,
                "actual_base_diameter_cm": revolved_body["base_diameter_cm"],
                "actual_top_diameter_cm": revolved_body["top_diameter_cm"],
                "actual_max_diameter_cm": revolved_body["width_cm"],
                "actual_secondary_max_diameter_cm": revolved_body["thickness_cm"],
                "actual_height_cm": revolved_body["height_cm"],
                "axis": revolved_body["axis"],
                "angle_deg": revolved_body["angle_deg"],
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_tapered_knob_blank_workflow(self, spec: CreateTaperedKnobBlankInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("tapered_knob_blank")
        max_diameter_cm = max(spec.base_diameter_cm, spec.top_diameter_cm)
        expected_dimensions = {
            "width_cm": max_diameter_cm,
            "height_cm": spec.height_cm,
            "thickness_cm": max_diameter_cm,
        }

        knob_body, revolve_snapshot = self._create_revolved_body(
            stages=stages,
            workflow_name="tapered_knob_blank",
            design_name="Tapered Knob Blank Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            base_diameter_cm=spec.base_diameter_cm,
            top_diameter_cm=spec.top_diameter_cm,
            height_cm=spec.height_cm,
            expected_dimensions=expected_dimensions,
        )

        socket_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xz", name=spec.socket_sketch_name),
        )
        socket_sketch_token = socket_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": socket_sketch_token,
                "plane": "xz",
                "sketch_role": "stem_socket",
            }
        )

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=0.0,
                center_y_cm=0.0,
                radius_cm=spec.stem_socket_diameter_cm / 2.0,
                sketch_token=socket_sketch_token,
            ),
            partial_result={"sketch_token": socket_sketch_token},
        )
        stages.append(
            {
                "stage": "draw_circle",
                "status": "completed",
                "profile_role": "stem_socket",
                "diameter_cm": spec.stem_socket_diameter_cm,
            }
        )

        socket_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(socket_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": socket_sketch_token},
        )
        socket_profile = self._select_profile_by_dimensions(
            socket_profiles,
            expected_width_cm=spec.stem_socket_diameter_cm,
            expected_height_cm=spec.stem_socket_diameter_cm,
            workflow_label="Tapered knob blank",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(socket_profiles), "profile_role": "stem_socket"})

        socket_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=socket_profile["token"],
                distance_cm=spec.height_cm,
                body_name="stem_socket",
                operation="cut",
                target_body_token=knob_body["token"],
            )["result"]["body"],
            partial_result={"profile_token": socket_profile["token"], "body": knob_body},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": socket_body["token"], "operation": "cut", "profile_role": "stem_socket"})

        socket_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=socket_body,
            expected_dimensions=expected_dimensions,
            failure_message="Tapered knob blank socket-cut verification failed.",
            next_step="Inspect the XZ socket sketch and axial cut distance before retrying.",
            operation_label="stem_socket_cut",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(socket_body["token"], spec.output_path)["result"],
            partial_result={"body": socket_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_tapered_knob_blank",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": socket_body,
            "verification": {
                "body_count": socket_snapshot.body_count,
                "sketch_count": socket_snapshot.sketch_count,
                "base_diameter_cm": spec.base_diameter_cm,
                "top_diameter_cm": spec.top_diameter_cm,
                "stem_socket_diameter_cm": spec.stem_socket_diameter_cm,
                "actual_base_diameter_cm": knob_body["base_diameter_cm"],
                "actual_top_diameter_cm": knob_body["top_diameter_cm"],
                "actual_max_diameter_cm": socket_body["width_cm"],
                "actual_secondary_max_diameter_cm": socket_body["thickness_cm"],
                "actual_height_cm": socket_body["height_cm"],
                "axis": knob_body["axis"],
                "angle_deg": knob_body["angle_deg"],
                "outer_body_snapshot_body_count": revolve_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_flanged_bushing_workflow(self, spec: CreateFlangedBushingInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("flanged_bushing")
        max_outer_diameter_cm = max(spec.shaft_outer_diameter_cm, spec.flange_outer_diameter_cm)
        total_length_cm = spec.shaft_length_cm

        shaft_body, shaft_snapshot = self._create_revolved_body(
            stages=stages,
            workflow_name="flanged_bushing",
            design_name="Flanged Bushing Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            base_diameter_cm=spec.shaft_outer_diameter_cm,
            top_diameter_cm=spec.shaft_outer_diameter_cm,
            height_cm=spec.shaft_length_cm,
            expected_dimensions={
                "width_cm": spec.shaft_outer_diameter_cm,
                "height_cm": spec.shaft_length_cm,
                "thickness_cm": spec.shaft_outer_diameter_cm,
            },
        )

        flange_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name=spec.flange_sketch_name),
        )
        flange_sketch_token = flange_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": flange_sketch_token,
                "plane": "xy",
                "sketch_role": "flange",
            }
        )

        self._bridge_step(
            stage="draw_revolve_profile",
            stages=stages,
            action=lambda: self.draw_revolve_profile(
                base_diameter_cm=spec.flange_outer_diameter_cm,
                top_diameter_cm=spec.flange_outer_diameter_cm,
                height_cm=spec.flange_thickness_cm,
                sketch_token=flange_sketch_token,
            ),
            partial_result={"sketch_token": flange_sketch_token},
        )
        stages.append(
            {
                "stage": "draw_revolve_profile",
                "status": "completed",
                "profile_role": "flange",
                "base_diameter_cm": spec.flange_outer_diameter_cm,
                "top_diameter_cm": spec.flange_outer_diameter_cm,
                "height_cm": spec.flange_thickness_cm,
            }
        )

        flange_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(flange_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": flange_sketch_token},
        )
        flange_profile = self._select_profile_by_dimensions(
            flange_profiles,
            expected_width_cm=spec.flange_outer_diameter_cm,
            expected_height_cm=spec.flange_thickness_cm,
            workflow_label="Flanged bushing",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(flange_profiles), "profile_role": "flange"})

        flange_body = self._bridge_step(
            stage="revolve_profile",
            stages=stages,
            action=lambda: self.revolve_profile(
                profile_token=flange_profile["token"],
                body_name="Bushing Flange",
            )["result"]["body"],
            partial_result={"profile_token": flange_profile["token"], "body": shaft_body},
        )
        self._verify_revolve_body(
            revolve_body=flange_body,
            stages=stages,
            expected_body_name="Bushing Flange",
            expected_base_diameter_cm=spec.flange_outer_diameter_cm,
            expected_top_diameter_cm=spec.flange_outer_diameter_cm,
            expected_height_cm=spec.flange_thickness_cm,
        )
        stages.append(
            {
                "stage": "revolve_profile",
                "status": "completed",
                "body_token": flange_body["token"],
                "base_diameter_cm": flange_body["base_diameter_cm"],
                "top_diameter_cm": flange_body["top_diameter_cm"],
                "height_cm": flange_body["axial_height_cm"],
                "axis": flange_body["axis"],
                "profile_role": "flange",
            }
        )

        two_body_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"shaft_body": shaft_body, "flange_body": flange_body},
        )
        two_body_snapshot = VerificationSnapshot.from_scene(two_body_scene)
        if two_body_snapshot.body_count != 2:
            raise WorkflowFailure(
                "Flanged bushing verification failed before combining bodies.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": two_body_scene, "stages": stages},
                next_step="Inspect flange revolve profile and body creation before retrying.",
            )
        flange_actual_dimensions = {
            "width_cm": flange_body["width_cm"],
            "height_cm": flange_body["height_cm"],
            "thickness_cm": flange_body["thickness_cm"],
        }
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": two_body_snapshot.__dict__,
                "dimensions": flange_actual_dimensions,
                "operation": "flange_new_body",
            }
        )

        combined_body = self._bridge_step(
            stage="combine_bodies",
            stages=stages,
            action=lambda: self.combine_bodies(
                target_body_token=shaft_body["token"],
                tool_body_token=flange_body["token"],
            )["result"]["body"],
            partial_result={"target_body": shaft_body, "tool_body": flange_body},
        )
        if combined_body["token"] != shaft_body["token"]:
            raise WorkflowFailure(
                "Flanged bushing combine returned an unexpected body token.",
                stage="combine_bodies",
                classification="verification_failed",
                partial_result={"combined_body": combined_body, "expected_body": shaft_body, "stages": stages},
                next_step="Inspect target-body selection before retrying the body combine.",
            )
        stages.append(
            {
                "stage": "combine_bodies",
                "status": "completed",
                "body_token": combined_body["token"],
                "tool_body_token": flange_body["token"],
            }
        )

        combined_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=combined_body,
            expected_dimensions={
                "width_cm": max_outer_diameter_cm,
                "height_cm": total_length_cm,
                "thickness_cm": max_outer_diameter_cm,
            },
            failure_message="Flanged bushing combine verification failed.",
            next_step="Inspect flange placement and body combine before retrying.",
            operation_label="combine",
        )

        bored_body, bore_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="flanged_bushing",
            sketch_name=spec.bore_sketch_name,
            circle_diameter_cm=spec.bore_diameter_cm,
            center_x_cm=0.0,
            center_y_cm=0.0,
            cut_depth_cm=total_length_cm,
            body=combined_body,
            expected_dimensions={
                "width_cm": max_outer_diameter_cm,
                "height_cm": total_length_cm,
                "thickness_cm": max_outer_diameter_cm,
            },
            profile_role="bore",
            operation_label="bore_cut",
            sketch_plane="xz",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(bored_body["token"], spec.output_path)["result"],
            partial_result={"body": bored_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_flanged_bushing",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": bored_body,
            "verification": {
                "body_count": bore_snapshot.body_count,
                "sketch_count": bore_snapshot.sketch_count,
                "shaft_outer_diameter_cm": spec.shaft_outer_diameter_cm,
                "shaft_length_cm": spec.shaft_length_cm,
                "flange_outer_diameter_cm": spec.flange_outer_diameter_cm,
                "flange_thickness_cm": spec.flange_thickness_cm,
                "bore_diameter_cm": spec.bore_diameter_cm,
                "total_length_cm": total_length_cm,
                "actual_outer_diameter_cm": bored_body["width_cm"],
                "actual_secondary_outer_diameter_cm": bored_body["thickness_cm"],
                "actual_length_cm": bored_body["height_cm"],
                "shaft_body_count": shaft_snapshot.body_count,
                "pre_combine_body_count": two_body_snapshot.body_count,
                "post_combine_body_count": combined_snapshot.body_count,
                "post_bore_body_count": bore_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_pipe_clamp_half_workflow(self, spec: CreatePipeClampHalfInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("pipe_clamp_half")
        first_hole_center_x_cm = spec.bolt_hole_edge_offset_x_cm
        second_hole_center_x_cm = spec.clamp_width_cm - spec.bolt_hole_edge_offset_x_cm
        expected_dimensions = {
            "width_cm": spec.clamp_width_cm,
            "height_cm": spec.clamp_length_cm,
            "thickness_cm": spec.clamp_height_cm,
        }

        base_body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="pipe_clamp_half",
            design_name="Pipe Clamp Half Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.clamp_width_cm,
            height_cm=spec.clamp_length_cm,
            thickness_cm=spec.clamp_height_cm,
        )

        saddle_body, saddle_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="pipe_clamp_half",
            sketch_name=spec.channel_sketch_name,
            circle_diameter_cm=spec.pipe_outer_diameter_cm,
            center_x_cm=spec.clamp_width_cm / 2.0,
            # In the current live xz adapter path, negative sketch-local Y maps toward positive model Z.
            center_y_cm=-spec.clamp_height_cm,
            cut_depth_cm=spec.clamp_length_cm,
            body=base_body,
            expected_dimensions=expected_dimensions,
            profile_role="pipe_saddle",
            operation_label="pipe_saddle_cut",
            sketch_plane="xz",
        )

        first_hole_body, first_hole_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="pipe_clamp_half",
            sketch_name=spec.first_hole_sketch_name,
            circle_diameter_cm=spec.bolt_hole_diameter_cm,
            center_x_cm=first_hole_center_x_cm,
            center_y_cm=spec.bolt_hole_center_y_cm,
            cut_depth_cm=spec.clamp_height_cm,
            body=saddle_body,
            expected_dimensions=expected_dimensions,
            profile_role="first_bolt_hole",
            operation_label="first_bolt_hole_cut",
        )

        second_hole_body, second_hole_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="pipe_clamp_half",
            sketch_name=spec.second_hole_sketch_name,
            circle_diameter_cm=spec.bolt_hole_diameter_cm,
            center_x_cm=second_hole_center_x_cm,
            center_y_cm=spec.bolt_hole_center_y_cm,
            cut_depth_cm=spec.clamp_height_cm,
            body=first_hole_body,
            expected_dimensions=expected_dimensions,
            profile_role="second_bolt_hole",
            operation_label="second_bolt_hole_cut",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(second_hole_body["token"], spec.output_path)["result"],
            partial_result={"body": second_hole_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_pipe_clamp_half",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": second_hole_body,
            "verification": {
                "body_count": second_hole_snapshot.body_count,
                "sketch_count": second_hole_snapshot.sketch_count,
                "clamp_width_cm": spec.clamp_width_cm,
                "clamp_length_cm": spec.clamp_length_cm,
                "clamp_height_cm": spec.clamp_height_cm,
                "pipe_outer_diameter_cm": spec.pipe_outer_diameter_cm,
                "bolt_hole_diameter_cm": spec.bolt_hole_diameter_cm,
                "bolt_hole_edge_offset_x_cm": spec.bolt_hole_edge_offset_x_cm,
                "bolt_hole_center_y_cm": spec.bolt_hole_center_y_cm,
                "actual_clamp_width_cm": second_hole_body["width_cm"],
                "actual_clamp_length_cm": second_hole_body["height_cm"],
                "actual_clamp_height_cm": second_hole_body["thickness_cm"],
                "base_body_count": base_snapshot.body_count,
                "post_saddle_body_count": saddle_snapshot.body_count,
                "post_first_hole_body_count": first_hole_snapshot.body_count,
                "post_second_hole_body_count": second_hole_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_tube_mounting_plate_workflow(self, spec: CreateTubeMountingPlateInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("tube_mounting_plate")
        hole_center_x_cm = spec.width_cm / 2.0
        upper_hole_center_y_cm = spec.edge_offset_y_cm
        lower_hole_center_y_cm = spec.height_cm - spec.edge_offset_y_cm
        tube_center_x_cm = spec.width_cm / 2.0
        tube_center_y_cm = spec.height_cm / 2.0
        overall_height_cm = spec.plate_thickness_cm + spec.tube_height_cm

        base_body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="tube_mounting_plate",
            design_name="Tube Mounting Plate Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.height_cm,
            thickness_cm=spec.plate_thickness_cm,
        )

        upper_hole_body, upper_hole_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="tube_mounting_plate",
            sketch_name=spec.first_hole_sketch_name,
            circle_diameter_cm=spec.hole_diameter_cm,
            center_x_cm=hole_center_x_cm,
            center_y_cm=upper_hole_center_y_cm,
            cut_depth_cm=spec.plate_thickness_cm,
            body=base_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.height_cm,
                "thickness_cm": spec.plate_thickness_cm,
            },
            profile_role="upper_mount_hole",
            operation_label="upper_mount_hole_cut",
        )

        lower_hole_body, lower_hole_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="tube_mounting_plate",
            sketch_name=spec.second_hole_sketch_name,
            circle_diameter_cm=spec.hole_diameter_cm,
            center_x_cm=hole_center_x_cm,
            center_y_cm=lower_hole_center_y_cm,
            cut_depth_cm=spec.plate_thickness_cm,
            body=upper_hole_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.height_cm,
                "thickness_cm": spec.plate_thickness_cm,
            },
            profile_role="lower_mount_hole",
            operation_label="lower_mount_hole_cut",
        )

        tube_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(
                plane="xy",
                name=spec.tube_sketch_name,
                offset_cm=spec.plate_thickness_cm,
            ),
        )
        tube_sketch_token = tube_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": tube_sketch_token,
                "plane": "xy",
                "sketch_role": "tube_outer",
                "offset_cm": spec.plate_thickness_cm,
            }
        )

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=tube_center_x_cm,
                center_y_cm=tube_center_y_cm,
                radius_cm=spec.tube_outer_diameter_cm / 2.0,
                sketch_token=tube_sketch_token,
            ),
            partial_result={"sketch_token": tube_sketch_token},
        )
        stages.append(
            {
                "stage": "draw_circle",
                "status": "completed",
                "profile_role": "tube_outer",
                "diameter_cm": spec.tube_outer_diameter_cm,
            }
        )

        tube_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(tube_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": tube_sketch_token},
        )
        tube_profile = self._select_profile_by_dimensions(
            tube_profiles,
            expected_width_cm=spec.tube_outer_diameter_cm,
            expected_height_cm=spec.tube_outer_diameter_cm,
            workflow_label="Tube mounting plate",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(tube_profiles), "profile_role": "tube_outer"})

        tube_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=tube_profile["token"],
                distance_cm=spec.tube_height_cm,
                body_name="Tube Sleeve",
            )["result"]["body"],
            partial_result={"profile_token": tube_profile["token"], "body": lower_hole_body},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": tube_body["token"], "operation": "new_body", "profile_role": "tube_outer"})

        two_body_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"base_body": lower_hole_body, "tube_body": tube_body},
        )
        two_body_snapshot = VerificationSnapshot.from_scene(two_body_scene)
        tube_expected_dimensions = {
            "width_cm": spec.tube_outer_diameter_cm,
            "height_cm": spec.tube_outer_diameter_cm,
            "thickness_cm": spec.tube_height_cm,
        }
        tube_actual_dimensions = {
            "width_cm": tube_body["width_cm"],
            "height_cm": tube_body["height_cm"],
            "thickness_cm": tube_body["thickness_cm"],
        }
        if two_body_snapshot.body_count != 2 or tube_actual_dimensions != tube_expected_dimensions:
            raise WorkflowFailure(
                "Tube mounting plate sleeve verification failed before combining bodies.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={
                    "scene": two_body_scene,
                    "tube_body": tube_body,
                    "expected": tube_expected_dimensions,
                    "stages": stages,
                },
                next_step="Inspect the offset tube sketch and extrusion before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": two_body_snapshot.__dict__,
                "dimensions": tube_actual_dimensions,
                "operation": "tube_outer_new_body",
            }
        )

        combined_body = self._bridge_step(
            stage="combine_bodies",
            stages=stages,
            action=lambda: self.combine_bodies(
                target_body_token=lower_hole_body["token"],
                tool_body_token=tube_body["token"],
            )["result"]["body"],
            partial_result={"target_body": lower_hole_body, "tool_body": tube_body},
        )
        if combined_body["token"] != lower_hole_body["token"]:
            raise WorkflowFailure(
                "Tube mounting plate combine returned an unexpected body token.",
                stage="combine_bodies",
                classification="verification_failed",
                partial_result={"combined_body": combined_body, "expected_body": lower_hole_body, "stages": stages},
                next_step="Inspect target-body selection before retrying the body combine.",
            )
        stages.append(
            {
                "stage": "combine_bodies",
                "status": "completed",
                "body_token": combined_body["token"],
                "tool_body_token": tube_body["token"],
            }
        )

        combined_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=combined_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.height_cm,
                "thickness_cm": overall_height_cm,
            },
            failure_message="Tube mounting plate combine verification failed.",
            next_step="Inspect the sleeve placement and body combine before retrying.",
            operation_label="combine",
        )

        bored_body, bore_snapshot = self._run_circle_cut_stage(
            stages=stages,
            workflow_name="tube_mounting_plate",
            sketch_name=spec.bore_sketch_name,
            circle_diameter_cm=spec.tube_inner_diameter_cm,
            center_x_cm=tube_center_x_cm,
            center_y_cm=tube_center_y_cm,
            cut_depth_cm=spec.tube_height_cm,
            body=combined_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.height_cm,
                "thickness_cm": overall_height_cm,
            },
            profile_role="tube_bore",
            operation_label="tube_bore_cut",
            sketch_offset_cm=spec.plate_thickness_cm,
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(bored_body["token"], spec.output_path)["result"],
            partial_result={"body": bored_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_tube_mounting_plate",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": bored_body,
            "verification": {
                "body_count": bore_snapshot.body_count,
                "sketch_count": bore_snapshot.sketch_count,
                "plate_width_cm": spec.width_cm,
                "plate_height_cm": spec.height_cm,
                "plate_thickness_cm": spec.plate_thickness_cm,
                "tube_outer_diameter_cm": spec.tube_outer_diameter_cm,
                "tube_inner_diameter_cm": spec.tube_inner_diameter_cm,
                "tube_height_cm": spec.tube_height_cm,
                "overall_height_cm": overall_height_cm,
                "mount_hole_diameter_cm": spec.hole_diameter_cm,
                "mount_hole_count": 2,
                "edge_offset_y_cm": spec.edge_offset_y_cm,
                "actual_width_cm": bored_body["width_cm"],
                "actual_height_cm": bored_body["height_cm"],
                "actual_thickness_cm": bored_body["thickness_cm"],
                "base_body_count": base_snapshot.body_count,
                "post_upper_hole_body_count": upper_hole_snapshot.body_count,
                "post_lower_hole_body_count": lower_hole_snapshot.body_count,
                "pre_combine_body_count": two_body_snapshot.body_count,
                "post_combine_body_count": combined_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_t_handle_with_square_socket_workflow(self, spec: CreateTHandleWithSquareSocketInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("t_handle_with_square_socket")
        stem_origin_x_cm = (spec.tee_width_cm - spec.tee_depth_cm) / 2.0
        effective_square_socket_width_cm = spec.square_socket_width_cm + (spec.socket_clearance_per_side_cm * 2.0)
        socket_origin_x_cm = stem_origin_x_cm + ((spec.tee_depth_cm - effective_square_socket_width_cm) / 2.0)
        socket_origin_y_cm = (spec.tee_depth_cm - effective_square_socket_width_cm) / 2.0
        total_height_cm = spec.stem_length_cm + spec.tee_thickness_cm

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("T Handle Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        stem_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name=spec.stem_sketch_name),
        )
        stem_sketch_token = stem_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": stem_sketch_token, "plane": "xy", "sketch_role": "stem"})

        self._bridge_step(
            stage="draw_rectangle_at",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=stem_origin_x_cm,
                origin_y_cm=0.0,
                width_cm=spec.tee_depth_cm,
                height_cm=spec.tee_depth_cm,
                sketch_token=stem_sketch_token,
            ),
            partial_result={"sketch_token": stem_sketch_token},
        )
        stages.append(
            {
                "stage": "draw_rectangle_at",
                "status": "completed",
                "profile_role": "stem",
                "origin_x_cm": stem_origin_x_cm,
                "origin_y_cm": 0.0,
                "width_cm": spec.tee_depth_cm,
                "height_cm": spec.tee_depth_cm,
            }
        )

        stem_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(stem_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": stem_sketch_token},
        )
        stem_profile = self._select_profile_by_dimensions(
            stem_profiles,
            expected_width_cm=spec.tee_depth_cm,
            expected_height_cm=spec.tee_depth_cm,
            workflow_label="T handle with square socket",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(stem_profiles), "profile_role": "stem"})

        stem_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=stem_profile["token"],
                distance_cm=spec.stem_length_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": stem_profile["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": stem_body["token"], "operation": "new_body", "profile_role": "stem"})

        stem_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=stem_body,
            expected_dimensions={
                "width_cm": spec.tee_depth_cm,
                "height_cm": spec.tee_depth_cm,
                "thickness_cm": spec.stem_length_cm,
            },
            failure_message="T handle stem verification failed.",
            next_step="Inspect the centered stem profile and extrusion before retrying.",
            operation_label="stem_new_body",
        )

        tee_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(
                plane="xy",
                name=spec.tee_sketch_name,
                offset_cm=spec.stem_length_cm,
            ),
        )
        tee_sketch_token = tee_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": tee_sketch_token,
                "plane": "xy",
                "sketch_role": "tee",
                "offset_cm": spec.stem_length_cm,
            }
        )

        self._bridge_step(
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(
                width_cm=spec.tee_width_cm,
                height_cm=spec.tee_depth_cm,
                sketch_token=tee_sketch_token,
            ),
            partial_result={"sketch_token": tee_sketch_token},
        )
        stages.append({"stage": "draw_rectangle", "status": "completed", "profile_role": "tee"})

        tee_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(tee_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": tee_sketch_token},
        )
        tee_profile = self._select_profile_by_dimensions(
            tee_profiles,
            expected_width_cm=spec.tee_width_cm,
            expected_height_cm=spec.tee_depth_cm,
            workflow_label="T handle with square socket",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(tee_profiles), "profile_role": "tee"})

        tee_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=tee_profile["token"],
                distance_cm=spec.tee_thickness_cm,
                body_name="Tee Bar",
            )["result"]["body"],
            partial_result={"profile_token": tee_profile["token"], "body": stem_body},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": tee_body["token"], "operation": "new_body", "profile_role": "tee"})

        two_body_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"stem_body": stem_body, "tee_body": tee_body},
        )
        two_body_snapshot = VerificationSnapshot.from_scene(two_body_scene)
        tee_expected_dimensions = {
            "width_cm": spec.tee_width_cm,
            "height_cm": spec.tee_depth_cm,
            "thickness_cm": spec.tee_thickness_cm,
        }
        tee_actual_dimensions = {
            "width_cm": tee_body["width_cm"],
            "height_cm": tee_body["height_cm"],
            "thickness_cm": tee_body["thickness_cm"],
        }
        if two_body_snapshot.body_count != 2 or tee_actual_dimensions != tee_expected_dimensions:
            raise WorkflowFailure(
                "T handle tee verification failed before combining bodies.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={
                    "scene": two_body_scene,
                    "tee_body": tee_body,
                    "expected": tee_expected_dimensions,
                    "stages": stages,
                },
                next_step="Inspect the tee sketch offset and extrusion before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": two_body_snapshot.__dict__,
                "dimensions": tee_actual_dimensions,
                "operation": "tee_new_body",
            }
        )

        combined_body = self._bridge_step(
            stage="combine_bodies",
            stages=stages,
            action=lambda: self.combine_bodies(
                target_body_token=stem_body["token"],
                tool_body_token=tee_body["token"],
            )["result"]["body"],
            partial_result={"target_body": stem_body, "tool_body": tee_body},
        )
        if combined_body["token"] != stem_body["token"]:
            raise WorkflowFailure(
                "T handle combine returned an unexpected body token.",
                stage="combine_bodies",
                classification="verification_failed",
                partial_result={"combined_body": combined_body, "expected_body": stem_body, "stages": stages},
                next_step="Inspect target-body selection before retrying the body combine.",
            )
        stages.append(
            {
                "stage": "combine_bodies",
                "status": "completed",
                "body_token": combined_body["token"],
                "tool_body_token": tee_body["token"],
            }
        )

        combined_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=combined_body,
            expected_dimensions={
                "width_cm": spec.tee_width_cm,
                "height_cm": spec.tee_depth_cm,
                "thickness_cm": total_height_cm,
            },
            failure_message="T handle combine verification failed.",
            next_step="Inspect the tee placement and body combine before retrying.",
            operation_label="combine",
        )

        socket_body, socket_snapshot = self._run_rectangle_cut_stage(
            stages=stages,
            workflow_name="t_handle_with_square_socket",
            sketch_name=spec.socket_sketch_name,
            origin_x_cm=socket_origin_x_cm,
            origin_y_cm=socket_origin_y_cm,
            width_cm=effective_square_socket_width_cm,
            height_cm=effective_square_socket_width_cm,
            cut_depth_cm=spec.socket_depth_cm,
            body=combined_body,
            expected_dimensions={
                "width_cm": spec.tee_width_cm,
                "height_cm": spec.tee_depth_cm,
                "thickness_cm": total_height_cm,
            },
            profile_role="square_socket",
            operation_label="square_socket_cut",
        )

        chamfer = self._bridge_step(
            stage="apply_chamfer",
            stages=stages,
            action=lambda: self.apply_chamfer(
                body_token=socket_body["token"],
                distance_cm=spec.top_chamfer_distance_cm,
                edge_selection="top_outer",
            )["result"]["chamfer"],
            partial_result={"body": socket_body},
        )
        if not chamfer.get("chamfer_applied"):
            raise WorkflowFailure(
                "T handle workflow: chamfer operation did not complete.",
                stage="apply_chamfer",
                classification="verification_failed",
                partial_result={"chamfer": chamfer, "stages": stages},
                next_step="Inspect the top-edge chamfer selection before retrying.",
            )
        if chamfer.get("edge_count") != 4:
            raise WorkflowFailure(
                f"T handle workflow: top chamfer.edge_count mismatch: expected 4 top edges, got {chamfer.get('edge_count')}.",
                stage="apply_chamfer",
                classification="verification_failed",
                partial_result={"chamfer": chamfer, "stages": stages},
                next_step="Inspect the top-edge chamfer selection before retrying.",
            )
        stages.append(
            {
                "stage": "apply_chamfer",
                "status": "completed",
                "body_token": socket_body["token"],
                "distance_cm": spec.top_chamfer_distance_cm,
                "edge_count": chamfer["edge_count"],
                "edge_selection": "top_outer",
            }
        )

        chamfer_body = {
            **socket_body,
            "width_cm": chamfer["width_cm"],
            "height_cm": chamfer["height_cm"],
            "thickness_cm": chamfer["thickness_cm"],
        }
        chamfer_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=chamfer_body,
            expected_dimensions={
                "width_cm": spec.tee_width_cm,
                "height_cm": spec.tee_depth_cm,
                "thickness_cm": total_height_cm,
            },
            failure_message="T handle top chamfer verification failed.",
            next_step="Inspect the top-edge chamfer and combined body before retrying.",
            operation_label="top_outer_chamfer",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(socket_body["token"], spec.output_path)["result"],
            partial_result={"body": socket_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_t_handle_with_square_socket",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": socket_body,
            "chamfer": chamfer,
            "verification": {
                "body_count": chamfer_snapshot.body_count,
                "sketch_count": chamfer_snapshot.sketch_count,
                "tee_width_cm": spec.tee_width_cm,
                "tee_depth_cm": spec.tee_depth_cm,
                "tee_thickness_cm": spec.tee_thickness_cm,
                "stem_length_cm": spec.stem_length_cm,
                "square_socket_width_cm": spec.square_socket_width_cm,
                "socket_clearance_per_side_cm": spec.socket_clearance_per_side_cm,
                "effective_square_socket_width_cm": effective_square_socket_width_cm,
                "socket_depth_cm": spec.socket_depth_cm,
                "top_chamfer_distance_cm": spec.top_chamfer_distance_cm,
                "actual_width_cm": socket_body["width_cm"],
                "actual_depth_cm": socket_body["height_cm"],
                "actual_height_cm": socket_body["thickness_cm"],
                "stem_body_count": stem_snapshot.body_count,
                "pre_combine_body_count": two_body_snapshot.body_count,
                "post_combine_body_count": combined_snapshot.body_count,
                "post_socket_cut_body_count": socket_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _verify_revolve_body(
        self,
        *,
        revolve_body: dict,
        stages: list[dict],
        expected_body_name: str,
        expected_base_diameter_cm: float,
        expected_top_diameter_cm: float,
        expected_height_cm: float,
    ) -> None:
        expected_fields = {
            "name": expected_body_name,
            "base_diameter_cm": expected_base_diameter_cm,
            "top_diameter_cm": expected_top_diameter_cm,
            "axial_height_cm": expected_height_cm,
            "axis": "y",
            "angle_deg": 360.0,
        }
        if not revolve_body.get("revolve_applied"):
            raise WorkflowFailure(
                "Revolve workflow did not report a completed revolve operation.",
                stage="revolve_profile",
                classification="verification_failed",
                partial_result={"body": revolve_body, "stages": stages},
                next_step="Inspect the revolve feature execution before retrying.",
            )
        for field_name, expected_value in expected_fields.items():
            actual_value = revolve_body.get(field_name)
            if isinstance(expected_value, float):
                matches = self._close(actual_value, expected_value)
            else:
                matches = actual_value == expected_value
            if not matches:
                raise WorkflowFailure(
                    f"Revolve workflow {field_name} mismatch.",
                    stage="revolve_profile",
                    classification="verification_failed",
                    partial_result={"body": revolve_body, "expected": expected_fields, "stages": stages},
                    next_step="Inspect the revolve axis, angle, and returned body metadata before retrying.",
                )

    def _create_base_plate_body(
        self,
        *,
        stages: list[dict],
        workflow_name: str,
        design_name: str,
        sketch_name: str,
        body_name: str,
        plane: str,
        width_cm: float,
        height_cm: float,
        thickness_cm: float,
    ) -> tuple[dict, VerificationSnapshot]:
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=plane, name=sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token, "plane": plane})

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
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=width_cm,
            expected_height_cm=height_cm,
            workflow_label=workflow_name.replace("_", " ").capitalize(),
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "profile_role": "base"})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=thickness_cm,
                body_name=body_name,
            )["result"]["body"],
            partial_result={"profile_token": selected_profile["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"], "operation": "new_body"})

        snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=body,
            expected_dimensions={"width_cm": width_cm, "height_cm": height_cm, "thickness_cm": thickness_cm},
            failure_message=f"{workflow_name.replace('_', ' ').capitalize()} base-body verification failed.",
            next_step="Inspect the base profile selection and extrusion before retrying.",
            operation_label="new_body",
        )
        return body, snapshot

    def _run_circle_cut_stage(
        self,
        *,
        stages: list[dict],
        workflow_name: str,
        sketch_name: str,
        circle_diameter_cm: float,
        center_x_cm: float,
        center_y_cm: float,
        cut_depth_cm: float,
        body: dict,
        expected_dimensions: dict[str, float],
        profile_role: str,
        operation_label: str,
        sketch_plane: str = "xy",
        sketch_offset_cm: float | None = None,
    ) -> tuple[dict, VerificationSnapshot]:
        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=sketch_plane, name=sketch_name, offset_cm=sketch_offset_cm),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": sketch_token,
                "plane": sketch_plane,
                "sketch_role": profile_role,
                **({"offset_cm": sketch_offset_cm} if sketch_offset_cm is not None else {}),
            }
        )

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=center_x_cm,
                center_y_cm=center_y_cm,
                radius_cm=circle_diameter_cm / 2.0,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "profile_role": profile_role, "diameter_cm": circle_diameter_cm})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=circle_diameter_cm,
            expected_height_cm=circle_diameter_cm,
            workflow_label=workflow_name.replace("_", " ").capitalize(),
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "profile_role": profile_role})

        cut_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=cut_depth_cm,
                body_name=profile_role,
                operation="cut",
                target_body_token=body["token"],
            )["result"]["body"],
            partial_result={"profile_token": selected_profile["token"], "body": body},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": cut_body["token"], "operation": "cut", "profile_role": profile_role})

        snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=cut_body,
            expected_dimensions=expected_dimensions,
            failure_message=f"{workflow_name.replace('_', ' ').capitalize()} {operation_label} verification failed.",
            next_step="Inspect the cut sketch and cut depth before retrying.",
            operation_label=operation_label,
        )
        return cut_body, snapshot

    def _run_rectangle_cut_stage(
        self,
        *,
        stages: list[dict],
        workflow_name: str,
        sketch_name: str,
        origin_x_cm: float,
        origin_y_cm: float,
        width_cm: float,
        height_cm: float,
        cut_depth_cm: float,
        body: dict,
        expected_dimensions: dict[str, float],
        profile_role: str,
        operation_label: str,
        sketch_offset_cm: float | None = None,
    ) -> tuple[dict, VerificationSnapshot]:
        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name=sketch_name, offset_cm=sketch_offset_cm),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": sketch_token,
                "plane": "xy",
                "sketch_role": profile_role,
                **({"offset_cm": sketch_offset_cm} if sketch_offset_cm is not None else {}),
            }
        )

        self._bridge_step(
            stage="draw_rectangle_at",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=origin_x_cm,
                origin_y_cm=origin_y_cm,
                width_cm=width_cm,
                height_cm=height_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append(
            {
                "stage": "draw_rectangle_at",
                "status": "completed",
                "profile_role": profile_role,
                "width_cm": width_cm,
                "height_cm": height_cm,
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
            expected_width_cm=width_cm,
            expected_height_cm=height_cm,
            workflow_label=workflow_name.replace("_", " ").capitalize(),
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "profile_role": profile_role})

        cut_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=cut_depth_cm,
                body_name=profile_role,
                operation="cut",
                target_body_token=body["token"],
            )["result"]["body"],
            partial_result={"profile_token": selected_profile["token"], "body": body},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": cut_body["token"], "operation": "cut", "profile_role": profile_role})

        snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=cut_body,
            expected_dimensions=expected_dimensions,
            failure_message=f"{workflow_name.replace('_', ' ').capitalize()} {operation_label} verification failed.",
            next_step="Inspect the recess sketch placement and cut depth before retrying.",
            operation_label=operation_label,
        )
        return cut_body, snapshot

    def _verify_shell_result(
        self,
        *,
        shell: dict,
        stages: list[dict],
        expected_body: dict,
        expected_wall_thickness_cm: float,
        expected_inner_width_cm: float,
        expected_inner_depth_cm: float,
        expected_inner_height_cm: float,
    ) -> None:
        if not shell.get("shell_applied"):
            raise WorkflowFailure(
                "Simple enclosure workflow: shell operation did not complete.",
                stage="apply_shell",
                classification="verification_failed",
                partial_result={"shell": shell, "stages": stages},
                next_step="Inspect the top-face selection and shell feature before retrying.",
            )
        if shell.get("body_token") != expected_body["token"]:
            raise WorkflowFailure(
                "Simple enclosure workflow: shell result referenced an unexpected body.",
                stage="apply_shell",
                classification="verification_failed",
                partial_result={"shell": shell, "body": expected_body, "stages": stages},
                next_step="Inspect the shell target body selection before retrying.",
            )
        if shell.get("removed_face_count") != 1:
            raise WorkflowFailure(
                "Simple enclosure workflow: removed_face_count mismatch.",
                stage="apply_shell",
                classification="verification_failed",
                partial_result={"shell": shell, "stages": stages},
                next_step="Inspect the face removal list before retrying.",
            )
        if shell.get("open_face") != "top":
            raise WorkflowFailure(
                "Simple enclosure workflow: open_face mismatch.",
                stage="apply_shell",
                classification="verification_failed",
                partial_result={"shell": shell, "stages": stages},
                next_step="Inspect the shell face selection before retrying.",
            )

        expected_fields = {
            "width_cm": expected_body["width_cm"],
            "height_cm": expected_body["height_cm"],
            "thickness_cm": expected_body["thickness_cm"],
            "wall_thickness_cm": expected_wall_thickness_cm,
            "inner_width_cm": expected_inner_width_cm,
            "inner_depth_cm": expected_inner_depth_cm,
            "inner_height_cm": expected_inner_height_cm,
        }
        for field_name, expected_value in expected_fields.items():
            if not self._close(shell.get(field_name), expected_value):
                raise WorkflowFailure(
                    f"Simple enclosure workflow: shell.{field_name} mismatch.",
                    stage="apply_shell",
                    classification="verification_failed",
                    partial_result={"shell": shell, "expected": expected_fields, "stages": stages},
                    next_step="Inspect shell thickness and inner cavity dimensions before retrying.",
                )

    def _verify_body_against_expected_dimensions(
        self,
        *,
        stages: list[dict],
        body: dict,
        expected_dimensions: dict[str, float],
        failure_message: str,
        next_step: str,
        operation_label: str,
    ) -> VerificationSnapshot:
        scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
        snapshot = VerificationSnapshot.from_scene(scene)
        actual_dimensions = {
            "width_cm": body["width_cm"],
            "height_cm": body["height_cm"],
            "thickness_cm": body["thickness_cm"],
        }
        dimensions_match = all(
            self._close(actual_dimensions[field_name], expected_value)
            for field_name, expected_value in expected_dimensions.items()
        )
        if snapshot.body_count != 1 or not dimensions_match:
            raise WorkflowFailure(
                failure_message,
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step=next_step,
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": snapshot.__dict__,
                "dimensions": actual_dimensions,
                "operation": operation_label,
            }
        )
        return snapshot

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

    _FILLET_EDGE_COUNT_MAX = 4

    def _create_filleted_bracket_workflow(self, spec: CreateFilletedBracketInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("filleted_bracket")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Filleted Bracket Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token, "plane": spec.plane})

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
        stages.append({"stage": "draw_l_bracket_profile", "status": "completed", "leg_thickness_cm": spec.leg_thickness_cm})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                "Filleted bracket workflow expected exactly one profile.",
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
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": profiles[0]["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        scene_before_fillet = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
        snapshot_before = VerificationSnapshot.from_scene(scene_before_fillet)
        if snapshot_before.body_count != 1:
            raise WorkflowFailure(
                "Filleted bracket workflow verification failed: expected exactly one body after extrusion.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene_before_fillet, "stages": stages},
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
                "Filleted bracket workflow verification failed: body dimensions do not match the requested values.",
                stage="verify_dimensions",
                classification="verification_failed",
                partial_result={"body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect the profile selection and extrusion distance before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": snapshot_before.__dict__, "dimensions": actual_dimensions})

        fillet = self._bridge_step(
            stage="apply_fillet",
            stages=stages,
            action=lambda: self.apply_fillet(body_token=body["token"], radius_cm=spec.fillet_radius_cm)["result"]["fillet"],
            partial_result={"body": body},
        )
        if not fillet.get("fillet_applied"):
            raise WorkflowFailure(
                "Filleted bracket workflow: fillet operation did not complete.",
                stage="apply_fillet",
                classification="verification_failed",
                partial_result={"fillet": fillet, "stages": stages},
                next_step="Inspect the body and edge selection before retrying.",
            )
        edge_count = fillet.get("edge_count", 0)
        if edge_count < 1 or edge_count > self._FILLET_EDGE_COUNT_MAX:
            raise WorkflowFailure(
                f"Filleted bracket workflow: fillet.edge_count mismatch: expected 1–{self._FILLET_EDGE_COUNT_MAX} interior edges, got {edge_count}.",
                stage="apply_fillet",
                classification="verification_failed",
                partial_result={"fillet": fillet, "stages": stages},
                next_step="Inspect the edge selection strategy and bracket geometry before retrying.",
            )
        stages.append({"stage": "apply_fillet", "status": "completed", "edge_count": edge_count, "radius_cm": spec.fillet_radius_cm})

        scene_after_fillet = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body, "fillet": fillet},
        )
        snapshot_after = VerificationSnapshot.from_scene(scene_after_fillet)
        if snapshot_after.body_count != 1:
            raise WorkflowFailure(
                "Filleted bracket workflow verification failed: expected exactly one body after filleting.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene_after_fillet, "stages": stages},
                next_step="Inspect the fillet result before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": snapshot_after.__dict__})

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], spec.output_path)["result"],
            partial_result={"body": body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_filleted_bracket",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "fillet": fillet,
            "verification": {
                "body_count": snapshot_after.body_count,
                "sketch_count": snapshot_after.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": body["width_cm"],
                "actual_height_cm": body["height_cm"],
                "actual_thickness_cm": body["thickness_cm"],
                "sketch_plane": spec.plane,
                "leg_thickness_cm": spec.leg_thickness_cm,
                "fillet_radius_cm": spec.fillet_radius_cm,
                "fillet_edge_count": edge_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_chamfered_bracket_workflow(self, spec: CreateChamferedBracketInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("chamfered_bracket")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Chamfered Bracket Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token, "plane": spec.plane})

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
        stages.append({"stage": "draw_l_bracket_profile", "status": "completed", "leg_thickness_cm": spec.leg_thickness_cm})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                "Chamfered bracket workflow expected exactly one profile.",
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
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": profiles[0]["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        scene_before_chamfer = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
        snapshot_before = VerificationSnapshot.from_scene(scene_before_chamfer)
        if snapshot_before.body_count != 1:
            raise WorkflowFailure(
                "Chamfered bracket workflow verification failed: expected exactly one body after extrusion.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene_before_chamfer, "stages": stages},
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
                "Chamfered bracket workflow verification failed: body dimensions do not match the requested values.",
                stage="verify_dimensions",
                classification="verification_failed",
                partial_result={"body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect the profile selection and extrusion distance before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": snapshot_before.__dict__, "dimensions": actual_dimensions})

        chamfer = self._bridge_step(
            stage="apply_chamfer",
            stages=stages,
            action=lambda: self.apply_chamfer(body_token=body["token"], distance_cm=spec.chamfer_distance_cm)["result"]["chamfer"],
            partial_result={"body": body},
        )
        if not chamfer.get("chamfer_applied"):
            raise WorkflowFailure(
                "Chamfered bracket workflow: chamfer operation did not complete.",
                stage="apply_chamfer",
                classification="verification_failed",
                partial_result={"chamfer": chamfer, "stages": stages},
                next_step="Inspect the body and edge selection before retrying.",
            )
        edge_count = chamfer.get("edge_count", 0)
        if edge_count < 1 or edge_count > self._FILLET_EDGE_COUNT_MAX:
            raise WorkflowFailure(
                f"Chamfered bracket workflow: chamfer.edge_count mismatch: expected 1-{self._FILLET_EDGE_COUNT_MAX} interior edges, got {edge_count}.",
                stage="apply_chamfer",
                classification="verification_failed",
                partial_result={"chamfer": chamfer, "stages": stages},
                next_step="Inspect the edge selection strategy and bracket geometry before retrying.",
            )
        stages.append({"stage": "apply_chamfer", "status": "completed", "edge_count": edge_count, "distance_cm": spec.chamfer_distance_cm})

        scene_after_chamfer = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body, "chamfer": chamfer},
        )
        snapshot_after = VerificationSnapshot.from_scene(scene_after_chamfer)
        if snapshot_after.body_count != 1:
            raise WorkflowFailure(
                "Chamfered bracket workflow verification failed: expected exactly one body after chamfering.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene_after_chamfer, "stages": stages},
                next_step="Inspect the chamfer result before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": snapshot_after.__dict__})

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], spec.output_path)["result"],
            partial_result={"body": body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_chamfered_bracket",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "chamfer": chamfer,
            "verification": {
                "body_count": snapshot_after.body_count,
                "sketch_count": snapshot_after.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": body["width_cm"],
                "actual_height_cm": body["height_cm"],
                "actual_thickness_cm": body["thickness_cm"],
                "sketch_plane": spec.plane,
                "leg_thickness_cm": spec.leg_thickness_cm,
                "chamfer_distance_cm": spec.chamfer_distance_cm,
                "chamfer_edge_count": edge_count,
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

    def _create_two_hole_plate_workflow(self, spec: CreateTwoHolePlateInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("two_hole_plate")
        hole_centers = (
            (spec.edge_offset_x_cm, spec.hole_center_y_cm),
            (spec.width_cm - spec.edge_offset_x_cm, spec.hole_center_y_cm),
        )

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Two-Hole Plate Workflow"))
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
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
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
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.height_cm, sketch_token=sketch_token),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})

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
        matching_hole_profiles = self._matching_profiles_by_dimensions(
            profiles,
            expected_width_cm=spec.hole_diameter_cm,
            expected_height_cm=spec.hole_diameter_cm,
        )
        if len(matching_hole_profiles) != 2:
            raise WorkflowFailure(
                "Two-hole plate workflow expected exactly two matching hole profiles.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected_hole_diameter_cm": spec.hole_diameter_cm,
                    "stages": stages,
                },
                next_step="Inspect the mirrored hole placement before extrusion.",
            )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=spec.width_cm,
            expected_height_cm=spec.height_cm,
            workflow_label="Two-hole plate",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "hole_count": 2})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
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
                "Two-hole plate workflow verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect profile selection and mirrored hole placement before retrying.",
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
            "workflow": "create_two_hole_plate",
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
                "hole_diameter_cm": spec.hole_diameter_cm,
                "hole_count": 2,
                "edge_offset_x_cm": spec.edge_offset_x_cm,
                "hole_center_y_cm": spec.hole_center_y_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_four_hole_mounting_plate_workflow(self, spec: CreateFourHoleMountingPlateInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("four_hole_mounting_plate")
        hole_centers = (
            (spec.edge_offset_x_cm, spec.edge_offset_y_cm),
            (spec.width_cm - spec.edge_offset_x_cm, spec.edge_offset_y_cm),
            (spec.edge_offset_x_cm, spec.height_cm - spec.edge_offset_y_cm),
            (spec.width_cm - spec.edge_offset_x_cm, spec.height_cm - spec.edge_offset_y_cm),
        )

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Four-Hole Mounting Plate Workflow"))
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
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
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
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.height_cm, sketch_token=sketch_token),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})

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
        matching_hole_profiles = self._matching_profiles_by_dimensions(
            profiles,
            expected_width_cm=spec.hole_diameter_cm,
            expected_height_cm=spec.hole_diameter_cm,
        )
        if len(matching_hole_profiles) != 4:
            raise WorkflowFailure(
                "Four-hole mounting plate workflow expected exactly four matching hole profiles.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected_hole_diameter_cm": spec.hole_diameter_cm,
                    "stages": stages,
                },
                next_step="Inspect the corner hole placement before extrusion.",
            )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=spec.width_cm,
            expected_height_cm=spec.height_cm,
            workflow_label="Four-hole mounting plate",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "hole_count": 4})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
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
                "Four-hole mounting plate workflow verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect profile selection and corner hole placement before retrying.",
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
            "workflow": "create_four_hole_mounting_plate",
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
                "hole_diameter_cm": spec.hole_diameter_cm,
                "hole_count": 4,
                "edge_offset_x_cm": spec.edge_offset_x_cm,
                "edge_offset_y_cm": spec.edge_offset_y_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_slotted_mounting_plate_workflow(self, spec: CreateSlottedMountingPlateInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("slotted_mounting_plate")
        hole_centers = (
            (spec.edge_offset_x_cm, spec.edge_offset_y_cm),
            (spec.width_cm - spec.edge_offset_x_cm, spec.edge_offset_y_cm),
            (spec.edge_offset_x_cm, spec.height_cm - spec.edge_offset_y_cm),
            (spec.width_cm - spec.edge_offset_x_cm, spec.height_cm - spec.edge_offset_y_cm),
        )
        slot_center_x_cm = spec.width_cm / 2.0
        slot_center_y_cm = spec.height_cm / 2.0

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Slotted Mounting Plate Workflow"))
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
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
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
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.height_cm, sketch_token=sketch_token),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})

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

        self._bridge_step(
            stage="draw_slot",
            stages=stages,
            action=lambda: self.draw_slot(
                center_x_cm=slot_center_x_cm,
                center_y_cm=slot_center_y_cm,
                length_cm=spec.slot_length_cm,
                width_cm=spec.slot_width_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append(
            {
                "stage": "draw_slot",
                "status": "completed",
                "slot_length_cm": spec.slot_length_cm,
                "slot_width_cm": spec.slot_width_cm,
                "slot_center_x_cm": slot_center_x_cm,
                "slot_center_y_cm": slot_center_y_cm,
            }
        )

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        matching_hole_profiles = self._matching_profiles_by_dimensions(
            profiles,
            expected_width_cm=spec.hole_diameter_cm,
            expected_height_cm=spec.hole_diameter_cm,
        )
        if len(matching_hole_profiles) != 4:
            raise WorkflowFailure(
                "Slotted mounting plate workflow expected exactly four matching hole profiles.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected_hole_diameter_cm": spec.hole_diameter_cm,
                    "stages": stages,
                },
                next_step="Inspect the corner hole placement before extrusion.",
            )
        matching_slot_profiles = self._matching_profiles_by_dimensions(
            profiles,
            expected_width_cm=spec.slot_length_cm,
            expected_height_cm=spec.slot_width_cm,
        )
        if len(matching_slot_profiles) != 1:
            raise WorkflowFailure(
                "Slotted mounting plate workflow expected exactly one matching slot profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected_slot_length_cm": spec.slot_length_cm,
                    "expected_slot_width_cm": spec.slot_width_cm,
                    "stages": stages,
                },
                next_step="Inspect the centered slot before extrusion.",
            )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=spec.width_cm,
            expected_height_cm=spec.height_cm,
            workflow_label="Slotted mounting plate",
            stages=stages,
        )
        stages.append(
            {
                "stage": "list_profiles",
                "status": "completed",
                "profile_count": len(profiles),
                "hole_count": 4,
                "slot_count": 1,
            }
        )

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
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
                "Slotted mounting plate workflow verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect profile selection, hole placement, and slot placement before retrying.",
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
            "workflow": "create_slotted_mounting_plate",
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
                "hole_diameter_cm": spec.hole_diameter_cm,
                "hole_count": 4,
                "edge_offset_x_cm": spec.edge_offset_x_cm,
                "edge_offset_y_cm": spec.edge_offset_y_cm,
                "slot_length_cm": spec.slot_length_cm,
                "slot_width_cm": spec.slot_width_cm,
                "slot_center_x_cm": slot_center_x_cm,
                "slot_center_y_cm": slot_center_y_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_slotted_mount_workflow(self, spec: CreateSlottedMountInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("slotted_mount")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Slotted Mount Workflow"))
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
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
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
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.height_cm, sketch_token=sketch_token),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})

        self._bridge_step(
            stage="draw_slot",
            stages=stages,
            action=lambda: self.draw_slot(
                center_x_cm=spec.slot_center_x_cm,
                center_y_cm=spec.slot_center_y_cm,
                length_cm=spec.slot_length_cm,
                width_cm=spec.slot_width_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append(
            {
                "stage": "draw_slot",
                "status": "completed",
                "slot_length_cm": spec.slot_length_cm,
                "slot_width_cm": spec.slot_width_cm,
            }
        )

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        matching_slot_profiles = self._matching_profiles_by_dimensions(
            profiles,
            expected_width_cm=spec.slot_length_cm,
            expected_height_cm=spec.slot_width_cm,
        )
        if len(matching_slot_profiles) != 1:
            raise WorkflowFailure(
                "Slotted mount workflow expected exactly one matching slot profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected_slot_length_cm": spec.slot_length_cm,
                    "expected_slot_width_cm": spec.slot_width_cm,
                    "stages": stages,
                },
                next_step="Inspect the slot sketch before extrusion.",
            )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=spec.width_cm,
            expected_height_cm=spec.height_cm,
            workflow_label="Slotted mount",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "slot_count": 1})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
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
                "Slotted mount workflow verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect profile selection and slot placement before retrying.",
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
            "workflow": "create_slotted_mount",
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
                "slot_length_cm": spec.slot_length_cm,
                "slot_width_cm": spec.slot_width_cm,
                "slot_center_x_cm": spec.slot_center_x_cm,
                "slot_center_y_cm": spec.slot_center_y_cm,
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

    def _select_revolve_profile_by_dimensions(
        self,
        profiles: list[dict],
        expected_width_cm: float,
        expected_height_cm: float,
        workflow_label: str,
        stages: list[dict],
    ) -> dict:
        matches = self._matching_profiles_by_dimensions(
            profiles,
            expected_width_cm=expected_width_cm,
            expected_height_cm=expected_height_cm,
        )
        if len(matches) == 1:
            return matches[0]

        # Live Fusion can report the sketched side-profile bounds for revolve input
        # as radius-by-height rather than diameter-by-height. Accept that narrower
        # profile shape during selection, then rely on revolve-body verification.
        fallback_matches = self._matching_profiles_by_dimensions(
            profiles,
            expected_width_cm=expected_width_cm / 2.0,
            expected_height_cm=expected_height_cm,
        )
        if len(fallback_matches) == 1:
            return fallback_matches[0]

        raise WorkflowFailure(
            f"{workflow_label} workflow could not determine the intended outer profile.",
            stage="list_profiles",
            classification="verification_failed",
            partial_result={
                "profiles": profiles,
                "expected_width_cm": expected_width_cm,
                "expected_height_cm": expected_height_cm,
                "accepted_revolve_fallback_width_cm": expected_width_cm / 2.0,
                "stages": stages,
            },
            next_step="Inspect the revolve sketch profile set before extrusion.",
        )

    def _matching_profiles_by_dimensions(
        self,
        profiles: list[dict],
        *,
        expected_width_cm: float,
        expected_height_cm: float,
    ) -> list[dict]:
        return [
            profile
            for profile in profiles
            if self._close(profile.get("width_cm"), expected_width_cm)
            and self._close(profile.get("height_cm"), expected_height_cm)
        ]

    def _close(self, actual: object, expected: float, tolerance: float = 1e-9) -> bool:
        try:
            number = float(actual)
        except (TypeError, ValueError):
            return False
        return abs(number - expected) <= tolerance

    def _create_cable_gland_plate_workflow(self, spec: CreateCableGlandPlateInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("cable_gland_plate")
        plate_center_x = spec.width_cm / 2.0
        plate_center_y = spec.height_cm / 2.0
        mounting_hole_centers = (
            (spec.edge_offset_x_cm, spec.edge_offset_y_cm),
            (spec.width_cm - spec.edge_offset_x_cm, spec.edge_offset_y_cm),
            (spec.edge_offset_x_cm, spec.height_cm - spec.edge_offset_y_cm),
            (spec.width_cm - spec.edge_offset_x_cm, spec.height_cm - spec.edge_offset_y_cm),
        )

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Cable Gland Plate Workflow"))
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
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
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
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.height_cm, sketch_token=sketch_token),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})

        for hole_index, (center_x_cm, center_y_cm) in enumerate(mounting_hole_centers, start=1):
            self._bridge_step(
                stage="draw_circle",
                stages=stages,
                action=lambda cx=center_x_cm, cy=center_y_cm: self.draw_circle(
                    center_x_cm=cx,
                    center_y_cm=cy,
                    radius_cm=spec.mounting_hole_diameter_cm / 2.0,
                    sketch_token=sketch_token,
                ),
                partial_result={"sketch_token": sketch_token, "hole_index": hole_index},
            )
            stages.append(
                {
                    "stage": "draw_circle",
                    "status": "completed",
                    "role": "mounting_hole",
                    "hole_index": hole_index,
                    "diameter_cm": spec.mounting_hole_diameter_cm,
                }
            )

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=plate_center_x,
                center_y_cm=plate_center_y,
                radius_cm=spec.center_hole_diameter_cm / 2.0,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append(
            {
                "stage": "draw_circle",
                "status": "completed",
                "role": "center_hole",
                "diameter_cm": spec.center_hole_diameter_cm,
            }
        )

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        matching_mounting_profiles = self._matching_profiles_by_dimensions(
            profiles,
            expected_width_cm=spec.mounting_hole_diameter_cm,
            expected_height_cm=spec.mounting_hole_diameter_cm,
        )
        if len(matching_mounting_profiles) != 4:
            raise WorkflowFailure(
                "Cable gland plate workflow expected exactly four matching mounting hole profiles.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected_mounting_hole_diameter_cm": spec.mounting_hole_diameter_cm,
                    "stages": stages,
                },
                next_step="Inspect corner hole placement before extrusion.",
            )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=spec.width_cm,
            expected_height_cm=spec.height_cm,
            workflow_label="Cable gland plate",
            stages=stages,
        )
        stages.append(
            {
                "stage": "list_profiles",
                "status": "completed",
                "profile_count": len(profiles),
                "mounting_hole_count": 4,
                "center_hole_count": 1,
            }
        )

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
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
                "Cable gland plate workflow verification failed.",
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
            "workflow": "create_cable_gland_plate",
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
                "center_hole_diameter_cm": spec.center_hole_diameter_cm,
                "mounting_hole_diameter_cm": spec.mounting_hole_diameter_cm,
                "mounting_hole_count": 4,
                "edge_offset_x_cm": spec.edge_offset_x_cm,
                "edge_offset_y_cm": spec.edge_offset_y_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_triangular_bracket_workflow(self, spec: CreateTriangularBracketInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("triangular_bracket")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Triangular Bracket Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token, "plane": spec.plane})

        # Right triangle with right angle at origin: (0,0), (base_width,0), (0,height)
        tri = self._bridge_step(
            stage="draw_triangle",
            stages=stages,
            action=lambda: self.draw_triangle(
                x1_cm=0.0, y1_cm=0.0,
                x2_cm=spec.base_width_cm, y2_cm=0.0,
                x3_cm=0.0, y3_cm=spec.height_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({
            "stage": "draw_triangle",
            "status": "completed",
            "base_width_cm": spec.base_width_cm,
            "height_cm": spec.height_cm,
            "vertices": tri["result"]["vertices"],
        })

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=spec.base_width_cm,
            expected_height_cm=spec.height_cm,
            workflow_label="Triangular bracket",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
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
            "width_cm": spec.base_width_cm,
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
                "Triangular bracket workflow verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect triangle profile selection before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": snapshot.__dict__, "dimensions": actual_dimensions})

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], spec.output_path)["result"],
            partial_result={"body": body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_triangular_bracket",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "verification": {
                "body_count": snapshot.body_count,
                "sketch_count": snapshot.sketch_count,
                "expected_width_cm": spec.base_width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": body["width_cm"],
                "actual_height_cm": body["height_cm"],
                "actual_thickness_cm": body["thickness_cm"],
                "sketch_plane": spec.plane,
            },
            "export_triangular_bracket": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_l_bracket_with_gusset_workflow(self, spec: CreateLBracketWithGussetInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("l_bracket_with_gusset")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("L-Bracket With Gusset Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        # --- step 1: L-bracket body ---
        bracket_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
        )
        bracket_sketch_token = bracket_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": bracket_sketch_token, "sketch_role": "bracket", "plane": spec.plane})

        self._bridge_step(
            stage="draw_l_bracket_profile",
            stages=stages,
            action=lambda: self.draw_l_bracket_profile(
                width_cm=spec.width_cm,
                height_cm=spec.height_cm,
                leg_thickness_cm=spec.leg_thickness_cm,
                sketch_token=bracket_sketch_token,
            ),
            partial_result={"sketch_token": bracket_sketch_token},
        )
        stages.append({"stage": "draw_l_bracket_profile", "status": "completed"})

        bracket_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(bracket_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": bracket_sketch_token},
        )
        bracket_profile = self._select_profile_by_dimensions(
            bracket_profiles,
            expected_width_cm=spec.width_cm,
            expected_height_cm=spec.height_cm,
            workflow_label="L-bracket",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(bracket_profiles), "profile_role": "bracket"})

        bracket_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=bracket_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": bracket_profile["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": bracket_body["token"], "profile_role": "bracket"})

        scene1 = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": bracket_body},
        )
        snap1 = VerificationSnapshot.from_scene(scene1)
        if snap1.body_count != 1:
            raise WorkflowFailure(
                "L-bracket body verification failed: expected 1 body after bracket extrusion.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene1, "stages": stages},
                next_step="Inspect L-bracket profile before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": snap1.__dict__, "verification_role": "bracket"})

        # --- step 2: gusset body in inner corner ---
        # Inner corner of the L is at (leg_thickness, leg_thickness).
        # Gusset triangle: right angle at inner corner, legs of length gusset_size.
        gx = spec.leg_thickness_cm
        gy = spec.leg_thickness_cm
        gusset_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=f"{spec.sketch_name} Gusset"),
        )
        gusset_sketch_token = gusset_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": gusset_sketch_token, "sketch_role": "gusset", "plane": spec.plane})

        self._bridge_step(
            stage="draw_triangle",
            stages=stages,
            action=lambda: self.draw_triangle(
                x1_cm=gx, y1_cm=gy,
                x2_cm=gx + spec.gusset_size_cm, y2_cm=gy,
                x3_cm=gx, y3_cm=gy + spec.gusset_size_cm,
                sketch_token=gusset_sketch_token,
            ),
            partial_result={"sketch_token": gusset_sketch_token},
        )
        stages.append({
            "stage": "draw_triangle",
            "status": "completed",
            "gusset_size_cm": spec.gusset_size_cm,
            "inner_corner_x_cm": gx,
            "inner_corner_y_cm": gy,
        })

        gusset_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(gusset_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": gusset_sketch_token},
        )
        gusset_profile = self._select_profile_by_dimensions(
            gusset_profiles,
            expected_width_cm=spec.gusset_size_cm,
            expected_height_cm=spec.gusset_size_cm,
            workflow_label="Gusset triangle",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(gusset_profiles), "profile_role": "gusset"})

        gusset_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=gusset_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name=f"{spec.body_name} Gusset",
                operation="new_body",
            )["result"]["body"],
            partial_result={"profile_token": gusset_profile["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": gusset_body["token"], "profile_role": "gusset"})

        scene2 = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": gusset_body},
        )
        snap2 = VerificationSnapshot.from_scene(scene2)
        if snap2.body_count != 2:
            raise WorkflowFailure(
                "Gusset verification failed: expected 2 bodies before combine.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene2, "stages": stages},
                next_step="Inspect gusset triangle placement — must overlap with bracket body.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": snap2.__dict__, "verification_role": "gusset"})

        # --- step 3: combine gusset into bracket ---
        combined = self._bridge_step(
            stage="combine_bodies",
            stages=stages,
            action=lambda: self.combine_bodies(
                target_body_token=bracket_body["token"],
                tool_body_token=gusset_body["token"],
            )["result"],
            partial_result={"bracket_body": bracket_body, "gusset_body": gusset_body},
        )
        combined_body = combined["body"]
        stages.append({"stage": "combine_bodies", "status": "completed", "body_token": combined_body["token"]})

        scene3 = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": combined_body},
        )
        snap3 = VerificationSnapshot.from_scene(scene3)
        expected_dimensions = {
            "width_cm": spec.width_cm,
            "height_cm": spec.height_cm,
            "thickness_cm": spec.thickness_cm,
        }
        actual_dimensions = {
            "width_cm": combined_body["width_cm"],
            "height_cm": combined_body["height_cm"],
            "thickness_cm": combined_body["thickness_cm"],
        }
        if snap3.body_count != 1 or actual_dimensions != expected_dimensions:
            raise WorkflowFailure(
                "L-bracket with gusset combine verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene3, "body": combined_body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect gusset size and placement — gusset must fully intersect the bracket body.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": snap3.__dict__, "dimensions": actual_dimensions, "verification_role": "combined"})

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(combined_body["token"], spec.output_path)["result"],
            partial_result={"body": combined_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_l_bracket_with_gusset",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": combined_body,
            "verification": {
                "body_count": snap3.body_count,
                "sketch_count": snap3.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": combined_body["width_cm"],
                "actual_height_cm": combined_body["height_cm"],
                "actual_thickness_cm": combined_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "gusset_size_cm": spec.gusset_size_cm,
                "leg_thickness_cm": spec.leg_thickness_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }
