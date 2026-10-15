"""Synthetic contract/policy guards; real geometry is exercised in the proof runner."""
import copy
import json
import os
from pathlib import Path
import sys
import time

import jsonschema
import pytest

from cad_backends.solidcraft.adapter import FILES, SolidCraftBackend, digest
from cad_backends.solidcraft.external_edits import EXTERNAL_FILES, compare, constrained, read_owned
from mcp_server.errors import WorkflowFailure
from mcp_server.solidcraft_runtime import SolidCraftRuntime
from mcp_server.utility_runtime import REQUEST_CANCEL, RequestCancellation


class SyntheticBackend:
    capabilities = SolidCraftBackend.capabilities
    _guard = SolidCraftBackend._guard
    timeout = 5
    cancel_event = None

    def __init__(self, root):
        self.output_root, self.calls = root, []

    def build(self, directory, kind, p, previous=None):
        self.calls.append("build")
        for key, name in FILES.items():
            (directory / name).write_text(json.dumps(p) if key == "parameters" else "synthetic evidence")
        return {"measurements": {"body_count": 1}, "checks": [{"passed": True}]}

    def revalidate(self, directory, kind, p, previous):
        self.calls.append("revalidate")
        result = self.build(directory, kind, p, previous)
        for key in ("native_definition", "reference_definition"):
            (directory / EXTERNAL_FILES[key]).write_text("{}")
        result["native_definition_policy"] = {"passed": True, "synthetic": True}
        return result


def create(root, kind="plate"):
    r = SolidCraftRuntime(SyntheticBackend(root))
    workflow = "plate_with_hole" if kind == "plate" else "bracket"
    p = {"width_cm": 80 if kind == "plate" else 50, "height_cm": 60 if kind == "plate" else 80, "thickness_cm": 5, "units": "mm"}
    p.update({"hole_diameter_cm": 10, "hole_center_x_cm": 40, "hole_center_y_cm": 30} if kind == "plate" else {"leg_thickness_cm": 5})
    parent = r.build({"workflow": workflow, "parameters": p})
    prepare = {"workflow": workflow, "revision_id": parent["revision_id"], "external_edit": {"action": "prepare"}}
    return r, parent, prepare


def submit(prepare, edit_id):
    return {**prepare, "external_edit": {"action": "revalidate", "edit_id": edit_id}, "parameters": {"width_cm": 100, "units": "mm"}}


def unchanged(parent):
    assert all(digest(path) == parent["artifact_sha256"][key] for key, path in parent["artifacts"].items())


@pytest.mark.parametrize("kind", ["plate", "bracket"])
def test_prepare_and_explicit_revalidation_create_new_immutable_revision(tmp_path, kind):
    r, parent, prepare = create(tmp_path, kind)
    schema = r.tool_schema("cad_build", {"properties": {}})
    jsonschema.validate({"payload": prepare}, schema)
    editable = r.build(prepare)
    assert editable["acceptance"] == "not_accepted_edit_copy"
    assert digest(editable["document_path"]) == parent["artifact_sha256"]["native"]
    assert len(list(tmp_path.glob("*/verification.json"))) == 1
    Path(editable["document_path"]).write_text("edited synthetic native")
    payload = submit(prepare, editable["edit_id"])
    jsonschema.validate({"payload": payload}, schema)
    result = r.build(payload)
    assert result["revision_id"] != parent["revision_id"]
    assert result["acceptance"] == "accepted" and result["parent_revision_id"] == parent["revision_id"]
    assert result["external_edit"]["submitted_sha256"] == digest(editable["document_path"])
    assert result["parameters"]["width"] == 100
    assert set(result["artifacts"]) == set(FILES) | set(EXTERNAL_FILES)
    assert r._record(result["revision_id"])
    unchanged(parent)


@pytest.mark.parametrize("key", list(EXTERNAL_FILES))
def test_external_source_and_policy_evidence_hashes_are_enforced(tmp_path, key):
    r, parent, prepare = create(tmp_path)
    editable = r.build(prepare)
    result = r.build(submit(prepare, editable["edit_id"]))
    Path(result["artifacts"][key]).write_text("modified")
    with pytest.raises(WorkflowFailure) as exc:
        r._record(result["revision_id"])
    assert exc.value.stage == "revision_integrity"
    unchanged(parent)


