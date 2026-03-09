from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from urllib.error import URLError


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "fusion_smoke_test.py"
_SPEC = importlib.util.spec_from_file_location("paramaitric_fusion_smoke_test", _SCRIPT_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
smoke_test = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = smoke_test
_SPEC.loader.exec_module(smoke_test)


def test_smoke_script_exits_when_bridge_is_not_reachable(monkeypatch) -> None:
    monkeypatch.setattr(smoke_test, "_health", lambda base_url: (_ for _ in ()).throw(URLError("offline")))

    exit_code = smoke_test.main([])
    assert exit_code == 1


def test_smoke_script_fails_fast_when_workflow_not_in_live_catalog(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        smoke_test,
        "_health",
        lambda base_url: {
            "ok": True,
            "mode": "live",
            "status": "ready",
            "workflow_catalog": [{"name": "spacer"}, {"name": "bracket"}],
        },
    )

    def unexpected_send(base_url: str, command: str, arguments: dict) -> dict:
        raise AssertionError("Smoke script should fail before issuing bridge commands.")

    monkeypatch.setattr(smoke_test, "_send", unexpected_send)

    exit_code = smoke_test.main(["--workflow", "plate_with_hole"])

    assert exit_code == 1
    assert "Reload the Fusion add-in" in capsys.readouterr().out


def test_smoke_script_validates_xz_geometry(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_xz_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    def fake_health(base_url: str) -> dict:
        assert base_url == "http://127.0.0.1:8123"
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        assert base_url == "http://127.0.0.1:8123"
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Smoke Test",
                    "sketches": [],
                    "bodies": [],
                    "exports": [],
                },
            }
        if command == "create_sketch":
            return {
                "ok": True,
                "result": {
                    "sketch": {"token": "sketch-1", "name": "Smoke Sketch", "plane": "xz"},
                },
            }
        if command == "draw_rectangle":
            return {
                "ok": True,
                "result": {
                    "sketch_token": "sketch-1",
                    "rectangle_index": 0,
                    "width_cm": 4.0,
                    "height_cm": 2.0,
                },
            }
        if command == "list_profiles":
            return {
                "ok": True,
                "result": {
                    "profiles": [
                        {"token": "profile-1", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0}
                    ]
                },
            }
        if command == "extrude_profile":
            return {
                "ok": True,
                "result": {
                    "body": {
                        "token": "body-1",
                        "name": "Smoke Spacer",
                        "width_cm": 4.0,
                        "height_cm": 2.0,
                        "thickness_cm": 0.75,
                    }
                },
            }
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Smoke Sketch", "plane": "xz"}],
                    "bodies": [
                        {
                            "token": "body-1",
                            "name": "Smoke Spacer",
                            "width_cm": 4.0,
                            "height_cm": 2.0,
                            "thickness_cm": 0.75,
                        }
                    ],
                    "exports": [],
                },
            }
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {
                "ok": True,
                "result": {
                    "body_token": "body-1",
                    "output_path": str(output_path.resolve(strict=False)),
                },
            }
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--plane",
            "xz",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.75",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0


