"""One real guided MCP stdio plate build/edit/inspection proof; no model involved."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from evaluations.runner.metadata import ReproducibilityMetadata, utc_timestamp

ROOT = Path(__file__).resolve().parents[1]


async def run(python: Path, output: Path) -> dict:
    env = {**os.environ, "PARAMAITRIC_CAD_BACKEND": "cadgen", "PARAMAITRIC_CAD_PYTHON": str(python.absolute()),
           "PARAMAITRIC_CAD_OUTPUT_ROOT": str(output.resolve())}
    env.pop("PARAMAITRIC_PROFILE", None)
    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.mcp_entrypoint"],
                                  cwd=str(ROOT), env=env)
    fixture = ROOT / "evaluations/cases/plate_centered_hole_success.json"
    case = json.loads(fixture.read_text())
    report = {"timestamp": utc_timestamp(), "metadata": ReproducibilityMetadata.capture(case["id"], model="none",
              inference_backend="none", tool_profile="guided").to_dict(), "transport": "MCP_stdio",
              "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest()}
    report["request_timings"] = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            report["tools"] = [t.name for t in tools]
            if set(report["tools"]) != {"cad_health", "cad_recommend_workflow", "cad_get_requirements", "cad_build", "cad_inspect"}:
                raise ValueError("open backend exposed an unexpected tool surface")
            async def call(name, payload=None):
                start = time.perf_counter()
                reply = await session.call_tool(name, {} if payload is None else {"payload": payload})
                if reply.structuredContent is not None:
                    result = reply.structuredContent
                else:
                    result = json.loads(next(c.text for c in reply.content if c.type == "text"))
                report["request_timings"].append({"tool": name, "wall_seconds": time.perf_counter() - start,
                                                  "ok": result.get("ok")})
                return result
            report["health"] = await call("cad_health")
            if report["health"].get("ok") is not True:
                raise ValueError(f"worker health failed: {report['health']}")
            arguments = dict(case["arguments"])
            arguments.pop("output_path")  # Product default must use its configured output folder.
            report["initial"] = await call("cad_build", {"workflow": "plate_with_hole", "parameters": arguments})
            if report["initial"].get("ok") is not True:
                raise ValueError(f"guided build failed: {report['initial']}")
            report["edited"] = await call("cad_build", {"workflow": "plate_with_hole",
                         "revision_id": report["initial"]["revision_id"], "parameters": {"width_cm": 10}})
            if report["edited"].get("ok") is not True:
                raise ValueError(f"guided replay failed: {report['edited']}")
            inspection = {"operation": "get_revision", "parameters": {"revision_id": report["edited"]["revision_id"]}}
            report["inspection"] = await call("cad_inspect", inspection)
            facts = report["inspection"].get("measurements", {})
            if facts.get("hole_center_x_mm") != 50 or facts.get("hole_diameter_mm") != 10:
                raise ValueError("guided saved-export inspection did not preserve the centered bore")
            before = set(output.iterdir())
            report["unsupported"] = await call("cad_build", {"workflow": "spacer", "parameters": {}})
            if report["unsupported"].get("classification") != "unsupported_capability" or set(output.iterdir()) != before:
                raise ValueError("unsupported workflow did not fail before artifacts/mutation")
            for kind in ("step", "stl"):
                artifact = Path(report["edited"]["artifacts"][kind])
                original = artifact.read_bytes()
                try:
                    artifact.write_text(f"modified exported {kind}")
                    failure = await call("cad_inspect", inspection)
                    report[f"corrupt_{kind}"] = failure
                    if failure.get("stage") != "revision_integrity" or failure.get("ok") is not False:
                        raise ValueError(f"modified {kind} evidence was accepted")
                finally:
                    artifact.write_bytes(original)
    report["status"] = "pass"
    report["source_sha256"] = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in (
        "mcp_server/utility_runtime.py", "mcp_server/mcp_entrypoint.py", "mcp_server/utility_plate.py",
        "cad_backends/cadgen/adapter.py", "cad_backends/cadgen/recipe.py")}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    start = time.perf_counter()
    async def bounded_run():
        async with asyncio.timeout(120):
            return await run(args.python, args.output_root.resolve())
    try:
        report = asyncio.run(bounded_run())
    except Exception as exc:
        report = {"status": "fail", "error": str(exc), "transport": "MCP_stdio"}
    report["elapsed_seconds"] = time.perf_counter() - start
    args.output_root.mkdir(parents=True, exist_ok=True)
    path = args.output_root / "guided-smoke.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "report": str(path), "elapsed_seconds": report["elapsed_seconds"]}))
    return int(report["status"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
