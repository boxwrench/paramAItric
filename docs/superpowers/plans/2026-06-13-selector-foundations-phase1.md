# Selector Foundations — Phase 1 Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ParamAItric's opaque, MCP-side geometry selection with a small deterministic semantic selector layer that resolves against live topology add-in-side, fails closed on ambiguity, and emits an explainable `SelectionTrace`.

**Architecture:** A shared, pure resolver module (`mcp_server/selectors.py`) defines a JSON-serializable selector *descriptor*, a `SelectionTrace` dataclass, and deterministic resolution over the face/edge dicts the add-in already produces. A new `resolve_selector` command is registered in both `fusion_addin/ops/mock_ops.py` and `fusion_addin/ops/live_ops.py`; each fetches live faces/edges and delegates to the pure resolver. `find_face` is then retrofitted to go through this path, preserving its existing six directional selectors as a compatibility mapping.

**Tech Stack:** Python 3 (stdlib + dataclasses), pytest. No new dependencies. No external CAD runtime dependency (per `docs/NEXT_PHASE_PLAN.md` planning rules).

**Scope guardrails (from `internal/research/selector-foundations-2026-04-08/SYNTHESIS.md`):**
- v1 vocabulary only: `face_normal_axis`, `face_largest_planar`, `edge_geometry_type`, `edge_longest`.
- Cardinality (`expect: one|many`) is a first-class contract; singleton ambiguity fails closed *before* any mutation.
- `SelectionTrace` is a **diagnostic** artifact, not a second verification gate.
- Do NOT build: selector ASTs, affinity scores, topology fingerprints, relational selectors, persistent cross-session identity, candidate-pool dumps as normal output.

---

## File Structure

- Create: `mcp_server/selectors.py` — descriptor validation, `SelectionTrace`, pure deterministic resolver. (Shared; importable by both MCP and add-in layers, consistent with existing `from mcp_server.schemas import ...` imports inside `fusion_addin/ops/live_ops.py`.)
- Create: `tests/test_selectors.py` — pure unit tests for descriptor validation, resolution, cardinality guards, trace emission.
- Modify: `fusion_addin/ops/mock_ops.py` — register `resolve_selector` command; fetch faces/edges and delegate to resolver.
- Modify: `fusion_addin/ops/live_ops.py` — register `resolve_selector` command; same delegation against live B-Rep.
- Modify: `tests/test_addin_workflows.py` — integration test that `resolve_selector` works through the mock registry end-to-end.
- Modify: `mcp_server/primitives/core.py:360-407` — retrofit `find_face` to build a descriptor, call `resolve_selector`, and return the trace.
- Modify: `tests/test_workflow.py` (or wherever `find_face` is covered) — assert retrofitted `find_face` still returns the correct face for legacy directional selectors and now includes a `selection_trace`.

---

## Task 1: Selector descriptor schema + validation

**Files:**
- Create: `mcp_server/selectors.py`
- Test: `tests/test_selectors.py`

A descriptor is a plain dict (JSON-serializable across the bridge). Validation normalizes and rejects malformed input before any topology work.

