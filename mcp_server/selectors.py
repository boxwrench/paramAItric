"""Pure selector module for ParamAItric.

Provides deterministic, unit-testable face/edge selection operating on plain
dicts — no Fusion API dependencies.

Three public surfaces:
  - validate_descriptor(raw) -> dict
  - SelectionTrace (dataclass)
  - resolve(descriptor, faces, edges, operation) -> (result, SelectionTrace)
  - SelectorAmbiguityError(ValueError)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FACE_KINDS: frozenset[str] = frozenset({"normal_axis", "largest_planar"})
_EDGE_KINDS: frozenset[str] = frozenset({"geometry_type", "longest"})
_ALL_KINDS: frozenset[str] = _FACE_KINDS | _EDGE_KINDS

_VALID_AXES: frozenset[str] = frozenset({"+x", "-x", "+y", "-y", "+z", "-z"})
_VALID_EDGE_TYPES: frozenset[str] = frozenset({"linear", "circular"})

_AXIS_VECTORS: dict[str, tuple[float, float, float]] = {
    "+x": (1.0, 0.0, 0.0),
    "-x": (-1.0, 0.0, 0.0),
    "+y": (0.0, 1.0, 0.0),
    "-y": (0.0, -1.0, 0.0),
    "+z": (0.0, 0.0, 1.0),
    "-z": (0.0, 0.0, -1.0),
}

_NORMAL_AXIS_DOT_THRESHOLD = 0.9
_AREA_TOLERANCE = 1e-6
_LENGTH_TOLERANCE = 1e-6


# ---------------------------------------------------------------------------
# Increment 1 — descriptor validation
# ---------------------------------------------------------------------------


def validate_descriptor(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a raw selector descriptor dict.

    Parameters
    ----------
    raw:
        Mapping with keys: target, kind, scope, expect (optional), params
        (optional), pin (optional).

    Returns
    -------
    Normalized dict with keys: target, kind, scope, expect, params, pin.

    Raises
    ------
    ValueError
        On any validation failure.
    """
    # --- target ---
    target = raw.get("target")
    if target not in ("face", "edge"):
        raise ValueError(f"target must be 'face' or 'edge', got {target!r}")

    # --- kind ---
    kind = raw.get("kind")
    if kind not in _ALL_KINDS:
        raise ValueError(f"Unknown kind {kind!r}; valid kinds are {sorted(_ALL_KINDS)}")

    # Check kind is valid for target
    if target == "face" and kind not in _FACE_KINDS:
        raise ValueError(
            f"kind {kind!r} is not valid for target 'face'; "
            f"face kinds are {sorted(_FACE_KINDS)}"
        )
    if target == "edge" and kind not in _EDGE_KINDS:
        raise ValueError(
            f"kind {kind!r} is not valid for target 'edge'; "
            f"edge kinds are {sorted(_EDGE_KINDS)}"
        )

    # --- scope ---
    scope = raw.get("scope", {})
    body_token = scope.get("body_token") if isinstance(scope, dict) else None
    if not body_token or not isinstance(body_token, str):
        raise ValueError("scope.body_token must be a non-empty string")

    # --- expect ---
    expect = raw.get("expect", "one")
    if expect not in ("one", "many"):
        raise ValueError(f"expect must be 'one' or 'many', got {expect!r}")

    # --- params ---
    params: dict[str, Any] = raw.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError("params must be a dict")

    _validate_params(kind, params)

    # --- pin ---
    pin = raw.get("pin", None)
    if pin is not None and (not isinstance(pin, str) or not pin):
        raise ValueError("pin must be a non-empty string or None")

    return {
        "target": target,
        "kind": kind,
        "scope": {"body_token": body_token},
        "expect": expect,
        "params": params,
        "pin": pin,
    }


def _validate_params(kind: str, params: dict[str, Any]) -> None:
    """Validate params dict for a given kind. Raises ValueError on failure."""
    if kind == "normal_axis":
        axis = params.get("axis")
        if axis not in _VALID_AXES:
            raise ValueError(
                f"params.axis must be one of {sorted(_VALID_AXES)}, got {axis!r}"
            )
    elif kind == "geometry_type":
        edge_type = params.get("type")
        if edge_type not in _VALID_EDGE_TYPES:
            raise ValueError(
                f"params.type must be one of {sorted(_VALID_EDGE_TYPES)}, got {edge_type!r}"
            )
    # largest_planar and longest take no required params — nothing to validate


# ---------------------------------------------------------------------------
# Increment 2 — SelectionTrace
# ---------------------------------------------------------------------------


