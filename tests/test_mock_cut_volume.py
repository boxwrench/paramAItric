"""Mock cut volume: cuts must actually remove volume.

The mock adapter reported ``width * height * thickness`` for every body -- a
bounding-box volume that ignored cuts entirely. A plate with a hole reported the
same volume as a solid plate, so a mock-mode volume check could not distinguish
"hole cut correctly" from "hole never cut at all".

Found by the G1 comparator on its first real run:
``plate_centered_hole_success`` reported 24.0 against a live Claude baseline of
23.60730091830126, which is 24.0 - pi * 0.5^2 * 0.5.
"""

from __future__ import annotations

import math

from fusion_addin.dispatcher import CommandDispatcher


def _plate(d: CommandDispatcher, width=8.0, height=6.0, thickness=0.5) -> dict:
    """Create a solid plate and return its body payload."""
    sketch = d.submit("create_sketch", {"plane": "xy", "name": "plate"})["result"]["sketch"]
    d.submit(
        "draw_rectangle",
        {"sketch_token": sketch["token"], "width_cm": width, "height_cm": height},
    )
    profiles = d.submit("list_profiles", {"sketch_token": sketch["token"]})["result"][
        "profiles"
    ]
    return d.submit(
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": thickness,
            "body_name": "Plate",
        },
    )["result"]["body"]


def _cut_circle(d: CommandDispatcher, radius_cm: float, depth_cm: float) -> None:
    """Cut a circular hole of ``radius_cm`` to ``depth_cm``."""
    sketch = d.submit("create_sketch", {"plane": "xy", "name": "hole"})["result"]["sketch"]
    d.submit(
        "draw_circle",
        {
            "sketch_token": sketch["token"],
            "center_x_cm": 0.0,
            "center_y_cm": 0.0,
            "radius_cm": radius_cm,
        },
    )
    profiles = d.submit("list_profiles", {"sketch_token": sketch["token"]})["result"][
        "profiles"
    ]
    d.submit(
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": depth_cm,
            "body_name": "hole",
            "operation": "cut",
        },
    )


def _cut_rectangle(d: CommandDispatcher, width_cm: float, height_cm: float, depth_cm: float) -> None:
    """Cut a rectangular pocket."""
    sketch = d.submit("create_sketch", {"plane": "xy", "name": "pocket"})["result"]["sketch"]
    d.submit(
        "draw_rectangle",
        {"sketch_token": sketch["token"], "width_cm": width_cm, "height_cm": height_cm},
    )
    profiles = d.submit("list_profiles", {"sketch_token": sketch["token"]})["result"][
        "profiles"
    ]
    d.submit(
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": depth_cm,
            "body_name": "pocket",
            "operation": "cut",
        },
    )


def _volume_via_list(d: CommandDispatcher, token: str) -> float:
    bodies = d.submit("list_design_bodies", {})["result"]["bodies"]
    return next(b["volume_cm3"] for b in bodies if b["body_token"] == token)


def _volume_via_info(d: CommandDispatcher, token: str) -> float:
    info = d.submit("get_body_info", {"body_token": token})["result"]["body_info"]
    return info["volume_cm3"]


class TestSolidBodyVolumeUnchanged:
    """The uncut case must keep behaving exactly as before."""

    def test_plate_volume_is_the_prism_volume(self) -> None:
        d = CommandDispatcher()
        body = _plate(d)

        assert _volume_via_list(d, body["token"]) == 8.0 * 6.0 * 0.5


class TestCircularCut:
    """A circular cut removes a cylinder."""

    def test_subtracts_the_cylinder_volume(self) -> None:
        """The exact case the comparator caught against the Claude baseline."""
        d = CommandDispatcher()
        body = _plate(d)

        _cut_circle(d, radius_cm=0.5, depth_cm=0.5)

        expected = 24.0 - math.pi * 0.5**2 * 0.5
        assert _volume_via_list(d, body["token"]) == pytest_approx(expected)

    def test_matches_the_live_claude_baseline_value(self) -> None:
        d = CommandDispatcher()
        body = _plate(d)

        _cut_circle(d, radius_cm=0.5, depth_cm=0.5)

        assert _volume_via_list(d, body["token"]) == pytest_approx(23.60730091830126)

    def test_a_bigger_hole_removes_more(self) -> None:
        small, large = CommandDispatcher(), CommandDispatcher()
        small_body, large_body = _plate(small), _plate(large)

        _cut_circle(small, radius_cm=0.25, depth_cm=0.5)
        _cut_circle(large, radius_cm=1.0, depth_cm=0.5)

        assert _volume_via_list(large, large_body["token"]) < _volume_via_list(
            small, small_body["token"]
        )


class TestRectangularCut:
    """A rectangular cut removes a box."""

    def test_subtracts_the_box_volume(self) -> None:
        d = CommandDispatcher()
        body = _plate(d)

        _cut_rectangle(d, width_cm=2.0, height_cm=1.0, depth_cm=0.5)

        assert _volume_via_list(d, body["token"]) == pytest_approx(24.0 - 2.0 * 1.0 * 0.5)


class TestCutDepth:
    """Depth is bounded by the body: a cut cannot remove what is not there."""

    def test_a_partial_depth_cut_removes_less(self) -> None:
        d = CommandDispatcher()
        body = _plate(d)

        _cut_circle(d, radius_cm=0.5, depth_cm=0.25)

        expected = 24.0 - math.pi * 0.5**2 * 0.25
        assert _volume_via_list(d, body["token"]) == pytest_approx(expected)

    def test_an_overdeep_cut_is_clamped_to_the_body(self) -> None:
        """Cutting 10 cm deep through a 0.5 cm plate removes 0.5 cm worth."""
        d = CommandDispatcher()
        body = _plate(d)

        _cut_circle(d, radius_cm=0.5, depth_cm=10.0)

        expected = 24.0 - math.pi * 0.5**2 * 0.5
        assert _volume_via_list(d, body["token"]) == pytest_approx(expected)

    def test_volume_never_goes_negative(self) -> None:
        """An absurdly large cut floors at zero rather than reporting nonsense."""
        d = CommandDispatcher()
        body = _plate(d)

        _cut_rectangle(d, width_cm=100.0, height_cm=100.0, depth_cm=10.0)

        assert _volume_via_list(d, body["token"]) >= 0.0


class TestMultipleCuts:
    """Removed volume accumulates across cuts."""

    def test_two_holes_remove_twice_as_much(self) -> None:
        d = CommandDispatcher()
        body = _plate(d)

        _cut_circle(d, radius_cm=0.5, depth_cm=0.5)
        _cut_circle(d, radius_cm=0.5, depth_cm=0.5)

        expected = 24.0 - 2 * math.pi * 0.5**2 * 0.5
        assert _volume_via_list(d, body["token"]) == pytest_approx(expected)


class TestAllReportingPathsAgree:
    """Three call sites computed volume; all three must tell the same story."""

    def test_list_and_info_agree_after_a_cut(self) -> None:
        d = CommandDispatcher()
        body = _plate(d)

        _cut_circle(d, radius_cm=0.5, depth_cm=0.5)

        assert _volume_via_list(d, body["token"]) == pytest_approx(
            _volume_via_info(d, body["token"])
        )


def pytest_approx(value: float, tol: float = 1e-9):
    """Local approx helper so the intent reads clearly at each call site."""
    import pytest

    return pytest.approx(value, abs=tol)
