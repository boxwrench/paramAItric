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
    "create_box_with_lid": ToolSpec(
        method="create_box_with_lid",
        description=(
            "Create a matched box and cap lid as two separate bodies in one design. "
            "The lid outer footprint is larger than the box by wall_thickness + clearance on each side "
            "so it slides over the box. Both bodies are exported as separate STL files."
        ),
    ),
}

# ---------------------------------------------------------------------------
# Inspection tools (read-only, non-destructive)
# ---------------------------------------------------------------------------

INSPECTION_TOOLS: dict[str, ToolSpec] = {
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
}

# All tools in declaration order (status, inspection, workflows)
ALL_TOOLS: dict[str, ToolSpec] = {**STATUS_TOOLS, **INSPECTION_TOOLS, **WORKFLOW_TOOLS}
