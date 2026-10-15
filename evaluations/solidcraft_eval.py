"""Bounded SolidCraft adoption experiment. No production adapter or tool registration."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from evaluations.runner.metadata import current_commit, utc_timestamp
from evaluations.solidcraft_cases import BRACKET, PLATE, bracket_stages, command, plate_stages

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment(directory: Path) -> dict:
    env = {**os.environ, "DO_NOT_TRACK": "1"}
    for name, suffix in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"),
                         ("XDG_CACHE_HOME", "cache"), ("TMPDIR", "tmp")):
        path = directory / "state" / suffix
        path.mkdir(parents=True, exist_ok=True)
        env[name] = str(path)
    return env


def semantic_state(state: dict) -> dict:
    """Compare authored state/history; elapsed timings and revision counters are diagnostics."""
    return {"params": state.get("params"), "timeline": [
        {key: f.get(key) for key in ("id", "name", "type", "error", "warning", "suppressed", "rolled_back")}
        for f in state.get("timeline", [])],
        **{key: state.get(key) for key in ("undo", "redo", "marker", "active_sketch")}}


def timeline_errors(state: dict) -> list:
    return [f for f in state.get("timeline", []) if f.get("error")]


@asynccontextmanager
async def session(cli: Path, directory: Path):
    params = StdioServerParameters(command=str(cli), args=["mcp", "--allow-path", str(directory)],
                                  cwd=str(directory), env=environment(directory))
    with (directory / "mcp-stderr.log").open("a") as log:
        async with stdio_client(params, errlog=log) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                yield client


async def call(client, log: list, name: str, args: dict, *, allow_error=False) -> dict:
    start = time.perf_counter()
    result = await client.call_tool(name, args)
    texts = [b.text for b in result.content if b.type == "text"]
    try:
        data = json.loads(texts[0]) if texts else {}
    except json.JSONDecodeError:
        data = {"message": "\n".join(texts)}
    log.append({"tool": name, "arguments": args, "isError": result.isError,
                "wall_seconds": time.perf_counter() - start, "result": data})
    if result.isError and not allow_error:
        raise ValueError(f"{name} failed: {data}")
    return {"isError": result.isError, "data": data}


async def healthy(client, log):
    state = (await call(client, log, "inspect_design", {"measure": False}))["data"]
    if timeline_errors(state):
        raise ValueError("Feature errors prevent acceptance or the next mutation")
    return state


async def readback(client, log, python: Path, directory: Path, label: str, kind: str, p: dict) -> dict:
    await healthy(client, log)
    path = directory / f"{label}.step"
    await call(client, log, "export", {"path": str(path), "format": "step"})
    mesh = directory / f"{label}.stl"
    await call(client, log, "export", {"path": str(mesh), "format": "stl"})
    def inspect():
        return subprocess.run([str(python), "-I", str(ROOT / "evaluations/solidcraft_readback.py"), str(path), kind, json.dumps(p), str(mesh)],
                              capture_output=True, text=True, timeout=60,
                              env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
    result = await asyncio.to_thread(inspect)
    try:
        facts = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Independent reader failed: {result.stderr[-1000:]}") from exc
    facts.update({"step": str(path), "step_sha256": digest(path), "stl": str(mesh), "stl_sha256": digest(mesh), "parameters": dict(p)})
    (directory / f"{label}-readback.json").write_text(json.dumps(facts, indent=2) + "\n")
    if result.returncode or facts.get("ok") is not True:
        raise ValueError(f"Required independent STEP verification failed at {label}: {facts}")
    return facts


async def family(cli: Path, python: Path, directory: Path, kind: str) -> dict:
    directory.mkdir()
    log, checks = [], []
    p = dict(PLATE if kind == "plate" else BRACKET)
    stages = plate_stages() if kind == "plate" else bracket_stages()
    (directory / "commands.json").write_text(json.dumps({"stages": stages}, indent=2) + "\n")
    result = {"kind": kind, "status": "fail", "log": log, "readbacks": checks}
    try:
        async with session(cli, directory) as client:
            for i, stage in enumerate(stages):
                await call(client, log, "batch", {"commands": stage, "verbose": False})
                checks.append(await readback(client, log, python, directory, f"stage-{i}", "plate_base" if kind == "plate" and i == 0 else kind, p))
            state = await healthy(client, log)
            if not state.get("timeline") or not state.get("params"):
                raise ValueError("Native authored history and parameters are missing")
            await call(client, log, "save", {"path": str(directory / "initial.solidcraft")})
            await call(client, log, "export", {"path": str(directory / "initial.stl"), "format": "stl"})
            await call(client, log, "screenshot", {"path": str(directory / "initial.png"), "source": "model", "view": "iso", "width": 800, "height": 600})
            result["native_measurement"] = (await call(client, log, "measure", {}))["data"]
        # A new process must reconstruct and edit the native history. Save's default
        # has no warm geometry cache, and STEP import is never used as editability proof.
        async with session(cli, directory) as client:
            await call(client, log, "open", {"path": str(directory / "initial.solidcraft")})
            result["reopened_authored_state"] = await healthy(client, log)
            checks.append(await readback(client, log, python, directory, "reopened-initial", kind, p))
            edited_width = 100 if kind == "plate" else 70
            for i, width in enumerate((edited_width, p["width"], edited_width, p["width"], edited_width)):
                response = (await call(client, log, "set_parameter", {"name": "width", "value": f"{width} mm"}))["data"]
                if response.get("errors"):
                    raise ValueError(f"Parameter regeneration failed: {response['errors']}")
                p["width"] = width
                checks.append(await readback(client, log, python, directory, f"regenerate-{i}", kind, p))
            await call(client, log, "save", {"path": str(directory / "edited.solidcraft")})
            await call(client, log, "export", {"path": str(directory / "edited.stl"), "format": "stl"})
            await call(client, log, "screenshot", {"path": str(directory / "edited.png"), "source": "model", "view": "iso", "width": 800, "height": 600})
        async with session(cli, directory) as client:
            await call(client, log, "open", {"path": str(directory / "edited.solidcraft")})
            checks.append(await readback(client, log, python, directory, "reopened-edited", kind, p))
            if kind == "bracket":
                await call(client, log, "set_parameter", {"name": "leg", "value": "6 mm"})
                p["leg"] = 6
                checks.append(await readback(client, log, python, directory, "leg-edited", kind, p))
        result["status"] = "pass"
    except Exception as exc:
        result["failure"] = str(exc)
    result["artifacts"] = {f.name: {"path": str(f), "sha256": digest(f)} for f in directory.iterdir()
                           if f.is_file() and f.suffix in (".step", ".solidcraft", ".stl", ".png", ".json")}
    return result


async def failures(cli: Path, python: Path, directory: Path, native: Path) -> dict:
    import shutil
    directory.mkdir()
    copied = directory / "baseline.solidcraft"
    shutil.copyfile(native, copied)
    native = copied
    log, results = [], {}
    async with session(cli, directory) as client:
        # This isolated scratch session cannot overwrite accepted experiment artifacts.
        await call(client, log, "open", {"path": str(native)})
        actions = {
            "invalid_zero_width": ("set_parameter", {"name": "width", "value": "0 mm"}),
            "failed_fillet": ("execute", {"command": "solid.fillet", "params": {"edges": [[80, 0, 2.5]], "radius": 100, "body": "Plate"}}),
            "missing_edge_reference": ("execute", {"command": "solid.fillet", "params": {"edges": [{"body": "MissingBody", "index": 999999}], "radius": 1}}),
            "missing_parameter_reference": ("execute", {"command": "timeline.edit", "params": {"feature": "Bore", "set": {"extent": {"distance": "missing_dimension"}}}}),
            "far_coordinate_edge_pick": ("execute", {"command": "solid.fillet", "params": {"edges": [[10000, 10000, 10000]], "radius": 1, "body": "Plate"}}),
            "batch_rollback": ("batch", {"commands": [command("parameters.change", name="width", expression="100 mm"), command("missing.command")], "rollback": True}),
        }
        for name, (tool, args) in actions.items():
            before = semantic_state(await healthy(client, log))
            checkpoint = (await call(client, log, "execute", {"command": "edit.checkpoint"}))["data"]["checkpoint"]
            response = await call(client, log, tool, args, allow_error=True)
            after = (await call(client, log, "inspect_design", {"measure": False}))["data"]
            data = response["data"]
            signalled = bool(response["isError"] or data.get("errors") or data.get("failed") or timeline_errors(after))
            results[name] = {"failure_signalled": signalled, "isError": response["isError"],
                             "authored_state_unchanged": semantic_state(after) == before, "response": data}
            await call(client, log, "execute", {"command": "edit.restore_checkpoint", "params": {"checkpoint": checkpoint}})
            restored = semantic_state(await healthy(client, log)) == before
            results[name]["checkpoint_restored"] = restored
            results[name]["readback"] = await readback(client, log, python, directory, name + "-restored", "plate", PLATE)
            results[name]["status"] = "pass" if signalled and restored else "fail"
    return {"cases": results, "log": log}


async def fillet(cli: Path, python: Path, directory: Path, native: Path) -> dict:
    import shutil
    directory.mkdir()
    copied = directory / "baseline.solidcraft"
    shutil.copyfile(native, copied)
    log, checks = [], []
    p = {**BRACKET, "width": 70, "fillet": 1.5}
    result = {"status": "fail", "log": log, "readbacks": checks,
              "selection": {"kind": "outer vertical edge", "point_mm": [70, 0, 2.5], "radius_mm": 1.5}}
    try:
        async with session(cli, directory) as client:
            await call(client, log, "open", {"path": str(copied)})
            await call(client, log, "execute", {"command": "solid.fillet", "params": {"edges": [[70, 0, 2.5]], "radius": 1.5, "body": "Bracket"}})
            checks.append(await readback(client, log, python, directory, "fillet", "bracket", p))
            await call(client, log, "save", {"path": str(directory / "filleted.solidcraft")})
            await call(client, log, "screenshot", {"path": str(directory / "fillet.png"), "source": "model", "view": "iso", "width": 800, "height": 600})
        async with session(cli, directory) as client:
            await call(client, log, "open", {"path": str(directory / "filleted.solidcraft")})
            await call(client, log, "set_parameter", {"name": "width", "value": "90 mm"})
            p["width"] = 90
            checks.append(await readback(client, log, python, directory, "fillet-edited", "bracket", p))
        result["status"] = "pass"
    except Exception as exc:
        result["failure"] = str(exc)
    return result


def cancellation(cli: Path, directory: Path, native: Path, *, terminate: bool) -> dict:
    """Real protocol notification vs explicit process termination are distinct evidence."""
    directory.mkdir()
    sentinel = directory / "after-cancel.solidcraft"
    commands = [command("parameters.change", name="width", expression=f"{100 if i % 2 else 80} mm") for i in range(600)]
    commands.append(command("file.save_as", path=str(sentinel)))
    before = digest(native)
    with (directory / "stderr.log").open("wb") as log:
        process = subprocess.Popen([str(cli), "mcp", "--allow-path", str(directory), "--allow-path", str(native.parent)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, cwd=directory,
                                   env=environment(directory), start_new_session=True, text=True)
        def send(message):
            process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
            process.stdin.flush()
        def receive(request_id, timeout=15):
            deadline = time.monotonic() + timeout
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            try:
                while time.monotonic() < deadline:
                    if not selector.select(max(0, deadline - time.monotonic())):
                        break
                    line = process.stdout.readline()
                    if not line:
                        break
                    message = json.loads(line)
                    if message.get("id") == request_id:
                        return message
            finally:
                selector.close()
            raise TimeoutError("SolidCraft did not answer within the evaluation limit")
        try:
            send({"id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "ParamAItric-evaluation", "version": "0.1"}}})
            receive(1)
            send({"method": "notifications/initialized"})
            send({"id": 2, "method": "tools/call", "params": {"name": "open", "arguments": {"path": str(native)}}})
            receive(2)
            send({"id": 3, "method": "tools/call", "params": {"name": "batch", "arguments": {"commands": commands, "verbose": False}}})
            time.sleep(0.02)
            sent = time.time_ns()
            if terminate:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                response = None
            else:
                send({"method": "notifications/cancelled", "params": {"requestId": 3, "reason": "bounded evaluation cancellation"}})
                response = receive(3)
            modified_after_cancel = sentinel.exists() and sentinel.stat().st_mtime_ns > sent
            response_summary = None
            if response is not None:
                (directory / "response.json").write_text(json.dumps(response, indent=2) + "\n")
                reply = response.get("result", {})
                texts = [b.get("text") for b in reply.get("content", []) if b.get("type") == "text"]
                parsed = json.loads(texts[0]) if texts else {}
                response_summary = {"id": response.get("id"), "isError": reply.get("isError"),
                                    **{k: parsed.get(k) for k in ("completed", "ok", "failed")},
                                    "raw_response_sha256": digest(directory / "response.json")}
            return {"mode": "process_group_termination" if terminate else "MCP_cancellation_notification", "cancel_sent_ns": sent,
                    "response": response_summary, "sentinel_written_after_cancel": modified_after_cancel,
                    "process_stopped": process.poll() is not None, "source_native_unchanged": digest(native) == before,
                    "status": ("pass" if process.poll() is not None and not sentinel.exists() and digest(native) == before else "fail") if terminate else
                              ("fail" if modified_after_cancel else "inconclusive")}
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)


async def run(cli: Path, python: Path, root: Path) -> dict:
    start = time.perf_counter()
    report = {"timestamp": utc_timestamp(), "paramaitric_commit": current_commit(), "solidcraft_binary_sha256": digest(cli),
              "binary": str(cli), "independent_python": str(python), "cases": {}, "decision": "not_decided"}
    report["fixture_sha256"] = {name: digest(ROOT / "evaluations/cases" / name) for name in
                               ("plate_centered_hole_success.json", "bracket_success.json")}
    for kind in ("plate", "bracket"):
        report["cases"][kind] = await family(cli, python, root / kind, kind)
    if report["cases"]["bracket"]["status"] == "pass":
        report["fillet"] = await fillet(cli, python, root / "fillet", root / "bracket/edited.solidcraft")
    if report["cases"]["plate"]["status"] == "pass":
        import shutil
        scratch = root / "failure-tests"
        scratch.mkdir()
        native = scratch / "baseline.solidcraft"
        shutil.copyfile(root / "plate/initial.solidcraft", native)
        report["failure_tests"] = await failures(cli, python, root / "failure-session", native)
        for terminate in (False, True):
            name = "process_cancellation" if terminate else "protocol_cancellation"
            try:
                report[name] = await asyncio.to_thread(cancellation, cli, root / name, native, terminate=terminate)
            except Exception as exc:
                report[name] = {"status": "fail", "error": str(exc)}
    report["elapsed_seconds"] = time.perf_counter() - start
    report["geometry_status"] = "pass" if all(c["status"] == "pass" for c in report["cases"].values()) else "fail"
    report["adoption_status"] = "not_qualified"
    report["interactive_UI"] = "not_run"
    report["decision_document"] = "docs/consolidation/solidcraft_evaluation.md"
    report["source_sha256"] = {p: digest(ROOT / p) for p in ("evaluations/solidcraft_eval.py", "evaluations/solidcraft_cases.py", "evaluations/solidcraft_readback.py")}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solidcraft-cli", type=Path, required=True)
    parser.add_argument("--cad-python", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="solidcraft-", dir=args.output_root.resolve()))
    async def bounded():
        async with asyncio.timeout(240):
            return await run(args.solidcraft_cli.absolute(), args.cad_python.absolute(), root)
    try:
        report = asyncio.run(bounded())
    except Exception as exc:
        report = {"status": "incomplete", "error": str(exc)}
    path = root / "evaluation.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(path), "cases": {k: v["status"] for k, v in report.get("cases", {}).items()}, "error": report.get("error")}))
    # Completing an experiment does not mean its engine-adoption gates passed.
    return int("error" in report or report.get("geometry_status") != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
