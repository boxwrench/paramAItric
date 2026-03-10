from __future__ import annotations
import pytest
from pathlib import Path
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

def test_ratchet_wheel_valid(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    
    result = server.create_ratchet_wheel({
        "outer_diameter_cm": 6.0,
        "thickness_cm": 0.8,
        "bore_diameter_cm": 1.0,
        "tooth_count": 10,
        "tooth_height_cm": 0.4,
        "slope_width_cm": 0.5,
        "locking_width_cm": 0.1,
        "tip_fillet_cm": 0.05,
        "output_path": str(tmp_path / "wheel.stl")
    })
    assert result["ok"] is True
