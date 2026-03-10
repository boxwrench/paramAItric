
    def _create_telescoping_containers_workflow(self, spec: CreateTelescopingContainersInput) -> dict:
        """Create three nesting rectangular containers with progressive clearances.
        
        All three containers are created in a single design as separate bodies.
        Phase 1: Outer container (largest)
        Phase 2: Middle container (fits inside outer)
        Phase 3: Inner container (fits inside middle)
        Phase 4: Export all three
        """
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get("telescoping_containers")
        
        # Calculate dimensions for all three containers
        middle_outer_width_cm = spec.outer_width_cm - (spec.middle_clearance_cm * 2.0)
        middle_outer_depth_cm = spec.outer_depth_cm - (spec.middle_clearance_cm * 2.0)
        middle_height_cm = spec.outer_height_cm - 0.5
        
        inner_outer_width_cm = middle_outer_width_cm - (spec.inner_clearance_cm * 2.0)
        inner_outer_depth_cm = middle_outer_depth_cm - (spec.inner_clearance_cm * 2.0)
        inner_height_cm = middle_height_cm - 0.5
        
        # --- Initialize design ---
        self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design("Telescoping Containers Workflow"))
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
        
        # --- Phase 1: Outer container ---
        # Create sketch
        outer_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Outer Container Sketch"),
        )
        outer_sketch_token = outer_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": outer_sketch_token, "plane": "xy"})
        
        # Draw rectangle
        self._bridge_step(
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(sketch_token=outer_sketch_token, width_cm=spec.outer_width_cm, height_cm=spec.outer_depth_cm),
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})
        
        # List profiles
        outer_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token=outer_sketch_token),
        )
        outer_profile_token = self._select_solid_profile(outer_profiles["result"]["profiles"])
        stages.append({"stage": "list_profiles", "status": "completed", "profile_token": outer_profile_token})
        
        # Extrude
        outer_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(profile_token=outer_profile_token, distance_cm=spec.outer_height_cm, operation="new_body")["result"]["body"],
        )
        outer_body["token"] = outer_body["body_token"]
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": outer_body["token"]})
        
        # Verify
        self._verify_single_body_creation(stages, outer_body, "outer_body")
        
        # Apply shell
        outer_shell = self._bridge_step(
            stage="apply_shell",
            stages=stages,
            action=lambda: self.apply_shell(
                body_token=outer_body["token"],
                wall_thickness_cm=spec.wall_thickness_cm,
            )["result"]["shell"],
            partial_result={"body": outer_body},
        )
        outer_shell["token"] = outer_shell["body_token"]
        stages.append({"stage": "apply_shell", "status": "completed", "container": "outer"})
        
        # --- Phase 2: Middle container ---
        middle_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Middle Container Sketch"),
        )
        middle_sketch_token = middle_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": middle_sketch_token, "plane": "xy"})
        
        self._bridge_step(
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(sketch_token=middle_sketch_token, width_cm=middle_outer_width_cm, height_cm=middle_outer_depth_cm),
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})
        
        middle_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token=middle_sketch_token),
        )
        middle_profile_token = self._select_solid_profile(middle_profiles["result"]["profiles"])
        stages.append({"stage": "list_profiles", "status": "completed", "profile_token": middle_profile_token})
        
        middle_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(profile_token=middle_profile_token, distance_cm=middle_height_cm, operation="new_body")["result"]["body"],
        )
        middle_body["token"] = middle_body["body_token"]
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": middle_body["token"]})
        
        # Verify we now have 2 bodies
        mid_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
        )
        mid_snapshot = VerificationSnapshot.from_scene(mid_scene)
        if mid_snapshot.body_count != 2:
            raise WorkflowFailure(
                f"Expected 2 bodies after middle container, got {mid_snapshot.body_count}.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": mid_scene, "stages": stages},
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "body_count": mid_snapshot.body_count})
        
        middle_shell = self._bridge_step(
            stage="apply_shell",
            stages=stages,
            action=lambda: self.apply_shell(
                body_token=middle_body["token"],
                wall_thickness_cm=spec.wall_thickness_cm,
            )["result"]["shell"],
            partial_result={"body": middle_body},
        )
        middle_shell["token"] = middle_shell["body_token"]
        stages.append({"stage": "apply_shell", "status": "completed", "container": "middle"})
        
        # --- Phase 3: Inner container ---
        inner_sketch = self._bridge_step(
            stage="create_sketch",
            stages=stages,
            action=lambda: self.create_sketch(plane="xy", name="Inner Container Sketch"),
        )
        inner_sketch_token = inner_sketch["result"]["sketch"]["token"]
        stages.append({"stage": "create_sketch", "status": "completed", "sketch_token": inner_sketch_token, "plane": "xy"})
        
        self._bridge_step(
            stage="draw_rectangle",
            stages=stages,
            action=lambda: self.draw_rectangle(sketch_token=inner_sketch_token, width_cm=inner_outer_width_cm, height_cm=inner_outer_depth_cm),
        )
        stages.append({"stage": "draw_rectangle", "status": "completed"})
        
        inner_profiles = self._bridge_step(
            stage="list_profiles",
            stages=stages,
            action=lambda: self.list_profiles(sketch_token=inner_sketch_token),
        )
        inner_profile_token = self._select_solid_profile(inner_profiles["result"]["profiles"])
        stages.append({"stage": "list_profiles", "status": "completed", "profile_token": inner_profile_token})
        
        inner_body = self._bridge_step(
            stage="extrude_profile",
            stages=stages,
            action=lambda: self.extrude_profile(profile_token=inner_profile_token, distance_cm=inner_height_cm, operation="new_body")["result"]["body"],
        )
        inner_body["token"] = inner_body["body_token"]
        stages.append({"stage": "extrude_profile", "status": "completed", "body_token": inner_body["token"]})
        
        inner_shell = self._bridge_step(
            stage="apply_shell",
            stages=stages,
            action=lambda: self.apply_shell(
                body_token=inner_body["token"],
                wall_thickness_cm=spec.wall_thickness_cm,
            )["result"]["shell"],
            partial_result={"body": inner_body},
        )
        inner_shell["token"] = inner_shell["body_token"]
        stages.append({"stage": "apply_shell", "status": "completed", "container": "inner"})
        
        # Verify all three bodies exist
        final_scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
        )
        final_snapshot = VerificationSnapshot.from_scene(final_scene)
        if final_snapshot.body_count != 3:
            raise WorkflowFailure(
                f"Expected 3 bodies (outer, middle, inner), got {final_snapshot.body_count}.",
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": final_scene, "stages": stages},
                next_step="Inspect container creation - some containers may have failed.",
            )
        stages.append({"stage": "verify_geometry", "status": "completed", "snapshot": final_snapshot.__dict__, "role": "final_count"})
        
        # --- Phase 4: Export all three ---
        exported_outer = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(outer_shell["token"], spec.output_path_outer)["result"],
            partial_result={"body": outer_shell},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported_outer["output_path"], "role": "outer"})
        
        exported_middle = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(middle_shell["token"], spec.output_path_middle)["result"],
            partial_result={"body": middle_shell},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported_middle["output_path"], "role": "middle"})
        
        exported_inner = self._bridge_step(
            stage="export_stl",
            stages=stages,
            action=lambda: self.export_stl(inner_shell["token"], spec.output_path_inner)["result"],
            partial_result={"body": inner_shell},
        )
        stages.append({"stage": "export_stl", "status": "completed", "output_path": exported_inner["output_path"], "role": "inner"})
        
        return {
            "ok": True,
            "workflow": "create_telescoping_containers",
            "workflow_basis": {
                "name": workflow_definition.name,
                "intent": workflow_definition.intent,
                "stages": list(workflow_definition.stages),
            },
            "outer_body": outer_shell,
            "middle_body": middle_shell,
            "inner_body": inner_shell,
            "verification": {
                "body_count": final_snapshot.body_count,
                "sketch_count": final_snapshot.sketch_count,
                "outer_width_cm": spec.outer_width_cm,
                "outer_depth_cm": spec.outer_depth_cm,
                "outer_height_cm": spec.outer_height_cm,
                "middle_outer_width_cm": middle_outer_width_cm,
                "middle_outer_depth_cm": middle_outer_depth_cm,
                "middle_height_cm": middle_height_cm,
                "inner_outer_width_cm": inner_outer_width_cm,
                "inner_outer_depth_cm": inner_outer_depth_cm,
                "inner_height_cm": inner_height_cm,
                "wall_thickness_cm": spec.wall_thickness_cm,
                "middle_clearance_cm": spec.middle_clearance_cm,
                "inner_clearance_cm": spec.inner_clearance_cm,
            },
            "export_outer": exported_outer,
            "export_middle": exported_middle,
            "export_inner": exported_inner,
            "stages": stages,
            "retry_policy": "none",
        }
