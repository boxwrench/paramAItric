from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.bridge_client import BridgeClient
from mcp_server.schemas import CommandEnvelope, CreateSpacerInput


def test_create_spacer_requires_positive_dimensions(tmp_path) -> None:
    with pytest.raises(ValueError):
        CreateSpacerInput.from_payload(
            {
                "width_cm": 0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(tmp_path / "bad.stl"),
            }
        )


def test_bridge_reports_missing_server() -> None:
    client = BridgeClient("http://127.0.0.1:1")
    with pytest.raises(RuntimeError, match="not reachable"):
        client.health()


def test_command_requires_name() -> None:
    with pytest.raises(ValueError):
        CommandEnvelope.build("", {})


def test_create_spacer_rejects_output_path_outside_allowlist() -> None:
    outside = Path.cwd().parent / "outside.stl"
    with pytest.raises(ValueError, match="allowlisted"):
        CreateSpacerInput.from_payload(
            {
                "width_cm": 1.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(outside),
            }
        )
