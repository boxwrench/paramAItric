"""Tests for the backend-neutral operation vocabulary (mcp_server/operations.py)."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Increment 1 — ExpectedDelta (machine-checkable)
# ---------------------------------------------------------------------------


def test_expected_delta_passes_when_observation_matches() -> None:
    from mcp_server.operations import ExpectedDelta, VolumeDelta

    delta = ExpectedDelta(body_count_delta=1, volume=VolumeDelta.INCREASE)
    failures = delta.check(body_count_delta=1, volume=VolumeDelta.INCREASE, features=())
    assert failures == []


def test_expected_delta_flags_each_invariant_independently() -> None:
    from mcp_server.operations import ExpectedDelta, VolumeDelta

    delta = ExpectedDelta(
        body_count_delta=1,
        volume=VolumeDelta.INCREASE,
        features_present=("fillet",),
    )
    # Every invariant is violated: wrong body delta, wrong volume direction,
    # missing feature.
    failures = delta.check(
        body_count_delta=0, volume=VolumeDelta.DECREASE, features=()
    )
    assert len(failures) == 3


def test_expected_delta_feature_presence_is_subset_check() -> None:
    from mcp_server.operations import ExpectedDelta, VolumeDelta

    delta = ExpectedDelta(
        body_count_delta=0,
        volume=VolumeDelta.DECREASE,
        features_present=("hole",),
    )
    # Extra observed features are fine; the declared ones must all be present.
    assert delta.check(
        body_count_delta=0, volume=VolumeDelta.DECREASE, features=("hole", "chamfer")
    ) == []
    assert delta.check(
        body_count_delta=0, volume=VolumeDelta.DECREASE, features=("chamfer",)
    )


# ---------------------------------------------------------------------------
# Increment 2 — Operation, OperationMode, Target, Placement
# ---------------------------------------------------------------------------


def _new_body_op():
    from mcp_server.operations import (
        ExpectedDelta,
        Operation,
        OperationMode,
        Placement,
        Target,
        VolumeDelta,
    )

    return Operation(
        mode=OperationMode.NEW_BODY,
        target=Target(profile="rectangle", dimensions_cm={"width": 4.0, "height": 4.0}, extent_cm=1.0),
        placement=Placement(plane="xy"),
        expected_delta=ExpectedDelta(body_count_delta=1, volume=VolumeDelta.INCREASE),
    )


def test_operation_carries_the_four_attributes() -> None:
    from mcp_server.operations import OperationMode

    op = _new_body_op()
    assert op.mode is OperationMode.NEW_BODY
    assert op.target.profile == "rectangle"
    assert op.placement.plane == "xy"
    assert op.expected_delta.body_count_delta == 1


def test_operation_mode_covers_the_four_operations() -> None:
    from mcp_server.operations import OperationMode

    assert {m.value for m in OperationMode} == {"new_body", "cut", "add", "intersect"}


def test_placement_rejects_unknown_plane() -> None:
    from mcp_server.operations import Placement

    with pytest.raises(ValueError, match="plane"):
        Placement(plane="diagonal")


def test_target_rejects_unknown_profile() -> None:
    from mcp_server.operations import Target

    with pytest.raises(ValueError, match="profile"):
        Target(profile="hexagon", dimensions_cm={"width": 1.0}, extent_cm=1.0)


def test_target_rejects_nonpositive_dimensions() -> None:
    from mcp_server.operations import Target

    with pytest.raises(ValueError):
        Target(profile="rectangle", dimensions_cm={"width": 0.0, "height": 4.0}, extent_cm=1.0)
    with pytest.raises(ValueError):
        Target(profile="rectangle", dimensions_cm={"width": 4.0, "height": 4.0}, extent_cm=-1.0)


# ---------------------------------------------------------------------------
# Increment 3 — the spacer expresses itself and round-trips against a real run
# ---------------------------------------------------------------------------


def test_spacer_expresses_as_a_single_new_body_operation() -> None:
    from mcp_server.operations import OperationMode, VolumeDelta
    from mcp_server.schemas import CreateSpacerInput
    from mcp_server.workflows.plates import spacer_operations

    spec = CreateSpacerInput.from_payload(
        {"width_cm": 4.0, "height_cm": 3.0, "thickness_cm": 1.0, "output_path": "s.stl"}
    )
    ops = spacer_operations(spec)

    assert len(ops) == 1
    op = ops[0]
    assert op.mode is OperationMode.NEW_BODY
    assert op.placement.plane == "xy"
    assert op.target.dimensions_cm == {"width": 4.0, "height": 3.0}
    assert op.target.extent_cm == 1.0
    assert op.expected_delta.body_count_delta == 1
    assert op.expected_delta.volume is VolumeDelta.INCREASE


def test_spacer_declaration_round_trips_against_a_real_run(running_bridge, tmp_path) -> None:
    from mcp_server.bridge_client import BridgeClient
    from mcp_server.operations import VolumeDelta
    from mcp_server.schemas import CreateSpacerInput
    from mcp_server.server import ParamAIToolServer
    from mcp_server.workflows.plates import spacer_operations

    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    payload = {
        "width_cm": 4.0,
        "height_cm": 3.0,
        "thickness_cm": 1.0,
        "output_path": str(tmp_path / "spacer.stl"),
    }
    spec = CreateSpacerInput.from_payload(payload)
    op = spacer_operations(spec)[0]

    result = server.create_spacer(payload)

    # The spacer verifies a clean (0-body) start, so body_count is the delta.
    observed_body_count_delta = result["verification"]["body_count"]
    body = result["body"]
    observed_volume = body["width_cm"] * body["height_cm"] * body["thickness_cm"]
    observed = VolumeDelta.INCREASE if observed_volume > 0 else VolumeDelta.UNCHANGED

    # Declaration and reality agree on every invariant -> the round-trip holds.
    assert op.expected_delta.check(
        body_count_delta=observed_body_count_delta,
        volume=observed,
        features=(),
    ) == []


# ---------------------------------------------------------------------------
# Increment 4 — the vocabulary surface stays backend-neutral
# ---------------------------------------------------------------------------


def test_public_surface_has_no_backend_specific_terms() -> None:
    import dataclasses
    import enum

    import mcp_server.operations as ops

    # Terms that would mean a Fusion (or any single backend) concept leaked into
    # what is meant to be the neutral protocol vocabulary.
    forbidden = {"fusion", "adsk", "brep", "occurrence", "timeline", "token", "entity"}

    surface: list[str] = []
    for name in dir(ops):
        if name.startswith("_"):
            continue
        surface.append(name.lower())
        obj = getattr(ops, name)
        if isinstance(obj, type) and issubclass(obj, enum.Enum):
            surface.extend(str(member.value).lower() for member in obj)
        if dataclasses.is_dataclass(obj):
            surface.extend(f.name.lower() for f in dataclasses.fields(obj))

    blob = " ".join(surface)
    for term in forbidden:
        assert term not in blob, f"backend-specific term {term!r} leaked into the vocabulary"
