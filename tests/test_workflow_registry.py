from __future__ import annotations

from mcp_server.workflows import build_default_registry


def test_workflow_registry_tracks_extension_paths() -> None:
    registry = build_default_registry()

    spacer = registry.get("spacer")
    bracket = registry.get("bracket")
    mounting_bracket = registry.get("mounting_bracket")
    two_hole_mounting_bracket = registry.get("two_hole_mounting_bracket")
    two_hole_plate = registry.get("two_hole_plate")

    assert spacer.stages[0] == "new_design"
    assert "verify_geometry" in spacer.stages
    assert "draw_l_bracket_profile" in bracket.stages
    assert "export_stl" in bracket.stages
    assert bracket.extension_of == ("spacer",)
    assert "draw_circle" in mounting_bracket.stages
    assert mounting_bracket.extension_of == ("bracket",)
    assert two_hole_mounting_bracket.stages.count("draw_circle") == 2
    assert two_hole_mounting_bracket.extension_of == ("mounting_bracket",)
    assert two_hole_plate.stages.count("draw_circle") == 2
    assert "draw_rectangle" in two_hole_plate.stages
    assert two_hole_plate.extension_of == ("plate_with_hole",)
