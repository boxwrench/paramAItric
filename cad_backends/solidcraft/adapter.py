"""Disposable native documents, bounded processes and cold independent OCCT gates.

Only reviewed command plans execute. Process limits/path grants are not an OS
sandbox. Native cancellation is deliberately replaced by process-group teardown.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from cad_backends.protocol import Capabilities, Editability
from cad_backends.solidcraft.recipes import bracket_stages, plate_stages
from cad_backends.solidcraft.readback import verify
from mcp_server.errors import WorkflowFailure

CLI_SHA256 = "c1b5fd3d07015b13b8c2e5465795bd8e457f889b7051d7f4da66ba5af7b58be6"
SOURCE_COMMIT = "b01b9689c8999a4415b4a6daaa2f8aae8a1a2f25"
FILES = {"native": "part.solidcraft", "step": "part.step", "stl": "part.stl",
         "parameters": "parameters.json", "commands": "commands.json", "runtime": "runtime.json",
         "readback": "readback.json"}
HERE = Path(__file__).parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fail(message, stage="native_execution", classification="backend_error", **partial):
    raise WorkflowFailure(message, stage=stage, classification=classification, partial_result=partial,
                          next_step="The previous accepted revision is preserved. Inspect this failure before retrying.")


def check_result(result):
    """A successful protocol reply may still contain failed native features."""
    if not isinstance(result, dict) or result.get("isError"):
        fail("SolidCraft reported a tool failure.", response=result)
    blocks = result.get("content")
    if not isinstance(blocks, list) or not blocks or not isinstance(blocks[0], dict) or blocks[0].get("type") != "text":
        fail("SolidCraft returned no structured tool payload.")
    try:
        data = json.loads(blocks[0]["text"])
    except (ValueError, KeyError, TypeError):
        fail("SolidCraft returned an invalid JSON tool payload.")
    if not isinstance(data, dict) or data.get("ok") is False or data.get("errors") or data.get("failed") or data.get("error"):
        fail("SolidCraft feature evaluation failed.", response=data)
    timeline = data.get("timeline", [])
    if not isinstance(timeline, list) or any(not isinstance(f, dict) or f.get("error") or f.get("suppressed") or f.get("rolled_back") for f in timeline):
        fail("SolidCraft has failed, suppressed or rolled-back features.", stage="feature_health", response=data)
    return data


class NativeSession:
    """Sequential stdio JSON-RPC; bounded buffering and cancellable reads."""
    def __init__(self, process, guard):
        self.process, self.guard, self.buffer, self.sequence = process, guard, b"", 0

    def send(self, message):
        self.guard()
        try:
            self.process.stdin.write(json.dumps({"jsonrpc": "2.0", **message}, allow_nan=False).encode() + b"\n")
            self.process.stdin.flush()
        except OSError:
            fail("SolidCraft protocol pipe closed before submission.")

    def request(self, method, params):
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            while True:
                self.guard()
                if b"\n" not in self.buffer:
                    if not selector.select(0.005):
                        continue
                    chunk = os.read(self.process.stdout.fileno(), 65536)
                    if not chunk:
                        fail("SolidCraft exited before replying.")
                    self.buffer += chunk
                    if len(self.buffer) > 8 * 1024**2:
                        fail("SolidCraft response exceeded its size limit.")
                    continue
                line, self.buffer = self.buffer.split(b"\n", 1)
                try:
                    message = json.loads(line)
                except ValueError:
                    fail("SolidCraft emitted invalid protocol JSON.")
                if not isinstance(message, dict):
                    fail("SolidCraft emitted a non-object protocol message.")
                if message.get("id") == request_id:
                    if "error" in message or "result" not in message:
                        fail("SolidCraft protocol request failed.", response=message)
                    return message["result"]

    def call(self, name, args):
        return check_result(self.request("tools/call", {"name": name, "arguments": args}))

    def healthy(self, expected=None):
        state = self.call("inspect_design", {"measure": False})
        params, sketches = state.get("params"), state.get("sketches")
        if not isinstance(state.get("timeline"), list) or not state["timeline"] or not isinstance(params, list) or not params:
            fail("Native feature history/parameters are missing.", stage="feature_health")
        if any(not isinstance(p, dict) or p.get("error") for p in params) or not isinstance(sketches, list) or any(
            not isinstance(s, dict) or s.get("failing") for s in sketches):
            fail("Native parameters/sketches failed evaluation.", stage="feature_health")
        if expected:
            by_name = {p.get("name"): p for p in params}
            for name, value in expected.items():
                param = by_name.get(name, {})
                actual = param.get("value")
                if param.get("unit") != "mm" or not isinstance(actual, (int, float)) or isinstance(actual, bool) or not math.isfinite(actual) or abs(actual - value) > 1e-8:
                    fail("Native parameters differ from the requested recipe.", stage="feature_health")
        return state


class SolidCraftBackend:
    capabilities = Capabilities("solidcraft", "opt_in_native_worker_independent_OCCT", frozenset(),
        frozenset({"body_count", "valid", "dimensions", "volume", "bore", "L_profile"}),
        frozenset({"step", "stl"}), Editability.HISTORY)

    def __init__(self, cli: Path, python: Path, output_root: Path, *, timeout=120):
        self.cli, self.python, self.output_root = Path(cli).absolute(), Path(python).absolute(), Path(output_root).resolve()
        if sys.platform != "linux":
            raise ValueError("The pinned SolidCraft worker is qualified on Linux only")
        if not self.cli.is_file() or digest(self.cli) != CLI_SHA256:
            raise ValueError("SolidCraft CLI must match the pinned v0.11.1 Linux release hash")
        if not self.python.is_file():
            raise ValueError("Independent CAD reader Python does not exist")
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise ValueError("SolidCraft transaction timeout must be positive and at most 300 seconds")
        self.timeout, self.cancel_event = timeout, None

    def _guard(self, deadline):
        if self.cancel_event is not None and self.cancel_event.is_set():
            fail("SolidCraft transaction cancelled.", stage="worker", classification="cancelled")
        if time.monotonic() >= deadline:
            fail("SolidCraft transaction exceeded its wall-time limit.", stage="worker", classification="timeout")

    @contextmanager
    def _process(self, command, directory, deadline, label):
        self._guard(deadline)
        env = {"PATH": os.defpath, "LANG": "C.UTF-8", "DO_NOT_TRACK": "1",
               "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        for name, suffix in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache"), ("TMPDIR", "tmp")):
            path = directory / "state" / suffix
            path.mkdir(parents=True, exist_ok=True)
            env[name] = str(path)
        with (directory / f"{label}.log").open("ab") as log:
            process = subprocess.Popen(command, cwd=directory, env=env, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=log, start_new_session=True)
            try:
                yield process
                self._guard(deadline)
            finally:
                # Kill descendants even if a leader exited. No worker survives acceptance.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                process.stdin.close()
                process.stdout.close()

    @contextmanager
    def _session(self, directory, deadline):
        # Check the binary at execution too, not only at application startup.
        if digest(self.cli) != CLI_SHA256:
            fail("Pinned SolidCraft executable changed.", stage="worker_setup", classification="verification_failed")
        command = [sys.executable, "-I", str(HERE / "worker.py"), str(self.cli), "mcp", "--allow-path", str(directory)]
        with self._process(command, directory, deadline, "native") as process:
            client = NativeSession(process, lambda: self._guard(deadline))
            client.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "ParamAItric", "version": "0.1"}})
            client.send({"method": "notifications/initialized"})
            yield client

    def _reader(self, directory, args, deadline):
        command = [str(self.python), "-I", str(HERE / "readback.py"), *args]
        with self._process(command, directory, deadline, "reader") as process:
            output = bytearray()
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    self._guard(deadline)
                    if not selector.select(0.005):
                        continue
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > 1024**2:
                        fail("Independent reader exceeded response limit.", stage="verify_geometry")
            while process.poll() is None:
                self._guard(deadline)
                time.sleep(0.01)
            try:
                result = json.loads(output)
            except ValueError:
                fail("Independent OCCT reader failed.", stage="verify_geometry", classification="verification_failed")
            if process.returncode or not isinstance(result, dict) or result.get("ok") is not True:
                fail("Independent reader failed.", stage="verify_geometry", classification="verification_failed", readback=result)
            return result

    def _readback(self, directory, kind, p, deadline, stem="part"):
        result = self._reader(directory, [str(directory / f"{stem}.step"), kind,
                              json.dumps(p, allow_nan=False), str(directory / f"{stem}.stl")], deadline)
        expected_checks = verify(result.get("measurements", {}), kind, p)
        if not all(c["passed"] for c in expected_checks) or not result.get("mesh"):
            fail("Required independent geometry verification failed.", stage="verify_geometry",
                 classification="verification_failed", readback=result)
        result["checks"] = expected_checks
        return result

    def _verify_session(self, client, directory, kind, p, deadline, stem):
        client.healthy(p)
        for fmt in ("step", "stl"):
            client.call("export", {"path": str(directory / f"{stem}.{fmt}"), "format": fmt})
        result = self._readback(directory, kind, p, deadline, stem)
        (directory / f"{stem}-readback.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        return result

    def build(self, directory, kind, p, previous=None):
        deadline = time.monotonic() + self.timeout
        transcript = []
        with self._session(directory, deadline) as client:
            if previous:
                # Only a copy is granted to the worker; the accepted native is immutable.
                shutil.copyfile(previous["artifacts"]["native"], directory / "source.solidcraft")
                if digest(directory / "source.solidcraft") != previous["artifact_sha256"]["native"]:
                    fail("Native source changed during replay.", stage="revision_integrity", classification="verification_failed")
                client.call("open", {"path": str(directory / "source.solidcraft")})
                client.healthy(previous["parameters"])
                checkpoint = client.call("execute", {"command": "edit.checkpoint"})["checkpoint"]
                transcript.append({"checkpoint": checkpoint, "source_revision": previous["revision_id"]})
                try:
                    old = dict(previous["parameters"])
                    for name, value in p.items():
                        if value == old[name]:
                            continue
                        client.call("set_parameter", {"name": name, "value": f"{value} mm"})
                        old[name] = value
                        self._verify_session(client, directory, kind, old, deadline, "edit-stage")
                        transcript.append({"set_parameter": name, "value_mm": value, "verified": True})
                except WorkflowFailure as exc:
                    # Cancellation/timeout kills the worker immediately. Other errors
                    # attempt native restore; every failure still discards this worker.
                    if exc.classification not in {"cancelled", "timeout"}:
                        try:
                            client.call("execute", {"command": "edit.restore_checkpoint", "params": {"checkpoint": checkpoint}})
                            self._verify_session(client, directory, kind, previous["parameters"], deadline, "restored")
                            exc.partial_result["checkpoint_recovery"] = "independently_verified"
                        except Exception:
                            exc.partial_result["checkpoint_recovery"] = "failed_worker_discarded"
                    raise
            else:
                stages = plate_stages(p) if kind == "plate" else bracket_stages(p)
                for i, stage in enumerate(stages):
                    transcript.append({"batch": stage})
                    client.call("batch", {"commands": stage, "verbose": False, "rollback": True})
                    self._verify_session(client, directory, "plate_base" if kind == "plate" and i == 0 else kind, p, deadline, f"stage-{i}")
            client.call("save", {"path": str(directory / FILES["native"])})
        # Cold native reopen is required even for new parts. Never import STEP as
        # a substitute for authored parameter/history editability.
        with self._session(directory, deadline) as client:
            client.call("open", {"path": str(directory / FILES["native"])})
            state = client.healthy(p)
            result = self._verify_session(client, directory, kind, p, deadline, "part")
        for path, value in (("parameters.json", p), ("commands.json", transcript), ("readback.json", result),
                            ("runtime.json", {"solidcraft": "0.11.1", "cli_sha256": CLI_SHA256,
                             "upstream_commit": SOURCE_COMMIT, "reader": result["versions"],
                             "source_sha256": {name: digest(HERE / name) for name in ("adapter.py", "recipes.py", "readback.py", "worker.py")},
                             "native_history": state, "units": "mm", "datum": "lower_left_xy_positive_z"})):
            (directory / path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
        self._guard(deadline)
        return result

    def inspect(self, record):
        # Read-only inspection runs on copies so accepted evidence cannot be rewritten.
        with tempfile.TemporaryDirectory(prefix="inspect-", dir=self.output_root) as name:
            directory = Path(name)
            for fmt in ("step", "stl"):
                shutil.copyfile(record["artifacts"][fmt], directory / f"part.{fmt}")
            return self._readback(directory, record["kind"], record["parameters"], time.monotonic() + self.timeout)

    def probe(self):
        self.output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="health-", dir=self.output_root) as name:
            # A separate backend does not inherit another request's cancellation.
            probe = type(self)(self.cli, self.python, self.output_root, timeout=self.timeout)
            with probe._session(Path(name), time.monotonic() + self.timeout) as client:
                client.call("inspect_design", {"measure": False})
            result = probe._reader(Path(name), ["--health"], time.monotonic() + self.timeout)
            return {"versions": {"solidcraft": "0.11.1", "cli_sha256": CLI_SHA256, "reader": result["versions"]}}
