from __future__ import annotations
import pytest
from pathlib import Path
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

def test_wire_clamp_valid(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    
    result = server.create_wire_clamp({
        "body_length_cm": 4.0,
        "body_width_cm": 3.0,
        "body_height_cm": 2.0,
        "bore_radius_cm": 0.35,
        "lead_in_depth_cm": 0.8,
        "lead_in_exit_radius_cm": 0.6,
        "rib_count": 4,
        "rib_height_cm": 0.05,
        "rib_width_cm": 0.1,
        "rib_spacing_cm": 0.8,
        "split_slot_width_cm": 0.1,
        "output_path": str(tmp_path / "clamp.stl")
    })
    assert result["ok"] is True
