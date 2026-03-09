from __future__ import annotations

import threading

from fusion_addin.cancellation import OperationCancelledError, raise_if_cancelled
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


def test_dispatcher_error_propagates_to_caller() -> None:
    """An exception raised by a command handler reaches the submit() caller."""
    registry = OperationRegistry()
    registry.register("boom", lambda state, arguments: (_ for _ in ()).throw(ValueError("deliberate failure")))
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: RecordingDispatchDriver(inner),
    )

    try:
        dispatcher.submit("boom", {})
    except ValueError as exc:
        assert "deliberate failure" in str(exc)
    else:
        raise AssertionError("Expected ValueError from boom command.")


def test_dispatcher_concurrent_submissions_complete_without_mixing() -> None:
    """Multiple threads submitting unique commands each get their own response back."""
    registry = OperationRegistry()
    registry.register("echo", lambda state, arguments: {"echo": arguments["value"]})
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: RecordingDispatchDriver(inner),
    )

    results: dict[int, str] = {}
    errors: list[Exception] = []

    def _submit(index: int) -> None:
        try:
            result = dispatcher.submit("echo", {"value": str(index)})
            results[index] = result["result"]["echo"]
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_submit, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not errors, f"Threads raised errors: {errors}"
    for i in range(20):
        assert results.get(i) == str(i), f"index {i}: expected '{i}', got {results.get(i)!r}"


def test_dispatcher_repeated_submissions_do_not_leak_state() -> None:
    """Submitting many commands in sequence leaves the queue empty after each."""
    dispatcher = CommandDispatcher()
    for _ in range(10):
        result = dispatcher.submit("new_design", {"name": "loop"})
        assert result["ok"] is True
    assert dispatcher._queue.empty()


def test_dispatcher_barrier_coordinated_concurrent_submissions() -> None:
    """Ten threads all start submitting at the same moment via a Barrier.

    Each thread must get back its own unique echo value with no mixing.
    """
    n = 10
    registry = OperationRegistry()
    registry.register("echo", lambda state, arguments: {"echo": arguments["value"]})
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: RecordingDispatchDriver(inner),
    )

    barrier = threading.Barrier(n)
    results: dict[int, str] = {}
    errors: list[Exception] = []

    def _submit(index: int) -> None:
        barrier.wait()  # synchronise all threads to the same start instant
        try:
            result = dispatcher.submit("echo", {"value": str(index)})
            results[index] = result["result"]["echo"]
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_submit, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not errors, f"Threads raised: {errors}"
    for i in range(n):
        assert results.get(i) == str(i), f"index {i}: got {results.get(i)!r}"
    assert dispatcher._queue.empty()


def test_dispatcher_error_does_not_block_subsequent_commands() -> None:
    """A command that raises must not prevent the next command from completing."""
    registry = OperationRegistry()
    registry.register("boom", lambda state, args: (_ for _ in ()).throw(ValueError("boom")))
    registry.register("ok", lambda state, args: {"done": True})
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: RecordingDispatchDriver(inner),
    )

    try:
        dispatcher.submit("boom", {})
    except ValueError:
        pass

    result = dispatcher.submit("ok", {})
    assert result["ok"] is True
    assert result["result"]["done"] is True
    assert dispatcher._queue.empty()


def test_dispatcher_can_cancel_pending_request_before_execution() -> None:
    registry = OperationRegistry()
    registry.register("echo", lambda state, arguments: {"echo": arguments["value"]})
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: PassiveDispatchDriver(),
    )
    result_holder: dict[str, object] = {}
    request = dispatcher.submit_async("echo", {"value": "later"}, request_id="req-1")

    def wait_for_result() -> None:
        request.done.wait(timeout=5)
        result_holder["error"] = request.error

    waiter = threading.Thread(target=wait_for_result, daemon=True)
    waiter.start()

    cancelled = dispatcher.cancel("req-1")
    dispatcher.process_pending()
    waiter.join(timeout=5)

    assert cancelled is True
    assert isinstance(result_holder["error"], RuntimeError)
    assert "cancelled" in str(result_holder["error"]).lower()


def test_dispatcher_cannot_cancel_started_request() -> None:
    registry = OperationRegistry()
    release = threading.Event()
    entered = threading.Event()

    def slow_echo(state, arguments):  # noqa: ANN001
        _ = state
        entered.set()
        release.wait(timeout=5)
        return {"echo": arguments["value"]}

    registry.register("echo", slow_echo)
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: PassiveDispatchDriver(),
    )
    request = dispatcher.submit_async("echo", {"value": "now"}, request_id="req-2")

    worker = threading.Thread(target=dispatcher.process_pending, daemon=True)
    worker.start()
    entered.wait(timeout=5)
    cancelled = dispatcher.cancel("req-2")
    release.set()
    request.done.wait(timeout=5)
    worker.join(timeout=5)

    assert cancelled is True
    assert request.response is not None


def test_dispatcher_running_request_can_abort_cooperatively_on_cancel() -> None:
    registry = OperationRegistry()
    entered = threading.Event()

    def slow_echo(state, arguments):  # noqa: ANN001
        _ = state
        entered.set()
        while True:
            raise_if_cancelled()

    registry.register("echo", slow_echo)
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: PassiveDispatchDriver(),
    )
    request = dispatcher.submit_async("echo", {"value": "now"}, request_id="req-3")

    worker = threading.Thread(target=dispatcher.process_pending, daemon=True)
    worker.start()
    entered.wait(timeout=5)
    cancelled = dispatcher.cancel("req-3")
    request.done.wait(timeout=5)
    worker.join(timeout=5)

    assert cancelled is True
    assert isinstance(request.error, OperationCancelledError)


class PassiveDispatchDriver(DispatchDriver):
    def notify(self) -> None:
        return None