def test_smoke_script_routes_bracket_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_bracket_xz_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        assert base_url == "http://127.0.0.1:8123"
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        assert base_url == "http://127.0.0.1:8123"
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Bracket Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Bracket Smoke Test",
                    "sketches": [],
                    "bodies": [],
                    "exports": [],
                },
            }
        if command == "create_sketch":
            return {
                "ok": True,
                "result": {
                    "sketch": {"token": "sketch-1", "name": "Bracket Smoke Sketch", "plane": "xz"},
                },
            }
        if command == "draw_l_bracket_profile":
            return {
                "ok": True,
                "result": {
                    "sketch_token": "sketch-1",
                    "profile_index": 0,
                    "width_cm": 4.0,
                    "height_cm": 2.0,
                    "leg_thickness_cm": 0.5,
                },
            }
        if command == "list_profiles":
            return {
                "ok": True,
                "result": {
                    "profiles": [
                        {"token": "profile-1", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0}
                    ]
                },
            }
        if command == "extrude_profile":
            return {
                "ok": True,
                "result": {
                    "body": {
                        "token": "body-1",
                        "name": "Smoke Bracket",
                        "width_cm": 4.0,
                        "height_cm": 2.0,
                        "thickness_cm": 0.75,
                    }
                },
            }
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Bracket Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Bracket Smoke Sketch", "plane": "xz"}],
                    "bodies": [
                        {
                            "token": "body-1",
                            "name": "Smoke Bracket",
                            "width_cm": 4.0,
                            "height_cm": 2.0,
                            "thickness_cm": 0.75,
                        }
                    ],
                    "exports": [],
                },
            }
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {
                "ok": True,
                "result": {
                    "body_token": "body-1",
                    "output_path": str(output_path.resolve(strict=False)),
                },
            }
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "bracket",
            "--plane",
            "xz",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.75",
            "--leg-thickness-cm",
            "0.5",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert recorded_commands[0] == (
        "new_design",
        {"name": "Fusion Live Bracket Smoke Test", "workflow_name": "bracket"},
    )
    assert all(arguments["workflow_name"] == "bracket" for _, arguments in recorded_commands)
    create_sketch_arguments = next(arguments for command, arguments in recorded_commands if command == "create_sketch")
    assert create_sketch_arguments["name"] == "Bracket Smoke Sketch"
    draw_arguments = next(arguments for command, arguments in recorded_commands if command == "draw_l_bracket_profile")
    assert draw_arguments["leg_thickness_cm"] == 0.5
    extrude_arguments = next(arguments for command, arguments in recorded_commands if command == "extrude_profile")
    assert extrude_arguments["body_name"] == "Smoke Bracket"


def test_smoke_script_routes_mounting_bracket_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_mounting_bracket_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        assert base_url == "http://127.0.0.1:8123"
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        assert base_url == "http://127.0.0.1:8123"
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Mounting Bracket Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Mounting Bracket Smoke Test",
                    "sketches": [],
                    "bodies": [],
                    "exports": [],
                },
            }
        if command == "create_sketch":
            return {
                "ok": True,
                "result": {
                    "sketch": {"token": "sketch-1", "name": "Mounting Bracket Smoke Sketch", "plane": "xy"},
                },
            }
        if command == "draw_l_bracket_profile":
            return {
                "ok": True,
                "result": {
                    "sketch_token": "sketch-1",
                    "profile_index": 0,
                    "width_cm": 4.0,
                    "height_cm": 2.0,
                    "leg_thickness_cm": 0.5,
                },
            }
        if command == "draw_circle":
            return {
                "ok": True,
                "result": {
                    "sketch_token": "sketch-1",
                    "circle_index": 1,
                    "center_x_cm": 0.25,
                    "center_y_cm": 1.5,
                    "radius_cm": 0.2,
                },
            }
        if command == "list_profiles":
            return {
                "ok": True,
                "result": {
                    "profiles": [
                        {"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0},
                        {"token": "profile-hole", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                    ]
                },
            }
        if command == "extrude_profile":
            return {
                "ok": True,
                "result": {
                    "body": {
                        "token": "body-1",
                        "name": "Smoke Mounting Bracket",
                        "width_cm": 4.0,
                        "height_cm": 2.0,
                        "thickness_cm": 0.75,
                    }
                },
            }
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Mounting Bracket Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Mounting Bracket Smoke Sketch", "plane": "xy"}],
                    "bodies": [
                        {
                            "token": "body-1",
                            "name": "Smoke Mounting Bracket",
                            "width_cm": 4.0,
                            "height_cm": 2.0,
                            "thickness_cm": 0.75,
                        }
                    ],
                    "exports": [],
                },
            }
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {
                "ok": True,
                "result": {
                    "body_token": "body-1",
                    "output_path": str(output_path.resolve(strict=False)),
                },
            }
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "mounting_bracket",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.75",
            "--leg-thickness-cm",
            "0.5",
            "--hole-diameter-cm",
            "0.4",
            "--hole-center-x-cm",
            "0.25",
            "--hole-center-y-cm",
            "1.5",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert recorded_commands[0] == (
        "new_design",
        {"name": "Fusion Live Mounting Bracket Smoke Test", "workflow_name": "mounting_bracket"},
    )
    draw_circle_arguments = next(arguments for command, arguments in recorded_commands if command == "draw_circle")
    assert draw_circle_arguments["radius_cm"] == 0.2


