"""Adversarial input validation tests for mock_ops operations via the dispatcher.

Each test exercises one bad-input scenario and verifies that a clear exception
is raised rather than silently storing corrupt state.
"""
from __future__ import annotations

import math
import pytest

from fusion_addin.dispatcher import CommandDispatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fresh() -> CommandDispatcher:
    """Return a dispatcher backed by a clean mock registry."""
    return CommandDispatcher()


def _setup_sketch(d: CommandDispatcher) -> str:
    """Create a design + sketch and return the sketch token."""
    d.submit("new_design", {"name": "test"})
    return d.submit("create_sketch", {"plane": "xy", "name": "s"})["result"]["sketch"]["token"]


def _setup_profile(d: CommandDispatcher) -> tuple[str, str]:
    """Create a design + sketch + rectangle and return (sketch_token, profile_token)."""
    token = _setup_sketch(d)
    d.submit("draw_rectangle", {"sketch_token": token, "width_cm": 2.0, "height_cm": 1.0})
    profiles = d.submit("list_profiles", {"sketch_token": token})["result"]["profiles"]
    return token, profiles[0]["token"]


def _setup_body(d: CommandDispatcher) -> tuple[str, str]:
    """Create everything up to a body and return (sketch_token, body_token)."""
    sketch_token, profile_token = _setup_profile(d)
    body = d.submit("extrude_profile", {
        "profile_token": profile_token,
        "distance_cm": 0.5,
        "body_name": "b",
    })["result"]["body"]
    return sketch_token, body["token"]


# ---------------------------------------------------------------------------
# create_sketch
# ---------------------------------------------------------------------------

def test_create_sketch_missing_plane() -> None:
    d = fresh()
    with pytest.raises((KeyError, ValueError)):
        d.submit("create_sketch", {"name": "s"})


def test_create_sketch_missing_name() -> None:
    d = fresh()
    with pytest.raises((KeyError, ValueError)):
        d.submit("create_sketch", {"plane": "xy"})


def test_create_sketch_missing_both() -> None:
    d = fresh()
    with pytest.raises((KeyError, ValueError)):
        d.submit("create_sketch", {})


# ---------------------------------------------------------------------------
# draw_rectangle
# ---------------------------------------------------------------------------

def test_draw_rectangle_missing_width() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises((KeyError, ValueError)):
        d.submit("draw_rectangle", {"sketch_token": token, "height_cm": 1.0})


def test_draw_rectangle_missing_height() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises((KeyError, ValueError)):
        d.submit("draw_rectangle", {"sketch_token": token, "width_cm": 1.0})


def test_draw_rectangle_zero_width() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="width_cm"):
        d.submit("draw_rectangle", {"sketch_token": token, "width_cm": 0.0, "height_cm": 1.0})


def test_draw_rectangle_negative_width() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="width_cm"):
        d.submit("draw_rectangle", {"sketch_token": token, "width_cm": -1.0, "height_cm": 1.0})


def test_draw_rectangle_zero_height() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="height_cm"):
        d.submit("draw_rectangle", {"sketch_token": token, "width_cm": 1.0, "height_cm": 0.0})


def test_draw_rectangle_nan_width() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="width_cm"):
        d.submit("draw_rectangle", {"sketch_token": token, "width_cm": float("nan"), "height_cm": 1.0})


def test_draw_rectangle_inf_width() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="width_cm"):
        d.submit("draw_rectangle", {"sketch_token": token, "width_cm": float("inf"), "height_cm": 1.0})


def test_draw_rectangle_nan_height() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="height_cm"):
        d.submit("draw_rectangle", {"sketch_token": token, "width_cm": 1.0, "height_cm": float("nan")})


def test_draw_rectangle_string_width() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises((ValueError, TypeError)):
        d.submit("draw_rectangle", {"sketch_token": token, "width_cm": "wide", "height_cm": 1.0})


def test_draw_rectangle_nonexistent_sketch_token() -> None:
    d = fresh()
    d.submit("new_design", {"name": "test"})
    with pytest.raises(ValueError, match="sketch_token"):
        d.submit("draw_rectangle", {"sketch_token": "sketch-999", "width_cm": 1.0, "height_cm": 1.0})


def test_draw_rectangle_empty_sketch_token() -> None:
    d = fresh()
    d.submit("new_design", {"name": "test"})
    with pytest.raises(ValueError, match="sketch_token"):
        d.submit("draw_rectangle", {"sketch_token": "", "width_cm": 1.0, "height_cm": 1.0})


