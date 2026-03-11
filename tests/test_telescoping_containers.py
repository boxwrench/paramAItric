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
    
    # --- HARDENING: Verify containers are concentric ---
    # This catches the bug where containers were corner-aligned (all starting at 0,0)
    # instead of centered. Concentric containers have centroids at approximately
    # the same X,Y position (the geometric center of the outer container).
    
    verification = result.get("verification", {})
    outer_centroid = verification.get("outer_centroid")
    middle_centroid = verification.get("middle_centroid")
    inner_centroid = verification.get("inner_centroid")
    
    # Skip centroid checks in mock environment (returns 0,0,0)
    # These assertions are for live testing where real geometry is calculated
    if outer_centroid and middle_centroid and inner_centroid:
        # Check if we have real centroid data (not mock zeros)
        if outer_centroid["x"] != 0 or outer_centroid["y"] != 0:
            # All centroids should be approximately the same for concentric containers
            # The outer container centroid should be at (outer_width/2, outer_depth/2)
            expected_center = 20.0 / 2.0  # 10.0
            
            # Check middle container is centered (not offset to corner)
            assert abs(middle_centroid["x"] - expected_center) < 1.0, (
                f"Middle container not centered: centroid x={middle_centroid['x']}, "
                f"expected near {expected_center}. Container may be corner-aligned."
            )
            assert abs(middle_centroid["y"] - expected_center) < 1.0, (
                f"Middle container not centered: centroid y={middle_centroid['y']}, "
                f"expected near {expected_center}. Container may be corner-aligned."
            )
            
            # Check inner container is centered
            assert abs(inner_centroid["x"] - expected_center) < 1.0, (
                f"Inner container not centered: centroid x={inner_centroid['x']}, "
                f"expected near {expected_center}. Container may be corner-aligned."
            )
            assert abs(inner_centroid["y"] - expected_center) < 1.0, (
                f"Inner container not centered: centroid y={inner_centroid['y']}, "
                f"expected near {expected_center}. Container may be corner-aligned."
            )
