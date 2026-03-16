"""Bracket workflow family for ParamAItric.

Includes L-brackets, filleted brackets, chamfered brackets, mounting brackets,
and gusseted brackets.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CreateBracketInput,
    CreateFilletedBracketInput,
    CreateChamferedBracketInput,
    CreateMountingBracketInput,
    CreateTwoHoleMountingBracketInput,
    CreateLBracketWithGussetInput,
    CreateTriangularBracketInput,
    VerificationSnapshot,
)

if TYPE_CHECKING:
    pass


class BracketWorkflowsMixin:
    """Mixin providing bracket-related CAD workflows.

    Workflows in this family:
    - create_bracket: Simple L-bracket
    - create_filleted_bracket: L-bracket with edge fillets
    - create_chamfered_bracket: L-bracket with chamfers
    - create_mounting_bracket: L-bracket with mounting holes
    - create_two_hole_mounting_bracket: L-bracket with two holes
    - create_l_bracket_with_gusset: L-bracket with triangular gusset
    - create_triangular_bracket: Flat right-triangle bracket
    """

    _FILLET_EDGE_COUNT_MAX = 4

    # -------------------------------------------------------------------------
    # Public API methods
    # -------------------------------------------------------------------------

    def create_bracket(self, payload: dict) -> dict:
        """Create an L-bracket: sketch an L-profile, extrude, verify, export STL."""
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
        """Create an L-bracket with edge fillets applied after extrusion."""
        spec = CreateFilletedBracketInput.from_payload(payload)
        return self._create_filleted_bracket_workflow(spec)

    def create_chamfered_bracket(self, payload: dict) -> dict:
        """Create an L-bracket with equal-distance chamfers applied after extrusion."""
        spec = CreateChamferedBracketInput.from_payload(payload)
        return self._create_chamfered_bracket_workflow(spec)

    def create_mounting_bracket(self, payload: dict) -> dict:
        """Create an L-bracket with one mounting hole cut through the vertical leg."""
        spec = CreateMountingBracketInput.from_payload(payload)
        return self._create_mounting_bracket_workflow(
            spec=spec,
            workflow_name="mounting_bracket",
            workflow_call_name="create_mounting_bracket",
            design_name="Mounting Bracket Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            hole_centers=[(spec.hole_center_x_cm, spec.hole_center_y_cm)],
        )

    def create_two_hole_mounting_bracket(self, payload: dict) -> dict:
        """Create an L-bracket with two mounting holes cut through the vertical leg."""
        spec = CreateTwoHoleMountingBracketInput.from_payload(payload)
        return self._create_mounting_bracket_workflow(
            spec=spec,
            workflow_name="two_hole_mounting_bracket",
            workflow_call_name="create_two_hole_mounting_bracket",
            design_name="Two-Hole Mounting Bracket Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            hole_centers=[
                (spec.first_hole_center_x_cm, spec.first_hole_center_y_cm),
                (spec.second_hole_center_x_cm, spec.second_hole_center_y_cm),
            ],
        )

    def create_triangular_bracket(self, payload: dict) -> dict:
        """Create a flat right-triangle plate extruded to a given thickness."""
        spec = CreateTriangularBracketInput.from_payload(payload)
        return self._create_triangular_bracket_workflow(spec)

    def create_l_bracket_with_gusset(self, payload: dict) -> dict:
        """Create an L-bracket with an internal right-triangle gusset for reinforcement."""
        spec = CreateLBracketWithGussetInput.from_payload(payload)
        return self._create_l_bracket_with_gusset_workflow(spec)

    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------

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
        """Core L-bracket workflow implementation."""
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get(workflow_name)
        workflow_label = workflow_name.capitalize()

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design(design_name))
        stages.append({"stage": "new_design", "status": "completed"})

        # Verify clean state
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

        # Create sketch
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

        # Draw L-bracket profile
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

        # List profiles
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

        # Extrude
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

        # Verify
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
                f"{workflow_label} workflow verification failed: body dimensions do not match.",
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

        # Export
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

    # -------------------------------------------------------------------------
    # Abstract methods provided by other mixins
    # -------------------------------------------------------------------------

    def _bridge_step(self, *, stage, stages, action, partial_result=None, next_step=None):
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def draw_circle(self, center_x_cm, center_y_cm, radius_cm, sketch_token=None):
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def apply_fillet(self, body_token, radius_cm):
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def apply_chamfer(self, body_token, distance_cm, edge_selection=None):
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_triangle(self, x1_cm, y1_cm, x2_cm, y2_cm, x3_cm, y3_cm, sketch_token=None):
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def combine_bodies(self, target_body_token, tool_body_token):
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def _create_filleted_bracket_workflow(self, spec: CreateFilletedBracketInput) -> dict:
        """Filleted bracket workflow: L-bracket with edge fillets applied after extrusion."""
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
                f"Filleted bracket workflow: fillet.edge_count mismatch: expected 1-{self._FILLET_EDGE_COUNT_MAX} interior edges, got {edge_count}.",
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
        """Chamfered bracket workflow: L-bracket with chamfers applied after extrusion."""
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
        """Mounting bracket workflow: L-bracket with mounting holes cut through vertical leg."""
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

    def _create_triangular_bracket_workflow(self, spec: CreateTriangularBracketInput) -> dict:
        """Triangular bracket workflow: flat right-triangle plate extruded to thickness."""
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
        """L-bracket with gusset workflow: L-bracket with triangular gusset combined for reinforcement."""
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
                next_step="Inspect gusset triangle placement - must overlap with bracket body.",
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
                next_step="Inspect gusset size and placement - gusset must fully intersect the bracket body.",
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

    def draw_l_bracket_profile(self, width_cm: float, height_cm: float, leg_thickness_cm: float, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_circle(self, center_x_cm: float, center_y_cm: float, radius_cm: float, sketch_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_triangle(self, x1_cm: float, y1_cm: float, x2_cm: float, y2_cm: float, x3_cm: float, y3_cm: float, sketch_token: str | None = None) -> dict:
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

    def apply_fillet(self, body_token: str, radius_cm: float) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def apply_chamfer(self, body_token: str, distance_cm: float, edge_selection: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def combine_bodies(self, target_body_token: str, tool_body_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def _select_profile_by_dimensions(
        self, profiles: list[dict], expected_width_cm: float, expected_height_cm: float, workflow_label: str, stages: list
    ) -> dict:
        """Provided by WorkflowMixin."""
        raise NotImplementedError

