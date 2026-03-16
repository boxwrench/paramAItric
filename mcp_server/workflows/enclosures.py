"""Enclosure workflow family for ParamAItric.

Includes boxes, lids, shells, snap-fit enclosures, and telescoping containers.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server.schemas import (
    CreateSimpleEnclosureInput,
    CreateOpenBoxBodyInput,
    CreateLidForBoxInput,
    CreateBoxWithLidInput,
    CreateFlushLidEnclosurePairInput,
    CreateProjectBoxWithStandoffsInput,
    CreateSnapFitEnclosureInput,
    CreateTelescopingContainersInput,
)

if TYPE_CHECKING:
    pass


class EnclosureWorkflowsMixin:
    """Mixin providing enclosure-related CAD workflows.

    Workflows in this family:
    - create_simple_enclosure: Open-top rectangular enclosure by shelling
    - create_open_box_body: Open-top box with inset cavity
    - create_lid_for_box: Cap lid with perimeter rim
    - create_box_with_lid: Matched box and lid as two bodies
    - create_flush_lid_enclosure_pair: Enclosure base and flush lid
    - create_project_box_with_standoffs: Shelled box with PCB standoffs
    - create_snap_fit_enclosure: Snap-fit box with view holes and wrap-over lid
    - create_telescoping_containers: Three concentric nesting containers
    """

    def create_simple_enclosure(self, payload: dict) -> dict:
        """Create an open-top rectangular enclosure by shelling the top face."""
        raise NotImplementedError("Enclosure workflows not yet migrated from server.py")

    def create_open_box_body(self, payload: dict) -> dict:
        """Create an open-top box body with an inset cavity cut from an offset floor plane."""
        raise NotImplementedError("Enclosure workflows not yet migrated from server.py")

    def create_lid_for_box(self, payload: dict) -> dict:
        """Create a cap lid with a downward perimeter rim."""
        raise NotImplementedError("Enclosure workflows not yet migrated from server.py")

    def create_box_with_lid(self, payload: dict) -> dict:
        """Create a matched box and cap lid as two separate bodies in one design."""
        raise NotImplementedError("Enclosure workflows not yet migrated from server.py")

    def create_flush_lid_enclosure_pair(self, payload: dict) -> dict:
        """Create a matched enclosure base and flush lid as two separate bodies."""
        raise NotImplementedError("Enclosure workflows not yet migrated from server.py")

    def create_project_box_with_standoffs(self, payload: dict) -> dict:
        """Create a shelled project box with four internal corner standoffs for PCB mounting."""
        raise NotImplementedError("Enclosure workflows not yet migrated from server.py")

    def create_snap_fit_enclosure(self, payload: dict) -> dict:
        """Create a snap-fit enclosure box with view holes and wrap-over snap-on lid."""
        raise NotImplementedError("Enclosure workflows not yet migrated from server.py")

    def create_telescoping_containers(self, payload: dict) -> dict:
        """Create three concentric nesting rectangular containers with progressive clearances."""
        raise NotImplementedError("Enclosure workflows not yet migrated from server.py")
