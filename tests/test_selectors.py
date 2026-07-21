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


@pytest.mark.parametrize("kind", ["axis_parallel", "max_face_perimeter"])
def test_relational_edge_kinds_require_cartesian_axis(kind):
    with pytest.raises(ValueError, match="axis"):
        validate_descriptor({
            "target": "edge",
            "kind": kind,
            "scope": {"body_token": "b1"},
            "expect": "many",
            "params": {"axis": "+z"},
        })


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

BOX_EDGES = [
    {"token": "bottom_x", "type": "linear", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 4, "y": 0, "z": 0}, "length_cm": 4},
    {"token": "top_front", "type": "linear", "start_point": {"x": 0, "y": 0, "z": 1}, "end_point": {"x": 4, "y": 0, "z": 1}, "length_cm": 4},
    {"token": "top_right", "type": "linear", "start_point": {"x": 4, "y": 0, "z": 1}, "end_point": {"x": 4, "y": 2, "z": 1}, "length_cm": 2},
    {"token": "top_back", "type": "linear", "start_point": {"x": 4, "y": 2, "z": 1}, "end_point": {"x": 0, "y": 2, "z": 1}, "length_cm": 4},
    {"token": "top_left", "type": "linear", "start_point": {"x": 0, "y": 2, "z": 1}, "end_point": {"x": 0, "y": 0, "z": 1}, "length_cm": 2},
    {"token": "vertical", "type": "linear", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 0, "y": 0, "z": 1}, "length_cm": 1},
    {"token": "circle", "type": "circular", "start_point": None, "end_point": None, "length_cm": 1},
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


def test_axis_parallel_selects_only_linear_edges_in_requested_direction():
    desc = _desc(target="edge", kind="axis_parallel", params={"axis": "z"}, expect="many")
    result, trace = resolve(desc, FACES, BOX_EDGES, operation="t")
    assert result["tokens"] == ["vertical"]
    assert trace.kind == "axis_parallel"


def test_max_face_perimeter_selects_top_outer_loop():
    desc = _desc(target="edge", kind="max_face_perimeter", params={"axis": "z"}, expect="many")
    result, trace = resolve(desc, FACES, BOX_EDGES, operation="t")
    assert set(result["tokens"]) == {"top_front", "top_right", "top_back", "top_left"}
    assert trace.resolved_count == 4


def test_empty_candidate_set_fails_closed():
    desc = _desc(target="edge", kind="geometry_type", params={"type": "circular"})
    no_circular = [e for e in EDGES if e["type"] != "circular"]
    with pytest.raises(SelectorAmbiguityError) as exc:
        resolve(desc, FACES, no_circular, operation="t")
    assert exc.value.trace.status == "empty"


# ---------------------------------------------------------------------------
# Increment 4 — attribute pinning (G5)
# ---------------------------------------------------------------------------


def test_pin_accepts_attribute_record():
    # Re-specified from the old string form: a pin is now a recorded-attribute
    # record (policy: pins match on attributes, not identity).
    pin = {"target": "face", "attributes": {"type": "planar", "area_cm2": 100.0}}
    desc = validate_descriptor({
        "target": "face", "kind": "largest_planar",
        "scope": {"body_token": "b1"}, "expect": "one",
        "pin": pin,
    })
    assert desc["pin"] == pin


def test_pin_rejects_bare_string():
    # The old bookmark-by-token form is no longer accepted.
    with pytest.raises(ValueError, match="pin"):
        validate_descriptor({
            "target": "face", "kind": "largest_planar",
            "scope": {"body_token": "b1"}, "expect": "one",
            "pin": "b1:face:top",
        })


def test_unpinned_descriptor_pin_is_none():
    desc = validate_descriptor({
        "target": "face", "kind": "largest_planar",
        "scope": {"body_token": "b1"}, "expect": "one",
    })
    assert desc["pin"] is None


def test_create_pin_records_attributes_not_identity():
    from mcp_server.selectors import create_pin

    top_face = FACES[0]  # b1:face:top
    pin = create_pin("face", top_face)
    assert pin["target"] == "face"
    assert isinstance(pin["attributes"], dict) and pin["attributes"]
    # A pin must never record the entity token — that is bookmarking by
    # identity, which the policy rejects.
    assert "token" not in pin["attributes"]
    assert top_face["token"] not in pin["attributes"].values()


def test_create_pin_distinguishes_differently_shaped_faces():
    from mcp_server.selectors import create_pin

    # The top face and the side face differ in shape; their recorded
    # attributes must differ, or a pin could never tell them apart.
    top_pin = create_pin("face", FACES[0])   # planar, +z, area 100
    side_pin = create_pin("face", FACES[2])  # planar, +x, area 40
    assert top_pin["attributes"] != side_pin["attributes"]


def test_fresh_pin_resolves_to_single_entity():
    from mcp_server.selectors import create_pin

    pin = create_pin("face", FACES[0])  # b1:face:top
    desc = validate_descriptor({
        "target": "face", "kind": "largest_planar",
        "scope": {"body_token": "b1"}, "expect": "one",
        "pin": pin,
    })
    result, trace = resolve(desc, FACES, EDGES, operation="t")
    assert result["tokens"] == ["b1:face:top"]
    assert trace.status == "resolved"


