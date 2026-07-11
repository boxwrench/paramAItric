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

    def _create_valve_handle_workflow(self, spec: CreateValveHandleInput) -> dict:
        """Execute valve handle creation workflow.

        Workflow:
        1. Create socket profile (hex/square/round) on XY plane
        2. Extrude socket to stem_depth
        3. Create lever profile on YZ plane (side view)
        4. Extrude lever symmetric, combine with socket
        5. Cut set screw hole if specified
        6. Apply fillets at stress concentrations
        7. Export STL
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

        # === Phase 1: Socket Body ===
        # Create sketch on XY plane for socket profile
        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="socket_profile"),
        )
        socket_sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_socket_sketch",
                "status": "completed",
                "sketch_token": socket_sketch_token,
            }
        )

        # Draw socket shape based on type
        if spec.socket_type == "hex":
            # Hex socket: 6-sided polygon
            # radius = stem_width / (2 * cos(30deg)) = stem_width / sqrt(3)
            radius = (spec.stem_width_cm + spec.clearance_cm) / math.sqrt(3)
            self._bridge_step(
                stage="draw_socket_profile",
                stages=stages,
                action=lambda: self.draw_polygon(
                    center_x_cm=0,
                    center_y_cm=0,
                    radius_cm=radius,
                    num_sides=6,
                    sketch_token=socket_sketch_token,
                ),
            )
        elif spec.socket_type == "square":
            # Square socket: 4-sided polygon
            # radius = stem_width / (2 * cos(45deg)) = stem_width / sqrt(2)
            radius = (spec.stem_width_cm + spec.clearance_cm) / math.sqrt(2)
            self._bridge_step(
                stage="draw_socket_profile",
                stages=stages,
                action=lambda: self.draw_polygon(
                    center_x_cm=0,
                    center_y_cm=0,
                    radius_cm=radius,
                    num_sides=4,
                    sketch_token=socket_sketch_token,
                ),
            )
        else:  # round_flat
            # Round with flat: circle for now (flat cut is advanced)
            self._bridge_step(
                stage="draw_socket_profile",
                stages=stages,
                action=lambda: self.draw_circle(
                    center_x_cm=0,
                    center_y_cm=0,
                    radius_cm=(spec.stem_width_cm + spec.clearance_cm) / 2,
                    sketch_token=socket_sketch_token,
                ),
            )

        # Get socket profile
        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(socket_sketch_token)["result"]["profiles"],
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                f"expected exactly one socket profile, got {len(profiles)}.",
                stage="draw_socket_profile",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect socket profile creation.",
            )
        socket_profile = profiles[0]
        stages.append(
            {
                "stage": "draw_socket_profile",
                "status": "completed",
                "profile_token": socket_profile["token"],
            }
        )

        # Extrude socket
        socket_body = self._bridge_step(
            stage="extrude_socket",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=socket_profile["token"],
                distance_cm=spec.stem_depth_cm,
                body_name="socket_body",
            )["result"]["body"],
        )
        socket_body_token = socket_body["token"]
        stages.append(
            {
                "stage": "extrude_socket",
                "status": "completed",
                "body_token": socket_body_token,
            }
        )

        # === Phase 2: Lever Arm ===
        # Create sketch on YZ plane for lever profile
        lever_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="yz", name="lever_profile"),
        )
        lever_sketch_token = lever_sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_lever_sketch",
                "status": "completed",
                "sketch_token": lever_sketch_token,
            }
        )

        # Draw lever as rectangle extending from socket
        # Rectangle: from socket edge to lever_length, centered on Y axis
        socket_radius = spec.stem_width_cm / 2 + 0.2  # Approximate socket outer radius
        self._bridge_step(
            stage="draw_lever_profile",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=socket_radius,
                origin_y_cm=-spec.lever_width_cm / 2,
                width_cm=spec.lever_length_cm - socket_radius,
                height_cm=spec.lever_width_cm,
                sketch_token=lever_sketch_token,
            ),
        )

        # Get lever profile
        lever_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(lever_sketch_token)["result"]["profiles"],
        )
        if len(lever_profiles) != 1:
            raise WorkflowFailure(
                f"expected exactly one lever profile, got {len(lever_profiles)}.",
                stage="draw_lever_profile",
                classification="verification_failed",
                partial_result={"profiles": lever_profiles, "stages": stages},
                next_step="Inspect lever profile creation.",
            )
        lever_profile = lever_profiles[0]
        stages.append(
            {
                "stage": "draw_lever_profile",
                "status": "completed",
                "profile_token": lever_profile["token"],
            }
        )

        # Extrude lever symmetric
        lever_body = self._bridge_step(
            stage="extrude_lever",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=lever_profile["token"],
                distance_cm=spec.lever_thickness_cm,
                body_name="lever_body",
                symmetric=True,
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

        # Combine socket and lever
        combined = self._bridge_step(
            stage="combine_bodies",
            stages=stages,
            action=lambda: self.combine_bodies(
                target_body_token=socket_body_token,
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

        # === Phase 3: Set Screw Hole (Optional) ===
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
                    center_y_cm=spec.stem_depth_cm / 2,
                    radius_cm=spec.set_screw_diameter_cm / 2,
                    sketch_token=screw_sketch_token,
                ),
            )

            screw_profiles = self._bridge_step(
                stage="list_profiles",
                stages=stages,
                action=lambda: self.list_profiles(screw_sketch_token)["result"]["profiles"],
            )
            if screw_profiles:
                screw_profile = screw_profiles[0]
                self._bridge_step(
                    stage="cut_set_screw_hole",
                    stages=stages,
                    action=lambda: self.extrude_profile(
                        profile_token=screw_profile["token"],
                        distance_cm=spec.stem_width_cm + 0.5,
                        body_name="set_screw_cut",
                        operation="cut",
                        target_body_token=combined_body_token,
                    ),
                )

            stages.append({"stage": "set_screw_hole", "status": "completed"})

        # === Phase 4: Finishing ===
        # Apply fillets at stress concentrations
        self._bridge_step(
            stage="apply_fillets",
            stages=stages,
            action=lambda: self.apply_fillet(
                body_token=combined_body_token,
                radius_cm=spec.fillet_radius_cm,
                edge_selection="all",
            ),
        )
        stages.append({"stage": "apply_fillets", "status": "completed"})

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
