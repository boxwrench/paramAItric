from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    intent: str
    stages: tuple[str, ...]
    extension_of: tuple[str, ...] = ()


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        self._workflows[workflow.name] = workflow

    def get(self, name: str) -> WorkflowDefinition:
        return self._workflows[name]

    def list(self) -> list[WorkflowDefinition]:
        return list(self._workflows.values())


def build_default_registry() -> WorkflowRegistry:
    registry = WorkflowRegistry()
    registry.register(
        WorkflowDefinition(
            name="spacer",
            intent="Golden-path mechanical workflow for sketch, profile, extrude, verify, export.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="cylinder",
            intent=(
                "Narrow cylindrical solid workflow using one circle profile, one extrusion, "
                "geometry verification, and STL export."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("spacer",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="tube",
            intent=(
                "Narrow hollow-cylinder workflow: outer cylindrical body first, then a centered bore cut, "
                "with verification after each stage and STL export."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("cylinder", "plate_with_hole"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="revolve",
            intent=(
                "Narrow revolve workflow using one tapered side profile revolved about the Y axis, "
                "geometry verification, and STL export."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_revolve_profile",
                "list_profiles",
                "revolve_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("cylinder",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="tapered_knob_blank",
            intent=(
                "Tapered knob blank built by revolve with a centered stem-socket cut through the axis."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_revolve_profile",
                "list_profiles",
                "revolve_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("revolve", "tube"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="flanged_bushing",
            intent=(
                "Flanged bushing built from a revolved shaft, a flange added as a second revolved body, "
                "an explicit body combine, and a centered axial bore cut."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_revolve_profile",
                "list_profiles",
                "revolve_profile",
                "verify_geometry",
                "create_sketch",
                "draw_revolve_profile",
                "list_profiles",
                "revolve_profile",
                "verify_geometry",
                "combine_bodies",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("revolve", "tube_mounting_plate"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="pipe_clamp_half",
            intent=(
                "Pipe clamp half built from a rectangular base body, one non-XY saddle cut, "
                "and two mirrored bolt-hole cuts."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("tube", "two_hole_plate"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="t_handle_with_square_socket",
            intent=(
                "True T-handle built from a centered stem and top tee bar, with a square valve socket cut "
                "from the stem and a top comfort chamfer on the tee."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "combine_bodies",
                "verify_geometry",
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "apply_chamfer",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("tube_mounting_plate", "chamfered_bracket"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="tube_mounting_plate",
            intent=(
                "Wall-mount plate with a centered tube socket: rectangular base, two mounting holes, "
                "joined cylindrical sleeve, and a final bore cut."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "combine_bodies",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("cylinder", "plate_with_hole"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="bracket",
            intent="Narrow L-bracket workflow using a single validated L-profile sketch, extrude, verify, export path.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("spacer",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="simple_enclosure",
            intent=(
                "Open-top rectangular enclosure made by shelling the top face of a solid body. "
                "First workflow using a dedicated shell operation before closure or fit features."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "apply_shell",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("spacer",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="mounting_bracket",
            intent="Narrow bracket workflow with one validated sketch hole and deterministic outer-profile selection.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("bracket",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="two_hole_mounting_bracket",
            intent="Narrow bracket workflow with two validated sketch holes and deterministic outer-profile selection.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "draw_circle",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("mounting_bracket",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="plate_with_hole",
            intent=(
                "Flat plate with a single through-hole via cut extrusion. "
                "First workflow using cut operations: solid body first, "
                "then a second sketch on the top face drives a cut extrude."
            ),
            # NOTE: WorkflowSession.record() uses position-based matching
            # (allowed_stages[len(completed_stages)]), so duplicate stage names
            # are safe here — each occurrence is matched at its own index.
            # The two_hole_mounting_bracket workflow already relies on this
            # for its two "draw_circle" stages.
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",      # first sketch: rectangle profile
                "draw_rectangle",
                "list_profiles",      # first profile listing: one solid profile
                "extrude_profile",    # new_body: creates the base plate
                "verify_geometry",    # verify exactly one body
                "create_sketch",      # second sketch: circle on top face
                "draw_circle",
                "list_profiles",      # second profile listing: hole profile
                "extrude_profile",    # cut: removes material from base plate
                "verify_geometry",    # verify body count is still 1
                "export_stl",
            ),
            extension_of=("spacer", "mounting_bracket"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="two_hole_plate",
            intent=(
                "Flat plate with two mirrored through-holes on a shared centerline. "
                "Extends the validated plate path with symmetric edge-offset placement "
                "while keeping the same single-sketch extrusion contract."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "draw_circle",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("plate_with_hole",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="slotted_mount",
            intent=(
                "Flat plate with one horizontal slot in the base sketch. "
                "First workflow using a bounded slot primitive while keeping "
                "the same single-sketch extrusion contract."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "draw_slot",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("two_hole_plate",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="four_hole_mounting_plate",
            intent=(
                "Flat mounting plate with four corner through-holes using mirrored X and Y edge offsets. "
                "Extends the validated plate path with a practical corner-hole pattern while keeping "
                "the same single-sketch extrusion contract."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("two_hole_plate",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="slotted_mounting_plate",
            intent=(
                "Flat mounting plate with four corner through-holes plus one centered slot in the same sketch. "
                "Composes validated hole and slot stages without adding a new low-level primitive."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "draw_slot",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("four_hole_mounting_plate", "slotted_mount"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="counterbored_plate",
            intent=(
                "Flat plate with a through-hole plus a larger shallow concentric counterbore. "
                "Extends the validated cut workflow with one additional partial-depth circular cut."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("plate_with_hole",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="recessed_mount",
            intent=(
                "Flat plate with one bounded rectangular pocket cut from the top face. "
                "Extends the validated plate workflow with an explicitly placed partial-depth recess."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("plate_with_hole",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="open_box_body",
            intent=(
                "Open-top box body with an inset cavity cut from an offset floor plane. "
                "Extends the recessed cut path with one offset sketch plane while preserving outer dimensions."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("recessed_mount",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="lid_for_box",
            intent=(
                "Cap lid with a downward perimeter rim formed by a bottom-side rectangular cut. "
                "Extends the box family without introducing clearance or paired-fit logic."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("open_box_body",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="filleted_bracket",
            intent="L-bracket with edge fillets applied after extrusion. First workflow using fillet operations.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "apply_fillet",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("bracket",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="chamfered_bracket",
            intent="L-bracket with equal-distance chamfers applied to interior edges after extrusion.",
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "apply_chamfer",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("bracket",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="shaft_coupler",
            intent=(
                "Shaft coupler with an axial bore and a cross-pin hole. "
                "Cylinder extruded first, then an axial bore cut, then an orthogonal pin hole "
                "cut on the XZ plane. First workflow proving orthogonal cuts on cylindrical geometry."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                # outer cylinder
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                # axial bore
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                # cross-pin hole (XZ plane)
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                # export
                "export_stl",
            ),
            extension_of=("tube", "pipe_clamp_half"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="project_box_with_standoffs",
            intent=(
                "Shelled project box with four internal corner standoffs for PCB mounting. "
                "Solid body is shelled first, then standoff posts are extruded from the interior floor "
                "and combined into the shelled body. First workflow proving post-shell internal features."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                # outer solid
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                # shell
                "apply_shell",
                "verify_geometry",
                # standoff 1
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "combine_bodies",
                "verify_geometry",
                # standoff 2
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "combine_bodies",
                "verify_geometry",
                # standoff 3
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "combine_bodies",
                "verify_geometry",
                # standoff 4
                "create_sketch",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "combine_bodies",
                "verify_geometry",
                # export
                "export_stl",
            ),
            extension_of=("simple_enclosure", "tube_mounting_plate"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="box_with_lid",
            intent=(
                "Matched box and lid produced in one design as two separate bodies. "
                "Box body: rectangular base extruded, cavity cut from top face. "
                "Lid body: rectangular base extruded as new_body in same design, rim cut from bottom face. "
                "First multi-body workflow: two bodies coexist and are exported separately."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                # box base
                "create_sketch",
                "draw_rectangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                # box cavity cut
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                # lid base (new_body, centered over box)
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                # lid rim cut
                "create_sketch",
                "draw_rectangle_at",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                # export both
                "export_stl",
                "export_stl",
            ),
            extension_of=("open_box_body", "lid_for_box"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="triangular_bracket",
            intent=(
                "Flat right-triangle plate extruded to a given thickness. "
                "Uses the new draw_triangle primitive as its sole sketch operation. "
                "Golden-path test of the triangle primitive: one sketch, one extrusion, export."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_triangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("spacer",),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="l_bracket_with_gusset",
            intent=(
                "L-bracket with an internal right-triangle gusset for reinforcement. "
                "L profile extruded first, then a separate sketch draws the gusset triangle "
                "in the inner corner, extruded as a new body and combined. "
                "Proves draw_triangle integrates with existing bodies via combine."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_l_bracket_profile",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "create_sketch",
                "draw_triangle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "combine_bodies",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("bracket", "triangular_bracket"),
        )
    )
    registry.register(
        WorkflowDefinition(
            name="cable_gland_plate",
            intent=(
                "Flat plate with four corner mounting holes and one large center pass-through for a cable or conduit. "
                "All five holes are cut in a single sketch extrusion. Extends the four_hole_mounting_plate pattern "
                "with an explicitly placed center hole sized for a cable gland or conduit fitting."
            ),
            stages=(
                "new_design",
                "verify_clean_state",
                "create_sketch",
                "draw_rectangle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "draw_circle",
                "list_profiles",
                "extrude_profile",
                "verify_geometry",
                "export_stl",
            ),
            extension_of=("four_hole_mounting_plate",),
        )
    )
    return registry
