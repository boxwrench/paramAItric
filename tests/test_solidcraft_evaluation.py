import asyncio
import math
import struct

import pytest

from evaluations import solidcraft_eval
from evaluations.solidcraft_cases import BRACKET, PLATE
from evaluations.solidcraft_readback import read_mesh, verify


def plate_facts():
    return {"body_count": 1, "valid": True, "width": 80, "height": 60, "thickness": 5,
            "min_x": 0, "min_y": 0, "min_z": 0, "volume_mm3": 80 * 60 * 5 - math.pi * 25 * 5,
            "bore_diameter": 10, "bore_x": 40, "bore_y": 30, "bore_through": True}


@pytest.mark.parametrize("field,value", [("body_count", 2), ("body_count", True), ("valid", False),
    ("width", float("nan")), ("volume_mm3", float("inf")), ("bore_x", 39),
    ("bore_diameter", 9), ("bore_through", False), ("min_x", 10)])
def test_independent_plate_gates_reject_incorrect_or_incomplete_geometry(field, value):
    facts = plate_facts()
    assert all(c["passed"] for c in verify(facts, "plate", PLATE))
    facts[field] = value
    failed = [c["name"] for c in verify(facts, "plate", PLATE) if not c["passed"]]
    assert field in failed
    facts.pop(field)
    assert field in [c["name"] for c in verify(facts, "plate", PLATE) if not c["passed"]]


def test_bracket_envelope_volume_alone_do_not_prove_the_L_profile():
    facts = {"body_count": 1, "valid": True, "width": 50, "height": 80, "thickness": 5,
             "min_x": 0, "min_y": 0, "min_z": 0, "volume_mm3": 3125,
             "inner_corner": False, "legs_contain_material": False, "inner_void": False}
    checks = verify(facts, "bracket", BRACKET)
    assert {c["name"] for c in checks if not c["passed"]} == {"inner_corner", "legs_contain_material", "inner_void"}


def test_feature_error_cannot_be_accepted_even_if_the_tool_did_not_return_isError(monkeypatch):
    async def fake_call(*args, **kwargs):
        return {"isError": False, "data": {"timeline": [{"name": "Bore", "error": "missing reference"}]}}
    monkeypatch.setattr(solidcraft_eval, "call", fake_call)
    with pytest.raises(ValueError, match="prevent acceptance"):
        asyncio.run(solidcraft_eval.healthy(None, []))


def test_rollback_comparison_checks_parameter_and_undo_history_changes():
    before = {"params": [{"name": "width", "expression": "80 mm"}], "timeline": [], "undo": 2}
    after = {**before, "params": [{"name": "width", "expression": "100 mm"}]}
    assert solidcraft_eval.semantic_state(before) != solidcraft_eval.semantic_state(after)
    assert solidcraft_eval.semantic_state(before) != solidcraft_eval.semantic_state({**before, "undo": 3})


@pytest.mark.parametrize("blob", [b"truncated", b"\0" * 80 + struct.pack("<I", 1),
    b"\0" * 80 + struct.pack("<I", 1) + struct.pack("<12fH", float("nan"), *([0.0] * 11), 0)])
def test_malformed_or_nonfinite_meshes_never_become_export_evidence(tmp_path, blob):
    path = tmp_path / "bad.stl"
    path.write_bytes(blob)
    with pytest.raises(ValueError):
        read_mesh(path, PLATE, plate_facts()["volume_mm3"])
