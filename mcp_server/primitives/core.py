"""Low-level CAD primitive operations for ParamAItric.

These are thin wrappers around the Fusion bridge that provide basic
CAD operations: sketching, extruding, revolving, filleting, etc.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class PrimitiveMixin:
    """Mixin providing low-level CAD primitive operations.

    These methods map 1:1 to Fusion operations and form the building
    blocks for higher-level workflows.
    """

    # -------------------------------------------------------------------------
    # Server status and lifecycle
    # -------------------------------------------------------------------------

    def health(self) -> dict:
        """Check that the Fusion 360 bridge is reachable."""
        return self.bridge_client.health()

    def get_workflow_catalog(self) -> list[dict]:
        """Return the list of workflows registered in the Fusion add-in."""
        return self.bridge_client.workflow_catalog()

    def new_design(self, name: str = "ParamAItric Design") -> dict:
        """Create a new design, clearing any existing geometry."""
        return self._send("new_design", {"name": name})

    # -------------------------------------------------------------------------
    # Sketching primitives
    # -------------------------------------------------------------------------

    def create_sketch(
        self,
        plane: str,
        name: str,
        offset_cm: float | None = None
    ) -> dict:
        """Create a new sketch on the specified plane.

        Args:
            plane: One of "xy", "xz", "yz" or a face token.
            name: Human-readable name for the sketch.
            offset_cm: Optional offset from the plane in cm.
        """
        arguments = {"plane": plane, "name": name}
        if offset_cm is not None:
            arguments["offset_cm"] = offset_cm
        return self._send("create_sketch", arguments)

    def draw_rectangle(
        self,
        width_cm: float,
        height_cm: float,
        sketch_token: str | None = None
    ) -> dict:
        """Draw a rectangle from origin (0,0) to (width, height).

        Args:
            width_cm: Rectangle width in centimeters.
            height_cm: Rectangle height in centimeters.
            sketch_token: Optional sketch to draw in (uses active if None).
        """
        arguments = {"width_cm": width_cm, "height_cm": height_cm}
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_rectangle", arguments)

    def draw_rectangle_at(
        self,
        origin_x_cm: float,
        origin_y_cm: float,
        width_cm: float,
        height_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        """Draw a rectangle at a specific origin point.

        Args:
            origin_x_cm: X coordinate of rectangle origin.
            origin_y_cm: Y coordinate of rectangle origin.
            width_cm: Rectangle width in centimeters.
            height_cm: Rectangle height in centimeters.
            sketch_token: Optional sketch to draw in.
        """
        arguments = {
            "origin_x_cm": origin_x_cm,
            "origin_y_cm": origin_y_cm,
            "width_cm": width_cm,
            "height_cm": height_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_rectangle_at", arguments)

    def draw_l_bracket_profile(
        self,
        width_cm: float,
        height_cm: float,
        leg_thickness_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        """Draw an L-shaped bracket profile.

        Args:
            width_cm: Total width of the L-bracket.
            height_cm: Total height of the L-bracket.
            leg_thickness_cm: Thickness of each leg.
            sketch_token: Optional sketch to draw in.
        """
        arguments = {
            "width_cm": width_cm,
            "height_cm": height_cm,
            "leg_thickness_cm": leg_thickness_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_l_bracket_profile", arguments)

    def draw_circle(
        self,
        center_x_cm: float,
        center_y_cm: float,
        radius_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        """Draw a circle at the specified center.

        Args:
            center_x_cm: X coordinate of circle center.
            center_y_cm: Y coordinate of circle center.
            radius_cm: Circle radius in centimeters.
            sketch_token: Optional sketch to draw in.
        """
        arguments = {
            "center_x_cm": center_x_cm,
            "center_y_cm": center_y_cm,
            "radius_cm": radius_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_circle", arguments)

    def draw_revolve_profile(
        self,
        base_diameter_cm: float,
        top_diameter_cm: float,
        height_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        """Draw a tapered profile suitable for revolving.

        Creates a side profile that when revolved around Y axis produces
        a tapered cylinder (frustum).

        Args:
            base_diameter_cm: Diameter at the base.
            top_diameter_cm: Diameter at the top.
            height_cm: Total height.
            sketch_token: Optional sketch to draw in.
        """
        arguments = {
            "base_diameter_cm": base_diameter_cm,
            "top_diameter_cm": top_diameter_cm,
            "height_cm": height_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_revolve_profile", arguments)

    def draw_slot(
        self,
        center_x_cm: float,
        center_y_cm: float,
        length_cm: float,
        width_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        """Draw a slot (rounded rectangle) centered at the given point.

        Args:
            center_x_cm: X coordinate of slot center.
            center_y_cm: Y coordinate of slot center.
            length_cm: Total length of the slot.
            width_cm: Width of the slot (diameter of end caps).
            sketch_token: Optional sketch to draw in.
        """
        arguments = {
            "center_x_cm": center_x_cm,
            "center_y_cm": center_y_cm,
            "length_cm": length_cm,
            "width_cm": width_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_slot", arguments)

    def draw_triangle(
        self,
        x1_cm: float,
        y1_cm: float,
        x2_cm: float,
        y2_cm: float,
        x3_cm: float,
        y3_cm: float,
        sketch_token: str | None = None,
    ) -> dict:
        """Draw a triangle with vertices at the three specified points.

        Args:
            x1_cm, y1_cm: First vertex coordinates.
            x2_cm, y2_cm: Second vertex coordinates.
            x3_cm, y3_cm: Third vertex coordinates.
            sketch_token: Optional sketch to draw in.
        """
        arguments = {
            "x1_cm": x1_cm,
            "y1_cm": y1_cm,
            "x2_cm": x2_cm,
            "y2_cm": y2_cm,
            "x3_cm": x3_cm,
            "y3_cm": y3_cm,
        }
        if sketch_token:
            arguments["sketch_token"] = sketch_token
        return self._send("draw_triangle", arguments)

    def list_profiles(self, sketch_token: str) -> dict:
        """List all profiles (closed loops) in a sketch.

        Args:
            sketch_token: Token of the sketch to inspect.

        Returns:
            Dict containing list of profiles with their tokens and dimensions.
        """
        return self._send("list_profiles", {"sketch_token": sketch_token})

    # -------------------------------------------------------------------------
    # 3D modeling primitives
    # -------------------------------------------------------------------------

    def extrude_profile(
        self,
        profile_token: str,
        distance_cm: float,
        body_name: str,
        operation: str = "new_body",
        target_body_token: str | None = None,
        symmetric: bool = False,
    ) -> dict:
        """Extrude a sketch profile to create or modify a body.

        Args:
            profile_token: Token of the profile to extrude.
            distance_cm: Extrusion distance in centimeters.
            body_name: Name for the resulting body.
            operation: Either "new_body" or "cut".
            target_body_token: Required when operation is "cut".
            symmetric: If True, extrude symmetrically in both directions.
        """
        arguments = {
            "profile_token": profile_token,
            "distance_cm": distance_cm,
            "body_name": body_name,
            "operation": operation,
            "symmetric": symmetric,
        }
        if target_body_token:
            arguments["target_body_token"] = target_body_token
        return self._send("extrude_profile", arguments)

    def revolve_profile(
        self,
        profile_token: str,
        body_name: str,
        axis: str = "y",
        angle_deg: float = 360.0,
    ) -> dict:
        """Revolve a profile around an axis to create a body.

        Args:
            profile_token: Token of the profile to revolve.
            body_name: Name for the resulting body.
            axis: Axis to revolve around ("x", "y", or "z").
            angle_deg: Revolution angle in degrees (default 360 for full revolve).
        """
        return self._send(
            "revolve_profile",
            {
                "profile_token": profile_token,
                "body_name": body_name,
                "axis": axis,
                "angle_deg": angle_deg,
            },
        )

    # -------------------------------------------------------------------------
    # Body inspection primitives
    # -------------------------------------------------------------------------

    def get_scene_info(self) -> dict:
        """Get information about the current design scene.

        Returns:
            Dict containing body count, total volume, and other scene metadata.
        """
        return self._send("get_scene_info", {})

    def list_design_bodies(self, payload: dict | None = None) -> dict:
        """List all bodies in the current design.

        Args:
            payload: Optional filter parameters (currently unused).
        """
        _ = payload
        return self._send("list_design_bodies", {})

    def get_body_info(self, payload: dict) -> dict:
        """Get detailed information about a specific body.

        Args:
            payload: Dict containing "body_token" key.
        """
        body_token = payload.get("body_token")
        if not body_token or not isinstance(body_token, str):
            raise ValueError("body_token must be a non-empty string.")
        return self._send("get_body_info", {"body_token": body_token})

    def get_body_faces(self, payload: dict) -> dict:
        """Get all faces of a specific body.

        Args:
            payload: Dict containing "body_token" key.
        """
        body_token = payload.get("body_token")
        if not body_token or not isinstance(body_token, str):
            raise ValueError("body_token must be a non-empty string.")
        return self._send("get_body_faces", {"body_token": body_token})

    def get_body_edges(self, payload: dict) -> dict:
        """Get all edges of a specific body.

        Args:
            payload: Dict containing "body_token" key.
        """
        body_token = payload.get("body_token")
        if not body_token or not isinstance(body_token, str):
            raise ValueError("body_token must be a non-empty string.")
        return self._send("get_body_edges", {"body_token": body_token})

    def find_face(self, payload: dict) -> dict:
        """Find a specific face on a body using a semantic selector.

        Args:
            payload: Dict containing:
                - "body_token": Token of the body to search.
                - "selector": One of "top", "bottom", "left", "right", "front", "back".

        Returns:
            Dict with the selected face token and information.
        """
        body_token = payload.get("body_token")
        selector = payload.get("selector")
        if not body_token:
            raise ValueError("body_token is required.")
        if selector not in {"top", "bottom", "left", "right", "front", "back"}:
            raise ValueError("selector must be one of: top, bottom, left, right, front, back.")

        faces_res = self.get_body_faces({"body_token": body_token})
        faces = faces_res.get("result", {}).get("body_faces", [])
        if not faces:
            raise ValueError(f"Body {body_token} has no faces.")

        # Define sorting logic for axis-aligned extremes
        def get_face_val(face: dict, sel: str) -> float:
            bb = face.get("bounding_box", {})
            if sel == "top":
                return bb.get("max_z", 0)
            if sel == "bottom":
                return -bb.get("min_z", 0)
            if sel == "left":
                return -bb.get("min_x", 0)
            if sel == "right":
                return bb.get("max_x", 0)
            if sel == "front":
                return -bb.get("min_y", 0)
            if sel == "back":
                return bb.get("max_y", 0)
            return 0

        selected_face = max(faces, key=lambda f: get_face_val(f, selector))

        return {
            "ok": True,
            "face_token": selected_face["token"],
            "selector": selector,
            "face_info": selected_face,
        }

    # -------------------------------------------------------------------------
    # Body modification primitives
    # -------------------------------------------------------------------------

    def export_stl(self, body_token: str, output_path: str) -> dict:
        """Export a body as an STL file.

        Args:
            body_token: Token of the body to export.
            output_path: Destination path for the STL file.
        """
        return self._send("export_stl", {"body_token": body_token, "output_path": output_path})

    def apply_fillet(self, body_token: str, radius_cm: float) -> dict:
        """Apply fillets to edges of a body.

        Args:
            body_token: Token of the body to modify.
            radius_cm: Fillet radius in centimeters.
        """
        return self._send("apply_fillet", {"body_token": body_token, "radius_cm": radius_cm})

    def apply_chamfer(
        self,
        body_token: str,
        distance_cm: float,
        edge_selection: str | None = None
    ) -> dict:
        """Apply chamfers to edges of a body.

        Args:
            body_token: Token of the body to modify.
            distance_cm: Chamfer distance in centimeters.
            edge_selection: Optional selector for which edges (e.g., "interior_bracket").
        """
        arguments = {"body_token": body_token, "distance_cm": distance_cm}
        if edge_selection is not None:
            arguments["edge_selection"] = edge_selection
        return self._send("apply_chamfer", arguments)

    def apply_shell(self, body_token: str, wall_thickness_cm: float) -> dict:
        """Shell a body, removing a face and creating a hollow shell.

        Args:
            body_token: Token of the body to shell.
            wall_thickness_cm: Thickness of the resulting walls.
        """
        return self._send("apply_shell", {"body_token": body_token, "wall_thickness_cm": wall_thickness_cm})

    def combine_bodies(self, target_body_token: str, tool_body_token: str) -> dict:
        """Combine two bodies using a boolean union operation.

        Args:
            target_body_token: The body to keep (target of the operation).
            tool_body_token: The body to merge into the target (will be deleted).
        """
        return self._send(
            "combine_bodies",
            {"target_body_token": target_body_token, "tool_body_token": tool_body_token},
        )

    def convert_bodies_to_components(self, payload: dict) -> dict:
        """Convert bodies to Fusion 360 components.

        Args:
            payload: Dict containing:
                - "body_tokens": List of body tokens to convert.
                - "component_names": Optional list of names for the components.
        """
        body_tokens = payload.get("body_tokens")
        if not isinstance(body_tokens, list) or not body_tokens:
            raise ValueError("body_tokens must be a non-empty list of strings.")
        if not all(isinstance(t, str) and t for t in body_tokens):
            raise ValueError("All body_tokens entries must be non-empty strings.")
        args: dict = {"body_tokens": body_tokens}
        component_names = payload.get("component_names")
        if component_names is not None:
            if not isinstance(component_names, list):
                raise ValueError("component_names must be a list.")
            args["component_names"] = component_names
        return self._send("convert_bodies_to_components", args)
