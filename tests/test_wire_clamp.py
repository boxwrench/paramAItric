from __future__ import annotations
import pytest
import math
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
    
    # --- HARDENING: Verify workflow stages completed ---
    stages = result.get("stages", [])
    
    # Find key stages that must exist
    bore_stage = next((s for s in stages if s.get("role") == "bore"), None)
    assert bore_stage is not None, "Missing bore cut stage"
    assert bore_stage.get("status") == "completed", "Bore cut failed"
    
    # Verify body count stayed at 1 after bore (catches split body issues)
    bore_verify_stage = next((s for s in stages if s.get("stage") == "verify_geometry" and s.get("role") == "after_bore"), None)
    assert bore_verify_stage is not None, "Missing bore verification stage"
    assert bore_verify_stage.get("body_count") == 1, "Bore cut split the body"
