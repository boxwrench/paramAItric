"""Plates workflow family for ParamAItric.

Includes spacer, plate_with_hole, two_hole_plate, four_hole_mounting_plate, slotted_mounting_plate, counterbored_plate, recessed_mount, slotted_mount, cable_gland_plate, slotted_flex_panel.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CreateSpacerInput,
    CreatePlateWithHoleInput,
    CreateTwoHolePlateInput,
    CreateFourHoleMountingPlateInput,
    CreateSlottedMountingPlateInput,
    CreateCounterboredPlateInput,
    CreateRecessedMountInput,
    CreateSlottedMountInput,
    CreateCableGlandPlateInput,
    CreateSlottedFlexPanelInput,
    VerificationSnapshot,
)

if TYPE_CHECKING:
    from mcp_server.workflow_registry import WorkflowRegistry


class PlateWorkflowsMixin:
    """Mixin providing plates-related CAD workflows."""

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

    def create_two_hole_plate(self, payload: dict) -> dict:
        """Create a two hole plate."""
        spec = CreateTwoHolePlateInput.from_payload(payload)
        return self._create_two_hole_plate_workflow(spec)

    def create_slotted_mount(self, payload: dict) -> dict:
        """Create a slotted mount."""
        spec = CreateSlottedMountInput.from_payload(payload)
        return self._create_slotted_mount_workflow(spec)

    def create_counterbored_plate(self, payload: dict) -> dict:
        """Create a counterbored plate."""
        spec = CreateCounterboredPlateInput.from_payload(payload)
        return self._create_counterbored_plate_workflow(spec)

    def create_four_hole_mounting_plate(self, payload: dict) -> dict:
        """Create a four hole mounting plate."""
        spec = CreateFourHoleMountingPlateInput.from_payload(payload)
        return self._create_four_hole_mounting_plate_workflow(spec)

    def create_slotted_mounting_plate(self, payload: dict) -> dict:
        """Create a slotted mounting plate."""
        spec = CreateSlottedMountingPlateInput.from_payload(payload)
        return self._create_slotted_mounting_plate_workflow(spec)

    def create_recessed_mount(self, payload: dict) -> dict:
        """Create a recessed mount."""
        spec = CreateRecessedMountInput.from_payload(payload)
        return self._create_recessed_mount_workflow(spec)

    def create_cable_gland_plate(self, payload: dict) -> dict:
        """Create a cable gland plate."""
        spec = CreateCableGlandPlateInput.from_payload(payload)
        return self._create_cable_gland_plate_workflow(spec)

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


    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Shared helper methods
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Abstract methods provided by other mixins
    # -------------------------------------------------------------------------

    def _bridge_step(self, *, stage, stages, action, partial_result=None, next_step=None):
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_circle(self, center_x_cm: float, center_y_cm: float, radius_cm: float, sketch_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_rectangle(self, width_cm: float, height_cm: float, sketch_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def export_stl(self, body_token: str, output_path: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, **kwargs) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def get_scene_info(self) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def list_profiles(self, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def new_design(self, name: str = "ParamAItric Design") -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

