import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import jsonschema
import pytest

from cad_backends.cadgen import CadgenPlateBackend
from cad_backends.protocol import Measurements, Part
from mcp_server.errors import WorkflowFailure
from mcp_server.mcp_entrypoint import call_tool
from mcp_server.server import ParamAIToolServer
from mcp_server.utility_plate import CenteredPlate
from mcp_server.utility_runtime import REQUEST_CANCEL, RequestCancellation, UtilityPlateRuntime, runtime_from_environment


def runtime(root, python=None, **kwargs):
    return UtilityPlateRuntime(CadgenPlateBackend(Path(python or sys.executable), root, **kwargs))


def payload(root):
    return {"workflow": "plate_with_hole", "parameters": {
        "width_cm": 80, "height_cm": 60, "thickness_cm": 5, "hole_diameter_cm": 10,
        "hole_center_x_cm": 40, "hole_center_y_cm": 30, "units": "mm", "output_path": str(root / "plate.stl")}}


def staged_report(root, spec=None):
    """Synthetic evidence for persistence tests, never claimed as CAD geometry."""
    spec = spec or CenteredPlate()
    directory = root / "plate-synthetic"
    directory.mkdir()
    artifacts = {}
    for key, name in {"step": "plate.step", "stl": "plate.stl", "recipe": "recipe.py",
                      "parameters": "parameters.json", "runtime": "runtime.json", "mesh_verification": "mesh-verification.json"}.items():
        path = directory / name
        path.write_text(json.dumps(spec.parameters()) if key == "parameters" else f"synthetic {key}")
        artifacts[key] = str(path)
    hashes = {key: hashlib.sha256(Path(path).read_bytes()).hexdigest() for key, path in artifacts.items()}
    record = {"ok": True, "acceptance": "geometry_verified", "directory": str(directory),
              "backend": "cadgen-build123d", "recipe": spec.parameters(), "artifacts": artifacts,
              "artifact_sha256": hashes, "recipe_sha256": hashes["parameters"], "editability": "parameterized_recipe",
              "measurements": {"body_count": 1, "width_mm": spec.width_mm, "height_mm": spec.height_mm,
                               "thickness_mm": spec.thickness_mm, "hole_diameter_mm": spec.hole_diameter_mm}}
    (directory / "geometry-verification.json").write_text(json.dumps(record))
    return record


def build_synthetic(r, monkeypatch, p=None):
    monkeypatch.setattr("mcp_server.utility_runtime.build_plate", lambda backend, spec, root: staged_report(root, spec))
    return r.build(p or payload(r.root))


def test_cancellation_after_geometry_before_acceptance_is_not_reloadable(tmp_path, monkeypatch):
    r = runtime(tmp_path)
    original = r._accept
    def cancel_before_acceptance(report):
        assert json.loads(Path(report["directory"], "geometry-verification.json").read_text())["acceptance"] == "geometry_verified"
        r.cancel_active()
        original(report)
    monkeypatch.setattr(r, "_accept", cancel_before_acceptance)
    with pytest.raises(WorkflowFailure) as error:
        build_synthetic(r, monkeypatch)
    assert error.value.classification == "cancelled"
    directory = tmp_path / "plate-synthetic"
    assert not (directory / "verification.json").exists()
    assert not list(directory.glob(".acceptance-*"))
    with pytest.raises(ValueError, match="No accepted"):
        runtime(tmp_path)._record(directory.name)
    assert not r._transaction.locked()


def test_atomic_acceptance_is_complete_and_cancellation_after_commit_is_too_late(tmp_path, monkeypatch):
    r = runtime(tmp_path)
    original = os.replace
    def publish(source, destination):
        with pytest.raises(ValueError, match="No accepted"):
            runtime(tmp_path)._record("plate-synthetic")
        candidate = json.loads(Path(source).read_text())
        assert candidate["acceptance"] == "accepted" and candidate["revision_id"] == "plate-synthetic"
        original(source, destination)
    monkeypatch.setattr("mcp_server.utility_runtime.os.replace", publish)
    cancel = RequestCancellation()
    token = REQUEST_CANCEL.set(cancel)
    try:
        result = build_synthetic(r, monkeypatch)
    finally:
        REQUEST_CANCEL.reset(token)
    cancel.set()
    assert cancel.committed and not cancel.is_set()
    assert runtime(tmp_path)._record(result["revision_id"]) == result


def test_acceptance_write_failure_never_publishes(tmp_path, monkeypatch):
    r = runtime(tmp_path)
    def fail(*args):
        raise OSError("failed publication")
    monkeypatch.setattr("mcp_server.utility_runtime.os.replace", fail)
    with pytest.raises(OSError):
        build_synthetic(r, monkeypatch)
    assert not (tmp_path / "plate-synthetic" / "verification.json").exists()
    assert not list((tmp_path / "plate-synthetic").glob(".acceptance-*"))
    assert not r._transaction.locked()


