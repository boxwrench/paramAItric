"""Mock-to-live dispatcher upgrade.

With "Run on Startup" the add-in boots on Fusion's home screen where no design
document is active, so bootstrap falls back to the mock adapter and — before
this feature — stayed there until a manual Stop/Run. try_upgrade_to_live()
re-runs the bootstrap (from a documentActivated handler on Fusion's main
thread) and swaps the registry, dispatch driver, and design state in place.
"""
from __future__ import annotations

import pytest

from fusion_addin import dispatcher as dispatcher_module
from fusion_addin.bootstrap import LiveBootstrapResult, MockBootstrapResult
from fusion_addin.dispatcher import CommandDispatcher, DispatchDriver
from fusion_addin.ops import mock_ops
from fusion_addin.ops.live_ops import FusionExecutionContext, RecordingFakeFusionAdapter


class _FakeMainThreadDriver(DispatchDriver):
    """Stands in for FusionMainThreadDispatchDriver (which needs adsk.core)."""

    def __init__(self, dispatcher: CommandDispatcher, app: object) -> None:
        self.dispatcher = dispatcher
        self.app = app

    def notify(self) -> None:
        self.dispatcher.process_pending()


class _FusionEnvironment:
    """Simulates Fusion's design availability: home screen first, design later."""

    def __init__(self) -> None:
        self.adapter = RecordingFakeFusionAdapter()
        self.adapter.app = object()  # real adapters carry the adsk Application
        self.design_open = False

    def open_design(self) -> None:
        self.design_open = True

    def bootstrap(self, workflow_registry):
        if not self.design_open:
            return MockBootstrapResult(mode="mock", workflow_registry=workflow_registry)
        return LiveBootstrapResult(
            mode="live",
            workflow_registry=workflow_registry,
            execution_context=FusionExecutionContext(adapter=self.adapter),
        )


@pytest.fixture()
def fusion_env(monkeypatch) -> _FusionEnvironment:
    env = _FusionEnvironment()
    monkeypatch.setattr(dispatcher_module, "bootstrap_addin", env.bootstrap)
    monkeypatch.setattr(
        dispatcher_module, "FusionMainThreadDispatchDriver", _FakeMainThreadDriver
    )
    return env


def test_upgrade_swaps_mock_dispatcher_to_live(fusion_env) -> None:
    # Run-on-Startup boot: home screen, no design -> mock fallback.
    dispatcher = CommandDispatcher()
    assert dispatcher.mode == "mock"

    # No design yet: upgrade attempts change nothing.
    assert dispatcher.try_upgrade_to_live() is False
    assert dispatcher.mode == "mock"

    # User opens a design (documentActivated fires and calls the upgrade).
    fusion_env.open_design()
    assert dispatcher.try_upgrade_to_live() is True

    assert dispatcher.mode == "live"
    assert isinstance(dispatcher._dispatch_driver, _FakeMainThreadDriver)
    # Live registry answers commands end to end through the fake adapter.
    response = dispatcher.submit("new_design", {"name": "post-upgrade"})
    assert response["ok"] is True
    assert ("new_design", {"name": "post-upgrade"}) in [
        (name, args) for name, args in fusion_env.adapter.calls
    ]


def test_upgrade_resets_mock_era_design_state(fusion_env) -> None:
    dispatcher = CommandDispatcher()
    dispatcher.submit("new_design", {"name": "mock-era"})
    assert dispatcher.state.design_name == "mock-era"

    fusion_env.open_design()
    assert dispatcher.try_upgrade_to_live() is True

    # Mock-era tokens mean nothing to live Fusion; state must start fresh.
    assert dispatcher.state.design_name != "mock-era"


def test_upgrade_is_idempotent_once_live(fusion_env) -> None:
    fusion_env.open_design()
    dispatcher = CommandDispatcher()
    assert dispatcher.mode == "live"
    driver_before = dispatcher._dispatch_driver
    assert dispatcher.try_upgrade_to_live() is True
    assert dispatcher._dispatch_driver is driver_before


def test_upgrade_refuses_custom_registry_dispatchers(fusion_env) -> None:
    dispatcher = CommandDispatcher(
        registry_builder=lambda: mock_ops.build_registry(),
        mode="mock",
    )
    fusion_env.open_design()
    # Explicitly-built dispatchers (tests, embedded uses) must never be
    # silently swapped out from under their owner.
    assert dispatcher.try_upgrade_to_live() is False
    assert dispatcher.mode == "mock"