def test_smoke_script_routes_two_hole_mounting_bracket_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_two_hole_mounting_bracket_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Two-Hole Mounting Bracket Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Two-Hole Mounting Bracket Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Two-Hole Mounting Bracket Smoke Sketch", "plane": "xy"}}}
        if command == "draw_l_bracket_profile":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "profile_index": 0, "width_cm": 4.0, "height_cm": 2.0, "leg_thickness_cm": 0.5}}
        if command == "draw_circle":
            circle_index = 1 if len([c for c, _ in recorded_commands if c == "draw_circle"]) == 1 else 2
            return {"ok": True, "result": {"sketch_token": "sketch-1", "circle_index": circle_index, "center_x_cm": arguments["center_x_cm"], "center_y_cm": arguments["center_y_cm"], "radius_cm": 0.2}}
        if command == "list_profiles":
            return {
                "ok": True,
                "result": {
                    "profiles": [
                        {"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0},
                        {"token": "profile-hole-1", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                        {"token": "profile-hole-2", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                    ]
                },
            }
        if command == "extrude_profile":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Two-Hole Mounting Bracket", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.75}}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {"ok": True, "result": {"design_name": "Fusion Live Two-Hole Mounting Bracket Smoke Test", "sketches": [{"token": "sketch-1", "name": "Two-Hole Mounting Bracket Smoke Sketch", "plane": "xy"}], "bodies": [{"token": "body-1", "name": "Smoke Two-Hole Mounting Bracket", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.75}], "exports": []}}
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "two_hole_mounting_bracket",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.75",
            "--leg-thickness-cm",
            "0.5",
            "--hole-diameter-cm",
            "0.4",
            "--hole-center-x-cm",
            "0.25",
            "--hole-center-y-cm",
            "1.5",
            "--second-hole-center-x-cm",
            "1.5",
            "--second-hole-center-y-cm",
            "0.25",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert len([command for command, _ in recorded_commands if command == "draw_circle"]) == 2


def test_smoke_script_routes_two_hole_plate_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_two_hole_plate_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Two-Hole Plate Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Two-Hole Plate Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Two-Hole Plate Smoke Sketch", "plane": "xy"}}}
        if command == "draw_rectangle":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "rectangle_index": 0, "width_cm": 4.0, "height_cm": 2.0}}
        if command == "draw_circle":
            return {
                "ok": True,
                "result": {
                    "sketch_token": "sketch-1",
                    "circle_index": len([c for c, _ in recorded_commands if c == "draw_circle"]),
                    "center_x_cm": arguments["center_x_cm"],
                    "center_y_cm": arguments["center_y_cm"],
                    "radius_cm": 0.2,
                },
            }
        if command == "list_profiles":
            return {
                "ok": True,
                "result": {
                    "profiles": [
                        {"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0},
                        {"token": "profile-hole-1", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                        {"token": "profile-hole-2", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4},
                    ]
                },
            }
        if command == "extrude_profile":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Two-Hole Plate", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.4}}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Two-Hole Plate Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Two-Hole Plate Smoke Sketch", "plane": "xy"}],
                    "bodies": [{"token": "body-1", "name": "Smoke Two-Hole Plate", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.4}],
                    "exports": [],
                },
            }
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "two_hole_plate",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.4",
            "--hole-diameter-cm",
            "0.4",
            "--hole-center-y-cm",
            "1.0",
            "--edge-offset-x-cm",
            "0.75",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    draw_circles = [arguments for command, arguments in recorded_commands if command == "draw_circle"]
    assert len(draw_circles) == 2
    assert draw_circles[0]["center_x_cm"] == 0.75
    assert draw_circles[1]["center_x_cm"] == 3.25


