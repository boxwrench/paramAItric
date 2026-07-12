from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
import pytest
import anyio

import mcp_server.mcp_entrypoint
import mcp_server.runtime_info as runtime_info
from mcp_server.schemas import default_exports_dir


@pytest.fixture(autouse=True)
def cleanup_mcp_entrypoint(monkeypatch):
    # Backup sys.argv
    old_argv = list(sys.argv)
    yield
    # Restore environment, sys.argv, and reload
    monkeypatch.delenv("PARAMAITRIC_PROFILE", raising=False)
    sys.argv = old_argv
    importlib.reload(runtime_info)
    importlib.reload(mcp_server.mcp_entrypoint)


def test_no_profile_activation() -> None:
    # Reload with no profile
    importlib.reload(runtime_info)
    importlib.reload(mcp_server.mcp_entrypoint)

    assert runtime_info.ACTIVE_PROFILE_NAME is None
    assert runtime_info.ACTIVE_PROFILE_EXPORT_DIR is None
    assert "create_cylinder" in mcp_server.mcp_entrypoint.registered_tools


def test_profile_activation_via_env(monkeypatch) -> None:
    monkeypatch.setenv("PARAMAITRIC_PROFILE", "lemonade-cuda-fusion")
    importlib.reload(runtime_info)
    importlib.reload(mcp_server.mcp_entrypoint)

    assert runtime_info.ACTIVE_PROFILE_NAME == "lemonade-cuda-fusion"
    assert runtime_info.ACTIVE_PROFILE_EXPORT_DIR is not None
    assert default_exports_dir() == Path(runtime_info.ACTIVE_PROFILE_EXPORT_DIR)

    # Gated tools
    tools = anyio.run(mcp_server.mcp_entrypoint.mcp.list_tools)
    registered_names = {tool.name for tool in tools}
    expected_names = {"health", "recommend_workflow", "workflow_catalog", "create_spacer", "list_design_bodies"}
    assert registered_names == expected_names


def test_profile_activation_via_cli(monkeypatch) -> None:
    sys.argv = [sys.argv[0], "--profile", "claude-fusion"]
    importlib.reload(runtime_info)
    importlib.reload(mcp_server.mcp_entrypoint)

    assert runtime_info.ACTIVE_PROFILE_NAME == "claude-fusion"
    # full profile should register all tools
    assert "create_cylinder" in mcp_server.mcp_entrypoint.registered_tools
    assert "--profile" not in sys.argv


def test_invalid_profile_fails_fast(monkeypatch) -> None:
    monkeypatch.setenv("PARAMAITRIC_PROFILE", "nonexistent-profile-xyz")
    importlib.reload(runtime_info)
    with pytest.raises(SystemExit) as excinfo:
        importlib.reload(mcp_server.mcp_entrypoint)
    assert excinfo.value.code == 1


def test_health_surfaces_active_profile(monkeypatch) -> None:
    monkeypatch.setenv("PARAMAITRIC_PROFILE", "claude-fusion")
    importlib.reload(runtime_info)
    importlib.reload(mcp_server.mcp_entrypoint)

    server = mcp_server.mcp_entrypoint._server
    res = server.health()
    assert res.get("active_profile") == "claude-fusion"
