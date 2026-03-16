"""Specialty workflow family for ParamAItric.

Includes strut channel brackets, ratchet wheels, wire clamps, and other specialized parts.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server.schemas import (
    CreateStrutChannelBracketInput,
    CreateRatchetWheelInput,
    CreateWireClampInput,
)

if TYPE_CHECKING:
    pass


class SpecialtyWorkflowsMixin:
    """Mixin providing specialty CAD workflows.

    Workflows in this family:
    - create_strut_channel_bracket: McMaster-style strut channel bracket
    - create_ratchet_wheel: Ratchet wheel with asymmetric teeth
    - create_wire_clamp: Wire clamp with bore and split slot
    """

    def create_strut_channel_bracket(self, payload: dict) -> dict:
        """Create a McMaster-style strut channel bracket with taper, holes, and fillet."""
        raise NotImplementedError("Specialty workflows not yet migrated from server.py")

    def create_ratchet_wheel(self, payload: dict) -> dict:
        """Create a ratchet wheel with asymmetric silhouette-cut teeth."""
        raise NotImplementedError("Specialty workflows not yet migrated from server.py")

    def create_wire_clamp(self, payload: dict) -> dict:
        """Create a wire clamp with centered bore and split slot."""
        raise NotImplementedError("Specialty workflows not yet migrated from server.py")
