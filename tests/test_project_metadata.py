from __future__ import annotations

import tomllib
from pathlib import Path

from mcp_server import mcp_entrypoint


ROOT = Path(__file__).resolve().parents[1]


def test_project_metadata_points_to_readme_repository_and_entrypoint() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project["readme"] == "README.md"
    assert project["urls"]["Repository"] == "https://github.com/boxwrench/paramAItric"
    assert project["urls"]["Issues"] == "https://github.com/boxwrench/paramAItric/issues"
    assert project["scripts"]["paramaitric"] == "mcp_server.mcp_entrypoint:main"


def test_console_entrypoint_runs_mcp_server(monkeypatch) -> None:
    calls: list[None] = []
    monkeypatch.setattr(mcp_entrypoint.mcp, "run", lambda: calls.append(None))

    result = mcp_entrypoint.main()

    assert result is None
    assert calls == [None]