def test_smoke_script_routes_slotted_mount_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_slotted_mount_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Slotted Mount Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Slotted Mount Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Slotted Mount Smoke Sketch", "plane": "xy"}}}
        if command == "draw_rectangle":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "rectangle_index": 0, "width_cm": 4.0, "height_cm": 2.0}}
        if command == "draw_slot":
            return {
                "ok": True,
                "result": {
                    "sketch_token": "sketch-1",
                    "slot_index": 1,
                    "center_x_cm": 2.0,
                    "center_y_cm": 1.0,
                    "length_cm": 1.5,
                    "width_cm": 0.5,
                },
            }
        if command == "list_profiles":
            return {
                "ok": True,
                "result": {
                    "profiles": [
                        {"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0},
                        {"token": "profile-slot", "kind": "profile", "width_cm": 1.5, "height_cm": 0.5},
                    ]
                },
            }
        if command == "extrude_profile":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Slotted Mount", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.4}}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Slotted Mount Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Slotted Mount Smoke Sketch", "plane": "xy"}],
                    "bodies": [{"token": "body-1", "name": "Smoke Slotted Mount", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.4}],
                    "exports": [],
                },
            }
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "slotted_mount",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.4",
            "--slot-length-cm",
            "1.5",
            "--slot-width-cm",
            "0.5",
            "--slot-center-x-cm",
            "2.0",
            "--slot-center-y-cm",
            "1.0",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    slot_arguments = next(arguments for command, arguments in recorded_commands if command == "draw_slot")
    assert slot_arguments["length_cm"] == 1.5
    assert slot_arguments["width_cm"] == 0.5


def test_smoke_script_routes_plate_with_hole_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_plate_with_hole_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Plate With Hole Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Plate With Hole Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch" and arguments["name"] == "Plate Sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Plate Sketch", "plane": "xy"}}}
        if command == "draw_rectangle":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "rectangle_index": 0, "width_cm": 3.0, "height_cm": 2.0}}
        if command == "list_profiles" and arguments["sketch_token"] == "sketch-1":
            return {"ok": True, "result": {"profiles": [{"token": "profile-outer", "kind": "profile", "width_cm": 3.0, "height_cm": 2.0}]}}
        if command == "extrude_profile" and arguments.get("operation") != "cut":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Plate", "width_cm": 3.0, "height_cm": 2.0, "thickness_cm": 0.5}}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Plate With Hole Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Plate Sketch", "plane": "xy"}],
                    "bodies": [{"token": "body-1", "name": "Smoke Plate", "width_cm": 3.0, "height_cm": 2.0, "thickness_cm": 0.5}],
                    "exports": [],
                },
            }
        if command == "create_sketch" and arguments["name"] == "Hole Sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-2", "name": "Hole Sketch", "plane": "xy"}}}
        if command == "draw_circle":
            return {"ok": True, "result": {"sketch_token": "sketch-2", "circle_index": 0, "center_x_cm": 1.0, "center_y_cm": 0.5, "radius_cm": 0.2}}
        if command == "list_profiles" and arguments["sketch_token"] == "sketch-2":
            return {"ok": True, "result": {"profiles": [{"token": "profile-hole", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4}]}}
        if command == "extrude_profile" and arguments.get("operation") == "cut":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Plate", "width_cm": 3.0, "height_cm": 2.0, "thickness_cm": 0.5, "operation": "cut"}}}
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "plate_with_hole",
            "--plane",
            "xy",
            "--width-cm",
            "3.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.5",
            "--hole-diameter-cm",
            "0.4",
            "--hole-center-x-cm",
            "1.0",
            "--hole-center-y-cm",
            "0.5",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    cut_arguments = next(arguments for command, arguments in recorded_commands if command == "extrude_profile" and arguments.get("operation") == "cut")
    assert cut_arguments["distance_cm"] == 0.5