Descriptor shape:
```python
{
    "target": "face" | "edge",
    "kind": "normal_axis" | "largest_planar" | "geometry_type" | "longest",
    "scope": {"body_token": "<token>"},
    "expect": "one" | "many",
    "params": { ... },          # kind-specific, may be omitted/empty
    "pin": "<optional name>",   # reserved for later attribute pinning; carried, not used yet
}
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_selectors.py
import pytest

from mcp_server.selectors import validate_descriptor


def test_valid_face_normal_axis_descriptor_normalizes():
    desc = validate_descriptor({
        "target": "face",
        "kind": "normal_axis",
        "scope": {"body_token": "b1"},
        "expect": "one",
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
        validate_descriptor({
            "target": "face", "kind": "largest_planar",
            "scope": {}, "expect": "one",
        })


def test_unknown_kind_rejected():
    with pytest.raises(ValueError, match="kind"):
        validate_descriptor({
            "target": "face", "kind": "bogus",
            "scope": {"body_token": "b1"}, "expect": "one",
        })


def test_kind_target_mismatch_rejected():
    # geometry_type is an edge kind; pairing with target=face is invalid
    with pytest.raises(ValueError, match="not valid for target"):
        validate_descriptor({
            "target": "face", "kind": "geometry_type",
            "scope": {"body_token": "b1"}, "expect": "one",
        })


def test_expect_defaults_to_one():
    desc = validate_descriptor({
        "target": "edge", "kind": "longest",
        "scope": {"body_token": "b1"},
    })
    assert desc["expect"] == "one"


def test_normal_axis_requires_valid_axis_param():
    with pytest.raises(ValueError, match="axis"):
        validate_descriptor({
            "target": "face", "kind": "normal_axis",
            "scope": {"body_token": "b1"}, "expect": "one",
            "params": {"axis": "diagonal"},
        })
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_selectors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mcp_server.selectors'`

- [ ] **Step 3: Write minimal implementation**

```python
# mcp_server/selectors.py
"""Deterministic semantic selector layer for ParamAItric (Phase 1).

Descriptors are plain JSON-serializable dicts so they cross the Fusion bridge
unchanged. Resolution is pure: it operates on the face/edge dicts the add-in
already produces from live B-Rep, so it is fully unit-testable without Fusion.
"""
from __future__ import annotations

# kind -> the target it is valid for
_FACE_KINDS = {"normal_axis", "largest_planar"}
_EDGE_KINDS = {"geometry_type", "longest"}
_VALID_AXES = {"+x", "-x", "+y", "-y", "+z", "-z"}
_VALID_EDGE_TYPES = {"linear", "circular"}


def validate_descriptor(raw: dict) -> dict:
    """Validate and normalize a selector descriptor. Raises ValueError on bad input."""
    if not isinstance(raw, dict):
        raise ValueError("selector descriptor must be a dict.")

    target = raw.get("target")
    if target not in {"face", "edge"}:
        raise ValueError("selector target must be 'face' or 'edge'.")

    kind = raw.get("kind")
    valid_kinds = _FACE_KINDS if target == "face" else _EDGE_KINDS
    if kind not in (_FACE_KINDS | _EDGE_KINDS):
        raise ValueError(f"unknown selector kind: {kind!r}.")
    if kind not in valid_kinds:
        raise ValueError(f"selector kind {kind!r} is not valid for target {target!r}.")

    scope = raw.get("scope") or {}
    body_token = scope.get("body_token")
    if not isinstance(body_token, str) or not body_token.strip():
        raise ValueError("selector scope.body_token must be a non-empty string.")

    expect = raw.get("expect", "one")
    if expect not in {"one", "many"}:
        raise ValueError("selector expect must be 'one' or 'many'.")

    params = raw.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("selector params must be a dict.")
    params = _validate_params(kind, params)

    pin = raw.get("pin")
    if pin is not None and (not isinstance(pin, str) or not pin.strip()):
        raise ValueError("selector pin must be a non-empty string when provided.")

    return {
        "target": target,
        "kind": kind,
        "scope": {"body_token": body_token},
        "expect": expect,
        "params": params,
        "pin": pin,
    }


def _validate_params(kind: str, params: dict) -> dict:
    if kind == "normal_axis":
        axis = params.get("axis")
        if axis not in _VALID_AXES:
            raise ValueError(f"normal_axis requires params.axis in {sorted(_VALID_AXES)}.")
        return {"axis": axis}
    if kind == "geometry_type":
        edge_type = params.get("type")
        if edge_type not in _VALID_EDGE_TYPES:
            raise ValueError(f"geometry_type requires params.type in {sorted(_VALID_EDGE_TYPES)}.")
        return {"type": edge_type}
    # largest_planar and longest take no params
    return {}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_selectors.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add mcp_server/selectors.py tests/test_selectors.py
git commit -m "feat(selectors): add validated selector descriptor schema"
```

