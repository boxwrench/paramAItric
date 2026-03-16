"""Cylinder and revolve workflow family for ParamAItric.

Includes cylinders, tubes, revolved solids, bushings, and couplers.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CreateCylinderInput,
    CreateTubeInput,
    CreateRevolveInput,
    CreateTaperedKnobBlankInput,
    CreateFlangedBushingInput,
    CreateShaftCouplerInput,
    CreatePipeClampHalfInput,
    CreateTubeMountingPlateInput,
    CreateTHandleWithSquareSocketInput,
    VerificationSnapshot,
)

if TYPE_CHECKING:
    from mcp_server.workflow_registry import WorkflowRegistry


class CylinderWorkflowsMixin:
    """Mixin providing cylinder and revolve-related CAD workflows.

    Workflows in this family:
    - create_cylinder: Cylindrical solid
    - create_tube: Hollow tube with bore
    - create_revolve: Revolved tapered solid
    - create_tapered_knob_blank: Tapered knob with stem socket
    - create_flanged_bushing: Bushing with flange and axial bore
    - create_shaft_coupler: Coupler with axial and cross-pin holes
    - create_pipe_clamp_half: Half clamp with saddle and bolt holes
    - create_tube_mounting_plate: Wall plate with tube socket
    - create_t_handle_with_square_socket: T-handle with square valve socket
    """

    def create_cylinder(self, payload: dict) -> dict:
        """Create a cylindrical solid."""
        spec = CreateCylinderInput.from_payload(payload)
        return self._create_cylinder_workflow(spec)

    def create_tube(self, payload: dict) -> dict:
        """Create a hollow tube with centered bore cut."""
        spec = CreateTubeInput.from_payload(payload)
        return self._create_tube_workflow(spec)

    def create_revolve(self, payload: dict) -> dict:
        """Create a revolved solid from a tapered side profile."""
        spec = CreateRevolveInput.from_payload(payload)
        return self._create_revolve_workflow(spec)

    def create_tapered_knob_blank(self, payload: dict) -> dict:
        """Create a tapered knob blank with centered stem socket."""
        spec = CreateTaperedKnobBlankInput.from_payload(payload)
        return self._create_tapered_knob_blank_workflow(spec)

    def create_flanged_bushing(self, payload: dict) -> dict:
        """Create a flanged bushing with axial bore."""
        spec = CreateFlangedBushingInput.from_payload(payload)
        return self._create_flanged_bushing_workflow(spec)

    def create_shaft_coupler(self, payload: dict) -> dict:
        """Create a shaft coupler with axial bore and orthogonal cross-pin hole."""
        spec = CreateShaftCouplerInput.from_payload(payload)
        return self._create_shaft_coupler_workflow(spec)

    def create_pipe_clamp_half(self, payload: dict) -> dict:
        """Create a half clamp body with non-XY pipe saddle cut and mirrored bolt holes."""
        spec = CreatePipeClampHalfInput.from_payload(payload)
        return self._create_pipe_clamp_half_workflow(spec)

    def create_tube_mounting_plate(self, payload: dict) -> dict:
        """Create a wall-mount plate with tube socket joined into one body."""
        spec = CreateTubeMountingPlateInput.from_payload(payload)
        return self._create_tube_mounting_plate_workflow(spec)

    def create_t_handle_with_square_socket(self, payload: dict) -> dict:
        """Create a T-handle with square valve socket and comfort chamfer."""
        spec = CreateTHandleWithSquareSocketInput.from_payload(payload)
        return self._create_t_handle_with_square_socket_workflow(spec)

    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------

    def _create_cylinder_workflow(self, spec: CreateCylinderInput) -> dict:
        """Core cylinder workflow: circle sketch extruded to cylinder."""
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
        """Core tube workflow: outer cylinder with bore cut."""
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

        # Bore cut stage - inline instead of using helper
        bore_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.bore_sketch_name),
        )
        bore_sketch_token = bore_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": bore_sketch_token, "plane": spec.plane, "sketch_role": "tube_bore"})

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=outer_radius_cm,
                center_y_cm=outer_radius_cm,
                radius_cm=spec.inner_diameter_cm / 2.0,
                sketch_token=bore_sketch_token,
            ),
            partial_result={"sketch_token": bore_sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "profile_role": "tube_bore", "diameter_cm": spec.inner_diameter_cm})

        bore_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(bore_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": bore_sketch_token},
        )
        selected_bore_profile = self._select_profile_by_dimensions(
            bore_profiles,
            expected_width_cm=spec.inner_diameter_cm,
            expected_height_cm=spec.inner_diameter_cm,
            workflow_label="Tube",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(bore_profiles), "profile_role": "tube_bore"})

        tube_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_bore_profile["token"],
                distance_cm=spec.height_cm,
                body_name="tube_bore",
                operation="cut",
                target_body_token=outer_body["token"],
            )["result"]["body"],
            partial_result={"profile_token": selected_bore_profile["token"], "body": outer_body},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": tube_body["token"], "operation": "cut", "profile_role": "tube_bore"})

        tube_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=tube_body,
            expected_dimensions={
                "width_cm": spec.outer_diameter_cm,
                "height_cm": spec.outer_diameter_cm,
                "thickness_cm": spec.height_cm,
            },
            failure_message="Tube tube_bore_cut verification failed.",
            next_step="Inspect the cut sketch and cut depth before retrying.",
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
        """Core revolve workflow: tapered profile revolved around Y-axis."""
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
        """Tapered knob workflow: revolved body with stem socket cut."""
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
        """Flanged bushing workflow: shaft + flange revolve, combine, bore cut."""
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

    def _create_shaft_coupler_workflow(self, spec: CreateShaftCouplerInput) -> dict:
        """Shaft coupler workflow: cylinder with cross-pin hole and axial bore."""
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

    def _create_pipe_clamp_half_workflow(self, spec: CreatePipeClampHalfInput) -> dict:
        """Pipe clamp half workflow: base plate + saddle cut + bolt holes."""
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

    def _create_t_handle_with_square_socket_workflow(self, spec: CreateTHandleWithSquareSocketInput) -> dict:
        """T-handle workflow: stem + tee combine, square socket cut, chamfer."""
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

    def _create_tube_mounting_plate_workflow(self, spec: CreateTubeMountingPlateInput) -> dict:
        """Tube mounting plate workflow: plate + holes + tube socket combined."""
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

    # -------------------------------------------------------------------------
    # Cylinder helper methods
    # -------------------------------------------------------------------------

    def _create_revolved_body(
        self,
        stages: list[dict],
        workflow_name: str,
        design_name: str,
        sketch_name: str,
        body_name: str,
        base_diameter_cm: float,
        top_diameter_cm: float,
        height_cm: float,
        expected_dimensions: dict,
    ) -> tuple[dict, VerificationSnapshot]:
        """Create a revolved body from a tapered profile.

        Returns:
            Tuple of (revolved_body, verification_snapshot)
        """
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
                f"{workflow_name} workflow did not start from a clean design state.",
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
        selected_profile = self._select_revolve_profile_by_dimensions(
            profiles,
            expected_base_diameter_cm=base_diameter_cm,
            expected_top_diameter_cm=top_diameter_cm,
            expected_height_cm=height_cm,
            workflow_label=workflow_name,
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="revolve_profile",
            stages=stages,
            action=lambda: self.revolve_profile(profile_token=selected_profile["token"], body_name=body_name)["result"]["body"],
            partial_result={"profile_token": selected_profile["token"]},
        )
        self._verify_revolve_body(
            revolve_body=body,
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
                "body_token": body["token"],
                "base_diameter_cm": body["base_diameter_cm"],
                "top_diameter_cm": body["top_diameter_cm"],
                "height_cm": body["axial_height_cm"],
                "axis": body["axis"],
            }
        )

        scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
        snapshot = VerificationSnapshot.from_scene(scene)
        if snapshot.body_count != 1:
            raise WorkflowFailure(
                f"{workflow_name} workflow verification failed: expected exactly one body.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene, "stages": stages},
                next_step="Preserve the partial model and inspect body creation before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": snapshot.__dict__})

        return body, snapshot

    def _verify_revolve_body(
        self,
        revolve_body: dict,
        stages: list,
        expected_body_name: str,
        expected_base_diameter_cm: float,
        expected_top_diameter_cm: float,
        expected_height_cm: float,
    ) -> None:
        """Verify a revolved body has the expected dimensions.

        Raises WorkflowFailure if verification fails.
        """
        max_diameter_cm = max(expected_base_diameter_cm, expected_top_diameter_cm)
        expected_dimensions = {
            "base_diameter_cm": expected_base_diameter_cm,
            "top_diameter_cm": expected_top_diameter_cm,
            "axial_height_cm": expected_height_cm,
            "width_cm": max_diameter_cm,
            "height_cm": expected_height_cm,
            "thickness_cm": max_diameter_cm,
        }
        actual_dimensions = {
            "base_diameter_cm": revolve_body.get("base_diameter_cm"),
            "top_diameter_cm": revolve_body.get("top_diameter_cm"),
            "axial_height_cm": revolve_body.get("axial_height_cm"),
            "width_cm": revolve_body.get("width_cm"),
            "height_cm": revolve_body.get("height_cm"),
            "thickness_cm": revolve_body.get("thickness_cm"),
        }

        mismatches = []
        for key, expected in expected_dimensions.items():
            actual = actual_dimensions.get(key)
            if actual is None:
                mismatches.append(f"{key}: missing in response")
            elif abs(actual - expected) > 0.01:
                mismatches.append(f"{key}: expected {expected}, got {actual}")

        if mismatches:
            raise WorkflowFailure(
                f"Revolve body '{expected_body_name}' verification failed: " + "; ".join(mismatches),
                stage="verify_revolve_body",
                classification="verification_failed",
                partial_result={
                    "body": revolve_body,
                    "expected": expected_dimensions,
                    "actual": actual_dimensions,
                    "stages": stages,
                },
                next_step="Inspect the revolve profile sketch and revolve parameters before retrying.",
            )

    def _select_revolve_profile_by_dimensions(
        self,
        profiles: list[dict],
        expected_base_diameter_cm: float,
        expected_top_diameter_cm: float,
        expected_height_cm: float,
        workflow_label: str,
        stages: list,
    ) -> dict:
        """Select a revolve profile by its expected dimensions.

        Returns:
            The matching profile dict

        Raises:
            WorkflowFailure if no matching profile is found or multiple match
        """
        max_diameter_cm = max(expected_base_diameter_cm, expected_top_diameter_cm)
        expected_width_cm = max_diameter_cm
        expected_profile_height_cm = expected_height_cm

        matching_profiles = [
            p
            for p in profiles
            if self._close(p.get("width_cm"), expected_width_cm)
            and self._close(p.get("height_cm"), expected_profile_height_cm)
        ]

        if len(matching_profiles) == 0:
            raise WorkflowFailure(
                f"{workflow_label} workflow: no profile matching expected revolve dimensions.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected_width_cm": expected_width_cm,
                    "expected_height_cm": expected_profile_height_cm,
                    "stages": stages,
                },
                next_step="Inspect the revolve profile sketch dimensions before retrying.",
            )

        if len(matching_profiles) > 1:
            raise WorkflowFailure(
                f"{workflow_label} workflow: multiple profiles match expected revolve dimensions.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "matching_profiles": matching_profiles,
                    "expected_width_cm": expected_width_cm,
                    "expected_height_cm": expected_profile_height_cm,
                    "stages": stages,
                },
                next_step="Remove ambiguous sketch geometry before retrying.",
            )

        return matching_profiles[0]

    # -------------------------------------------------------------------------
    # Abstract methods provided by other mixins
    # -------------------------------------------------------------------------

    def _bridge_step(self, *, stage, stages, action, partial_result=None, next_step=None):
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def new_design(self, name: str = "ParamAItric Design") -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def get_scene_info(self) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_circle(self, center_x_cm: float, center_y_cm: float, radius_cm: float, sketch_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def list_profiles(self, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, **kwargs) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def export_stl(self, body_token: str, output_path: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_revolve_profile(self, base_diameter_cm: float, top_diameter_cm: float, height_cm: float, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def revolve_profile(self, profile_token: str, body_name: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def combine_bodies(self, target_body_token: str, tool_body_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def _close(self, a: float, b: float, tolerance: float = 0.01) -> bool:
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def _select_profile_by_dimensions(
        self, profiles: list[dict], expected_width_cm: float, expected_height_cm: float, workflow_label: str, stages: list
    ) -> dict:
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def _verify_body_against_expected_dimensions(
        self,
        stages: list,
        body: dict,
        expected_dimensions: dict,
        failure_message: str,
        next_step: str,
        operation_label: str,
    ) -> VerificationSnapshot:
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def _run_circle_cut_stage(
        self,
        stages: list,
        workflow_name: str,
        sketch_name: str,
        circle_diameter_cm: float,
        center_x_cm: float,
        center_y_cm: float,
        cut_depth_cm: float,
        body: dict,
        expected_dimensions: dict,
        profile_role: str,
        operation_label: str,
        sketch_plane: str = "xy",
        sketch_offset_cm: float = 0.0,
    ) -> tuple[dict, VerificationSnapshot]:
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def _run_rectangle_cut_stage(
        self,
        stages: list,
        workflow_name: str,
        sketch_name: str,
        origin_x_cm: float,
        origin_y_cm: float,
        width_cm: float,
        height_cm: float,
        cut_depth_cm: float,
        body: dict,
        expected_dimensions: dict,
        profile_role: str,
        operation_label: str,
    ) -> tuple[dict, VerificationSnapshot]:
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def _create_base_plate_body(
        self,
        stages: list,
        workflow_name: str,
        design_name: str,
        sketch_name: str,
        body_name: str,
        plane: str,
        width_cm: float,
        height_cm: float,
        thickness_cm: float,
    ) -> tuple[dict, VerificationSnapshot]:
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def draw_rectangle_at(
        self, origin_x_cm: float, origin_y_cm: float, width_cm: float, height_cm: float, sketch_token: str
    ) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_rectangle(self, width_cm: float, height_cm: float, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def apply_chamfer(self, body_token: str, distance_cm: float, edge_selection: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError
