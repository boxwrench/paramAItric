from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.runtime_profiles import RuntimeProfile
from mcp_server.doctor import (
    Check,
    check_python_env,
    check_package_import,
    check_mcp_startup,
    check_lemonade,
    check_cad_backend,
    check_bridge_auth,
    check_export_directory,
    check_cad_health_call,
    run_doctor,
)


def test_check_python_env() -> None:
    check = check_python_env()
    assert check.label == "Python version"
    assert check.status == "ok"


def test_check_package_import() -> None:
    check = check_package_import()
    assert check.label == "Package import"
    assert check.status == "ok"


@patch("subprocess.run")
def test_check_mcp_startup_success(mock_run: MagicMock) -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=Path("~/exports"),
    )
    stdout_json = json.dumps({
        "active_profile": "claude-fusion",
        "registered_tools": ["create_spacer"],
        "active_export_directory": str(Path("~/exports"))
    })
    mock_run.return_value = MagicMock(returncode=0, stdout=stdout_json)
    checks = check_mcp_startup(profile)
    assert len(checks) == 3
    assert all(c.status == "ok" for c in checks)


@patch("subprocess.run")
def test_check_mcp_startup_failure(mock_run: MagicMock) -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=Path("~/exports"),
    )
    mock_run.return_value = MagicMock(returncode=1, stderr="ImportError: missing module")
    checks = check_mcp_startup(profile)
    assert len(checks) == 1
    assert checks[0].status == "fail"
    assert "missing module" in checks[0].detail


def test_check_lemonade_claude_profile() -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    checks = check_lemonade(profile)
    assert len(checks) == 1
    assert checks[0].status == "ok"
    assert "Cloud provider" in checks[0].detail


@patch("urllib.request.urlopen")
def test_check_lemonade_success(mock_urlopen: MagicMock) -> None:
    profile = RuntimeProfile(
        profile="lemonade-cuda-fusion",
        agent="pi",
        model_provider="lemonade",
        model_endpoint="http://127.0.0.1:13305/api/v1",
        model="Qwen3.5-9B-GGUF",
        inference_backend="cuda",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="guided",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "data": [{"id": "Qwen3.5-9B-GGUF"}, {"id": "other-model"}]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    checks = check_lemonade(profile)
    assert len(checks) == 2
    assert checks[0].status == "ok"
    assert checks[1].status == "ok"
    assert "available on the server" in checks[1].detail


@patch("urllib.request.urlopen")
def test_check_lemonade_model_missing(mock_urlopen: MagicMock) -> None:
    profile = RuntimeProfile(
        profile="lemonade-cuda-fusion",
        agent="pi",
        model_provider="lemonade",
        model_endpoint="http://127.0.0.1:13305/api/v1",
        model="Qwen3.5-9B-GGUF",
        inference_backend="cuda",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="guided",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "data": [{"id": "some-other-model"}]
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    checks = check_lemonade(profile)
    assert len(checks) == 2
    assert checks[0].status == "ok"
    assert checks[1].status == "fail"
    assert "not available on the server" in checks[1].detail


@patch("urllib.request.urlopen")
def test_check_lemonade_unreachable(mock_urlopen: MagicMock) -> None:
    profile = RuntimeProfile(
        profile="lemonade-cuda-fusion",
        agent="pi",
        model_provider="lemonade",
        model_endpoint="http://127.0.0.1:13305/api/v1",
        model="Qwen3.5-9B-GGUF",
        inference_backend="cuda",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="guided",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    
    mock_urlopen.side_effect = Exception("Connection refused")

    checks = check_lemonade(profile)
    assert len(checks) == 2
    assert checks[0].status == "fail"
    assert checks[1].status == "fail"


@patch("urllib.request.urlopen")
def test_check_cad_backend_success(mock_urlopen: MagicMock) -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "backend": "autodesk_fusion",
        "mode": "live",
        "status": "ready"
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    check = check_cad_backend(profile)
    assert check.status == "ok"
    assert "mode: live" in check.detail


@patch("urllib.request.urlopen")
def test_check_cad_backend_mock(mock_urlopen: MagicMock) -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "backend": "autodesk_fusion",
        "mode": "mock",
        "status": "ready"
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    check = check_cad_backend(profile)
    assert check.status == "warn"
    assert "practice mode" in check.detail
    assert "mock" in check.detail


@patch("urllib.request.urlopen")
def test_check_cad_backend_not_ready(mock_urlopen: MagicMock) -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "backend": "fusion",
        "mode": "live",
        "status": "initializing"
    }).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    check = check_cad_backend(profile)
    assert check.status == "fail"


@patch("urllib.request.urlopen")
def test_check_cad_backend_failure(mock_urlopen: MagicMock) -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    
    mock_urlopen.side_effect = Exception("HTTP 500")

    check = check_cad_backend(profile)
    assert check.status == "fail"
    assert "Fusion" in check.next_step


def test_check_cad_backend_freecad_failure() -> None:
    profile = RuntimeProfile(
        profile="lemonade-rocm-freecad",
        agent="pi",
        model_provider="lemonade",
        model_endpoint="http://127.0.0.1:13305/api/v1",
        model="Qwen3.5-9B-GGUF",
        inference_backend="rocm",
        cad_backend="freecad",
        cad_endpoint="http://127.0.0.1:8124",
        tool_profile="full",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = Exception("Connection refused")
        check = check_cad_backend(profile)
    
    assert check.status == "fail"
    assert "FreeCAD" in check.next_step


def test_check_bridge_auth_always_warns() -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=Path("~/Documents/ParamAItric Exports"),
    )
    check = check_bridge_auth(profile)
    assert check.status == "warn"
    assert "not configured" in check.detail


def test_check_export_directory_writable(tmp_path: Path) -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=tmp_path / "exports",
    )
    
    check = check_export_directory(profile)
    assert check.status == "ok"
    assert (tmp_path / "exports").exists()


