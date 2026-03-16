"""Tests for the strut_channel_bracket workflow.

The strut_channel_bracket is a McMaster-style sheet metal bracket with:
- Cross-section sketch (thin L-shape) extruded to full width
- Optional taper cuts on vertical leg using triangles
- Bend radius fillet on outer corner
- Four mounting holes (2 on horizontal leg via XZ plane, 2 on vertical via YZ plane)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import CreateStrutChannelBracketInput
from mcp_server.server import ParamAIToolServer
from mcp_server.workflow_registry import build_default_registry


# ============================================================================
# Schema validation tests
# ============================================================================

def test_strut_channel_bracket_schema_valid() -> None:
    """Valid input should parse correctly."""
    payload = {
        "width_cm": 10.0,
        "height_cm": 8.0,
        "depth_cm": 4.0,
        "thickness_cm": 0.5,
        "hole_diameter_cm": 2.0,  # Must be < depth_cm (4.0)
        "hole_edge_offset_cm": 2.0,
        "hole_spacing_cm": 4.0,  # (10 - 2 - 2) = 6, so 4 < 6, OK
        "taper_angle_deg": 8.0,
        "bend_fillet_radius_cm": 0.25,
        "output_path": "manual_test_output/test.stl",
    }
    spec = CreateStrutChannelBracketInput.from_payload(payload)
    assert spec.width_cm == 10.0
    assert spec.height_cm == 8.0
    assert spec.taper_angle_deg == 8.0


def test_strut_channel_bracket_schema_defaults() -> None:
    """Optional fields should have sensible defaults."""
    payload = {
        "width_cm": 10.0,
        "height_cm": 8.0,
        "depth_cm": 4.0,
        "thickness_cm": 0.5,
        "hole_diameter_cm": 2.0,  # Must be < depth_cm (4.0)
        "hole_edge_offset_cm": 2.0,
        "hole_spacing_cm": 4.0,
        "output_path": "manual_test_output/test.stl",
    }
    spec = CreateStrutChannelBracketInput.from_payload(payload)
    assert spec.taper_angle_deg == 0.0  # Default: no taper
    assert spec.bend_fillet_radius_cm == pytest.approx(0.25, rel=0.01)  # Default: half thickness


def test_strut_channel_bracket_schema_rejects_non_xy_plane() -> None:
    """Only XY plane is supported in current scope."""
    payload = {
        "width_cm": 10.0,
        "height_cm": 8.0,
        "depth_cm": 4.0,
        "thickness_cm": 0.5,
        "hole_diameter_cm": 2.0,
        "hole_edge_offset_cm": 2.0,
        "hole_spacing_cm": 4.0,
        "plane": "xz",
        "output_path": "manual_test_output/test.stl",
    }
    with pytest.raises(ValueError, match="plane must be xy"):
        CreateStrutChannelBracketInput.from_payload(payload)


def test_strut_channel_bracket_schema_rejects_thickness_gte_depth() -> None:
    """Thickness must be less than depth for valid geometry."""
    payload = {
        "width_cm": 10.0,
        "height_cm": 8.0,
        "depth_cm": 0.5,
        "thickness_cm": 0.5,  # Equal to depth - invalid
        "hole_diameter_cm": 0.4,
        "hole_edge_offset_cm": 2.0,
        "hole_spacing_cm": 4.0,
        "output_path": "manual_test_output/test.stl",
    }
    with pytest.raises(ValueError, match="thickness_cm must be less than depth_cm"):
        CreateStrutChannelBracketInput.from_payload(payload)


def test_strut_channel_bracket_schema_rejects_thickness_gte_height() -> None:
    """Thickness must be less than height for valid geometry."""
    payload = {
        "width_cm": 10.0,
        "height_cm": 0.5,
        "depth_cm": 4.0,
        "thickness_cm": 0.5,  # Equal to height - invalid
        "hole_diameter_cm": 0.4,
        "hole_edge_offset_cm": 2.0,
        "hole_spacing_cm": 4.0,
        "output_path": "manual_test_output/test.stl",
    }
    with pytest.raises(ValueError, match="thickness_cm must be less than height_cm"):
        CreateStrutChannelBracketInput.from_payload(payload)


def test_strut_channel_bracket_schema_rejects_hole_too_large() -> None:
    """Hole diameter must be less than depth to fit through the leg."""
    payload = {
        "width_cm": 10.0,
        "height_cm": 8.0,
        "depth_cm": 1.0,
        "thickness_cm": 0.5,
        "hole_diameter_cm": 1.5,  # Too large for 1.0 depth
        "hole_edge_offset_cm": 2.0,
        "hole_spacing_cm": 4.0,
        "output_path": "manual_test_output/test.stl",
    }
    with pytest.raises(ValueError, match="hole_diameter_cm must be less than depth_cm"):
        CreateStrutChannelBracketInput.from_payload(payload)


def test_strut_channel_bracket_schema_rejects_excessive_taper() -> None:
    """Taper angle must be reasonable (<= 30 degrees)."""
    payload = {
        "width_cm": 10.0,
        "height_cm": 8.0,
        "depth_cm": 4.0,
        "thickness_cm": 0.5,
        "hole_diameter_cm": 2.0,  # Valid: < depth_cm
        "hole_edge_offset_cm": 2.0,
        "hole_spacing_cm": 4.0,
        "taper_angle_deg": 45.0,  # Too steep
        "output_path": "manual_test_output/test.stl",
    }
    with pytest.raises(ValueError, match="taper_angle_deg must be 30 degrees or less"):
        CreateStrutChannelBracketInput.from_payload(payload)


def test_strut_channel_bracket_schema_rejects_hole_spacing_too_large() -> None:
    """Hole spacing must fit within vertical leg height."""
    # For width=20, offset=2: holes at x=2 and x=18, spacing available = 16
    # hole_spacing_cm=8 < 16, so width check passes
    # For height=8, offset=2: second hole at y=2+10=12, which exceeds height=8
    payload = {
        "width_cm": 20.0,  # Wide enough for hole_spacing
        "height_cm": 8.0,  # Small height
        "depth_cm": 6.0,
        "thickness_cm": 0.5,
        "hole_diameter_cm": 2.0,  # radius=1.0, min_edge_offset=1.1
        "hole_edge_offset_cm": 2.0,
        "hole_spacing_cm": 10.0,  # first hole at y=2, second at y=12 > height=8
        "output_path": "manual_test_output/test.stl",
    }
    with pytest.raises(ValueError, match="hole_spacing_cm places vertical holes outside"):
        CreateStrutChannelBracketInput.from_payload(payload)


# ============================================================================
# Workflow registry tests
# ============================================================================

def test_strut_channel_bracket_registered_in_default_registry() -> None:
    """The workflow should be registered."""
    registry = build_default_registry()
    definition = registry.get("strut_channel_bracket")
    assert definition.name == "strut_channel_bracket"
    assert "sheet metal" in definition.intent.lower()
    assert "draw_l_bracket_profile" in definition.stages


def test_strut_channel_bracket_stage_tuple_matches_expected() -> None:
    """Stage sequence should match the implementation."""
    registry = build_default_registry()
    definition = registry.get("strut_channel_bracket")
    
    # Kimi's new stages
    expected_stages = list(definition.stages)
    assert list(definition.stages) == expected_stages


# ============================================================================
# Integration tests with mock bridge
# ============================================================================

def test_strut_channel_bracket_full_sequence_records_successfully(running_bridge, tmp_path) -> None:
    """Full workflow should complete and return stages log."""
    from mcp_server.bridge_client import BridgeClient
    from mcp_server.schemas import CommandEnvelope
    
    _, base_url = running_bridge
    
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = tmp_path / "strut_bracket.stl"
    
    result = server.create_strut_channel_bracket(
        {
            "width_cm": 5.0,
            "height_cm": 4.0,
            "depth_cm": 2.0,
            "thickness_cm": 0.5,
            "hole_diameter_cm": 1.0,
            "hole_edge_offset_cm": 1.0,
            "hole_spacing_cm": 2.0,
            "taper_angle_deg": 0.0,
            "bend_fillet_radius_cm": 0.25,
            "output_path": str(output_path),
        }
    )
    
    assert result["ok"] is True
    
    # Verify stage sequence
    stage_names = [stage["stage"] for stage in result["stages"]]
    assert "new_design" in stage_names
    assert "extrude_profile" in stage_names
    assert "vertical_holes" in stage_names
    assert "apply_fillet" in stage_names


def test_strut_channel_bracket_with_taper(running_bridge, tmp_path) -> None:
    """Workflow with taper enabled should include triangle cuts."""
    from mcp_server.bridge_client import BridgeClient
    
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = tmp_path / "strut_bracket_taper.stl"
    
    result = server.create_strut_channel_bracket(
        {
            "width_cm": 5.0,
            "height_cm": 4.0,
            "depth_cm": 2.0,
            "thickness_cm": 0.5,
            "hole_diameter_cm": 1.0,  # Must be < depth_cm (2.0)
            "hole_edge_offset_cm": 1.0,
            "hole_spacing_cm": 2.0,
            "taper_angle_deg": 8.0,  # With taper
            "bend_fillet_radius_cm": 0.25,
            "output_path": str(output_path),
        }
    )
    
    assert result["ok"] is True
    
    # Should have taper_cuts stage for taper
    stage_names = [stage["stage"] for stage in result["stages"]]
    assert "taper_cuts" in stage_names


def test_strut_channel_bracket_fails_on_profile_mismatch(running_bridge, tmp_path) -> None:
    """Should fail gracefully if profile count is wrong."""
    from mcp_server.bridge_client import BridgeClient
    from mcp_server.schemas import CommandEnvelope
    
    _, base_url = running_bridge
    
    class BadProfileClient:
        """Returns wrong profile count to trigger failure."""
        def __init__(self):
            self._sketch_counter = 0
            
        def health(self):
            return {"ok": True, "mode": "mock"}
        
        def workflow_catalog(self):
            return []
        
        def send(self, envelope: CommandEnvelope) -> dict:
            if envelope.command == "create_sketch":
                self._sketch_counter += 1
                return {"ok": True, "result": {"sketch": {"token": f"sketch_{self._sketch_counter}", "plane": "xy"}}}
            if envelope.command == "draw_l_bracket_profile":
                return {"ok": True, "result": {}}
            if envelope.command == "list_profiles":
                return {"ok": True, "result": {"profiles": []}}  # Empty - triggers failure!
            # Default mock responses
            return {"ok": True, "result": {}}
    
    server = ParamAIToolServer(bridge_client=BadProfileClient())  # type: ignore
    output_path = tmp_path / "strut_bracket_fail.stl"
    
    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_strut_channel_bracket(
            {
                "width_cm": 5.0,
                "height_cm": 4.0,
                "depth_cm": 2.0,
                "thickness_cm": 0.5,
                "hole_diameter_cm": 1.0,  # Must be < depth_cm
                "hole_edge_offset_cm": 1.0,
                "hole_spacing_cm": 2.0,
                "output_path": str(output_path),
            }
        )
    
    assert exc_info.value.stage == "draw_l_bracket_profile"
    assert "expected exactly one L-profile" in str(exc_info.value)


def test_strut_channel_bracket_body_count_preserved_through_cuts(running_bridge, tmp_path) -> None:
    """Body count should remain 1 through all hole cuts."""
    from mcp_server.bridge_client import BridgeClient
    
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = tmp_path / "strut_bracket_count.stl"
    
    result = server.create_strut_channel_bracket(
        {
            "width_cm": 5.0,
            "height_cm": 4.0,
            "depth_cm": 2.0,
            "thickness_cm": 0.5,
            "hole_diameter_cm": 1.0,  # Must be < depth_cm
            "hole_edge_offset_cm": 1.0,
            "hole_spacing_cm": 2.0,
            "taper_angle_deg": 0.0,
            "output_path": str(output_path),
        }
    )
    
    assert result["ok"] is True
