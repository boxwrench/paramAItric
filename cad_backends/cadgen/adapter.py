"""Fixed-recipe worker adapter. No model-provided code, shell, daemon or viewer.

Process/resource isolation is not an OS security sandbox. This interface accepts
only validated numeric plate parameters and executes repository-owned source.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

from cad_backends.protocol import Capabilities, Editability, Measurements, Part
from mcp_server.errors import WorkflowFailure
from mcp_server.operations import Operation, OperationMode

class CadgenPlateBackend:
    capabilities = Capabilities(
        "cadgen-build123d", "real_geometry_worker", frozenset({"new_body", "cut"}),
        frozenset({"body_count", "width_mm", "height_mm", "thickness_mm", "volume_mm3", "valid",
                   "hole_diameter_mm", "hole_center_x_mm", "hole_center_y_mm", "through_hole"}),
        frozenset({"step", "stl"}), Editability.RECIPE,
    )

    def __init__(self, python: Path, output_root: Path, *, timeout: float = 60):
        # Preserve the venv executable path: resolving its symlink would bypass
        # the environment containing the pinned CAD runtime.
        self.python = Path(python).absolute()
        self.output_root = Path(output_root).resolve()
        if not self.python.is_file():
            raise ValueError("CAD worker Python executable does not exist")
        if not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise ValueError("worker timeout must be between 0 and 300 seconds")
        if os.name != "posix":
            raise WorkflowFailure("This worker is currently qualified for POSIX only.", stage="worker_setup", classification="unsupported_capability")
        self.timeout = timeout
        self.cancel_event = None

    def _check_cancelled(self, action: str) -> None:
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise WorkflowFailure("CAD worker request was cancelled.", stage=action, classification="cancelled",
                                  next_step="Inspect the retained revision before starting a new request.")

    def _owned(self, part: Part) -> Path:
        directory = part.directory.resolve()
        if not directory.is_relative_to(self.output_root) or directory == self.output_root:
            raise ValueError("worker directory must be inside the configured output root")
        if directory != part.directory or part.directory.is_symlink():
            raise ValueError("worker directory must not be a symlink")
        return directory

    def start_part(self, directory: Path, parameters: dict) -> Part:
        from mcp_server.utility_plate import CenteredPlate
        spec = CenteredPlate(**{k: parameters[k] for k in CenteredPlate.__dataclass_fields__})
        if parameters != spec.parameters():
            raise ValueError("unsupported recipe, units, datum or parameters")
        part = Part(directory)
        self._owned(part)
        source = Path(__file__).with_name("recipe.py")
        shutil.copyfile(source, directory / "recipe.py")
        (directory / "parameters.json").write_text(json.dumps(parameters, indent=2) + "\n")
        return part

    def _run(self, part: Part, action: str, request: dict) -> dict:
        self._check_cancelled(action)
        directory = self._owned(part)
        # Input and output filenames are fixed; no input path or Python source
        # can be supplied by a model. The copied recipe is an editable artifact,
        # but replay always executes the reviewed installed recipe, never that copy.
        (directory / "request.json").write_text(json.dumps(request, allow_nan=False))
        env = {"PATH": os.defpath, "LANG": "C.UTF-8", "TMPDIR": str(directory),
               "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
               "DO_NOT_TRACK": "1"}
        response = directory / "response.json"
        response.unlink(missing_ok=True)
        with (directory / "worker.log").open("wb") as log:
            process = subprocess.Popen(
                [str(self.python), "-I", str(Path(__file__).with_name("recipe.py")), action],
                cwd=directory, env=env, stdout=log, stderr=log, start_new_session=True,
            )
            deadline = time.monotonic() + self.timeout
            try:
                while True:
                    self._check_cancelled(action)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise WorkflowFailure("CAD worker exceeded its wall-time limit.", stage=action,
                                              classification="timeout", partial_result={"directory": str(directory)},
                                              next_step="Inspect the retained worker log before retrying.")
                    try:
                        code = process.wait(timeout=min(0.05, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        continue
                self._check_cancelled(action)
            except BaseException:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait()
                raise
        if not response.is_file():
            raise WorkflowFailure(f"CAD worker failed (exit {code}).", stage=action, classification="backend_error",
                                  partial_result={"directory": str(directory), "log": str(directory / "worker.log")},
                                  next_step="Inspect the worker log and pinned runtime.")
        result = json.loads(response.read_text())
        if code != 0 or not result.get("ok"):
            raise WorkflowFailure(result.get("error", "CAD worker failed"), stage=action,
                                  classification=result.get("classification", "backend_error"),
                                  partial_result={"directory": str(directory)}, next_step="Inspect the retained worker log.")
        return result

    def apply(self, part: Part, operation: Operation) -> None:
        self.capabilities.require(operations=(operation.mode.value,))
        expected_mode = OperationMode.NEW_BODY if part.revision == 0 else OperationMode.CUT
        if part.revision >= 2 or operation.mode is not expected_mode:
            raise WorkflowFailure("Only new_body then cut is supported.", stage="operation", classification="unsupported_capability")
        response = self._run(part, "apply", {"revision": part.revision, "operation": asdict(operation)})
        part.revision += 1
        part.state["versions"] = response["versions"]

    def inspect(self, part: Part) -> Measurements:
        response = self._run(part, "inspect", {"revision": part.revision})
        return Measurements(response["facts"], "saved_STEP_cold_OCCT_readback", "native BRep; mm; 0.01 mm dimensional tolerance")

    def inspect_export(self, part: Part) -> Measurements:
        response = self._run(part, "inspect", {"revision": 2, "artifact": "final"})
        return Measurements(response["facts"], "exported_STEP_cold_OCCT_readback", "native BRep; mm; 0.01 mm dimensional tolerance")

    def probe(self) -> dict:
        self.output_root.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="health-", dir=self.output_root))
        # A separate adapter avoids cancelling a concurrent build during health.
        probe = type(self)(self.python, self.output_root, timeout=self.timeout)
        result = probe._run(Part(directory), "health", {})
        shutil.rmtree(directory)
        return result

    def export(self, part: Part, formats: tuple[str, ...]) -> dict[str, Path]:
        self.capabilities.require(exports=formats)
        self._run(part, "export", {"revision": part.revision, "formats": list(formats)})
        artifacts = {fmt: part.directory / f"plate.{fmt}" for fmt in formats}
        for path in artifacts.values():
            if not path.is_file() or path.stat().st_size == 0:
                raise WorkflowFailure("Missing output artifact.", stage="export", classification="verification_failed")
        artifacts.update({"recipe": part.directory / "recipe.py", "parameters": part.directory / "parameters.json",
                          "runtime": part.directory / "runtime.json"})
        if "stl" in formats:
            artifacts["mesh_verification"] = part.directory / "mesh-verification.json"
        part.artifacts.update(artifacts)
        return artifacts
