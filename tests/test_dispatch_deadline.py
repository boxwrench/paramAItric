"""Server-side dispatch deadline + late-mutation policy (0d).

These tests drive a stalled dispatch driver so the deadline can be exercised
with a short, configurable value -- no slow tests.
"""
from __future__ import annotations

import http.client
import json
import threading
import time

import pytest

from fusion_addin.dispatcher import CommandDispatcher, DispatchDriver
from fusion_addin.http_bridge import HTTPBridgeService

AUTH = "test-deadline-token"


class StalledDriver(DispatchDriver):
    """Never runs the queue on notify; the test flushes it explicitly."""

    def __init__(self, dispatcher: CommandDispatcher) -> None:
        self._dispatcher = dispatcher
        self.notified = threading.Event()

    def notify(self) -> None:
        self.notified.set()  # record only; deliberately do not process

    def flush(self) -> None:
        # Simulate the driver finally running (e.g. Fusion's main thread).
        self._dispatcher.process_pending()


class DelayedDriver(DispatchDriver):
    """Processes the queue after a short delay, in a background thread."""

    def __init__(self, dispatcher: CommandDispatcher, delay: float) -> None:
        self._dispatcher = dispatcher
        self._delay = delay

    def notify(self) -> None:
        def run() -> None:
            time.sleep(self._delay)
            self._dispatcher.process_pending()

        threading.Thread(target=run, daemon=True).start()


def _post(address: tuple[str, int], path: str, obj: dict, token: str | None = AUTH):
    host, port = address
    body = json.dumps(obj).encode("utf-8")
    conn = http.client.HTTPConnection(host, port, timeout=10)
    conn.putrequest("POST", path)
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Content-Length", str(len(body)))
    if token is not None:
        conn.putheader("X-ParamAItric-Auth", token)
    conn.endheaders()
    conn.send(body)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, json.loads(data.decode("utf-8"))


def _service(driver_factory, deadline: float) -> HTTPBridgeService:
    dispatcher = CommandDispatcher(dispatch_driver_factory=driver_factory)
    return HTTPBridgeService(
        port=0, dispatcher=dispatcher, auth_token=AUTH, dispatch_deadline=deadline
    )


def test_stalled_request_times_out_with_structured_envelope() -> None:
    service = _service(StalledDriver, deadline=0.2)
    service.start()
    try:
        status, payload = _post(
            service.address,
            "/command",
            {"command": "new_design", "arguments": {"name": "x"}},
        )
        assert status == 504
        assert payload["ok"] is False
        assert payload["classification"] == "timeout"
        assert payload["recoverable"] is True
        assert "inspect" in payload["next_step"].lower()
    finally:
        service.stop()


def test_request_completing_under_deadline_succeeds() -> None:
    service = _service(lambda d: DelayedDriver(d, delay=0.05), deadline=1.0)
    service.start()
    try:
        status, payload = _post(
            service.address,
            "/command",
            {"command": "new_design", "arguments": {"name": "x"}},
        )
        assert status == 200
        assert payload["ok"] is True
    finally:
        service.stop()


def test_timed_out_late_completion_is_discarded_and_marked_cancelled() -> None:
    holder: dict[str, StalledDriver] = {}

    def factory(dispatcher: CommandDispatcher) -> StalledDriver:
        driver = StalledDriver(dispatcher)
        holder["driver"] = driver
        return driver

    service = _service(factory, deadline=0.2)
    service.start()
    dispatcher = service.dispatcher
    try:
        status, _ = _post(
            service.address,
            "/command",
            {"command": "new_design", "arguments": {"name": "x"}, "request_id": "req-1"},
        )
        assert status == 504
        # Cancellation token reflects the timeout.
        assert dispatcher.request_status("req-1") in ("cancelled", "cancellation_requested")

        # The driver finally runs: the late completion must be discarded and the
        # pending entry cleaned up (no leak, no second response to anyone).
        holder["driver"].flush()
        assert dispatcher.request_status("req-1") is None
        assert dispatcher._pending_requests == {}
    finally:
        service.stop()


def test_cancel_still_works_while_a_request_is_being_waited_on() -> None:
    service = _service(StalledDriver, deadline=3.0)
    service.start()
    result: dict[str, tuple[int, dict]] = {}

    def do_command() -> None:
        result["command"] = _post(
            service.address,
            "/command",
            {"command": "new_design", "arguments": {"name": "x"}, "request_id": "c1"},
        )

    try:
        worker = threading.Thread(target=do_command)
        worker.start()
        time.sleep(0.3)  # let the command reach its bounded wait
        status, _ = _post(service.address, "/cancel", {"request_id": "c1"})
        assert status == 200
        worker.join(timeout=5)
        assert not worker.is_alive()
        cmd_status, cmd_payload = result["command"]
        assert cmd_status == 409
        assert cmd_payload["classification"] == "cancelled"
    finally:
        service.stop()


def test_dispatcher_submit_raises_timeout_when_stalled() -> None:
    dispatcher = CommandDispatcher(dispatch_driver_factory=StalledDriver)
    with pytest.raises(TimeoutError, match="deadline"):
        dispatcher.submit("new_design", {"name": "x"}, timeout=0.2)
    # No leak: the abandoned request is cleaned up once the driver runs.
    dispatcher._dispatch_driver.flush()
    assert dispatcher._pending_requests == {}
