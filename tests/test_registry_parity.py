"""Mock/live operation-registry parity.

The mock adapter (fusion_addin/ops/mock_ops.py) and the live adapter
(fusion_addin/ops/live_ops.py) each register their own command set. Nothing
else enforces that they stay in sync, and drift is invisible until a live
Fusion session hits "Unknown command: ..." (this happened with draw_polygon,
which shipped in the mock on 2026-06 but only reached the live adapter on
2026-07-10). This test makes that drift a same-day suite failure.
"""
from __future__ import annotations

from fusion_addin.ops import live_ops, mock_ops
from fusion_addin.ops.live_ops import FusionExecutionContext, RecordingFakeFusionAdapter


def test_mock_and_live_registries_expose_identical_commands() -> None:
    mock_commands = set(mock_ops.build_registry().list_commands())
    live_registry = live_ops.build_registry(
        execution_context=FusionExecutionContext(adapter=RecordingFakeFusionAdapter())
    )
    live_commands = set(live_registry.list_commands())

    mock_only = sorted(mock_commands - live_commands)
    live_only = sorted(live_commands - mock_commands)
    assert not mock_only and not live_only, (
        "Mock and live operation registries have drifted.\n"
        f"  commands only in mock_ops: {mock_only}\n"
        f"  commands only in live_ops: {live_only}\n"
        "Register the missing command(s) in the lagging adapter (or remove the "
        "orphan) so both adapters accept the same command surface."
    )
