from __future__ import annotations

import os
import sys

# Add repo root to path so Fusion can find mcp_server
_addin_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_addin_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

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
