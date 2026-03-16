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

    def _create_filleted_bracket_workflow(self, spec):
        """To be implemented - filleted bracket with edge fillets."""
        raise NotImplementedError("Filleted bracket workflow not yet migrated")

    def _create_chamfered_bracket_workflow(self, spec):
        """To be implemented - chamfered bracket workflow."""
        raise NotImplementedError("Chamfered bracket workflow not yet migrated")

    def _create_mounting_bracket_workflow(self, spec, workflow_name, workflow_call_name, design_name, sketch_name, body_name, hole_centers):
        """To be implemented - mounting bracket with holes."""
        raise NotImplementedError("Mounting bracket workflow not yet migrated")

    def _create_triangular_bracket_workflow(self, spec):
        """To be implemented - flat triangular bracket."""
        raise NotImplementedError("Triangular bracket workflow not yet migrated")

    def _create_l_bracket_with_gusset_workflow(self, spec):
        """To be implemented - L-bracket with gusset."""
        raise NotImplementedError("Gusset bracket workflow not yet migrated")
