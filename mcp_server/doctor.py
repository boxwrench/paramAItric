"""ParamAItric doctor command.

Tests runtime environment, package imports, MCP startup, local model server (Lemonade)
reachability, model availability, CAD backend reachability, bridge auth, export
directory write permissions, and one health call.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp_server.runtime_profiles import (
    RuntimeProfile,
    RuntimeProfileError,
    load_runtime_profile,
    list_runtime_profiles,
)

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


def supports_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _status_text(status: str) -> str:
    return {"ok": "OK", "warn": "WARN", "fail": "FAIL"}.get(status, status.upper())


def _format_status(status: str, *, color: bool) -> str:
    text = f"[{_status_text(status)}]"
    if not color:
        return text
    return f"{_STATUS_COLORS.get(status, '')}{text}{_RESET}"


def check_python_env() -> Check:
    version = sys.version_info
    if version >= (3, 11):
        return Check("Python version", "ok", f"{version.major}.{version.minor}.{version.micro}")
    return Check(
        "Python version",
        "fail",
        f"{version.major}.{version.minor}.{version.micro}",
        "Install Python 3.11 or newer.",
    )


def check_package_import() -> Check:
    try:
        import mcp  # noqa: F401
        import pydantic  # noqa: F401
        import mcp_server.server  # noqa: F401
        import mcp_server.runtime_profiles  # noqa: F401
        return Check("Package import", "ok", "All critical packages imported successfully")
    except ImportError as exc:
        return Check(
            "Package import",
            "fail",
            f"Failed to import package: {exc}",
            "Install project dependencies with `pip install -e .`",
        )


def check_mcp_startup() -> Check:
    try:
        res = subprocess.run(
            [sys.executable, "-c", "import mcp_server.mcp_entrypoint"],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if res.returncode == 0:
            return Check("MCP startup", "ok", "MCP server entrypoint verified")
        else:
            detail = res.stderr.strip().split("\n")[-1] or "Unknown import/startup error"
            return Check(
                "MCP startup",
                "fail",
                f"MCP entrypoint failed to start: {detail}",
                "Check dependency resolution and codebase integrity.",
            )
    except Exception as exc:
        return Check("MCP startup", "fail", f"Subprocess execution failed: {exc}")


def check_lemonade(profile: RuntimeProfile) -> list[Check]:
    if profile.model_provider != "lemonade":
        return [Check("Lemonade API", "ok", "Cloud provider (no local endpoint check required)")]

    endpoint = profile.model_endpoint
    model = profile.model
    if not endpoint:
        return [
            Check(
                "Lemonade API",
                "fail",
                "Lemonade provider selected but no model_endpoint specified in profile",
            )
        ]

    # Verify endpoint reachability
    models_url = endpoint.rstrip("/") + "/models"
    try:
        req = urllib.request.Request(models_url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as response:
            data = json.loads(response.read().decode("utf-8"))

        available_models = []
        if isinstance(data, dict) and "data" in data:
            available_models = [m.get("id") for m in data["data"] if isinstance(m, dict) and "id" in m]
        elif isinstance(data, list):
            available_models = [m.get("id") if isinstance(m, dict) else m for m in data]

        if model in available_models:
            return [
                Check("Lemonade API", "ok", f"Reachable at {endpoint}"),
                Check("Model check", "ok", f"Model '{model}' is loaded and available"),
            ]
        else:
            models_str = ", ".join(available_models) if available_models else "none found"
            return [
                Check("Lemonade API", "ok", f"Reachable at {endpoint}"),
                Check(
                    "Model check",
                    "warn",
                    f"Model '{model}' is not currently loaded. Available models: {models_str}",
                    f"Load '{model}' on the Lemonade server.",
                ),
            ]
    except Exception as exc:
        # Fallback base connection check
        try:
            req = urllib.request.Request(endpoint, method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                response.read()
            return [
                Check("Lemonade API", "ok", f"Reachable at {endpoint} (but could not retrieve model list: {exc})"),
                Check(
                    "Model check",
                    "warn",
                    f"Could not verify if model '{model}' is loaded",
                    "Ensure Lemonade server has the model active.",
                ),
            ]
        except Exception as exc2:
            return [
                Check(
                    "Lemonade API",
                    "fail",
                    f"Unreachable: {endpoint} ({exc2})",
                    "Start the Lemonade server and ensure it is listening on the correct port.",
                ),
                Check("Model check", "fail", f"Cannot verify model '{model}' because endpoint is unreachable"),
            ]


def check_cad_backend(profile: RuntimeProfile) -> Check:
    endpoint = profile.cad_endpoint
    if not endpoint:
        return Check("CAD backend", "fail", "No cad_endpoint specified in profile")

    try:
        health_url = endpoint.rstrip("/") + "/health"
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))

        mode = payload.get("mode", "unknown")
        status = payload.get("status", "unknown")
        backend = payload.get("backend", "unknown")

        detail = f"Reachable at {endpoint} (backend: {backend}, mode: {mode}, status: {status})"
        return Check("CAD backend", "ok", detail)
    except Exception as exc:
        return Check(
            "CAD backend",
            "fail",
            f"Unreachable: {endpoint} ({exc})",
            "Start Fusion 360 and run the FusionAIBridge add-in.",
        )


def check_bridge_auth(profile: RuntimeProfile) -> Check:
    endpoint = profile.cad_endpoint
    if not endpoint:
        return Check("Bridge auth", "fail", "No cad_endpoint specified in profile")

    try:
        health_url = endpoint.rstrip("/") + "/health"
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as response:
            code = response.getcode()

        if code in (200, 204):
            return Check("Bridge auth", "ok", "No authorization required (open loopback bridge)")
        elif code in (401, 403):
            return Check(
                "Bridge auth",
                "warn",
                f"Bridge returned status {code} (authorization required but credentials missing)",
            )
        else:
            return Check("Bridge auth", "warn", f"Bridge returned unexpected status code {code}")
    except Exception as exc:
        return Check("Bridge auth", "fail", f"Cannot verify authorization: bridge unreachable ({exc})")


def check_export_directory(profile: RuntimeProfile) -> Check:
    export_dir = profile.export_directory
    if not export_dir:
        return Check("Export dir", "fail", "No export_directory specified in profile")

    path = Path(export_dir).expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
        # Test write
        test_file = path / ".paramaitric_doctor_write_test"
        test_file.write_text("write test", encoding="utf-8")
        test_file.unlink()
        return Check("Export dir", "ok", f"Writable: {path}")
    except Exception as exc:
        return Check(
            "Export dir",
            "fail",
            f"Cannot write to export directory {path}: {exc}",
            "Check filesystem permissions.",
        )


def check_cad_health_call(profile: RuntimeProfile) -> Check:
    endpoint = profile.cad_endpoint
    if not endpoint:
        return Check("CAD health call", "fail", "No cad_endpoint specified in profile")

    try:
        health_url = endpoint.rstrip("/") + "/health"
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))

        version = payload.get("version", "unknown")
        workflow_count = payload.get("workflow_count", 0)
        mode = payload.get("mode", "unknown")
        backend = payload.get("backend", "unknown")

        detail = f"Health call succeeded: backend={backend}, mode={mode}, version={version}, workflows={workflow_count}"
        return Check("CAD health call", "ok", detail)
    except Exception as exc:
        return Check(
            "CAD health call",
            "fail",
            f"Health call failed: {exc}",
            "Ensure the bridge is running and reachable.",
        )


def render_check_summary(checks: list[Check], *, color: bool = False) -> str:
    lines = []
    for check in checks:
        lines.append(f"{_format_status(check.status, color=color):<8} {check.label:<14} {check.detail}")
        if check.status != "ok" and check.next_step:
            lines.append(f"         What to do: {check.next_step}")
    return "\n".join(lines)


def run_doctor(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the ParamAItric environment and stack config for a specific profile."
    )
    parser.add_argument(
        "--profile",
        type=str,
        required=False,
        help="Name of the runtime profile to check (e.g. lemonade-cuda-fusion).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output.",
    )
    args = parser.parse_args(argv)

    if not args.profile:
        available = list_runtime_profiles()
        suffix = f" Available profiles: {', '.join(available)}." if available else ""
        print(f"Error: --profile is required.{suffix}", file=sys.stderr)
        return 1

    try:
        profile = load_runtime_profile(args.profile)
    except RuntimeProfileError as exc:
        print(f"Error loading profile: {exc}", file=sys.stderr)
        return 1

    use_color = supports_color() and not args.no_color

    width = 78
    print("=" * width)
    print(f"ParamAItric Doctor: {args.profile}")
    print("=" * width)
    print()

    checks: list[Check] = []
    checks.append(check_python_env())
    checks.append(check_package_import())
    checks.append(check_mcp_startup())
    checks.extend(check_lemonade(profile))
    checks.append(check_cad_backend(profile))
    checks.append(check_bridge_auth(profile))
    checks.append(check_export_directory(profile))
    checks.append(check_cad_health_call(profile))

    print(render_check_summary(checks, color=use_color))
    print()

    has_failures = any(c.status == "fail" for c in checks)
    if has_failures:
        print(f"{_format_status('fail', color=use_color)} Some checks failed. Review 'What to do' steps above.")
        return 1
    else:
        print(f"{_format_status('ok', color=use_color)} All checks passed! Profile is ready.")
        return 0
