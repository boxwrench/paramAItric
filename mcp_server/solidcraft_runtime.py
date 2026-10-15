"""Two opt-in Utility families on SolidCraft; reuse guided transaction acceptance."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import tempfile

from cad_backends.solidcraft.adapter import FILES, SolidCraftBackend, digest, fail
from mcp_server.errors import WorkflowFailure
from mcp_server.schema_generation import tool_input_schema
from mcp_server.schemas import CreateBracketInput, CreatePlateWithHoleInput
from mcp_server.unit_normalization import normalize_workflow_units
from mcp_server.utility_plate import CenteredPlate
from mcp_server.utility_runtime import UtilityPlateRuntime, _numeric, unsupported

REVISION = re.compile(r"^solidcraft-[a-z0-9_-]+$")
WORKFLOWS = {"plate_with_hole": "plate", "create_plate_with_hole": "plate", "bracket": "bracket", "create_bracket": "bracket"}
DIMENSIONS = {"plate": {"width_cm": "width", "height_cm": "height", "thickness_cm": "thickness", "hole_diameter_cm": "hole_diameter"},
              "bracket": {"width_cm": "width", "height_cm": "height", "thickness_cm": "thickness", "leg_thickness_cm": "leg"}}


def validate(kind, p):
    if set(p) != set(DIMENSIONS[kind].values()):
        raise ValueError("Unsupported SolidCraft recipe parameters")
    _numeric(p, p)
    if any(not 0 < value <= 10000 for value in p.values()):
        raise ValueError("Dimensions must be positive and at most 10000 mm")
    if kind == "plate":
        CenteredPlate(p["width"], p["height"], p["thickness"], p["hole_diameter"])
    elif p["leg"] >= min(p["width"], p["height"]):
        raise ValueError("Leg thickness must be smaller than both overall dimensions")
    return p


class SolidCraftRuntime(UtilityPlateRuntime):
    """Shares cancellation/transaction locks and atomic publisher with frozen OCCT."""
    def __init__(self, backend: SolidCraftBackend):
        super().__init__(backend)

    def _workflow(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("workflow must be a non-empty string")
        if name.strip() not in WORKFLOWS:
            unsupported("SolidCraft currently supports only centered plates and flat XY L-profiles; no fillets or mounting holes.")
        return WORKFLOWS[name.strip()]

    def _edit_schema(self, kind):
        return {"type": "object", "minProperties": 1, "additionalProperties": False,
                "anyOf": [{"required": [key]} for key in DIMENSIONS[kind]],
                "properties": {**{key: {"type": "number", "exclusiveMinimum": 0} for key in DIMENSIONS[kind]},
                               "units": {"enum": ["cm", "mm", "in"], "default": "cm"}}}

    def requirements(self, payload):
        kind = self._workflow(payload.get("workflow"))
        tool = "create_plate_with_hole" if kind == "plate" else "create_bracket"
        schema = copy.deepcopy(tool_input_schema(tool, tool)["properties"]["payload"])
        allowed = set(DIMENSIONS[kind]) | {"plane", "units", "output_path"}
        if kind == "plate":
            allowed |= {"hole_center_x_cm", "hole_center_y_cm"}
        schema["properties"] = {k: v for k, v in schema["properties"].items() if k in allowed}
        schema["required"] = [k for k in schema["required"] if k != "output_path"]
        schema["additionalProperties"] = False
        schema["properties"]["plane"] = {"const": "xy", "default": "xy"}
        schema["properties"]["output_path"]["description"] = "Optional STL destination hint inside configured root. Omit for automatic revision folder; use returned artifact paths."
        schema["description"] = ("Centered through-hole plate; hole centers must equal width/2 and height/2." if kind == "plate" else
                                 "Flat XY L-profile extruded in +Z. Leg thickness controls both legs. No holes, fillets or folded angle.")
        schema["x-edit-parameters"] = self._edit_schema(kind)
        return schema

    def tool_schema(self, tool, default):
        schema = copy.deepcopy(default)
        revision = {"type": "string", "pattern": REVISION.pattern}
        if tool == "cad_build":
            variants = []
            for workflow, kind in (("plate_with_hole", "plate"), ("bracket", "bracket")):
                for edit in (False, True):
                    properties = {"workflow": {"enum": [workflow, "create_" + workflow]},
                                  "parameters": self._edit_schema(kind) if edit else self.requirements({"workflow": workflow})}
                    if edit:
                        properties["revision_id"] = revision
                    variants.append({"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False})
            schema["properties"]["payload"] = {"oneOf": variants}
        elif tool == "cad_inspect":
            schema["properties"]["payload"] = {"type": "object", "properties": {"operation": {"const": "get_revision"},
                "parameters": {"type": "object", "properties": {"revision_id": revision}, "required": ["revision_id"], "additionalProperties": False}},
                "required": ["operation", "parameters"], "additionalProperties": False}
        return schema

    def health(self):
        result = super().health()
        result["workflow_count"] = 2
        result["capabilities"]["workflows"] = ["plate_with_hole", "bracket"]
        result["qualification"] = "experimental_opt_in; interactive_UI_and_target_hardware_not_run"
        return result

    def recommend(self, payload):
        from dataclasses import replace
        from mcp_server.discovery import CARDS, recommend
        intent, constraints = payload.get("intent"), payload.get("constraints")
        if not isinstance(intent, str) or not intent.strip() or (constraints is not None and not isinstance(constraints, dict)):
            raise ValueError("intent must be non-empty text; constraints must be an object")
        cards = tuple(replace(c, summary="Flat XY L-profile with equal-width legs, extruded in +Z; no holes or fillets.",
                              not_for=("folded angle brackets", "mounting holes", "fillets")) if c.name == "bracket" else
                      replace(c, summary="Flat plate with one centered through-hole.", not_for=("off-center holes", "multiple holes"))
                      for c in CARDS if c.name in ("bracket", "plate_with_hole"))
        result = recommend(intent, constraints, limit=payload.get("limit", 3), cards=cards)
        result.update({"status": "matched" if result["candidates"] else "no_confident_match",
                       "supported_workflows": ["plate_with_hole", "bracket"],
                       "scope_note": "Experimental native SolidCraft: centered plate or flat XY L-profile only.", "families": ["flat_parts", "brackets"]})
        return result

    def _record(self, revision_id):
        if not isinstance(revision_id, str) or not REVISION.fullmatch(revision_id):
            raise ValueError("revision_id must be a returned SolidCraft revision ID")
        directory = self.root / revision_id
        if directory.is_symlink() or directory.resolve().parent != self.root:
            raise ValueError("revision directory must belong to configured root")
        try:
            record = json.loads((directory / "verification.json").read_text())
        except (OSError, ValueError) as exc:
            raise ValueError("No accepted SolidCraft revision exists for this ID") from exc
        if not isinstance(record, dict) or record.get("ok") is not True or record.get("acceptance") != "accepted" or record.get("backend") != "solidcraft" or record.get("revision_id") != revision_id or record.get("directory") != str(directory):
            raise ValueError("Revision identity/acceptance is invalid")
        if record.get("kind") not in DIMENSIONS or not isinstance(record.get("parameters"), dict):
            raise ValueError("Revision recipe is invalid")
        validate(record["kind"], record["parameters"])
        artifacts, hashes = record.get("artifacts"), record.get("artifact_sha256")
        if not isinstance(artifacts, dict) or set(artifacts) != set(FILES) or not isinstance(hashes, dict) or set(hashes) != set(FILES):
            raise ValueError("Revision evidence is incomplete")
        changed = []
        for key, filename in FILES.items():
            path = directory / filename
            if artifacts[key] != str(path) or path.is_symlink():
                raise ValueError("Revision artifacts must be owned fixed files")
            try:
                actual = digest(path)
            except OSError:
                actual = None
            if actual != hashes[key]:
                changed.append(key)
        if changed:
            fail("Accepted artifacts changed or are missing; revalidation required.", stage="revision_integrity", classification="verification_failed", modified_artifacts=changed)
        if json.loads((directory / "parameters.json").read_text()) != record["parameters"]:
            raise ValueError("Saved revision parameters differ from accepted parameters")
        return record

    def _initial(self, kind, p):
        workflow = "plate_with_hole" if kind == "plate" else "bracket"
        allowed = set(self.requirements({"workflow": workflow})["properties"]) - {"units"}
        if set(p) - allowed:
            raise ValueError("Unsupported recipe parameters")
        if p.get("plane", "xy") != "xy":
            unsupported("SolidCraft Utility currently supports only the XY plane.")
        required = set(DIMENSIONS[kind]) - ({"leg_thickness_cm"} if kind == "bracket" else set())
        if kind == "plate":
            required |= {"hole_center_x_cm", "hole_center_y_cm"}
        _numeric(p, required)
        if kind == "bracket":
            p.setdefault("leg_thickness_cm", p["thickness_cm"])
        _numeric(p, DIMENSIONS[kind])
        dimensions = validate(kind, {name: p[key] * 10 for key, name in DIMENSIONS[kind].items()})
        requested = p.get("output_path", "part.stl")
        if not isinstance(requested, str) or not requested.strip():
            raise ValueError("output_path must be an STL path inside the configured root")
        destination = Path(requested)
        if destination.parent == Path("."):
            destination = self.root / destination
        if destination.suffix.lower() != ".stl" or not destination.resolve().is_relative_to(self.root):
            raise ValueError("output_path must be an STL path inside the configured root")
        p["output_path"] = str(destination)
        (CreatePlateWithHoleInput if kind == "plate" else CreateBracketInput).from_payload(p)
        if kind == "plate" and (abs(p["hole_center_x_cm"] * 10 - dimensions["width"] / 2) > 1e-8 or abs(p["hole_center_y_cm"] * 10 - dimensions["height"] / 2) > 1e-8):
            unsupported("Only centered holes are supported by SolidCraft Utility.")
        return dimensions

    def build(self, payload):
        kind = self._workflow(payload.get("workflow"))
        if set(payload) - {"workflow", "parameters", "revision_id"} or not isinstance(payload.get("parameters"), dict):
            raise ValueError("Build requires supported workflow and parameter object")
        p = normalize_workflow_units(payload["parameters"])
        edit = "revision_id" in payload
        if edit:
            if not p or set(p) - set(DIMENSIONS[kind]):
                raise ValueError("Edits require supported dimension changes")
            _numeric(p, p)
            previous = self._record(payload["revision_id"])
            if previous["kind"] != kind:
                raise ValueError("Revision workflow differs from requested workflow")
            dimensions = validate(kind, {**previous["parameters"], **{DIMENSIONS[kind][key]: value * 10 for key, value in p.items()}})
        else:
            dimensions = self._initial(kind, p)
        self._enter()
        try:
            if edit:
                previous = self._record(payload["revision_id"])
            self.root.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix="solidcraft-", dir=self.root))
            try:
                result = self.backend.build(directory, kind, dimensions, previous if edit else None)
                artifacts = {key: str(directory / filename) for key, filename in FILES.items()}
                if any(Path(path).is_symlink() or not Path(path).is_file() or Path(path).stat().st_size == 0 for path in artifacts.values()):
                    fail("SolidCraft output evidence is missing.", stage="artifacts", classification="verification_failed")
                report = {"ok": True, "acceptance": "geometry_verified", "backend": "solidcraft", "kind": kind,
                          "workflow": "create_plate_with_hole" if kind == "plate" else "create_bracket",
                          "revision_id": directory.name, "directory": str(directory), "parameters": dimensions,
                          "editability": "native_feature_history", "artifacts": artifacts,
                          "artifact_sha256": {key: digest(path) for key, path in artifacts.items()},
                          "measurements": result["measurements"], "verification_signals": result["checks"],
                          "export": {"format": "stl", "output_path": artifacts["stl"]},
                          "review": {"model_path": artifacts["step"], "native_document": artifacts["native"],
                                     "previous_model_path": previous["artifacts"]["step"] if edit else None},
                          "user_next_step": "Review the verified part. Revise dimensions with cad_build and revision_id; returned paths are authoritative."}
                (directory / "geometry-verification.json").write_text(json.dumps(report, indent=2) + "\n")
                self._accept(report)
                return report
            except WorkflowFailure as exc:
                exc.partial_result["directory"] = str(directory)
                raise
        finally:
            self._leave()

    def inspect(self, payload):
        if set(payload) != {"operation", "parameters"} or payload.get("operation") != "get_revision":
            unsupported("Use get_revision to inspect accepted SolidCraft geometry.")
        p = payload["parameters"]
        if not isinstance(p, dict) or set(p) != {"revision_id"}:
            raise ValueError("get_revision requires only revision_id")
        self._enter()
        try:
            record = self._record(p["revision_id"])
            result = self.backend.inspect(record)
            self._record(p["revision_id"])
            return {"ok": True, "revision_id": p["revision_id"], "measurements": result["measurements"],
                    "verification_signals": result["checks"], "artifacts": record["artifacts"], "editability": record["editability"]}
        finally:
            self._leave()