def test_smoke_script_routes_counterbored_plate_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_counterbored_plate_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Counterbored Plate Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Counterbored Plate Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch" and arguments["name"] == "Counterbored Plate Sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Counterbored Plate Sketch", "plane": "xy"}}}
        if command == "draw_rectangle":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "rectangle_index": 0, "width_cm": 4.0, "height_cm": 2.5}}
        if command == "list_profiles" and arguments["sketch_token"] == "sketch-1":
            return {"ok": True, "result": {"profiles": [{"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 2.5}]}}
        if command == "extrude_profile" and arguments.get("operation") != "cut":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Counterbored Plate", "width_cm": 4.0, "height_cm": 2.5, "thickness_cm": 0.5}}}
        if command == "create_sketch" and arguments["name"] == "Hole Sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-2", "name": "Hole Sketch", "plane": "xy"}}}
        if command == "create_sketch" and arguments["name"] == "Counterbore Sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-3", "name": "Counterbore Sketch", "plane": "xy"}}}
        if command == "draw_circle" and arguments["sketch_token"] == "sketch-2":
            return {"ok": True, "result": {"sketch_token": "sketch-2", "circle_index": 0, "center_x_cm": 2.0, "center_y_cm": 1.25, "radius_cm": 0.2}}
        if command == "draw_circle" and arguments["sketch_token"] == "sketch-3":
            return {"ok": True, "result": {"sketch_token": "sketch-3", "circle_index": 0, "center_x_cm": 2.0, "center_y_cm": 1.25, "radius_cm": 0.4}}
        if command == "list_profiles" and arguments["sketch_token"] == "sketch-2":
            return {"ok": True, "result": {"profiles": [{"token": "profile-hole", "kind": "profile", "width_cm": 0.4, "height_cm": 0.4}]}}
        if command == "list_profiles" and arguments["sketch_token"] == "sketch-3":
            return {"ok": True, "result": {"profiles": [{"token": "profile-counterbore", "kind": "profile", "width_cm": 0.8, "height_cm": 0.8}]}}
        if command == "extrude_profile" and arguments.get("operation") == "cut":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Counterbored Plate", "width_cm": 4.0, "height_cm": 2.5, "thickness_cm": 0.5, "operation": "cut"}}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Counterbored Plate Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Counterbored Plate Sketch", "plane": "xy"}],
                    "bodies": [{"token": "body-1", "name": "Smoke Counterbored Plate", "width_cm": 4.0, "height_cm": 2.5, "thickness_cm": 0.5}],
                    "exports": [],
                },
            }
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "counterbored_plate",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.5",
            "--thickness-cm",
            "0.5",
            "--hole-diameter-cm",
            "0.4",
            "--hole-center-x-cm",
            "2.0",
            "--hole-center-y-cm",
            "1.25",
            "--counterbore-diameter-cm",
            "0.8",
            "--counterbore-depth-cm",
            "0.2",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    cut_commands = [arguments for command, arguments in recorded_commands if command == "extrude_profile" and arguments.get("operation") == "cut"]
    assert len(cut_commands) == 2
    assert cut_commands[0]["distance_cm"] == 0.5
    assert cut_commands[1]["distance_cm"] == 0.2


def test_smoke_script_routes_recessed_mount_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_recessed_mount_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Recessed Mount Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Recessed Mount Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch" and arguments["name"] == "Recessed Mount Sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Recessed Mount Sketch", "plane": "xy"}}}
        if command == "draw_rectangle":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "rectangle_index": 0, "width_cm": 4.0, "height_cm": 2.5}}
        if command == "list_profiles" and arguments["sketch_token"] == "sketch-1":
            return {"ok": True, "result": {"profiles": [{"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 2.5}]}}
        if command == "extrude_profile" and arguments.get("operation") != "cut":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Recessed Mount", "width_cm": 4.0, "height_cm": 2.5, "thickness_cm": 0.5}}}
        if command == "create_sketch" and arguments["name"] == "Recess Sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-2", "name": "Recess Sketch", "plane": "xy"}}}
        if command == "draw_rectangle_at":
            return {"ok": True, "result": {"sketch_token": "sketch-2", "rectangle_index": 0, "origin_x_cm": 1.0, "origin_y_cm": 0.75, "width_cm": 2.0, "height_cm": 1.0}}
        if command == "list_profiles" and arguments["sketch_token"] == "sketch-2":
            return {"ok": True, "result": {"profiles": [{"token": "profile-recess", "kind": "profile", "width_cm": 2.0, "height_cm": 1.0}]}}
        if command == "extrude_profile" and arguments.get("operation") == "cut":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Recessed Mount", "width_cm": 4.0, "height_cm": 2.5, "thickness_cm": 0.5, "operation": "cut"}}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Recessed Mount Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Recessed Mount Sketch", "plane": "xy"}],
                    "bodies": [{"token": "body-1", "name": "Smoke Recessed Mount", "width_cm": 4.0, "height_cm": 2.5, "thickness_cm": 0.5}],
                    "exports": [],
                },
            }
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "recessed_mount",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.5",
            "--thickness-cm",
            "0.5",
            "--recess-width-cm",
            "2.0",
            "--recess-height-cm",
            "1.0",
            "--recess-depth-cm",
            "0.2",
            "--recess-origin-x-cm",
            "1.0",
            "--recess-origin-y-cm",
            "0.75",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    recess_arguments = next(arguments for command, arguments in recorded_commands if command == "draw_rectangle_at")
    assert recess_arguments["origin_x_cm"] == 1.0
    assert recess_arguments["origin_y_cm"] == 0.75


