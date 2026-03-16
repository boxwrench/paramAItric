"""MCP-facing server layer for ParamAItric.

Refactored to use mixins for different functional areas:
- FreeformSessionManager: Freeform session lifecycle
- PrimitiveMixin: Low-level CAD primitives
- WorkflowMixins: High-level workflow implementations

Architecture:
  AI host
    -> MCP-facing server (this file)
    -> loopback HTTP request
    -> Fusion add-in bridge
    -> CustomEvent handler on Fusion main thread
    -> Fusion API
"""
from __future__ import annotations

from mcp_server.bridge_client import BridgeClient
from mcp_server.primitives import PrimitiveMixin
from mcp_server.sessions import FreeformSessionManager
from mcp_server.workflows import (
    WorkflowMixin,
    BracketWorkflowsMixin,
    PlateWorkflowsMixin,
    EnclosureWorkflowsMixin,
    CylinderWorkflowsMixin,
    SpecialtyWorkflowsMixin,
)
from mcp_server.workflow_registry import WorkflowRegistry, build_default_registry


class ParamAIToolServer(
    FreeformSessionManager,
    PrimitiveMixin,
    WorkflowMixin,
    BracketWorkflowsMixin,
    PlateWorkflowsMixin,
    EnclosureWorkflowsMixin,
    CylinderWorkflowsMixin,
    SpecialtyWorkflowsMixin,
):
    """MCP-facing server for ParamAItric CAD operations.

    This class orchestrates CAD workflows by combining:
    - Session management (freeform mode)
    - Primitive operations (sketch, extrude, etc.)
    - Workflow infrastructure (error handling, bridge communication)
    - High-level workflows (brackets, plates, enclosures, etc.)

    The class uses Python's multiple inheritance (mixins) to organize
    ~9,500 lines of functionality into logical, testable units.
    """

    def __init__(
        self,
        bridge_client: BridgeClient | None = None,
        workflow_registry: WorkflowRegistry | None = None,
    ) -> None:
        """Initialize the tool server with bridge and registry.

        Args:
            bridge_client: Client for Fusion bridge communication.
            workflow_registry: Registry of available workflows.
        """
        # Initialize bridge and registry for WorkflowMixin
        self.bridge_client = bridge_client or BridgeClient()
        self.workflow_registry = workflow_registry or build_default_registry()

        # Initialize FreeformSessionManager (needs no args)
        super().__init__()

    # All methods are inherited from mixins:
    # - FreeformSessionManager: start_freeform_session, commit_verification, etc.
    # - PrimitiveMixin: create_sketch, draw_rectangle, extrude_profile, etc.
    # - WorkflowMixin: _send, _bridge_step
    # - BracketWorkflowsMixin: create_bracket, create_filleted_bracket, etc.
    # - PlateWorkflowsMixin: create_plate_with_hole, create_two_hole_plate, etc.
    # - EnclosureWorkflowsMixin: create_box_with_lid, create_simple_enclosure, etc.
    # - CylinderWorkflowsMixin: create_cylinder, create_tube, create_revolve, etc.
    # - SpecialtyWorkflowsMixin: create_strut_channel_bracket, etc.


# Backwards compatibility: keep the old name available
# This ensures existing imports continue to work
ParamAIToolServer = ParamAIToolServer
