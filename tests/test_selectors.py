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
