"""Chamfer contract tests."""
from __future__ import annotations

import pytest

from fusion_addin.dispatcher import CommandDispatcher
from fusion_addin.workflows import WorkflowRuntime
from mcp_server.workflows import build_default_registry


def _setup_with_body(d: CommandDispatcher) -> str:
    d.submit("new_design", {"name": "Chamfer Test"})
    sketch_token = d.submit("create_sketch", {"plane": "xy", "name": "s"})["result"]["sketch"]["token"]
    d.submit(
        "draw_rectangle",
        {"sketch_token": sketch_token, "width_cm": 3.0, "height_cm": 2.0},
    )
    profiles = d.submit("list_profiles", {"sketch_token": sketch_token})["result"]["profiles"]
    body = d.submit(
        "extrude_profile",
        {
            "profile_token": profiles[0]["token"],
            "distance_cm": 0.5,
            "body_name": "Bracket",
        },
    )["result"]["body"]
    return body["token"]


def test_apply_chamfer_valid_body_and_distance() -> None:
    d = CommandDispatcher()
    body_token = _setup_with_body(d)
    result = d.submit("apply_chamfer", {"body_token": body_token, "distance_cm": 0.1})
    assert result["ok"] is True
    assert result["result"]["chamfer"]["chamfer_applied"] is True
    assert result["result"]["chamfer"]["body_token"] == body_token
    assert result["result"]["chamfer"]["distance_cm"] == pytest.approx(0.1)


def test_apply_chamfer_nonexistent_body_raises() -> None:
    d = CommandDispatcher()
    d.submit("new_design", {"name": "Empty"})
    with pytest.raises(ValueError, match="does not exist"):
        d.submit("apply_chamfer", {"body_token": "body-999", "distance_cm": 0.1})


def test_apply_chamfer_missing_body_token_raises() -> None:
    d = CommandDispatcher()
    d.submit("new_design", {"name": "Empty"})
    with pytest.raises((ValueError, KeyError)):
        d.submit("apply_chamfer", {"distance_cm": 0.1})


def test_apply_chamfer_zero_distance_raises() -> None:
    d = CommandDispatcher()
    body_token = _setup_with_body(d)
    with pytest.raises(ValueError, match="finite positive"):
        d.submit("apply_chamfer", {"body_token": body_token, "distance_cm": 0.0})


def test_apply_chamfer_negative_distance_raises() -> None:
    d = CommandDispatcher()
    body_token = _setup_with_body(d)
    with pytest.raises(ValueError, match="finite positive"):
        d.submit("apply_chamfer", {"body_token": body_token, "distance_cm": -0.5})


CHAMFERED_BRACKET_STAGES = (
    "new_design",
    "verify_clean_state",
    "create_sketch",
    "draw_l_bracket_profile",
    "list_profiles",
    "extrude_profile",
    "verify_geometry",
    "apply_chamfer",
    "verify_geometry",
    "export_stl",
)


def test_chamfered_bracket_registered_in_default_registry() -> None:
    registry = build_default_registry()
    workflow = registry.get("chamfered_bracket")
    assert workflow.name == "chamfered_bracket"
    assert "chamfer" in workflow.intent.lower()
    assert workflow.extension_of == ("bracket",)


def test_chamfered_bracket_stage_tuple_matches_expected() -> None:
    registry = build_default_registry()
    assert registry.get("chamfered_bracket").stages == CHAMFERED_BRACKET_STAGES


def test_chamfered_bracket_full_sequence_records_successfully() -> None:
    session = WorkflowRuntime(build_default_registry()).start("chamfered_bracket")
    for stage in CHAMFERED_BRACKET_STAGES:
        session.record(stage)
    assert list(session.completed_stages) == list(CHAMFERED_BRACKET_STAGES)


def test_chamfered_bracket_out_of_order_raises() -> None:
    session = WorkflowRuntime(build_default_registry()).start("chamfered_bracket")
    session.record("new_design")
    with pytest.raises(ValueError, match="out of order"):
        session.record("apply_chamfer")

