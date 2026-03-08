from __future__ import annotations

from fusion_addin.dispatcher import CommandDispatcher, DispatchDriver, DispatchRequest
from fusion_addin.ops.registry import OperationRegistry


class RecordingDispatchDriver(DispatchDriver):
    def __init__(self, dispatcher: CommandDispatcher) -> None:
        self.dispatcher = dispatcher
        self.notified = 0
        self.closed = False

    def notify(self) -> None:
        self.notified += 1
        self.dispatcher.process_pending()

    def close(self) -> None:
        self.closed = True


def test_dispatcher_uses_injected_driver_and_closes_it() -> None:
    driver_holder: dict[str, RecordingDispatchDriver] = {}

    def build_driver(dispatcher: CommandDispatcher) -> DispatchDriver:
        driver = RecordingDispatchDriver(dispatcher)
        driver_holder["driver"] = driver
        return driver

    dispatcher = CommandDispatcher(dispatch_driver_factory=build_driver)

    result = dispatcher.submit("new_design", {"name": "Driver Smoke Test"})

    assert result["ok"] is True
    assert driver_holder["driver"].notified == 1

    dispatcher.close()

    assert driver_holder["driver"].closed is True


def test_process_pending_drains_until_queue_is_empty() -> None:
    registry = OperationRegistry()
    calls: list[str] = []
    registry.register("record", lambda state, arguments: calls.append(arguments["value"]) or {"value": arguments["value"]})
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: RecordingDispatchDriver(inner),
    )
    first = DispatchRequest("record", {"value": "first"})
    second = DispatchRequest("record", {"value": "second"})
    dispatcher._queue.put(first)
    dispatcher._queue.put(second)

    dispatcher.process_pending()

    assert calls == ["first", "second"]
    assert first.response is not None
    assert second.response is not None
