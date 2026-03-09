from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    intent: str
    stages: tuple[str, ...]
    extension_of: tuple[str, ...] = ()


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        self._workflows[workflow.name] = workflow

    def get(self, name: str) -> WorkflowDefinition:
        return self._workflows[name]

    def list(self) -> list[WorkflowDefinition]:
        return list(self._workflows.values())


def build_default_registry() -> WorkflowRegistry:
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="spacer",
            intent="Golden-path mechanical workflow for sketch, profile, extrude, verify, export.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="bracket",
            intent="Narrow L-bracket workflow using a single validated L-profile sketch, extrude, verify, export path.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("spacer",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="simple_enclosure",
            intent="Future staged multi-part workflow with body-first validation before fit or closure logic.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
            ),
            extension_of=("spacer", "bracket"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="mounting_bracket",
            intent="Narrow bracket workflow with one validated sketch hole and deterministic outer-profile selection.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("bracket",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="two_hole_mounting_bracket",
            intent="Narrow bracket workflow with two validated sketch holes and deterministic outer-profile selection.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "draw_circle",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("mounting_bracket",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="plate_with_hole",
            intent=(
                "Flat plate with a single through-hole via cut extrusion. "
                "First workflow using cut operations: solid body first, "
                "then a second sketch on the top face drives a cut extrude."
            ),
            # NOTE: WorkflowSession.record() uses position-based matching
            # (allowed_stages[len(completed_stages)]), so duplicate stage names
            # are safe here — each occurrence is matched at its own index.
            # The two_hole_mounting_bracket workflow already relies on this
            # for its two "draw_circle" stages.
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",      # first sketch: rectangle profile
                "draw_rectangle",
                "list_profiles",      # first profile listing: one solid profile
                "extrude_profile",    # new_body: creates the base plate
                "verify_geometry",    # verify exactly one body
                "create_sketch",      # second sketch: circle on top face
                "draw_circle",
                "list_profiles",      # second profile listing: hole profile
                "extrude_profile",    # cut: removes material from base plate
                "verify_geometry",    # verify body count is still 1
                "export_stl",
            ),
            extension_of=("spacer", "mounting_bracket"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="two_hole_plate",
            intent=(
                "Flat plate with two mirrored through-holes on a shared centerline. "
                "Extends the validated plate path with symmetric edge-offset placement "
                "while keeping the same single-sketch extrusion contract."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "draw_circle",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("plate_with_hole",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="slotted_mount",
            intent=(
                "Flat plate with one horizontal slot in the base sketch. "
                "First workflow using a bounded slot primitive while keeping "
                "the same single-sketch extrusion contract."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "draw_slot",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("two_hole_plate",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="four_hole_mounting_plate",
            intent=(
                "Flat mounting plate with four corner through-holes using mirrored X and Y edge offsets. "
                "Extends the validated plate path with a practical corner-hole pattern while keeping "
                "the same single-sketch extrusion contract."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("two_hole_plate",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="slotted_mounting_plate",
            intent=(
                "Flat mounting plate with four corner through-holes plus one centered slot in the same sketch. "
                "Composes validated hole and slot stages without adding a new low-level primitive."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "draw_slot",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("four_hole_mounting_plate", "slotted_mount"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="counterbored_plate",
            intent=(
                "Flat plate with a through-hole plus a larger shallow concentric counterbore. "
                "Extends the validated cut workflow with one additional partial-depth circular cut."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("plate_with_hole",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="recessed_mount",
            intent=(
                "Flat plate with one bounded rectangular pocket cut from the top face. "
                "Extends the validated plate workflow with an explicitly placed partial-depth recess."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("plate_with_hole",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="open_box_body",
            intent=(
                "Open-top box body with an inset cavity cut from an offset floor plane. "
                "Extends the recessed cut path with one offset sketch plane while preserving outer dimensions."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("recessed_mount",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="lid_for_box",
            intent=(
                "Cap lid with a downward perimeter rim formed by a bottom-side rectangular cut. "
                "Extends the box family without introducing clearance or paired-fit logic."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("open_box_body",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="filleted_bracket",
            intent="L-bracket with edge fillets applied after extrusion. First workflow using fillet operations.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "apply_fillet",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("bracket",),
        )
    )
    return registry
