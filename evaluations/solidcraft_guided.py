"""Real five-tool MCP proof for the opt-in SolidCraft transactional bridge."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from evaluations.runner.metadata import current_commit, utc_timestamp

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


async def run(cli, python, output_root):
    output_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="guided-", dir=output_root))
    report = {"timestamp": utc_timestamp(), "source_commit": current_commit(), "directory": str(root),
              "host": {"platform": platform.platform(), "cpu": subprocess.check_output(["uname", "-m"], text=True).strip()},
              "status": "fail", "calls": [], "families": {}, "negative_checks": {},
              "UI_target_hardware_live_Fusion": "not_run",
              "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in [*sorted((ROOT / "cad_backends/solidcraft").glob("*.py")),
                  ROOT / "mcp_server/solidcraft_runtime.py", ROOT / "mcp_server/utility_runtime.py", ROOT / "evaluations/solidcraft_guided.py"]}}
    env = {**os.environ, "PARAMAITRIC_CAD_BACKEND": "solidcraft", "PARAMAITRIC_SOLIDCRAFT_CLI": str(cli),
           "PARAMAITRIC_CAD_PYTHON": str(python), "PARAMAITRIC_CAD_OUTPUT_ROOT": str(root)}
    env.pop("PARAMAITRIC_PROFILE", None)
    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.mcp_entrypoint"], cwd=str(ROOT), env=env)
    start = time.perf_counter()
    try:
        with (root / "mcp.log").open("w") as log:
            async with stdio_client(params, errlog=log) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    tools = [tool.name for tool in (await client.list_tools()).tools]
                    assert set(tools) == {"cad_health", "cad_recommend_workflow", "cad_get_requirements", "cad_build", "cad_inspect"}
                    report["tools"] = tools
                    async def call(name, payload=None, *, failure=None):
                        begun = time.perf_counter()
                        result = await client.call_tool(name, {} if payload is None else {"payload": payload})
                        data = result.structuredContent or json.loads(next(b.text for b in result.content if b.type == "text"))
                        report["calls"].append({"tool": name, "payload": payload, "wall_seconds": time.perf_counter() - begun,
                                                "ok": data.get("ok"), "classification": data.get("classification")})
                        if failure:
                            assert data.get("ok") is False and data.get("classification") == failure, data
                        else:
                            assert not result.isError and data.get("ok", True) is not False, data
                        return data
                    report["health"] = await call("cad_health")
                    for kind, workflow, dimensions, width in (
                        ("plate", "plate_with_hole", {"width_cm": 80, "height_cm": 60, "thickness_cm": 5,
                         "hole_diameter_cm": 10, "hole_center_x_cm": 40, "hole_center_y_cm": 30}, 100),
                        ("bracket", "bracket", {"width_cm": 50, "height_cm": 80, "thickness_cm": 5, "leg_thickness_cm": 5}, 70)):
                        await call("cad_recommend_workflow", {"intent": "centered plate with hole" if kind == "plate" else "flat L bracket"})
                        await call("cad_get_requirements", {"workflow": workflow})
                        first = await call("cad_build", {"workflow": workflow, "parameters": {**dimensions, "units": "mm"}})
                        second = await call("cad_build", {"workflow": workflow, "revision_id": first["revision_id"], "parameters": {"width_cm": width, "units": "mm"}})
                        inspection = {"operation": "get_revision", "parameters": {"revision_id": second["revision_id"]}}
                        checked = await call("cad_inspect", inspection)
                        assert abs(checked["measurements"]["width"] - width) < 0.01
                        if kind == "plate":
                            assert abs(checked["measurements"]["bore_x"] - 50) < 0.01
                        for revision in (first, second):
                            assert revision["acceptance"] == "accepted" and all(c["passed"] for c in revision["verification_signals"])
                            assert all(digest(path) == revision["artifact_sha256"][key] for key, path in revision["artifacts"].items())
                        report["families"][kind] = {"initial": first, "edited": second, "inspection": checked}
                        for key in ("native", "step", "stl"):
                            path = Path(second["artifacts"][key])
                            blob = path.read_bytes()
                            try:
                                path.write_bytes(b"modified evidence")
                                await call("cad_inspect", inspection, failure="verification_failed")
                                report["negative_checks"][f"{kind}_{key}_tamper_rejected"] = True
                            finally:
                                path.write_bytes(blob)
                        await call("cad_build", {"workflow": workflow, "revision_id": second["revision_id"],
                                                 "parameters": {"width_cm": 0}}, failure="validation_error")
                        report["negative_checks"][f"{kind}_zero_width_rejected"] = True
                        assert all(digest(path) == second["artifact_sha256"][key] for key, path in second["artifacts"].items())
                    await call("cad_build", {"workflow": "filleted_bracket", "parameters": {}}, failure="unsupported_capability")
                    report["negative_checks"]["unsupported_workflow_rejected"] = True
                    report["status"] = "pass"
    except Exception as exc:
        report["failure"] = repr(exc)
    report["wall_seconds"] = time.perf_counter() - start
    (root / "evidence.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "evidence": str(root / "evidence.json"), "wall_seconds": report["wall_seconds"], "failure": report.get("failure")}))
    return report["status"] == "pass"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solidcraft-cli", required=True, type=Path)
    parser.add_argument("--cad-python", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    if not all(p.is_absolute() for p in (args.solidcraft_cli, args.cad_python, args.output_root)):
        parser.error("all paths must be absolute")
    return asyncio.run(asyncio.wait_for(run(args.solidcraft_cli, args.cad_python, args.output_root), timeout=180))


if __name__ == "__main__":
    raise SystemExit(int(not main()))
