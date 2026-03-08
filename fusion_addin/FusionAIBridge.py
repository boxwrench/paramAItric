from __future__ import annotations

from fusion_addin.dispatcher import CommandDispatcher
from fusion_addin.http_bridge import HTTPBridgeService

_service: HTTPBridgeService | None = None


def run(context: object | None = None) -> HTTPBridgeService:
    """Fusion 360 add-in entrypoint scaffold."""
    _ = context
    global _service
    if _service is None:
        _service = HTTPBridgeService(dispatcher=CommandDispatcher())
        _service.start()
    return _service


def stop(context: object | None = None) -> None:
    """Fusion 360 add-in shutdown scaffold."""
    _ = context
    global _service
    if _service is not None:
        _service.stop()
        _service = None
