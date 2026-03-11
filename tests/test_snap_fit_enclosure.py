from __future__ import annotations
import pytest
from pathlib import Path
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

def test_snap_fit_enclosure_valid(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    
    box_width_cm = 10.0
    box_depth_cm = 8.0
    wall_thickness_cm = 0.3
    clearance_cm = 0.02
    
    result = server.create_snap_fit_enclosure({
        "box_width_cm": box_width_cm,
        "box_depth_cm": box_depth_cm,
        "box_height_cm": 6.0,
        "wall_thickness_cm": wall_thickness_cm,
        "lid_height_cm": 0.5,
        "snap_bead_width_cm": 0.3,
        "snap_bead_height_cm": 0.15,
        "clearance_cm": clearance_cm,
        "front_hole_diameter_cm": 2.0,
        "front_hole_center_z_cm": 2.5,
        "side_hole_diameter_cm": 1.5,
        "side_hole_center_z_cm": 2.0,
        "output_path_box": str(tmp_path / "box.stl"),
        "output_path_lid": str(tmp_path / "lid.stl")
    })
    assert result["ok"] is True
    
    # --- HARDENING: Verify lid wraps over box ---
    # Lid outer dimensions should exceed box outer dimensions
    # lid_outer = box_outer + 2*wall + clearance
    expected_lid_width = box_width_cm + (wall_thickness_cm * 2.0) + clearance_cm
    expected_lid_depth = box_depth_cm + (wall_thickness_cm * 2.0) + clearance_cm
    
    verification = result.get("verification", {})
    lid_bbox = verification.get("lid_bounding_box", {})
    box_bbox = verification.get("box_bounding_box", {})
    
    if lid_bbox and box_bbox:
        lid_width = lid_bbox.get("width_cm", 0)
        lid_depth = lid_bbox.get("depth_cm", 0)
        box_width = box_bbox.get("width_cm", 0)
        box_depth = box_bbox.get("depth_cm", 0)
        
        assert lid_width > box_width, (
            f"Lid width ({lid_width}) should exceed box width ({box_width}). "
            f"Lid should wrap over box like a cap, not sit flush/inside."
        )
        assert lid_depth > box_depth, (
            f"Lid depth ({lid_depth}) should exceed box depth ({box_depth}). "
            f"Lid should wrap over box like a cap, not sit flush/inside."
        )
    
    # Verify two bodies exported
    assert verification.get("body_count") == 2, "Expected 2 bodies (box and lid with bead)"
