from __future__ import annotations

import json
from http.client import HTTPConnection
import threading
import time
from urllib import error, request
from urllib.parse import urlsplit

from fusion_addin.cancellation import raise_if_cancelled
from fusion_addin.dispatcher import CommandDispatcher, DispatchDriver
from fusion_addin.http_bridge import HTTPBridgeService, MAX_REQUEST_BODY_BYTES
from fusion_addin.ops.registry import OperationRegistry
from mcp_server.bridge_client import BridgeClient
from mcp_server.schemas import CommandEnvelope


class PassiveDispatchDriver(DispatchDriver):
    def notify(self) -> None:
        return None


def _raw_post(
    base_url: str,
    path: str,
    body: bytes = b"",
    *,
    content_type: str | None = "application/json",
    content_length: str | None = None,
    auth_token: str | None = None,
) -> tuple[int, dict]:
    parsed = urlsplit(base_url)
    connection = HTTPConnection(parsed.hostname, parsed.port, timeout=5)
    connection.putrequest("POST", path)
    if content_type is not None:
        connection.putheader("Content-Type", content_type)
    if content_length is not None:
        connection.putheader("Content-Length", content_length)
    if auth_token is not None:
        connection.putheader("X-ParamAItric-Auth", auth_token)
    connection.endheaders(body)
    response = connection.getresponse()
    result = response.status, json.loads(response.read().decode("utf-8"))
    connection.close()
    return result


def test_http_bridge_accepts_bridge_client_json_envelope() -> None:
    registry = OperationRegistry()
    registry.register("echo", lambda state, arguments: {"echo": arguments["value"]})
    dispatcher = CommandDispatcher(registry_builder=lambda: registry, mode="custom")
    service = HTTPBridgeService(port=0, dispatcher=dispatcher, auth_token="test-auth-token")
    service.start()
    host, port = service.address

    try:
        result = BridgeClient(f"http://{host}:{port}", auth_token="test-auth-token").send(
            CommandEnvelope.build("echo", {"value": "safe"})
        )
    finally:
        service.stop()

    assert result == {"ok": True, "command": "echo", "result": {"echo": "safe"}}


def test_http_bridge_rejects_missing_or_invalid_request_headers(running_bridge) -> None:
    service, base_url = running_bridge
    auth_token = service.auth_token

    status, payload = _raw_post(
        base_url,
        "/command",
        b'{}',
        content_length="2",
        content_type=None,
        auth_token=auth_token,
    )
    assert status == 415
    assert payload["classification"] == "invalid_request"

    status, payload = _raw_post(base_url, "/command", b'{}', auth_token=auth_token)
    assert status == 411
    assert payload["classification"] == "invalid_request"

    status, payload = _raw_post(base_url, "/command", content_length="not-a-number", auth_token=auth_token)
    assert status == 400
    assert payload["classification"] == "invalid_request"


def test_http_bridge_rejects_oversized_request_without_reading_body(running_bridge) -> None:
    service, base_url = running_bridge
    auth_token = service.auth_token

    status, payload = _raw_post(
        base_url,
        "/command",
        content_length=str(MAX_REQUEST_BODY_BYTES + 1),
        auth_token=auth_token,
    )

    assert status == 413
    assert payload["classification"] == "request_too_large"


def test_http_bridge_returns_json_errors_for_malformed_command_envelopes(running_bridge) -> None:
    service, base_url = running_bridge
    auth_token = service.auth_token
    invalid_bodies = [
        b"{not-json",
        b"[]",
        b"{}",
        b'{"command": 3}',
        b'{"command": "health", "arguments": []}',
        b'{"command": "health", "request_id": 3}',
    ]

    for body in invalid_bodies:
        status, payload = _raw_post(base_url, "/command", body, content_length=str(len(body)), auth_token=auth_token)
        assert status == 400
        assert payload["ok"] is False
        assert payload["classification"] == "invalid_request"


def test_http_bridge_applies_json_envelope_validation_to_cancel(running_bridge) -> None:
    service, base_url = running_bridge
    auth_token = service.auth_token

    for body in (b"not-json", b"[]", b'{"request_id": 3}'):
        status, payload = _raw_post(base_url, "/cancel", body, content_length=str(len(body)), auth_token=auth_token)
        assert status == 400
        assert payload["ok"] is False
        assert payload["classification"] == "invalid_request"


def test_http_bridge_can_cancel_pending_request() -> None:
    registry = OperationRegistry()
    registry.register("echo", lambda state, arguments: {"echo": arguments["value"]})
    dispatcher = CommandDispatcher(
        registry_builder=lambda: registry,
        mode="custom",
        dispatch_driver_factory=lambda inner: PassiveDispatchDriver(),
    )
    auth_token = "test-auth-token"
    service = HTTPBridgeService(port=0, dispatcher=dispatcher, auth_token=auth_token)
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
            headers={
                "Content-Type": "application/json",
                "X-ParamAItric-Auth": auth_token,
            },
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
        headers={
            "Content-Type": "application/json",
            "X-ParamAItric-Auth": auth_token,
        },
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
    assert "HTTP Error 409" in str(error)


