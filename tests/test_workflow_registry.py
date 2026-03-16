from __future__ import annotations

from mcp_server.workflow_registry import build_default_registry


def test_workflow_registry_tracks_extension_paths() -> None:
    registry = build_default_registry()

    spacer = registry.get("spacer")
    cylinder = registry.get("cylinder")
    tube = registry.get("tube")
    revolve = registry.get("revolve")
    tapered_knob_blank = registry.get("tapered_knob_blank")
    flanged_bushing = registry.get("flanged_bushing")
    pipe_clamp_half = registry.get("pipe_clamp_half")
    t_handle_with_square_socket = registry.get("t_handle_with_square_socket")
    tube_mounting_plate = registry.get("tube_mounting_plate")
    bracket = registry.get("bracket")
    mounting_bracket = registry.get("mounting_bracket")
    two_hole_mounting_bracket = registry.get("two_hole_mounting_bracket")
    two_hole_plate = registry.get("two_hole_plate")
    four_hole_mounting_plate = registry.get("four_hole_mounting_plate")
    slotted_mounting_plate = registry.get("slotted_mounting_plate")
    slotted_mount = registry.get("slotted_mount")
    counterbored_plate = registry.get("counterbored_plate")
    recessed_mount = registry.get("recessed_mount")
    simple_enclosure = registry.get("simple_enclosure")
    open_box_body = registry.get("open_box_body")
    lid_for_box = registry.get("lid_for_box")

    assert spacer.stages[0] == "new_design"
    assert "verify_geometry" in spacer.stages
    assert "draw_circle" in cylinder.stages
    assert cylinder.stages[-1] == "export_stl"
    assert cylinder.extension_of == ("spacer",)
    assert tube.stages.count("draw_circle") == 2
    assert tube.stages.count("extrude_profile") == 2
    assert tube.extension_of == ("cylinder", "plate_with_hole")
    assert "draw_revolve_profile" in revolve.stages
    assert "revolve_profile" in revolve.stages
    assert revolve.extension_of == ("cylinder",)
    assert "draw_revolve_profile" in tapered_knob_blank.stages
    assert "revolve_profile" in tapered_knob_blank.stages
    assert tapered_knob_blank.stages.count("draw_circle") == 1
    assert tapered_knob_blank.extension_of == ("revolve", "tube")
    assert "draw_revolve_profile" in flanged_bushing.stages
    assert flanged_bushing.stages.count("draw_revolve_profile") == 2
    assert flanged_bushing.stages.count("draw_circle") == 1
    assert "combine_bodies" in flanged_bushing.stages
    assert flanged_bushing.extension_of == ("revolve", "tube_mounting_plate")
    assert pipe_clamp_half.stages.count("draw_circle") == 3
    assert pipe_clamp_half.stages.count("create_sketch") == 4
    assert pipe_clamp_half.stages[-1] == "export_stl"
    assert pipe_clamp_half.extension_of == ("tube", "two_hole_plate")
    assert t_handle_with_square_socket.stages.count("draw_rectangle_at") == 2
    assert "combine_bodies" in t_handle_with_square_socket.stages
    assert "apply_chamfer" in t_handle_with_square_socket.stages
    assert t_handle_with_square_socket.extension_of == ("tube_mounting_plate", "chamfered_bracket")
    assert "combine_bodies" in tube_mounting_plate.stages
    assert tube_mounting_plate.stages.count("draw_circle") == 4
    assert tube_mounting_plate.extension_of == ("cylinder", "plate_with_hole")
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
    assert four_hole_mounting_plate.stages.count("draw_circle") == 4
    assert "draw_rectangle" in four_hole_mounting_plate.stages
    assert four_hole_mounting_plate.extension_of == ("two_hole_plate",)
    assert slotted_mounting_plate.stages.count("draw_circle") == 4
    assert "draw_slot" in slotted_mounting_plate.stages
    assert slotted_mounting_plate.extension_of == ("four_hole_mounting_plate", "slotted_mount")
    assert "draw_slot" in slotted_mount.stages
    assert slotted_mount.extension_of == ("two_hole_plate",)
    assert counterbored_plate.stages.count("draw_circle") == 2
    assert counterbored_plate.stages.count("extrude_profile") == 3
    assert counterbored_plate.extension_of == ("plate_with_hole",)
    assert "draw_rectangle_at" in recessed_mount.stages
    assert recessed_mount.extension_of == ("plate_with_hole",)
    assert "apply_shell" in simple_enclosure.stages
    assert simple_enclosure.stages.count("verify_geometry") == 2
    assert simple_enclosure.stages[-1] == "export_stl"
    assert simple_enclosure.extension_of == ("spacer",)
    assert open_box_body.stages.count("create_sketch") == 2
    assert "draw_rectangle_at" in open_box_body.stages
    assert open_box_body.extension_of == ("recessed_mount",)
    assert lid_for_box.stages.count("create_sketch") == 2
    assert "draw_rectangle_at" in lid_for_box.stages
    assert lid_for_box.extension_of == ("open_box_body",)

    chamfered_bracket = registry.get("chamfered_bracket")
    assert "apply_chamfer" in chamfered_bracket.stages
    assert chamfered_bracket.extension_of == ("bracket",)

    shaft_coupler = registry.get("shaft_coupler")
    assert shaft_coupler.stages.count("draw_circle") == 3
    assert shaft_coupler.stages.count("extrude_profile") == 3
    assert shaft_coupler.stages.count("verify_geometry") == 3
    assert shaft_coupler.stages[-1] == "export_stl"
    assert shaft_coupler.extension_of == ("tube", "pipe_clamp_half")

    project_box = registry.get("project_box_with_standoffs")
    assert "apply_shell" in project_box.stages
    assert project_box.stages.count("draw_circle") == 4
    assert project_box.stages.count("combine_bodies") == 4
    assert project_box.stages.count("verify_geometry") == 10
    assert project_box.stages[-1] == "export_stl"
    assert project_box.extension_of == ("simple_enclosure", "tube_mounting_plate")

    box_with_lid = registry.get("box_with_lid")
    assert box_with_lid.stages.count("create_sketch") == 4
    assert box_with_lid.stages.count("draw_rectangle_at") == 3
    assert box_with_lid.stages.count("export_stl") == 2
    assert box_with_lid.extension_of == ("open_box_body", "lid_for_box")

    flush_lid_enclosure_pair = registry.get("flush_lid_enclosure_pair")
    assert flush_lid_enclosure_pair.stages.count("create_sketch") == 4
    assert flush_lid_enclosure_pair.stages.count("draw_rectangle") == 1
    assert flush_lid_enclosure_pair.stages.count("draw_rectangle_at") == 3
    assert flush_lid_enclosure_pair.stages.count("apply_shell") == 1
    assert flush_lid_enclosure_pair.stages.count("combine_bodies") == 2
    assert flush_lid_enclosure_pair.stages.count("export_stl") == 2
    assert flush_lid_enclosure_pair.extension_of == ("open_box_body", "box_with_lid")

    cable_gland_plate = registry.get("cable_gland_plate")
    assert cable_gland_plate.stages.count("draw_circle") == 5
    assert "draw_rectangle" in cable_gland_plate.stages
    assert cable_gland_plate.extension_of == ("four_hole_mounting_plate",)

    triangular_bracket = registry.get("triangular_bracket")
    assert "draw_triangle" in triangular_bracket.stages
    assert triangular_bracket.stages[-1] == "export_stl"
    assert triangular_bracket.extension_of == ("spacer",)

    l_bracket_with_gusset = registry.get("l_bracket_with_gusset")
    assert "draw_l_bracket_profile" in l_bracket_with_gusset.stages
    assert "draw_triangle" in l_bracket_with_gusset.stages
    assert "combine_bodies" in l_bracket_with_gusset.stages
    assert l_bracket_with_gusset.stages.count("create_sketch") == 2
    assert l_bracket_with_gusset.extension_of == ("bracket", "triangular_bracket")
