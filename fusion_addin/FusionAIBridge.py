from __future__ import annotations

import os
import sys

# Add repo root to path so Fusion can find mcp_server
_addin_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_addin_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def _clear_cached_project_modules() -> None:
    """Reload project code on Fusion Stop -> Run during development.

    Fusion re-executes this manifest entrypoint but keeps imported dependency
    modules in its embedded Python interpreter. Clearing only ParamAItric
    submodules here makes the next imports read the current files without
    requiring a full Fusion restart.
    """
    current_module = __name__
    prefixes = ("fusion_addin.", "mcp_server.")
    cached = [
        module_name
        for module_name in sys.modules
        if module_name != current_module
        and module_name.startswith(prefixes)
    ]
    for module_name in sorted(cached, key=lambda name: name.count("."), reverse=True):
        sys.modules.pop(module_name, None)


_clear_cached_project_modules()

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
