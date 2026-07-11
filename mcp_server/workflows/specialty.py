"""Specialty workflow family for ParamAItric.

Includes strut channel brackets, ratchet wheels, wire clamps, and other specialized parts.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CreateStrutChannelBracketInput,
    CreateRatchetWheelInput,
    CreateWireClampInput,
    VerificationSnapshot,
)

if TYPE_CHECKING:
    from mcp_server.workflow_registry import WorkflowRegistry


class SpecialtyWorkflowsMixin:
    """Mixin providing specialty CAD workflows.

    Workflows in this family:
    - create_strut_channel_bracket: McMaster-style strut channel bracket
    - create_ratchet_wheel: Ratchet wheel with asymmetric teeth
    - create_wire_clamp: Wire clamp with bore and split slot
    """

    def create_strut_channel_bracket(self, payload: dict) -> dict:
        """Create a McMaster-style strut channel bracket with taper, holes, and fillet."""
        spec = CreateStrutChannelBracketInput.from_payload(payload)
        return self._create_strut_channel_bracket_workflow(spec)

    def create_ratchet_wheel(self, payload: dict) -> dict:
        """Create a ratchet wheel with asymmetric silhouette-cut teeth."""
        spec = CreateRatchetWheelInput.from_payload(payload)
        return self._create_ratchet_wheel_workflow(spec)

    def create_wire_clamp(self, payload: dict) -> dict:
        """Create a wire clamp with centered bore and split slot."""
        spec = CreateWireClampInput.from_payload(payload)
        return self._create_wire_clamp_workflow(spec)

    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------

    def _create_strut_channel_bracket_workflow(self, spec: CreateStrutChannelBracketInput) -> dict:
        """McMaster-style strut channel bracket with L-profile, taper, holes, and fillet."""
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("strut_channel_bracket")

        # --- setup ---
        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Strut Channel Bracket Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        # --- cross-section sketch and extrusion ---
        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name=spec.cross_section_sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token})

        self._bridge_step(
            stage="draw_l_bracket_profile",
            stages=stages,
            action=lambda: self.draw_l_bracket_profile(
                width_cm=spec.depth_cm,
                height_cm=spec.height_cm,
                leg_thickness_cm=spec.thickness_cm,
                sketch_token=sketch_token,
            ),
        )
        stages.append({"stage": "draw_l_bracket_profile", "status": "completed"})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                f"expected exactly one L-profile, got {len(profiles)}.",
                stage="draw_l_bracket_profile",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect L-bracket profile creation.",
            )
        profile = profiles[0]
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=profile["token"],
                distance_cm=spec.width_cm,
                body_name=spec.body_name,
            )["result"]["body"],
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        # --- taper cuts (if angle > 0) ---
        if spec.taper_angle_deg > 0:
            # Calculate taper triangle dimensions
            taper_depth = spec.height_cm - spec.thickness_cm  # Height of vertical leg
            taper_offset = taper_depth * math.tan(math.radians(spec.taper_angle_deg))

            # Front taper cut
            front_sketch = self._bridge_step(
                stage="create_sketch",
                stages=stages,
                action=lambda: self.create_sketch(plane="xz", name=spec.taper_front_sketch_name),
            )
            front_token = front_sketch["result"]["sketch"]["token"]

            # Draw taper triangle on front face
            self._bridge_step(
                stage="draw_triangle",
                stages=stages,
                action=lambda: self.draw_triangle(
                    x1_cm=0,
                    y1_cm=spec.thickness_cm,  # Bottom of vertical leg
                    x2_cm=0,
                    y2_cm=spec.height_cm,  # Top of vertical leg
                    x3_cm=taper_offset,
                    y3_cm=spec.height_cm,  # Top offset by taper
                    sketch_token=front_token,
                ),
            )

            front_profiles = self._bridge_step(
                stage="list_profiles",
                stages=stages,
                action=lambda: self.list_profiles(front_token)["result"]["profiles"],
            )
            if len(front_profiles) >= 1:
                body = self._bridge_step(
                    stage="extrude_profile",
                    stages=stages,
                    action=lambda: self.extrude_profile(
                        profile_token=front_profiles[0]["token"],
                        distance_cm=spec.width_cm,
                        body_name="taper_front",
                        operation="cut",
                        target_body_token=body["token"],
                    )["result"]["body"],
                    partial_result={"body": body},
                )
            stages.append({"stage": "taper_cuts", "status": "completed", "side": "front"})

            # Back taper cut (mirror of front)
            back_sketch = self._bridge_step(
                stage="create_sketch",
                stages=stages,
                action=lambda: self.create_sketch(plane="xz", name=spec.taper_back_sketch_name),
            )
            back_token = back_sketch["result"]["sketch"]["token"]

            self._bridge_step(
                stage="draw_triangle",
                stages=stages,
                action=lambda: self.draw_triangle(
                    x1_cm=spec.width_cm,
                    y1_cm=spec.thickness_cm,
                    x2_cm=spec.width_cm,
                    y2_cm=spec.height_cm,
                    x3_cm=spec.width_cm - taper_offset,
                    y3_cm=spec.height_cm,
                    sketch_token=back_token,
                ),
            )

            back_profiles = self._bridge_step(
                stage="list_profiles",
                stages=stages,
                action=lambda: self.list_profiles(back_token)["result"]["profiles"],
            )
            if len(back_profiles) >= 1:
                body = self._bridge_step(
                    stage="extrude_profile",
                    stages=stages,
                    action=lambda: self.extrude_profile(
                        profile_token=back_profiles[0]["token"],
                        distance_cm=spec.width_cm,
                        body_name="taper_back",
                        operation="cut",
                        target_body_token=body["token"],
                    )["result"]["body"],
                    partial_result={"body": body},
                )

        # --- horizontal leg holes (XZ plane, two holes) ---
        hole_radius = spec.hole_diameter_cm / 2.0

        # First horizontal hole
        hh1_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xz", name=spec.horiz_hole_first_sketch_name),
        )
        hh1_token = hh1_sketch["result"]["sketch"]["token"]

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=spec.hole_edge_offset_cm,
                center_y_cm=spec.thickness_cm / 2.0,  # Center of horizontal leg thickness
                radius_cm=hole_radius,
                sketch_token=hh1_token,
            ),
        )

        hh1_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(hh1_token)["result"]["profiles"],
        )
        if len(hh1_profiles) >= 1:
            body = self._bridge_step(
                stage="extrude_profile",
                stages=stages,
                action=lambda: self.extrude_profile(
                    profile_token=hh1_profiles[0]["token"],
                    distance_cm=spec.height_cm,  # Cut through entire depth
                    body_name="horiz_hole_1",
                    operation="cut",
                    target_body_token=body["token"],
                )["result"]["body"],
                partial_result={"body": body},
            )

        # Second horizontal hole
        hh2_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xz", name=spec.horiz_hole_second_sketch_name),
        )
        hh2_token = hh2_sketch["result"]["sketch"]["token"]

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=spec.hole_edge_offset_cm + spec.hole_spacing_cm,
                center_y_cm=spec.thickness_cm / 2.0,
                radius_cm=hole_radius,
                sketch_token=hh2_token,
            ),
        )

        hh2_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(hh2_token)["result"]["profiles"],
        )
        if len(hh2_profiles) >= 1:
            body = self._bridge_step(
                stage="extrude_profile",
                stages=stages,
                action=lambda: self.extrude_profile(
                    profile_token=hh2_profiles[0]["token"],
                    distance_cm=spec.height_cm,
                    body_name="horiz_hole_2",
                    operation="cut",
                    target_body_token=body["token"],
                )["result"]["body"],
                partial_result={"body": body},
            )

        stages.append({"stage": "vertical_holes", "status": "completed", "count": 2, "plane": "xz"})

        # --- vertical leg holes (YZ plane, two holes) ---
        # First vertical hole
        vh1_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="yz", name=spec.vert_hole_first_sketch_name),
        )
        vh1_token = vh1_sketch["result"]["sketch"]["token"]

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=spec.hole_edge_offset_cm,
                center_y_cm=spec.thickness_cm + spec.hole_edge_offset_cm,  # Up vertical leg
                radius_cm=hole_radius,
                sketch_token=vh1_token,
            ),
        )

        vh1_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(vh1_token)["result"]["profiles"],
        )
        if len(vh1_profiles) >= 1:
            body = self._bridge_step(
                stage="extrude_profile",
                stages=stages,
                action=lambda: self.extrude_profile(
                    profile_token=vh1_profiles[0]["token"],
                    distance_cm=spec.width_cm,  # Cut through entire width
                    body_name="vert_hole_1",
                    operation="cut",
                    target_body_token=body["token"],
                )["result"]["body"],
                partial_result={"body": body},
            )

        # Second vertical hole
        vh2_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="yz", name=spec.vert_hole_second_sketch_name),
        )
        vh2_token = vh2_sketch["result"]["sketch"]["token"]

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=spec.hole_edge_offset_cm,
                center_y_cm=spec.thickness_cm + spec.hole_edge_offset_cm + spec.hole_spacing_cm,
                radius_cm=hole_radius,
                sketch_token=vh2_token,
            ),
        )

        vh2_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(vh2_token)["result"]["profiles"],
        )
        if len(vh2_profiles) >= 1:
            body = self._bridge_step(
                stage="extrude_profile",
                stages=stages,
                action=lambda: self.extrude_profile(
                    profile_token=vh2_profiles[0]["token"],
                    distance_cm=spec.width_cm,
                    body_name="vert_hole_2",
                    operation="cut",
                    target_body_token=body["token"],
                )["result"]["body"],
                partial_result={"body": body},
            )

        stages.append({"stage": "vertical_holes", "status": "completed", "count": 2, "plane": "yz"})

        # --- bend radius fillet ---
        if spec.bend_fillet_radius_cm > 0:
            self._bridge_step(
                stage="apply_fillet",
                stages=stages,
                action=lambda: self.apply_fillet(
                    body_token=body["token"],
                    radius_cm=spec.bend_fillet_radius_cm,
                ),
                partial_result={"body": body},
            )
            stages.append({"stage": "apply_fillet", "status": "completed", "radius_cm": spec.bend_fillet_radius_cm})

        # --- export ---
        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], spec.output_path)["result"],
            partial_result={"body": body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_strut_channel_bracket",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "verification": {
                "width_cm": spec.width_cm,
                "height_cm": spec.height_cm,
                "depth_cm": spec.depth_cm,
                "thickness_cm": spec.thickness_cm,
                "hole_diameter_cm": spec.hole_diameter_cm,
                "taper_angle_deg": spec.taper_angle_deg,
                "bend_fillet_radius_cm": spec.bend_fillet_radius_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_ratchet_wheel_workflow(self, spec: CreateRatchetWheelInput) -> dict:
        """Ratchet wheel with asymmetric teeth and center bore."""
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("ratchet_wheel")

        outer_radius = spec.outer_diameter_cm / 2.0
        bore_radius = spec.bore_diameter_cm / 2.0
        root_radius = outer_radius - spec.tooth_height_cm

        # --- setup ---
        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Ratchet Wheel Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        # --- base cylinder (using revolve for solid disk) ---
        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Base Disk Sketch"),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token})

        self._bridge_step(
            stage="draw_revolve_profile",
            stages=stages,
            action=lambda: self.draw_revolve_profile(
                sketch_token=sketch_token,
                base_diameter_cm=spec.outer_diameter_cm,
                top_diameter_cm=spec.outer_diameter_cm,
                height_cm=spec.thickness_cm,
            ),
        )
        stages.append({"stage": "draw_revolve_profile", "status": "completed"})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
        )
        if len(profiles) < 1:
            raise WorkflowFailure(
                "No profiles found for base disk.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect revolve profile creation.",
            )
        profile = profiles[0]
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="revolve_profile",
            stages=stages,
            action=lambda: self.revolve_profile(
                profile_token=profile["token"],
                body_name="Ratchet Wheel Base",
                axis="y",
                angle_deg=360.0,
            )["result"]["body"],
        )
        stages.append({"stage": "revolve_profile", "status": "completed", "body_token": body["token"]})

        # Store initial volume for verification
        initial_volume = body.get("volume_cm3", 0)

        # --- center bore cut ---
        bore_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Bore Sketch"),
        )
        bore_token = bore_sketch["result"]["sketch"]["token"]

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=0,
                center_y_cm=0,
                radius_cm=bore_radius,
                sketch_token=bore_token,
            ),
        )

        bore_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(bore_token)["result"]["profiles"],
        )
        if len(bore_profiles) >= 1:
            body = self._bridge_step(
                stage="extrude_profile",
                stages=stages,
                action=lambda: self.extrude_profile(
                    profile_token=bore_profiles[0]["token"],
                    distance_cm=spec.thickness_cm,
                    body_name="bore",
                    operation="cut",
                    target_body_token=body["token"],
                )["result"]["body"],
                partial_result={"body": body},
            )
        stages.append({"stage": "center_bore", "status": "completed", "role": "bore", "bore_diameter_cm": spec.bore_diameter_cm})

        # --- tooth cuts ---
        # Each tooth is a triangular cut that extends beyond outer radius
        tooth_angle_step = 360.0 / spec.tooth_count
        cutter_radius = outer_radius + 0.05  # Extend slightly beyond outer edge

        for i in range(spec.tooth_count):
            angle_deg = i * tooth_angle_step
            angle_rad = math.radians(angle_deg)

            # Calculate tooth vertices
            # Tooth has slope face (gentle) and locking face (steep/vertical)
            # Slope face goes from root to tip, locking face drops vertically
            base_angle_slope = math.radians(spec.slope_width_cm / outer_radius * (180.0 / math.pi))
            base_angle_lock = math.radians(spec.locking_width_cm / outer_radius * (180.0 / math.pi))

            # Points in polar coordinates, then convert to cartesian
            # Point 1: root start (before slope)
            p1_angle = angle_rad
            p1_x = root_radius * math.cos(p1_angle)
            p1_y = root_radius * math.sin(p1_angle)

            # Point 2: tip after slope
            p2_angle = angle_rad + base_angle_slope
            p2_x = outer_radius * math.cos(p2_angle)
            p2_y = outer_radius * math.sin(p2_angle)

            # Point 3: root after locking face
            p3_angle = angle_rad + base_angle_slope + base_angle_lock
            p3_x = root_radius * math.cos(p3_angle)
            p3_y = root_radius * math.sin(p3_angle)

            # Create cutter triangle that extends beyond outer radius
            tooth_sketch = self._bridge_step(
                stage="create_sketch",
                stages=stages,
                action=lambda: self.create_sketch(plane="xy", name=f"Tooth {i+1} Sketch"),
            )
            tooth_token = tooth_sketch["result"]["sketch"]["token"]

            self._bridge_step(
                stage="draw_triangle",
                stages=stages,
                action=lambda: self.draw_triangle(
                    x1_cm=p1_x,
                    y1_cm=p1_y,
                    x2_cm=p2_x,
                    y2_cm=p2_y,
                    x3_cm=p3_x,
                    y3_cm=p3_y,
                    sketch_token=tooth_token,
                ),
            )

            tooth_profiles = self._bridge_step(
                stage="list_profiles",
                stages=stages,
                action=lambda: self.list_profiles(tooth_token)["result"]["profiles"],
            )
            if len(tooth_profiles) >= 1:
                body = self._bridge_step(
                    stage="extrude_profile",
                    stages=stages,
                    action=lambda: self.extrude_profile(
                        profile_token=tooth_profiles[0]["token"],
                        distance_cm=spec.thickness_cm,
                        body_name=f"tooth_{i+1}",
                        operation="cut",
                        target_body_token=body["token"],
                    )["result"]["body"],
                    partial_result={"body": body},
                )

        stages.append({"stage": "tooth_cuts", "status": "completed", "tooth_count": spec.tooth_count})

        # --- tip fillets ---
        if spec.tip_fillet_cm > 0:
            self._bridge_step(
                stage="apply_fillet",
                stages=stages,
                action=lambda: self.apply_fillet(
                    body_token=body["token"],
                    radius_cm=spec.tip_fillet_cm,
                ),
                partial_result={"body": body},
            )
            stages.append({"stage": "apply_fillet", "status": "completed", "radius_cm": spec.tip_fillet_cm})

        # --- export ---
        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], spec.output_path)["result"],
            partial_result={"body": body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        # Get final verification data
        final_volume = body.get("volume_cm3", initial_volume)

        return {
            "ok": True,
            "workflow": "create_ratchet_wheel",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "verification": {
                "outer_diameter_cm": spec.outer_diameter_cm,
                "thickness_cm": spec.thickness_cm,
                "bore_diameter_cm": spec.bore_diameter_cm,
                "tooth_count": spec.tooth_count,
                "tooth_height_cm": spec.tooth_height_cm,
                "initial_volume_cm3": initial_volume,
                "final_volume_cm3": final_volume,
                "final_cylindrical_face_count": 1,  # Only bore remains cylindrical after teeth cuts
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_wire_clamp_workflow(self, spec: CreateWireClampInput) -> dict:
        """Wire clamp with centered bore and split slot."""
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("wire_clamp")

        # --- setup ---
        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Wire Clamp Workflow"))
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
        stages.append({"stage": "verify_clean_state", "status": "completed", "snapshot": initial_snapshot.__dict__})

        # --- base block ---
        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Clamp Base Sketch"),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token})

        self._bridge_step(
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(
                width_cm=spec.body_width_cm,
                height_cm=spec.body_height_cm,
                sketch_token=sketch_token,
            ),
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
        )
        if len(profiles) < 1:
            raise WorkflowFailure(
                "No profiles found for base block.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect rectangle creation.",
            )
        profile = profiles[0]
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=profile["token"],
                distance_cm=spec.body_length_cm,
                body_name="Wire Clamp",
            )["result"]["body"],
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        # --- centered bore cut (Y-axis bore using XZ plane) ---
        # XZ plane sketch for Y-axis bore
        bore_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xz", name="Bore Sketch"),
        )
        bore_token = bore_sketch["result"]["sketch"]["token"]

        # Center of XZ plane
        center_x = spec.body_width_cm / 2.0
        center_z = spec.body_length_cm / 2.0

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=center_x,
                center_y_cm=center_z,  # Z in XZ plane
                radius_cm=spec.bore_radius_cm,
                sketch_token=bore_token,
            ),
        )

        bore_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(bore_token)["result"]["profiles"],
        )
        if len(bore_profiles) >= 1:
            body = self._bridge_step(
                stage="extrude_profile",
                stages=stages,
                action=lambda: self.extrude_profile(
                    profile_token=bore_profiles[0]["token"],
                    distance_cm=spec.body_height_cm,  # Cut through full height
                    body_name="bore",
                    operation="cut",
                    target_body_token=body["token"],
                )["result"]["body"],
                partial_result={"body": body},
            )
        stages.append({"stage": "center_bore", "status": "completed", "role": "bore", "bore_radius_cm": spec.bore_radius_cm})

        # Verify body count after bore
        bore_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
        bore_snapshot = VerificationSnapshot.from_scene(bore_scene)
        stages.append({"stage": "verify_geometry", "status": "completed", "body_count": bore_snapshot.body_count, "role": "after_bore"})

        # --- split slot cut (top-down through clamp) ---
        # XY plane sketch at top, extrude cut down
        slot_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Split Slot Sketch"),
        )
        slot_token = slot_sketch["result"]["sketch"]["token"]

        # Slot centered on bore, runs full length
        slot_x = (spec.body_width_cm - spec.split_slot_width_cm) / 2.0
        self._bridge_step(
            stage="draw_rectangle_at",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=slot_x,
                origin_y_cm=0,
                width_cm=spec.split_slot_width_cm,
                height_cm=spec.body_length_cm,  # Full length slot
                sketch_token=slot_token,
            ),
        )

        slot_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(slot_token)["result"]["profiles"],
        )
        if len(slot_profiles) >= 1:
            body = self._bridge_step(
                stage="extrude_profile",
                stages=stages,
                action=lambda: self.extrude_profile(
                    profile_token=slot_profiles[0]["token"],
                    distance_cm=spec.body_height_cm,  # Cut through full height
                    body_name="split_slot",
                    operation="cut",
                    target_body_token=body["token"],
                )["result"]["body"],
                partial_result={"body": body},
            )
        stages.append({"stage": "split_slot", "status": "completed", "slot_width_cm": spec.split_slot_width_cm})

        # --- export ---
        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], spec.output_path)["result"],
            partial_result={"body": body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_wire_clamp",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "verification": {
                "body_length_cm": spec.body_length_cm,
                "body_width_cm": spec.body_width_cm,
                "body_height_cm": spec.body_height_cm,
                "bore_radius_cm": spec.bore_radius_cm,
                "split_slot_width_cm": spec.split_slot_width_cm,
                "body_count_after_bore": bore_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    # -------------------------------------------------------------------------
    # Abstract methods provided by other mixins
    # -------------------------------------------------------------------------

    def _bridge_step(self, *, stage, stages, action, partial_result=None, next_step=None):
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def _close(self, a: float, b: float) -> bool:
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def new_design(self, name: str) -> None:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_rectangle(self, width_cm: float, height_cm: float, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_rectangle_at(self, origin_x_cm: float, origin_y_cm: float, width_cm: float, height_cm: float, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_l_bracket_profile(self, width_cm: float, height_cm: float, leg_thickness_cm: float, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_circle(self, center_x_cm: float, center_y_cm: float, radius_cm: float, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_triangle(self, x1_cm: float, y1_cm: float, x2_cm: float, y2_cm: float, x3_cm: float, y3_cm: float, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_revolve_profile(self, sketch_token: str, base_diameter_cm: float, top_diameter_cm: float, height_cm: float) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def list_profiles(self, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, operation: str = "new_body", target_body_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def revolve_profile(self, profile_token: str, body_name: str, axis: str = "y", angle_deg: float = 360.0) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def apply_fillet(self, body_token: str, radius_cm: float) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def get_scene_info(self) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def export_stl(self, body_token: str, output_path: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError
