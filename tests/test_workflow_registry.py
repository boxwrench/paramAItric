from __future__ import annotations

from mcp_server.workflows import build_default_registry


def test_workflow_registry_tracks_extension_paths() -> None:
    registry = build_default_registry()

    spacer = registry.get("spacer")
    bracket = registry.get("bracket")

    assert spacer.stages[0] == "new_design"
    assert "verify_geometry" in spacer.stages
    assert bracket.extension_of == ("spacer",)
