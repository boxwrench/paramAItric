from __future__ import annotations

from collections.abc import Iterator

import pytest

from fusion_addin.http_bridge import HTTPBridgeService


@pytest.fixture
def running_bridge(tmp_path) -> Iterator[tuple[HTTPBridgeService, str]]:
    service = HTTPBridgeService(port=0)
    service.start()
    host, port = service.address
    try:
        yield service, f"http://{host}:{port}"
    finally:
        service.stop()
