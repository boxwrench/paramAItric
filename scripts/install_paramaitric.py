"""ParamAItric setup helper.

This script is intentionally dependency-free so it can run before the project is
installed. By default it does not mutate user config files; it checks the local
checkout and prints exact MCP client snippets for this machine.
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
_STATUS_COLORS = {
    "ok": "\033[32m",
    "warn": "\033[33m",
    "fail": "\033[31m",
}
_RESET = "\033[0m"


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


def fusion_addins_dir(system: str | None = None, env: dict[str, str] | None = None) -> Path:
    """Fusion 360's user AddIns folder, where add-ins are auto-discovered."""
    system = system or platform.system()
    env = env or os.environ
    home = Path.home()
    if system == "Windows":
        base = Path(env.get("APPDATA", home / "AppData" / "Roaming"))
        return base / "Autodesk" / "Autodesk Fusion 360" / "API" / "AddIns"
    if system == "Darwin":
        return home / "Library" / "Application Support" / "Autodesk" / "Autodesk Fusion 360" / "API" / "AddIns"
    return home / ".config" / "Autodesk" / "Autodesk Fusion 360" / "API" / "AddIns"


ADDIN_LINK_NAME = "FusionAIBridge"


def addin_link_path(system: str | None = None, env: dict[str, str] | None = None) -> Path:
    return fusion_addins_dir(system=system, env=env) / ADDIN_LINK_NAME


def addin_link_status(root: Path, link: Path | None = None) -> tuple[str, str]:
    """Return (status, detail) describing the AddIns link for this checkout."""
    link = link or addin_link_path()
    source = (root / "fusion_addin").resolve()
    if not link.exists():
        return "warn", f"not installed ({link})"
    try:
        target = link.resolve(strict=True)
    except OSError:
        return "fail", f"broken link: {link}"
    if target == source:
        return "ok", str(link)
    return "warn", f"{link} points to {target}, not this checkout"


def install_addin_link(root: Path, link: Path | None = None) -> Path:
    """Link this checkout's fusion_addin folder into Fusion's AddIns directory.

    Uses a directory junction on Windows (no admin rights needed) or a symlink
    elsewhere, so the installed add-in always runs the code in this checkout.
    Fusion lists it automatically as "FusionAIBridge" — the user only has to
    press Run (or tick Run on Startup) once.
    """
    link = link or addin_link_path()
    source = (root / "fusion_addin").resolve()
    if not source.exists():
        raise FileNotFoundError(f"fusion_addin folder not found at {source}")
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        status, _detail = addin_link_status(root, link)
        if status == "ok":
            return link
        raise FileExistsError(
            f"{link} already exists and does not point to this checkout. "
            "Remove it, then rerun --install-addin."
        )
    if platform.system() == "Windows":
        import _winapi

        _winapi.CreateJunction(str(source), str(link))
    else:
        link.symlink_to(source, target_is_directory=True)
    return link


def build_claude_config(root: Path, python_path: Path | None = None) -> dict:
    python_path = python_path or mcp_python_for_config(root)
    return {
        "mcpServers": {
            SERVER_NAME: build_claude_server_entry(root, python_path=python_path)
        }
    }


def build_claude_server_entry(root: Path, python_path: Path | None = None) -> dict:
    python_path = python_path or mcp_python_for_config(root)
    return {
        "command": str(python_path),
        "args": ["-m", "mcp_server.mcp_entrypoint"],
        "cwd": str(root),
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

    link_status, link_detail = addin_link_status(root)
    checks.append(
        Check(
            "AddIns link",
            link_status,
            link_detail,
            "Run: python scripts/install_paramaitric.py --install-addin "
            "(then in Fusion: Utilities > Add-Ins > FusionAIBridge > Run).",
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


def supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _format_status(status: str, *, color: bool) -> str:
    text = f"[{_status_text(status)}]"
    if not color:
        return text
    return f"{_STATUS_COLORS.get(status, '')}{text}{_RESET}"


def has_failures(checks: list[Check]) -> bool:
    return any(check.status == "fail" for check in checks)


def render_check_summary(checks: list[Check], *, color: bool = False) -> str:
    lines = []
    for check in checks:
        lines.append(f"{_format_status(check.status, color=color):<8} {check.label:<14} {check.detail}")
    return "\n".join(lines)


def merge_claude_config(existing: dict, root: Path, python_path: Path | None = None) -> dict:
    merged = dict(existing)
    servers = dict(merged.get("mcpServers") or {})
    servers[SERVER_NAME] = build_claude_server_entry(root, python_path=python_path)
    merged["mcpServers"] = servers
    return merged


def write_claude_config(root: Path, config_path: Path, python_path: Path | None = None) -> dict:
    existing: dict = {}
    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8").strip()
        if raw:
            existing = json.loads(raw)
            if not isinstance(existing, dict):
                raise ValueError(f"Claude config must contain a JSON object: {config_path}")

    merged = merge_claude_config(existing, root, python_path=python_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return merged


def render_dashboard(root: Path, checks: list[Check], *, color: bool = False) -> str:
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
        label = _format_status(check.status, color=color)
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
    parser.add_argument("--doctor", action="store_true", help="Print the setup dashboard. Same as the default view.")
    parser.add_argument("--check", action="store_true", help="Print local checks and exit nonzero only on failures.")
    parser.add_argument("--no-color", action="store_true", help="Disable colored status labels.")
    parser.add_argument(
        "--write-claude-config",
        action="store_true",
        help="Merge the ParamAItric server entry into Claude Desktop config.",
    )
    parser.add_argument(
        "--claude-config-path",
        type=Path,
        default=None,
        help="Override the Claude Desktop config path used by --write-claude-config.",
    )
    parser.add_argument(
        "--install-addin",
        action="store_true",
        help="Link the Fusion add-in into Fusion 360's AddIns folder so it appears automatically.",
    )
    parser.add_argument("-y", "--yes", action="store_true", help="Confirm config writes without prompting.")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    checks = run_checks(root)
    use_color = supports_color() and not args.no_color

    if args.check:
        print(render_check_summary(checks, color=use_color))
        return 1 if has_failures(checks) else 0

    if args.print == "claude":
        print(json.dumps(build_claude_config(root), indent=2))
        return 0
    if args.print == "cursor":
        print(build_cursor_command(root))
        return 0

    if args.install_addin:
        try:
            link = install_addin_link(root)
        except (FileExistsError, FileNotFoundError, OSError) as exc:
            print(f"Could not install the Fusion add-in link: {exc}")
            return 1
        print(f"Fusion add-in linked: {link}")
        print("In Fusion 360: Utilities > Scripts and Add-Ins > Add-Ins > FusionAIBridge > Run.")
        print('Tip: tick "Run on Startup" so you never have to do this again.')
        return 0

    if args.write_claude_config:
        config_path = (args.claude_config_path or claude_config_path()).expanduser()
        if not args.yes:
            response = input(f"Write ParamAItric MCP config to {config_path}? [y/N] ").strip().lower()
            if response not in {"y", "yes"}:
                print("No changes written.")
                return 1
        write_claude_config(root, config_path)
        print(f"Updated Claude Desktop config: {config_path}")
        return 0

    print(render_dashboard(root, checks, color=use_color))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
