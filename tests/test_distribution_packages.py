"""Regression tests for the Python package surface shipped by setuptools."""

from fnmatch import fnmatchcase
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOTS = ("fusion_addin", "mcp_server")


def test_setuptools_discovery_includes_every_runtime_package() -> None:
    """Every import package in the runtime roots must be included in distributions."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    discovery = config["tool"]["setuptools"]["packages"]["find"]

    assert discovery["where"] == ["."]
    include_patterns = discovery["include"]
    assert include_patterns == ["fusion_addin*", "mcp_server*"]

    runtime_packages = {
        init_file.parent.relative_to(ROOT).as_posix().replace("/", ".")
        for package_root in PACKAGE_ROOTS
        for init_file in (ROOT / package_root).rglob("__init__.py")
    }
    excluded_packages = discovery.get("exclude", [])

    assert runtime_packages
    assert all(
        any(fnmatchcase(package, pattern) for pattern in include_patterns)
        and not any(fnmatchcase(package, pattern) for pattern in excluded_packages)
        for package in runtime_packages
    )
    assert {
        "mcp_server.primitives",
        "mcp_server.sessions",
        "mcp_server.workflows",
    } <= runtime_packages


def test_packaged_profiles_are_discoverable() -> None:
    from mcp_server.runtime_profiles import list_runtime_profiles, load_runtime_profile

    profiles = list_runtime_profiles()
    assert "claude-fusion" in profiles
    assert "lemonade-cuda-fusion" in profiles

    claude = load_runtime_profile("claude-fusion")
    assert claude.profile == "claude-fusion"

    lemonade = load_runtime_profile("lemonade-cuda-fusion")
    assert lemonade.profile == "lemonade-cuda-fusion"

