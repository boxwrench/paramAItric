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
