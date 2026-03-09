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