@patch("mcp_server.doctor.load_runtime_profile")
@patch("mcp_server.doctor.check_mcp_startup")
@patch("urllib.request.urlopen")
def test_run_doctor_cli_success(mock_urlopen: MagicMock, mock_mcp: MagicMock, mock_load_profile: MagicMock, tmp_path: Path) -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=tmp_path / "exports",
    )
    mock_load_profile.return_value = profile
    mock_mcp.return_value = [Check("Active profile", "ok", "ok")]
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "backend": "autodesk_fusion",
        "mode": "live",
        "status": "ready",
        "version": "0.1.0",
        "workflow_count": 5
    }).encode("utf-8")
    mock_response.getcode.return_value = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    exit_code = run_doctor(["--profile", "claude-fusion"])
    assert exit_code == 0


@patch("mcp_server.doctor.load_runtime_profile")
@patch("mcp_server.doctor.check_mcp_startup")
@patch("urllib.request.urlopen")
def test_run_doctor_cli_warning_strict(mock_urlopen: MagicMock, mock_mcp: MagicMock, mock_load_profile: MagicMock, tmp_path: Path) -> None:
    profile = RuntimeProfile(
        profile="claude-fusion",
        agent="claude",
        model_provider="claude",
        model_endpoint=None,
        model=None,
        inference_backend="cloud",
        cad_backend="fusion",
        cad_endpoint="http://127.0.0.1:8123",
        tool_profile="full",
        export_directory=tmp_path / "exports",
    )
    mock_load_profile.return_value = profile
    mock_mcp.return_value = [Check("Active profile", "ok", "ok")]
    
    mock_response = MagicMock()
    # Mock CAD mode returns warning when mode is mock
    mock_response.read.return_value = json.dumps({
        "backend": "autodesk_fusion",
        "mode": "mock",
        "status": "ready",
        "version": "0.1.0",
        "workflow_count": 5
    }).encode("utf-8")
    mock_response.getcode.return_value = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Non-strict mode should return exit code 0
    exit_code = run_doctor(["--profile", "claude-fusion"])
    assert exit_code == 0

    # Strict mode should return exit code 1 for warning
    exit_code_strict = run_doctor(["--profile", "claude-fusion", "--strict"])
    assert exit_code_strict == 1
