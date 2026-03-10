"""MCP tool registry table.

Maps MCP tool names to ParamAIToolServer method names and short descriptions.
Kept separate from mcp_entrypoint.py to avoid decorator sprawl and to make the
exported surface easy to audit.

Lanes:
  status    — read-only health and catalog queries
  workflow  — validated, staged create_ methods
"""
from __future__ import annotations

from typing import NamedTuple


class ToolSpec(NamedTuple):
    method: str
    description: str


# ---------------------------------------------------------------------------
# Status tools
# ---------------------------------------------------------------------------

STATUS_TOOLS: dict[str, ToolSpec] = {
    "health": ToolSpec(
        method="health",
        description="Check that the Fusion 360 bridge is reachable and report its operating mode.",
    ),
    "workflow_catalog": ToolSpec(
        method="get_workflow_catalog",
        description="Return the list of workflows registered in the Fusion add-in.",
    ),
}

# ---------------------------------------------------------------------------
# Validated workflow tools
# ---------------------------------------------------------------------------

WORKFLOW_TOOLS: dict[str, ToolSpec] = {
    "create_spacer": ToolSpec(
        method="create_spacer",
        description=(
            "Create a flat rectangular spacer: sketch a rectangle, extrude it, verify geometry, export STL."
        ),
    ),
    "create_cylinder": ToolSpec(
        method="create_cylinder",
        description=(
            "Create a cylindrical solid: sketch one circle, extrude it, verify diameter and height, export STL."
        ),
    ),
    "create_tube": ToolSpec(
        method="create_tube",
        description=(
            "Create a hollow tube: outer cylinder first, then a centered bore cut through the same body."
        ),
    ),
    "create_revolve": ToolSpec(
        method="create_revolve",
        description=(
            "Create a revolved solid from a tapered side profile about the Y axis."
        ),
    ),
    "create_tapered_knob_blank": ToolSpec(
        method="create_tapered_knob_blank",
        description=(
            "Create a tapered knob blank with a centered stem socket cut through its axis."
        ),
    ),
    "create_flanged_bushing": ToolSpec(
        method="create_flanged_bushing",
        description=(
            "Create a flanged bushing using a revolved shaft, a joined flange body, and a centered axial bore cut."
        ),
    ),
    "create_pipe_clamp_half": ToolSpec(
        method="create_pipe_clamp_half",
        description=(
            "Create a half clamp body with a non-XY pipe saddle cut and two mirrored bolt-hole cuts."
        ),
    ),
    "create_t_handle_with_square_socket": ToolSpec(
        method="create_t_handle_with_square_socket",
        description=(
            "Create a true T-handle with a square valve socket in the stem and a comfort chamfer on the tee."
        ),
    ),
    "create_tube_mounting_plate": ToolSpec(
        method="create_tube_mounting_plate",
        description=(
            "Create a wall-mount plate with two mounting holes and a centered tube socket joined into one body."
        ),
    ),
    "create_bracket": ToolSpec(
        method="create_bracket",
        description=(
            "Create an L-bracket: sketch an L-profile, extrude, verify, export STL. "
            "Supports xy and xz planes."
        ),
    ),
    "create_filleted_bracket": ToolSpec(
        method="create_filleted_bracket",
        description=(
            "Create an L-bracket with edge fillets applied after extrusion. "
            "Specify fillet_radius_cm; validated against leg and plate thickness."
        ),
    ),
    "create_chamfered_bracket": ToolSpec(
        method="create_chamfered_bracket",
        description=(
            "Create an L-bracket with equal-distance chamfers applied after extrusion. "
            "Specify chamfer_distance_cm; validated against leg and plate thickness."
        ),
    ),
    "create_mounting_bracket": ToolSpec(
        method="create_mounting_bracket",
        description=(
            "Create an L-bracket with one mounting hole cut through the vertical leg."
        ),
    ),
    "create_two_hole_mounting_bracket": ToolSpec(
        method="create_two_hole_mounting_bracket",
        description=(
            "Create an L-bracket with two mounting holes cut through the vertical leg."
        ),
    ),
    "create_plate_with_hole": ToolSpec(
        method="create_plate_with_hole",
        description=(
            "Create a flat plate with a single through-hole. "
            "Base plate extruded first; hole cut in a second sketch on the top face."
        ),
    ),
    "create_two_hole_plate": ToolSpec(
        method="create_two_hole_plate",
        description=(
            "Create a flat plate with two mirrored through-holes on a shared centerline."
        ),
    ),
    "create_four_hole_mounting_plate": ToolSpec(
        method="create_four_hole_mounting_plate",
        description=(
            "Create a flat mounting plate with four corner through-holes using mirrored edge offsets."
        ),
    ),
    "create_slotted_mount": ToolSpec(
        method="create_slotted_mount",
        description=(
            "Create a flat plate with one horizontal slot. "
            "First workflow using the bounded slot primitive."
        ),
    ),
    "create_slotted_mounting_plate": ToolSpec(
        method="create_slotted_mounting_plate",
        description=(
            "Create a flat mounting plate with four corner holes plus a centered slot."
        ),
    ),
    "create_counterbored_plate": ToolSpec(
        method="create_counterbored_plate",
        description=(
            "Create a flat plate with a through-hole and a larger shallow concentric counterbore."
        ),
    ),
    "create_recessed_mount": ToolSpec(
        method="create_recessed_mount",
        description=(
            "Create a flat plate with a rectangular pocket cut from the top face."
        ),
    ),
    "create_simple_enclosure": ToolSpec(
        method="create_simple_enclosure",
        description=(
            "Create an open-top rectangular enclosure by shelling the top face of a solid body."
        ),
    ),
    "create_open_box_body": ToolSpec(
        method="create_open_box_body",
        description=(
            "Create an open-top box body with an inset cavity cut from an offset floor plane."
        ),
    ),
    "create_lid_for_box": ToolSpec(
        method="create_lid_for_box",
        description=(
            "Create a cap lid with a downward perimeter rim formed by a bottom-side rectangular cut."
        ),
    ),
    "create_shaft_coupler": ToolSpec(
        method="create_shaft_coupler",
        description=(
            "Create a shaft coupler with an axial bore and an orthogonal cross-pin hole. "
            "Cylinder body first, then axial bore cut, then cross-pin hole cut on the XZ plane."
        ),
    ),
    "create_project_box_with_standoffs": ToolSpec(
        method="create_project_box_with_standoffs",
        description=(
            "Create a shelled project box with four internal corner standoffs for PCB mounting. "
            "Solid body shelled first, then standoff posts extruded from the interior floor and combined."
        ),
    ),
    "create_box_with_lid": ToolSpec(
        method="create_box_with_lid",
        description=(
            "Create a matched box and cap lid as two separate bodies in one design. "
            "The lid outer footprint is larger than the box by wall_thickness + clearance on each side "
            "so it slides over the box. Both bodies are exported as separate STL files."
        ),
    ),
    "create_triangular_bracket": ToolSpec(
        method="create_triangular_bracket",
        description=(
            "Create a flat right-triangle plate extruded to a given thickness. "
            "The right angle is at the origin; the base runs along the X axis and the "
            "height runs along the Y axis. First workflow using the draw_triangle primitive."
        ),
    ),
    "create_l_bracket_with_gusset": ToolSpec(
        method="create_l_bracket_with_gusset",
        description=(
            "Create an L-bracket with an internal right-triangle gusset for reinforcement. "
            "The gusset fills the inner corner of the L and is combined into the bracket body. "
            "Specify gusset_size_cm to control how far into the cavity the triangular rib extends."
        ),
    ),
    "create_cable_gland_plate": ToolSpec(
        method="create_cable_gland_plate",
        description=(
            "Create a flat plate with four corner mounting holes and one large center pass-through "
            "for a cable gland or conduit fitting. All five holes are cut in one sketch extrusion. "
            "Specify center_hole_diameter_cm for the gland aperture and mounting_hole_diameter_cm "
            "for the corner bolts."
        ),
    ),
    "create_strut_channel_bracket": ToolSpec(
        method="create_strut_channel_bracket",
        description=(
            "Create a McMaster-style strut channel bracket: bent sheet metal L-bracket with taper, "
            "four mounting holes, and outer bend radius fillet. Cross-section sketch (thin L-shape) "
            "is extruded to full width. Optional taper cuts on vertical leg. Holes on horizontal leg "
            "use XZ plane; holes on vertical leg use YZ plane with offset. Specify width_cm for the "
            "horizontal leg span, height_cm for vertical leg, depth_cm for bracket depth, and "
            "thickness_cm for sheet metal thickness."
        ),
    ),
    "create_snap_fit_enclosure": ToolSpec(
        method="create_snap_fit_enclosure",
        description=(
            "Create a snap-fit enclosure box with view holes and a snap-on lid. The box is shell-hollowed "
            "with circular view holes cut on front (XZ plane) and side (YZ plane) walls. The separate lid "
            "has a rectangular snap bead ring on its underside for retention. Exports both box and lid as "
            "separate STL files. Tests shell, multi-plane cuts, and multi-body workflows."
        ),
    ),
    "create_telescoping_containers": ToolSpec(
        method="create_telescoping_containers",
        description=(
            "Create three nesting rectangular containers with progressive clearances. Outer container is "
            "largest; middle container fits inside outer with middle_clearance_cm gap; inner container fits "
            "inside middle with inner_clearance_cm gap. All containers are shelled open-top. Exports all "
            "three as separate STL files. Tests multi-body shell operations and dimensional cascading."
        ),
    ),
    "create_slotted_flex_panel": ToolSpec(
        method="create_slotted_flex_panel",
        description=(
            "Create a flat rectangular panel with 5 evenly spaced rectangular slots for living hinge "
            "flexibility. Panel is extruded, slots are cut sequentially through thickness, then fillets "
            "are applied to all slot edges. Tests manual slot array, cumulative volume tracking, and "
            "fillet operations on thin-feature edges."
        ),
    ),
    "create_ratchet_wheel": ToolSpec(
        method="create_ratchet_wheel",
        description=(
            "Create a ratchet wheel with asymmetric teeth and center bore. Cylindrical wheel with "
            "10 triangular teeth cut around the outer edge (gentle slope engagement face, vertical "
            "locking face). Center bore cut through. Fillets applied to tooth tips. Tests manual "
            "wedge array, volume tracking across sequential cuts, and centroid stability."
        ),
    ),
    "create_wire_clamp": ToolSpec(
        method="create_wire_clamp",
        description=(
            "Create a wire clamp with bore, tapered lead-ins, grip ribs, and split slot. "
            "Block body with Y-axis through-bore, tapered lead-in entries on both ends, "
            "internal grip ribs as combined protrusions, and longitudinal split slot through top. "
            "Tests internal feature protrusions, tapered cuts, and split slot operations."
        ),
    ),
}

