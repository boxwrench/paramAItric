"""ParamAItric setup helper.

This script is intentionally dependency-free so it can run before the project is
installed. It does not mutate user config files; it checks the local checkout and
prints exact MCP client snippets for this machine.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_NAME = "ParamAItric"
SERVER_NAME = "paramaitric"


@dataclass(frozen=True)
class Check:
    label: str
    status: str
    detail: str
    next_step: str | None = None


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def default_venv_python(root: Path, system: str | None = None) -> Path:
    system = system or platform.system()
    if system == "Windows":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def mcp_python_for_config(root: Path, *, system: str | None = None) -> Path:
    venv_python = default_venv_python(root, system=system)
    if venv_python.exists():
        return venv_python
    return Path(sys.executable).resolve()


def claude_config_path(system: str | None = None, env: dict[str, str] | None = None) -> Path:
    system = system or platform.system()
    env = env or os.environ
    home = Path.home()
    if system == "Windows":
        base = Path(env.get("APPDATA", home / "AppData" / "Roaming"))
        return base / "Claude" / "claude_desktop_config.json"
    if system == "Darwin":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return home / ".config" / "Claude" / "claude_desktop_config.json"


def build_claude_config(root: Path, python_path: Path | None = None) -> dict:
    python_path = python_path or mcp_python_for_config(root)
    return {
        "mcpServers": {
            SERVER_NAME: {
                "command": str(python_path),
                "args": ["-m", "mcp_server.mcp_entrypoint"],
                "cwd": str(root),
            }
        }
    }


def build_cursor_command(root: Path, python_path: Path | None = None) -> str:
    python_path = python_path or mcp_python_for_config(root)
    return f'"{python_path}" -m mcp_server.mcp_entrypoint'


def run_checks(root: Path) -> list[Check]:
    checks: list[Check] = []

    version = sys.version_info
    if version >= (3, 11):
        checks.append(Check("Python", "ok", f"{version.major}.{version.minor}.{version.micro}"))
    else:
        checks.append(
            Check(
                "Python",
                "fail",
                f"{version.major}.{version.minor}.{version.micro}",
                "Install Python 3.11 or newer.",
            )
        )

    checks.append(
        Check(
            "Repo root",
            "ok" if (root / "pyproject.toml").exists() else "fail",
            str(root),
            "Run this script from a ParamAItric checkout.",
        )
    )

    addin = root / "fusion_addin"
    manifest = addin / "FusionAIBridge.manifest"
    checks.append(
        Check(
            "Fusion add-in",
            "ok" if addin.exists() and manifest.exists() else "fail",
            str(addin),
            "In Fusion 360, add this folder under Utilities > Scripts and Add-Ins > Add-Ins.",
        )
    )

    venv_python = default_venv_python(root)
    checks.append(
        Check(
            "Virtualenv",
            "ok" if venv_python.exists() else "warn",
            str(venv_python),
            "Run: python -m venv .venv",
        )
    )

    config_python = mcp_python_for_config(root)
    checks.append(
        Check(
            "MCP command",
            "ok" if config_python.exists() else "fail",
            f"{config_python} -m mcp_server.mcp_entrypoint",
            "Create the virtualenv and install ParamAItric with: pip install -e .",
        )
    )

    return checks


def _status_text(status: str) -> str:
    return {"ok": "OK", "warn": "WARN", "fail": "FAIL"}.get(status, status.upper())


def render_dashboard(root: Path, checks: list[Check]) -> str:
    width = 78
    lines = [
        "=" * width,
        f"{PROJECT_NAME} setup",
        "=" * width,
        "",
        "Local checks",
        "-" * 12,
    ]

    for check in checks:
        label = f"[{_status_text(check.status)}]"
        lines.append(f"{label:<8} {check.label:<14} {check.detail}")

    next_steps = [check.next_step for check in checks if check.status != "ok" and check.next_step]
    if next_steps:
        lines.extend(["", "Next actions", "-" * 12])
        for index, step in enumerate(dict.fromkeys(next_steps), start=1):
            lines.append(f"{index}. {step}")

    lines.extend(
        [
            "",
            "Fusion add-in folder",
            "-" * 20,
            str(root / "fusion_addin"),
            "",
            "Claude Desktop config target",
            "-" * 28,
            str(claude_config_path()),
            "",
            "Claude Desktop config snippet",
            "-" * 29,
            json.dumps(build_claude_config(root), indent=2),
            "",
            "Cursor command",
            "-" * 14,
            build_cursor_command(root),
            "",
            "First prompt",
            "-" * 12,
            (
                "Check your MCP tools. Use the ParamAItric health check to ensure you can "
                "reach Fusion 360."
            ),
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check ParamAItric setup and print MCP config snippets.")
    parser.add_argument("--root", type=Path, default=repo_root_from_script(), help="ParamAItric checkout root.")
    parser.add_argument(
        "--print",
        choices=("dashboard", "claude", "cursor"),
        default="dashboard",
        help="Output format to print.",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if args.print == "claude":
        print(json.dumps(build_claude_config(root), indent=2))
        return 0
    if args.print == "cursor":
        print(build_cursor_command(root))
        return 0

    print(render_dashboard(root, run_checks(root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