---

## Task 2: SelectionTrace dataclass

**Files:**
- Modify: `mcp_server/selectors.py`
- Test: `tests/test_selectors.py`

Trace fields are the minimal high-signal set from the synthesis (intent vs. resolution, candidate count, status, reason). No telemetry, no geometry dumps in the default path.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_selectors.py  (append)
from mcp_server.selectors import SelectionTrace


def test_selection_trace_to_dict_roundtrips():
    trace = SelectionTrace(
        operation="find_face",
        target="face",
        kind="normal_axis",
        params={"axis": "+z"},
        expect="one",
        status="resolved",
        candidate_count=6,
        resolved_count=1,
        resolved_tokens=["b1:face:top"],
        reason=None,
    )
    payload = trace.to_dict()
    assert payload["operation"] == "find_face"
    assert payload["status"] == "resolved"
    assert payload["candidate_count"] == 6
    assert payload["resolved_tokens"] == ["b1:face:top"]
    assert "trace_id" in payload and payload["trace_id"]


def test_two_traces_have_distinct_ids():
    a = SelectionTrace(operation="x", target="face", kind="largest_planar",
                       params={}, expect="one", status="resolved",
                       candidate_count=1, resolved_count=1,
                       resolved_tokens=["t"], reason=None)
    b = SelectionTrace(operation="x", target="face", kind="largest_planar",
                       params={}, expect="one", status="resolved",
                       candidate_count=1, resolved_count=1,
                       resolved_tokens=["t"], reason=None)
    assert a.trace_id != b.trace_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_selectors.py -k trace -v`
Expected: FAIL with `ImportError: cannot import name 'SelectionTrace'`

- [ ] **Step 3: Write minimal implementation**

```python
# mcp_server/selectors.py  (add imports at top)
import uuid
from dataclasses import dataclass, field
```

```python
# mcp_server/selectors.py  (append)
@dataclass
class SelectionTrace:
    """Diagnostic record of one selector resolution. NOT a verification gate."""
    operation: str
    target: str
    kind: str
    params: dict
    expect: str
    status: str               # "resolved" | "ambiguous" | "empty" | "error"
    candidate_count: int
    resolved_count: int
    resolved_tokens: list
    reason: str | None
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "operation": self.operation,
            "target": self.target,
            "kind": self.kind,
            "params": self.params,
            "expect": self.expect,
            "status": self.status,
            "candidate_count": self.candidate_count,
            "resolved_count": self.resolved_count,
            "resolved_tokens": self.resolved_tokens,
            "reason": self.reason,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_selectors.py -k trace -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mcp_server/selectors.py tests/test_selectors.py