# ---------------------------------------------------------------------------
# Inspection tools (read-only, non-destructive)
# ---------------------------------------------------------------------------

INSPECTION_TOOLS: dict[str, ToolSpec] = {
    "list_design_bodies": ToolSpec(
        method="list_design_bodies",
        description=(
            "List all bodies currently in the design. Returns body token, name, face count, "
            "edge count, and volume for each body. Use after cut operations to verify that "
            "the expected number of bodies still exists — a cut that splits a body creates "
            "extra bodies here, which is always a geometry bug."
        ),
    ),
    "get_body_info": ToolSpec(
        method="get_body_info",
        description=(
            "Inspect a single body by token. Returns bounding box (absolute min/max position), "
            "dimensions, face count, edge count, and volume. Read-only, does not modify the design."
        ),
    ),
    "get_body_faces": ToolSpec(
        method="get_body_faces",
        description=(
            "Inspect all faces on a single body by token. Returns face tokens, surface types, "
            "planar face normals when available, face area, and face bounding boxes. "
            "Read-only, does not modify the design."
        ),
    ),
    "get_body_edges": ToolSpec(
        method="get_body_edges",
        description=(
            "Inspect all edges on a single body by token. Returns edge tokens, edge types, "
            "start/end points, and edge lengths. Read-only, does not modify the design."
        ),
    ),
    "convert_bodies_to_components": ToolSpec(
        method="convert_bodies_to_components",
        description=(
            "Convert one or more bodies to Fusion 360 components by body token. "
            "Each body is moved into its own component occurrence in the root design. "
            "Returns component tokens and names. Prerequisite for joints and assembly operations."
        ),
    ),
    "find_face": ToolSpec(
        method="find_face",
        description=(
            "Find a specific face on a body using a semantic selector. "
            "Supported selectors: 'top', 'bottom', 'left', 'right', 'front', 'back'. "
            "Returns the stable face token and geometric details."
        ),
    ),
}

