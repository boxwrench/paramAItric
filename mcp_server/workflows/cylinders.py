"""Cylinder and revolve workflow family for ParamAItric.

Includes cylinders, tubes, revolved solids, bushings, and couplers.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CreateCylinderInput,
    CreateTubeInput,
    CreateRevolveInput,
    CreateTaperedKnobBlankInput,
    CreateFlangedBushingInput,
    CreateShaftCouplerInput,
    CreatePipeClampHalfInput,
    CreateTubeMountingPlateInput,
    CreateTHandleWithSquareSocketInput,
    VerificationSnapshot,
)

if TYPE_CHECKING:
    from mcp_server.workflow_registry import WorkflowRegistry


class CylinderWorkflowsMixin:
    """Mixin providing cylinder and revolve-related CAD workflows.

    Workflows in this family:
    - create_cylinder: Cylindrical solid
    - create_tube: Hollow tube with bore
    - create_revolve: Revolved tapered solid
    - create_tapered_knob_blank: Tapered knob with stem socket
    - create_flanged_bushing: Bushing with flange and axial bore
    - create_shaft_coupler: Coupler with axial and cross-pin holes
    - create_pipe_clamp_half: Half clamp with saddle and bolt holes
    - create_tube_mounting_plate: Wall plate with tube socket
    - create_t_handle_with_square_socket: T-handle with square valve socket
    """

    def create_cylinder(self, payload: dict) -> dict:
        """Create a cylindrical solid."""
        spec = CreateCylinderInput.from_payload(payload)
        return self._create_cylinder_workflow(spec)

    def create_tube(self, payload: dict) -> dict:
        """Create a hollow tube with centered bore cut."""
        spec = CreateTubeInput.from_payload(payload)
        return self._create_tube_workflow(spec)

    def create_revolve(self, payload: dict) -> dict:
        """Create a revolved solid from a tapered side profile."""
        raise NotImplementedError("Cylinder workflows not yet migrated from server.py")

    def create_tapered_knob_blank(self, payload: dict) -> dict:
        """Create a tapered knob blank with centered stem socket."""
        raise NotImplementedError("Cylinder workflows not yet migrated from server.py")

    def create_flanged_bushing(self, payload: dict) -> dict:
        """Create a flanged bushing with axial bore."""
        raise NotImplementedError("Cylinder workflows not yet migrated from server.py")

    def create_shaft_coupler(self, payload: dict) -> dict:
        """Create a shaft coupler with axial bore and orthogonal cross-pin hole."""
        raise NotImplementedError("Cylinder workflows not yet migrated from server.py")

    def create_pipe_clamp_half(self, payload: dict) -> dict:
        """Create a half clamp body with non-XY pipe saddle cut and mirrored bolt holes."""
        raise NotImplementedError("Cylinder workflows not yet migrated from server.py")

    def create_tube_mounting_plate(self, payload: dict) -> dict:
        """Create a wall-mount plate with tube socket joined into one body."""
        raise NotImplementedError("Cylinder workflows not yet migrated from server.py")

    def create_t_handle_with_square_socket(self, payload: dict) -> dict:
        """Create a T-handle with square valve socket and comfort chamfer."""
        raise NotImplementedError("Cylinder workflows not yet migrated from server.py")

    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------

    def _create_cylinder_workflow(self, spec: CreateCylinderInput) -> dict:
        """Core cylinder workflow: circle sketch extruded to cylinder."""
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("cylinder")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Cylinder Workflow"))
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

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": sketch_token,
                "plane": spec.plane,
            }
        )

        radius_cm = spec.diameter_cm / 2.0
        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=radius_cm,
                center_y_cm=radius_cm,
                radius_cm=radius_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "diameter_cm": spec.diameter_cm})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                "Cylinder workflow expected exactly one profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the circle sketch and remove ambiguity before extrusion.",
            )
        profile = profiles[0]
        expected_profile_dimensions = {
            "width_cm": spec.diameter_cm,
            "height_cm": spec.diameter_cm,
        }
        actual_profile_dimensions = {
            "width_cm": profile["width_cm"],
            "height_cm": profile["height_cm"],
        }
        if actual_profile_dimensions != expected_profile_dimensions:
            raise WorkflowFailure(
                "Cylinder workflow profile verification failed.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected": expected_profile_dimensions,
                    "stages": stages,
                },
                next_step="Inspect the circle radius and selected profile before extrusion.",
            )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles)})

        body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=profile["token"],
                distance_cm=spec.height_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": profile["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": body["token"]})

        scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
        snapshot = VerificationSnapshot.from_scene(scene)
        if snapshot.body_count != 1:
            raise WorkflowFailure(
                "Cylinder workflow verification failed: expected exactly one body.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene, "stages": stages},
                next_step="Preserve the partial model and inspect body creation before retrying.",
            )
        expected_dimensions = {
            "width_cm": spec.diameter_cm,
            "height_cm": spec.diameter_cm,
            "thickness_cm": spec.height_cm,
        }
        actual_dimensions = {
            "width_cm": body["width_cm"],
            "height_cm": body["height_cm"],
            "thickness_cm": body["thickness_cm"],
        }
        if actual_dimensions != expected_dimensions:
            raise WorkflowFailure(
                "Cylinder workflow verification failed: body dimensions do not match the requested values.",
                stage="verify_dimensions",
                classification="verification_failed",
                partial_result={"body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect the circle profile and extrusion distance before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": snapshot.__dict__,
                "dimensions": actual_dimensions,
            }
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(body["token"], spec.output_path)["result"],
            partial_result={"body": body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_cylinder",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": body,
            "verification": {
                "body_count": snapshot.body_count,
                "sketch_count": snapshot.sketch_count,
                "expected_diameter_cm": spec.diameter_cm,
                "expected_height_cm": spec.height_cm,
                "actual_diameter_cm": body["width_cm"],
                "actual_secondary_diameter_cm": body["height_cm"],
                "actual_height_cm": body["thickness_cm"],
                "sketch_plane": spec.plane,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_tube_workflow(self, spec: CreateTubeInput) -> dict:
        """Core tube workflow: outer cylinder with bore cut."""
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("tube")

        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Tube Workflow"))
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

        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.sketch_name),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": sketch_token, "plane": spec.plane})

        outer_radius_cm = spec.outer_diameter_cm / 2.0
        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=outer_radius_cm,
                center_y_cm=outer_radius_cm,
                radius_cm=outer_radius_cm,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "diameter_cm": spec.outer_diameter_cm, "profile_role": "outer"})

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        if len(profiles) != 1:
            raise WorkflowFailure(
                "Tube workflow expected exactly one outer profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={"profiles": profiles, "stages": stages},
                next_step="Inspect the outer circle sketch before extrusion.",
            )
        outer_profile = profiles[0]
        if not self._close(outer_profile.get("width_cm"), spec.outer_diameter_cm) or not self._close(
            outer_profile.get("height_cm"), spec.outer_diameter_cm
        ):
            raise WorkflowFailure(
                "Tube workflow outer profile verification failed.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected": {"width_cm": spec.outer_diameter_cm, "height_cm": spec.outer_diameter_cm},
                    "stages": stages,
                },
                next_step="Inspect the outer circle radius before extrusion.",
            )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(profiles), "profile_role": "outer"})

        outer_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=outer_profile["token"],
                distance_cm=spec.height_cm,
                body_name=spec.body_name,
            )["result"]["body"],
            partial_result={"profile_token": outer_profile["token"]},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": outer_body["token"], "operation": "new_body"})

        outer_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=outer_body,
            expected_dimensions={
                "width_cm": spec.outer_diameter_cm,
                "height_cm": spec.outer_diameter_cm,
                "thickness_cm": spec.height_cm,
            },
            failure_message="Tube workflow outer-body verification failed.",
            next_step="Inspect the outer circle profile and extrusion distance before retrying.",
            operation_label="outer_body",
        )

        # Bore cut stage - inline instead of using helper
        bore_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane=spec.plane, name=spec.bore_sketch_name),
        )
        bore_sketch_token = bore_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": bore_sketch_token, "plane": spec.plane, "sketch_role": "tube_bore"})

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=outer_radius_cm,
                center_y_cm=outer_radius_cm,
                radius_cm=spec.inner_diameter_cm / 2.0,
                sketch_token=bore_sketch_token,
            ),
            partial_result={"sketch_token": bore_sketch_token},
        )
        stages.append({"stage": "draw_circle", "status": "completed", "profile_role": "tube_bore", "diameter_cm": spec.inner_diameter_cm})

        bore_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(bore_sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": bore_sketch_token},
        )
        selected_bore_profile = self._select_profile_by_dimensions(
            bore_profiles,
            expected_width_cm=spec.inner_diameter_cm,
            expected_height_cm=spec.inner_diameter_cm,
            workflow_label="Tube",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(bore_profiles), "profile_role": "tube_bore"})

        tube_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_bore_profile["token"],
                distance_cm=spec.height_cm,
                body_name="tube_bore",
                operation="cut",
                target_body_token=outer_body["token"],
            )["result"]["body"],
            partial_result={"profile_token": selected_bore_profile["token"], "body": outer_body},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": tube_body["token"], "operation": "cut", "profile_role": "tube_bore"})

        tube_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=tube_body,
            expected_dimensions={
                "width_cm": spec.outer_diameter_cm,
                "height_cm": spec.outer_diameter_cm,
                "thickness_cm": spec.height_cm,
            },
            failure_message="Tube tube_bore_cut verification failed.",
            next_step="Inspect the cut sketch and cut depth before retrying.",
            operation_label="tube_bore_cut",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(tube_body["token"], spec.output_path)["result"],
            partial_result={"body": tube_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_tube",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": tube_body,
            "verification": {
                "body_count": tube_snapshot.body_count,
                "sketch_count": tube_snapshot.sketch_count,
                "outer_diameter_cm": spec.outer_diameter_cm,
                "inner_diameter_cm": spec.inner_diameter_cm,
                "height_cm": spec.height_cm,
                "actual_outer_diameter_cm": tube_body["width_cm"],
                "actual_secondary_outer_diameter_cm": tube_body["height_cm"],
                "actual_height_cm": tube_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "outer_body_snapshot_body_count": outer_snapshot.body_count,
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

    def new_design(self, name: str = "ParamAItric Design") -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def get_scene_info(self) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def draw_circle(self, center_x_cm: float, center_y_cm: float, radius_cm: float, sketch_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def list_profiles(self, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, **kwargs) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def export_stl(self, body_token: str, output_path: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError
