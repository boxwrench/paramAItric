import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib
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
from mcp_server.utility_runtime import REQUEST_CANCEL, UtilityPlateRuntime, runtime_from_environment


def runtime(root, python=None, **kwargs):
    return UtilityPlateRuntime(CadgenPlateBackend(Path(python or sys.executable), root, **kwargs))


def payload(root):
    return {"workflow": "plate_with_hole", "parameters": {
        "width_cm": 80, "height_cm": 60, "thickness_cm": 5, "hole_diameter_cm": 10,
        "hole_center_x_cm": 40, "hole_center_y_cm": 30, "units": "mm", "output_path": str(root / "plate.stl")}}


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
    assert not stat.exists() or stat.read_text().split()[2] == "Z"


def test_open_mcp_surface_and_request_local_cancellation(tmp_path, monkeypatch):
    import mcp_server.mcp_entrypoint as entrypoint
    with monkeypatch.context() as env:
        env.setenv("PARAMAITRIC_CAD_BACKEND", "cadgen")
        env.setenv("PARAMAITRIC_CAD_PYTHON", sys.executable)
        env.setenv("PARAMAITRIC_CAD_OUTPUT_ROOT", str(tmp_path))
        env.delenv("PARAMAITRIC_PROFILE", raising=False)
        importlib.reload(entrypoint)
        assert set(entrypoint.registered_tools) == {"cad_health", "cad_recommend_workflow", "cad_get_requirements", "cad_build", "cad_inspect"}
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
