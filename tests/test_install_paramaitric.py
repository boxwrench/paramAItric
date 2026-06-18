from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


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

    dashboard = install_helper.render_dashboard(root, install_helper.run_checks(root))

    assert "ParamAItric setup" in dashboard
    assert "Local checks" in dashboard
    assert "Claude Desktop config snippet" in dashboard
    assert '"mcpServers"' in dashboard
    assert "Cursor command" in dashboard
    assert str(root / "fusion_addin") in dashboard
