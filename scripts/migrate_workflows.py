#!/usr/bin/env python3
"""Migrate workflows from monolithic server.py to mixin architecture.

This script:
1. Parses the original server.py to extract workflow methods
2. Maps workflows to appropriate mixin files based on naming
3. Generates the boilerplate code following the established pattern
4. Outputs patches for review before applying

Usage:
    python scripts/migrate_workflows.py --source path/to/original/server.py --output-dir migrated/
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class WorkflowMethod:
    """Represents a workflow method extracted from the original server.py."""

    name: str
    is_public: bool  # True for create_X, False for _create_X_workflow
    source: str
    line_start: int
    line_end: int
    input_class: Optional[str] = None
    calls_private: Optional[str] = None


WORKFLOW_TO_MIXIN = {
    # Plate workflows
    "create_spacer": "plates",
    "create_plate_with_hole": "plates",
    "create_two_hole_plate": "plates",
    "create_four_hole_mounting_plate": "plates",
    "create_slotted_mounting_plate": "plates",
    "create_counterbored_plate": "plates",
    "create_recessed_mount": "plates",
    "create_slotted_mount": "plates",
    "create_cable_gland_plate": "plates",
    "create_slotted_flex_panel": "plates",
    # Cylinder workflows
    "create_cylinder": "cylinders",
    "create_tube": "cylinders",
    "create_revolve": "cylinders",
    "create_tapered_knob_blank": "cylinders",
    "create_flanged_bushing": "cylinders",
    "create_shaft_coupler": "cylinders",
    "create_pipe_clamp_half": "cylinders",
    "create_tube_mounting_plate": "cylinders",
    "create_t_handle_with_square_socket": "cylinders",
    # Bracket workflows
    "create_bracket": "brackets",
    "create_filleted_bracket": "brackets",
    "create_chamfered_bracket": "brackets",
    "create_mounting_bracket": "brackets",
    "create_two_hole_mounting_bracket": "brackets",
    "create_triangular_bracket": "brackets",
    "create_l_bracket_with_gusset": "brackets",
    # Enclosure workflows
    "create_simple_enclosure": "enclosures",
    "create_open_box_body": "enclosures",
    "create_lid_for_box": "enclosures",
    "create_box_with_lid": "enclosures",
    "create_flush_lid_enclosure_pair": "enclosures",
    "create_project_box_with_standoffs": "enclosures",
    "create_snap_fit_enclosure": "enclosures",
    "create_telescoping_containers": "enclosures",
    # Specialty workflows
    "create_strut_channel_bracket": "specialty",
    "create_ratchet_wheel": "specialty",
    "create_wire_clamp": "specialty",
}

MIXIN_IMPORTS = {
    "plates": """from mcp_server.errors import WorkflowFailure
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
)""",
    "cylinders": """from mcp_server.errors import WorkflowFailure
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
)""",
    "brackets": """from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CreateBracketInput,
    CreateFilletedBracketInput,
    CreateChamferedBracketInput,
    CreateMountingBracketInput,
    CreateTwoHoleMountingBracketInput,
    CreateTriangularBracketInput,
    CreateLBracketWithGussetInput,
    VerificationSnapshot,
)""",
    "enclosures": """from mcp_server.errors import WorkflowFailure
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
)""",
    "specialty": """from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CreateStrutChannelBracketInput,
    CreateRatchetWheelInput,
    CreateWireClampInput,
    VerificationSnapshot,
)""",
}

MIXIN_CLASS_NAMES = {
    "plates": "PlateWorkflowsMixin",
    "cylinders": "CylinderWorkflowsMixin",
    "brackets": "BracketWorkflowsMixin",
    "enclosures": "EnclosureWorkflowsMixin",
    "specialty": "SpecialtyWorkflowsMixin",
}


class WorkflowExtractor(ast.NodeVisitor):
    """Extract workflow methods from server.py AST."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.source_lines = source_code.split("\n")
        self.methods: list[WorkflowMethod] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        name = node.name

        # Check if this is a workflow method
        if name.startswith("create_") or name.startswith("_create_"):
            is_public = not name.startswith("_")

            # Extract the source for this method
            line_start = node.lineno - 1  # 0-indexed
            line_end = node.end_lineno  # ast gives 1-indexed end

            # Find the actual method boundaries (handle decorators)
            if node.decorator_list:
                first_decorator = node.decorator_list[0]
                line_start = first_decorator.lineno - 1

            source = "\n".join(self.source_lines[line_start:line_end])

            # Try to find input class from the method body
            input_class = self._extract_input_class(node)

            # For public methods, find which private method they call
            calls_private = None
            if is_public:
                calls_private = self._extract_private_call(node)

            method = WorkflowMethod(
                name=name,
                is_public=is_public,
                source=source,
                line_start=line_start + 1,
                line_end=line_end,
                input_class=input_class,
                calls_private=calls_private,
            )
            self.methods.append(method)

        self.generic_visit(node)

    def _extract_input_class(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract the Input class used (e.g., CreateCylinderInput)."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr == "from_payload":
                        if isinstance(child.func.value, ast.Name):
                            return child.func.value.id
        return None

    def _extract_private_call(self, node: ast.FunctionDef) -> Optional[str]:
        """Extract the private workflow method called by a public method."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr.startswith("_create_"):
                        return child.func.attr
        return None


def generate_public_api_method(
    method: WorkflowMethod, workflow_name: str
) -> str:
    """Generate a public API method following the established pattern."""

    if not method.input_class:
        # Fallback if we couldn't detect the input class
        input_class_guess = f"Create{method.name.replace('create_', '').title().replace('_', '')}Input"
    else:
        input_class_guess = method.input_class

    if method.calls_private:
        # Check if it calls a shared helper vs a workflow-specific private method
        private_name = method.calls_private
        if private_name in {
            "_create_rectangular_prism_workflow",
            "_create_l_bracket_workflow",
            "_create_mounting_bracket_workflow",
        }:
            # Complex case: calls a shared helper - need full source
            # Original source has 4-space class-level indent, strip it and re-add
            import textwrap
            dedented = textwrap.dedent(method.source)
            lines = dedented.split("\n")
            adapted = [f"    {line}" for line in lines]
            return "\n".join(adapted) + "\n"

        # Simple case: just calls a workflow-specific private method
        return f'''    def {method.name}(self, payload: dict) -> dict:
        """{generate_docstring(workflow_name)}"""
        spec = {input_class_guess}.from_payload(payload)
        return self.{method.calls_private}(spec)
'''

    # Has inline implementation - dedent then indent properly
    import textwrap
    dedented = textwrap.dedent(method.source)
    lines = dedented.split("\n")
    adapted = [f"    {line}" for line in lines]
    return "\n".join(adapted) + "\n"


def generate_docstring(workflow_name: str) -> str:
    """Generate a docstring based on workflow name."""
    # Convert snake_case to readable description
    words = workflow_name.replace("create_", "").split("_")
    description = " ".join(words)
    return f"Create a {description}."


def generate_mixin_boilerplate(mixin_type: str, methods: list[WorkflowMethod]) -> str:
    """Generate a complete mixin file with migrated workflows."""

    class_name = MIXIN_CLASS_NAMES[mixin_type]
    imports = MIXIN_IMPORTS[mixin_type]

    # Separate public and private methods
    public_methods = [m for m in methods if m.is_public]
    private_methods = [m for m in methods if not m.is_public]

    # Generate public API methods
    public_section = "\n".join(
        generate_public_api_method(m, m.name.replace("create_", ""))
        for m in public_methods
    )

    # For private methods, we include the original source but need to adapt it
    private_section_lines = ["    # -------------------------------------------------------------------------", "    # Private workflow implementations", "    # -------------------------------------------------------------------------\n"]

    for method in private_methods:
        adapted_source = adapt_private_method(method)
        private_section_lines.append(adapted_source)

    private_section = "\n".join(private_section_lines)

    # Generate abstract method declarations based on primitives used
    primitives_used = detect_primitives_used(methods)
    abstract_section = generate_abstract_declarations(primitives_used)

    return f'''"""{mixin_type.title()} workflow family for ParamAItric.

Includes {", ".join(w.replace("create_", "") for w in WORKFLOW_TO_MIXIN if WORKFLOW_TO_MIXIN[w] == mixin_type)}.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

{imports}

if TYPE_CHECKING:
    from mcp_server.workflow_registry import WorkflowRegistry


class {class_name}:
    """Mixin providing {mixin_type}-related CAD workflows."""

{public_section}

{private_section}

{abstract_section}
'''


def adapt_private_method(method: WorkflowMethod) -> str:
    """Adapt a private workflow method to the mixin pattern."""
    import textwrap

    # Check if this already uses _bridge_step pattern
    uses_bridge_step = "_bridge_step" in method.source

    if uses_bridge_step:
        # Already migrated - dedent, re-indent and return
        dedented = textwrap.dedent(method.source)
        lines = dedented.split("\n")
        adapted = [f"    {line}" for line in lines]
        return "\n".join(adapted) + "\n"

    # Needs migration from _send pattern - add TODO
    dedented = textwrap.dedent(method.source)
    lines = dedented.split("\n")
    adapted = ["    # TODO: Migrate from _send to _bridge_step pattern", "    # Original implementation:"]
    for line in lines:
        adapted.append(f"    # {line}")
    adapted.append("    raise NotImplementedError('Migration incomplete')")

    return "\n".join(adapted) + "\n"


def detect_primitives_used(methods: list[WorkflowMethod]) -> set[str]:
    """Detect which primitive methods are called by these workflows."""
    primitives = set()
    primitive_names = {
        "new_design",
        "get_scene_info",
        "create_sketch",
        "draw_rectangle",
        "draw_rectangle_at",
        "draw_circle",
        "draw_slot",
        "draw_triangle",
        "draw_l_bracket_profile",
        "draw_revolve_profile",
        "list_profiles",
        "extrude_profile",
        "revolve_profile",
        "export_stl",
        "apply_fillet",
        "apply_chamfer",
        "apply_shell",
        "combine_bodies",
        "get_body_faces",
        "find_face",
    }

    for method in methods:
        for primitive in primitive_names:
            if primitive in method.source:
                primitives.add(primitive)

    return primitives


def generate_abstract_declarations(primitives: set[str]) -> str:
    """Generate abstract method declarations for primitives used."""

    declarations = [
        "    # -------------------------------------------------------------------------",
        "    # Abstract methods provided by other mixins",
        "    # -------------------------------------------------------------------------\n",
        "    def _bridge_step(self, *, stage, stages, action, partial_result=None, next_step=None):",
        '        """Provided by WorkflowMixin."""',
        "        raise NotImplementedError\n",
    ]

    # Map primitive names to their signatures
    signatures = {
        "new_design": "def new_design(self, name: str = \"ParamAItric Design\") -> dict:",
        "get_scene_info": "def get_scene_info(self) -> dict:",
        "create_sketch": "def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:",
        "draw_rectangle": "def draw_rectangle(self, width_cm: float, height_cm: float, sketch_token: str | None = None) -> dict:",
        "draw_rectangle_at": "def draw_rectangle_at(self, origin_x_cm: float, origin_y_cm: float, width_cm: float, height_cm: float, sketch_token: str | None = None) -> dict:",
        "draw_circle": "def draw_circle(self, center_x_cm: float, center_y_cm: float, radius_cm: float, sketch_token: str | None = None) -> dict:",
        "draw_slot": "def draw_slot(self, center_x_cm: float, center_y_cm: float, length_cm: float, width_cm: float, sketch_token: str | None = None) -> dict:",
        "draw_triangle": "def draw_triangle(self, x1_cm: float, y1_cm: float, x2_cm: float, y2_cm: float, x3_cm: float, y3_cm: float, sketch_token: str | None = None) -> dict:",
        "draw_l_bracket_profile": "def draw_l_bracket_profile(self, width_cm: float, height_cm: float, leg_thickness_cm: float, sketch_token: str | None = None) -> dict:",
        "draw_revolve_profile": "def draw_revolve_profile(self, base_diameter_cm: float, top_diameter_cm: float, height_cm: float, sketch_token: str | None = None) -> dict:",
        "list_profiles": "def list_profiles(self, sketch_token: str) -> dict:",
        "extrude_profile": "def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, **kwargs) -> dict:",
        "revolve_profile": "def revolve_profile(self, profile_token: str, body_name: str, axis: str = \"y\", angle_deg: float = 360.0) -> dict:",
        "export_stl": "def export_stl(self, body_token: str, output_path: str) -> dict:",
        "apply_fillet": "def apply_fillet(self, body_token: str, radius_cm: float) -> dict:",
        "apply_chamfer": "def apply_chamfer(self, body_token: str, distance_cm: float, edge_selection: str | None = None) -> dict:",
        "apply_shell": "def apply_shell(self, body_token: str, wall_thickness_cm: float) -> dict:",
        "combine_bodies": "def combine_bodies(self, target_body_token: str, tool_body_token: str) -> dict:",
        "get_body_faces": "def get_body_faces(self, payload: dict) -> dict:",
        "find_face": "def find_face(self, payload: dict) -> dict:",
    }

    for primitive in sorted(primitives):
        if primitive in signatures:
            declarations.extend([
                f"    {signatures[primitive]}",
 f'        """Provided by PrimitiveMixin."""',
                "        raise NotImplementedError\n",
            ])

    return "\n".join(declarations)


def parse_server_py(source_path: Path) -> dict[str, list[WorkflowMethod]]:
    """Parse server.py and extract all workflow methods organized by mixin."""

    source_code = source_path.read_text(encoding="utf-8")

    tree = ast.parse(source_code)
    extractor = WorkflowExtractor(source_code)
    extractor.visit(tree)

    # Group methods by mixin
    grouped: dict[str, list[WorkflowMethod]] = {
        "plates": [],
        "cylinders": [],
        "brackets": [],
        "enclosures": [],
        "specialty": [],
    }

    for method in extractor.methods:
        mixin_type = WORKFLOW_TO_MIXIN.get(method.name)
        if mixin_type:
            grouped[mixin_type].append(method)

    return grouped


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate workflows from server.py to mixins")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py"),
        help="Path to original server.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("migrated"),
        help="Output directory for migrated files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without writing files",
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Error: Source file not found: {args.source}")
        return 1

    print(f"Parsing {args.source}...")
    grouped = parse_server_py(args.source)

    # Count workflows
    total = sum(len(methods) for methods in grouped.values())
    print(f"Found {total} workflow methods to migrate:")
    for mixin_type, methods in grouped.items():
        print(f"  {mixin_type}: {len(methods)} methods")

    if args.dry_run:
        print("\nDry run - would generate the following files:")
        for mixin_type, methods in grouped.items():
            if methods:
                output_path = args.output_dir / f"{mixin_type}.py"
                print(f"  {output_path}")
        return 0

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Generate mixin files
    for mixin_type, methods in grouped.items():
        if not methods:
            continue

        output_path = args.output_dir / f"{mixin_type}_migrated.py"
        content = generate_mixin_boilerplate(mixin_type, methods)

        output_path.write_text(content, encoding="utf-8")
        print(f"Wrote {output_path}")

    print(f"\nMigration complete. Review the files in {args.output_dir} before applying.")
    print("\nNext steps:")
    print("1. Review the generated public API methods")
    print("2. Adapt the private workflow implementations (marked with TODO)")
    print("3. Copy the content to the appropriate mixin files")
    print("4. Run tests: pytest tests/test_workflow.py -v")

    return 0


if __name__ == "__main__":
    sys.exit(main())
