"""Utility part workflows: valve handle, instrument brackets, etc."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import CreateValveHandleInput, VerificationSnapshot

if TYPE_CHECKING:
    from mcp_server.workflow_registry import WorkflowRegistry


class UtilityPartsMixin:
    """Mixin providing utility/maintenance part workflows."""

    def create_valve_handle(self, payload: dict) -> dict:
        """Create a valve handle replacement part."""
        spec = CreateValveHandleInput.from_payload(payload)
        return self._create_valve_handle_workflow(spec)

    def _verify_valve_handle_body_count(self, stages: list[dict], context: str) -> None:
        """Assert the design holds exactly one body (split/disjoint-body detector).

        Distinct from WorkflowMixin._verify_single_body: that variant also asserts
        exact body dimensions, which don't apply to a combined hub+lever body.
        """
        scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
        )
        snapshot = VerificationSnapshot.from_scene(scene)
        if snapshot.body_count != 1:
            raise WorkflowFailure(
                f"Valve handle verification failed {context}: expected 1 body, "
                f"found {snapshot.body_count}.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "stages": stages},
                next_step="Inspect body placement and overlap before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": snapshot.__dict__,
                "context": context,
            }
        )

    def _create_valve_handle_workflow(self, spec: CreateValveHandleInput) -> dict:
        """Execute valve handle creation workflow.

        Geometry model (all sketches on validated planes, no YZ needed):
        1. Hub cylinder on XY: radius = socket circumradius + wall, height =
           stem_depth + cap. The stem enters from below (z=0).
        2. Lever bar on XY at offset (top of hub), overlapping the hub axis;
           same-plane combine into one body, verified via body count.
        3. Socket cavity (hex/square polygon or circle) cut upward from the
           base plane to stem_depth, leaving a solid cap; verified.
        4. Optional set-screw cross-hole on XZ at mid-cavity height.
        5. Best-effort stress-relief fillets, then STL export.
        """
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("valve_handle")

        # --- setup ---
        self._bridge_step(
            stage="new_design",
            stages=stages,
            action=lambda: self.new_design("Valve Handle Workflow"),
        )
        stages.append({"stage": "new_design", "status": "completed"})

        initial_scene = self._bridge_step(
            stage="verify_clean_state",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
        )
        initial_snapshot = VerificationSnapshot.from_scene(initial_scene)
        if initial_snapshot.body_count != 0 or initial_snapshot.export_count != 0:
            raise WorkflowFailure(
                "Workflow did not start from a clean design state.",
                stage="verify_clean_state",
                classification="state_drift",
                partial_result={"scene": initial_scene, "stages": stages},
                next_step="Inspect the design reset path before attempting another workflow.",
            )
        stages.append(
            {
                "stage": "verify_clean_state",
                "status": "completed",
                "snapshot": initial_snapshot.__dict__,
            }
        )

        # === Geometry parameters ===
        # Socket cavity circumradius from across-flats + clearance.
        if spec.socket_type == "hex":
            # circumradius = across_flats / (2 * cos(30deg)) = across_flats / sqrt(3)
            socket_radius = (spec.stem_width_cm + spec.clearance_cm) / math.sqrt(3)
            socket_sides = 6
        elif spec.socket_type == "square":
            # circumradius = across_flats / (2 * cos(45deg)) = across_flats / sqrt(2)
            socket_radius = (spec.stem_width_cm + spec.clearance_cm) / math.sqrt(2)
            socket_sides = 4
        else:  # round_flat
            socket_radius = (spec.stem_width_cm + spec.clearance_cm) / 2.0
            socket_sides = None

        # Hub wraps the cavity; wall thickness is measured at the polygon corners
        # (the thinnest point), so it holds everywhere on the perimeter.
        hub_wall_cm = max(0.3, 0.3 * spec.stem_width_cm)
        hub_radius = socket_radius + hub_wall_cm
        cap_thickness_cm = 0.3  # solid material above the blind cavity
        hub_height = spec.stem_depth_cm + cap_thickness_cm
        if spec.lever_length_cm <= hub_radius:
            raise WorkflowFailure(
                f"lever_length_cm ({spec.lever_length_cm}) must exceed the hub radius "
                f"({hub_radius:.3f}) so the lever extends past the hub.",
                stage="create_hub_sketch",
                classification="verification_failed",
                partial_result={"stages": stages},
                next_step="Increase lever_length_cm or reduce stem_width_cm.",
            )
        # Lever rides at the top of the hub; the stem enters from below (z=0).
        lever_offset_cm = max(0.0, hub_height - spec.lever_thickness_cm)

        # === Phase 1: Hub cylinder (XY plane) ===
        hub_sketch = self._bridge_step(
            stage="create_hub_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="hub_profile"),
        )
        hub_sketch_token = hub_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_hub_sketch",
                "status": "completed",
                "sketch_token": hub_sketch_token,
            }
        )

        self._bridge_step(
            stage="draw_hub_profile",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=0,
                center_y_cm=0,
                radius_cm=hub_radius,
                sketch_token=hub_sketch_token,
            ),
        )
        stages.append({"stage": "draw_hub_profile", "status": "completed"})

        hub_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(hub_sketch_token)["result"]["profiles"],
        )
        hub_profile = self._select_profile_by_dimensions(
            hub_profiles,
            expected_width_cm=hub_radius * 2.0,
            expected_height_cm=hub_radius * 2.0,
            workflow_label="Valve handle hub",
            stages=stages,
        )

        hub_body = self._bridge_step(
            stage="extrude_hub",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=hub_profile["token"],
                distance_cm=hub_height,
                body_name="valve_handle",
            )["result"]["body"],
        )
        hub_body_token = hub_body["token"]
        stages.append(
            {
                "stage": "extrude_hub",
                "status": "completed",
                "body_token": hub_body_token,
            }
        )

        # === Phase 2: Lever arm (XY plane, offset to the top of the hub) ===
        # Same-plane bodies keep combine_bodies on its validated path. The lever
        # rectangle starts at the hub axis (x=0) so the two bodies always overlap.
        lever_sketch = self._bridge_step(
            stage="create_lever_sketch",
            stages=stages,
            action=lambda: self.create_sketch(
                plane="xy",
                name="lever_profile",
                offset_cm=lever_offset_cm if lever_offset_cm > 0 else None,
            ),
        )
        lever_sketch_token = lever_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_lever_sketch",
                "status": "completed",
                "sketch_token": lever_sketch_token,
                "offset_cm": lever_offset_cm,
            }
        )

        self._bridge_step(
            stage="draw_lever_profile",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=0.0,
                origin_y_cm=-spec.lever_width_cm / 2,
                width_cm=spec.lever_length_cm,
                height_cm=spec.lever_width_cm,
                sketch_token=lever_sketch_token,
            ),
        )

        lever_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(lever_sketch_token)["result"]["profiles"],
        )
        lever_profile = self._select_profile_by_dimensions(
            lever_profiles,
            expected_width_cm=spec.lever_length_cm,
            expected_height_cm=spec.lever_width_cm,
            workflow_label="Valve handle lever",
            stages=stages,
        )
        stages.append(
            {
                "stage": "draw_lever_profile",
                "status": "completed",
                "profile_token": lever_profile["token"],
            }
        )

        lever_body = self._bridge_step(
            stage="extrude_lever",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=lever_profile["token"],
                distance_cm=spec.lever_thickness_cm,
                body_name="lever_body",
            )["result"]["body"],
        )
        lever_body_token = lever_body["token"]
        stages.append(
            {
                "stage": "extrude_lever",
                "status": "completed",
                "body_token": lever_body_token,
            }
        )

        # Combine hub and lever
        combined = self._bridge_step(
            stage="combine_bodies",
            stages=stages,
            action=lambda: self.combine_bodies(
                target_body_token=hub_body_token,
                tool_body_token=lever_body_token,
            )["result"]["body"],
        )
        combined_body_token = combined["token"]
        stages.append(
            {
                "stage": "combine_bodies",
                "status": "completed",
                "body_token": combined_body_token,
            }
        )

        self._verify_valve_handle_body_count(stages, context="after combining hub and lever")

        # === Phase 3: Socket cavity cut (draw_polygon on the base plane) ===
        # The cavity is cut upward from the bottom face, leaving cap_thickness_cm
        # of solid material at the top of the hub (blind socket).
        socket_sketch = self._bridge_step(
            stage="create_socket_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="socket_profile"),
        )
        socket_sketch_token = socket_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_socket_sketch",
                "status": "completed",
                "sketch_token": socket_sketch_token,
            }
        )

        if socket_sides is not None:
            self._bridge_step(
                stage="draw_socket_profile",
                stages=stages,
                action=lambda: self.draw_polygon(
                    center_x_cm=0,
                    center_y_cm=0,
                    radius_cm=socket_radius,
                    num_sides=socket_sides,
                    sketch_token=socket_sketch_token,
                ),
            )
        else:  # round_flat: circle for now (flat cut is advanced)
            self._bridge_step(
                stage="draw_socket_profile",
                stages=stages,
                action=lambda: self.draw_circle(
                    center_x_cm=0,
                    center_y_cm=0,
                    radius_cm=socket_radius,
                    sketch_token=socket_sketch_token,
                ),
            )

        socket_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(socket_sketch_token)["result"]["profiles"],
        )
        # Expected profile bbox: a regular polygon with a vertex at angle 0 is
        # not 2R x 2R (hex = 2R x sqrt(3)R); a circle is.
        if socket_sides is not None:
            vertex_angles = [2.0 * math.pi * i / socket_sides for i in range(socket_sides)]
            vertex_xs = [math.cos(a) * socket_radius for a in vertex_angles]
            vertex_ys = [math.sin(a) * socket_radius for a in vertex_angles]
            expected_socket_width = max(vertex_xs) - min(vertex_xs)
            expected_socket_height = max(vertex_ys) - min(vertex_ys)
        else:
            expected_socket_width = expected_socket_height = socket_radius * 2.0
        socket_profile = self._select_profile_by_dimensions(
            socket_profiles,
            expected_width_cm=expected_socket_width,
            expected_height_cm=expected_socket_height,
            workflow_label="Valve handle socket",
            stages=stages,
        )
        stages.append(
            {
                "stage": "draw_socket_profile",
                "status": "completed",
                "profile_token": socket_profile["token"],
            }
        )

        self._bridge_step(
            stage="extrude_socket",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=socket_profile["token"],
                distance_cm=spec.stem_depth_cm,
                body_name="socket_cavity",
                operation="cut",
                target_body_token=combined_body_token,
            ),
        )
        stages.append(
            {
                "stage": "extrude_socket",
                "status": "completed",
                "operation": "cut",
            }
        )

        self._verify_valve_handle_body_count(stages, context="after cutting the socket cavity")

        # === Phase 4: Set Screw Hole (Optional) ===
        # Cut on the XZ plane (y=0, through the hub axis) firing in +Y through the
        # cavity and the far hub wall. XZ convention: sketch-Y maps to -worldZ, so
        # the mid-cavity height +stem_depth/2 is sketched at -stem_depth/2.
        if spec.set_screw_diameter_cm:
            screw_sketch = self._bridge_step(
                stage="create_sketch",
                stages=stages,
                action=lambda: self.create_sketch(plane="xz", name="set_screw_hole"),
            )
            screw_sketch_token = screw_sketch["result"]["sketch"]["token"]

            self._bridge_step(
                stage="draw_set_screw_hole",
                stages=stages,
                action=lambda: self.draw_circle(
                    center_x_cm=0,
                    center_y_cm=-spec.stem_depth_cm / 2,
                    radius_cm=spec.set_screw_diameter_cm / 2,
                    sketch_token=screw_sketch_token,
                ),
            )

            screw_profiles = self._bridge_step(
                stage="list_profiles",
                stages=stages,
                action=lambda: self.list_profiles(screw_sketch_token)["result"]["profiles"],
            )
            screw_profile = self._select_profile_by_dimensions(
                screw_profiles,
                expected_width_cm=spec.set_screw_diameter_cm,
                expected_height_cm=spec.set_screw_diameter_cm,
                workflow_label="Valve handle set screw",
                stages=stages,
            )
            self._bridge_step(
                stage="cut_set_screw_hole",
                stages=stages,
                action=lambda: self.extrude_profile(
                    profile_token=screw_profile["token"],
                    distance_cm=hub_radius + 0.2,
                    body_name="set_screw_cut",
                    operation="cut",
                    target_body_token=combined_body_token,
                ),
            )

            stages.append({"stage": "set_screw_hole", "status": "completed"})
            self._verify_valve_handle_body_count(stages, context="after cutting the set screw hole")

        # === Phase 4: Finishing ===
        # Stress-relief fillets are best-effort: the live apply_fillet op only selects
        # interior bracket edges, which combined socket+lever geometry may not have.
        # A missing fillet degrades strength, not correctness, so record the stage as
        # skipped instead of failing the build. Explicit junction-edge selection via
        # apply_fillet_to_edges is the planned upgrade path.
        try:
            self._bridge_step(
                stage="apply_fillets",
                stages=stages,
                action=lambda: self.apply_fillet(
                    body_token=combined_body_token,
                    radius_cm=spec.fillet_radius_cm,
                ),
            )
            stages.append({"stage": "apply_fillets", "status": "completed"})
        except WorkflowFailure as exc:
            if "interior bracket edges" not in str(exc):
                raise
            stages.append(
                {
                    "stage": "apply_fillets",
                    "status": "skipped",
                    "reason": "no fillet-eligible edges on combined socket+lever body",
                }
            )

        # === Export ===
        export_path = spec.output_path or "valve_handle.stl"
        self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(
                body_token=combined_body_token,
                output_path=export_path,
            ),
        )
        stages.append(
            {
                "stage": "export_stl",
                "status": "completed",
                "file_path": export_path,
            }
        )

        return {
            "ok": True,
            "workflow": "valve_handle",
            "workflow_basis": "explicit",
            "body_token": combined_body_token,
            "stages": stages,
            "export": {"file_path": export_path},
        }
