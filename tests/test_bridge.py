from __future__ import annotations

import io
import json
import socket
import threading
from urllib import error

import pytest

from mcp_server import bridge_client as bridge_client_module
from mcp_server.bridge_client import BridgeCancelledError, BridgeClient, BridgeTimeoutError
from mcp_server.schemas import CommandEnvelope


def test_bridge_health_endpoint(running_bridge) -> None:
    service, base_url = running_bridge
    auth_token = service.auth_token
    client = BridgeClient(base_url, auth_token=auth_token)
    health = client.health()
    assert health["ok"] is True
    assert health["status"] == "ready"
    assert health["mode"] == "mock"
    assert any(workflow["name"] == "spacer" for workflow in health["workflow_catalog"])


def test_bridge_runs_single_command(running_bridge) -> None:
    service, base_url = running_bridge
    auth_token = service.auth_token
    client = BridgeClient(base_url, auth_token=auth_token)
    result = client.send(CommandEnvelope.build("new_design", {"name": "Smoke Test"}))
    assert result["ok"] is True
    assert result["result"]["design_name"] == "Smoke Test"


def test_bridge_cancel_raises_for_unknown_request(running_bridge) -> None:
    service, base_url = running_bridge
    auth_token = service.auth_token
    client = BridgeClient(base_url, auth_token=auth_token)
    with pytest.raises(RuntimeError, match="Bridge cancel failed"):
        client.cancel("missing")


def test_bridge_raises_on_unknown_command(running_bridge) -> None:
    service, base_url = running_bridge
    auth_token = service.auth_token
    client = BridgeClient(base_url, auth_token=auth_token)
    with pytest.raises(RuntimeError, match="Bridge command failed"):
        client.send(CommandEnvelope.build("nonexistent_command", {}))


def test_bridge_raises_on_bad_operation_arguments(running_bridge) -> None:
    service, base_url = running_bridge
    auth_token = service.auth_token
    client = BridgeClient(base_url, auth_token=auth_token)
    # extrude_profile with an invalid profile_token should return HTTP 400
    with pytest.raises(RuntimeError, match="Bridge command failed"):
        client.send(CommandEnvelope.build("extrude_profile", {"profile_token": "bad:token", "distance_cm": 1.0, "body_name": "x"}))


def test_bridge_client_configurable_timeouts() -> None:
    client = BridgeClient("http://127.0.0.1:8123", health_timeout=2.0, command_timeout=15.0, auth_token="t")
    assert client.health_timeout == 2.0
    assert client.command_timeout == 15.0


