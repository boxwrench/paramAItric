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


def check_mcp_startup(profile: RuntimeProfile) -> list[Check]:
    import_script = (
        "import json\n"
        "import mcp_server.mcp_entrypoint as ep\n"
        "import mcp_server.runtime_info as ri\n"
        "import anyio\n"
        "tools = anyio.run(ep.mcp.list_tools)\n"
        "res = {\n"
        "    'active_profile': ri.ACTIVE_PROFILE_NAME,\n"
        "    'registered_tools': [t.name for t in tools],\n"
        "    'active_export_directory': ri.ACTIVE_PROFILE_EXPORT_DIR\n"
        "}\n"
        "print(json.dumps(res))\n"
    )
    try:
        env = os.environ.copy()
        env["PARAMAITRIC_PROFILE"] = profile.profile
        res = subprocess.run(
            [sys.executable, "-c", import_script],
            capture_output=True,
            text=True,
            timeout=5.0,
            env=env,
        )
        if res.returncode != 0:
            detail = res.stderr.strip().split("\n")[-1] or "Unknown import/startup error"
            return [
                Check(
                    "MCP startup",
                    "fail",
                    f"MCP entrypoint failed to import under profile '{profile.profile}': {detail}",
                    "Check dependency resolution and codebase integrity.",
                )
            ]
        
        data = json.loads(res.stdout.strip())
        act_prof = data.get("active_profile")
        reg_tools = data.get("registered_tools", [])
        act_exp = data.get("active_export_directory")

        checks = []
        # 1. Profile name verification
        if act_prof == profile.profile:
            checks.append(Check("Active profile", "ok", f"Expected '{profile.profile}', got '{act_prof}'"))
        else:
            checks.append(
                Check(
                    "Active profile",
                    "fail",
                    f"Profile mismatch: expected '{profile.profile}', but server reported '{act_prof}'",
                    "Ensure profile activation works correctly."
                )
            )

        # 2. Export directory verification
        expected_dir = str(profile.export_directory)
        if act_exp == expected_dir:
            checks.append(Check("Export directory", "ok", f"Expected '{expected_dir}', got '{act_exp}'"))
        else:
            checks.append(
                Check(
                    "Export directory",
                    "fail",
                    f"Export directory mismatch: expected '{expected_dir}', but server used '{act_exp}'",
                    "Check export_directory resolution in schemas.py."
                )
            )

        # 3. Tool surface check
        if profile.tool_profile == "guided":
            expected_guided = {"cad_health", "cad_recommend_workflow", "cad_get_requirements", "cad_build", "cad_inspect"}
            if set(reg_tools) == expected_guided:
                checks.append(Check("Tool surface", "ok", "Guided profile tool facade verified"))
            else:
                checks.append(
                    Check(
                        "Tool surface",
                        "fail",
                        f"Expected guided tool surface {sorted(expected_guided)}, but got {sorted(reg_tools)}",
                        "Check tool profile registration gating in mcp_entrypoint.py."
                    )
                )
        else:
            if "create_spacer" in reg_tools:
                checks.append(Check("Tool surface", "ok", "Full profile tool surface verified"))
            else:
                checks.append(
                    Check(
                        "Tool surface",
                        "fail",
                        "Expected full tool surface, but basic tools like 'create_spacer' are missing",
                        "Check tool profile registration gating in mcp_entrypoint.py."
                    )
                )

        return checks
    except Exception as exc:
        return [Check("MCP startup", "fail", f"Subprocess execution failed: {exc}")]


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
                Check("Model check", "ok", f"Model '{model}' is available on the server"),
            ]
        else:
            models_str = ", ".join(available_models) if available_models else "none found"
            return [
                Check("Lemonade API", "ok", f"Reachable at {endpoint}"),
                Check(
                    "Model check",
                    "fail",
                    f"Model '{model}' is not available on the server. Available models: {models_str}",
                    f"Download or load '{model}' on the Lemonade server.",
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
                    f"Could not verify if model '{model}' is available on the server",
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

        # Check backend identity:
        # profile cad_backend -> Expected health backend
        # fusion -> autodesk_fusion
        # freecad -> freecad
        # mock -> mock
        expected_backend = {
            "fusion": "autodesk_fusion",
            "freecad": "freecad",
            "mock": "mock",
        }.get(profile.cad_backend, profile.cad_backend)

        if backend != expected_backend:
            return Check(
                "CAD backend",
                "fail",
                f"Backend identity mismatch: profile specifies '{profile.cad_backend}' (expects health backend '{expected_backend}'), but reachable bridge is '{backend}'",
                "Ensure the correct CAD application and bridge are running for the selected profile."
            )

        detail = f"Reachable at {endpoint} (backend: {backend}, mode: {mode}, status: {status})"
        
        if status != "ready":
            return Check(
                "CAD backend",
                "fail",
                detail,
                "Check CAD backend health and document status.",
            )

        if mode == "mock":
            return Check(
                "CAD backend",
                "warn",
                detail + " - running in practice mode because no design is open",
                "Open or create a design in Fusion 360/FreeCAD; the bridge should upgrade to live automatically.",
            )

        if mode == "unknown":
            return Check(
                "CAD backend",
                "fail",
                detail,
                "Verify the CAD bridge/add-in operating mode.",
            )

        return Check("CAD backend", "ok", detail)
    except Exception as exc:
        if profile.cad_backend == "freecad":
            advice = "Start the FreeCAD bridge service."
        else:
            advice = "Start Fusion 360 and run the FusionAIBridge add-in."
        return Check(
            "CAD backend",
            "fail",
            f"Unreachable: {endpoint} ({exc})",
            advice,
        )


def check_bridge_auth(profile: RuntimeProfile) -> Check:
    # Until mutation authorization lands, warn that mutation auth is not configured
    return Check(
        "Bridge auth",
        "warn",
        "Mutation authorization is not configured.",
        "Add token-based authorization to secure the loopback mutation boundary."
    )


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
        if profile.cad_backend == "freecad":
            advice = "Start the FreeCAD bridge service."
        else:
            advice = "Ensure Fusion 360 is running and the FusionAIBridge add-in is active."
        return Check(
            "CAD health call",
            "fail",
            f"Health call failed: {exc}",
            advice,
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
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Make warnings return exit code 1.",
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
    checks.extend(check_mcp_startup(profile))
    checks.extend(check_lemonade(profile))
    checks.append(check_cad_backend(profile))
    checks.append(check_bridge_auth(profile))
    checks.append(check_export_directory(profile))
    checks.append(check_cad_health_call(profile))

    print(render_check_summary(checks, color=use_color))
    print()

    has_failures = any(c.status == "fail" for c in checks)
    has_warnings = any(c.status == "warn" for c in checks)
    if has_failures:
        print(f"{_format_status('fail', color=use_color)} Some checks failed. Review 'What to do' steps above.")
        return 1
    elif has_warnings:
        print(f"{_format_status('warn', color=use_color)} Profile is usable with warnings, but not release-ready.")
        if args.strict:
            return 1
        return 0
    else:
        print(f"{_format_status('ok', color=use_color)} All checks passed! Profile is ready.")
        return 0