def test_http_bridge_cancel_returns_not_found_for_unknown_request() -> None:
    auth_token = "test-auth-token"
    service = HTTPBridgeService(port=0, auth_token=auth_token)
    service.start()
    host, port = service.address
    base_url = f"http://{host}:{port}"

    cancel_payload = json.dumps({"request_id": "missing"}).encode("utf-8")
    cancel_req = request.Request(
        f"{base_url}/cancel",
        data=cancel_payload,
        headers={
            "Content-Type": "application/json",
            "X-ParamAItric-Auth": auth_token,
        },
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


def test_http_bridge_can_request_cancellation_for_running_command() -> None:
    registry = OperationRegistry()
    entered = threading.Event()
    release = threading.Event()

    def slow_echo(state, arguments):  # noqa: ANN001
        _ = (state, arguments)
        entered.set()
        while not release.is_set():
            time.sleep(0.01)
            raise_if_cancelled()
        return {"echo": "done"}

    registry.register("echo", slow_echo)
    dispatcher = CommandDispatcher(registry_builder=lambda: registry, mode="custom")
    auth_token = "test-auth-token"
    service = HTTPBridgeService(port=0, dispatcher=dispatcher, auth_token=auth_token)
    service.start()
    host, port = service.address
    base_url = f"http://{host}:{port}"
    request_id = "running-echo"
    response_holder: dict[str, object] = {}

    def send_command() -> None:
        payload = json.dumps(
            {"command": "echo", "arguments": {"value": "later"}, "request_id": request_id}
        ).encode("utf-8")
        req = request.Request(
            f"{base_url}/command",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-ParamAItric-Auth": auth_token,
            },
            method="POST",
        )
        try:
            request.urlopen(req, timeout=5)
        except Exception as exc:  # noqa: BLE001
            response_holder["error"] = exc

    command_thread = threading.Thread(target=send_command, daemon=True)
    command_thread.start()
    entered.wait(timeout=5)

    cancel_payload = json.dumps({"request_id": request_id}).encode("utf-8")
    cancel_req = request.Request(
        f"{base_url}/cancel",
        data=cancel_payload,
        headers={
            "Content-Type": "application/json",
            "X-ParamAItric-Auth": auth_token,
        },
        method="POST",
    )
    with request.urlopen(cancel_req, timeout=5) as response:
        cancel_result = json.loads(response.read().decode("utf-8"))

    command_thread.join(timeout=5)
    service.stop()

    assert cancel_result == {"ok": True, "request_id": request_id, "status": "cancellation_requested"}
    error_value = response_holder["error"]
    assert isinstance(error_value, error.HTTPError)
    assert error_value.code == 409


# ── Negative auth tests ──────────────────────────────────────────────


def test_http_bridge_rejects_post_without_auth_token(running_bridge):
    """POST without X-ParamAItric-Auth header is rejected with 401."""
    _, base_url = running_bridge
    status, payload = _raw_post(base_url, '/command', b'{"command": "echo"}', content_length='19')
    assert status == 401
    assert payload['classification'] == 'unauthorized'
    assert payload['recoverable'] is False


def test_http_bridge_rejects_post_with_wrong_auth_token(running_bridge):
    """POST with wrong token is rejected with 401."""
    _, base_url = running_bridge
    status, payload = _raw_post(base_url, '/command', b'{"command": "echo"}', content_length='19', auth_token='wrong-token')
    assert status == 401
    assert payload['classification'] == 'unauthorized'


def test_http_bridge_rejects_post_with_origin_header(running_bridge):
    """POST with Origin header is rejected with 403 (cross-origin protection)."""
    service, base_url = running_bridge
    auth_token = service.auth_token
    parsed = urlsplit(base_url)
    conn = HTTPConnection(parsed.hostname, parsed.port, timeout=5)
    body = b'{"command": "echo"}'
    conn.putrequest('POST', '/command')
    conn.putheader('Content-Type', 'application/json')
    conn.putheader('Content-Length', str(len(body)))
    conn.putheader('X-ParamAItric-Auth', auth_token)
    conn.putheader('Origin', 'http://evil.example.com')
    conn.endheaders(body)
    response = conn.getresponse()
    status = response.status
    payload = json.loads(response.read().decode('utf-8'))
    conn.close()
    assert status == 403
    assert payload['classification'] == 'unauthorized'
    assert 'cross-origin' in payload['error'].lower()


def test_http_bridge_rejects_post_with_referer_header(running_bridge):
    """POST with Referer header is rejected with 403."""
    service, base_url = running_bridge
    auth_token = service.auth_token
    parsed = urlsplit(base_url)
    conn = HTTPConnection(parsed.hostname, parsed.port, timeout=5)
    body = b'{"command": "echo"}'
    conn.putrequest('POST', '/command')
    conn.putheader('Content-Type', 'application/json')
    conn.putheader('Content-Length', str(len(body)))
    conn.putheader('X-ParamAItric-Auth', auth_token)
    conn.putheader('Referer', 'http://evil.example.com/page')
    conn.endheaders(body)
    response = conn.getresponse()
    status = response.status
    payload = json.loads(response.read().decode('utf-8'))
    conn.close()
    assert status == 403
    assert payload['classification'] == 'unauthorized'


def test_http_bridge_health_does_not_require_auth(running_bridge):
    """GET /health is read-only and does not require auth."""
    _, base_url = running_bridge
    import urllib.request
    with urllib.request.urlopen(f'{base_url}/health', timeout=5) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
    assert payload['ok'] is True


def test_http_bridge_valid_token_and_command_succeeds():
    """Valid auth token + valid command round-trips successfully against mock dispatcher."""
    registry = OperationRegistry()
    registry.register('echo', lambda state, arguments: {'echo': arguments['value']})
    dispatcher = CommandDispatcher(registry_builder=lambda: registry, mode='custom')
    token = 'positive-test-token'
    service = HTTPBridgeService(port=0, dispatcher=dispatcher, auth_token=token)
    service.start()
    host, port = service.address
    try:
        client = BridgeClient(f'http://{host}:{port}', auth_token=token)
        result = client.send(CommandEnvelope.build('echo', {'value': 'works'}))
    finally:
        service.stop()
    assert result == {'ok': True, 'command': 'echo', 'result': {'echo': 'works'}}