def test_draw_rectangle_large_values_succeed() -> None:
    """1e6 is unusual but the mock has no physical limits; it should not crash."""
    d = fresh()
    token = _setup_sketch(d)
    result = d.submit("draw_rectangle", {"sketch_token": token, "width_cm": 1e6, "height_cm": 1e6})
    assert result["ok"] is True


# ---------------------------------------------------------------------------
# draw_l_bracket_profile
# ---------------------------------------------------------------------------

def test_draw_l_bracket_zero_width() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="width_cm"):
        d.submit("draw_l_bracket_profile", {
            "sketch_token": token, "width_cm": 0.0, "height_cm": 2.0, "leg_thickness_cm": 0.5,
        })


def test_draw_l_bracket_negative_height() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="height_cm"):
        d.submit("draw_l_bracket_profile", {
            "sketch_token": token, "width_cm": 4.0, "height_cm": -1.0, "leg_thickness_cm": 0.5,
        })


def test_draw_l_bracket_nan_leg() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="leg_thickness_cm"):
        d.submit("draw_l_bracket_profile", {
            "sketch_token": token, "width_cm": 4.0, "height_cm": 2.0,
            "leg_thickness_cm": float("nan"),
        })


def test_draw_l_bracket_inf_width() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="width_cm"):
        d.submit("draw_l_bracket_profile", {
            "sketch_token": token, "width_cm": float("inf"), "height_cm": 2.0,
            "leg_thickness_cm": 0.5,
        })


def test_draw_l_bracket_leg_too_large() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="leg_thickness_cm"):
        d.submit("draw_l_bracket_profile", {
            "sketch_token": token, "width_cm": 4.0, "height_cm": 2.0,
            "leg_thickness_cm": 5.0,
        })


def test_draw_l_bracket_nonexistent_sketch() -> None:
    d = fresh()
    d.submit("new_design", {"name": "test"})
    with pytest.raises(ValueError, match="sketch_token"):
        d.submit("draw_l_bracket_profile", {
            "sketch_token": "sketch-999", "width_cm": 4.0, "height_cm": 2.0,
            "leg_thickness_cm": 0.5,
        })


def test_draw_l_bracket_missing_leg_thickness() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises((KeyError, ValueError)):
        d.submit("draw_l_bracket_profile", {"sketch_token": token, "width_cm": 4.0, "height_cm": 2.0})


# ---------------------------------------------------------------------------
# draw_circle
# ---------------------------------------------------------------------------

def test_draw_circle_zero_radius() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="radius_cm"):
        d.submit("draw_circle", {"sketch_token": token, "center_x_cm": 0.5, "center_y_cm": 0.5, "radius_cm": 0.0})


def test_draw_circle_negative_radius() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="radius_cm"):
        d.submit("draw_circle", {"sketch_token": token, "center_x_cm": 0.5, "center_y_cm": 0.5, "radius_cm": -1.0})


def test_draw_circle_nan_radius() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="radius_cm"):
        d.submit("draw_circle", {"sketch_token": token, "center_x_cm": 0.5, "center_y_cm": 0.5, "radius_cm": float("nan")})


def test_draw_circle_inf_radius() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError, match="radius_cm"):
        d.submit("draw_circle", {"sketch_token": token, "center_x_cm": 0.5, "center_y_cm": 0.5, "radius_cm": float("inf")})


def test_draw_circle_nan_center() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError):
        d.submit("draw_circle", {"sketch_token": token, "center_x_cm": float("nan"), "center_y_cm": 0.5, "radius_cm": 0.2})


def test_draw_circle_inf_center() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises(ValueError):
        d.submit("draw_circle", {"sketch_token": token, "center_x_cm": float("inf"), "center_y_cm": 0.5, "radius_cm": 0.2})


def test_draw_circle_missing_radius() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises((KeyError, ValueError)):
        d.submit("draw_circle", {"sketch_token": token, "center_x_cm": 0.5, "center_y_cm": 0.5})


def test_draw_circle_nonexistent_sketch() -> None:
    d = fresh()
    d.submit("new_design", {"name": "test"})
    with pytest.raises(ValueError, match="sketch_token"):
        d.submit("draw_circle", {"sketch_token": "sketch-999", "center_x_cm": 0.5, "center_y_cm": 0.5, "radius_cm": 0.2})


