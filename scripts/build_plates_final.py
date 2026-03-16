#!/usr/bin/env python3
"""Build plates.py from scratch using extraction script."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


HEADER = '''"""Plate workflow family for ParamAItric.

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
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("plate_with_hole")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Plate With Hole Workflow"))
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
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
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
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.height_cm, sketch_token=sketch_token),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                "Plate with hole workflow expected exactly one base profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the base plate sketch before extrusion.",
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
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"], "operation": "new_body"})

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
                "Plate with hole base-body verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect profile selection and base extrusion before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": snapshot.__dict__,
                "dimensions": actual_dimensions,
                "operation": "new_body",
            }
        )

        hole_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.hole_sketch_name),
        )
        hole_sketch_token = hole_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": hole_sketch_token,
                "plane": spec.plane,
                "sketch_role": "hole",
            }
        )

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=spec.hole_center_x_cm,
                center_y_cm=spec.hole_center_y_cm,
                radius_cm=spec.hole_diameter_cm / 2.0,
                sketch_token=hole_sketch_token,
            ),
            partial_result={"sketch_token": hole_sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "hole_diameter_cm": spec.hole_diameter_cm})

        hole_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(hole_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": hole_sketch_token},
        )
        selected_hole_profile = self._select_profile_by_dimensions(
            hole_profiles,
            expected_width_cm=spec.hole_diameter_cm,
            expected_height_cm=spec.hole_diameter_cm,
            workflow_label="Plate with hole",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(hole_profiles), "profile_role": "hole"})

        cut_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_hole_profile["token"],
                distance_cm=spec.thickness_cm,
                body_name="hole",
                operation="cut",
                target_body_token=body["token"],
            )["result"]["body"],
            partial_result={"profile_token": selected_hole_profile["token"], "body": body},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": cut_body["token"], "operation": "cut"})

        post_cut_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": cut_body},
        )
        post_cut_snapshot = VerificationSnapshot.from_scene(post_cut_scene)
        post_cut_dimensions = {
            "width_cm": cut_body["width_cm"],
            "height_cm": cut_body["height_cm"],
            "thickness_cm": cut_body["thickness_cm"],
        }
        if post_cut_snapshot.body_count != 1 or post_cut_dimensions != expected_dimensions:
            raise WorkflowFailure(
                "Plate with hole cut verification failed.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": post_cut_scene, "body": cut_body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect the hole sketch and cut intersection before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": post_cut_snapshot.__dict__,
                "dimensions": post_cut_dimensions,
                "operation": "cut",
            }
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(cut_body["token"], spec.output_path)["result"],
            partial_result={"body": cut_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_plate_with_hole",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": cut_body,
            "verification": {
                "body_count": post_cut_snapshot.body_count,
                "sketch_count": post_cut_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_height_cm": spec.height_cm,
                "expected_thickness_cm": spec.thickness_cm,
                "actual_width_cm": cut_body["width_cm"],
                "actual_height_cm": cut_body["height_cm"],
                "actual_thickness_cm": cut_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "hole_diameter_cm": spec.hole_diameter_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

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

FOOTER = '''    # -------------------------------------------------------------------------
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


def extract_workflow(workflow_name: str) -> str:
    """Extract workflow from original server.py."""
    result = subprocess.run(
        [sys.executable, "scripts/extract_workflow.py", "--workflow", workflow_name],
        capture_output=True,
        text=True,
        cwd="C:/Github/paramAItric",
    )
    if result.returncode != 0:
        print(f"Error extracting {workflow_name}: {result.stderr}")
        return ""
    return result.stdout


def main() -> int:
    output_path = Path("C:/Github/paramAItric/mcp_server/workflows/plates.py")

    workflows = [
        "two_hole_plate",
        "four_hole_mounting_plate",
        "rectangular_prism",
        "counterbored_plate",
        "recessed_mount",
        "slotted_mount",
        "slotted_mounting_plate",
        "cable_gland_plate",
    ]

    parts = [HEADER]

    for workflow in workflows:
        print(f"Extracting {workflow}...")
        code = extract_workflow(workflow)
        if code:
            # Remove "# Helper methods:" and "# Main workflow method:" comments
            lines = code.split("\n")
            filtered = []
            for line in lines:
                if not line.startswith("# Helper") and not line.startswith("# Main"):
                    filtered.append(line)
            parts.append("\n".join(filtered))
            parts.append("")

    parts.append(FOOTER)

    full_content = "\n".join(parts)
    output_path.write_text(full_content, encoding="utf-8")

    print(f"Built {output_path}")
    print(f"Total lines: {len(full_content.split(chr(10)))}")

    # Verify syntax
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(output_path)],
        capture_output=True,
    )
    if result.returncode == 0:
        print("Syntax OK!")
    else:
        print("Syntax ERROR!")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