def test_smoke_script_routes_open_box_body_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_open_box_body_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Open Box Body Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Open Box Body Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch" and arguments["name"] == "Open Box Body Sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Open Box Body Sketch", "plane": "xy"}}}
        if command == "draw_rectangle":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "rectangle_index": 0, "width_cm": 4.0, "height_cm": 3.0}}
        if command == "list_profiles" and arguments["sketch_token"] == "sketch-1":
            return {"ok": True, "result": {"profiles": [{"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 3.0}]}}
        if command == "extrude_profile" and arguments.get("operation") != "cut":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Open Box Body", "width_cm": 4.0, "height_cm": 3.0, "thickness_cm": 2.0}}}
        if command == "create_sketch" and arguments["name"] == "Cavity Sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-2", "name": "Cavity Sketch", "plane": "xy", "offset_cm": 0.4}}}
        if command == "draw_rectangle_at":
            return {"ok": True, "result": {"sketch_token": "sketch-2", "rectangle_index": 0, "origin_x_cm": 0.3, "origin_y_cm": 0.3, "width_cm": 3.4, "height_cm": 2.4}}
        if command == "list_profiles" and arguments["sketch_token"] == "sketch-2":
            return {"ok": True, "result": {"profiles": [{"token": "profile-cavity", "kind": "profile", "width_cm": 3.4, "height_cm": 2.4}]}}
        if command == "extrude_profile" and arguments.get("operation") == "cut":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Open Box Body", "width_cm": 4.0, "height_cm": 3.0, "thickness_cm": 2.0, "operation": "cut"}}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            cavity_started = any(
                recorded_command == "create_sketch" and recorded_arguments.get("name") == "Cavity Sketch"
                for recorded_command, recorded_arguments in recorded_commands[:-1]
            )
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Open Box Body Smoke Test",
                    "sketches": (
                        [
                            {"token": "sketch-1", "name": "Open Box Body Sketch", "plane": "xy"},
                            {"token": "sketch-2", "name": "Cavity Sketch", "plane": "xy"},
                        ]
                        if cavity_started
                        else [{"token": "sketch-1", "name": "Open Box Body Sketch", "plane": "xy"}]
                    ),
                    "bodies": [{"token": "body-1", "name": "Smoke Open Box Body", "width_cm": 4.0, "height_cm": 3.0, "thickness_cm": 2.0}],
                    "exports": [],
                },
            }
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "open_box_body",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--depth-cm",
            "3.0",
            "--box-height-cm",
            "2.0",
            "--wall-thickness-cm",
            "0.3",
            "--floor-thickness-cm",
            "0.4",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    cavity_sketch_arguments = next(
        arguments
        for command, arguments in recorded_commands
        if command == "create_sketch" and arguments["name"] == "Cavity Sketch"
    )
    assert cavity_sketch_arguments["offset_cm"] == 0.4
    cavity_cut_arguments = next(
        arguments
        for command, arguments in recorded_commands
        if command == "extrude_profile" and arguments.get("operation") == "cut"
    )
    assert cavity_cut_arguments["distance_cm"] == 1.6


