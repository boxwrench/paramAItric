from __future__ import annotations

import pytest

import mcp_server.runtime_info as runtime_info
from mcp_server.bridge_client import BridgeClient
from mcp_server.server import ParamAIToolServer


@pytest.fixture(autouse=True)
def _reset_active_profile_cad_endpoint():
    original = runtime_info.ACTIVE_PROFILE_CAD_ENDPOINT
    try:
        yield
    finally:
        runtime_info.ACTIVE_PROFILE_CAD_ENDPOINT = original


def test_server_uses_active_profile_cad_endpoint_when_set() -> None:
    runtime_info.ACTIVE_PROFILE_CAD_ENDPOINT = "http://127.0.0.1:9999"

    server = ParamAIToolServer()

    assert server.bridge_client.base_url == "http://127.0.0.1:9999"


def test_server_falls_back_to_default_endpoint_when_unset() -> None:
    runtime_info.ACTIVE_PROFILE_CAD_ENDPOINT = None

    server = ParamAIToolServer()

    assert server.bridge_client.base_url == BridgeClient().base_url


def test_explicit_bridge_client_is_never_overridden() -> None:
    runtime_info.ACTIVE_PROFILE_CAD_ENDPOINT = "http://127.0.0.1:9999"
    explicit_client = BridgeClient(base_url="http://127.0.0.1:5555")

    server = ParamAIToolServer(bridge_client=explicit_client)

    assert server.bridge_client is explicit_client
    assert server.bridge_client.base_url == "http://127.0.0.1:5555"
