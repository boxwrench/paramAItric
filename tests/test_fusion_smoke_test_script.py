from __future__ import annotations

from scripts.fusion_smoke_test import main


def test_smoke_script_exits_when_bridge_is_not_reachable() -> None:
    exit_code = main([])
    assert exit_code == 1
