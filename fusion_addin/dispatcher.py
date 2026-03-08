from __future__ import annotations

from queue import Queue
from threading import Event

from collections.abc import Callable

from fusion_addin.bootstrap import bootstrap_addin
from fusion_addin.ops.registry import OperationRegistry
from fusion_addin.state import DesignState
from fusion_addin.workflows import WorkflowRuntime
from mcp_server.workflows import WorkflowRegistry, build_default_registry


class DispatchRequest:
    def __init__(self, command: str, arguments: dict) -> None:
        self.command = command
        self.arguments = arguments
        self.done = Event()
        self.response: dict | None = None
        self.error: Exception | None = None


class CommandDispatcher:
    def __init__(
        self,
        state: DesignState | None = None,
        workflow_registry: WorkflowRegistry | None = None,
        registry_builder: Callable[[], OperationRegistry] | None = None,
        mode: str | None = None,
    ) -> None:
        self.state = state or DesignState()
        self.workflow_registry = workflow_registry or build_default_registry()
        self.workflow_runtime = WorkflowRuntime(self.workflow_registry)
        if registry_builder is not None:
            self.registry = registry_builder()
            self.mode = mode or "custom"
        else:
            bootstrap = bootstrap_addin(self.workflow_registry)
            self.registry = bootstrap.build_registry()
            self.mode = bootstrap.mode
        self._queue: Queue[DispatchRequest] = Queue()

    def submit(self, command: str, arguments: dict) -> dict:
        request = DispatchRequest(command, arguments)
        self._queue.put(request)
        self.process_next()
        request.done.wait()
        if request.error:
            raise request.error
        assert request.response is not None
        return request.response

    def process_next(self) -> None:
        request = self._queue.get()
        try:
            payload = self.registry.execute(self.state, request.command, request.arguments)
            request.response = {"ok": True, "command": request.command, "result": payload}
        except Exception as exc:  # noqa: BLE001
            request.error = exc
        finally:
            request.done.set()

    def workflow_catalog(self) -> list[dict]:
        return self.workflow_runtime.catalog()
