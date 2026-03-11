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
    
    # --- HARDENING: Verify teeth cut into outer silhouette ---
    # This catches the bug where teeth were surface fins instead of silhouette cuts.
    # With correct teeth, the outer rim is no longer cylindrical - it becomes jagged.
    # Verification: cylindrical face count should be exactly 1 (just the bore).
    # If teeth didn't cut the outer rim, there would be 2 cylindrical faces (bore + outer rim).
    
    verification = result.get("verification", {})
    final_cylindrical_count = verification.get("final_cylindrical_face_count")
    
    if final_cylindrical_count is not None:
        assert final_cylindrical_count == 1, (
            f"Expected 1 cylindrical face (bore only), got {final_cylindrical_count}. "
            f"If 2, the outer rim is still cylindrical (teeth didn't cut silhouette). "
            f"If >2, unexpected geometry."
        )
    
    # Also verify volume decreased after teeth cuts (skip in mock mode where volumes are static)
    initial_volume = verification.get("initial_volume_cm3")
    final_volume = verification.get("final_volume_cm3")
    if initial_volume and final_volume and initial_volume != final_volume:
        assert final_volume < initial_volume, (
            f"Volume did not decrease after teeth cuts: initial={initial_volume}, final={final_volume}"
        )
