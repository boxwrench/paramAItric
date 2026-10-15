"""Contract/integrity guards are synthetic; marked real tests require pinned CAD."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
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

from cad_backends.solidcraft.adapter import FILES, SolidCraftBackend, check_result, digest, fail
from cad_backends.solidcraft.recipes import BRACKET, PLATE
from cad_backends.solidcraft.readback import verify
from mcp_server.errors import WorkflowFailure
from mcp_server.solidcraft_runtime import SolidCraftRuntime
from mcp_server.utility_runtime import REQUEST_CANCEL, RequestCancellation, runtime_from_environment


class SyntheticBackend:
    capabilities = SolidCraftBackend.capabilities
    cancel_event = None

    def __init__(self, root):
        self.output_root = root
        self.calls = []

    def probe(self):
        return {"versions": {"synthetic": True}}

    def build(self, directory, kind, p, previous=None):
        self.calls.append((kind, p, previous))
        facts = {"body_count": 1, "valid": True, "width": p["width"], "height": p["height"], "thickness": p["thickness"]}
        for name in FILES.values():
            (directory / name).write_text(json.dumps(p) if name == "parameters.json" else "synthetic evidence")
        return {"measurements": facts, "checks": [{"passed": True}]}

    def inspect(self, record):
        return {"measurements": {"body_count": 1}, "checks": [{"passed": True}]}


def runtime(root):
    return SolidCraftRuntime(SyntheticBackend(root))


def payload(kind="plate", width=None):
    p = dict(PLATE if kind == "plate" else BRACKET)
    if width:
        p["width"] = width
    params = {name + "_cm": value for name, value in p.items() if name != "leg"}
    if kind == "plate":
        params.update(hole_center_x_cm=p["width"] / 2, hole_center_y_cm=p["height"] / 2)
    else:
        params["leg_thickness_cm"] = p["leg"]
    params["units"] = "mm"
    return {"workflow": "plate_with_hole" if kind == "plate" else "bracket", "parameters": params}


@pytest.mark.parametrize("kind", ["plate", "bracket"])
def test_guided_build_edit_schemas_and_persistent_native_integrity(tmp_path, kind):
    r = runtime(tmp_path)
    schema = r.tool_schema("cad_build", {"properties": {}})
    jsonschema.validate({"payload": payload(kind)}, schema)
    first = r.build(payload(kind))
    assert first["acceptance"] == "accepted"
    assert first["editability"] == "native_feature_history"
    assert r._record(first["revision_id"])["artifact_sha256"]["native"]
    edit = {"workflow": payload(kind)["workflow"], "revision_id": first["revision_id"], "parameters": {"width_cm": 100, "units": "mm"}}
    jsonschema.validate({"payload": edit}, schema)
    second = runtime(tmp_path).build(edit)
    assert second["parameters"]["width"] == 100
    assert second["review"]["previous_model_path"] == first["artifacts"]["step"]
    result = runtime(tmp_path).inspect({"operation": "get_revision", "parameters": {"revision_id": second["revision_id"]}})
    assert result["ok"]


@pytest.mark.parametrize("artifact", list(FILES))
def test_all_accepted_artifacts_are_immutable_on_inspection_and_edit(tmp_path, artifact):
    r = runtime(tmp_path)
    first = r.build(payload())
    Path(first["artifacts"][artifact]).write_text("modified")
    for action in (lambda: r.inspect({"operation": "get_revision", "parameters": {"revision_id": first["revision_id"]}}),
                   lambda: r.build({"workflow": "plate_with_hole", "revision_id": first["revision_id"], "parameters": {"width_cm": 10}})):
        with pytest.raises(WorkflowFailure) as exc:
            action()
        assert exc.value.stage == "revision_integrity"
        assert exc.value.partial_result["modified_artifacts"] == [artifact]
    assert len(r.backend.calls) == 1


@pytest.mark.parametrize("change", [{"width_cm": 0}, {"width_cm": True}, {"width_cm": float("nan")}, {"width_cm": 10001},
    {"hole_center_x_cm": 39}, {"plane": "xz"}, {"fillet_radius_cm": 1}, {"output_path": "/tmp/escape.stl"}, {"output_path": "part.step"}])
def test_invalid_input_rejected_before_worker_or_artifacts(tmp_path, change):
    r = runtime(tmp_path)
    p = payload()
    p["parameters"].update(change)
    with pytest.raises((ValueError, WorkflowFailure)):
        r.build(p)
    assert not r.backend.calls and not list(tmp_path.iterdir())


def test_bracket_requires_non_degenerate_legs_and_explicit_supported_operations(tmp_path):
    r = runtime(tmp_path)
    p = payload("bracket")
    p["parameters"]["leg_thickness_cm"] = 50
    with pytest.raises(ValueError):
        r.build(p)
    p["workflow"] = "filleted_bracket"
    with pytest.raises(WorkflowFailure) as exc:
        r.build(p)
    assert exc.value.classification == "unsupported_capability"
    for revision in ("../escape", "plate-previous", "solidcraft-missing"):
        with pytest.raises(ValueError):
            r._record(revision)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("when", ["before_commit", "after_commit"])
def test_acceptance_linearizes_with_request_cancellation(tmp_path, monkeypatch, when):
    r = runtime(tmp_path)
    token = RequestCancellation()
    context = REQUEST_CANCEL.set(token)
    original = r._accept
    def accept(report):
        if when == "before_commit":
            token.set()
        original(report)
        if when == "after_commit":
            token.set()
    monkeypatch.setattr(r, "_accept", accept)
    try:
        if when == "before_commit":
            with pytest.raises(WorkflowFailure) as exc:
                r.build(payload())
            assert exc.value.classification == "cancelled"
            assert not list(tmp_path.glob("*/verification.json"))
            assert list(tmp_path.glob("*/geometry-verification.json"))
        else:
            result = r.build(payload())
            assert result["acceptance"] == "accepted" and not token.is_set()
            assert r._record(result["revision_id"])
    finally:
        REQUEST_CANCEL.reset(context)
    assert not r._transaction.locked()


def test_failed_verification_never_publishes_and_preserves_prior_revision(tmp_path, monkeypatch):
    r = runtime(tmp_path)
    first = r.build(payload())
    before = {key: digest(path) for key, path in first["artifacts"].items()}
    def failed(*args):
        fail("bad geometry", stage="verify_geometry", classification="verification_failed")
    monkeypatch.setattr(r.backend, "build", failed)
    with pytest.raises(WorkflowFailure):
        r.build({"workflow": "plate_with_hole", "revision_id": first["revision_id"], "parameters": {"width_cm": 10}})
    assert {key: digest(path) for key, path in first["artifacts"].items()} == before
    assert len(list(tmp_path.glob("*/verification.json"))) == 1
    assert not r._transaction.locked()


@pytest.mark.parametrize("data", [{"errors": ["no closed profile"]}, {"timeline": [{"error": "missing body"}]},
    {"timeline": [{"suppressed": True}]}, {"failed": True}, {"error": "bad state"}, {"timeline": None}])
def test_native_errors_block_even_when_isError_is_false(data):
    with pytest.raises(WorkflowFailure):
        check_result({"isError": False, "content": [{"type": "text", "text": json.dumps(data)}]})


def unpinned_backend(root, timeout=2):
    """Bypass binary setup for testing actual process ownership, never CAD proof."""
    b = object.__new__(SolidCraftBackend)
    b.python, b.output_root, b.timeout, b.cancel_event = Path(sys.executable), root, timeout, threading.Event()
    return b


@pytest.mark.parametrize("reason", ["cancelled", "timeout"])
def test_actual_process_group_stops_without_trusting_native_cancellation(tmp_path, reason):
    b = unpinned_backend(tmp_path)
    sentinel = tmp_path / "after-cancel"
    helper = "import subprocess,sys,time;from pathlib import Path; c=subprocess.Popen([sys.executable,'-c',\"import time;from pathlib import Path;time.sleep(2);Path('after-cancel').write_text('bad')\"]);Path('child.pid').write_text(str(c.pid));time.sleep(30)"
    parent = []
    def work():
        deadline = time.monotonic() + (0.3 if reason == "timeout" else 5)
        with b._process([sys.executable, "-I", "-c", helper], tmp_path, deadline, "test") as process:
            parent.append(process)
            while True:
                b._guard(deadline)
                time.sleep(0.01)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(work)
        deadline = time.monotonic() + 2
        while not (tmp_path / "child.pid").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert (tmp_path / "child.pid").exists()
        if reason == "cancelled":
            b.cancel_event.set()
        with pytest.raises(WorkflowFailure) as exc:
            future.result(timeout=3)
    assert exc.value.classification == reason
    assert parent[0].poll() is not None and not sentinel.exists()
    stat = Path(f"/proc/{(tmp_path / 'child.pid').read_text()}/stat")
    try:
        state = stat.read_text().split()[2]
    except (FileNotFoundError, ProcessLookupError):
        state = "gone"
    assert state in {"gone", "Z"}


def test_native_checkpoint_recovery_after_false_success_does_not_continue_editing(tmp_path, monkeypatch):
    b = unpinned_backend(tmp_path)
    native = tmp_path / "previous.solidcraft"
    native.write_text("preserved")
    directory = tmp_path / "scratch"
    directory.mkdir()
    calls = []
    class Client:
        def healthy(self, *args):
            return {"timeline": [{}], "params": [{}]}
        def call(self, tool, args):
            calls.append((tool, args))
            if tool == "set_parameter":
                return check_result({"isError": False, "content": [{"type": "text", "text": '{"errors":["bad feature"]}'}]})
            return {"checkpoint": "saved"}
    @contextmanager
    def session(*args):
        yield Client()
    monkeypatch.setattr(b, "_session", session)
    readbacks = []
    monkeypatch.setattr(b, "_verify_session", lambda *args: readbacks.append(args[-1]))
    with pytest.raises(WorkflowFailure) as exc:
        b.build(directory, "plate", {**PLATE, "width": 100, "height": 70},
                {"revision_id": "solidcraft-source", "parameters": PLATE, "artifacts": {"native": str(native)}, "artifact_sha256": {"native": digest(native)}})
    assert exc.value.partial_result["checkpoint_recovery"] == "independently_verified"
    assert [tool for tool, _ in calls].count("set_parameter") == 1
    assert readbacks == ["restored"] and native.read_text() == "preserved"
    assert not (directory / "part.solidcraft").exists()


def test_explicit_environment_and_five_tool_surface(tmp_path, monkeypatch):
    import cad_backends.solidcraft.adapter as adapter
    import mcp_server.mcp_entrypoint as entry
    with monkeypatch.context() as env:
        env.setattr(adapter, "SolidCraftBackend", SyntheticBackendFactory)
        env.setenv("PARAMAITRIC_CAD_BACKEND", "solidcraft")
        env.setenv("PARAMAITRIC_SOLIDCRAFT_CLI", "/tmp/pinned-cli")
        env.setenv("PARAMAITRIC_CAD_PYTHON", sys.executable)
        env.setenv("PARAMAITRIC_CAD_OUTPUT_ROOT", str(tmp_path))
        env.delenv("PARAMAITRIC_PROFILE", raising=False)
        assert isinstance(runtime_from_environment(), SolidCraftRuntime)
        importlib.reload(entry)
        assert set(entry.registered_tools) == {"cad_health", "cad_recommend_workflow", "cad_get_requirements", "cad_build", "cad_inspect"}
        assert "Omit output_path" in entry.cad_request("plate")
        assert entry._server.utility_runtime.health()["workflow_count"] == 2
    importlib.reload(entry)


def SyntheticBackendFactory(cli, python, root):
    return SyntheticBackend(root)


def test_real_native_build_reopen_edit_inspect_and_integrity(tmp_path):
    cli, python = os.environ.get("PARAMAITRIC_SOLIDCRAFT_CLI"), os.environ.get("PARAMAITRIC_CAD_PYTHON")
    if not cli or not python:
        pytest.skip("Set pinned PARAMAITRIC_SOLIDCRAFT_CLI and PARAMAITRIC_CAD_PYTHON for real geometry")
    r = SolidCraftRuntime(SolidCraftBackend(Path(cli), Path(python), tmp_path))
    assert r.health()["workflow_count"] == 2
    for kind in ("plate", "bracket"):
        first = r.build(payload(kind))
        original = dict(first["artifact_sha256"])
        r = SolidCraftRuntime(SolidCraftBackend(Path(cli), Path(python), tmp_path))
        second = r.build({"workflow": payload(kind)["workflow"], "revision_id": first["revision_id"],
                          "parameters": {"width_cm": 100 if kind == "plate" else 70, "units": "mm"}})
        assert all(check["passed"] for check in second["verification_signals"])
        assert second["measurements"]["width"] == pytest.approx(100 if kind == "plate" else 70, abs=0.01)
        if kind == "plate":
            assert second["measurements"]["bore_x"] == pytest.approx(50, abs=0.01)
        assert {key: digest(path) for key, path in first["artifacts"].items()} == original
        assert r.inspect({"operation": "get_revision", "parameters": {"revision_id": second["revision_id"]}})["ok"]
        Path(second["artifacts"]["native"]).write_text("changed native")
        with pytest.raises(WorkflowFailure) as exc:
            r.inspect({"operation": "get_revision", "parameters": {"revision_id": second["revision_id"]}})
        assert exc.value.stage == "revision_integrity"


def test_real_native_ignoring_protocol_cancel_is_killed_before_acceptance(tmp_path, monkeypatch):
    """Replay the observed 601-step failure through the product's kill boundary."""
    cli, python = os.environ.get("PARAMAITRIC_SOLIDCRAFT_CLI"), os.environ.get("PARAMAITRIC_CAD_PYTHON")
    if not cli or not python:
        pytest.skip("Set pinned SolidCraft and reader paths for real cancellation")
    from cad_backends.solidcraft.adapter import NativeSession
    from cad_backends.solidcraft.recipes import command
    r = SolidCraftRuntime(SolidCraftBackend(Path(cli), Path(python), tmp_path))
    first = r.build(payload())
    sent, cancellation, observed = threading.Event(), RequestCancellation(), {}
    original_call, original_send = NativeSession.call, NativeSession.send
    def call(self, name, args):
        if name == "open":
            observed["directory"] = Path(args["path"]).parent
        if name == "set_parameter":
            observed["process"] = self.process
            steps = [command("parameters.change", name="width", expression=f"{100 if i % 2 else 80} mm") for i in range(600)]
            steps.append(command("file.save_as", path=str(observed["directory"] / "after-cancel.solidcraft")))
            return original_call(self, "batch", {"commands": steps, "verbose": False})
        return original_call(self, name, args)
    def send(self, message):
        original_send(self, message)
        if message.get("method") == "tools/call" and message["params"].get("name") == "batch":
            sent.set()
    monkeypatch.setattr(NativeSession, "call", call)
    monkeypatch.setattr(NativeSession, "send", send)
    def work():
        context = REQUEST_CANCEL.set(cancellation)
        try:
            return r.build({"workflow": "plate_with_hole", "revision_id": first["revision_id"], "parameters": {"width_cm": 100, "units": "mm"}})
        finally:
            REQUEST_CANCEL.reset(context)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(work)
        assert sent.wait(5)
        time.sleep(0.02)
        cancelled_at = time.time_ns()
        cancellation.set()
        with pytest.raises(WorkflowFailure) as exc:
            future.result(timeout=5)
    assert exc.value.classification == "cancelled"
    assert observed["process"].poll() is not None
    sentinel = observed["directory"] / "after-cancel.solidcraft"
    assert not sentinel.exists() or sentinel.stat().st_mtime_ns <= cancelled_at
    assert not (observed["directory"] / "verification.json").exists()
    assert r._record(first["revision_id"])["artifact_sha256"] == first["artifact_sha256"]
    assert not r._transaction.locked()


