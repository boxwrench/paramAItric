from __future__ import annotations

from dataclasses import dataclass, field

from mcp_server.workflow_registry import WorkflowRegistry, build_default_registry


@dataclass
class WorkflowSession:
    workflow_name: str
    allowed_stages: tuple[str, ...]
    completed_stages: list[str] = field(default_factory=list)

    def record(self, stage: str) -> None:
        if stage not in self.allowed_stages:
            raise ValueError(f"Stage '{stage}' is not part of workflow '{self.workflow_name}'.")
        expected_stage = self.allowed_stages[len(self.completed_stages)]
        if stage != expected_stage:
            raise ValueError(
                f"Stage '{stage}' is out of order for workflow '{self.workflow_name}'. "
                f"Expected '{expected_stage}'."
            )
        self.completed_stages.append(stage)


class WorkflowRuntime:
    def __init__(self, workflow_registry: WorkflowRegistry | None = None) -> None:
        self.workflow_registry = workflow_registry or build_default_registry()

    def start(self, workflow_name: str) -> WorkflowSession:
        workflow = self.workflow_registry.get(workflow_name)
        return WorkflowSession(workflow_name=workflow.name, allowed_stages=workflow.stages)

    def catalog(self) -> list[dict]:
        return [
            {
                "name": workflow.name,
                "intent": workflow.intent,
                "stages": list(workflow.stages),
                "extension_of": list(workflow.extension_of),
            }
            for workflow in self.workflow_registry.list()
        ]