@pytest.mark.parametrize("artifact", ["step", "stl", "recipe", "parameters", "runtime", "mesh_verification"])
@pytest.mark.parametrize("change", ["modify", "delete"])
def test_changed_artifacts_block_inspection_and_regeneration(tmp_path, monkeypatch, artifact, change):
    r = runtime(tmp_path)
    result = build_synthetic(r, monkeypatch)
    path = Path(result["artifacts"][artifact])
    if change == "modify":
        path.write_text("changed externally")
    else:
        path.unlink()
    fresh = runtime(tmp_path)
    def forbidden(*args):
        raise AssertionError("modified evidence must fail before CAD execution")
    monkeypatch.setattr(fresh.backend, "inspect_export", forbidden)
    monkeypatch.setattr("mcp_server.utility_runtime.regenerate_plate", forbidden)
    s = ParamAIToolServer(utility_runtime=fresh)
    for method, p in (("inspect_design", {"operation": "get_revision", "parameters": {"revision_id": result["revision_id"]}}),
                      ("build_workflow", {"workflow": "plate_with_hole", "revision_id": result["revision_id"], "parameters": {"width_cm": 10}})):
        failure = call_tool(s, method, p)
        assert failure["classification"] == "verification_failed"
        assert failure["stage"] == "revision_integrity"
        assert failure["partial_result"]["modified_artifacts"] == [artifact]


def test_missing_hash_and_staging_records_cannot_be_reopened(tmp_path, monkeypatch):
    r = runtime(tmp_path)
    report = build_synthetic(r, monkeypatch)
    record = Path(report["directory"], "verification.json")
    report["artifact_sha256"].pop("stl")
    record.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="hashes"):
        r._record(report["revision_id"])
    report["acceptance"] = "geometry_verified"
    record.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="not an accepted"):
        r._record(report["revision_id"])


@pytest.mark.parametrize("destination", [None, "part.stl"])
def test_default_output_uses_configured_root(tmp_path, monkeypatch, destination):
    r = runtime(tmp_path)
    p = payload(tmp_path)
    if destination is None:
        p["parameters"].pop("output_path")
    else:
        p["parameters"]["output_path"] = destination
    from mcp_server.schema_generation import tool_input_schema
    jsonschema.validate({"payload": p}, r.tool_schema("cad_build", tool_input_schema("cad_build", "build_workflow")))
    result = build_synthetic(r, monkeypatch, p)
    assert result["acceptance"] == "accepted"
    assert Path(result["artifacts"]["stl"]).is_relative_to(tmp_path)


@pytest.mark.parametrize("failure", [False, True])
def test_health_probe_always_cleans_its_directory(tmp_path, monkeypatch, failure):
    backend = CadgenPlateBackend(Path(sys.executable), tmp_path)
    retained = tmp_path / "plate-retained"
    retained.mkdir()
    def probe(self, part, action, request):
        assert action == "health" and part.directory.is_dir()
        (part.directory / "worker.log").write_text("dependency probe")
        if failure:
            raise WorkflowFailure("Missing dependency", stage="health", classification="backend_error")
        return {"ok": True, "versions": {}}
    monkeypatch.setattr(CadgenPlateBackend, "_run", probe)
    if failure:
        with pytest.raises(WorkflowFailure, match="Missing dependency"):
            backend.probe()
    else:
        assert backend.probe()["ok"]
    assert list(tmp_path.iterdir()) == [retained]


def test_backend_configuration_is_explicit_and_fails_closed(tmp_path, monkeypatch):
    monkeypatch.delenv("PARAMAITRIC_CAD_BACKEND", raising=False)
    assert runtime_from_environment() is None
    monkeypatch.setenv("PARAMAITRIC_CAD_BACKEND", "automatic")
    with pytest.raises(ValueError):
        runtime_from_environment()
    monkeypatch.setenv("PARAMAITRIC_CAD_BACKEND", "cadgen")
    monkeypatch.delenv("PARAMAITRIC_CAD_PYTHON", raising=False)
    with pytest.raises(ValueError):
        runtime_from_environment()
    monkeypatch.setenv("PARAMAITRIC_CAD_PYTHON", sys.executable)
    monkeypatch.setenv("PARAMAITRIC_CAD_OUTPUT_ROOT", str(tmp_path))
    assert runtime_from_environment().root == tmp_path