@pytest.mark.parametrize("edit_id", ["../elsewhere", "/tmp/native.solidcraft", "solidcraft-source", "edit-missing"])
def test_only_owned_edit_ids_are_accepted(tmp_path, edit_id):
    r, parent, prepare = create(tmp_path)
    before = list(tmp_path.iterdir())
    with pytest.raises((ValueError, WorkflowFailure)):
        r.build(submit(prepare, edit_id))
    assert list(tmp_path.iterdir()) == before
    unchanged(parent)


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "directory", "too_large"])
def test_unsafe_source_files_are_rejected_before_cad_execution(tmp_path, kind):
    r, parent, prepare = create(tmp_path)
    editable = r.build(prepare)
    path = Path(editable["document_path"])
    path.unlink()
    target = tmp_path / "other"
    target.write_text("outside input")
    if kind == "symlink":path.symlink_to(target)
    elif kind == "hardlink":os.link(target, path)
    elif kind == "fifo":os.mkfifo(path)
    elif kind == "directory":path.mkdir()
    else:
        with path.open("wb") as stream:stream.truncate(8 * 1024**2 + 1)
    calls = list(r.backend.calls)
    with pytest.raises(WorkflowFailure) as exc:
        r.build(submit(prepare, editable["edit_id"]))
    assert exc.value.classification == "validation_error" and r.backend.calls == calls
    unchanged(parent)


def test_workspace_directory_symlink_and_foreign_parent_are_rejected(tmp_path):
    r, parent, prepare = create(tmp_path)
    editable = r.build(prepare)
    (tmp_path / "edit-link").symlink_to(Path(editable["document_path"]).parent, target_is_directory=True)
    with pytest.raises(ValueError):r.build(submit(prepare, "edit-link"))
    manifest = Path(editable["document_path"]).with_name("edit.json")
    value = json.loads(manifest.read_text());value["parent_revision_id"] = "solidcraft-foreign"
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError):r.build(submit(prepare, editable["edit_id"]))
    unchanged(parent)


@pytest.mark.parametrize("change", [{"width_cm": 0}, {"width_cm": True}, {"width_cm": float("nan")}, {"fillet_radius_cm": 1}, {}])
def test_invalid_or_unsupported_dimensions_never_reach_native_worker(tmp_path, change):
    r, parent, prepare = create(tmp_path);editable = r.build(prepare)
    p = submit(prepare, editable["edit_id"]);p["parameters"] = change
    with pytest.raises((ValueError, WorkflowFailure)):r.build(p)
    assert r.backend.calls == ["build"]
    unchanged(parent)


def test_paths_are_not_an_import_or_export_interface(tmp_path):
    r, parent, prepare = create(tmp_path)
    for p in ({**prepare, "document_path": "/tmp/input.solidcraft"},
              {**prepare, "external_edit": {"action": "prepare", "output_path": "/tmp/output.solidcraft"}}):
        with pytest.raises(ValueError):r.build(p)
    unchanged(parent)


def test_changed_accepted_parent_is_never_used_or_silently_repaired(tmp_path):
    r, parent, prepare = create(tmp_path);editable = r.build(prepare)
    path = Path(parent["artifacts"]["native"]);path.write_text("altered accepted source")
    with pytest.raises(WorkflowFailure) as exc:r.build(submit(prepare, editable["edit_id"]))
    assert exc.value.stage == "revision_integrity"
    assert path.read_text() == "altered accepted source"
    assert len(list(tmp_path.glob("*/verification.json"))) == 1
    assert r.backend.calls == ["build"]


@pytest.mark.parametrize("classification", ["verification_failed", "cancelled", "timeout"])
def test_interrupted_revalidation_cannot_publish_or_damage_parent(tmp_path, monkeypatch, classification):
    r, parent, prepare = create(tmp_path);editable = r.build(prepare)
    def stop(*args):raise WorkflowFailure("interrupted", stage="verify_geometry", classification=classification)
    monkeypatch.setattr(r.backend, "revalidate", stop)
    with pytest.raises(WorkflowFailure):r.build(submit(prepare, editable["edit_id"]))
    unchanged(parent)
    assert len(list(tmp_path.glob("*/verification.json"))) == 1
    assert not r._transaction.locked()


@pytest.mark.parametrize("target", ["workspace", "snapshot"])
def test_source_drift_during_verification_rejects_candidate(tmp_path, monkeypatch, target):
    r, parent, prepare = create(tmp_path);editable = r.build(prepare)
    original = r.backend.revalidate
    def drift(directory, *args):
        result = original(directory, *args)
        path = Path(editable["document_path"]) if target == "workspace" else directory / "submitted.solidcraft"
        path.write_text("changed during verification")
        return result
    monkeypatch.setattr(r.backend, "revalidate", drift)
    with pytest.raises(WorkflowFailure) as exc:r.build(submit(prepare, editable["edit_id"]))
    assert exc.value.stage == "revision_integrity"
    unchanged(parent)
    assert len(list(tmp_path.glob("*/verification.json"))) == 1


def test_external_acceptance_uses_the_existing_atomic_cancel_commit(tmp_path, monkeypatch):
    r, parent, prepare = create(tmp_path);editable = r.build(prepare)
    cancellation = RequestCancellation();token = REQUEST_CANCEL.set(cancellation)
    original = r._accept
    def cancel_before_commit(report):
        cancellation.set();original(report)
    monkeypatch.setattr(r, "_accept", cancel_before_commit)
    try:
        with pytest.raises(WorkflowFailure) as exc:r.build(submit(prepare, editable["edit_id"]))
        assert exc.value.classification == "cancelled"
    finally:REQUEST_CANCEL.reset(token)
    unchanged(parent)
    assert len(list(tmp_path.glob("*/verification.json"))) == 1


