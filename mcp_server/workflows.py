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
    return registry
