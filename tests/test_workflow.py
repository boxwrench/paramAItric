from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.bridge_client import BridgeCancelledError, BridgeClient, BridgeTimeoutError
from mcp_server.errors import WorkflowFailure
from mcp_server.server import ParamAIToolServer
from mcp_server.schemas import CommandEnvelope


class InterceptingBridgeClient:
    def __init__(self, base_url: str, interceptors: dict[str, object] | None = None) -> None:
        self._client = BridgeClient(base_url)
        self._interceptors = interceptors or {}
        self._call_counts: dict[str, int] = {}

    def health(self) -> dict:
        return self._client.health()

    def send(self, envelope: CommandEnvelope) -> dict:
        command = envelope.command
        self._call_counts[command] = self._call_counts.get(command, 0) + 1
        interceptor = self._interceptors.get(command)
        if interceptor is not None:
            return interceptor(
                envelope=envelope,
                client=self._client,
                call_count=self._call_counts[command],
            )
        return self._client.send(envelope)


def _raise_bridge_error(message: str):
    def _interceptor(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
        _ = (envelope, client, call_count)
        raise RuntimeError(message)

    return _interceptor


def _raise_bridge_timeout(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
    _ = (envelope, client, call_count)
    raise BridgeTimeoutError("Fusion bridge request timed out.")


def _raise_bridge_cancelled(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
    _ = (envelope, client, call_count)
    raise BridgeCancelledError("Fusion bridge request was cancelled.")


def _dirty_scene_once(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
    if call_count == 1:
        return {"result": {"design_name": "stale", "bodies": [{"token": "b1"}], "sketches": [], "exports": []}}
    return client.send(envelope)


def _corrupt_extrude_width(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
    _ = call_count
    result = client.send(envelope)
    return {
        **result,
        "result": {
            **result["result"],
            "body": {
                **result["result"]["body"],
                "width_cm": 999.0,
            },
        },
    }


def _get_square_socket_cut_width(stages: list[dict]) -> float:
    for stage in stages:
        if stage.get("stage") == "draw_rectangle_at" and stage.get("profile_role") == "square_socket":
            return float(stage["width_cm"])
    raise AssertionError("Expected square_socket draw_rectangle_at stage.")


def test_create_spacer_workflow_exports_stl(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_workflow_exports_stl.stl"

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
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_stops_on_bad_input.stl"

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
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "extrude_profile": _corrupt_extrude_width,
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_preserves_partial_result.stl"

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


def test_create_spacer_wraps_bridge_failure_in_workflow_failure(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "get_scene_info": _raise_bridge_error("Fusion bridge is not reachable."),
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_wraps_bridge_failure.stl"

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
    assert failure.stage == "verify_clean_state"
    assert failure.classification == "bridge_error"
    assert failure.partial_result["stages"] == [{"stage": "new_design", "status": "completed"}]
    assert "Fusion bridge is not reachable." in str(failure)


def test_create_cylinder_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_cylinder_workflow.stl"

    result = server.create_cylinder(
        {
            "diameter_cm": 2.0,
            "height_cm": 3.0,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_cylinder"
    assert result["workflow_basis"]["name"] == "cylinder"
    assert result["verification"]["actual_diameter_cm"] == 2.0
    assert result["verification"]["actual_secondary_diameter_cm"] == 2.0
    assert result["verification"]["actual_height_cm"] == 3.0
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_cylinder_preserves_partial_result_on_verification_failure(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "extrude_profile": _corrupt_extrude_width,
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_cylinder_preserves_partial_result.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_cylinder(
            {
                "diameter_cm": 2.0,
                "height_cm": 3.0,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "verify_dimensions"
    assert failure.classification == "verification_failed"
    assert failure.partial_result["expected"]["width_cm"] == 2.0


def test_create_tube_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_tube_workflow.stl"

    result = server.create_tube(
        {
            "outer_diameter_cm": 2.0,
            "inner_diameter_cm": 1.2,
            "height_cm": 3.0,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_tube"
    assert result["workflow_basis"]["name"] == "tube"
    assert result["verification"]["actual_outer_diameter_cm"] == 2.0
    assert result["verification"]["actual_secondary_outer_diameter_cm"] == 2.0
    assert result["verification"]["actual_height_cm"] == 3.0
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_revolve_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_revolve_workflow.stl"

    result = server.create_revolve(
        {
            "base_diameter_cm": 3.0,
            "top_diameter_cm": 2.0,
            "height_cm": 2.5,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_revolve"
    assert result["workflow_basis"]["name"] == "revolve"
    assert result["verification"]["actual_base_diameter_cm"] == 3.0
    assert result["verification"]["actual_top_diameter_cm"] == 2.0
    assert result["verification"]["actual_max_diameter_cm"] == 3.0
    assert result["verification"]["actual_secondary_max_diameter_cm"] == 3.0
    assert result["verification"]["actual_height_cm"] == 2.5
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_revolve_profile",
        "list_profiles",
        "revolve_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_revolve_accepts_live_half_profile_width(running_bridge) -> None:
    _, base_url = running_bridge

    def _radius_width_list_profiles(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
        result = client.send(envelope)
        if call_count != 1:
            return result
        profiles = result["result"]["profiles"]
        return {
            **result,
            "result": {
                "profiles": [
                    {**profile, "width_cm": 1.5}
                    for profile in profiles
                ]
            },
        }

    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"list_profiles": _radius_width_list_profiles},
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_revolve_half_profile_width.stl"

    result = server.create_revolve(
        {
            "base_diameter_cm": 3.0,
            "top_diameter_cm": 2.0,
            "height_cm": 2.5,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["verification"]["actual_base_diameter_cm"] == 3.0
    assert Path(result["export"]["output_path"]).exists()


def _corrupt_revolve_field(field_name: str, value: object):
    def _interceptor(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
        result = client.send(envelope)
        return {
            **result,
            "result": {
                "body": {
                    **result["result"]["body"],
                    field_name: value,
                },
            },
        }

    return _interceptor


def test_create_revolve_fails_when_revolve_result_is_invalid(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"revolve_profile": _corrupt_revolve_field("axis", "x")},
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_revolve_bad_result.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_revolve(
            {
                "base_diameter_cm": 3.0,
                "top_diameter_cm": 2.0,
                "height_cm": 2.5,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "revolve_profile"
    assert failure.classification == "verification_failed"


def test_create_tapered_knob_blank_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_tapered_knob_blank_workflow.stl"

    result = server.create_tapered_knob_blank(
        {
            "base_diameter_cm": 4.0,
            "top_diameter_cm": 2.5,
            "height_cm": 2.5,
            "stem_socket_diameter_cm": 1.0,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_tapered_knob_blank"
    assert result["workflow_basis"]["name"] == "tapered_knob_blank"
    assert result["verification"]["actual_base_diameter_cm"] == 4.0
    assert result["verification"]["actual_top_diameter_cm"] == 2.5
    assert result["verification"]["actual_max_diameter_cm"] == 4.0
    assert result["verification"]["actual_secondary_max_diameter_cm"] == 4.0
    assert result["verification"]["actual_height_cm"] == 2.5
    assert result["verification"]["stem_socket_diameter_cm"] == 1.0
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_revolve_profile",
        "list_profiles",
        "revolve_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_flanged_bushing_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_flanged_bushing_workflow.stl"

    result = server.create_flanged_bushing(
        {
            "shaft_outer_diameter_cm": 2.0,
            "shaft_length_cm": 3.0,
            "flange_outer_diameter_cm": 3.0,
            "flange_thickness_cm": 0.6,
            "bore_diameter_cm": 1.0,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_flanged_bushing"
    assert result["workflow_basis"]["name"] == "flanged_bushing"
    assert result["verification"]["actual_outer_diameter_cm"] == 3.0
    assert result["verification"]["actual_secondary_outer_diameter_cm"] == 3.0
    assert result["verification"]["actual_length_cm"] == 3.0
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_revolve_profile",
        "list_profiles",
        "revolve_profile",
        "verify_geometry",
        "create_sketch",
        "draw_revolve_profile",
        "list_profiles",
        "revolve_profile",
        "verify_geometry",
        "combine_bodies",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_pipe_clamp_half_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_pipe_clamp_half_workflow.stl"

    result = server.create_pipe_clamp_half(
        {
            "clamp_width_cm": 6.0,
            "clamp_length_cm": 8.0,
            "clamp_height_cm": 2.0,
            "pipe_outer_diameter_cm": 2.4,
            "bolt_hole_diameter_cm": 0.6,
            "bolt_hole_edge_offset_x_cm": 1.0,
            "bolt_hole_center_y_cm": 4.0,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_pipe_clamp_half"
    assert result["workflow_basis"]["name"] == "pipe_clamp_half"
    assert result["verification"]["actual_clamp_width_cm"] == 6.0
    assert result["verification"]["actual_clamp_length_cm"] == 8.0
    assert result["verification"]["actual_clamp_height_cm"] == 2.0
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_t_handle_with_square_socket_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_t_handle_with_square_socket_workflow.stl"

    result = server.create_t_handle_with_square_socket(
        {
            "tee_width_cm": 12.7,
            "tee_depth_cm": 5.08,
            "stem_length_cm": 5.08,
            "square_socket_width_cm": 1.905,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_t_handle_with_square_socket"
    assert result["workflow_basis"]["name"] == "t_handle_with_square_socket"
    assert result["verification"]["actual_width_cm"] == 12.7
    assert result["verification"]["actual_depth_cm"] == 5.08
    assert result["verification"]["actual_height_cm"] == 10.16
    assert result["verification"]["square_socket_width_cm"] == pytest.approx(1.905)
    assert result["verification"]["socket_clearance_per_side_cm"] == pytest.approx(0.0)
    assert result["verification"]["effective_square_socket_width_cm"] == pytest.approx(1.905)
    assert result["chamfer"]["edge_count"] == 4
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle_at",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "combine_bodies",
        "verify_geometry",
        "create_sketch",
        "draw_rectangle_at",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "apply_chamfer",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_t_handle_with_square_socket_replay_changes_only_socket_fit(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path_base = Path.cwd() / "manual_test_output" / "test_create_t_handle_with_square_socket_replay_base.stl"
    output_path_replay = Path.cwd() / "manual_test_output" / "test_create_t_handle_with_square_socket_replay_looser_socket.stl"

    base_payload = {
        "tee_width_cm": 12.7,
        "tee_depth_cm": 5.08,
        "stem_length_cm": 5.08,
        "square_socket_width_cm": 1.905,
        "output_path": str(output_path_base),
    }
    replay_clearance_per_side_cm = 0.05
    replay_payload = {
        **base_payload,
        "socket_clearance_per_side_cm": replay_clearance_per_side_cm,
        "output_path": str(output_path_replay),
    }

    base_result = server.create_t_handle_with_square_socket(base_payload)
    replay_result = server.create_t_handle_with_square_socket(replay_payload)

    assert base_result["ok"] is True
    assert replay_result["ok"] is True
    assert Path(base_result["export"]["output_path"]).exists()
    assert Path(replay_result["export"]["output_path"]).exists()

    # Replay should preserve the outer envelope while widening only the socket cut.
    assert replay_result["verification"]["actual_width_cm"] == pytest.approx(base_result["verification"]["actual_width_cm"])
    assert replay_result["verification"]["actual_depth_cm"] == pytest.approx(base_result["verification"]["actual_depth_cm"])
    assert replay_result["verification"]["actual_height_cm"] == pytest.approx(base_result["verification"]["actual_height_cm"])
    assert replay_result["verification"]["square_socket_width_cm"] == pytest.approx(
        base_result["verification"]["square_socket_width_cm"]
    )
    assert base_result["verification"]["effective_square_socket_width_cm"] == pytest.approx(
        base_result["verification"]["square_socket_width_cm"]
    )
    assert replay_result["verification"]["socket_clearance_per_side_cm"] == pytest.approx(replay_clearance_per_side_cm)
    assert replay_result["verification"]["effective_square_socket_width_cm"] == pytest.approx(
        base_result["verification"]["square_socket_width_cm"] + (replay_clearance_per_side_cm * 2.0)
    )
    assert _get_square_socket_cut_width(replay_result["stages"]) > _get_square_socket_cut_width(base_result["stages"])


def test_create_t_handle_with_square_socket_fails_when_top_chamfer_edge_count_is_wrong(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"apply_chamfer": _corrupt_chamfer_edge_count(3)},
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_t_handle_with_square_socket_bad_chamfer.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_t_handle_with_square_socket(
            {
                "tee_width_cm": 12.7,
                "tee_depth_cm": 5.08,
                "stem_length_cm": 5.08,
                "square_socket_width_cm": 1.905,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "apply_chamfer"
    assert failure.classification == "verification_failed"


def test_create_tube_mounting_plate_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_tube_mounting_plate_workflow.stl"

    result = server.create_tube_mounting_plate(
        {
            "width_cm": 6.0,
            "height_cm": 10.0,
            "plate_thickness_cm": 0.5,
            "hole_diameter_cm": 0.5,
            "edge_offset_y_cm": 1.5,
            "tube_outer_diameter_cm": 2.0,
            "tube_inner_diameter_cm": 1.2,
            "tube_height_cm": 3.0,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_tube_mounting_plate"
    assert result["workflow_basis"]["name"] == "tube_mounting_plate"
    assert result["verification"]["mount_hole_count"] == 2
    assert result["verification"]["actual_width_cm"] == 6.0
    assert result["verification"]["actual_height_cm"] == 10.0
    assert result["verification"]["actual_thickness_cm"] == 3.5
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "combine_bodies",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def _corrupt_body_token_result(command_name: str, field_name: str, value: object):
    def _interceptor(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
        result = client.send(envelope)
        if envelope.command != command_name:
            return result
        return {
            **result,
            "result": {
                field_name: {
                    **result["result"][field_name],
                    "token": value,
                },
            },
        }

    return _interceptor


def test_create_tube_mounting_plate_fails_when_combine_returns_wrong_body(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "combine_bodies": _corrupt_body_token_result("combine_bodies", "body", "wrong-body"),
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_tube_mounting_plate_bad_combine.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_tube_mounting_plate(
            {
                "width_cm": 6.0,
                "height_cm": 10.0,
                "plate_thickness_cm": 0.5,
                "hole_diameter_cm": 0.5,
                "edge_offset_y_cm": 1.5,
                "tube_outer_diameter_cm": 2.0,
                "tube_inner_diameter_cm": 1.2,
                "tube_height_cm": 3.0,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "combine_bodies"
    assert failure.classification == "verification_failed"


def test_create_bracket_workflow_exports_stl(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_bracket_workflow_exports_stl.stl"

    result = server.create_bracket(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.75,
            "leg_thickness_cm": 0.5,
            "plane": "xz",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_bracket"
    assert result["workflow_basis"]["name"] == "bracket"
    assert result["verification"]["body_count"] == 1
    assert result["verification"]["actual_width_cm"] == 4.0
    assert result["verification"]["actual_height_cm"] == 2.0
    assert result["verification"]["actual_thickness_cm"] == 0.75
    assert result["verification"]["sketch_plane"] == "xz"
    assert result["verification"]["leg_thickness_cm"] == 0.5
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_l_bracket_profile",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_filleted_bracket_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_filleted_bracket_workflow_exports_stl.stl"

    result = server.create_filleted_bracket(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.75,
            "leg_thickness_cm": 0.5,
            "fillet_radius_cm": 0.2,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_filleted_bracket"
    assert result["workflow_basis"]["name"] == "filleted_bracket"
    assert result["verification"]["body_count"] == 1
    assert result["verification"]["actual_width_cm"] == 4.0
    assert result["verification"]["actual_height_cm"] == 2.0
    assert result["verification"]["actual_thickness_cm"] == 0.75
    assert result["verification"]["sketch_plane"] == "xy"
    assert result["verification"]["leg_thickness_cm"] == 0.5
    assert result["verification"]["fillet_radius_cm"] == 0.2
    assert result["verification"]["fillet_edge_count"] == 2
    assert result["fillet"]["fillet_applied"] is True
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_l_bracket_profile",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "apply_fillet",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def _corrupt_fillet_edge_count(edge_count: int):
    def _interceptor(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
        result = client.send(envelope)
        return {
            **result,
            "result": {
                "fillet": {
                    **result["result"]["fillet"],
                    "edge_count": edge_count,
                },
            },
        }
    return _interceptor


def test_create_filleted_bracket_fails_when_fillet_edge_count_is_out_of_range(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"apply_fillet": _corrupt_fillet_edge_count(6)},
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_filleted_bracket_bad_edge_count.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_filleted_bracket(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "fillet_radius_cm": 0.2,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "apply_fillet"
    assert failure.classification == "verification_failed"
    assert "edge_count mismatch" in str(failure)


def test_create_chamfered_bracket_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_chamfered_bracket_workflow_exports_stl.stl"

    result = server.create_chamfered_bracket(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.75,
            "leg_thickness_cm": 0.5,
            "chamfer_distance_cm": 0.2,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_chamfered_bracket"
    assert result["workflow_basis"]["name"] == "chamfered_bracket"
    assert result["verification"]["body_count"] == 1
    assert result["verification"]["actual_width_cm"] == 4.0
    assert result["verification"]["actual_height_cm"] == 2.0
    assert result["verification"]["actual_thickness_cm"] == 0.75
    assert result["verification"]["sketch_plane"] == "xy"
    assert result["verification"]["leg_thickness_cm"] == 0.5
    assert result["verification"]["chamfer_distance_cm"] == 0.2
    assert result["verification"]["chamfer_edge_count"] == 2
    assert result["chamfer"]["chamfer_applied"] is True
    assert [stage["stage"] for stage in result["stages"]] == [
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
    ]
    assert Path(result["export"]["output_path"]).exists()


def _corrupt_chamfer_edge_count(edge_count: int):
    def _interceptor(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
        result = client.send(envelope)
        return {
            **result,
            "result": {
                "chamfer": {
                    **result["result"]["chamfer"],
                    "edge_count": edge_count,
                },
            },
        }

    return _interceptor


def test_create_chamfered_bracket_fails_when_chamfer_edge_count_is_out_of_range(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"apply_chamfer": _corrupt_chamfer_edge_count(6)},
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_chamfered_bracket_bad_edge_count.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_chamfered_bracket(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "chamfer_distance_cm": 0.2,
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "apply_chamfer"
    assert failure.classification == "verification_failed"
    assert "edge_count mismatch" in str(failure)


def test_create_mounting_bracket_workflow_selects_outer_profile(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_mounting_bracket_workflow_exports_stl.stl"

    result = server.create_mounting_bracket(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.75,
            "leg_thickness_cm": 0.5,
            "hole_diameter_cm": 0.4,
            "hole_center_x_cm": 0.25,
            "hole_center_y_cm": 1.5,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_mounting_bracket"
    assert result["workflow_basis"]["name"] == "mounting_bracket"
    assert result["verification"]["actual_width_cm"] == 4.0
    assert result["verification"]["actual_height_cm"] == 2.0
    assert result["verification"]["actual_thickness_cm"] == 0.75
    assert result["verification"]["hole_diameter_cm"] == 0.4
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_l_bracket_profile",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_two_hole_mounting_bracket_workflow_exports_stl(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_two_hole_mounting_bracket_workflow.stl"

    result = server.create_two_hole_mounting_bracket(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.75,
            "leg_thickness_cm": 0.5,
            "hole_diameter_cm": 0.4,
            "first_hole_center_x_cm": 0.25,
            "first_hole_center_y_cm": 1.5,
            "second_hole_center_x_cm": 1.5,
            "second_hole_center_y_cm": 0.25,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_two_hole_mounting_bracket"
    assert result["workflow_basis"]["name"] == "two_hole_mounting_bracket"
    assert result["verification"]["hole_count"] == 2
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_l_bracket_profile",
        "draw_circle",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_two_hole_plate_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_two_hole_plate_workflow.stl"

    result = server.create_two_hole_plate(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.4,
            "hole_diameter_cm": 0.4,
            "edge_offset_x_cm": 0.75,
            "hole_center_y_cm": 1.0,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_two_hole_plate"
    assert result["workflow_basis"]["name"] == "two_hole_plate"
    assert result["verification"]["hole_count"] == 2
    assert result["verification"]["edge_offset_x_cm"] == 0.75
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "draw_circle",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_two_hole_plate_fails_when_hole_profiles_do_not_match(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "list_profiles": lambda *, envelope, client, call_count: {
                    "ok": True,
                    "result": {
                        "profiles": [
                            {"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0},
                            {"token": "profile-hole-1", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                        ]
                    },
                },
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_two_hole_plate_bad_holes.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_two_hole_plate(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.4,
                "edge_offset_x_cm": 0.75,
                "hole_center_y_cm": 1.0,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "list_profiles"
    assert failure.classification == "verification_failed"
    assert failure.partial_result["expected_hole_diameter_cm"] == 0.4


def test_create_four_hole_mounting_plate_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_four_hole_mounting_plate_workflow.stl"

    result = server.create_four_hole_mounting_plate(
        {
            "width_cm": 4.0,
            "height_cm": 3.0,
            "thickness_cm": 0.4,
            "hole_diameter_cm": 0.4,
            "edge_offset_x_cm": 0.6,
            "edge_offset_y_cm": 0.7,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_four_hole_mounting_plate"
    assert result["workflow_basis"]["name"] == "four_hole_mounting_plate"
    assert result["verification"]["hole_diameter_cm"] == 0.4
    assert result["verification"]["hole_count"] == 4
    assert result["verification"]["edge_offset_x_cm"] == 0.6
    assert result["verification"]["edge_offset_y_cm"] == 0.7
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_four_hole_mounting_plate_fails_when_hole_profile_count_is_wrong(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "list_profiles": lambda *, envelope, client, call_count: {
                    "ok": True,
                    "result": {
                        "profiles": [
                            {"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 3.0},
                            {"token": "profile-hole-1", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                            {"token": "profile-hole-2", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                            {"token": "profile-hole-3", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                        ]
                    },
                },
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_four_hole_mounting_plate_bad_profiles.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_four_hole_mounting_plate(
            {
                "width_cm": 4.0,
                "height_cm": 3.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.4,
                "edge_offset_x_cm": 0.6,
                "edge_offset_y_cm": 0.7,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "list_profiles"
    assert failure.classification == "verification_failed"


def test_create_slotted_mounting_plate_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_slotted_mounting_plate_workflow.stl"

    result = server.create_slotted_mounting_plate(
        {
            "width_cm": 4.0,
            "height_cm": 3.0,
            "thickness_cm": 0.4,
            "hole_diameter_cm": 0.4,
            "edge_offset_x_cm": 0.6,
            "edge_offset_y_cm": 0.7,
            "slot_length_cm": 1.5,
            "slot_width_cm": 0.5,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_slotted_mounting_plate"
    assert result["workflow_basis"]["name"] == "slotted_mounting_plate"
    assert result["verification"]["hole_count"] == 4
    assert result["verification"]["slot_length_cm"] == 1.5
    assert result["verification"]["slot_width_cm"] == 0.5
    assert result["verification"]["slot_center_x_cm"] == 2.0
    assert result["verification"]["slot_center_y_cm"] == 1.5
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "draw_slot",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_slotted_mounting_plate_fails_when_slot_profile_does_not_match(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "list_profiles": lambda *, envelope, client, call_count: {
                    "ok": True,
                    "result": {
                        "profiles": [
                            {"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 3.0},
                            {"token": "profile-hole-1", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                            {"token": "profile-hole-2", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                            {"token": "profile-hole-3", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                            {"token": "profile-hole-4", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                        ]
                    },
                },
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_slotted_mounting_plate_bad_slot.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_slotted_mounting_plate(
            {
                "width_cm": 4.0,
                "height_cm": 3.0,
                "thickness_cm": 0.4,
                "hole_diameter_cm": 0.4,
                "edge_offset_x_cm": 0.6,
                "edge_offset_y_cm": 0.7,
                "slot_length_cm": 1.5,
                "slot_width_cm": 0.5,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "list_profiles"
    assert failure.classification == "verification_failed"


def test_create_slotted_mount_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_slotted_mount_workflow.stl"

    result = server.create_slotted_mount(
        {
            "width_cm": 4.0,
            "height_cm": 2.0,
            "thickness_cm": 0.4,
            "slot_length_cm": 1.5,
            "slot_width_cm": 0.5,
            "slot_center_x_cm": 2.0,
            "slot_center_y_cm": 1.0,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_slotted_mount"
    assert result["workflow_basis"]["name"] == "slotted_mount"
    assert result["verification"]["slot_length_cm"] == 1.5
    assert result["verification"]["slot_width_cm"] == 0.5
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "draw_slot",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_slotted_mount_fails_when_slot_profile_does_not_match(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "list_profiles": lambda *, envelope, client, call_count: {
                    "ok": True,
                    "result": {
                        "profiles": [
                            {"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0},
                        ]
                    },
                },
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_slotted_mount_bad_slot.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_slotted_mount(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.4,
                "slot_length_cm": 1.5,
                "slot_width_cm": 0.5,
                "slot_center_x_cm": 2.0,
                "slot_center_y_cm": 1.0,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "list_profiles"
    assert failure.classification == "verification_failed"
    assert failure.partial_result["expected_slot_length_cm"] == 1.5


def test_create_plate_with_hole_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_plate_with_hole_workflow.stl"

    result = server.create_plate_with_hole(
        {
            "width_cm": 3.0,
            "height_cm": 2.0,
            "thickness_cm": 0.5,
            "hole_diameter_cm": 0.4,
            "hole_center_x_cm": 1.0,
            "hole_center_y_cm": 0.5,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_plate_with_hole"
    assert result["workflow_basis"]["name"] == "plate_with_hole"
    assert result["verification"]["hole_diameter_cm"] == 0.4
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert result["stages"][5]["operation"] == "new_body"
    assert result["stages"][10]["operation"] == "cut"
    assert Path(result["export"]["output_path"]).exists()


def test_create_plate_with_hole_wraps_cut_bridge_failure(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "extrude_profile": lambda *, envelope, client, call_count: (
                    client.send(envelope) if call_count == 1 else (_ for _ in ()).throw(RuntimeError("Bridge command failed: cut unavailable"))
                ),
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_plate_with_hole_cut_failure.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_plate_with_hole(
            {
                "width_cm": 3.0,
                "height_cm": 2.0,
                "thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 1.0,
                "hole_center_y_cm": 0.5,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "extrude_profile"
    assert failure.classification == "bridge_error"
    assert failure.partial_result["body"]["name"] == "Plate"


def test_create_counterbored_plate_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_counterbored_plate_workflow.stl"

    result = server.create_counterbored_plate(
        {
            "width_cm": 4.0,
            "height_cm": 2.5,
            "thickness_cm": 0.5,
            "hole_diameter_cm": 0.4,
            "hole_center_x_cm": 2.0,
            "hole_center_y_cm": 1.25,
            "counterbore_diameter_cm": 0.8,
            "counterbore_depth_cm": 0.2,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_counterbored_plate"
    assert result["workflow_basis"]["name"] == "counterbored_plate"
    assert result["verification"]["hole_diameter_cm"] == 0.4
    assert result["verification"]["counterbore_diameter_cm"] == 0.8
    assert result["verification"]["counterbore_depth_cm"] == 0.2
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_counterbored_plate_fails_when_counterbore_profile_does_not_match(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "list_profiles": lambda *, envelope, client, call_count: (
                    client.send(envelope)
                    if call_count != 3
                    else {
                        "ok": True,
                        "result": {
                            "profiles": [
                                {"token": "profile-counterbore", "kind": "profile", "width_cm": 0.7, "height_cm": 0.7}
                            ]
                        },
                    }
                )
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_counterbored_plate_bad_counterbore.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_counterbored_plate(
            {
                "width_cm": 4.0,
                "height_cm": 2.5,
                "thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 2.0,
                "hole_center_y_cm": 1.25,
                "counterbore_diameter_cm": 0.8,
                "counterbore_depth_cm": 0.2,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "list_profiles"
    assert failure.classification == "verification_failed"


def test_create_recessed_mount_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_recessed_mount_workflow.stl"

    result = server.create_recessed_mount(
        {
            "width_cm": 4.0,
            "height_cm": 2.5,
            "thickness_cm": 0.5,
            "recess_width_cm": 2.0,
            "recess_height_cm": 1.0,
            "recess_depth_cm": 0.2,
            "recess_origin_x_cm": 1.0,
            "recess_origin_y_cm": 0.75,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_recessed_mount"
    assert result["workflow_basis"]["name"] == "recessed_mount"
    assert result["verification"]["recess_width_cm"] == 2.0
    assert result["verification"]["recess_height_cm"] == 1.0
    assert result["verification"]["recess_depth_cm"] == 0.2
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_rectangle_at",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_recessed_mount_fails_when_recess_profile_does_not_match(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "list_profiles": lambda *, envelope, client, call_count: (
                    client.send(envelope)
                    if call_count != 2
                    else {
                        "ok": True,
                        "result": {
                            "profiles": [
                                {"token": "profile-recess", "kind": "profile", "width_cm": 1.9, "height_cm": 1.0}
                            ]
                        },
                    }
                )
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_recessed_mount_bad_recess.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_recessed_mount(
            {
                "width_cm": 4.0,
                "height_cm": 2.5,
                "thickness_cm": 0.5,
                "recess_width_cm": 2.0,
                "recess_height_cm": 1.0,
                "recess_depth_cm": 0.2,
                "recess_origin_x_cm": 1.0,
                "recess_origin_y_cm": 0.75,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "list_profiles"
    assert failure.classification == "verification_failed"


def test_create_open_box_body_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_open_box_body_workflow.stl"

    result = server.create_open_box_body(
        {
            "width_cm": 4.0,
            "depth_cm": 3.0,
            "height_cm": 2.0,
            "wall_thickness_cm": 0.3,
            "floor_thickness_cm": 0.4,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_open_box_body"
    assert result["workflow_basis"]["name"] == "open_box_body"
    assert result["verification"]["wall_thickness_cm"] == 0.3
    assert result["verification"]["floor_thickness_cm"] == 0.4
    assert result["verification"]["cavity_width_cm"] == 3.4
    assert result["verification"]["cavity_depth_cm"] == 2.4
    assert result["verification"]["actual_width_cm"] == 4.0
    assert result["verification"]["actual_depth_cm"] == 3.0
    assert result["verification"]["actual_height_cm"] == 2.0
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_rectangle_at",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_open_box_body_fails_when_cavity_profile_does_not_match(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "list_profiles": lambda *, envelope, client, call_count: (
                    client.send(envelope)
                    if call_count != 2
                    else {
                        "ok": True,
                        "result": {
                            "profiles": [
                                {"token": "profile-cavity", "kind": "profile", "width_cm": 3.3, "height_cm": 2.4}
                            ]
                        },
                    }
                )
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_open_box_body_bad_cavity.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_open_box_body(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "height_cm": 2.0,
                "wall_thickness_cm": 0.3,
                "floor_thickness_cm": 0.4,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "list_profiles"
    assert failure.classification == "verification_failed"


def test_create_simple_enclosure_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_simple_enclosure_workflow.stl"

    result = server.create_simple_enclosure(
        {
            "width_cm": 4.0,
            "depth_cm": 3.0,
            "height_cm": 2.0,
            "wall_thickness_cm": 0.3,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_simple_enclosure"
    assert result["workflow_basis"]["name"] == "simple_enclosure"
    assert result["verification"]["wall_thickness_cm"] == 0.3
    assert result["verification"]["inner_width_cm"] == pytest.approx(3.4)
    assert result["verification"]["inner_depth_cm"] == pytest.approx(2.4)
    assert result["verification"]["inner_height_cm"] == pytest.approx(1.7)
    assert result["verification"]["actual_width_cm"] == 4.0
    assert result["verification"]["actual_depth_cm"] == 3.0
    assert result["verification"]["actual_height_cm"] == 2.0
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "apply_shell",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def _corrupt_shell_field(field_name: str, value: object):
    def _interceptor(*, envelope: CommandEnvelope, client: BridgeClient, call_count: int) -> dict:
        result = client.send(envelope)
        return {
            **result,
            "result": {
                "shell": {
                    **result["result"]["shell"],
                    field_name: value,
                },
            },
        }

    return _interceptor


def test_create_simple_enclosure_fails_when_shell_result_is_invalid(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"apply_shell": _corrupt_shell_field("removed_face_count", 0)},
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_simple_enclosure_bad_shell.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_simple_enclosure(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "height_cm": 2.0,
                "wall_thickness_cm": 0.3,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "apply_shell"
    assert failure.classification == "verification_failed"
    assert failure.partial_result["shell"]["removed_face_count"] == 0


def test_create_lid_for_box_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_lid_for_box_workflow.stl"

    result = server.create_lid_for_box(
        {
            "width_cm": 4.0,
            "depth_cm": 3.0,
            "lid_thickness_cm": 0.2,
            "rim_depth_cm": 0.4,
            "wall_thickness_cm": 0.3,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_lid_for_box"
    assert result["workflow_basis"]["name"] == "lid_for_box"
    assert result["verification"]["lid_thickness_cm"] == 0.2
    assert result["verification"]["rim_depth_cm"] == 0.4
    assert result["verification"]["wall_thickness_cm"] == 0.3
    assert result["verification"]["rim_opening_width_cm"] == 3.4
    assert result["verification"]["rim_opening_depth_cm"] == 2.4
    assert result["verification"]["actual_width_cm"] == 4.0
    assert result["verification"]["actual_depth_cm"] == 3.0
    assert result["verification"]["actual_height_cm"] == pytest.approx(0.6)
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "create_sketch",
        "draw_rectangle_at",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_lid_for_box_fails_when_rim_opening_profile_does_not_match(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "list_profiles": lambda *, envelope, client, call_count: (
                    client.send(envelope)
                    if call_count != 2
                    else {
                        "ok": True,
                        "result": {
                            "profiles": [
                                {"token": "profile-rim-opening", "kind": "profile", "width_cm": 3.3, "height_cm": 2.4}
                            ]
                        },
                    }
                )
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_lid_for_box_bad_rim.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_lid_for_box(
            {
                "width_cm": 4.0,
                "depth_cm": 3.0,
                "lid_thickness_cm": 0.2,
                "rim_depth_cm": 0.4,
                "wall_thickness_cm": 0.3,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "list_profiles"
    assert failure.classification == "verification_failed"


def test_create_box_with_lid_workflow_exports_two_stls(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path_box = Path.cwd() / "manual_test_output" / "test_box_with_lid_box.stl"
    output_path_lid = Path.cwd() / "manual_test_output" / "test_box_with_lid_lid.stl"

    result = server.create_box_with_lid(
        {
            "width_cm": 6.0,
            "depth_cm": 4.0,
            "box_height_cm": 3.0,
            "wall_thickness_cm": 0.3,
            "floor_thickness_cm": 0.3,
            "lid_thickness_cm": 0.2,
            "rim_depth_cm": 0.5,
            "clearance_cm": 0.05,
            "output_path_box": str(output_path_box),
            "output_path_lid": str(output_path_lid),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_box_with_lid"
    assert result["workflow_basis"]["name"] == "box_with_lid"
    assert result["verification"]["body_count"] == 2
    assert result["box_body"]["token"] != result["lid_body"]["token"]
    assert result["box_body"]["name"] == "Box Body"
    assert result["lid_body"]["name"] == "Lid Body"
    assert result["verification"]["box_width_cm"] == 6.0
    assert result["verification"]["box_depth_cm"] == 4.0
    # lid is larger than box: width + 2*wall + 2*clearance
    assert result["verification"]["lid_width_cm"] == pytest.approx(6.0 + 2 * 0.3 + 2 * 0.05)
    assert result["verification"]["lid_depth_cm"] == pytest.approx(4.0 + 2 * 0.3 + 2 * 0.05)
    # rim opening slightly larger than box exterior
    assert result["verification"]["rim_opening_width_cm"] == pytest.approx(6.0 + 2 * 0.05)
    assert result["verification"]["rim_opening_depth_cm"] == pytest.approx(4.0 + 2 * 0.05)
    assert result["verification"]["clearance_cm"] == pytest.approx(0.05)
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design", "verify_clean_state",
        "create_sketch", "draw_rectangle", "list_profiles", "extrude_profile", "verify_geometry",
        "create_sketch", "draw_rectangle_at", "list_profiles", "extrude_profile", "verify_geometry",
        "create_sketch", "draw_rectangle_at", "list_profiles", "extrude_profile", "verify_geometry",
        "create_sketch", "draw_rectangle_at", "list_profiles", "extrude_profile", "verify_geometry",
        "export_stl", "export_stl",
    ]
    assert Path(result["export_box"]["output_path"]).exists()
    assert Path(result["export_lid"]["output_path"]).exists()


def test_create_box_with_lid_fails_when_rim_cut_returns_wrong_body(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "extrude_profile": lambda *, envelope, client, call_count: (
                    client.send(envelope)
                    if call_count != 4
                    else {
                        "ok": True,
                        "result": {
                            "body": {
                                "token": "wrong-body",
                                "name": "Box Body",
                                "width_cm": 6.0,
                                "height_cm": 4.0,
                                "thickness_cm": 3.0,
                                "operation": "cut",
                            }
                        },
                    }
                )
            },
        )
    )
    output_path_box = Path.cwd() / "manual_test_output" / "test_box_with_lid_wrong_body_box.stl"
    output_path_lid = Path.cwd() / "manual_test_output" / "test_box_with_lid_wrong_body_lid.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_box_with_lid(
            {
                "width_cm": 6.0,
                "depth_cm": 4.0,
                "box_height_cm": 3.0,
                "wall_thickness_cm": 0.3,
                "floor_thickness_cm": 0.3,
                "lid_thickness_cm": 0.2,
                "rim_depth_cm": 0.5,
                "clearance_cm": 0.05,
                "output_path_box": str(output_path_box),
                "output_path_lid": str(output_path_lid),
            }
        )

    failure = exc_info.value
    assert failure.stage == "extrude_profile"
    assert failure.classification == "verification_failed"
    assert failure.partial_result["lid_body"]["token"] == "wrong-body"


def test_get_body_info_returns_bounding_box_and_counts(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_get_body_info.stl"

    # Create a spacer to get a body
    spacer = server.create_spacer(
        {"width_cm": 3.0, "height_cm": 2.0, "thickness_cm": 0.5, "output_path": str(output_path)}
    )
    body_token = spacer["body"]["token"]

    result = server.get_body_info({"body_token": body_token})
    assert result["ok"] is True
    info = result["result"]["body_info"]
    assert info["body_token"] == body_token
    assert info["width_cm"] == pytest.approx(3.0)
    assert info["height_cm"] == pytest.approx(2.0)
    assert info["thickness_cm"] == pytest.approx(0.5)
    bb = info["bounding_box"]
    assert "min_x" in bb and "max_x" in bb
    assert "min_y" in bb and "max_y" in bb
    assert "min_z" in bb and "max_z" in bb
    assert info["face_count"] >= 1
    assert info["edge_count"] >= 1
    assert info["volume_cm3"] is not None


def test_get_body_info_nonexistent_body_raises(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    server.new_design("empty")
    with pytest.raises(RuntimeError):
        server.get_body_info({"body_token": "body-999"})


def test_get_body_info_missing_token_raises(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    with pytest.raises(ValueError, match="body_token"):
        server.get_body_info({})


def test_get_body_faces_returns_planar_faces_with_normals(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_get_body_faces.stl"

    spacer = server.create_spacer(
        {"width_cm": 3.0, "height_cm": 2.0, "thickness_cm": 0.5, "output_path": str(output_path)}
    )
    body_token = spacer["body"]["token"]

    result = server.get_body_faces({"body_token": body_token})
    assert result["ok"] is True
    faces = result["result"]["body_faces"]
    assert len(faces) == 6
    assert all(face["token"] for face in faces)
    assert all(face["type"] == "planar" for face in faces)
    assert all(face["area_cm2"] > 0 for face in faces)
    assert all("bounding_box" in face for face in faces)
    assert any(face["normal_vector"] == {"x": 0.0, "y": 0.0, "z": 1.0} for face in faces)
    assert any(face["normal_vector"] == {"x": 0.0, "y": 0.0, "z": -1.0} for face in faces)


def test_get_body_faces_nonexistent_body_raises(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    server.new_design("empty")
    with pytest.raises(RuntimeError):
        server.get_body_faces({"body_token": "body-999"})


def test_get_body_faces_missing_token_raises(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    with pytest.raises(ValueError, match="body_token"):
        server.get_body_faces({})


def test_get_body_edges_returns_linear_edges_with_points(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_get_body_edges.stl"

    spacer = server.create_spacer(
        {"width_cm": 3.0, "height_cm": 2.0, "thickness_cm": 0.5, "output_path": str(output_path)}
    )
    body_token = spacer["body"]["token"]

    result = server.get_body_edges({"body_token": body_token})
    assert result["ok"] is True
    edges = result["result"]["body_edges"]
    assert len(edges) == 12
    assert all(edge["token"] for edge in edges)
    assert all(edge["type"] == "linear" for edge in edges)
    assert all(edge["start_point"] is not None for edge in edges)
    assert all(edge["end_point"] is not None for edge in edges)
    assert any(edge["length_cm"] == pytest.approx(3.0) for edge in edges)
    assert any(edge["length_cm"] == pytest.approx(2.0) for edge in edges)
    assert any(edge["length_cm"] == pytest.approx(0.5) for edge in edges)


def test_get_body_edges_nonexistent_body_raises(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    server.new_design("empty")
    with pytest.raises(RuntimeError):
        server.get_body_edges({"body_token": "body-999"})


def test_get_body_edges_missing_token_raises(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    with pytest.raises(ValueError, match="body_token"):
        server.get_body_edges({})


def test_bridge_command_error_surfaces_as_runtime_error(running_bridge) -> None:
    """A bad command through the bridge raises RuntimeError, not a silent failure."""
    _, base_url = running_bridge
    client = BridgeClient(base_url)
    with pytest.raises(RuntimeError, match="Bridge command failed"):
        client.send(CommandEnvelope.build("draw_rectangle", {"sketch_token": "bad", "width_cm": 1.0, "height_cm": 1.0}))


def test_workflow_failure_includes_partial_state_on_dirty_scene(running_bridge) -> None:
    """WorkflowFailure on state_drift carries the scene snapshot in partial_result.

    The verify_clean_state check fires when get_scene_info reports bodies after new_design.
    We simulate that by patching get_scene_info to return a dirty scene on the first call.
    """
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "get_scene_info": _dirty_scene_once,
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_dirty_state.stl"

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
    assert failure.stage == "verify_clean_state"
    assert failure.classification == "state_drift"
    assert "scene" in failure.partial_result


def test_create_mounting_bracket_wraps_export_bridge_failure(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "export_stl": _raise_bridge_error("Bridge command failed: export unavailable"),
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_mounting_bracket_bridge_failure.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_mounting_bracket(
            {
                "width_cm": 4.0,
                "height_cm": 2.0,
                "thickness_cm": 0.75,
                "leg_thickness_cm": 0.5,
                "hole_diameter_cm": 0.4,
                "hole_center_x_cm": 0.25,
                "hole_center_y_cm": 1.5,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "export_stl"
    assert failure.classification == "bridge_error"
    assert failure.partial_result["body"]["name"] == "Mounting Bracket"
    assert failure.partial_result["stages"][-1]["stage"] == "verify_geometry"


def test_create_spacer_wraps_bridge_timeout_in_workflow_failure(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "get_scene_info": _raise_bridge_timeout,
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_wraps_bridge_timeout.stl"

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
    assert failure.stage == "verify_clean_state"
    assert failure.classification == "timeout"
    assert failure.partial_result["stages"] == [{"stage": "new_design", "status": "completed"}]
    assert "timed out" in str(failure)


def test_create_spacer_wraps_bridge_cancellation_in_workflow_failure(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "get_scene_info": _raise_bridge_cancelled,
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_create_spacer_wraps_bridge_cancellation.stl"

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
    assert failure.stage == "verify_clean_state"
    assert failure.classification == "cancelled"
    assert failure.partial_result["stages"] == [{"stage": "new_design", "status": "completed"}]
    assert "cancelled" in str(failure)


def test_create_project_box_with_standoffs_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_project_box_with_standoffs.stl"

    result = server.create_project_box_with_standoffs(
        {
            "width_cm": 8.0,
            "depth_cm": 6.0,
            "height_cm": 3.0,
            "wall_thickness_cm": 0.3,
            "standoff_diameter_cm": 0.5,
            "standoff_height_cm": 1.5,
            "standoff_inset_cm": 0.5,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_project_box_with_standoffs"
    assert result["workflow_basis"]["name"] == "project_box_with_standoffs"
    assert result["verification"]["wall_thickness_cm"] == 0.3
    assert result["verification"]["standoff_count"] == 4
    assert result["verification"]["standoff_diameter_cm"] == 0.5
    assert result["verification"]["standoff_height_cm"] == 1.5
    assert result["verification"]["inner_width_cm"] == pytest.approx(7.4)
    assert result["verification"]["inner_depth_cm"] == pytest.approx(5.4)
    assert result["verification"]["inner_height_cm"] == pytest.approx(2.7)
    assert result["verification"]["actual_width_cm"] == 8.0
    assert result["verification"]["actual_depth_cm"] == 6.0
    assert result["verification"]["actual_height_cm"] == 3.0
    expected_stages = [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "apply_shell",
        "verify_geometry",
    ]
    # 4 standoffs: each adds create_sketch, draw_circle, list_profiles, extrude_profile, verify_geometry, combine_bodies, verify_geometry
    for _ in range(4):
        expected_stages.extend([
            "create_sketch",
            "draw_circle",
            "list_profiles",
            "extrude_profile",
            "verify_geometry",
            "combine_bodies",
            "verify_geometry",
        ])
    expected_stages.append("export_stl")
    assert [stage["stage"] for stage in result["stages"]] == expected_stages
    assert Path(result["export"]["output_path"]).exists()


def test_create_project_box_with_standoffs_fails_when_shell_is_invalid(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={"apply_shell": _corrupt_shell_field("removed_face_count", 0)},
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_project_box_standoffs_bad_shell.stl"

    with pytest.raises(WorkflowFailure) as exc_info:
        server.create_project_box_with_standoffs(
            {
                "width_cm": 8.0,
                "depth_cm": 6.0,
                "height_cm": 3.0,
                "wall_thickness_cm": 0.3,
                "standoff_diameter_cm": 0.5,
                "standoff_height_cm": 1.5,
                "standoff_inset_cm": 0.5,
                "plane": "xy",
                "output_path": str(output_path),
            }
        )

    failure = exc_info.value
    assert failure.stage == "apply_shell"
    assert failure.classification == "verification_failed"


def test_create_shaft_coupler_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_shaft_coupler.stl"

    result = server.create_shaft_coupler(
        {
            "outer_diameter_cm": 2.5,
            "length_cm": 5.0,
            "bore_diameter_cm": 0.8,
            "pin_hole_diameter_cm": 0.4,
            "pin_hole_offset_cm": 2.5,
            "plane": "xy",
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_shaft_coupler"
    assert result["workflow_basis"]["name"] == "shaft_coupler"
    assert result["verification"]["outer_diameter_cm"] == 2.5
    assert result["verification"]["length_cm"] == 5.0
    assert result["verification"]["bore_diameter_cm"] == 0.8
    assert result["verification"]["pin_hole_diameter_cm"] == 0.4
    assert result["verification"]["pin_hole_offset_cm"] == 2.5
    assert result["verification"]["actual_outer_diameter_cm"] == pytest.approx(2.5)
    assert result["verification"]["actual_length_cm"] == pytest.approx(5.0)
    expected_stages = [
        "new_design",
        "verify_clean_state",
        # outer cylinder
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        # axial bore
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        # cross-pin hole
        "create_sketch",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        # export
        "export_stl",
    ]
    assert [stage["stage"] for stage in result["stages"]] == expected_stages
    assert Path(result["export"]["output_path"]).exists()


def test_create_cable_gland_plate_workflow_exports_stl(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(BridgeClient(base_url))
    output_path = Path.cwd() / "manual_test_output" / "test_create_cable_gland_plate_workflow.stl"

    result = server.create_cable_gland_plate(
        {
            "width_cm": 10.0,
            "height_cm": 8.0,
            "thickness_cm": 0.4,
            "center_hole_diameter_cm": 3.0,
            "mounting_hole_diameter_cm": 0.5,
            "edge_offset_x_cm": 1.0,
            "edge_offset_y_cm": 1.0,
            "output_path": str(output_path),
        }
    )

    assert result["ok"] is True
    assert result["workflow"] == "create_cable_gland_plate"
    assert result["workflow_basis"]["name"] == "cable_gland_plate"
    assert result["verification"]["center_hole_diameter_cm"] == 3.0
    assert result["verification"]["mounting_hole_diameter_cm"] == 0.5
    assert result["verification"]["mounting_hole_count"] == 4
    assert result["verification"]["edge_offset_x_cm"] == 1.0
    assert result["verification"]["edge_offset_y_cm"] == 1.0
    assert [stage["stage"] for stage in result["stages"]] == [
        "new_design",
        "verify_clean_state",
        "create_sketch",
        "draw_rectangle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "draw_circle",
        "list_profiles",
        "extrude_profile",
        "verify_geometry",
        "export_stl",
    ]
    assert Path(result["export"]["output_path"]).exists()


def test_create_cable_gland_plate_fails_when_mounting_hole_profile_count_is_wrong(running_bridge) -> None:
    _, base_url = running_bridge
    server = ParamAIToolServer(
        InterceptingBridgeClient(
            base_url,
            interceptors={
                "list_profiles": lambda *, envelope, client, call_count: {
                    "ok": True,
                    "result": {
                        "profiles": [
                            {"token": "profile-outer", "kind": "profile", "width_cm": 10.0, "height_cm": 8.0},
                            {"token": "profile-mount-1", "kind": "profile", "width_cm": 0.5, "height_cm": 0.5},
                            {"token": "profile-mount-2", "kind": "profile", "width_cm": 0.5, "height_cm": 0.5},
                            {"token": "profile-center", "kind": "profile", "width_cm": 3.0, "height_cm": 3.0},
                        ]
                    },
                },
            },
        )
    )
    output_path = Path.cwd() / "manual_test_output" / "test_cable_gland_plate_fail.stl"

    with pytest.raises(WorkflowFailure, match="four matching mounting hole profiles"):
        server.create_cable_gland_plate(
            {
                "width_cm": 10.0,
                "height_cm": 8.0,
                "thickness_cm": 0.4,
                "center_hole_diameter_cm": 3.0,
                "mounting_hole_diameter_cm": 0.5,
                "edge_offset_x_cm": 1.0,
                "edge_offset_y_cm": 1.0,
                "output_path": str(output_path),
            }
        )