def test_pin_matches_through_sub_tolerance_float_noise():
    from mcp_server.selectors import create_pin

    pin = create_pin("face", FACES[0])  # area 100.0, +z
    # The same face after a recompute with sub-tolerance float noise.
    noisy = [dict(FACES[0], area_cm2=100.0 + 1e-9)] + FACES[1:]
    desc = validate_descriptor({
        "target": "face", "kind": "largest_planar",
        "scope": {"body_token": "b1"}, "expect": "one",
        "pin": pin,
    })
    result, trace = resolve(desc, noisy, EDGES, operation="t")
    assert result["tokens"] == ["b1:face:top"]
    assert trace.status == "resolved"


def test_fresh_pin_success_trace_records_pin_presence():
    from mcp_server.selectors import create_pin

    pin = create_pin("edge", EDGES[0])  # b1:edge:long
    desc = validate_descriptor({
        "target": "edge", "kind": "longest",
        "scope": {"body_token": "b1"}, "expect": "one",
        "pin": pin,
    })
    _, trace = resolve(desc, FACES, EDGES, operation="t")
    assert trace.pin_present is True
    assert trace.pin_resolved is True


def test_stale_pin_hard_fails_with_structured_error():
    from mcp_server.selectors import create_pin

    # Pin a face that is absent from the pool at resolve time.
    ghost = {"token": "b1:face:ghost", "type": "planar",
             "normal_vector": {"x": 0.0, "y": 1.0, "z": 0.0}, "area_cm2": 77.0}
    pin = create_pin("face", ghost)
    desc = validate_descriptor({
        "target": "face", "kind": "largest_planar",
        "scope": {"body_token": "b1"}, "expect": "one",
        "pin": pin,
    })
    with pytest.raises(SelectorAmbiguityError) as exc:
        resolve(desc, FACES, EDGES, operation="t")
    trace = exc.value.trace
    assert trace.status == "pin_stale"
    assert trace.pin_present is True
    assert trace.pin_resolved is False
    assert trace.candidate_count == 0
    # Structured, actionable failure: guidance to re-select, and the recorded
    # attributes surfaced so the caller need not correlate.
    assert trace.next_step
    assert trace.to_dict()["pin_attributes"] == pin["attributes"]


def test_no_semantic_fallback_when_pin_is_stale():
    from mcp_server.selectors import create_pin

    # A stale pin whose SEMANTIC descriptor would resolve cleanly must still
    # hard-fail. If it resolves, a forbidden fallback path exists.
    ghost = {"token": "b1:edge:ghost", "type": "linear", "length_cm": 999.0}
    pin = create_pin("edge", ghost)
    desc = validate_descriptor({
        "target": "edge", "kind": "longest",  # would cleanly pick b1:edge:long
        "scope": {"body_token": "b1"}, "expect": "one",
        "pin": pin,
    })
    with pytest.raises(SelectorAmbiguityError) as exc:
        resolve(desc, FACES, EDGES, operation="t")
    assert exc.value.trace.status == "pin_stale"


def test_pin_duplicated_by_symmetry_is_pin_ambiguous():
    from mcp_server.selectors import create_pin

    # A symmetric topology change produced a second face with identical
    # intrinsic attributes; the pin can no longer identify one.
    pin = create_pin("face", FACES[0])  # planar, +z, area 100
    twin = dict(FACES[0], token="b1:face:top_twin")
    pool = FACES + [twin]
    desc = validate_descriptor({
        "target": "face", "kind": "largest_planar",
        "scope": {"body_token": "b1"}, "expect": "one",
        "pin": pin,
    })
    with pytest.raises(SelectorAmbiguityError) as exc:
        resolve(desc, pool, EDGES, operation="t")
    trace = exc.value.trace
    assert trace.status == "pin_ambiguous"
    assert trace.candidate_count == 2
    assert trace.pin_present is True
    assert trace.pin_resolved is False


def test_pin_against_deleted_geometry_is_stale():
    from mcp_server.selectors import create_pin

    # Pin a real face, then resolve against a pool from which it was deleted.
    pin = create_pin("face", FACES[2])  # b1:face:side
    pool = [f for f in FACES if f["token"] != "b1:face:side"]
    desc = validate_descriptor({
        "target": "face", "kind": "normal_axis",
        "scope": {"body_token": "b1"}, "expect": "one",
        "params": {"axis": "+x"},
        "pin": pin,
    })
    with pytest.raises(SelectorAmbiguityError) as exc:
        resolve(desc, pool, EDGES, operation="t")
    assert exc.value.trace.status == "pin_stale"


def test_pin_survives_unrelated_topology_change():
    from mcp_server.selectors import create_pin

    # Regression guard for the intrinsic-attribute choice: an unrelated face
    # (same area as the pinned one, but a different normal) is added. A pin that
    # recorded only area — or any positional data — would misbehave. This one
    # must still resolve to exactly the pinned face.
    pin = create_pin("face", FACES[0])  # planar, +z, area 100
    unrelated = {"token": "b1:face:new", "type": "planar",
                 "normal_vector": {"x": 0.0, "y": 1.0, "z": 0.0}, "area_cm2": 100.0}
    pool = FACES + [unrelated]
    desc = validate_descriptor({
        "target": "face", "kind": "largest_planar",
        "scope": {"body_token": "b1"}, "expect": "one",
        "pin": pin,
    })
    result, trace = resolve(desc, pool, EDGES, operation="t")
    assert result["tokens"] == ["b1:face:top"]
    assert trace.status == "resolved"


def test_unpinned_resolve_leaves_pin_trace_fields_default():
    # The semantic path must not touch pin visibility fields.
    desc = _desc(target="face", kind="normal_axis", params={"axis": "+z"})
    _, trace = resolve(desc, FACES, EDGES, operation="t")
    assert trace.pin_present is False
    assert trace.pin_resolved is None
    assert trace.to_dict()["pin_attributes"] is None