def test_smoke_script_routes_filleted_bracket_workflow(monkeypatch) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_filleted_bracket_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    recorded_commands: list[tuple[str, dict]] = []

    def fake_health(base_url: str) -> dict:
        return {"ok": True, "mode": "live", "status": "ready"}

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        recorded_commands.append((command, arguments))
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Filleted Bracket Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Filleted Bracket Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Filleted Bracket Smoke Sketch", "plane": "xy"}}}
        if command == "draw_l_bracket_profile":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "profile_index": 0, "width_cm": 4.0, "height_cm": 2.0, "leg_thickness_cm": 0.5}}
        if command == "list_profiles":
            return {"ok": True, "result": {"profiles": [{"token": "profile-1", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0}]}}
        if command == "extrude_profile":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Filleted Bracket", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.75}}}
        if command == "apply_fillet":
            return {"ok": True, "result": {"fillet": {"body_token": "body-1", "radius_cm": 0.2, "edge_count": 1, "fillet_applied": True}}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Filleted Bracket Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Filleted Bracket Smoke Sketch", "plane": "xy"}],
                    "bodies": [{"token": "body-1", "name": "Smoke Filleted Bracket", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.75}],
                    "exports": [],
                },
            }
        if command == "export_stl":
            assert Path(arguments["output_path"]) == output_path.resolve(strict=False)
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_health", fake_health)
    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "filleted_bracket",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.75",
            "--leg-thickness-cm",
            "0.5",
            "--fillet-radius-cm",
            "0.2",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 0
    fillet_arguments = next(arguments for command, arguments in recorded_commands if command == "apply_fillet")
    assert fillet_arguments["body_token"] == "body-1"
    assert fillet_arguments["radius_cm"] == 0.2


def test_smoke_script_fails_when_filleted_bracket_edge_selection_is_too_broad(monkeypatch, capsys) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_filleted_bracket_bad_edges_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)
    monkeypatch.setattr(smoke_test, "_health", lambda base_url: {"ok": True, "mode": "live", "status": "ready"})

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Filleted Bracket Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Filleted Bracket Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Filleted Bracket Smoke Sketch", "plane": "xy"}}}
        if command == "draw_l_bracket_profile":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "profile_index": 0, "width_cm": 4.0, "height_cm": 2.0, "leg_thickness_cm": 0.5}}
        if command == "list_profiles":
            return {"ok": True, "result": {"profiles": [{"token": "profile-1", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0}]}}
        if command == "extrude_profile":
            return {"ok": True, "result": {"body": {"token": "body-1", "name": "Smoke Filleted Bracket", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.75}}}
        if command == "apply_fillet":
            return {"ok": True, "result": {"fillet": {"body_token": "body-1", "radius_cm": 0.2, "edge_count": 6, "fillet_applied": True}}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Filleted Bracket Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Filleted Bracket Smoke Sketch", "plane": "xy"}],
                    "bodies": [{"token": "body-1", "name": "Smoke Filleted Bracket", "width_cm": 4.0, "height_cm": 2.0, "thickness_cm": 0.75}],
                    "exports": [],
                },
            }
        if command == "export_stl":
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "filleted_bracket",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.75",
            "--leg-thickness-cm",
            "0.5",
            "--fillet-radius-cm",
            "0.2",
            "--output-path",
            str(output_path),
        ]
    )

    assert exit_code == 1
    assert "fillet.edge_count mismatch" in capsys.readouterr().out


