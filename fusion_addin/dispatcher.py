from __future__ import annotations

import uuid
from queue import Empty, Queue
from threading import Event, Lock
from typing import TYPE_CHECKING

from collections.abc import Callable

from fusion_addin.bootstrap import LiveBootstrapResult, bootstrap_addin
from fusion_addin.cancellation import OperationCancelledError, reset_current_request, set_current_request
from fusion_addin.ops.registry import OperationRegistry
from fusion_addin.state import DesignState
from fusion_addin.workflows import WorkflowRuntime
from mcp_server.workflow_registry import WorkflowRegistry, build_default_registry

if TYPE_CHECKING:
    from adsk.core import CustomEventArgs  # type: ignore[import-not-found]


class DispatchRequest:
    def __init__(self, command: str, arguments: dict, request_id: str | None = None) -> None:
        self.request_id = request_id or uuid.uuid4().hex
        self.command = command
        self.arguments = arguments
        self.done = Event()
        self.response: dict | None = None
        self.error: Exception | None = None
        self.started = False
        self._cancel_requested = False

    def cancel(self) -> bool:
        if self.done.is_set():
            return False
        self._cancel_requested = True
        if not self.started:
            self.error = OperationCancelledError("Command was cancelled before execution.")
            self.done.set()
        return True

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested


class DispatchDriver:
    def notify(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        return None


class InlineDispatchDriver(DispatchDriver):
    def __init__(self, dispatcher: "CommandDispatcher") -> None:
        self._dispatcher = dispatcher

    def notify(self) -> None:
        self._dispatcher.process_pending()


class FusionMainThreadDispatchDriver(DispatchDriver):
    def __init__(self, dispatcher: "CommandDispatcher", app: object) -> None:
        import adsk.core  # type: ignore[import-not-found]

        self._dispatcher = dispatcher
        self._app = app
        self._event_id = "paramaitric_dispatch"
        unregister = getattr(self._app, "unregisterCustomEvent", None)
        if callable(unregister):
            try:
                unregister(self._event_id)
            except RuntimeError:
                pass
        self._custom_event = self._app.registerCustomEvent(self._event_id)

        class _Handler(adsk.core.CustomEventHandler):  # type: ignore[misc, valid-type]
            def __init__(self, owner: "FusionMainThreadDispatchDriver") -> None:
                super().__init__()
                self._owner = owner

            def notify(self, args: "CustomEventArgs") -> None:  # noqa: ARG002
                self._owner._dispatcher.process_pending()

        self._handler = _Handler(self)
        self._custom_event.add(self._handler)

    def notify(self) -> None:
        self._app.fireCustomEvent(self._event_id)

    def close(self) -> None:
        if hasattr(self._custom_event, "remove"):
            self._custom_event.remove(self._handler)
        unregister = getattr(self._app, "unregisterCustomEvent", None)
        if callable(unregister):
            try:
                unregister(self._event_id)
            except RuntimeError:
                pass


class CommandDispatcher:
    def __init__(
        self,
        state: DesignState | None = None,
        workflow_registry: WorkflowRegistry | None = None,
        registry_builder: Callable[[], OperationRegistry] | None = None,
        mode: str | None = None,
        dispatch_driver_factory: Callable[["CommandDispatcher"], DispatchDriver] | None = None,
    ) -> None:
        self.state = state or DesignState()
        self.workflow_registry = workflow_registry or build_default_registry()
        self.workflow_runtime = WorkflowRuntime(self.workflow_registry)
        live_app: object | None = None
        if registry_builder is not None:
            self.registry = registry_builder()
            self.mode = mode or "custom"
        else:
            bootstrap = bootstrap_addin(self.workflow_registry)
            self.registry = bootstrap.build_registry()
            self.mode = bootstrap.mode
            if isinstance(bootstrap, LiveBootstrapResult):
                live_app = bootstrap.execution_context.adapter.app
        self._queue: Queue[DispatchRequest] = Queue()
        self._pending_requests: dict[str, DispatchRequest] = {}
        self._pending_requests_lock = Lock()
        if dispatch_driver_factory is not None:
            self._dispatch_driver = dispatch_driver_factory(self)
        elif live_app is not None:
            self._dispatch_driver = FusionMainThreadDispatchDriver(self, live_app)
        else:
            self._dispatch_driver = InlineDispatchDriver(self)

    def submit(self, command: str, arguments: dict) -> dict:
        request = self.submit_async(command, arguments)
        request.done.wait()
        if request.error:
            raise request.error
        assert request.response is not None
        return request.response

    def submit_async(self, command: str, arguments: dict, request_id: str | None = None) -> DispatchRequest:
        request = DispatchRequest(command, arguments, request_id=request_id)
        with self._pending_requests_lock:
            self._pending_requests[request.request_id] = request
        self._queue.put(request)
        self._dispatch_driver.notify()
        return request

    def cancel(self, request_id: str) -> bool:
        with self._pending_requests_lock:
            request = self._pending_requests.get(request_id)
        if request is None:
            return False
        return request.cancel()

    def request_status(self, request_id: str) -> str | None:
        with self._pending_requests_lock:
            request = self._pending_requests.get(request_id)
        if request is None:
            return None
        if request.cancel_requested:
            if request.started:
                return "cancellation_requested"
            return "cancelled"
        if request.started:
            return "running"
        return "pending"

    def process_next(self) -> None:
        try:
            request = self._queue.get_nowait()
        except Empty:
            return
        if request.cancel_requested and not request.started:
            self._complete_request(request)
            return
        request.started = True
        context_token = set_current_request(request)
        try:
            payload = self.registry.execute(self.state, request.command, request.arguments)
            request.response = {"ok": True, "command": request.command, "result": payload}
        except Exception as exc:  # noqa: BLE001
            request.error = exc
        finally:
            reset_current_request(context_token)
            self._complete_request(request)

    def process_pending(self) -> None:
        while True:
            try:
                request = self._queue.get_nowait()
            except Empty:
                return
            if request.cancel_requested and not request.started:
                self._complete_request(request)
                continue
            request.started = True
            context_token = set_current_request(request)
            try:
                payload = self.registry.execute(self.state, request.command, request.arguments)
                request.response = {"ok": True, "command": request.command, "result": payload}
            except Exception as exc:  # noqa: BLE001
                request.error = exc
            finally:
                reset_current_request(context_token)
                self._complete_request(request)

    def close(self) -> None:
        self._dispatch_driver.close()

    def workflow_catalog(self) -> list[dict]:
        return self.workflow_runtime.catalog()

    def _complete_request(self, request: DispatchRequest) -> None:
        with self._pending_requests_lock:
            self._pending_requests.pop(request.request_id, None)
        request.done.set()
