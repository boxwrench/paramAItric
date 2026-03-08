from __future__ import annotations

from fusion_addin.dispatcher import CommandDispatcher, DispatchDriver


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
