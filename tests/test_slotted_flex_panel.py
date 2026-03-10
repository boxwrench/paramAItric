from __future__ import annotations
import pytest
from pathlib import Path
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

def test_slotted_flex_panel_valid(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    
    result = server.create_slotted_flex_panel({
        "panel_width_cm": 15.0,
        "panel_depth_cm": 10.0,
        "panel_thickness_cm": 0.4,
        "slot_length_cm": 8.0,
        "slot_width_cm": 0.2,
        "slot_spacing_cm": 1.0,
        "end_margin_cm": 1.0,
        "edge_fillet_radius_cm": 0.05,
        "output_path": str(tmp_path / "panel.stl")
    })
    assert result["ok"] is True