def test_open_scope_requirements_and_schema_are_honest(tmp_path):
    r = runtime(tmp_path)
    from mcp_server.schema_generation import tool_input_schema
    schema = r.tool_schema("cad_build", tool_input_schema("cad_build", "build_workflow"))
    jsonschema.validate({"payload": payload(tmp_path)}, schema)
    edit = {"payload": {"workflow": "plate_with_hole", "revision_id": "plate-123abc", "parameters": {"width_cm": 10}}}
    jsonschema.validate(edit, schema)
    for bad in ({"hole_center_x_cm": 3}, {}, {"units": "mm"}, {"width_cm": -1}):
        edit["payload"]["parameters"] = bad
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(edit, schema)
    result = r.recommend({"intent": "plate with hole"})
    assert [c["name"] for c in result["candidates"]] == ["plate_with_hole"]
    assert result["match_trace"]["considered"] == 1
    assert "off-center holes" in result["candidates"][0]["not_for"]
    assert r.recommend({"intent": "pipe clamp"})["candidates"] == []


def test_no_unsupported_workflow_or_primitive_can_fall_back_to_fusion(tmp_path):
    class ForbiddenBridge:
        def send(self, *args):
            raise AssertionError("Fusion must never be called")
    s = ParamAIToolServer(ForbiddenBridge(), utility_runtime=runtime(tmp_path))
    result = call_tool(s, "build_workflow", {"workflow": "spacer", "parameters": {}})
    assert result["classification"] == "unsupported_capability"
    result = call_tool(s, "new_design", {"name": "must not build"})
    assert result["classification"] == "unsupported_capability"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("change", [{"width_cm": float("nan")}, {"width_cm": True}, {"hole_center_x_cm": 35}, {"extra": 1}])
def test_invalid_or_unsupported_parameters_reject_before_mutation(tmp_path, change):
    p = payload(tmp_path)
    p["parameters"].update(change)
    result = call_tool(ParamAIToolServer(utility_runtime=runtime(tmp_path)), "build_workflow", p)
    assert result["ok"] is False
    assert result["classification"] in {"validation_error", "unsupported_capability"}
    assert list(tmp_path.iterdir()) == []


def test_revision_paths_and_output_root_cannot_escape(tmp_path):
    r = runtime(tmp_path)
    s = ParamAIToolServer(utility_runtime=r)
    for revision in ("../elsewhere", "/tmp/part", "plate-../part", "plate-missing"):
        result = call_tool(s, "build_workflow", {"workflow": "plate_with_hole", "revision_id": revision, "parameters": {"width_cm": 10}})
        assert result["classification"] == "validation_error"
    p = payload(tmp_path)
    p["parameters"]["output_path"] = str(tmp_path.parent / "outside.stl")
    assert call_tool(s, "build_workflow", p)["classification"] == "validation_error"
    link = tmp_path / "plate-link"
    link.symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        r._record("plate-link")


def test_failed_required_readback_stops_guided_transaction(tmp_path, monkeypatch):
    r = runtime(tmp_path)
    calls = []
    monkeypatch.setattr(r.backend, "apply", lambda *args: calls.append("mutation"))
    monkeypatch.setattr(r.backend, "inspect", lambda *args: Measurements({"body_count": 2}, "fault", "synthetic"))
    monkeypatch.setattr(r.backend, "export", lambda *args: calls.append("export"))
    result = call_tool(ParamAIToolServer(utility_runtime=r), "build_workflow", payload(tmp_path))
    assert result["classification"] == "verification_failed"
    assert calls == ["mutation"]
    assert not r._transaction.locked()


def test_overlapping_transaction_is_rejected(tmp_path):
    r = runtime(tmp_path)
    r._enter()
    try:
        result = call_tool(ParamAIToolServer(utility_runtime=r), "build_workflow", payload(tmp_path))
        assert result["classification"] == "state_drift"
    finally:
        r._leave()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["cancelled", "timeout"])
def test_worker_process_group_is_stopped(tmp_path, monkeypatch, kind):
    """Exercise real parent/child processes, without needing a CAD environment."""
    directory = tmp_path / "plate-test"
    directory.mkdir()
    b = CadgenPlateBackend(Path(sys.executable), tmp_path, timeout=0.3 if kind == "timeout" else 5)
    cancelled = threading.Event()
    b.cancel_event = cancelled
    original = subprocess.Popen
    parent = []
    helper = "import subprocess,sys,time; from pathlib import Path; child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); Path('child.pid').write_text(str(child.pid)); time.sleep(30)"
    def slow_process(command, **kwargs):
        p = original([sys.executable, "-I", "-c", helper], **kwargs)
        parent.append(p)
        return p
    monkeypatch.setattr("cad_backends.cadgen.adapter.subprocess.Popen", slow_process)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(b._run, Part(directory), "apply", {})
        deadline = time.monotonic() + 2
        while not (directory / "child.pid").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert (directory / "child.pid").exists()
        if kind == "cancelled":
            cancelled.set()
        with pytest.raises(WorkflowFailure) as error:
            future.result(timeout=3)
    assert error.value.classification == kind
    assert parent[0].poll() is not None
    child = int((directory / "child.pid").read_text())
    stat = Path(f"/proc/{child}/stat")
    try:
        state = stat.read_text().split()[2]
    except (FileNotFoundError, ProcessLookupError):
        state = "gone"
    assert state in {"gone", "Z"}