def test_smoke_script_fails_when_mounting_bracket_hole_profiles_do_not_match(monkeypatch, capsys) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_mounting_bracket_bad_holes_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)
    monkeypatch.setattr(smoke_test, "_health", lambda base_url: {"ok": True, "mode": "live", "status": "ready"})

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Mounting Bracket Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {"ok": True, "result": {"design_name": "Fusion Live Mounting Bracket Smoke Test", "sketches": [], "bodies": [], "exports": []}}
        if command == "create_sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Mounting Bracket Smoke Sketch", "plane": "xy"}}}
        if command == "draw_l_bracket_profile":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "profile_index": 0, "width_cm": 4.0, "height_cm": 2.0, "leg_thickness_cm": 0.5}}
        if command == "draw_circle":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "circle_index": 0, "center_x_cm": 0.25, "center_y_cm": 1.5, "radius_cm": 0.2}}
        if command == "list_profiles":
            return {
                "ok": True,
                "result": {
                    "profiles": [
                        {"token": "profile-outer", "kind": "profile", "width_cm": 4.0, "height_cm": 2.0},
                    ]
                },
            }
        raise AssertionError(f"Unexpected command: {command} with {arguments}")

    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(
        [
            "--workflow",
            "mounting_bracket",
            "--plane",
            "xy",
            "--width-cm",
            "4.0",
            "--height-cm",
            "2.0",
            "--thickness-cm",
            "0.75",
            "--leg-thickness-cm",
            "0.5",
            "--hole-diameter-cm",
            "0.4",
            "--hole-center-x-cm",
            "0.25",
            "--hole-center-y-cm",
            "1.5",
            "--output-path",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Expected exactly 1 hole profile matches" in captured.out


def test_smoke_script_fails_when_scene_geometry_does_not_match(monkeypatch, capsys) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_bad_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    monkeypatch.setattr(smoke_test, "_health", lambda base_url: {"ok": True, "mode": "live", "status": "ready"})

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {
                "ok": True,
                "result": {"design_name": "Fusion Live Smoke Test", "sketches": [], "bodies": [], "exports": []},
            }
        if command == "create_sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Smoke Sketch", "plane": "yz"}}}
        if command == "draw_rectangle":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "rectangle_index": 0, "width_cm": 2.0, "height_cm": 1.0}}
        if command == "list_profiles":
            return {"ok": True, "result": {"profiles": [{"token": "profile-1", "kind": "profile", "width_cm": 2.0, "height_cm": 1.0}]}}
        if command == "extrude_profile":
            return {
                "ok": True,
                "result": {"body": {"token": "body-1", "name": "Smoke Spacer", "width_cm": 2.0, "height_cm": 1.0, "thickness_cm": 0.5}},
            }
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Smoke Sketch", "plane": "xy"}],
                    "bodies": [{"token": "body-1", "name": "Smoke Spacer", "width_cm": 2.0, "height_cm": 1.0, "thickness_cm": 0.5}],
                    "exports": [],
                },
            }
        if command == "export_stl":
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(["--plane", "yz", "--output-path", str(output_path)])

    assert exit_code == 1
    assert "Sketch plane mismatch" in capsys.readouterr().out


def test_smoke_script_fails_when_profile_geometry_does_not_match(monkeypatch, capsys) -> None:
    output_path = Path.cwd() / "manual_test_output" / "smoke_bad_profile_test.stl"
    monkeypatch.setattr(smoke_test.Path, "mkdir", lambda self, parents=False, exist_ok=False: None)
    monkeypatch.setattr(smoke_test, "_health", lambda base_url: {"ok": True, "mode": "live", "status": "ready"})

    def fake_send(base_url: str, command: str, arguments: dict) -> dict:
        if command == "new_design":
            return {"ok": True, "result": {"design_name": "Fusion Live Smoke Test"}}
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_clean_state":
            return {
                "ok": True,
                "result": {"design_name": "Fusion Live Smoke Test", "sketches": [], "bodies": [], "exports": []},
            }
        if command == "create_sketch":
            return {"ok": True, "result": {"sketch": {"token": "sketch-1", "name": "Smoke Sketch", "plane": "xz"}}}
        if command == "draw_rectangle":
            return {"ok": True, "result": {"sketch_token": "sketch-1", "rectangle_index": 0, "width_cm": 2.0, "height_cm": 1.0}}
        if command == "list_profiles":
            return {"ok": True, "result": {"profiles": [{"token": "profile-1", "kind": "profile", "width_cm": 2.0, "height_cm": 0.0}]}}
        if command == "extrude_profile":
            return {
                "ok": True,
                "result": {"body": {"token": "body-1", "name": "Smoke Spacer", "width_cm": 2.0, "height_cm": 1.0, "thickness_cm": 0.5}},
            }
        if command == "get_scene_info" and arguments.get("workflow_stage") == "verify_geometry":
            return {
                "ok": True,
                "result": {
                    "design_name": "Fusion Live Smoke Test",
                    "sketches": [{"token": "sketch-1", "name": "Smoke Sketch", "plane": "xz"}],
                    "bodies": [{"token": "body-1", "name": "Smoke Spacer", "width_cm": 2.0, "height_cm": 1.0, "thickness_cm": 0.5}],
                    "exports": [],
                },
            }
        if command == "export_stl":
            return {"ok": True, "result": {"body_token": "body-1", "output_path": str(output_path.resolve(strict=False))}}
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(smoke_test, "_send", fake_send)

    exit_code = smoke_test.main(["--plane", "xz", "--output-path", str(output_path)])

    assert exit_code == 1
    assert "profile.height_cm mismatch" in capsys.readouterr().out
