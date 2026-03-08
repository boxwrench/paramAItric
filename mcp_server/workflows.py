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
            intent="Narrow bracket-blank workflow reusing the validated rectangle, extrude, verify, export path.",
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
    return registry
