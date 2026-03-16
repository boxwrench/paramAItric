"""Cylinders workflow family for ParamAItric.

Includes cylinder, tube, revolve, tapered_knob_blank, flanged_bushing, shaft_coupler, pipe_clamp_half, tube_mounting_plate, t_handle_with_square_socket.
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
    """Mixin providing cylinders-related CAD workflows."""

    def create_cylinder(self, payload: dict) -> dict:
        """Create a cylinder."""
        spec = CreateCylinderInput.from_payload(payload)
        return self._create_cylinder_workflow(spec)

    def create_tube(self, payload: dict) -> dict:
        """Create a tube."""
        spec = CreateTubeInput.from_payload(payload)
        return self._create_tube_workflow(spec)

    def create_revolve(self, payload: dict) -> dict:
        """Create a revolve."""
        spec = CreateRevolveInput.from_payload(payload)
        return self._create_revolve_workflow(spec)

    def create_tapered_knob_blank(self, payload: dict) -> dict:
        """Create a tapered knob blank."""
        spec = CreateTaperedKnobBlankInput.from_payload(payload)
        return self._create_tapered_knob_blank_workflow(spec)

    def create_flanged_bushing(self, payload: dict) -> dict:
        """Create a flanged bushing."""
        spec = CreateFlangedBushingInput.from_payload(payload)
        return self._create_flanged_bushing_workflow(spec)

    def create_shaft_coupler(self, payload: dict) -> dict:
        """Create a shaft coupler."""
        spec = CreateShaftCouplerInput.from_payload(payload)
        return self._create_shaft_coupler_workflow(spec)

    def create_pipe_clamp_half(self, payload: dict) -> dict:
        """Create a pipe clamp half."""
        spec = CreatePipeClampHalfInput.from_payload(payload)
        return self._create_pipe_clamp_half_workflow(spec)

    def create_tube_mounting_plate(self, payload: dict) -> dict:
        """Create a tube mounting plate."""
        spec = CreateTubeMountingPlateInput.from_payload(payload)
        return self._create_tube_mounting_plate_workflow(spec)

    def create_t_handle_with_square_socket(self, payload: dict) -> dict:
        """Create a t handle with square socket."""
        spec = CreateTHandleWithSquareSocketInput.from_payload(payload)
        return self._create_t_handle_with_square_socket_workflow(spec)


    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------


    # -------------------------------------------------------------------------
    # Abstract methods provided by other mixins
    # -------------------------------------------------------------------------

    def _bridge_step(self, *, stage, stages, action, partial_result=None, next_step=None):
        """Provided by WorkflowMixin."""
        raise NotImplementedError