@dataclass
class SelectionTrace:
    """Diagnostic artifact capturing how a selection was resolved.

    Not a verification gate — callers may inspect but should not branch on
    internal trace fields to implement business logic.
    """

    operation: str
    target: str
    kind: str
    params: dict[str, Any]
    expect: str
    status: str  # "resolved" | "ambiguous" | "empty" | "error"
    candidate_count: int
    resolved_count: int
    resolved_tokens: list[str]
    reason: str | None
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of all fields including trace_id."""
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


# ---------------------------------------------------------------------------
# Increment 3 — resolver with cardinality guards
# ---------------------------------------------------------------------------


class SelectorAmbiguityError(ValueError):
    """Raised when a selector cannot resolve to a definitive result.

    Attributes
    ----------
    trace:
        The SelectionTrace carrying status ("ambiguous" or "empty") and
        candidate_count at the time of failure.
    """

    def __init__(self, message: str, trace: SelectionTrace) -> None:
        super().__init__(message)
        self.trace = trace


def resolve(
    descriptor: dict[str, Any],
    faces: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    operation: str,
) -> tuple[dict[str, Any], SelectionTrace]:
    """Resolve a validated descriptor against face/edge pools.

    Parameters
    ----------
    descriptor:
        Output of validate_descriptor().
    faces:
        List of face dicts produced by the Fusion add-in.
    edges:
        List of edge dicts produced by the Fusion add-in.
    operation:
        Caller-supplied label for trace diagnostics (e.g. "find_face").

    Returns
    -------
    (result, trace) where result = {"tokens": [...], "entities": [...]}.

    Raises
    ------
    SelectorAmbiguityError
        When no candidates are found (status "empty") or when expect=="one"
        but multiple candidates exist (status "ambiguous").
    """
    target = descriptor["target"]
    kind = descriptor["kind"]
    params = descriptor["params"]
    expect = descriptor["expect"]
    # descriptor["pin"] is reserved for the Phase 2 attribute-pinning work and is
    # intentionally not consumed here yet (see NEXT_PHASE_PLAN Phase 1).

    pool = faces if target == "face" else edges
    candidates = _filter_and_rank(kind, params, pool)
    candidate_count = len(candidates)

    def _make_trace(status: str, resolved: list[dict[str, Any]], reason: str | None = None) -> SelectionTrace:
        tokens = [e["token"] for e in resolved]
        return SelectionTrace(
            operation=operation,
            target=target,
            kind=kind,
            params=params,
            expect=expect,
            status=status,
            candidate_count=candidate_count,
            resolved_count=len(resolved),
            resolved_tokens=tokens,
            reason=reason,
        )

    # --- empty ---
    if candidate_count == 0:
        trace = _make_trace("empty", [], reason=f"No candidates found for kind={kind!r} params={params!r}")
        raise SelectorAmbiguityError(
            f"No candidates found for kind={kind!r} params={params!r}",
            trace,
        )

    # --- expect many ---
    if expect == "many":
        trace = _make_trace("resolved", candidates)
        result = {"tokens": [e["token"] for e in candidates], "entities": candidates}
        return result, trace

    # --- expect one ---
    if candidate_count > 1:
        trace = _make_trace("ambiguous", candidates, reason=f"Ambiguous: {candidate_count} candidates for kind={kind!r} params={params!r}")
        raise SelectorAmbiguityError(
            f"Ambiguous: {candidate_count} candidates for kind={kind!r} params={params!r}",
            trace,
        )

    trace = _make_trace("resolved", candidates)
    result = {"tokens": [e["token"] for e in candidates], "entities": candidates}
    return result, trace


def _filter_and_rank(
    kind: str,
    params: dict[str, Any],
    pool: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return the subset of pool matching the kind+params selector."""
    if kind == "normal_axis":
        return _filter_normal_axis(params["axis"], pool)
    if kind == "largest_planar":
        return _filter_largest_planar(pool)
    if kind == "geometry_type":
        return _filter_geometry_type(params["type"], pool)
    if kind == "longest":
        return _filter_longest(pool)
    raise ValueError(f"Unhandled kind: {kind!r}")  # should be unreachable


def _dot(nv: dict[str, float], axis_vec: tuple[float, float, float]) -> float:
    return nv["x"] * axis_vec[0] + nv["y"] * axis_vec[1] + nv["z"] * axis_vec[2]


def _filter_normal_axis(
    axis: str,
    pool: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    axis_vec = _AXIS_VECTORS[axis]
    result = []
    for face in pool:
        nv = face.get("normal_vector")
        if nv is None:
            continue
        if _dot(nv, axis_vec) >= _NORMAL_AXIS_DOT_THRESHOLD:
            result.append(face)
    return result


def _filter_largest_planar(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    planar = [f for f in pool if f.get("type") == "planar"]
    if not planar:
        return []
    max_area = max(f["area_cm2"] for f in planar)
    return [f for f in planar if abs(f["area_cm2"] - max_area) <= _AREA_TOLERANCE]


def _filter_geometry_type(
    edge_type: str,
    pool: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [e for e in pool if e.get("type") == edge_type]


def _filter_longest(pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not pool:
        return []
    max_len = max(e["length_cm"] for e in pool)
    return [e for e in pool if abs(e["length_cm"] - max_len) <= _LENGTH_TOLERANCE]