# ---------------------------------------------------------------------------
# Freeform Session tools (Guided AI modeling mode)
# ---------------------------------------------------------------------------

FREEFORM_SESSION_TOOLS: dict[str, ToolSpec] = {
    "start_freeform_session": ToolSpec(
        method="start_freeform_session",
        description=(
            "Start a new Freeform session. The canvas is wiped clean. "
            "You are allowed ONE mutation before the state locks and requires verification."
        ),
    ),
    "commit_verification": ToolSpec(
        method="commit_verification",
        description=(
            "Commit your verification of the scene geometry to unlock the session for the next mutation. "
            "Must provide notes summarizing your findings and the expected total body count."
        ),
    ),
    "end_freeform_session": ToolSpec(
        method="end_freeform_session",
        description=(
            "End the active Freeform session. You cannot end a session while awaiting verification."
        ),
    ),
    "export_session_log": ToolSpec(
        method="export_session_log",
        description=(
            "Export the full mutation and verification log for the active Freeform session. "
            "Essential for reverse-engineering a reusable workflow from a successful freeform design."
        ),
    ),
}

# All tools in declaration order (status, inspection, freeform, workflows)
ALL_TOOLS: dict[str, ToolSpec] = {**STATUS_TOOLS, **INSPECTION_TOOLS, **FREEFORM_SESSION_TOOLS, **WORKFLOW_TOOLS}
