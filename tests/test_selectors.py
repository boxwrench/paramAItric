"""Tests for the pure selector module (mcp_server/selectors.py).

These tests cover:
  - Increment 1: validate_descriptor
  - Increment 2: SelectionTrace
  - Increment 3: resolve + SelectorAmbiguityError
"""
from __future__ import annotations

import pytest

from mcp_server.selectors import validate_descriptor


# ---------------------------------------------------------------------------
# Increment 1 — descriptor validation
# ---------------------------------------------------------------------------


def test_valid_face_normal_axis_descriptor_normalizes():
    desc = validate_descriptor({
        "target": "face", "kind": "normal_axis",
        "scope": {"body_token": "b1"}, "expect": "one",
        "params": {"axis": "+z"},
    })
    assert desc["target"] == "face"
    assert desc["kind"] == "normal_axis"
    assert desc["scope"]["body_token"] == "b1"
    assert desc["expect"] == "one"
    assert desc["params"] == {"axis": "+z"}
    assert desc["pin"] is None


def test_missing_body_token_rejected():
    with pytest.raises(ValueError, match="body_token"):
        validate_descriptor({"target": "face", "kind": "largest_planar", "scope": {}, "expect": "one"})


def test_unknown_kind_rejected():
    with pytest.raises(ValueError, match="kind"):
        validate_descriptor({"target": "face", "kind": "bogus", "scope": {"body_token": "b1"}, "expect": "one"})


def test_kind_target_mismatch_rejected():
    with pytest.raises(ValueError, match="not valid for target"):
        validate_descriptor({"target": "face", "kind": "geometry_type", "scope": {"body_token": "b1"}, "expect": "one"})


def test_expect_defaults_to_one():
    desc = validate_descriptor({"target": "edge", "kind": "longest", "scope": {"body_token": "b1"}})
    assert desc["expect"] == "one"


def test_normal_axis_requires_valid_axis_param():
    with pytest.raises(ValueError, match="axis"):
        validate_descriptor({"target": "face", "kind": "normal_axis", "scope": {"body_token": "b1"}, "expect": "one", "params": {"axis": "diagonal"}})


# ---------------------------------------------------------------------------
# Increment 2 — SelectionTrace
# ---------------------------------------------------------------------------

from mcp_server.selectors import SelectionTrace


def test_selection_trace_to_dict_roundtrips():
    trace = SelectionTrace(operation="find_face", target="face", kind="normal_axis", params={"axis": "+z"}, expect="one", status="resolved", candidate_count=6, resolved_count=1, resolved_tokens=["b1:face:top"], reason=None)
    payload = trace.to_dict()
    assert payload["operation"] == "find_face"
    assert payload["status"] == "resolved"
    assert payload["candidate_count"] == 6
    assert payload["resolved_tokens"] == ["b1:face:top"]
    assert "trace_id" in payload and payload["trace_id"]


def test_two_traces_have_distinct_ids():
    a = SelectionTrace(operation="x", target="face", kind="largest_planar", params={}, expect="one", status="resolved", candidate_count=1, resolved_count=1, resolved_tokens=["t"], reason=None)
    b = SelectionTrace(operation="x", target="face", kind="largest_planar", params={}, expect="one", status="resolved", candidate_count=1, resolved_count=1, resolved_tokens=["t"], reason=None)
    assert a.trace_id != b.trace_id


# ---------------------------------------------------------------------------
# Increment 3 — resolver with cardinality guards
# ---------------------------------------------------------------------------

from mcp_server.selectors import resolve, SelectorAmbiguityError

FACES = [
    {"token": "b1:face:top", "type": "planar", "normal_vector": {"x": 0.0, "y": 0.0, "z": 1.0}, "area_cm2": 100.0},
    {"token": "b1:face:bottom", "type": "planar", "normal_vector": {"x": 0.0, "y": 0.0, "z": -1.0}, "area_cm2": 100.0},
    {"token": "b1:face:side", "type": "planar", "normal_vector": {"x": 1.0, "y": 0.0, "z": 0.0}, "area_cm2": 40.0},
    {"token": "b1:face:round", "type": "cylindrical", "normal_vector": None, "area_cm2": 30.0},
]
EDGES = [
    {"token": "b1:edge:long", "type": "linear", "length_cm": 10.0},
    {"token": "b1:edge:short", "type": "linear", "length_cm": 4.0},
    {"token": "b1:edge:hole", "type": "circular", "length_cm": 6.28},
]


def _desc(**kw):
    from mcp_server.selectors import validate_descriptor
    base = {"scope": {"body_token": "b1"}, "expect": "one", "params": {}}
    base.update(kw)
    return validate_descriptor(base)


def test_normal_axis_selects_top_face():
    desc = _desc(target="face", kind="normal_axis", params={"axis": "+z"})
    result, trace = resolve(desc, FACES, EDGES, operation="t")
    assert result["tokens"] == ["b1:face:top"]
    assert trace.status == "resolved"


def test_largest_planar_with_tie_fails_closed_when_expect_one():
    desc = _desc(target="face", kind="largest_planar")
    with pytest.raises(SelectorAmbiguityError) as exc:
        resolve(desc, FACES, EDGES, operation="t")
    assert exc.value.trace.status == "ambiguous"
    assert exc.value.trace.candidate_count == 2


def test_expect_many_returns_all_matches_without_error():
    desc = _desc(target="edge", kind="geometry_type", params={"type": "linear"}, expect="many")
    result, trace = resolve(desc, FACES, EDGES, operation="t")
    assert set(result["tokens"]) == {"b1:edge:long", "b1:edge:short"}
    assert trace.status == "resolved"
    assert trace.resolved_count == 2


def test_edge_longest_selects_single_edge():
    desc = _desc(target="edge", kind="longest")
    result, trace = resolve(desc, FACES, EDGES, operation="t")
    assert result["tokens"] == ["b1:edge:long"]


def test_empty_candidate_set_fails_closed():
    desc = _desc(target="edge", kind="geometry_type", params={"type": "circular"})
    no_circular = [e for e in EDGES if e["type"] != "circular"]
    with pytest.raises(SelectorAmbiguityError) as exc:
        resolve(desc, FACES, no_circular, operation="t")
    assert exc.value.trace.status == "empty"
