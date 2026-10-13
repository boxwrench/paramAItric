"""Explicit, narrow Utility configuration behind the existing guided MCP facade."""
from __future__ import annotations

from contextvars import ContextVar
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import tempfile

from cad_backends.cadgen import CadgenPlateBackend
from cad_backends.protocol import Part
from mcp_server.errors import WorkflowFailure
from mcp_server.schema_generation import tool_input_schema
from mcp_server.schemas import CreatePlateWithHoleInput
from mcp_server.unit_normalization import normalize_workflow_units
from mcp_server.utility_plate import CenteredPlate, build_plate, regenerate_plate, verify_plate

class RequestCancellation(threading.Event):
    """Linearize cancellation and acceptance; cancellation after commit is too late."""

    def __init__(self):
        super().__init__()
        self._commit_lock = threading.Lock()
        self.committed = False

    def set(self):
        with self._commit_lock:
            if not self.committed:
                super().set()

    def commit(self, publish):
        with self._commit_lock:
            if self.is_set():
                raise WorkflowFailure("Utility request was cancelled.", stage="commit", classification="cancelled")
            publish()
            self.committed = True


REQUEST_CANCEL: ContextVar[RequestCancellation | None] = ContextVar("utility_request_cancel", default=None)
_DIMENSIONS = ("width_cm", "height_cm", "thickness_cm", "hole_diameter_cm")
_REVISION = re.compile(r"^plate-[a-z0-9_-]+$")


def unsupported(message: str):
    raise WorkflowFailure(message, stage="capabilities", classification="unsupported_capability",
                          next_step="Use the centered plate workflow or explicitly configure Fusion for other workflows.")


def _numeric(parameters: dict, keys) -> None:
    for key in keys:
        value = parameters.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")