git commit -m "feat(selectors): add SelectionTrace diagnostic dataclass"
```

---

## Task 3: Deterministic resolver with cardinality guards

**Files:**
- Modify: `mcp_server/selectors.py`
- Test: `tests/test_selectors.py`

`resolve(descriptor, faces, edges, operation)` returns `(result_dict, SelectionTrace)`. It never mutates geometry. Singleton ambiguity returns `status="ambiguous"` and raises so callers fail closed before mutation. The face/edge dict shapes match what `get_body_faces`/`get_body_edges` already return (`token`, `type`, `normal_vector`, `area_cm2`, `length_cm`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_selectors.py  (append)
from mcp_server.selectors import resolve, SelectorAmbiguityError

FACES = [
    {"token": "b1:face:top", "type": "planar",
     "normal_vector": {"x": 0.0, "y": 0.0, "z": 1.0}, "area_cm2": 100.0},
    {"token": "b1:face:bottom", "type": "planar",
     "normal_vector": {"x": 0.0, "y": 0.0, "z": -1.0}, "area_cm2": 100.0},
    {"token": "b1:face:side", "type": "planar",
     "normal_vector": {"x": 1.0, "y": 0.0, "z": 0.0}, "area_cm2": 40.0},
    {"token": "b1:face:round", "type": "cylindrical",
     "normal_vector": None, "area_cm2": 30.0},
]
EDGES = [
    {"token": "b1:edge:long", "type": "linear", "length_cm": 10.0},
    {"token": "b1:edge:short", "type": "linear", "length_cm": 4.0},
    {"token": "b1:edge:hole", "type": "circular", "length_cm": 6.28},
]


def _desc(**kw):
    base = {"scope": {"body_token": "b1"}, "expect": "one", "params": {}}
    base.update(kw)
    from mcp_server.selectors import validate_descriptor
    return validate_descriptor(base)


def test_normal_axis_selects_top_face():
    desc = _desc(target="face", kind="normal_axis", params={"axis": "+z"})
    result, trace = resolve(desc, FACES, EDGES, operation="t")
    assert result["tokens"] == ["b1:face:top"]
    assert trace.status == "resolved"


def test_largest_planar_with_tie_fails_closed_when_expect_one():
    # top and bottom both have area 100 -> ambiguous singleton
    desc = _desc(target="face", kind="largest_planar")
    with pytest.raises(SelectorAmbiguityError) as exc:
        resolve(desc, FACES, EDGES, operation="t")
    assert exc.value.trace.status == "ambiguous"
    assert exc.value.trace.candidate_count == 2


def test_expect_many_returns_all_matches_without_error():
    desc = _desc(target="edge", kind="geometry_type",
                 params={"type": "linear"}, expect="many")
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_selectors.py -k "normal_axis or largest or expect_many or longest or empty_candidate" -v`
Expected: FAIL with `ImportError: cannot import name 'resolve'`

- [ ] **Step 3: Write minimal implementation**

```python
# mcp_server/selectors.py  (append)
_AXIS_TO_VECTOR = {
    "+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0),
    "+y": (0.0, 1.0, 0.0), "-y": (0.0, -1.0, 0.0),
    "+z": (0.0, 0.0, 1.0), "-z": (0.0, 0.0, -1.0),
}
_AXIS_TOLERANCE = 0.9  # dot product threshold for "aligned with axis"
_AREA_TIE_TOLERANCE = 1e-6


class SelectorAmbiguityError(ValueError):
    """Raised when a singleton selector cannot resolve to exactly one entity."""

    def __init__(self, message: str, trace: "SelectionTrace") -> None:
        super().__init__(message)
        self.trace = trace


def resolve(descriptor: dict, faces: list, edges: list, operation: str):
    """Resolve a validated descriptor. Returns (result, trace) or raises SelectorAmbiguityError."""
    target = descriptor["target"]
    kind = descriptor["kind"]
    params = descriptor["params"]
    expect = descriptor["expect"]
    pool = faces if target == "face" else edges

    candidates = _filter_and_rank(kind, params, pool)

    def _trace(status, tokens, reason):
        return SelectionTrace(
            operation=operation, target=target, kind=kind, params=params,
            expect=expect, status=status, candidate_count=len(candidates),
            resolved_count=len(tokens), resolved_tokens=tokens, reason=reason,
        )

    tokens = [c["token"] for c in candidates]

    if not candidates:
        trace = _trace("empty", [], f"no {target} matched selector {kind!r}.")
        raise SelectorAmbiguityError(trace.reason, trace)

    if expect == "one":
        if len(candidates) > 1:
            trace = _trace("ambiguous", tokens,
                           f"selector {kind!r} expected one {target} but matched {len(candidates)}.")
            raise SelectorAmbiguityError(trace.reason, trace)
        trace = _trace("resolved", tokens, None)
        return {"tokens": tokens, "entities": candidates}, trace

    # expect == "many"
    trace = _trace("resolved", tokens, None)
    return {"tokens": tokens, "entities": candidates}, trace


def _filter_and_rank(kind: str, params: dict, pool: list) -> list:
    if kind == "normal_axis":
        ax = _AXIS_TO_VECTOR[params["axis"]]
        return [f for f in pool if _aligned(f.get("normal_vector"), ax)]
    if kind == "largest_planar":
        planar = [f for f in pool if f.get("type") == "planar"]
        if not planar:
            return []
        top = max(f.get("area_cm2", 0.0) for f in planar)
        return [f for f in planar if abs(f.get("area_cm2", 0.0) - top) <= _AREA_TIE_TOLERANCE]
    if kind == "geometry_type":
        return [e for e in pool if e.get("type") == params["type"]]
    if kind == "longest":
        if not pool:
            return []
        top = max(e.get("length_cm", 0.0) for e in pool)
        return [e for e in pool if abs(e.get("length_cm", 0.0) - top) <= _AREA_TIE_TOLERANCE]
    return []


def _aligned(normal: dict | None, axis: tuple) -> bool:
    if not normal:
        return False
    dot = normal.get("x", 0.0) * axis[0] + normal.get("y", 0.0) * axis[1] + normal.get("z", 0.0) * axis[2]
    return dot >= _AXIS_TOLERANCE
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_selectors.py -v`
Expected: PASS (all selector tests)

