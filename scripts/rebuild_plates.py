#!/usr/bin/env python3
"""Rebuild plates.py from original server.py with proper structure."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def extract_method(source_lines: list[str], method_name: str) -> str | None:
    """Extract a method from source lines."""
    start_line = None
    for i, line in enumerate(source_lines):
        if re.match(rf"    def {method_name}\(", line):
            start_line = i
            break

    if start_line is None:
        return None

    end_line = len(source_lines)
    for i in range(start_line + 1, len(source_lines)):
        line = source_lines[i]
        if re.match(r"    def [^_]|    def __", line):
            end_line = i
            break

    lines = source_lines[start_line:end_line]
    result = []
    for line in lines:
        if line.startswith("    "):
            result.append(line[4:])
        else:
            result.append(line)
    return "\n".join(result)


def main() -> int:
    original = Path("C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py")
    source_code = original.read_text(encoding="utf-8")
    source_lines = source_code.split("\n")

    # Header
    header = '''"""Plate workflow family for ParamAItric.

Includes flat plates with holes, slots, counterbores, and various mounting patterns.
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
    """Mixin providing plate-related CAD workflows.

    Workflows in this family:
    - create_spacer: Simple rectangular flat plate
    - create_plate_with_hole: Flat plate with single through-hole
    - create_two_hole_plate: Plate with two mirrored holes
    - create_four_hole_mounting_plate: Plate with four corner holes
    - create_slotted_mounting_plate: Plate with holes plus slot
    - create_counterbored_plate: Plate with counterbored hole
    - create_recessed_mount: Plate with rectangular pocket
    - create_slotted_mount: Plate with single horizontal slot
    - create_cable_gland_plate: Plate with corner holes plus large center hole
    - create_slotted_flex_panel: Panel with multiple slots for flexibility
    """

    def create_spacer(self, payload: dict) -> dict:
        """Create a flat rectangular spacer: sketch, extrude, verify, export."""
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

    def create_plate_with_hole(self, payload: dict) -> dict:
        """Create a flat plate with a single through-hole."""
        spec = CreatePlateWithHoleInput.from_payload(payload)
        return self._create_plate_with_hole_workflow(spec)

    def create_two_hole_plate(self, payload: dict) -> dict:
        """Create a flat plate with two mirrored through-holes."""
        spec = CreateTwoHolePlateInput.from_payload(payload)
        return self._create_two_hole_plate_workflow(spec)

    def create_four_hole_mounting_plate(self, payload: dict) -> dict:
        """Create a flat mounting plate with four corner through-holes."""
        spec = CreateFourHoleMountingPlateInput.from_payload(payload)
        return self._create_four_hole_mounting_plate_workflow(spec)

    def create_slotted_mounting_plate(self, payload: dict) -> dict:
        """Create a flat mounting plate with four corner holes plus a centered slot."""
        spec = CreateSlottedMountingPlateInput.from_payload(payload)
        return self._create_slotted_mounting_plate_workflow(spec)

    def create_counterbored_plate(self, payload: dict) -> dict:
        """Create a flat plate with a through-hole and larger shallow counterbore."""
        spec = CreateCounterboredPlateInput.from_payload(payload)
        return self._create_counterbored_plate_workflow(spec)

    def create_recessed_mount(self, payload: dict) -> dict:
        """Create a flat plate with a rectangular pocket cut from the top face."""
        spec = CreateRecessedMountInput.from_payload(payload)
        return self._create_recessed_mount_workflow(spec)

    def create_slotted_mount(self, payload: dict) -> dict:
        """Create a flat plate with one horizontal slot."""
        spec = CreateSlottedMountInput.from_payload(payload)
        return self._create_slotted_mount_workflow(spec)

    def create_cable_gland_plate(self, payload: dict) -> dict:
        """Create a flat plate with four corner mounting holes and one large center hole."""
        spec = CreateCableGlandPlateInput.from_payload(payload)
        return self._create_cable_gland_plate_workflow(spec)

    def create_slotted_flex_panel(self, payload: dict) -> dict:
        """Create a flat panel with evenly spaced slots for living hinge flexibility."""
        raise NotImplementedError("Plate workflows not yet migrated from server.py")

    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------
'''

    # Methods to extract
    methods_to_extract = [
        "_create_plate_with_hole_workflow",
        "_create_two_hole_plate_workflow",
        "_create_four_hole_mounting_plate_workflow",
        "_create_rectangular_prism_workflow",
        "_create_base_plate_body",
        "_run_circle_cut_stage",
        "_run_rectangle_cut_stage",
        "_create_counterbored_plate_workflow",
        "_create_recessed_mount_workflow",
        "_create_slotted_mount_workflow",
        "_create_slotted_mounting_plate_workflow",
        "_create_cable_gland_plate_workflow",
    ]

    methods_code = []
    extracted_methods = set()
    for method_name in methods_to_extract:
        if method_name in extracted_methods:
            continue
        code = extract_method(source_lines, method_name)
        if code:
            methods_code.append(code)
            methods_code.append("")
            extracted_methods.add(method_name)

    # Abstract methods footer
    footer = '''    # -------------------------------------------------------------------------
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

    def draw_rectangle(self, width_cm: float, height_cm: float, sketch_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_rectangle_at(self, origin_x_cm: float, origin_y_cm: float, width_cm: float, height_cm: float, sketch_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_circle(self, center_x_cm: float, center_y_cm: float, radius_cm: float, sketch_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_slot(self, center_x_cm: float, center_y_cm: float, length_cm: float, width_cm: float, sketch_token: str | None = None) -> dict:
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

    def find_face(self, payload: dict) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError
'''

    # Combine all parts
    full_content = header + "\n".join(methods_code) + footer

    output_path = Path("C:/Github/paramAItric/mcp_server/workflows/plates.py")
    output_path.write_text(full_content, encoding="utf-8")
    print(f"Rebuilt {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