class UtilityPlateRuntime:
    def __init__(self, backend: CadgenPlateBackend):
        self.backend = backend
        self.root = backend.output_root
        self._transaction = threading.Lock()
        self._active_cancel = None

    def _workflow(self, name: object) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("workflow must be a non-empty string")
        if name.strip() not in ("plate_with_hole", "create_plate_with_hole"):
            unsupported("The selected open backend currently supports only a centered plate with one hole.")

    def requirements(self, payload: dict) -> dict:
        self._workflow(payload.get("workflow"))
        schema = copy.deepcopy(tool_input_schema("create_plate_with_hole", "create_plate_with_hole")["properties"]["payload"])
        schema["description"] = "Centered through-hole plate. Supply measured dimensions; hole centers must equal half the width and height."
        schema["required"].remove("output_path")
        schema["properties"]["output_path"]["description"] = "Optional STL destination hint inside the configured output root, or a bare filename. Omit to use the configured folder automatically. A new revision folder holds verified STEP/STL and source; use returned artifact paths."
        schema["x-edit-parameters"] = self._edit_parameters()
        return schema

    def _edit_parameters(self) -> dict:
        return {"type": "object", "minProperties": 1, "additionalProperties": False,
                "anyOf": [{"required": [key]} for key in _DIMENSIONS],
                "properties": {**{key: {"type": "number", "exclusiveMinimum": 0,
                                        "description": "New dimension in selected units; the centered hole follows width/height changes."} for key in _DIMENSIONS},
                               "units": {"type": "string", "enum": ["cm", "mm", "in"], "default": "cm"}}}

    def tool_schema(self, tool: str, default: dict) -> dict:
        schema = copy.deepcopy(default)
        workflow = {"type": "string", "enum": ["plate_with_hole", "create_plate_with_hole"]}
        revision = {"type": "string", "pattern": _REVISION.pattern,
                    "description": "Revision ID returned by cad_build; never a filesystem path."}
        if tool == "cad_build":
            initial = {"type": "object", "properties": {"workflow": workflow,
                       "parameters": self.requirements({"workflow": "plate_with_hole"})},
                       "required": ["workflow", "parameters"], "additionalProperties": False}
            edit = {"type": "object", "properties": {"workflow": workflow, "revision_id": revision,
                    "parameters": self._edit_parameters()}, "required": ["workflow", "parameters", "revision_id"], "additionalProperties": False}
            schema["properties"]["payload"] = {"oneOf": [initial, edit]}
        elif tool == "cad_inspect":
            schema["properties"]["payload"] = {"type": "object", "properties": {
                "operation": {"const": "get_revision"}, "parameters": {"type": "object",
                "properties": {"revision_id": revision}, "required": ["revision_id"], "additionalProperties": False}},
                "required": ["operation", "parameters"], "additionalProperties": False}
        return schema

    def health(self) -> dict:
        from mcp_server.runtime_info import PARAMAITRIC_VERSION
        result = self.backend.probe()
        caps = self.backend.capabilities
        return {"ok": True, "status": "ready", "mode": "live", "backend": caps.name, "version": PARAMAITRIC_VERSION,
                "backend_versions": result["versions"], "workflow_count": 1,
                "capabilities": {"workflows": ["plate_with_hole"], "exports": sorted(caps.exports),
                                 "measurements": sorted(caps.measurements), "editability": caps.editability.value},
                "tool_profile": "guided", "output_root": str(self.root)}

    def recommend(self, payload: dict) -> dict:
        from mcp_server.discovery import CARDS, recommend
        intent, constraints = payload.get("intent"), payload.get("constraints")
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("intent must be a non-empty string")
        if constraints is not None and not isinstance(constraints, dict):
            raise ValueError("constraints must be a dict when provided")
        cards = tuple(c for c in CARDS if c.name == "plate_with_hole")
        result = recommend(intent, constraints, limit=payload.get("limit", 3), cards=cards)
        for candidate in result["candidates"]:
            candidate["summary"] = "A flat rectangular plate with one centered through-hole."
            candidate["not_for"] = ["off-center holes", "multiple holes", "round parts"]
        result["status"] = "matched" if result["candidates"] else "no_confident_match"
        result["supported_workflows"] = ["plate_with_hole"]
        result["scope_note"] = "Only centered plates with one through-hole are currently qualified on this backend."
        result["match_trace"]["returned"] = len(result["candidates"])
        result["families"] = ["flat_parts"]
        return result

    def _record(self, revision_id: object) -> dict:
        if not isinstance(revision_id, str) or not _REVISION.fullmatch(revision_id):
            raise ValueError("revision_id must be a returned plate revision ID")
        directory = self.root / revision_id
        if directory.is_symlink() or directory.resolve().parent != self.root:
            raise ValueError("revision directory must belong to the configured output root")
        try:
            record = json.loads((directory / "verification.json").read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("No accepted plate revision was found for this ID") from exc
        if not isinstance(record, dict) or record.get("ok") is not True or record.get("acceptance") != "accepted" or record.get("revision_id") != revision_id or record.get("backend") != self.backend.capabilities.name or record.get("directory") != str(directory):
            raise ValueError("revision is not an accepted part from this backend")
        recipe = record.get("recipe", {})
        try:
            spec = CenteredPlate(**{key: recipe[key] for key in CenteredPlate.__dataclass_fields__})
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("revision recipe parameters are missing or invalid") from exc
        if recipe != spec.parameters():
            raise ValueError("revision recipe metadata is unsupported")
        if not isinstance(record.get("artifacts"), dict):
            raise ValueError("revision artifact record is missing")
        artifacts = record["artifacts"]
        hashes = record.get("artifact_sha256")
        required = {"step", "stl", "recipe", "parameters", "runtime", "mesh_verification"}
        if set(artifacts) != required or not isinstance(hashes, dict) or set(hashes) != required:
            raise ValueError("revision artifact hashes are missing or incomplete")
        modified = []
        for key, path in artifacts.items():
            if not isinstance(path, str) or Path(path).is_symlink() or Path(path).resolve().parent != directory:
                raise ValueError("revision artifacts must belong to their original directory")
            try:
                actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            except OSError:
                actual = None
            if actual != hashes[key]:
                modified.append(key)
        if modified:
            raise WorkflowFailure("Saved revision artifacts were modified or are missing.", stage="revision_integrity",
                                  classification="verification_failed", partial_result={"revision_id": revision_id, "modified_artifacts": modified},
                                  next_step="This revision is no longer approved. Regenerate from measured parameters and revalidate as a new revision.")
        if record.get("recipe_sha256") != hashes["parameters"] or json.loads(Path(artifacts["parameters"]).read_text()) != recipe:
            raise ValueError("revision recipe does not match its saved parameters")
        return record

    def _enter(self):
        if not self._transaction.acquire(blocking=False):
            raise WorkflowFailure("A Utility transaction is already running.", stage="transaction", classification="state_drift",
                                  next_step="Wait for the active build or inspection to finish.")
        self._active_cancel = REQUEST_CANCEL.get() or RequestCancellation()
        self.backend.cancel_event = self._active_cancel

    def _leave(self):
        self.backend.cancel_event = None
        self._active_cancel = None
        self._transaction.release()

    def cancel_active(self):
        if self._active_cancel is not None:
            self._active_cancel.set()

    def _accept(self, report: dict) -> None:
        """Publish one complete acceptance record, synchronized with cancellation."""
        directory = Path(report["directory"])
        report["acceptance"] = "accepted"
        descriptor, path = tempfile.mkstemp(prefix=".acceptance-", suffix=".json", dir=directory)
        candidate = Path(path)
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(json.dumps(report, indent=2) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            self._active_cancel.commit(lambda: os.replace(candidate, directory / "verification.json"))
        finally:
            candidate.unlink(missing_ok=True)

    def build(self, payload: dict) -> dict:
        self._workflow(payload.get("workflow"))
        if set(payload) - {"workflow", "parameters", "revision_id"}:
            raise ValueError("unknown build fields")
        parameters = payload.get("parameters")
        if not isinstance(parameters, dict):
            raise ValueError("parameters must be a dictionary")
        p = normalize_workflow_units(parameters)
        if "revision_id" in payload:
            if not p or set(p) - set(_DIMENSIONS):
                raise ValueError("revision changes must contain only supported plate dimensions")
            _numeric(p, p)
            previous = self._record(payload["revision_id"])
            changes = {key.replace("_cm", "_mm"): value * 10 for key, value in p.items()}
            # Validate before taking the transaction or creating artifacts.
            values = {key: previous["recipe"][key] for key in CenteredPlate.__dataclass_fields__}
            CenteredPlate(**{**values, **changes})
        else:
            allowed = set(self.requirements({"workflow": "plate_with_hole"})["properties"]) - {"units"}
            if set(p) - allowed:
                raise ValueError("unknown plate parameters")
            _numeric(p, (*_DIMENSIONS, "hole_center_x_cm", "hole_center_y_cm"))
            requested = p.get("output_path", str(self.root / "plate.stl"))
            if not isinstance(requested, str) or not requested.strip():
                raise ValueError("output_path must be a non-empty STL path inside the configured output root")
            path = Path(requested)
            if path.parent == Path("."):
                path = self.root / path
            if path.suffix.lower() != ".stl":
                raise ValueError("output_path must use the STL format")
            p["output_path"] = str(path)
            # Existing schema/path rules first, plus this backend's narrower center relationship.
            legacy = CreatePlateWithHoleInput.from_payload(p)
            destination = Path(legacy.output_path).resolve()
            if not destination.is_relative_to(self.root):
                raise ValueError("output_path must be inside the configured CAD output root")
            spec = CenteredPlate(*(p[key] * 10 for key in _DIMENSIONS))
            if abs(p["hole_center_x_cm"] - spec.width_mm / 20) > 1e-9 or abs(p["hole_center_y_cm"] - spec.height_mm / 20) > 1e-9:
                unsupported("Off-center holes are not supported by the selected open backend.")
        self._enter()
        try:
            if "revision_id" in payload:
                report = regenerate_plate(self.backend, previous, changes, self.root)
            else:
                report = build_plate(self.backend, spec, self.root)
            facts = report["measurements"]
            report.update({"revision_id": Path(report["directory"]).name, "workflow": "create_plate_with_hole",
                           "export": {"output_path": report["artifacts"]["stl"], "format": "stl"},
                           "verification": {"body_count": facts["body_count"], "actual_width_cm": facts["width_mm"] / 10,
                                            "actual_height_cm": facts["height_mm"] / 10, "actual_thickness_cm": facts["thickness_mm"] / 10,
                                            "hole_diameter_cm": facts["hole_diameter_mm"] / 10},
                           "review": {"model_path": report["artifacts"]["step"],
                                      "previous_model_path": previous["artifacts"]["step"] if "revision_id" in payload else None},
                           "user_next_step": "Review the measured model. To revise it, call cad_build with its revision_id and changed dimensions."})
            self._accept(report)
            return report
        finally:
            self._leave()

    def inspect(self, payload: dict) -> dict:
        if set(payload) - {"operation", "parameters"}:
            raise ValueError("unknown inspection fields")
        if payload.get("operation") != "get_revision":
            unsupported("Use get_revision to inspect the saved open-backend part.")
        p = payload.get("parameters")
        if not isinstance(p, dict) or set(p) != {"revision_id"}:
            raise ValueError("get_revision requires only revision_id")
        record = self._record(p["revision_id"])
        spec = CenteredPlate(**{key: record["recipe"][key] for key in CenteredPlate.__dataclass_fields__})
        self._enter()
        try:
            observed = self.backend.inspect_export(Part(Path(record["directory"]), revision=2))
            signals = verify_plate(spec, observed, hole=True, full=True)
            return {"ok": True, "revision_id": p["revision_id"], "measurements": observed.facts,
                    "verification_signals": signals, "artifacts": record["artifacts"], "editability": record["editability"]}
        finally:
            self._leave()


def runtime_from_environment() -> UtilityPlateRuntime | None:
    name = os.environ.get("PARAMAITRIC_CAD_BACKEND", "fusion")
    if name == "fusion":
        return None
    if name != "cadgen":
        raise ValueError("PARAMAITRIC_CAD_BACKEND must be fusion or cadgen")
    python, root = os.environ.get("PARAMAITRIC_CAD_PYTHON"), os.environ.get("PARAMAITRIC_CAD_OUTPUT_ROOT")
    if not python or not root:
        raise ValueError("cadgen requires PARAMAITRIC_CAD_PYTHON and PARAMAITRIC_CAD_OUTPUT_ROOT")
    if not Path(python).is_absolute() or not Path(root).is_absolute():
        raise ValueError("CAD worker and output root must be absolute paths")
    output = Path(root).resolve()
    CenteredPlate().legacy_payload(output / "plate.stl")
    return UtilityPlateRuntime(CadgenPlateBackend(Path(python), output))