def synthetic_definition():
    return {"format": "solidcraft/20", "name": "part", "units": "mm", "params": [
        {"name": "width", "expr": "100 mm", "unit": "mm", "model": False},
        {"name": "d5", "expr": "width/2", "unit": "mm", "model": True}],
        "features": [{"id": 1, "type": "sketch", "sketch": {"points": [{"pos": [50, 30]}],
                     "constraints": [{"type": "distance_x", "param": "d5", "value": 50}]}}], "next_id": 2}


def test_native_policy_permits_only_display_name_and_literal_value_spelling():
    reference = synthetic_definition();candidate = copy.deepcopy(reference)
    candidate["name"] = "user saved copy";candidate["params"][0]["expr"] = "10 cm"
    assert compare(reference, candidate, {"width": 100})["passed"]


@pytest.mark.parametrize("mutation", ["feature", "constraint", "relationship", "point", "units", "history", "extra_param", "duplicate_param"])
def test_unsupported_authored_changes_cannot_hide_behind_matching_envelope(mutation):
    reference = synthetic_definition();candidate = copy.deepcopy(reference)
    if mutation == "feature":candidate["features"].append({"id": 2, "type": "fillet"})
    elif mutation == "constraint":candidate["features"][0]["sketch"]["constraints"] = []
    elif mutation == "relationship":candidate["params"][1]["expr"] = "50 mm"
    elif mutation == "point":candidate["features"][0]["sketch"]["points"][0]["pos"][0] = 49
    elif mutation == "units":candidate["units"] = "cm"
    elif mutation == "history":candidate["features"] = []
    elif mutation == "extra_param":candidate["params"].append({"name": "other", "expr": "1"})
    else:candidate["params"].append(candidate["params"][0])
    with pytest.raises(WorkflowFailure):compare(reference, candidate, {"width": 100})


@pytest.mark.parametrize("expression", ["height+40", "width", "1/0", "nan", "-100 mm"])
def test_dimension_expression_edits_cannot_introduce_new_dependencies(expression):
    reference = synthetic_definition();candidate = copy.deepcopy(reference)
    candidate["params"][0]["expr"] = expression
    with pytest.raises(WorkflowFailure):compare(reference, candidate, {"width": 100})


@pytest.mark.parametrize("state", [{"sketches": []}, {"sketches": [{"fully_constrained": False, "dof": 2, "status": "solved"}]},
    {"sketches": [{"fully_constrained": True, "dof": 0, "status": "failed"}]}])
def test_underconstrained_or_failed_native_sketches_cannot_be_accepted(state):
    with pytest.raises(WorkflowFailure):constrained(state)


@pytest.mark.parametrize("kind", ["plate", "bracket"])
def test_real_external_native_dimension_edit_is_independently_revalidated(tmp_path, kind):
    cli, python = os.environ.get("PARAMAITRIC_SOLIDCRAFT_CLI"), os.environ.get("PARAMAITRIC_CAD_PYTHON")
    if not cli or not python:
        pytest.skip("Set pinned native CLI and independent CAD Python for real external-edit geometry")
    backend = SolidCraftBackend(Path(cli), Path(python), tmp_path)
    r = SolidCraftRuntime(backend)
    workflow = "plate_with_hole" if kind == "plate" else "bracket"
    p = {"width_cm": 80 if kind == "plate" else 50, "height_cm": 60 if kind == "plate" else 80, "thickness_cm": 5, "units": "mm"}
    p.update({"hole_diameter_cm": 10, "hole_center_x_cm": 40, "hole_center_y_cm": 30} if kind == "plate" else {"leg_thickness_cm": 5})
    parent = r.build({"workflow": workflow, "parameters": p})
    prepare = {"workflow": workflow, "revision_id": parent["revision_id"], "external_edit": {"action": "prepare"}}
    editable = r.build(prepare)
    width = 100 if kind == "plate" else 70
    with backend._session(Path(editable["document_path"]).parent, time.monotonic() + 120) as client:
        client.call("open", {"path": editable["document_path"]})
        client.call("set_parameter", {"name": "width", "value": f"{width} mm"})
        client.call("save", {"path": editable["document_path"]})
    payload = submit(prepare, editable["edit_id"]);payload["parameters"]["width_cm"] = width
    result = r.build(payload)
    assert r._record(result["revision_id"])["external_edit"]["submitted_sha256"] == digest(editable["document_path"])
    assert result["measurements"]["width"] == pytest.approx(width, abs=0.01)
    if kind == "plate":assert result["measurements"]["bore_x"] == pytest.approx(50, abs=0.01)
    assert all(c["passed"] for c in result["verification_signals"])
    unchanged(parent)
