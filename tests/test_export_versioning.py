"""Export filename auto-versioning tests.

Covers mcp_server.schemas._next_available_versioned_path (the pure
disk-state-driven algorithm) and its wiring into
mcp_server.schemas._validate_export_path, which must:
- version filenames for real, user-visible export locations (Desktop,
  Downloads, the default "ParamAItric Exports" folder) so a reprint never
  clobbers a prior export, and
- leave internal test-fixture paths (manual_test_output, the OS tempdir)
  untouched, since many tests intentionally overwrite fixed filenames on
  every run.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir

from mcp_server.schemas import (
    CreateSpacerInput,
    _next_available_versioned_path,
    _validate_export_path,
)


def _payload(output_path: str) -> dict:
    return {
        "width_cm": 1.0,
        "height_cm": 1.0,
        "thickness_cm": 0.5,
        "output_path": output_path,
    }


def _best_effort_unlink(*paths: Path) -> None:
    """Clean up test-created files without failing the test on odd sandbox
    filesystem permissions that block deletion of freshly created files."""
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# _next_available_versioned_path -- pure function, no allowlist involved
# ---------------------------------------------------------------------------

def test_returns_path_unchanged_when_free(tmp_path) -> None:
    target = tmp_path / "bracket.stl"
    assert _next_available_versioned_path(target) == target


def test_versions_to_v2_when_original_exists(tmp_path) -> None:
    target = tmp_path / "bracket.stl"
    target.write_text("x")
    assert _next_available_versioned_path(target) == tmp_path / "bracket_v2.stl"


def test_versions_increment_past_v2(tmp_path) -> None:
    (tmp_path / "bracket.stl").write_text("x")
    (tmp_path / "bracket_v2.stl").write_text("x")
    result = _next_available_versioned_path(tmp_path / "bracket.stl")
    assert result == tmp_path / "bracket_v3.stl"


def test_versions_skip_past_multiple_existing_versions(tmp_path) -> None:
    (tmp_path / "bracket.stl").write_text("x")
    (tmp_path / "bracket_v2.stl").write_text("x")
    (tmp_path / "bracket_v3.stl").write_text("x")
    (tmp_path / "bracket_v4.stl").write_text("x")
    result = _next_available_versioned_path(tmp_path / "bracket.stl")
    assert result == tmp_path / "bracket_v5.stl"


def test_already_versioned_name_increments_in_place(tmp_path) -> None:
    """bracket_v2.stl colliding becomes bracket_v3.stl, not bracket_v2_v2.stl."""
    (tmp_path / "bracket_v2.stl").write_text("x")
    result = _next_available_versioned_path(tmp_path / "bracket_v2.stl")
    assert result == tmp_path / "bracket_v3.stl"


def test_already_versioned_name_skips_existing_higher_versions(tmp_path) -> None:
    (tmp_path / "bracket_v2.stl").write_text("x")
    (tmp_path / "bracket_v3.stl").write_text("x")
    result = _next_available_versioned_path(tmp_path / "bracket_v2.stl")
    assert result == tmp_path / "bracket_v4.stl"


def test_versioning_works_for_any_extension(tmp_path) -> None:
    (tmp_path / "part.step").write_text("x")
    result = _next_available_versioned_path(tmp_path / "part.step")
    assert result == tmp_path / "part_v2.step"


# ---------------------------------------------------------------------------
# Integration through _validate_export_path / CreateSpacerInput
# ---------------------------------------------------------------------------

def test_validate_export_path_versions_existing_desktop_file() -> None:
    desktop = Path.home() / "Desktop"
    original = desktop / "paramaitric_versioning_test_case.stl"
    versioned = desktop / "paramaitric_versioning_test_case_v2.stl"
    try:
        desktop.mkdir(parents=True, exist_ok=True)
        original.write_text("x")
        result = _validate_export_path(str(original))
        assert result == str(versioned)
    finally:
        _best_effort_unlink(original, versioned)


def test_validate_export_path_returns_original_when_desktop_file_absent() -> None:
    desktop = Path.home() / "Desktop"
    original = desktop / "paramaitric_versioning_absent_case.stl"
    _best_effort_unlink(original)
    result = _validate_export_path(str(original))
    assert result == str(original)


def test_validate_export_path_leaves_manual_test_output_unversioned() -> None:
    """Internal test fixtures intentionally keep overwrite-on-rerun semantics."""
    path = Path.cwd() / "manual_test_output" / "paramaitric_versioning_manual_test.stl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
        result = _validate_export_path(str(path))
        assert result == str(path)
    finally:
        _best_effort_unlink(path)


def test_validate_export_path_leaves_tempdir_unversioned() -> None:
    scratch = Path(gettempdir()) / "paramaitric_versioning_tempdir_test.stl"
    try:
        scratch.write_text("x")
        result = _validate_export_path(str(scratch))
        assert result == str(scratch)
    finally:
        _best_effort_unlink(scratch)


def test_create_spacer_input_versions_output_path_end_to_end() -> None:
    desktop = Path.home() / "Desktop"
    original = desktop / "paramaitric_versioning_spacer_case.stl"
    versioned = desktop / "paramaitric_versioning_spacer_case_v2.stl"
    try:
        desktop.mkdir(parents=True, exist_ok=True)
        original.write_text("x")
        spec = CreateSpacerInput.from_payload(_payload(str(original)))
        assert spec.output_path == str(versioned)
    finally:
        _best_effort_unlink(original, versioned)
