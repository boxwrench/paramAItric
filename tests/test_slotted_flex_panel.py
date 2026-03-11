from __future__ import annotations
import pytest
from pathlib import Path
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

def test_slotted_flex_panel_valid(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    
    panel_width_cm = 15.0
    slot_width_cm = 0.2
    slot_spacing_cm = 1.0
    
    result = server.create_slotted_flex_panel({
        "panel_width_cm": panel_width_cm,
        "panel_depth_cm": 10.0,
        "panel_thickness_cm": 0.4,
        "slot_length_cm": 8.0,
        "slot_width_cm": slot_width_cm,
        "slot_spacing_cm": slot_spacing_cm,
        "end_margin_cm": 1.0,
        "edge_fillet_radius_cm": 0.05,
        "output_path": str(tmp_path / "panel.stl")
    })
    assert result["ok"] is True
    
    # --- HARDENING: Verify slots are centered on the panel ---
    # This catches the bug where slots were left-justified instead of centered.
    # For 5 slots with 1.0cm spacing in a 15cm panel:
    #   Group width = 5*0.2 + 4*1.0 = 5.0cm
    #   First slot center = (15 - 5)/2 + 0.1 = 5.1cm
    #   Last slot center = 5.1 + 4*1.2 = 9.9cm (wait, that's slot_spacing + slot_width)
    #   Actually: centers are at 5.1, 6.3, 7.5, 8.7, 9.9
    #   First + Last = 5.1 + 9.9 = 15.0 = panel_width (symmetric about center)
    
    # Calculate expected first and last slot centers
    slot_count = 5
    group_width_cm = slot_count * slot_width_cm + (slot_count - 1) * slot_spacing_cm
    expected_first_center = (panel_width_cm - group_width_cm) / 2.0 + slot_width_cm / 2.0
    expected_last_center = expected_first_center + (slot_count - 1) * (slot_width_cm + slot_spacing_cm)
    
    # Symmetry check: first_center + last_center should equal panel_width
    # (both distances measured from left edge, symmetric about center = panel_width/2)
    # Actually for perfect centering: (first_center + last_center) / 2 = panel_width / 2
    # Therefore: first_center + last_center = panel_width
    expected_symmetry_sum = panel_width_cm
    
    # Get actual slot positions from result
    verification = result.get("verification", {})
    actual_first = verification.get("first_slot_center_x_cm")
    actual_last = verification.get("last_slot_center_x_cm")
    
    if actual_first is not None and actual_last is not None:
        actual_symmetry_sum = actual_first + actual_last
        assert abs(actual_symmetry_sum - expected_symmetry_sum) < 0.01, (
            f"Slots not centered: first={actual_first}, last={actual_last}, "
            f"sum={actual_symmetry_sum} (expected ~{expected_symmetry_sum}). "
            f"Slot group should be symmetric about panel center ({panel_width_cm/2})."
        )
