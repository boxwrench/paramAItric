"""Geometric validation helpers.

Pure functions for spatial constraint checks used by schemas.py.
No Fusion API dependencies; all inputs are plain Python numbers.
"""
from __future__ import annotations

import math


def validate_hole_position(
    width_cm: float,
    height_cm: float,
    leg_thickness_cm: float,
    hole_radius_cm: float,
    center_x_cm: float,
    center_y_cm: float,
    label: str,
) -> None:
    """Raise ValueError if a hole does not fit inside one L-bracket leg."""
    if not (hole_radius_cm < center_x_cm < width_cm - hole_radius_cm):
        raise ValueError(f"{label}_center_x_cm must keep the hole inside the sketch bounds.")
    if not (hole_radius_cm < center_y_cm < height_cm - hole_radius_cm):
        raise ValueError(f"{label}_center_y_cm must keep the hole inside the sketch bounds.")
    in_vertical_leg = center_x_cm + hole_radius_cm <= leg_thickness_cm
    in_horizontal_leg = center_y_cm - hole_radius_cm <= leg_thickness_cm
    if not (in_vertical_leg or in_horizontal_leg):
        raise ValueError(f"{label} center must land fully inside one L-bracket leg.")


def validate_rectangular_hole_position(
    *,
    width_cm: float,
    height_cm: float,
    hole_radius_cm: float,
    center_x_cm: float,
    center_y_cm: float,
    label: str,
) -> None:
    """Raise ValueError if a hole does not fit inside a rectangular plate."""
    if not (hole_radius_cm < center_x_cm < width_cm - hole_radius_cm):
        raise ValueError(f"{label}_center_x_cm must keep the hole inside the sketch bounds.")
    if not (hole_radius_cm < center_y_cm < height_cm - hole_radius_cm):
        raise ValueError(f"{label}_center_y_cm must keep the hole inside the sketch bounds.")


def validate_slot_position(
    *,
    width_cm: float,
    height_cm: float,
    slot_length_cm: float,
    slot_width_cm: float,
    center_x_cm: float,
    center_y_cm: float,
) -> None:
    """Raise ValueError if a slot capsule does not fit inside the sketch bounds."""
    half_length_cm = slot_length_cm / 2.0
    half_width_cm = slot_width_cm / 2.0
    if not (half_length_cm < center_x_cm < width_cm - half_length_cm):
        raise ValueError("slot_center_x_cm must keep the slot inside the sketch bounds.")
    if not (half_width_cm < center_y_cm < height_cm - half_width_cm):
        raise ValueError("slot_center_y_cm must keep the slot inside the sketch bounds.")


def validate_slot_hole_clearance(
    *,
    hole_center_x_cm: float,
    hole_center_y_cm: float,
    hole_radius_cm: float,
    slot_center_x_cm: float,
    slot_center_y_cm: float,
    slot_length_cm: float,
    slot_width_cm: float,
    label: str,
) -> None:
    """Raise ValueError if a circular hole overlaps a slot capsule envelope."""
    slot_radius_cm = slot_width_cm / 2.0
    half_centerline_cm = (slot_length_cm - slot_width_cm) / 2.0
    dx_cm = abs(hole_center_x_cm - slot_center_x_cm)
    dy_cm = abs(hole_center_y_cm - slot_center_y_cm)
    nearest_dx_cm = max(dx_cm - half_centerline_cm, 0.0)
    distance_to_slot_capsule_cm = math.hypot(nearest_dx_cm, dy_cm)
    if distance_to_slot_capsule_cm <= hole_radius_cm + slot_radius_cm:
        raise ValueError(
            f"{label} overlaps the centered slot envelope; reduce slot size or increase edge offsets."
        )


def validate_rectangle_placement(
    *,
    outer_width_cm: float,
    outer_height_cm: float,
    inner_width_cm: float,
    inner_height_cm: float,
    origin_x_cm: float,
    origin_y_cm: float,
    label: str,
) -> None:
    """Raise ValueError if an inset rectangle does not fit inside the outer bounds."""
    if origin_x_cm <= 0 or origin_y_cm <= 0:
        raise ValueError(
            f"{label}_origin_x_cm and {label}_origin_y_cm must keep the rectangle inside the sketch bounds."
        )
    if origin_x_cm + inner_width_cm >= outer_width_cm:
        raise ValueError(f"{label}_origin_x_cm must keep the rectangle inside the sketch bounds.")
    if origin_y_cm + inner_height_cm >= outer_height_cm:
        raise ValueError(f"{label}_origin_y_cm must keep the rectangle inside the sketch bounds.")