def test_bridge_health_raises_when_server_unreachable(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(ConnectionRefusedError("actively refused"))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:1", health_timeout=1.0, auth_token="t")
    with pytest.raises(RuntimeError, match="not reachable"):
        client.health()


def test_bridge_send_raises_when_server_unreachable(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(ConnectionRefusedError("actively refused"))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:1", command_timeout=1.0, auth_token="t")
    with pytest.raises(RuntimeError, match="not reachable"):
        client.send(CommandEnvelope.build("new_design", {}))


def test_bridge_send_raises_on_timeout() -> None:
    """Server accepts the TCP connection but never sends an HTTP response."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    accepted: list[socket.socket] = []

    def _accept_and_hang() -> None:
        conn, _ = server_sock.accept()
        accepted.append(conn)

    t = threading.Thread(target=_accept_and_hang, daemon=True)
    t.start()

    client = BridgeClient(f"http://127.0.0.1:{port}", command_timeout=0.5, auth_token="t")
    try:
        with pytest.raises(BridgeTimeoutError, match="timed out"):
            client.send(CommandEnvelope.build("new_design", {}))
    finally:
        server_sock.close()
        for conn in accepted:
            conn.close()
        t.join(timeout=2)


def test_bridge_health_raises_on_timeout() -> None:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    accepted: list[socket.socket] = []

    def _accept_and_hang() -> None:
        conn, _ = server_sock.accept()
        accepted.append(conn)

    t = threading.Thread(target=_accept_and_hang, daemon=True)
    t.start()

    client = BridgeClient(f"http://127.0.0.1:{port}", health_timeout=0.5, auth_token="t")
    try:
        with pytest.raises(BridgeTimeoutError, match="timed out"):
            client.health()
    finally:
        server_sock.close()
        for conn in accepted:
            conn.close()
        t.join(timeout=2)


def test_bridge_send_raises_on_cancelled_request(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(OSError(995, "The I/O operation has been aborted."))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:8123", command_timeout=1.0, auth_token="t")
    with pytest.raises(BridgeCancelledError, match="cancelled"):
        client.send(CommandEnvelope.build("new_design", {}))


def test_bridge_health_raises_on_cancelled_request(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(OSError(995, "The I/O operation has been aborted."))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:8123", health_timeout=1.0, auth_token="t")
    with pytest.raises(BridgeCancelledError, match="cancelled"):
        client.health()


def test_bridge_cancel_raises_when_server_unreachable(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(ConnectionRefusedError("actively refused"))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:1", command_timeout=1.0, auth_token="t")
    with pytest.raises(RuntimeError, match="not reachable"):
        client.cancel("req-1")


def test_bridge_send_default_command_timeout_exceeds_dispatch_deadline() -> None:
    """The default client command_timeout must stay strictly greater than the
    server's dispatch deadline so a timed-out client never races the
    authoritative server response."""
    from fusion_addin.dispatcher import DEFAULT_DISPATCH_DEADLINE

    client = BridgeClient("http://127.0.0.1:8123", auth_token="t")
    assert client.command_timeout > DEFAULT_DISPATCH_DEADLINE


def test_bridge_send_generates_request_id_when_not_supplied(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):  # noqa: ANN002
            return False

        def read(self):
            return json.dumps({"ok": True, "command": "new_design", "result": {}}).encode("utf-8")

    def fake_urlopen(req, *args, **kwargs):  # noqa: ARG001
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:8123", command_timeout=1.0, auth_token="t")
    client.send(CommandEnvelope.build("new_design", {}))

    assert "request_id" in captured["payload"]
    assert captured["payload"]["request_id"]


def test_bridge_send_timeout_issues_authenticated_cancel_with_request_id(monkeypatch) -> None:
    """An early socket-level timeout must trigger a best-effort authenticated
    cancel for the same request_id before the timeout is raised."""
    cancel_calls: list[tuple[str, dict]] = []

    def fake_urlopen(req, *args, **kwargs):  # noqa: ARG001
        if req.full_url.endswith("/command"):
            raise TimeoutError("timed out")
        if req.full_url.endswith("/cancel"):
            headers = {k.lower(): v for k, v in req.headers.items()}
            cancel_calls.append((json.loads(req.data.decode("utf-8"))["request_id"], headers))

            class _CancelResponse:
                def __enter__(self):
                    return self

                def __exit__(self, *args):  # noqa: ANN002
                    return False

                def read(self):
                    return json.dumps({"ok": True}).encode("utf-8")

            return _CancelResponse()
        raise AssertionError(f"unexpected url {req.full_url}")

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:8123", command_timeout=1.0, auth_token="t")

    with pytest.raises(BridgeTimeoutError):
        client.send(CommandEnvelope.build("new_design", {}), request_id="req-target")

    assert len(cancel_calls) == 1
    request_id, headers = cancel_calls[0]
    assert request_id == "req-target"
    assert headers.get("x-paramaitric-auth") == "t"


def test_bridge_send_cancel_failure_does_not_mask_timeout(monkeypatch) -> None:
    """If the best-effort cancel itself fails, the original timeout must still
    surface -- a cancel failure must never mask it."""

    def fake_urlopen(req, *args, **kwargs):  # noqa: ARG001
        if req.full_url.endswith("/command"):
            raise TimeoutError("timed out")
        raise error.URLError(ConnectionRefusedError("actively refused"))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:8123", command_timeout=1.0, auth_token="t")

    with pytest.raises(BridgeTimeoutError, match="timed out"):
        client.send(CommandEnvelope.build("new_design", {}))


def test_bridge_send_maps_504_body_to_bridge_timeout_error(monkeypatch) -> None:
    body = json.dumps(
        {
            "ok": False,
            "command": "new_design",
            "error": "Dispatch deadline of 0.2s exceeded.",
            "classification": "timeout",
            "recoverable": True,
        }
    ).encode("utf-8")

    def fake_urlopen(req, *args, **kwargs):  # noqa: ARG001
        raise error.HTTPError(req.full_url, 504, "Gateway Timeout", None, io.BytesIO(body))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:8123", command_timeout=1.0, auth_token="t")

    with pytest.raises(BridgeTimeoutError, match="Dispatch deadline"):
        client.send(CommandEnvelope.build("new_design", {}))


def test_bridge_send_maps_409_body_to_bridge_cancelled_error(monkeypatch) -> None:
    body = json.dumps(
        {
            "ok": False,
            "command": "new_design",
            "error": "Command was cancelled before execution.",
            "classification": "cancelled",
            "recoverable": True,
        }
    ).encode("utf-8")

    def fake_urlopen(req, *args, **kwargs):  # noqa: ARG001
        raise error.HTTPError(req.full_url, 409, "Conflict", None, io.BytesIO(body))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:8123", command_timeout=1.0, auth_token="t")

    with pytest.raises(BridgeCancelledError, match="cancelled"):
        client.send(CommandEnvelope.build("new_design", {}))


def test_bridge_send_401_refreshes_file_derived_token_and_retries_once(tmp_path, monkeypatch) -> None:
    token_path = tmp_path / ".paramaitric_auth_token"
    token_path.write_text("stale-token", encoding="utf-8")
    monkeypatch.setattr(bridge_client_module.Path, "home", lambda: tmp_path)

    unauthorized_body = json.dumps(
        {
            "ok": False,
            "error": "Access denied: invalid or missing authentication token.",
            "classification": "unauthorized",
            "recoverable": False,
        }
    ).encode("utf-8")

    attempts: list[str] = []

    class _OkResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):  # noqa: ANN002
            return False

        def read(self):
            return json.dumps({"ok": True, "command": "new_design", "result": {}}).encode("utf-8")

    def fake_urlopen(req, *args, **kwargs):  # noqa: ARG001
        headers = {k.lower(): v for k, v in req.headers.items()}
        token_used = headers.get("x-paramaitric-auth")
        attempts.append(token_used)
        if token_used == "stale-token":
            # Simulate an out-of-band token rotation (e.g. bridge restarted)
            # so the refresh actually picks up a different value.
            token_path.write_text("fresh-token", encoding="utf-8")
            raise error.HTTPError(req.full_url, 401, "Unauthorized", None, io.BytesIO(unauthorized_body))
        return _OkResponse()

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)

    client = BridgeClient("http://127.0.0.1:8123", command_timeout=1.0)
    # Force the token to resolve from the (patched-home) file rather than an
    # explicit constructor argument.
    result = client.send(CommandEnvelope.build("new_design", {}))

    assert result["ok"] is True
    # Exactly one retry: the first attempt used the stale token, the retry
    # picked up the freshly-rotated one, and no further attempts were made.
    assert attempts == ["stale-token", "fresh-token"]


def test_bridge_send_401_does_not_retry_for_explicit_token(monkeypatch) -> None:
    unauthorized_body = json.dumps(
        {
            "ok": False,
            "error": "Access denied: invalid or missing authentication token.",
            "classification": "unauthorized",
            "recoverable": False,
        }
    ).encode("utf-8")

    attempts: list[str] = []

    def fake_urlopen(req, *args, **kwargs):  # noqa: ARG001
        headers = {k.lower(): v for k, v in req.headers.items()}
        attempts.append(headers.get("x-paramaitric-auth"))
        raise error.HTTPError(req.full_url, 401, "Unauthorized", None, io.BytesIO(unauthorized_body))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)

    client = BridgeClient("http://127.0.0.1:8123", command_timeout=1.0, auth_token="explicit-token")
    with pytest.raises(RuntimeError, match="Bridge command failed"):
        client.send(CommandEnvelope.build("new_design", {}))

    # Exactly one attempt: an explicit token must never trigger a refresh-and-retry.
    assert attempts == ["explicit-token"]
