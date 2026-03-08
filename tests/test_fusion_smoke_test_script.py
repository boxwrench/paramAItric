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
