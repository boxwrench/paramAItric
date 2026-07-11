"""Enclosure workflow family for ParamAItric.

Includes boxes, lids, shells, snap-fit enclosures, and telescoping containers.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import (
    CreateSimpleEnclosureInput,
    CreateOpenBoxBodyInput,
    CreateLidForBoxInput,
    CreateBoxWithLidInput,
    CreateFlushLidEnclosurePairInput,
    CreateProjectBoxWithStandoffsInput,
    CreateSnapFitEnclosureInput,
    CreateTelescopingContainersInput,
    VerificationSnapshot,
)

if TYPE_CHECKING:
    from mcp_server.workflow_registry import WorkflowRegistry


class EnclosureWorkflowsMixin:
    """Mixin providing enclosure-related CAD workflows.

    Workflows in this family:
    - create_simple_enclosure: Open-top rectangular enclosure by shelling
    - create_open_box_body: Open-top box with inset cavity
    - create_lid_for_box: Cap lid with perimeter rim
    - create_box_with_lid: Matched box and lid as two bodies
    - create_flush_lid_enclosure_pair: Enclosure base and flush lid
    - create_project_box_with_standoffs: Shelled box with PCB standoffs
    - create_snap_fit_enclosure: Snap-fit box with view holes and wrap-over lid
    - create_telescoping_containers: Three concentric nesting containers
    """

    def create_simple_enclosure(self, payload: dict) -> dict:
        """Create an open-top rectangular enclosure by shelling the top face."""
        spec = CreateSimpleEnclosureInput.from_payload(payload)
        return self._create_simple_enclosure_workflow(spec)

    def create_open_box_body(self, payload: dict) -> dict:
        """Create an open-top box body with an inset cavity cut from an offset floor plane."""
        spec = CreateOpenBoxBodyInput.from_payload(payload)
        return self._create_open_box_body_workflow(spec)

    def create_lid_for_box(self, payload: dict) -> dict:
        """Create a cap lid with a downward perimeter rim."""
        spec = CreateLidForBoxInput.from_payload(payload)
        return self._create_lid_for_box_workflow(spec)

    def create_box_with_lid(self, payload: dict) -> dict:
        """Create a matched box and cap lid as two separate bodies in one design."""
        spec = CreateBoxWithLidInput.from_payload(payload)
        return self._create_box_with_lid_workflow(spec)

    def create_flush_lid_enclosure_pair(self, payload: dict) -> dict:
        """Create a matched enclosure base and flush lid as two separate bodies."""
        raise NotImplementedError("flush_lid_enclosure_pair not yet implemented")

    def create_project_box_with_standoffs(self, payload: dict) -> dict:
        """Create a shelled project box with four internal corner standoffs for PCB mounting."""
        spec = CreateProjectBoxWithStandoffsInput.from_payload(payload)
        return self._create_project_box_with_standoffs_workflow(spec)

    def create_snap_fit_enclosure(self, payload: dict) -> dict:
        """Create a snap-fit enclosure box with view holes and wrap-over snap-on lid."""
        raise NotImplementedError("snap_fit_enclosure not yet implemented")

    def create_telescoping_containers(self, payload: dict) -> dict:
        """Create three concentric nesting rectangular containers with progressive clearances."""
        raise NotImplementedError("telescoping_containers not yet implemented")

    # -------------------------------------------------------------------------
    # Private workflow implementations
    # -------------------------------------------------------------------------

    def _create_simple_enclosure_workflow(self, spec: CreateSimpleEnclosureInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("simple_enclosure")
        inner_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        inner_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        inner_height_cm = spec.height_cm - spec.wall_thickness_cm

        body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="simple_enclosure",
            design_name="Simple Enclosure Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.depth_cm,
            thickness_cm=spec.height_cm,
        )

        shell = self._bridge_step(
            stage="apply_shell",
            stages=stages,
            action=lambda: self.apply_shell(
                body_token=body["token"],
                wall_thickness_cm=spec.wall_thickness_cm,
            )["result"]["shell"],
            partial_result={"body": body},
        )
        self._verify_shell_result(
            shell=shell,
            stages=stages,
            expected_body=body,
            expected_wall_thickness_cm=spec.wall_thickness_cm,
            expected_inner_width_cm=inner_width_cm,
            expected_inner_depth_cm=inner_depth_cm,
            expected_inner_height_cm=inner_height_cm,
        )
        stages.append(
            {
                "stage": "apply_shell",
                "status": "completed",
                "wall_thickness_cm": spec.wall_thickness_cm,
                "removed_face_count": shell["removed_face_count"],
                "open_face": shell["open_face"],
            }
        )

        shell_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=shell,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.depth_cm,
                "thickness_cm": spec.height_cm,
            },
            failure_message="Simple enclosure shell verification failed.",
            next_step="Inspect the top-face shell operation before retrying.",
            operation_label="shell",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(shell["body_token"], spec.output_path)["result"],
            partial_result={"body": shell},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_simple_enclosure",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": shell,
            "verification": {
                "body_count": shell_snapshot.body_count,
                "sketch_count": shell_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_depth_cm": spec.depth_cm,
                "expected_height_cm": spec.height_cm,
                "actual_width_cm": shell["width_cm"],
                "actual_depth_cm": shell["height_cm"],
                "actual_height_cm": shell["thickness_cm"],
                "wall_thickness_cm": spec.wall_thickness_cm,
                "inner_width_cm": shell["inner_width_cm"],
                "inner_depth_cm": shell["inner_depth_cm"],
                "inner_height_cm": shell["inner_height_cm"],
                "open_face": shell["open_face"],
                "removed_face_count": shell["removed_face_count"],
                "base_body_count": base_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_open_box_body_workflow(self, spec: CreateOpenBoxBodyInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("open_box_body")
        cavity_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        cavity_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        cavity_depth_cut_cm = spec.height_cm - spec.floor_thickness_cm

        base_body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="open_box_body",
            design_name="Open Box Body Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.depth_cm,
            thickness_cm=spec.height_cm,
        )

        open_box_body, cavity_snapshot = self._run_rectangle_cut_stage(
            stages=stages,
            workflow_name="open_box_body",
            sketch_name=spec.cavity_sketch_name,
            origin_x_cm=spec.wall_thickness_cm,
            origin_y_cm=spec.wall_thickness_cm,
            width_cm=cavity_width_cm,
            height_cm=cavity_depth_cm,
            cut_depth_cm=cavity_depth_cut_cm,
            body=base_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.depth_cm,
                "thickness_cm": spec.height_cm,
            },
            profile_role="cavity",
            operation_label="cavity_cut",
            sketch_offset_cm=spec.floor_thickness_cm,
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(open_box_body["token"], spec.output_path)["result"],
            partial_result={"body": open_box_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_open_box_body",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": open_box_body,
            "verification": {
                "body_count": cavity_snapshot.body_count,
                "sketch_count": cavity_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_depth_cm": spec.depth_cm,
                "expected_height_cm": spec.height_cm,
                "actual_width_cm": open_box_body["width_cm"],
                "actual_depth_cm": open_box_body["height_cm"],
                "actual_height_cm": open_box_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "wall_thickness_cm": spec.wall_thickness_cm,
                "floor_thickness_cm": spec.floor_thickness_cm,
                "cavity_width_cm": cavity_width_cm,
                "cavity_depth_cm": cavity_depth_cm,
                "base_body_count": base_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_lid_for_box_workflow(self, spec: CreateLidForBoxInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("lid_for_box")
        rim_opening_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        rim_opening_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        total_height_cm = spec.lid_thickness_cm + spec.rim_depth_cm

        base_body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="lid_for_box",
            design_name="Lid For Box Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.depth_cm,
            thickness_cm=total_height_cm,
        )

        lid_body, rim_snapshot = self._run_rectangle_cut_stage(
            stages=stages,
            workflow_name="lid_for_box",
            sketch_name=spec.rim_cut_sketch_name,
            origin_x_cm=spec.wall_thickness_cm,
            origin_y_cm=spec.wall_thickness_cm,
            width_cm=rim_opening_width_cm,
            height_cm=rim_opening_depth_cm,
            cut_depth_cm=spec.rim_depth_cm,
            body=base_body,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.depth_cm,
                "thickness_cm": total_height_cm,
            },
            profile_role="rim_opening",
            operation_label="rim_cut",
        )

        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(lid_body["token"], spec.output_path)["result"],
            partial_result={"body": lid_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})
        return {
            "ok": True,
            "workflow": "create_lid_for_box",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": lid_body,
            "verification": {
                "body_count": rim_snapshot.body_count,
                "sketch_count": rim_snapshot.sketch_count,
                "expected_width_cm": spec.width_cm,
                "expected_depth_cm": spec.depth_cm,
                "expected_height_cm": total_height_cm,
                "actual_width_cm": lid_body["width_cm"],
                "actual_depth_cm": lid_body["height_cm"],
                "actual_height_cm": lid_body["thickness_cm"],
                "sketch_plane": spec.plane,
                "lid_thickness_cm": spec.lid_thickness_cm,
                "rim_depth_cm": spec.rim_depth_cm,
                "wall_thickness_cm": spec.wall_thickness_cm,
                "rim_opening_width_cm": rim_opening_width_cm,
                "rim_opening_depth_cm": rim_opening_depth_cm,
                "base_body_count": base_snapshot.body_count,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_box_with_lid_workflow(self, spec: CreateBoxWithLidInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("box_with_lid")

        cavity_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        cavity_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        cavity_cut_depth_cm = spec.box_height_cm - spec.floor_thickness_cm
        lid_total_height_cm = spec.lid_thickness_cm + spec.rim_depth_cm
        # Cap lid: outer dims extend beyond box exterior by wall + clearance on each side
        lid_width_cm = spec.width_cm + (spec.wall_thickness_cm * 2.0) + (spec.clearance_cm * 2.0)
        lid_depth_cm = spec.depth_cm + (spec.wall_thickness_cm * 2.0) + (spec.clearance_cm * 2.0)
        # Rim cut opening: slightly larger than box exterior so lid slides over it
        rim_opening_width_cm = spec.width_cm + (spec.clearance_cm * 2.0)
        rim_opening_depth_cm = spec.depth_cm + (spec.clearance_cm * 2.0)
        # Centering offsets: lid must be centered over box, not flush at (0,0)
        lid_origin_x_cm = -(spec.wall_thickness_cm + spec.clearance_cm)
        lid_origin_y_cm = -(spec.wall_thickness_cm + spec.clearance_cm)
        rim_origin_x_cm = -spec.clearance_cm
        rim_origin_y_cm = -spec.clearance_cm

        # --- setup ---
        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Box With Lid Workflow"))
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

        # --- box base ---
        box_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Box Outer Sketch"),
        )
        box_sketch_token = box_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": box_sketch_token, "role": "box_base"})

        self._bridge_step(
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(width_cm=spec.width_cm, height_cm=spec.depth_cm, sketch_token=box_sketch_token),
        )
        stages.append({"stage": "draw_rectangle", "status": "completed", "role": "box_base"})

        box_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(box_sketch_token)["result"]["profiles"],
        )
        box_base_profile = self._select_profile_by_dimensions(
            box_profiles,
            expected_width_cm=spec.width_cm,
            expected_height_cm=spec.depth_cm,
            workflow_label="Box with lid",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(box_profiles), "role": "box_base"})

        box_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=box_base_profile["token"],
                distance_cm=spec.box_height_cm,
                body_name="Box Body",
            )["result"]["body"],
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": box_body["token"], "role": "box_base"})

        box_base_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"box_body": box_body},
        )
        box_base_snapshot = VerificationSnapshot.from_scene(box_base_scene)
        if box_base_snapshot.body_count != 1:
            raise WorkflowFailure(
                "Box base extrusion produced unexpected body count.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": box_base_scene, "stages": stages},
                next_step="Inspect the box sketch and extrusion before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": box_base_snapshot.__dict__, "role": "box_base"})

        # --- box cavity cut ---
        cavity_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Box Cavity Sketch", offset_cm=spec.floor_thickness_cm),
        )
        cavity_sketch_token = cavity_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": cavity_sketch_token, "role": "cavity"})

        self._bridge_step(
            stage="draw_rectangle_at",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=spec.wall_thickness_cm,
                origin_y_cm=spec.wall_thickness_cm,
                width_cm=cavity_width_cm,
                height_cm=cavity_depth_cm,
                sketch_token=cavity_sketch_token,
            ),
        )
        stages.append({"stage": "draw_rectangle_at", "status": "completed", "role": "cavity"})

        cavity_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(cavity_sketch_token)["result"]["profiles"],
        )
        cavity_profile = self._select_profile_by_dimensions(
            cavity_profiles,
            expected_width_cm=cavity_width_cm,
            expected_height_cm=cavity_depth_cm,
            workflow_label="Box with lid",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(cavity_profiles), "role": "cavity"})

        box_body_after_cut = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=cavity_profile["token"],
                distance_cm=cavity_cut_depth_cm,
                body_name="cavity",
                operation="cut",
                target_body_token=box_body["token"],
            )["result"]["body"],
            partial_result={"box_body": box_body},
        )
        if box_body_after_cut["token"] != box_body["token"]:
            raise WorkflowFailure(
                "Box cavity cut returned an unexpected body token.",
                stage="extrude_profile",
                classification="verification_failed",
                partial_result={"box_body": box_body_after_cut, "expected_body": box_body, "stages": stages},
                next_step="Inspect cut-body targeting before retrying the box cavity cut.",
            )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": box_body_after_cut["token"], "role": "cavity_cut"})

        cavity_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"box_body": box_body_after_cut},
        )
        cavity_snapshot = VerificationSnapshot.from_scene(cavity_scene)
        if cavity_snapshot.body_count != 1:
            raise WorkflowFailure(
                "Box cavity cut produced unexpected body count.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": cavity_scene, "stages": stages},
                next_step="Inspect the cavity sketch and cut depth before retrying.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": cavity_snapshot.__dict__, "role": "cavity_cut"})

        # --- lid base (new_body in same design) ---
        lid_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Lid Outer Sketch"),
        )
        lid_sketch_token = lid_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": lid_sketch_token, "role": "lid_base"})

        self._bridge_step(
            stage="draw_rectangle_at",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=lid_origin_x_cm,
                origin_y_cm=lid_origin_y_cm,
                width_cm=lid_width_cm,
                height_cm=lid_depth_cm,
                sketch_token=lid_sketch_token,
            ),
        )
        stages.append({"stage": "draw_rectangle_at", "status": "completed", "role": "lid_base"})

        lid_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(lid_sketch_token)["result"]["profiles"],
        )
        lid_base_profile = self._select_profile_by_dimensions(
            lid_profiles,
            expected_width_cm=lid_width_cm,
            expected_height_cm=lid_depth_cm,
            workflow_label="Box with lid",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(lid_profiles), "role": "lid_base"})

        lid_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=lid_base_profile["token"],
                distance_cm=lid_total_height_cm,
                body_name="Lid Body",
                operation="new_body",
            )["result"]["body"],
            partial_result={"box_body": box_body_after_cut},
        )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": lid_body["token"], "role": "lid_base"})

        lid_base_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"box_body": box_body_after_cut, "lid_body": lid_body},
        )
        lid_base_snapshot = VerificationSnapshot.from_scene(lid_base_scene)
        if lid_base_snapshot.body_count != 2:
            raise WorkflowFailure(
                f"Lid base extrusion expected 2 bodies in design, got {lid_base_snapshot.body_count}.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": lid_base_scene, "stages": stages},
                next_step="Inspect the lid sketch and extrusion operation. Ensure new_body is used.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": lid_base_snapshot.__dict__, "role": "lid_base"})

        # --- lid rim cut ---
        rim_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Lid Rim Sketch"),
        )
        rim_sketch_token = rim_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": rim_sketch_token, "role": "rim"})

        self._bridge_step(
            stage="draw_rectangle_at",
            stages=stages,
            action=lambda: self.draw_rectangle_at(
                origin_x_cm=rim_origin_x_cm,
                origin_y_cm=rim_origin_y_cm,
                width_cm=rim_opening_width_cm,
                height_cm=rim_opening_depth_cm,
                sketch_token=rim_sketch_token,
            ),
        )
        stages.append({"stage": "draw_rectangle_at", "status": "completed", "role": "rim"})

        rim_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(rim_sketch_token)["result"]["profiles"],
        )
        rim_profile = self._select_profile_by_dimensions(
            rim_profiles,
            expected_width_cm=rim_opening_width_cm,
            expected_height_cm=rim_opening_depth_cm,
            workflow_label="Box with lid",
            stages=stages,
        )
        stages.append({"stage": "list_profiles", "status": "completed", "profile_count": len(rim_profiles), "role": "rim"})

        lid_body_after_rim = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=rim_profile["token"],
                distance_cm=spec.rim_depth_cm,
                body_name="rim",
                operation="cut",
                target_body_token=lid_body["token"],
            )["result"]["body"],
            partial_result={"box_body": box_body_after_cut, "lid_body": lid_body},
        )
        if lid_body_after_rim["token"] != lid_body["token"]:
            raise WorkflowFailure(
                "Lid rim cut returned an unexpected body token.",
                stage="extrude_profile",
                classification="verification_failed",
                partial_result={"lid_body": lid_body_after_rim, "expected_body": lid_body, "stages": stages},
                next_step="Inspect cut-body targeting before retrying the lid rim cut.",
            )
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": lid_body_after_rim["token"], "role": "rim_cut"})

        rim_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"box_body": box_body_after_cut, "lid_body": lid_body_after_rim},
        )
        rim_snapshot = VerificationSnapshot.from_scene(rim_scene)
        if rim_snapshot.body_count != 2:
            raise WorkflowFailure(
                f"Lid rim cut expected 2 bodies in design, got {rim_snapshot.body_count}.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": rim_scene, "stages": stages},
                next_step="Inspect the rim cut it may have cut the box body or merged bodies unexpectedly.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": rim_snapshot.__dict__, "role": "rim_cut"})

        # --- export both ---
        exported_box = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(box_body_after_cut["token"], spec.output_path_box)["result"],
            partial_result={"box_body": box_body_after_cut},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported_box["output_path"], "role": "box"})

        exported_lid = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(lid_body_after_rim["token"], spec.output_path_lid)["result"],
            partial_result={"lid_body": lid_body_after_rim},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported_lid["output_path"], "role": "lid"})

        return {
            "ok": True,
            "workflow": "create_box_with_lid",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "box_body": box_body_after_cut,
            "lid_body": lid_body_after_rim,
            "verification": {
                "body_count": rim_snapshot.body_count,
                "box_width_cm": spec.width_cm,
                "box_depth_cm": spec.depth_cm,
                "box_height_cm": spec.box_height_cm,
                "cavity_width_cm": cavity_width_cm,
                "cavity_depth_cm": cavity_depth_cm,
                "lid_width_cm": lid_width_cm,
                "lid_depth_cm": lid_depth_cm,
                "lid_total_height_cm": lid_total_height_cm,
                "rim_opening_width_cm": rim_opening_width_cm,
                "rim_opening_depth_cm": rim_opening_depth_cm,
                "rim_depth_cm": spec.rim_depth_cm,
                "wall_thickness_cm": spec.wall_thickness_cm,
                "clearance_cm": spec.clearance_cm,
            },
            "export_box": exported_box,
            "export_lid": exported_lid,
            "stages": stages,
            "retry_policy": "none",
        }

    def _create_project_box_with_standoffs_workflow(self, spec: CreateProjectBoxWithStandoffsInput) -> dict:
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("project_box_with_standoffs")
        inner_width_cm = spec.width_cm - (spec.wall_thickness_cm * 2.0)
        inner_depth_cm = spec.depth_cm - (spec.wall_thickness_cm * 2.0)
        inner_height_cm = spec.height_cm - spec.wall_thickness_cm

        # --- step 1: outer solid ---
        body, base_snapshot = self._create_base_plate_body(
            stages=stages,
            workflow_name="project_box_with_standoffs",
            design_name="Project Box With Standoffs Workflow",
            sketch_name=spec.sketch_name,
            body_name=spec.body_name,
            plane=spec.plane,
            width_cm=spec.width_cm,
            height_cm=spec.depth_cm,
            thickness_cm=spec.height_cm,
        )

        # --- step 2: shell (remove top face) ---
        shell = self._bridge_step(
            stage="apply_shell",
            stages=stages,
            action=lambda: self.apply_shell(
                body_token=body["token"],
                wall_thickness_cm=spec.wall_thickness_cm,
            )["result"]["shell"],
            partial_result={"body": body},
        )
        # Normalize: shell result uses body_token; add token alias for downstream consistency
        shell["token"] = shell["body_token"]
        self._verify_shell_result(
            shell=shell,
            stages=stages,
            expected_body=body,
            expected_wall_thickness_cm=spec.wall_thickness_cm,
            expected_inner_width_cm=inner_width_cm,
            expected_inner_depth_cm=inner_depth_cm,
            expected_inner_height_cm=inner_height_cm,
        )
        stages.append(
            {
                "stage": "apply_shell",
                "status": "completed",
                "wall_thickness_cm": spec.wall_thickness_cm,
                "removed_face_count": shell["removed_face_count"],
                "open_face": shell["open_face"],
            }
        )

        shell_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=shell,
            expected_dimensions={
                "width_cm": spec.width_cm,
                "height_cm": spec.depth_cm,
                "thickness_cm": spec.height_cm,
            },
            failure_message="Project box shell verification failed.",
            next_step="Inspect the top-face shell operation before retrying.",
            operation_label="shell",
        )

        # --- step 3: four corner standoffs ---
        # draw_rectangle draws from (0,0) to (width, depth), so the box center in sketch
        # coordinates is at (width_cm/2, depth_cm/2), NOT at the origin.
        # Standoff centers must be offset by this box center to land inside the inner cavity.
        # Standoffs are sketched on the base XY plane (Z=0, no offset) and extruded
        # with height = wall_thickness + standoff_height so they penetrate through
        # the floor material guaranteeing a real intersection for combine_bodies.
        standoff_total_height_cm = spec.wall_thickness_cm + spec.standoff_height_cm
        box_center_x = spec.width_cm / 2.0
        box_center_y = spec.depth_cm / 2.0
        half_inner_w = inner_width_cm / 2.0
        half_inner_d = inner_depth_cm / 2.0
        standoff_positions = [
            (box_center_x - half_inner_w + spec.standoff_inset_cm, box_center_y - half_inner_d + spec.standoff_inset_cm),
            (box_center_x + half_inner_w - spec.standoff_inset_cm, box_center_y - half_inner_d + spec.standoff_inset_cm),
            (box_center_x - half_inner_w + spec.standoff_inset_cm, box_center_y + half_inner_d - spec.standoff_inset_cm),
            (box_center_x + half_inner_w - spec.standoff_inset_cm, box_center_y + half_inner_d - spec.standoff_inset_cm),
        ]

        current_body = shell
        for i, (cx, cy) in enumerate(standoff_positions, start=1):
            standoff_body, current_body = self._create_standoff_and_combine(
                stages=stages,
                shell_body=current_body,
                standoff_index=i,
                center_x_cm=cx,
                center_y_cm=cy,
                diameter_cm=spec.standoff_diameter_cm,
                height_cm=standoff_total_height_cm,
                floor_offset_cm=None,
                expected_outer_dimensions={
                    "width_cm": spec.width_cm,
                    "height_cm": spec.depth_cm,
                    "thickness_cm": spec.height_cm,
                },
            )

        # --- step 4: export ---
        exported = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(current_body["token"], spec.output_path)["result"],
            partial_result={"body": current_body},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported["output_path"]})

        return {
            "ok": True,
            "workflow": "create_project_box_with_standoffs",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "body": current_body,
            "verification": {
                "body_count": 1,
                "expected_width_cm": spec.width_cm,
                "expected_depth_cm": spec.depth_cm,
                "expected_height_cm": spec.height_cm,
                "actual_width_cm": current_body["width_cm"],
                "actual_depth_cm": current_body["height_cm"],
                "actual_height_cm": current_body["thickness_cm"],
                "wall_thickness_cm": spec.wall_thickness_cm,
                "inner_width_cm": inner_width_cm,
                "inner_depth_cm": inner_depth_cm,
                "inner_height_cm": inner_height_cm,
                "standoff_count": 4,
                "standoff_diameter_cm": spec.standoff_diameter_cm,
                "standoff_height_cm": spec.standoff_height_cm,
                "standoff_inset_cm": spec.standoff_inset_cm,
            },
            "export": exported,
            "stages": stages,
            "retry_policy": "none",
        }

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _verify_shell_result(
        self,
        *,
        shell: dict,
        stages: list[dict],
        expected_body: dict,
        expected_wall_thickness_cm: float,
        expected_inner_width_cm: float,
        expected_inner_depth_cm: float,
        expected_inner_height_cm: float,
    ) -> None:
        """Verify shell operation produced expected results."""
        if not shell.get("shell_applied"):
            raise WorkflowFailure(
                "Shell operation did not complete.",
                stage="apply_shell",
                classification="verification_failed",
                partial_result={"shell": shell, "stages": stages},
                next_step="Inspect the top-face selection and shell feature before retrying.",
            )
        if shell.get("body_token") != expected_body["token"]:
            raise WorkflowFailure(
                "Shell result referenced an unexpected body.",
                stage="apply_shell",
                classification="verification_failed",
                partial_result={"shell": shell, "body": expected_body, "stages": stages},
                next_step="Inspect the shell target body selection before retrying.",
            )
        if shell.get("removed_face_count") != 1:
            raise WorkflowFailure(
                "Shell removed_face_count mismatch.",
                stage="apply_shell",
                classification="verification_failed",
                partial_result={"shell": shell, "stages": stages},
                next_step="Inspect the face removal list before retrying.",
            )
        if shell.get("open_face") != "top":
            raise WorkflowFailure(
                "Shell open_face mismatch.",
                stage="apply_shell",
                classification="verification_failed",
                partial_result={"shell": shell, "stages": stages},
                next_step="Inspect the shell face selection before retrying.",
            )

        expected_fields = {
            "width_cm": expected_body["width_cm"],
            "height_cm": expected_body["height_cm"],
            "thickness_cm": expected_body["thickness_cm"],
            "wall_thickness_cm": expected_wall_thickness_cm,
            "inner_width_cm": expected_inner_width_cm,
            "inner_depth_cm": expected_inner_depth_cm,
            "inner_height_cm": expected_inner_height_cm,
        }
        for field_name, expected_value in expected_fields.items():
            if not self._close(shell.get(field_name), expected_value):
                raise WorkflowFailure(
                    f"Shell {field_name} mismatch.",
                    stage="apply_shell",
                    classification="verification_failed",
                    partial_result={"shell": shell, "expected": expected_fields, "stages": stages},
                    next_step="Inspect shell thickness and inner cavity dimensions before retrying.",
                )

    def _create_standoff_and_combine(
        self,
        *,
        stages: list[dict],
        shell_body: dict,
        standoff_index: int,
        center_x_cm: float,
        center_y_cm: float,
        diameter_cm: float,
        height_cm: float,
        floor_offset_cm: float | None,
        expected_outer_dimensions: dict[str, float],
    ) -> tuple[dict, dict]:
        """Create one standoff post and combine it into the shell body.

        Returns (standoff_body, combined_body).
        """
        sketch_name = f"Standoff {standoff_index} Sketch"
        sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(
                plane="xy", name=sketch_name, offset_cm=floor_offset_cm,
            ),
        )
        sketch_token = sketch["result"]["sketch"]["token"]
        stages.append(
            {
                "stage": "create_sketch",
                "status": "completed",
                "sketch_token": sketch_token,
                "plane": "xy",
                "offset_cm": floor_offset_cm,
                "sketch_role": f"standoff_{standoff_index}",
            }
        )

        self._bridge_step(
            stage="draw_circle",
            stages=stages,
            action=lambda: self.draw_circle(
                center_x_cm=center_x_cm,
                center_y_cm=center_y_cm,
                radius_cm=diameter_cm / 2.0,
                sketch_token=sketch_token,
            ),
            partial_result={"sketch_token": sketch_token},
        )
        stages.append(
            {
                "stage": "draw_circle",
                "status": "completed",
                "profile_role": f"standoff_{standoff_index}",
                "diameter_cm": diameter_cm,
            }
        )

        profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token)["result"]["profiles"],
            partial_result={"sketch_token": sketch_token},
        )
        selected_profile = self._select_profile_by_dimensions(
            profiles,
            expected_width_cm=diameter_cm,
            expected_height_cm=diameter_cm,
            workflow_label="Project box with standoffs",
            stages=stages,
        )
        stages.append(
            {
                "stage": "list_profiles",
                "status": "completed",
                "profile_count": len(profiles),
                "profile_role": f"standoff_{standoff_index}",
            }
        )

        standoff_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(
                profile_token=selected_profile["token"],
                distance_cm=height_cm,
                body_name=f"Standoff {standoff_index}",
            )["result"]["body"],
            partial_result={"profile_token": selected_profile["token"]},
        )
        stages.append(
            {
                "stage": "extrude_profile",
                "status": "completed",
                "body_token": standoff_body["token"],
                "operation": "new_body",
                "profile_role": f"standoff_{standoff_index}",
            }
        )

        # Verify the standoff exists as a separate body before combining
        pre_combine_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"shell_body": shell_body, "standoff_body": standoff_body},
        )
        pre_combine_snapshot = VerificationSnapshot.from_scene(pre_combine_scene)
        if pre_combine_snapshot.body_count < 2:
            raise WorkflowFailure(
                f"Standoff {standoff_index} extrusion did not produce a separate body.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": pre_combine_scene, "stages": stages},
                next_step="Inspect the standoff sketch and extrusion before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": pre_combine_snapshot.__dict__,
                "operation": f"standoff_{standoff_index}_new_body",
            }
        )

        # Combine standoff into shell body
        combined_body = self._bridge_step(
            stage="combine_bodies",
            stages=stages,
            action=lambda: self.combine_bodies(
                target_body_token=shell_body["token"],
                tool_body_token=standoff_body["token"],
            )["result"]["body"],
            partial_result={"target_body": shell_body, "tool_body": standoff_body},
        )
        if combined_body["token"] != shell_body["token"]:
            raise WorkflowFailure(
                f"Standoff {standoff_index} combine returned an unexpected body token.",
                stage="combine_bodies",
                classification="verification_failed",
                partial_result={"combined_body": combined_body, "expected_body": shell_body, "stages": stages},
                next_step="Inspect target-body selection before retrying the body combine.",
            )
        stages.append(
            {
                "stage": "combine_bodies",
                "status": "completed",
                "body_token": combined_body["token"],
                "tool_body_token": standoff_body["token"],
                "standoff_index": standoff_index,
            }
        )

        # Verify after combine - outer dimensions should be unchanged
        combined_snapshot = self._verify_body_against_expected_dimensions(
            stages=stages,
            body=combined_body,
            expected_dimensions=expected_outer_dimensions,
            failure_message=f"Standoff {standoff_index} combine verification failed.",
            next_step="Inspect standoff placement and body combine before retrying.",
            operation_label=f"standoff_{standoff_index}_combine",
        )

        return standoff_body, combined_body

    # -------------------------------------------------------------------------
    # Abstract methods provided by other mixins
    # -------------------------------------------------------------------------

    def _bridge_step(self, *, stage, stages, action, partial_result=None, next_step=None):
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def _close(self, a: float, b: float) -> bool:
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def _create_base_plate_body(self, *, stages, workflow_name, design_name, sketch_name, body_name, plane, width_cm, height_cm, thickness_cm):
        """Provided by PlateWorkflowsMixin or CylinderWorkflowsMixin."""
        raise NotImplementedError

    def _run_rectangle_cut_stage(self, *, stages, workflow_name, sketch_name, origin_x_cm, origin_y_cm, width_cm, height_cm, cut_depth_cm, body, expected_dimensions, profile_role, operation_label, sketch_offset_cm=None):
        """Provided by PlateWorkflowsMixin or CylinderWorkflowsMixin."""
        raise NotImplementedError

    def _select_profile_by_dimensions(self, profiles, expected_width_cm, expected_height_cm, workflow_label, stages):
        """Provided by WorkflowMixin."""
        raise NotImplementedError

    def _verify_body_against_expected_dimensions(self, *, stages, body, expected_dimensions, failure_message, next_step, operation_label):
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

    def draw_circle(self, center_x_cm: float, center_y_cm: float, radius_cm: float, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def list_profiles(self, sketch_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, operation: str = "new_body", target_body_token: str | None = None) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def apply_shell(self, body_token: str, wall_thickness_cm: float) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def combine_bodies(self, target_body_token: str, tool_body_token: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def get_scene_info(self) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError

    def export_stl(self, body_token: str, output_path: str) -> dict:
        """Provided by PrimitiveMixin."""
        raise NotImplementedError
