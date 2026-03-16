"""Enclosures workflow family for ParamAItric.

Includes simple_enclosure, open_box_body, lid_for_box, box_with_lid, flush_lid_enclosure_pair, project_box_with_standoffs, snap_fit_enclosure, telescoping_containers.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CreateSimpleEnclosureInput,
    CreateOpenBoxBodyInput,
    CreateLidForBoxInput,
    CreateBoxWithLidInput,
    CreateFlushLidEnclosurePairInput,
    CreateProjectBoxWithStandoffsInput,
    CreateSnapFitEnclosureInput,
    CreateTelescopingContainersInput,
    VerificationSnapshot,
)

if TYPE_CHECKING:
    from mcp_server.workflow_registry import WorkflowRegistry


class EnclosureWorkflowsMixin:
    """Mixin providing enclosures-related CAD workflows."""

    def create_simple_enclosure(self, payload: dict) -> dict:
        """Create a simple enclosure."""
        spec = CreateSimpleEnclosureInput.from_payload(payload)
        return self._create_simple_enclosure_workflow(spec)

    def create_open_box_body(self, payload: dict) -> dict:
        """Create a open box body."""
        spec = CreateOpenBoxBodyInput.from_payload(payload)
        return self._create_open_box_body_workflow(spec)

    def create_lid_for_box(self, payload: dict) -> dict:
        """Create a lid for box."""
        spec = CreateLidForBoxInput.from_payload(payload)
        return self._create_lid_for_box_workflow(spec)

    def create_project_box_with_standoffs(self, payload: dict) -> dict:
        """Create a project box with standoffs."""
        spec = CreateProjectBoxWithStandoffsInput.from_payload(payload)
        return self._create_project_box_with_standoffs_workflow(spec)

    def create_box_with_lid(self, payload: dict) -> dict:
        """Create a box with lid."""
        spec = CreateBoxWithLidInput.from_payload(payload)
        return self._create_box_with_lid_workflow(spec)


    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------


    # -------------------------------------------------------------------------
    # Abstract methods provided by other mixins
    # -------------------------------------------------------------------------

    def _bridge_step(self, *, stage, stages, action, partial_result=None, next_step=None):
        """Provided by WorkflowMixin."""
        raise NotImplementedError

