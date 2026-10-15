"""Real native external-edit/revalidation proof. Headless edits are not human/UI evidence."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import traceback
import time

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from cad_backends.solidcraft.adapter import SolidCraftBackend, digest
from evaluations.runner.metadata import current_commit, utc_timestamp
from mcp_server.errors import WorkflowFailure
from mcp_server.solidcraft_runtime import SolidCraftRuntime

ROOT = Path(__file__).resolve().parents[1]


def unchanged(records):
    return all(digest(path) == record["artifact_sha256"][key] for record in records for key, path in record["artifacts"].items())


def native_edit(backend, editable, actions, *, fresh=False):
    """Controlled native editor surrogate; never presented as a human interaction."""
    path = Path(editable["document_path"])
    log = []
    with backend._session(path.parent, time.monotonic() + backend.timeout) as client:
        if not fresh:
            client.call("open", {"path": str(path)})
        for name, args, allow_error in actions:
            if allow_error:
                response = client.request("tools/call", {"name": name, "arguments": args})
            else:
                response = client.call(name, args)
            log.append({"tool": name, "arguments": args, "result": response})
        client.call("save", {"path": str(path)})
    return {"method": "headless_public_native_MCP_not_human_UI", "calls": log, "saved_sha256": digest(path)}


async def run(cli, python, output_root):
    output_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="external-", dir=output_root))
    backend = SolidCraftBackend(cli, python, root)
    report = {"timestamp": utc_timestamp(), "source_commit": current_commit(), "directory": str(root), "status": "fail",
              "host": {"platform": platform.platform(), "architecture": platform.machine()}, "families": {}, "failures": {},
              "human_native_desktop_UI": "not_run", "Strix_Halo": "not_run", "model_in_loop": "not_run",
              "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in [*sorted((ROOT / "cad_backends/solidcraft").glob("*.py")),
                 ROOT / "mcp_server/solidcraft_runtime.py", ROOT / "mcp_server/mcp_entrypoint.py", ROOT / "evaluations/solidcraft_external.py"]}}
    env = {**os.environ, "PARAMAITRIC_CAD_BACKEND": "solidcraft", "PARAMAITRIC_SOLIDCRAFT_CLI": str(cli),
           "PARAMAITRIC_CAD_PYTHON": str(python), "PARAMAITRIC_CAD_OUTPUT_ROOT": str(root)}
    env.pop("PARAMAITRIC_PROFILE", None)
    accepted = []
    began = time.perf_counter()
    try:
        with (root / "mcp.log").open("w") as log:
            async with stdio_client(StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.mcp_entrypoint"], cwd=str(ROOT), env=env), errlog=log) as (read, write):
                request_ids = []
                class CaptureWrite:
                    async def __aenter__(self):
                        await write.__aenter__()
                        return self
                    async def __aexit__(self, *args):
                        return await write.__aexit__(*args)
                    async def send(self, message):
                        wire = message.message.root
                        if getattr(wire, "method", None) == "tools/call":
                            request_ids.append(wire.id)
                        await write.send(message)
                async with ClientSession(read, CaptureWrite()) as client:
                    await client.initialize()
                    report["tools"] = [t.name for t in (await client.list_tools()).tools]
                    assert set(report["tools"]) == {"cad_health", "cad_recommend_workflow", "cad_get_requirements", "cad_build", "cad_inspect"}
                    async def call(name, payload=None, *, reject=False):
                        response = await client.call_tool(name, {} if payload is None else {"payload": payload})
                        result = response.structuredContent or json.loads(next(c.text for c in response.content if c.type == "text"))
                        assert result.get("ok", True) is (False if reject else True), result
                        return result
                    report["health"] = await call("cad_health")
                    async def prepare(parent):
                        return await call("cad_build", {"workflow": parent["workflow"], "revision_id": parent["revision_id"], "external_edit": {"action": "prepare"}})
                    def submission(parent, editable, width):
                        return {"workflow": parent["workflow"], "revision_id": parent["revision_id"],
                                "external_edit": {"action": "revalidate", "edit_id": editable["edit_id"]},
                                "parameters": {"width_cm": width, "units": "mm"}}
                    for kind, workflow, p, width in (
                        ("plate", "plate_with_hole", {"width_cm": 80, "height_cm": 60, "thickness_cm": 5, "hole_diameter_cm": 10, "hole_center_x_cm": 40, "hole_center_y_cm": 30}, 100),
                        ("bracket", "bracket", {"width_cm": 50, "height_cm": 80, "thickness_cm": 5, "leg_thickness_cm": 5}, 70)):
                        parent = await call("cad_build", {"workflow": workflow, "parameters": {**p, "units": "mm"}})
                        accepted.append(parent)
                        editable = await prepare(parent)
                        editing = await asyncio.to_thread(native_edit, backend, editable, [("set_parameter", {"name": "width", "value": f"{width} mm"}, False)])
                        result = await call("cad_build", submission(parent, editable, width))
                        accepted.append(result)
                        inspected = await call("cad_inspect", {"operation": "get_revision", "parameters": {"revision_id": result["revision_id"]}})
                        assert abs(inspected["measurements"]["width"] - width) < 0.01
                        assert result["parent_revision_id"] == parent["revision_id"] and result["external_edit"]["submitted_sha256"] == editing["saved_sha256"]
                        assert result["acceptance"] == "accepted" and all(c["passed"] for c in result["verification_signals"])
                        assert unchanged(accepted)
                        if kind == "plate":assert abs(inspected["measurements"]["bore_x"] - 50) < 0.01
                        report["families"][kind] = {"initial": parent, "editable_copy": editable, "native_edit": editing, "accepted_edit": result, "inspection": inspected}
                    parent = report["families"]["plate"]["initial"]
                    actions = {
                        "invalid_native_dimension": [("set_parameter", {"name": "width", "value": "0 mm"}, True)],
                        "unexpected_dimension": [("set_parameter", {"name": "height", "value": "70 mm"}, False)],
                        "unsupported_feature_definition": [("execute", {"command": "timeline.edit", "params": {"feature": "Base", "set": {"extent": {"distance": "thickness+0 mm"}}}}, False)],
                        "broken_constraint_relationship": [("set_parameter", {"name": "d5", "value": "40 mm"}, False)],
                    }
                    for name, changes in actions.items():
                        editable = await prepare(parent)
                        editing = await asyncio.to_thread(native_edit, backend, editable, changes)
                        result = await call("cad_build", submission(parent, editable, 80), reject=True)
                        report["failures"][name] = {"result": result, "native_edit": editing, "prior_revisions_unchanged": unchanged(accepted)}
                        assert unchanged(accepted)
                    for name in ("corrupt_native", "missing_history", "arbitrary_static_import", "invalid_declared_dimensions", "altered_accepted_source", "outside_directory_write"):
                        editable = await prepare(parent)
                        request = submission(parent, editable, 80)
                        path = Path(editable["document_path"])
                        restore = None
                        if name == "corrupt_native":path.write_bytes(b"not a native CAD document")
                        elif name == "missing_history":await asyncio.to_thread(native_edit, backend, editable, [], fresh=True)
                        elif name == "arbitrary_static_import":
                            shutil.copyfile(parent["artifacts"]["step"], path.parent / "static.step")
                            changes = [("execute", {"command": "file.insert_step", "params": {"path": str(path.parent / "static.step")}}, False)]
                            changes += [("set_parameter", {"name": key, "value": f"{value} mm"}, False) for key, value in parent["parameters"].items()]
                            await asyncio.to_thread(native_edit, backend, editable, changes, fresh=True)
                        elif name == "invalid_declared_dimensions":request["parameters"]["width_cm"] = 0
                        elif name == "altered_accepted_source":
                            restore = Path(parent["artifacts"]["native"]), Path(parent["artifacts"]["native"]).read_bytes()
                            restore[0].write_bytes(b"fault injection: altered accepted source")
                        else:
                            request["external_edit"]["output_path"] = str(root.parent / "must-not-write.solidcraft")
                        try:
                            result = await call("cad_build", request, reject=True)
                        finally:
                            if restore:restore[0].write_bytes(restore[1])
                        assert unchanged(accepted)
                        report["failures"][name] = {"result": result, "prior_revisions_unchanged": True,
                            "fault_restored_by_test_harness": restore is not None}
                    assert not (root.parent / "must-not-write.solidcraft").exists()
                    # Cancel a real guided request after native construction has
                    # reached the independent reader, rather than before dispatch.
                    editable = await prepare(parent)
                    before = set(root.glob("solidcraft-*"))
                    pending = asyncio.create_task(client.call_tool("cad_build", {"payload": submission(parent, editable, 80)}))
                    deadline = time.monotonic() + 15
                    active = None
                    while time.monotonic() < deadline and not pending.done():
                        active = next((p for p in set(root.glob("solidcraft-*")) - before if (p / "reference/reader.log").exists()), None)
                        if active:break
                        await asyncio.sleep(0.01)
                    assert active is not None, "Could not observe independent verification before cancellation"
                    # The pinned MCP SDK does not emit a cancellation notification
                    # when its Python awaiter is cancelled. Send the protocol message
                    # explicitly for the captured public JSON-RPC request ID.
                    cancelled_request_id = request_ids[-1]
                    await client.send_notification(types.ClientNotification(types.CancelledNotification(
                        params=types.CancelledNotificationParams(requestId=cancelled_request_id, reason="external-edit regression"))))
                    try:
                        await asyncio.wait_for(asyncio.shield(pending), timeout=3)
                    except Exception:
                        if not pending.done():
                            pending.cancel()
                            try:await pending
                            except asyncio.CancelledError:pass
                    deadline = time.monotonic() + 5
                    ready = False
                    while time.monotonic() < deadline:
                        status = await client.call_tool("cad_build", {"payload": {"workflow": parent["workflow"], "revision_id": parent["revision_id"], "external_edit": {"action": "prepare"}}})
                        data = status.structuredContent or json.loads(next(c.text for c in status.content if c.type == "text"))
                        if data.get("ok"):ready = True;break
                        assert data.get("classification") == "state_drift", data
                        await asyncio.sleep(0.05)
                    assert ready and not (active / "verification.json").exists() and unchanged(accepted)
                    report["failures"]["guided_cancellation"] = {"status": "pass", "directory": str(active), "observed_reader_start": True,
                        "protocol_notification_sent": True, "request_id": cancelled_request_id,
                        "transaction_released": ready, "cancelled_revision_accepted": False, "prior_revisions_unchanged": True}
        # Terminate an actual candidate verification process to exercise the
        # backend's failure reporting. No debug hook is added to product code.
        runtime = SolidCraftRuntime(backend)
        parent = report["families"]["plate"]["initial"]
        editable = runtime.build({"workflow": parent["workflow"], "revision_id": parent["revision_id"], "external_edit": {"action": "prepare"}})
        original, killed = backend._process, []
        @contextmanager
        def interrupt(command, directory, deadline, label):
            with original(command, directory, deadline, label) as process:
                if label == "reader" and directory.parent == root:
                    process.kill(); killed.append(process.pid)
                yield process
        backend._process = interrupt
        try:
            try:runtime.build(submission(parent, editable, 80))
            except WorkflowFailure as exc:
                assert exc.classification == "verification_failed" and killed
                report["failures"]["interrupted_verification"] = {"status": "pass", "classification": exc.classification,
                    "killed_reader_pids": killed, "prior_revisions_unchanged": unchanged(accepted), "diagnostics": exc.partial_result}
            else:raise AssertionError("Interrupted verification must not accept")
        finally:backend._process = original
        assert unchanged(accepted)
        assert len(list(root.glob("*/verification.json"))) == 4
        report.update(status="pass", all_prior_artifact_hashes_verified=True, accepted_revision_count=4)
    except Exception as exc:
        report["failure"] = repr(exc)
        report["traceback"] = traceback.format_exc()
    report["wall_seconds"] = time.perf_counter() - began
    (root / "evidence.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "evidence": str(root / "evidence.json"), "wall_seconds": report["wall_seconds"], "failure": report.get("failure")}))
    return report["status"] == "pass"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solidcraft-cli", type=Path, required=True)
    parser.add_argument("--cad-python", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not all(p.is_absolute() for p in (args.solidcraft_cli, args.cad_python, args.output_root)):parser.error("Use absolute paths")
    return asyncio.run(asyncio.wait_for(run(args.solidcraft_cli, args.cad_python, args.output_root), timeout=240))


if __name__ == "__main__":
    raise SystemExit(int(not main()))
