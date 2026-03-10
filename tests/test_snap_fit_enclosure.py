from __future__ import annotations
import pytest
from pathlib import Path
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

def test_snap_fit_enclosure_valid(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    
    result = server.create_snap_fit_enclosure({
        "box_width_cm": 10.0,
        "box_depth_cm": 8.0,
        "box_height_cm": 6.0,
        "wall_thickness_cm": 0.3,
        "lid_height_cm": 0.5,
        "snap_bead_width_cm": 0.3,
        "snap_bead_height_cm": 0.15,
        "clearance_cm": 0.02,
        "front_hole_diameter_cm": 2.0,
        "front_hole_center_z_cm": 2.5,
        "side_hole_diameter_cm": 1.5,
        "side_hole_center_z_cm": 2.0,
        "output_path_box": str(tmp_path / "box.stl"),
        "output_path_lid": str(tmp_path / "lid.stl")
    })
    assert result["ok"] is True
