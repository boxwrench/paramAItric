from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server.runtime_profiles import (
    RuntimeProfileError,
    list_runtime_profiles,
    load_runtime_profile,
)


EXPECTED_PROFILES = (
    "claude-fusion",
    "lemonade-cuda-fusion",
    "lemonade-rocm-freecad",
    "lemonade-rocm-fusion-remote",
    "lemonade-vulkan-freecad",
    "lemonade-vulkan-fusion",
    "lemonade-vulkan-fusion-remote",
)


def test_bundled_runtime_profiles_are_listed_and_parse() -> None:
    assert list_runtime_profiles() == EXPECTED_PROFILES

    profiles = [load_runtime_profile(name) for name in EXPECTED_PROFILES]

    assert [profile.profile for profile in profiles] == list(EXPECTED_PROFILES)
    assert {profile.cad_backend for profile in profiles} == {"fusion", "freecad"}
    assert all(profile.export_directory.is_absolute() for profile in profiles)


def test_cuda_profile_matches_specification_example() -> None:
    profile = load_runtime_profile("lemonade-cuda-fusion")

    assert profile.agent == "pi"
    assert profile.model_provider == "lemonade"
    assert profile.model_endpoint == "http://127.0.0.1:13305/api/v1"
    assert profile.model == "Qwen3.5-9B-GGUF"
    assert profile.inference_backend == "cuda"
    assert profile.cad_backend == "fusion"
    assert profile.cad_endpoint == "http://127.0.0.1:8123"
    assert profile.tool_profile == "guided"
    assert profile.as_dict()["export_directory"] == str(profile.export_directory)


def test_loader_rejects_path_names() -> None:
    with pytest.raises(RuntimeProfileError, match="profile name must use"):
        load_runtime_profile("../claude-fusion")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"profile": "wrong-name"}, "must match filename"),
        ({"tool_profile": "tiny"}, "field 'tool_profile' must be one of"),
        ({"cad_endpoint": "not-a-url"}, "field 'cad_endpoint' must be"),
        ({"model_endpoint": None}, "requires model_endpoint for Lemonade"),
    ],
)
def test_loader_rejects_invalid_profiles(
    tmp_path: Path,
    change: dict[str, object],
    message: str,
) -> None:
    source = load_runtime_profile("lemonade-cuda-fusion").as_dict()
    source.update(change)
    (tmp_path / "lemonade-cuda-fusion.json").write_text(
        json.dumps(source), encoding="utf-8"
    )

    with pytest.raises(RuntimeProfileError, match=message):
        load_runtime_profile("lemonade-cuda-fusion", tmp_path)


def test_loader_reports_missing_unknown_and_malformed_profiles(tmp_path: Path) -> None:
    with pytest.raises(RuntimeProfileError, match="was not found"):
        load_runtime_profile("missing", tmp_path)

    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    with pytest.raises(RuntimeProfileError, match="invalid JSON at line 1"):
        load_runtime_profile("broken", tmp_path)

    profile = load_runtime_profile("lemonade-cuda-fusion").as_dict()
    profile["surprise"] = True
    (tmp_path / "lemonade-cuda-fusion.json").write_text(
        json.dumps(profile), encoding="utf-8"
    )
    with pytest.raises(RuntimeProfileError, match="unknown fields: surprise"):
        load_runtime_profile("lemonade-cuda-fusion", tmp_path)
