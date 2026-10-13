"""Collect a real plate proof and viewer handoff; never self-certify hardware/UI gates."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
import time
from urllib.parse import quote, urlparse

from evaluations.runner.metadata import current_commit, utc_timestamp
from evaluations.utility_guided import run
from mcp_server.bridge_client import BridgeClient
from mcp_server.errors import error_from_exception
from mcp_server.runtime_info import FUSION_BACKEND_ID
from mcp_server.utility_plate import CenteredPlate


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def host_facts() -> dict:
    cpu = _read(Path("/proc/cpuinfo")) or ""
    cpu = next((line.split(":", 1)[1].strip() for line in cpu.splitlines() if line.startswith("model name")), None)
    graphics = []
    for card in sorted(Path("/sys/class/drm").glob("card*")):
        if not re.fullmatch(r"card\d+", card.name):
            continue
        device = card / "device"
        graphics.append({"card": card.name, "vendor_id": _read(device / "vendor"), "device_id": _read(device / "device"),
                         "kernel_driver": (device / "driver").resolve().name if (device / "driver").exists() else None})
    return {"os": platform.system(), "kernel": platform.release(), "architecture": platform.machine(),
            "cpu_model": cpu, "graphics_devices": graphics,
            "browser_renderer": None, "browser_version": None,
            "graphics_note": "Installed devices/drivers do not establish the active browser GPU or rendering API."}


def fusion_availability(endpoint: str) -> dict:
    """Read-only probe: live reachability is not live modeling evidence."""
    try:
        health = BridgeClient(endpoint, health_timeout=3).health()
        live = health.get("ok") is True and health.get("mode") == "live" and health.get("backend") == FUSION_BACKEND_ID
        return {"status": "available_live" if live else "not_live", "health": health, "modeling_evidence": "not_run"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc), "modeling_evidence": "not_run"}


def viewer_handoff(python: Path, proof: dict) -> dict:
    cli = python.absolute().with_name("cadgen")
    result = subprocess.run([str(cli), "viewer", "--host", "127.0.0.1", "--json", "--detach"],
                            capture_output=True, text=True, timeout=30, env={**os.environ, "DO_NOT_TRACK": "1"})
    if result.returncode:
        raise ValueError(f"CAD viewer launch failed (exit {result.returncode}): {result.stderr[-1000:]}")
    response = json.loads(result.stdout.strip().splitlines()[-1])
    url = response["url"]
    address = urlparse(url)
    if address.scheme != "http" or address.hostname != "127.0.0.1" or not address.port:
        raise ValueError("Viewer did not return an expected loopback URL")
    return {"status": "launched", "url": url,
            "models": {label: url + "?file=" + quote(proof[label]["artifacts"]["step"], safe="") for label in ("initial", "edited")},
            "interactive_checks": {key: "not_run" for key in ("open_both", "orbit_both", "bore_measurement", "envelope_measurement", "browser_gpu_api_driver")}}


async def collect(python: Path, root: Path, *, target_cpu: str | None, endpoint: str) -> dict:
    start = time.perf_counter()
    host = host_facts()
    report = {"timestamp": utc_timestamp(), "paramaitric_commit": current_commit(), "host": host,
              "target_cpu": target_cpu,
              "target_cpu_match": None if target_cpu is None or host["cpu_model"] is None else target_cpu.casefold() == host["cpu_model"].casefold(),
              "qualification_status": "incomplete", "fusion_geometry_parity": "not_run"}
    try:
        async with asyncio.timeout(120):
            proof = await run(python, root / "geometry")
        report["geometry"] = proof
        report["geometry_status"] = proof["status"]
        try:
            report["viewer"] = await asyncio.to_thread(viewer_handoff, python, proof)
        except Exception as exc:
            report["viewer"] = {"status": "failed", "failure": error_from_exception(exc)}
    except Exception as exc:
        report["geometry_status"] = "fail"
        report["failure"] = error_from_exception(exc)
    report["fusion"] = await asyncio.to_thread(fusion_availability, endpoint)
    report["elapsed_seconds"] = time.perf_counter() - start
    report["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True, help="Dedicated pinned CAD worker Python")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--target-cpu", help="Exact expected CPU model; mismatch cannot qualify another host")
    parser.add_argument("--fusion-endpoint", default="http://127.0.0.1:8123", help="Read-only health probe only")
    args = parser.parse_args()
    root = args.output_root.resolve()
    CenteredPlate().legacy_payload(root / "plate.stl")
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="qualification-", dir=root))
    report = asyncio.run(collect(args.python, directory, target_cpu=args.target_cpu, endpoint=args.fusion_endpoint))
    path = directory / "qualification.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"geometry_status": report["geometry_status"], "qualification_status": report["qualification_status"],
                      "report": str(path), "viewer": report.get("viewer")}))
    # Zero means evidence collection succeeded, never completed hardware qualification.
    return int(report["geometry_status"] != "pass" or report.get("viewer", {}).get("status") != "launched")


if __name__ == "__main__":
    raise SystemExit(main())