def test_open_mcp_surface_and_request_local_cancellation(tmp_path, monkeypatch):
    import mcp_server.mcp_entrypoint as entrypoint
    with monkeypatch.context() as env:
        env.setenv("PARAMAITRIC_CAD_BACKEND", "cadgen")
        env.setenv("PARAMAITRIC_CAD_PYTHON", sys.executable)
        env.setenv("PARAMAITRIC_CAD_OUTPUT_ROOT", str(tmp_path))
        env.delenv("PARAMAITRIC_PROFILE", raising=False)
        importlib.reload(entrypoint)
        assert set(entrypoint.registered_tools) == {"cad_health", "cad_recommend_workflow", "cad_get_requirements", "cad_build", "cad_inspect"}
        assert "Omit output_path" in entrypoint.cad_request("plate")
        assert "Documents/ParamAItric Exports" not in entrypoint.cad_request("plate")
        entered, stopped = threading.Event(), threading.Event()
        def wait_for_cancel(p):
            cancel = REQUEST_CANCEL.get()
            assert cancel is not None
            entered.set()
            if cancel.wait(2):
                stopped.set()
            return {"ok": False}
        env.setattr(entrypoint._server.utility_runtime, "build", wait_for_cancel)
        fn = entrypoint.mcp._tool_manager._tools["cad_build"].fn
        async def scenario():
            task = asyncio.create_task(fn(payload(tmp_path)))
            for _ in range(200):
                if entered.is_set():
                    break
                await asyncio.sleep(0.005)
            assert entered.is_set()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            for _ in range(200):
                if stopped.is_set():
                    break
                await asyncio.sleep(0.005)
            assert stopped.is_set()
        asyncio.run(scenario())
        # When acceptance wins, late task cancellation must return the accepted
        # result rather than claiming that the committed request was cancelled.
        committed, release = threading.Event(), threading.Event()
        def commit_then_wait(p):
            REQUEST_CANCEL.get().commit(lambda: None)
            committed.set()
            assert release.wait(2)
            return {"ok": True, "acceptance": "accepted"}
        env.setattr(entrypoint._server.utility_runtime, "build", commit_then_wait)
        async def late_cancellation():
            task = asyncio.create_task(fn(payload(tmp_path)))
            for _ in range(200):
                if committed.is_set():
                    break
                await asyncio.sleep(0.005)
            assert committed.is_set()
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()  # Repeated late cancellation also cannot undo acceptance.
            release.set()
            assert (await task)["acceptance"] == "accepted"
        asyncio.run(late_cancellation())
    importlib.reload(entrypoint)


def test_real_guided_build_edit_and_readonly_export_inspection(tmp_path):
    python = os.environ.get("PARAMAITRIC_CAD_PYTHON")
    if not python:
        pytest.skip("Set PARAMAITRIC_CAD_PYTHON for the real guided geometry gate")
    r = runtime(tmp_path, python)
    s = ParamAIToolServer(utility_runtime=r)
    a = call_tool(s, "build_workflow", payload(tmp_path))
    assert a["ok"], a
    # Accepted revisions survive a new runtime instance, with no token rebinding.
    s = ParamAIToolServer(utility_runtime=runtime(tmp_path, python))
    b = call_tool(s, "build_workflow", {"workflow": "plate_with_hole", "revision_id": a["revision_id"], "parameters": {"width_cm": 100, "units": "mm"}})
    assert b["ok"], b
    assert b["review"]["previous_model_path"] == a["artifacts"]["step"]
    f = b["measurements"]
    assert f["width_mm"] == 100 and f["hole_center_x_mm"] == 50 and f["hole_center_y_mm"] == 30
    before = {p: p.read_bytes() for p in Path(b["directory"]).glob("*.step")}
    inspection = {"operation": "get_revision", "parameters": {"revision_id": b["revision_id"]}}
    result = call_tool(s, "inspect_design", inspection)
    assert result["ok"] and result["measurements"]["through_hole"]
    assert all(p.read_bytes() == blob for p, blob in before.items())
    Path(b["artifacts"]["step"]).write_text("malformed final STEP")
    assert call_tool(s, "inspect_design", inspection)["ok"] is False
