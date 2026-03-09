from __future__ import annotations

import json
import threading
import time
from urllib import request

from fusion_addin.dispatcher import CommandDispatcher, DispatchDriver
from fusion_addin.http_bridge import HTTPBridgeService
from fusion_addin.ops.registry import OperationRegistry


class PassiveDispatchDriver(DispatchDriver):
    def notify(self) -> None:
        return None


def test_http_bridge_can_cancel_pending_request() -> None:
    registry = OperationRegistry()
    registry.register("echo", lambda state, arguments: {"echo": arguments["value"]})
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: PassiveDispatchDriver(),
    )
    service = HTTPBridgeService(port=0, dispatcher=dispatcher)
    service.start()
    host, port = service.address
    base_url = f"http://{host}:{port}"
    request_id = "pending-echo"
    response_holder: dict[str, object] = {}

    def send_command() -> None:
        payload = json.dumps(
            {"command": "echo", "arguments": {"value": "later"}, "request_id": request_id}
        ).encode("utf-8")
        req = request.Request(
            f"{base_url}/command",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=5) as response:
                response_holder["status"] = response.status
                response_holder["body"] = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            response_holder["error"] = exc

    command_thread = threading.Thread(target=send_command, daemon=True)
    command_thread.start()

    cancel_payload = json.dumps({"request_id": request_id}).encode("utf-8")
    cancel_req = request.Request(
        f"{base_url}/cancel",
        data=cancel_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    cancel_result = None
    for _ in range(50):
        try:
            with request.urlopen(cancel_req, timeout=5) as response:
                cancel_result = json.loads(response.read().decode("utf-8"))
                break
        except Exception as exc:  # noqa: BLE001
            if "HTTP Error 404" not in str(exc):
                raise
            time.sleep(0.01)
    if cancel_result is None:
        raise AssertionError("Expected pending request to become cancellable.")

    command_thread.join(timeout=5)
    service.stop()

    assert cancel_result == {"ok": True, "request_id": request_id, "status": "cancelled"}
    error = response_holder["error"]
    assert "HTTP Error 400" in str(error)


def test_http_bridge_cancel_returns_not_found_for_unknown_request() -> None:
    service = HTTPBridgeService(port=0)
    service.start()
    host, port = service.address
    base_url = f"http://{host}:{port}"

    cancel_payload = json.dumps({"request_id": "missing"}).encode("utf-8")
    cancel_req = request.Request(
        f"{base_url}/cancel",
        data=cancel_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        request.urlopen(cancel_req, timeout=5)
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
    else:
        raise AssertionError("Expected cancelling an unknown request to fail.")
    finally:
        service.stop()

    assert "HTTP Error 404" in error_text