@pytest.mark.parametrize("state", [
    {"timeline": [{}], "params": [{"error": "missing dimension"}], "sketches": []},
    {"timeline": [{}], "params": [{"name": "width", "unit": "mm", "value": 80}], "sketches": [{"failing": ["k1"]}]},
    {"timeline": [{}], "params": [{"name": "width", "unit": "mm", "value": 79}], "sketches": []},
])
def test_native_parameter_and_sketch_health_block_before_exports(state):
    from cad_backends.solidcraft.adapter import NativeSession
    client = object.__new__(NativeSession)
    client.call = lambda *args: state
    with pytest.raises(WorkflowFailure) as exc:
        client.healthy({"width": 80})
    assert exc.value.stage == "feature_health"


def test_health_failure_always_cleans_temporary_directory(tmp_path, monkeypatch):
    import cad_backends.solidcraft.adapter as adapter
    cli = tmp_path / "cli"
    cli.write_text("synthetic native binary")
    monkeypatch.setattr(adapter, "CLI_SHA256", digest(cli))
    b = SolidCraftBackend(cli, Path(sys.executable), tmp_path)
    @contextmanager
    def failed(*args):
        fail("dependency failure")
        yield
    monkeypatch.setattr(SolidCraftBackend, "_session", failed)
    with pytest.raises(WorkflowFailure):
        b.probe()
    assert list(tmp_path.iterdir()) == [cli]


def test_independent_reader_cannot_self_report_success_with_bad_geometry(tmp_path, monkeypatch):
    b = unpinned_backend(tmp_path)
    monkeypatch.setattr(b, "_reader", lambda *args: {"ok": True, "measurements": {"body_count": 2}, "mesh": {"triangle_count": 12}})
    with pytest.raises(WorkflowFailure) as exc:
        b._readback(tmp_path, "plate", PLATE, time.monotonic() + 1)
    assert exc.value.classification == "verification_failed"
