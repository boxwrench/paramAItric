"""Open-folder hand-off tests for mcp_server.mcp_entrypoint._attach_export_summary.

After a workflow exports a file, the host AI needs to know where it landed
and how to open that folder for the user (without this process ever
spawning that command itself).
"""
from __future__ import annotations

from mcp_server.mcp_entrypoint import _attach_export_summary, _open_folder_commands


def test_open_folder_commands_shape() -> None:
    commands = _open_folder_commands("/tmp/exports")
    assert commands == {
        "windows": 'explorer "/tmp/exports"',
        "macos": 'open "/tmp/exports"',
        "linux": 'xdg-open "/tmp/exports"',
    }


def test_attach_export_summary_adds_folder_and_open_commands() -> None:
    result = {"ok": True, "export": {"path": "/home/user/Desktop/bracket.stl"}}
    summary = _attach_export_summary(result)

    assert summary["export_folders"] == ["/home/user/Desktop"]
    assert summary["open_folder_commands"]["/home/user/Desktop"] == {
        "windows": 'explorer "/home/user/Desktop"',
        "macos": 'open "/home/user/Desktop"',
        "linux": 'xdg-open "/home/user/Desktop"',
    }
    assert "open_folder_note" in summary
    assert "user_next_step" in summary


def test_attach_export_summary_handles_multiple_export_folders() -> None:
    result = {
        "ok": True,
        "exports": {
            "box": "/home/user/exports/a/box.stl",
            "lid": "/home/user/exports/b/lid.stl",
        },
    }
    summary = _attach_export_summary(result)
    assert summary["export_folders"] == ["/home/user/exports/a", "/home/user/exports/b"]
    assert set(summary["open_folder_commands"].keys()) == set(summary["export_folders"])


def test_attach_export_summary_is_noop_without_exports() -> None:
    result = {"ok": True, "message": "no export happened"}
    summary = _attach_export_summary(result)
    assert "export_folders" not in summary
    assert "open_folder_commands" not in summary
    assert "open_folder_note" not in summary


def test_attach_export_summary_is_noop_on_error_result() -> None:
    result = {"ok": False, "error": {"code": "bad"}}
    summary = _attach_export_summary(result)
    assert summary == result
    assert "export_folders" not in summary


def test_attach_export_summary_does_not_overwrite_existing_keys() -> None:
    result = {
        "ok": True,
        "export": {"path": "/home/user/Desktop/bracket.stl"},
        "export_folders": ["already-set"],
    }
    summary = _attach_export_summary(result)
    assert summary["export_folders"] == ["already-set"]