def test_draw_circle_string_radius() -> None:
    d = fresh()
    token = _setup_sketch(d)
    with pytest.raises((ValueError, TypeError)):
        d.submit("draw_circle", {"sketch_token": token, "center_x_cm": 0.5, "center_y_cm": 0.5, "radius_cm": "big"})


# ---------------------------------------------------------------------------
# extrude_profile
# ---------------------------------------------------------------------------

def test_extrude_zero_distance() -> None:
    d = fresh()
    _, profile_token = _setup_profile(d)
    with pytest.raises(ValueError, match="distance_cm"):
        d.submit("extrude_profile", {"profile_token": profile_token, "distance_cm": 0.0, "body_name": "b"})


def test_extrude_negative_distance() -> None:
    d = fresh()
    _, profile_token = _setup_profile(d)
    with pytest.raises(ValueError, match="distance_cm"):
        d.submit("extrude_profile", {"profile_token": profile_token, "distance_cm": -1.0, "body_name": "b"})


def test_extrude_nan_distance() -> None:
    d = fresh()
    _, profile_token = _setup_profile(d)
    with pytest.raises(ValueError, match="distance_cm"):
        d.submit("extrude_profile", {"profile_token": profile_token, "distance_cm": float("nan"), "body_name": "b"})


def test_extrude_inf_distance() -> None:
    d = fresh()
    _, profile_token = _setup_profile(d)
    with pytest.raises(ValueError, match="distance_cm"):
        d.submit("extrude_profile", {"profile_token": profile_token, "distance_cm": float("inf"), "body_name": "b"})


def test_extrude_malformed_profile_token() -> None:
    d = fresh()
    _setup_sketch(d)
    with pytest.raises(ValueError, match="profile_token"):
        d.submit("extrude_profile", {"profile_token": "not-a-token", "distance_cm": 1.0, "body_name": "b"})


def test_extrude_profile_token_wrong_separator() -> None:
    d = fresh()
    _setup_sketch(d)
    with pytest.raises(ValueError, match="profile_token"):
        d.submit("extrude_profile", {"profile_token": "sketch-1|profile|0", "distance_cm": 1.0, "body_name": "b"})


def test_extrude_unknown_profile_token() -> None:
    d = fresh()
    _setup_profile(d)
    with pytest.raises(ValueError, match="profile_token"):
        d.submit("extrude_profile", {"profile_token": "profile-999", "distance_cm": 1.0, "body_name": "b"})


def test_extrude_nonexistent_profile_index() -> None:
    d = fresh()
    _, profile_token = _setup_profile(d)
    d.submit("new_design", {"name": "reset"})
    with pytest.raises(ValueError, match="profile_token"):
        d.submit("extrude_profile", {"profile_token": profile_token, "distance_cm": 1.0, "body_name": "b"})


def test_extrude_missing_profile_token() -> None:
    d = fresh()
    with pytest.raises((KeyError, ValueError)):
        d.submit("extrude_profile", {"distance_cm": 1.0, "body_name": "b"})


def test_extrude_missing_distance() -> None:
    d = fresh()
    _, profile_token = _setup_profile(d)
    with pytest.raises((KeyError, ValueError)):
        d.submit("extrude_profile", {"profile_token": profile_token, "body_name": "b"})


# ---------------------------------------------------------------------------
# export_stl
# ---------------------------------------------------------------------------

def test_export_nonexistent_body_token(tmp_path) -> None:
    d = fresh()
    d.submit("new_design", {"name": "test"})
    with pytest.raises(ValueError, match="body"):
        d.submit("export_stl", {"body_token": "body-999", "output_path": str(tmp_path / "out.stl")})


def test_export_missing_body_token(tmp_path) -> None:
    d = fresh()
    with pytest.raises((KeyError, ValueError)):
        d.submit("export_stl", {"output_path": str(tmp_path / "out.stl")})


def test_export_empty_body_token(tmp_path) -> None:
    d = fresh()
    d.submit("new_design", {"name": "test"})
    with pytest.raises(ValueError, match="body"):
        d.submit("export_stl", {"body_token": "", "output_path": str(tmp_path / "out.stl")})


def test_export_missing_output_path() -> None:
    d = fresh()
    _, body_token = _setup_body(d)
    with pytest.raises((KeyError, ValueError)):
        d.submit("export_stl", {"body_token": body_token})
