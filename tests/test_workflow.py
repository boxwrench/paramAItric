from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.bridge_client import BridgeClient
from mcp_server.errors import WorkflowFailure
from mcp_server.server import ParamAIToolServer


def test_create_spacer_workflow_exports_stl(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = tmp_path / "spacer.stl"

    result = server.create_spacer(
        {
            "width_cm": 2.0,
            "height_cm": 1.0,
            "thickness_cm": 0.5,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["verification"]["body_count"] == 1
    assert result["verification"]["actual_width_cm"] == 2.0
    assert result["retry_policy"] == "none"
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_spacer_stops_on_bad_input(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = tmp_path / "spacer.stl"

    try:
        server.create_spacer(
            {
                "width_cm": -2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(output_path),
            }
        )
    except ValueError as exc:
        assert "width_cm" in str(exc)
    else:
        raise AssertionError("Expected validation failure.")


def test_create_spacer_preserves_partial_result_on_verification_failure(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = tmp_path / "spacer.stl"

    original_extrude = server.extrude_profile

    def bad_extrude(profile_token: str, distance_cm: float, body_name: str) -> dict:
        result = original_extrude(profile_token, distance_cm, body_name)
        result["result"]["body"]["width_cm"] = 999.0
        return result

    server.extrude_profile = bad_extrude  # type: ignore[method-assign]

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_spacer(
            {
                "width_cm": 2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "verify_dimensions"
    assert failure.classification == "verification_failed"
    assert failure.partial_result["expected"]["width_cm"] == 2.0
