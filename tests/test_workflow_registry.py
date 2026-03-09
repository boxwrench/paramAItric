from __future__ import annotations

from mcp_server.workflows import build_default_registry


def test_workflow_registry_tracks_extension_paths() -> None:
    registry = build_default_registry()

    spacer = registry.get("spacer")
    bracket = registry.get("bracket")
    mounting_bracket = registry.get("mounting_bracket")
    two_hole_mounting_bracket = registry.get("two_hole_mounting_bracket")
    two_hole_plate = registry.get("two_hole_plate")
    slotted_mount = registry.get("slotted_mount")
    counterbored_plate = registry.get("counterbored_plate")
    recessed_mount = registry.get("recessed_mount")
    open_box_body = registry.get("open_box_body")
    lid_for_box = registry.get("lid_for_box")

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
    assert "draw_slot" in slotted_mount.stages
    assert slotted_mount.extension_of == ("two_hole_plate",)
    assert counterbored_plate.stages.count("draw_circle") == 2
    assert counterbored_plate.stages.count("extrude_profile") == 3
    assert counterbored_plate.extension_of == ("plate_with_hole",)
    assert "draw_rectangle_at" in recessed_mount.stages
    assert recessed_mount.extension_of == ("plate_with_hole",)
    assert open_box_body.stages.count("create_sketch") == 2
    assert "draw_rectangle_at" in open_box_body.stages
    assert open_box_body.extension_of == ("recessed_mount",)
    assert lid_for_box.stages.count("create_sketch") == 2
    assert "draw_rectangle_at" in lid_for_box.stages
    assert lid_for_box.extension_of == ("open_box_body",)