- [ ] **Step 5: Commit**

```bash
git add mcp_server/selectors.py tests/test_selectors.py
git commit -m "feat(selectors): add deterministic resolver with cardinality guards"
```

---

## Task 4: Register `resolve_selector` command in the mock registry

**Files:**
- Modify: `fusion_addin/ops/mock_ops.py` (register alongside `get_body_faces` at line ~156; add handler function)
- Test: `tests/test_addin_workflows.py`

The command fetches faces+edges from the existing handlers, then delegates to the pure resolver. On ambiguity it returns a structured failure payload *including the trace* rather than raising into the bridge.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_addin_workflows.py  (append; reuse this module's existing registry fixture/setup)
from fusion_addin.ops.mock_ops import build_registry
from fusion_addin.state import DesignState


def _seed_plate(state):
    # Use the same flow other tests in this file use to create a body; if a helper
    # exists, call it. Otherwise build via the registry's design/sketch/extrude ops.
    reg = build_registry()
    reg.execute(state, "new_design", {"name": "t"})
    sketch = reg.execute(state, "create_sketch", {"plane": "xy", "name": "s"})
    reg.execute(state, "draw_rectangle",
                {"sketch_token": sketch["sketch_token"], "width_cm": 10.0, "height_cm": 5.0})
    body = reg.execute(state, "extrude_profile",
                       {"sketch_token": sketch["sketch_token"], "distance_cm": 2.0,
                        "operation": "new_body"})
    return reg, body["body_token"]


def test_resolve_selector_top_face_through_mock_registry():
    state = DesignState()
    reg, body_token = _seed_plate(state)
    result = reg.execute(state, "resolve_selector", {
        "target": "face", "kind": "normal_axis",
        "scope": {"body_token": body_token}, "expect": "one",
        "params": {"axis": "+z"},
    })
    assert result["ok"] is True
    assert result["tokens"] == [f"{body_token}:face:top"]
    assert result["selection_trace"]["status"] == "resolved"


def test_resolve_selector_ambiguous_returns_structured_failure():
    state = DesignState()
    reg, body_token = _seed_plate(state)
    result = reg.execute(state, "resolve_selector", {
        "target": "face", "kind": "largest_planar",
        "scope": {"body_token": body_token}, "expect": "one",
    })
    assert result["ok"] is False
    assert result["selection_trace"]["status"] == "ambiguous"
```

> Note: confirm the exact body-creation handler names/args against the top of `tests/test_addin_workflows.py` before running; adjust `_seed_plate` to match the helper that file already uses. The assertion `f"{body_token}:face:top"` matches the mock face tokens in `fusion_addin/ops/mock_ops.py:650-740`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_addin_workflows.py -k resolve_selector -v`
Expected: FAIL — `resolve_selector` is not a registered command.

- [ ] **Step 3: Write minimal implementation**

```python
# fusion_addin/ops/mock_ops.py  (add near other imports)
from mcp_server.selectors import validate_descriptor, resolve, SelectorAmbiguityError
```

```python
# fusion_addin/ops/mock_ops.py  (add handler near get_body_faces/get_body_edges)
def resolve_selector(state: DesignState, arguments: dict) -> dict:
    descriptor = validate_descriptor(arguments)
    body_token = descriptor["scope"]["body_token"]
    faces = get_body_faces(state, {"body_token": body_token}).get("body_faces", [])
    edges = get_body_edges(state, {"body_token": body_token}).get("body_edges", [])
    try:
        result, trace = resolve(descriptor, faces, edges, operation="resolve_selector")
    except SelectorAmbiguityError as exc:
        return {"ok": False, "tokens": [], "selection_trace": exc.trace.to_dict()}
    return {"ok": True, "tokens": result["tokens"], "selection_trace": trace.to_dict()}
```

```python
# fusion_addin/ops/mock_ops.py  (in build_registry, near line 156)
    registry.register("resolve_selector", resolve_selector)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_addin_workflows.py -k resolve_selector -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add fusion_addin/ops/mock_ops.py tests/test_addin_workflows.py
git commit -m "feat(selectors): register resolve_selector command in mock registry"
```

---

## Task 5: Register `resolve_selector` command in the live registry

**Files:**
- Modify: `fusion_addin/ops/live_ops.py` (register alongside `get_body_faces` at line ~1880; add a module-level handler)

The live add-in already has `get_body_faces`/`get_body_edges` adapter methods (`live_ops.py:1158`, `1186`) returning the same dict shape as the mock. The handler mirrors Task 4 but pulls from the live adapter via the same `session_for`/adapter accessor pattern the neighboring registrations use.

> No new unit test here: live resolution requires Fusion and is exercised by the smoke runner (Task 8). This task is a structural mirror of Task 4 against live adapters; correctness of the pure logic is already covered by Tasks 1–4.

- [ ] **Step 1: Read the neighboring registration to copy the exact adapter/session pattern**

Run: `sed -n '1870,1900p' fusion_addin/ops/live_ops.py`
Expected: see how `get_body_faces` is registered (it wraps a module-level `get_body_faces(adapter, arguments, session)` call). Match that signature exactly.

- [ ] **Step 2: Write the handler mirroring the existing get_body_faces wrapper**

```python
# fusion_addin/ops/live_ops.py  (add import near the existing mcp_server import)
from mcp_server.selectors import validate_descriptor, resolve, SelectorAmbiguityError
```

```python
# fusion_addin/ops/live_ops.py  (add module-level handler; match the (adapter, arguments, session)
# shape used by the existing get_body_faces wrapper you read in Step 1)
def resolve_selector(adapter, arguments: dict, session) -> dict:
    descriptor = validate_descriptor(arguments)
    body_token = descriptor["scope"]["body_token"]
    faces = adapter.get_body_faces(body_token)
    edges = adapter.get_body_edges(body_token)
    try:
        result, trace = resolve(descriptor, faces, edges, operation="resolve_selector")
    except SelectorAmbiguityError as exc:
        return {"ok": False, "tokens": [], "selection_trace": exc.trace.to_dict()}
    return {"ok": True, "tokens": result["tokens"], "selection_trace": trace.to_dict()}
```

```python
# fusion_addin/ops/live_ops.py  (in the build_registry function, alongside the get_body_faces
# registration near line 1880 — copy the exact lambda/session_for shape used there)
    registry.register(
        "resolve_selector",
        lambda state, arguments: resolve_selector(
            adapter_for({**arguments, "_command_name": "resolve_selector"}),
            {**arguments, "_command_name": "resolve_selector"},
            session_for({**arguments, "_command_name": "resolve_selector"}),
        ),
    )
```

> The `adapter_for`/`session_for` names above are placeholders for whatever accessors the neighboring `get_body_faces` registration actually uses — Step 1 tells you the real names. Use those verbatim.

- [ ] **Step 3: Verify the module imports cleanly (no Fusion required for import)**

Run: `python -c "import ast; ast.parse(open('fusion_addin/ops/live_ops.py').read()); print('parse-ok')"`
Expected: `parse-ok`

- [ ] **Step 4: Run the existing add-in test suite to confirm no regressions**

Run: `pytest tests/test_addin_workflows.py tests/test_dispatcher.py -v`
Expected: PASS (existing tests unaffected)

- [ ] **Step 5: Commit**

```bash
git add fusion_addin/ops/live_ops.py
git commit -m "feat(selectors): register resolve_selector command in live registry"
```

---

## Task 6: Retrofit `find_face` to use the selector path

**Files:**
- Modify: `mcp_server/primitives/core.py:360-407`
- Test: `tests/test_workflow.py` (or the existing module covering `find_face`)

`find_face` keeps its public six-direction selectors but maps them to `normal_axis` descriptors, routes through `resolve_selector`, and returns the trace. This removes the bounding-box `max()` heuristic at `core.py:400` and makes the selection explainable + cardinality-guarded.

Direction → axis mapping:
`top→+z`, `bottom→-z`, `left→-x`, `right→+x`, `front→-y`, `back→+y`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_workflow.py  (append; use this module's existing primitives/client fixture)
def test_find_face_top_returns_face_and_trace(primitives):
    # `primitives` = the FusionPrimitives-style object wired to the mock bridge,
    # already constructed by this module's fixtures. Reuse the existing body-setup helper.
    body_token = _make_test_body(primitives)  # existing helper in this test module
    res = primitives.find_face({"body_token": body_token, "selector": "top"})
    assert res["ok"] is True
    assert res["face_token"].endswith(":face:top")
    assert res["selection_trace"]["status"] == "resolved"
    assert res["selection_trace"]["kind"] == "normal_axis"


def test_find_face_rejects_unknown_selector(primitives):
    body_token = _make_test_body(primitives)
    import pytest
    with pytest.raises(ValueError, match="selector must be one of"):
        primitives.find_face({"body_token": body_token, "selector": "diagonal"})
```

> Adjust the fixture/helper names (`primitives`, `_make_test_body`) to match what `tests/test_workflow.py` already provides. The token suffix assertion matches the mock face tokens.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_workflow.py -k find_face -v`
Expected: FAIL — `find_face` result has no `selection_trace` key yet.

- [ ] **Step 3: Replace the find_face body**

```python
# mcp_server/primitives/core.py  (replace lines 360-407)
    _DIRECTION_TO_AXIS = {
        "top": "+z", "bottom": "-z",
        "left": "-x", "right": "+x",
        "front": "-y", "back": "+y",
    }

    def find_face(self, payload: dict) -> dict:
        """Find a specific face on a body using a semantic selector.

        Resolution now happens add-in-side via the deterministic selector layer.
        The six directional selectors map to axis-normal descriptors.
        """
        body_token = payload.get("body_token")
        selector = payload.get("selector")
        if not body_token:
            raise ValueError("body_token is required.")
        if selector not in self._DIRECTION_TO_AXIS:
            raise ValueError("selector must be one of: top, bottom, left, right, front, back.")

        descriptor = {
            "target": "face",
            "kind": "normal_axis",
            "scope": {"body_token": body_token},
            "expect": "one",
            "params": {"axis": self._DIRECTION_TO_AXIS[selector]},
        }
        response = self._send("resolve_selector", descriptor)
        result = response.get("result", response)
        trace = result.get("selection_trace")

        if not result.get("ok"):
            raise ValueError(
                f"find_face could not resolve a single '{selector}' face: "
                f"{(trace or {}).get('reason', 'unknown')}"
            )

        tokens = result.get("tokens", [])
        return {
            "ok": True,
            "face_token": tokens[0],
            "selector": selector,
            "selection_trace": trace,
        }
```

> Confirm `self._send` returns the handler dict under a `"result"` key (as `get_body_faces` does at `core.py:347/378`). The `result = response.get("result", response)` line tolerates both shapes.

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_workflow.py -k find_face -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add mcp_server/primitives/core.py tests/test_workflow.py
git commit -m "refactor(find_face): route through deterministic selector layer with trace"
```

---

## Task 7: Full regression run

**Files:** none (verification only)

- [ ] **Step 1: Run the entire suite**

Run: `pytest -q`
Expected: PASS. If `find_face`'s changed return shape (now `selection_trace` instead of `face_info`) breaks a caller, find it:

Run: `grep -rn "face_info" mcp_server fusion_addin tests`
For each hit, update it to read `selection_trace` or `face_token`. Re-run `pytest -q`.

- [ ] **Step 2: Commit any caller fixes**

```bash
git add -A
git commit -m "fix(selectors): update find_face callers for new return shape"
```

---

## Task 8: Live smoke validation (requires Fusion 360)

**Files:** none (manual/live verification)

This is the only step needing a live Fusion session. It validates that add-in-side resolution works against real B-Rep, not just the mock.

- [ ] **Step 1: With Fusion running and the add-in loaded, run the smoke runner**

Run: `python scripts/fusion_smoke_test.py --workflow spacer`
Expected: workflow completes; any stage that calls `find_face` now returns a `selection_trace` with `status: resolved`.

- [ ] **Step 2: Spot-check a trace in the smoke output**

Confirm the emitted trace shows `kind: normal_axis`, the expected `candidate_count`, and `resolved_count: 1`. Capture the output in the dev log.

- [ ] **Step 3: Record evidence in the dev log**

Add a dated entry to `docs/dev-log.md` summarizing: selector layer landed, find_face retrofitted, mock + live registries wired, smoke result. Reference this plan file.

```bash
git add docs/dev-log.md
git commit -m "docs(dev-log): record selector foundations phase-1 landing + smoke evidence"
```

---

## Self-Review Notes

- **Spec coverage** (against `selector-foundations` SYNTHESIS "Recommended first implementation slice"): descriptor schema (Task 1) ✓; add-in-side resolution for body-scoped face/edge selectors (Tasks 4–5) ✓; cardinality + type guards before mutation (Task 3, fail-closed) ✓; minimal `SelectionTrace` (Task 2) ✓; traces emitted on failure + at find_face site (Tasks 4–6) ✓; instrument current opaque selector site `find_face` (Task 6) ✓.
- **Deliberately deferred to a follow-on plan** (still Phase 1, but out of this slice to keep it shippable): instrumenting `apply_chamfer`'s `"interior_bracket"` heuristic and `apply_fillet`/`apply_shell` edge selection; attribute pinning with post-mutation validity checks (descriptor already carries `pin`, unused). These depend on edge-loop selectors not in the v1 vocabulary and should follow once this slice is validated live.
- **Type consistency:** `validate_descriptor` → dict; `resolve(descriptor, faces, edges, operation)` → `(result, SelectionTrace)`; `SelectorAmbiguityError.trace` is a `SelectionTrace`; `SelectionTrace.to_dict()` is the only serialized form crossing the bridge. Names are consistent across Tasks 1–6.
- **Open verification points the implementer MUST confirm against the real files** (flagged inline): the exact body-setup helper in `tests/test_addin_workflows.py` and `tests/test_workflow.py`; the real `adapter_for`/`session_for` accessor names in the `get_body_faces` registration at `live_ops.py:~1880`; and whether `self._send` wraps results under `"result"`.
