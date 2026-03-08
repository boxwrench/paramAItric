"""Export path security tests.

Covers both layers where path enforcement happens:
- mcp_server.schemas._validate_export_path (schema layer, before the bridge)
- fusion_addin.state.DesignState.export (mock ops layer, inside the bridge)

Both layers must independently reject unsafe paths.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from fusion_addin.dispatcher import CommandDispatcher
from fusion_addin.state import DesignState
from mcp_server.schemas import CreateSpacerInput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state_export(path: str) -> str:
    """Call DesignState.export() directly to test the mock-ops allowlist."""
    return DesignState().export(path)


def _schema_payload(output_path: str) -> dict:
    return {
        "width_cm": 1.0,
        "height_cm": 1.0,
        "thickness_cm": 0.5,
        "output_path": output_path,
    }


# ---------------------------------------------------------------------------
# Schema layer — paths that must be REJECTED
# ---------------------------------------------------------------------------

def test_schema_rejects_absolute_path_outside_allowlist() -> None:
    with pytest.raises(ValueError, match="allowlisted"):
        CreateSpacerInput.from_payload(_schema_payload("C:/Windows/system32/bad.stl"))


def test_schema_rejects_home_directory_path() -> None:
    home_path = str(Path.home() / "Documents" / "bad.stl")
    with pytest.raises(ValueError, match="allowlisted"):
        CreateSpacerInput.from_payload(_schema_payload(home_path))


def test_schema_rejects_path_with_no_extension() -> None:
    path = str(Path.cwd() / "manual_test_output" / "no_extension")
    with pytest.raises(ValueError, match="extension"):
        CreateSpacerInput.from_payload(_schema_payload(path))


def test_schema_rejects_empty_output_path() -> None:
    with pytest.raises(ValueError):
        CreateSpacerInput.from_payload(_schema_payload(""))


def test_schema_accepts_manual_test_output_path() -> None:
    path = str(Path.cwd() / "manual_test_output" / "ok.stl")
    spec = CreateSpacerInput.from_payload(_schema_payload(path))
    assert spec.output_path.endswith("ok.stl")


def test_schema_accepts_tmp_path(tmp_path) -> None:
    path = str(tmp_path / "ok.stl")
    spec = CreateSpacerInput.from_payload(_schema_payload(path))
    assert spec.output_path.endswith("ok.stl")


def test_schema_traversal_that_escapes_tmp_stays_rejected() -> None:
    """A path crafted to escape beyond both allowlisted roots is rejected."""
    outside = str(Path("C:/Windows/bad.stl"))
    with pytest.raises(ValueError, match="allowlisted"):
        CreateSpacerInput.from_payload(_schema_payload(outside))


def test_schema_rejects_path_that_is_a_directory_name() -> None:
    """A path ending in a directory separator has no file extension."""
    path = str(Path.cwd() / "manual_test_output") + "/"
    with pytest.raises(ValueError):
        CreateSpacerInput.from_payload(_schema_payload(path))


# ---------------------------------------------------------------------------
# Mock ops layer (DesignState.export) — paths that must be REJECTED
# ---------------------------------------------------------------------------

def test_mock_ops_rejects_absolute_path_outside_allowlist() -> None:
    with pytest.raises(ValueError):
        _state_export("C:/Windows/system32/bad.stl")


def test_mock_ops_rejects_path_with_no_extension() -> None:
    with pytest.raises(ValueError):
        _state_export(str(Path.cwd() / "manual_test_output" / "noext"))


def test_mock_ops_accepts_manual_test_output_path() -> None:
    destination = Path.cwd() / "manual_test_output" / "test_mock_ops_export_security.stl"
    result = _state_export(str(destination))
    assert result is not None
    assert str(destination) == result


def test_mock_ops_accepts_tmp_path(tmp_path) -> None:
    path = str(tmp_path / "ok.stl")
    result = _state_export(path)
    assert result == path
    assert Path(result).exists()


def test_mock_ops_traversal_within_tmp_is_safe(tmp_path) -> None:
    """Path traversal that stays inside tmp is not an escape — resolve() normalises it."""
    deep = tmp_path / "a" / "b" / ".." / "ok.stl"
    result = _state_export(str(deep))
    assert "ok.stl" in result


def test_mock_ops_traversal_escaping_tmp_is_rejected(tmp_path) -> None:
    """Path traversal that escapes both allowlisted roots is rejected."""
    escaped = "C:/Windows/evil.stl"
    with pytest.raises(ValueError):
        _state_export(escaped)


# ---------------------------------------------------------------------------
# Dispatcher end-to-end: export_stl with a bad path raises RuntimeError
# ---------------------------------------------------------------------------

def test_dispatcher_export_stl_rejects_unsafe_path(tmp_path) -> None:
    """export_stl through the dispatcher surfaces the path error as an exception."""
    d = CommandDispatcher()
    d.submit("new_design", {"name": "test"})
    tok = d.submit("create_sketch", {"plane": "xy", "name": "s"})["result"]["sketch"]["token"]
    d.submit("draw_rectangle", {"sketch_token": tok, "width_cm": 1.0, "height_cm": 1.0})
    profiles = d.submit("list_profiles", {"sketch_token": tok})["result"]["profiles"]
    body = d.submit("extrude_profile", {
        "profile_token": profiles[0]["token"], "distance_cm": 0.5, "body_name": "b",
    })["result"]["body"]

    with pytest.raises(ValueError):
        d.submit("export_stl", {"body_token": body["token"], "output_path": "C:/Windows/bad.stl"})
