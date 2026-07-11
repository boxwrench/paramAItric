from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "install_paramaitric.py"
_SPEC = importlib.util.spec_from_file_location("paramaitric_install_helper", _SCRIPT_PATH)
install_helper = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
sys.modules[_SPEC.name] = install_helper
_SPEC.loader.exec_module(install_helper)


def test_build_claude_config_uses_absolute_checkout_paths(tmp_path):
    root = tmp_path / "paramAItric"
    root.mkdir()
    python_path = root / ".venv" / "bin" / "python"

    config = install_helper.build_claude_config(root, python_path=python_path)

    server = config["mcpServers"]["paramaitric"]
    assert server["command"] == str(python_path)
    assert server["args"] == ["-m", "mcp_server.mcp_entrypoint"]
    assert server["cwd"] == str(root)


def test_merge_claude_config_preserves_existing_servers(tmp_path):
    root = tmp_path / "paramAItric"
    python_path = root / ".venv" / "bin" / "python"
    existing = {
        "mcpServers": {
            "other": {
                "command": "python",
                "args": ["other.py"],
            }
        },
        "globalSetting": True,
    }

    merged = install_helper.merge_claude_config(existing, root, python_path=python_path)

    assert merged["globalSetting"] is True
    assert merged["mcpServers"]["other"] == existing["mcpServers"]["other"]
    assert merged["mcpServers"]["paramaitric"]["command"] == str(python_path)
    assert merged["mcpServers"]["paramaitric"]["cwd"] == str(root)


def test_write_claude_config_creates_parent_and_merges(tmp_path):
    root = tmp_path / "paramAItric"
    python_path = root / ".venv" / "bin" / "python"
    config_path = tmp_path / "Claude" / "claude_desktop_config.json"

    written = install_helper.write_claude_config(root, config_path, python_path=python_path)

    assert config_path.exists()
    assert written["mcpServers"]["paramaitric"]["command"] == str(python_path)
    assert '"paramaitric"' in config_path.read_text(encoding="utf-8")


def test_cursor_command_quotes_python_path(tmp_path):
    root = tmp_path / "Param With Spaces"
    python_path = root / ".venv" / "bin" / "python"

    command = install_helper.build_cursor_command(root, python_path=python_path)

    assert command == f'"{python_path}" -m mcp_server.mcp_entrypoint'


def test_default_venv_python_is_platform_specific(tmp_path):
    assert install_helper.default_venv_python(tmp_path, system="Windows") == (
        tmp_path / ".venv" / "Scripts" / "python.exe"
    )
    assert install_helper.default_venv_python(tmp_path, system="Linux") == (
        tmp_path / ".venv" / "bin" / "python"
    )


def test_dashboard_includes_checks_and_copy_paste_snippets(tmp_path):
    root = tmp_path / "paramAItric"
    (root / "fusion_addin").mkdir(parents=True)
    (root / "fusion_addin" / "FusionAIBridge.manifest").write_text("{}", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = 'paramaitric'\n", encoding="utf-8")

    dashboard = install_helper.render_dashboard(
        root, install_helper.run_checks(root, health_probe=lambda: None)
    )

    assert "ParamAItric setup" in dashboard
    assert "Local checks" in dashboard
    assert "Claude Desktop config snippet" in dashboard
    assert '"mcpServers"' in dashboard
    assert "Cursor command" in dashboard
    assert str(root / "fusion_addin") in dashboard


def test_main_check_returns_failure_for_bad_root(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(install_helper, "probe_bridge_health", lambda: None)
    code = install_helper.main(["--root", str(tmp_path / "missing"), "--check", "--no-color"])

    captured = capsys.readouterr()
    assert code == 1
    assert "[FAIL]" in captured.out


def test_main_check_returns_success_when_only_virtualenv_warns(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(install_helper, "probe_bridge_health", lambda: None)
    root = tmp_path / "paramAItric"
    (root / "fusion_addin").mkdir(parents=True)
    (root / "fusion_addin" / "FusionAIBridge.manifest").write_text("{}", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = 'paramaitric'\n", encoding="utf-8")

    code = install_helper.main(["--root", str(root), "--check", "--no-color"])

    captured = capsys.readouterr()
    assert code == 0
    assert "[WARN]" in captured.out


def test_bridge_health_check_distinguishes_live_mock_and_not_listening():
    live = install_helper.bridge_health_check({"ok": True, "mode": "live"})
    mock = install_helper.bridge_health_check({"ok": True, "mode": "mock"})
    offline = install_helper.bridge_health_check(None)

    assert (live.status, live.detail) == (
        "ok",
        "Fusion is connected and ready to build parts.",
    )
    assert mock.status == "warn"
    assert "practice mode" in mock.detail
    assert offline.status == "warn"
    assert "not listening" in offline.detail


def test_run_checks_accepts_an_injected_health_probe(tmp_path):
    root = tmp_path / "paramAItric"
    observed = []

    checks = install_helper.run_checks(
        root,
        health_probe=lambda: observed.append("called") or {"ok": True, "mode": "live"},
    )

    assert observed == ["called"]
    assert next(check for check in checks if check.label == "Fusion bridge").status == "ok"


def test_check_summary_explains_warning_in_plain_language():
    summary = install_helper.render_check_summary(
        [install_helper.bridge_health_check(None)], color=False
    )

    assert "The Fusion bridge is not listening yet." in summary
    assert "What to do: Open Fusion 360" in summary


@patch("mcp_server.doctor.run_doctor")
def test_main_routes_to_run_doctor_on_profile(mock_run_doctor):
    mock_run_doctor.return_value = 0
    code = install_helper.main(["--profile", "claude-fusion"])
    assert code == 0
    mock_run_doctor.assert_called_once_with(["--profile", "claude-fusion"])

