"""Brackets workflow family for ParamAItric.

Includes bracket, filleted_bracket, chamfered_bracket, mounting_bracket, two_hole_mounting_bracket, triangular_bracket, l_bracket_with_gusset.
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
    CreateTriangularBracketInput,
    CreateLBracketWithGussetInput,
    VerificationSnapshot,
)

if TYPE_CHECKING:
    from mcp_server.workflow_registry import WorkflowRegistry


class BracketWorkflowsMixin:
    """Mixin providing brackets-related CAD workflows."""

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
        """Create a filleted bracket."""
        spec = CreateFilletedBracketInput.from_payload(payload)
        return self._create_filleted_bracket_workflow(spec)

    def create_chamfered_bracket(self, payload: dict) -> dict:
        """Create a chamfered bracket."""
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

    def create_triangular_bracket(self, payload: dict) -> dict:
        """Create a triangular bracket."""
        spec = CreateTriangularBracketInput.from_payload(payload)
        return self._create_triangular_bracket_workflow(spec)

    def create_l_bracket_with_gusset(self, payload: dict) -> dict:
        """Create a l bracket with gusset."""
        spec = CreateLBracketWithGussetInput.from_payload(payload)
        return self._create_l_bracket_with_gusset_workflow(spec)


    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------


    # -------------------------------------------------------------------------
    # Abstract methods provided by other mixins
    # -------------------------------------------------------------------------

    def _bridge_step(self, *, stage, stages, action, partial_result=None, next_step=None):
        """Provided by WorkflowMixin."""
        raise NotImplementedError

