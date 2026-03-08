from __future__ import annotations

from collections.abc import Callable

from fusion_addin.state import DesignState
from mcp_server.workflows import WorkflowRegistry, build_default_registry

OperationHandler = Callable[[DesignState, dict], dict]


class OperationRegistry:
    def __init__(self, workflow_registry: WorkflowRegistry | None = None) -> None:
        self._handlers: dict[str, OperationHandler] = {}
        self.workflow_registry = workflow_registry or build_default_registry()

    def register(self, name: str, handler: OperationHandler) -> None:
        self._handlers[name] = handler

    def execute(self, state: DesignState, name: str, arguments: dict) -> dict:
        try:
            handler = self._handlers[name]
        except KeyError as exc:
            raise KeyError(f"Unknown command: {name}") from exc
        return handler(state, arguments)

    def list_commands(self) -> list[str]:
        return sorted(self._handlers)

    def workflow_catalog(self) -> list[dict]:
        return [
            {
                "name": workflow.name,
                "intent": workflow.intent,
                "stages": list(workflow.stages),
                "extension_of": list(workflow.extension_of),
            }
            for workflow in self.workflow_registry.list()
        ]
