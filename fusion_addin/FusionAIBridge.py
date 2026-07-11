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
# Fusion garbage-collects event handlers that are not referenced from module
# scope, so the (event, handler) pair must be pinned here for the add-in's
# lifetime.
_upgrade_watcher: tuple[object, object] | None = None


def _register_live_upgrade_watcher(service: HTTPBridgeService) -> None:
    """Auto-upgrade the bridge from mock to live when a design appears.

    With "Run on Startup" the add-in boots on Fusion's home screen, where no
    design document is active, so the initial bootstrap falls back to the mock
    adapter. Watching documentActivated (which fires on Fusion's main thread)
    lets the dispatcher retry the live bootstrap the moment any design is
    opened, created, or switched to — no manual Stop/Run needed.
    """
    global _upgrade_watcher
    if service.dispatcher.mode != "mock":
        return
    try:
        import adsk.core  # type: ignore[import-not-found]
    except ImportError:
        return  # Running outside Fusion (tests, dev server): nothing to watch.
    app = adsk.core.Application.get()
    if app is None:
        return

    class _DocumentActivatedHandler(adsk.core.DocumentEventHandler):  # type: ignore[misc, valid-type]
        def __init__(self, bridge_service: HTTPBridgeService) -> None:
            super().__init__()
            self._service = bridge_service

        def notify(self, args: object) -> None:  # noqa: ARG002
            # Cheap no-op once live; retries on every activation until then.
            self._service.dispatcher.try_upgrade_to_live()

    handler = _DocumentActivatedHandler(service)
    app.documentActivated.add(handler)
    _upgrade_watcher = (app.documentActivated, handler)


def _remove_live_upgrade_watcher() -> None:
    global _upgrade_watcher
    if _upgrade_watcher is None:
        return
    event, handler = _upgrade_watcher
    try:
        event.remove(handler)  # type: ignore[attr-defined]
    except RuntimeError:
        pass
    _upgrade_watcher = None


def run(context: object | None = None) -> HTTPBridgeService:
    """Fusion 360 add-in entrypoint scaffold."""
    _ = context
    global _service
    if _service is None:
        _service = HTTPBridgeService(dispatcher=CommandDispatcher())
        _service.start()
        _register_live_upgrade_watcher(_service)
    return _service


def stop(context: object | None = None) -> None:
    """Fusion 360 add-in shutdown scaffold."""
    _ = context
    global _service
    _remove_live_upgrade_watcher()
    if _service is not None:
        _service.stop()
        _service = None
