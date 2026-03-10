from __future__ import annotations
import pytest
from pathlib import Path
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

def test_telescoping_containers_valid(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    
    result = server.create_telescoping_containers({
        "outer_width_cm": 20.0,
        "outer_depth_cm": 20.0,
        "outer_height_cm": 8.0,
        "wall_thickness_cm": 0.3,
        "middle_clearance_cm": 0.4,
        "inner_clearance_cm": 0.4,
        "output_path_outer": str(tmp_path / "outer.stl"),
        "output_path_middle": str(tmp_path / "middle.stl"),
        "output_path_inner": str(tmp_path / "inner.stl")
    })
    assert result["ok"] is True
