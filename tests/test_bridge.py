from __future__ import annotations

import socket
import threading
from urllib import error

import pytest

from mcp_server import bridge_client as bridge_client_module
from mcp_server.bridge_client import BridgeCancelledError, BridgeClient, BridgeTimeoutError
from mcp_server.schemas import CommandEnvelope


def test_bridge_health_endpoint(running_bridge) -> None:
    _, base_url = running_bridge
    client = BridgeClient(base_url)
    health = client.health()
    assert health["ok"] is True
    assert health["status"] == "ready"
    assert health["mode"] == "mock"
    assert any(workflow["name"] == "spacer" for workflow in health["workflow_catalog"])


def test_bridge_runs_single_command(running_bridge) -> None:
    _, base_url = running_bridge
    client = BridgeClient(base_url)
    result = client.send(CommandEnvelope.build("new_design", {"name": "Smoke Test"}))
    assert result["ok"] is True
    assert result["result"]["design_name"] == "Smoke Test"


def test_bridge_cancel_raises_for_unknown_request(running_bridge) -> None:
    _, base_url = running_bridge
    client = BridgeClient(base_url)
    with pytest.raises(RuntimeError, match="Bridge cancel failed"):
        client.cancel("missing")


def test_bridge_raises_on_unknown_command(running_bridge) -> None:
    _, base_url = running_bridge
    client = BridgeClient(base_url)
    with pytest.raises(RuntimeError, match="Bridge command failed"):
        client.send(CommandEnvelope.build("nonexistent_command", {}))


def test_bridge_raises_on_bad_operation_arguments(running_bridge) -> None:
    _, base_url = running_bridge
    client = BridgeClient(base_url)
    # extrude_profile with an invalid profile_token should return HTTP 400
    with pytest.raises(RuntimeError, match="Bridge command failed"):
        client.send(CommandEnvelope.build("extrude_profile", {"profile_token": "bad:token", "distance_cm": 1.0, "body_name": "x"}))


def test_bridge_client_configurable_timeouts() -> None:
    client = BridgeClient("http://127.0.0.1:8123", health_timeout=2.0, command_timeout=15.0)
    assert client.health_timeout == 2.0
    assert client.command_timeout == 15.0


def test_bridge_health_raises_when_server_unreachable(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(ConnectionRefusedError("actively refused"))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:1", health_timeout=1.0)
    with pytest.raises(RuntimeError, match="not reachable"):
        client.health()


def test_bridge_send_raises_when_server_unreachable(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(ConnectionRefusedError("actively refused"))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:1", command_timeout=1.0)
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

    client = BridgeClient(f"http://127.0.0.1:{port}", command_timeout=0.5)
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

    client = BridgeClient(f"http://127.0.0.1:{port}", health_timeout=0.5)
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
    client = BridgeClient("http://127.0.0.1:8123", command_timeout=1.0)
    with pytest.raises(BridgeCancelledError, match="cancelled"):
        client.send(CommandEnvelope.build("new_design", {}))


def test_bridge_health_raises_on_cancelled_request(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(OSError(995, "The I/O operation has been aborted."))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:8123", health_timeout=1.0)
    with pytest.raises(BridgeCancelledError, match="cancelled"):
        client.health()


def test_bridge_cancel_raises_when_server_unreachable(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):  # noqa: ARG001
        raise error.URLError(ConnectionRefusedError("actively refused"))

    monkeypatch.setattr(bridge_client_module.request, "urlopen", fake_urlopen)
    client = BridgeClient("http://127.0.0.1:1", command_timeout=1.0)
    with pytest.raises(RuntimeError, match="not reachable"):
        client.cancel("req-1")
