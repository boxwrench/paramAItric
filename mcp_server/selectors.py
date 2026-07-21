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
_EDGE_KINDS: frozenset[str] = frozenset(
    {"geometry_type", "longest", "axis_parallel", "max_face_perimeter"}
)
_ALL_KINDS: frozenset[str] = _FACE_KINDS | _EDGE_KINDS

_VALID_AXES: frozenset[str] = frozenset({"+x", "-x", "+y", "-y", "+z", "-z"})
_VALID_EDGE_TYPES: frozenset[str] = frozenset({"linear", "circular"})
_VALID_CARTESIAN_AXES: frozenset[str] = frozenset({"x", "y", "z"})

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
_POSITION_TOLERANCE = 1e-9
# Tolerance for matching a pin's recorded numeric attributes against a
# candidate's — absorbs benign float recompute noise without matching a
# genuinely different face.
_PIN_ATTR_TOLERANCE = 1e-6


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
    # A pin is a recorded-attribute record (see docs/STABLE_REFERENCE_POLICY.md),
    # not an entity token. The old bookmark-by-string form is intentionally rejected.
    pin = raw.get("pin", None)
    if pin is not None and not isinstance(pin, dict):
        raise ValueError("pin must be an attribute record (dict) or None")

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
    elif kind in {"axis_parallel", "max_face_perimeter"}:
        axis = params.get("axis")
        if axis not in _VALID_CARTESIAN_AXES:
            raise ValueError(
                f"params.axis must be one of {sorted(_VALID_CARTESIAN_AXES)}, got {axis!r}"
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
    # "resolved" | "ambiguous" | "empty" | "error" | "pin_stale" | "pin_ambiguous"
    status: str
    candidate_count: int
    resolved_count: int
    resolved_tokens: list[str]
    reason: str | None
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    # Pin visibility (all defaulted; a semantic resolve leaves these untouched).
    pin_present: bool = False
    pin_resolved: bool | None = None
    pin_attributes: dict[str, Any] | None = None
    next_step: str | None = None

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
            "pin_present": self.pin_present,
            "pin_resolved": self.pin_resolved,
            "pin_attributes": self.pin_attributes,
            "next_step": self.next_step,
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

    pool = faces if target == "face" else edges

    # A pin, if present, is a strict opt-in assertion of stability. It is matched
    # by recorded attributes, never re-resolved semantically — so there is no
    # fallback from the pin path to the semantic path (see
    # docs/STABLE_REFERENCE_POLICY.md).
    pin = descriptor.get("pin")
    if pin is not None:
        return _resolve_pinned(descriptor, pin, pool, operation)

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
    if kind == "axis_parallel":
        return _filter_axis_parallel(params["axis"], pool)
    if kind == "max_face_perimeter":
        return _filter_max_face_perimeter(params["axis"], pool)
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


def _edge_endpoints(edge: dict[str, Any]) -> tuple[dict[str, float], dict[str, float]] | None:
    start = edge.get("start_point")
    end = edge.get("end_point")
    if not isinstance(start, dict) or not isinstance(end, dict):
        return None
    if any(axis not in start or axis not in end for axis in _VALID_CARTESIAN_AXES):
        return None
    return start, end


def _edge_parallel_to_axis(edge: dict[str, Any], axis: str) -> bool:
    endpoints = _edge_endpoints(edge)
    if edge.get("type") != "linear" or endpoints is None:
        return False
    start, end = endpoints
    cross_axes = sorted(_VALID_CARTESIAN_AXES - {axis})
    return (
        abs(float(end[axis]) - float(start[axis])) > _POSITION_TOLERANCE
        and all(
            abs(float(end[cross_axis]) - float(start[cross_axis]))
            <= _POSITION_TOLERANCE
            for cross_axis in cross_axes
        )
    )


def _filter_axis_parallel(axis: str, pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [edge for edge in pool if _edge_parallel_to_axis(edge, axis)]


def _axis_bounds(pool: list[dict[str, Any]]) -> dict[str, tuple[float, float]] | None:
    points: list[dict[str, float]] = []
    for edge in pool:
        endpoints = _edge_endpoints(edge)
        if endpoints is not None:
            points.extend(endpoints)
    if not points:
        return None
    return {
        axis: (
            min(float(point[axis]) for point in points),
            max(float(point[axis]) for point in points),
        )
        for axis in _VALID_CARTESIAN_AXES
    }


# ---------------------------------------------------------------------------
# Increment 4 — attribute pinning (G5)
# ---------------------------------------------------------------------------
#
# A pin is an opt-in assertion that a specific piece of geometry is still
# present (docs/STABLE_REFERENCE_POLICY.md). It records the *intrinsic,
# shape-defining* attributes of a resolved entity at selection time, and
# re-resolves later by matching those attributes against the candidate pool —
# never by entity token, which would be bookmarking by identity. create_pin()
# and the matcher both derive from _pin_attributes(), so the recorded set and
# the matched set cannot drift apart.


def _pin_attributes(target: str, entity: dict[str, Any]) -> dict[str, Any]:
    """Return the distinguishing attributes that identify an entity for pinning.

    This is the heart of the pinning policy. The returned attributes are what a
    pin is matched on later, so the choice determines pin behavior:

      - Record too FEW attributes  -> unrelated faces/edges also match -> the
        pin spuriously reports ``pin_ambiguous``.
      - Record POSITIONAL attributes (absolute coordinates, endpoints) -> a
        benign move elsewhere shifts them -> the pin spuriously goes
        ``pin_stale``. A pin must survive topology changes unrelated to the
        pinned geometry itself.
      - NEVER record ``entity["token"]`` -> that is identity/bookmarking, which
        the policy rejects.

    Intrinsic, shape-defining attributes are the sweet spot — the same ones the
    selector filters already rank on:
      - face: ``type``, ``normal_vector``, ``area_cm2``
      - edge: ``type``, ``length_cm``

    Parameters
    ----------
    target:
        "face" or "edge".
    entity:
        A single face or edge dict from the add-in (same shape the filters see).

    Returns
    -------
    A dict of the recorded attributes. Must be non-empty and must not contain
    the entity token.
    """
    if target == "face":
        return {
            "type": entity.get("type"),
            "normal_vector": entity.get("normal_vector"),
            "area_cm2": entity.get("area_cm2"),
        }
    return {
        "type": entity.get("type"),
        "length_cm": entity.get("length_cm"),
    }


def create_pin(target: str, entity: dict[str, Any]) -> dict[str, Any]:
    """Create a pin from a resolved selection entity.

    The envelope is fixed; the substance comes from _pin_attributes(). Later,
    resolve() with this pin present matches candidates whose _pin_attributes()
    equal these recorded ones.
    """
    return {"target": target, "attributes": _pin_attributes(target, entity)}


def _value_match(recorded: Any, candidate: Any) -> bool:
    """Compare two recorded-attribute values, with float tolerance for numbers."""
    if isinstance(recorded, dict) and isinstance(candidate, dict):
        return _attrs_match(recorded, candidate)
    recorded_num = isinstance(recorded, (int, float)) and not isinstance(recorded, bool)
    candidate_num = isinstance(candidate, (int, float)) and not isinstance(candidate, bool)
    if recorded_num and candidate_num:
        return abs(float(recorded) - float(candidate)) <= _PIN_ATTR_TOLERANCE
    return recorded == candidate


def _attrs_match(recorded: dict[str, Any], candidate: dict[str, Any]) -> bool:
    """True when every recorded attribute matches the candidate's, key for key."""
    if set(recorded.keys()) != set(candidate.keys()):
        return False
    return all(_value_match(recorded[k], candidate[k]) for k in recorded)


def _match_pin(pin: dict[str, Any], pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return every candidate whose attributes match the pin's recorded ones."""
    target = pin.get("target")
    wanted = pin.get("attributes") or {}
    return [e for e in pool if _attrs_match(wanted, _pin_attributes(target, e))]


def _resolve_pinned(
    descriptor: dict[str, Any],
    pin: dict[str, Any],
    pool: list[dict[str, Any]],
    operation: str,
) -> tuple[dict[str, Any], SelectionTrace]:
    """Resolve a descriptor that carries a pin, strictly by recorded attributes.

    Cardinality of the match decides the outcome, with no semantic fallback:
      0  -> pin_stale (hard-fail), 1 -> resolved, >1 -> pin_ambiguous.
    """
    target = descriptor["target"]
    matches = _match_pin(pin, pool)
    count = len(matches)
    attrs = pin.get("attributes")

    def _trace(status: str, resolved: list[dict[str, Any]], reason: str | None,
               next_step: str | None) -> SelectionTrace:
        return SelectionTrace(
            operation=operation,
            target=target,
            kind=descriptor["kind"],
            params=descriptor["params"],
            expect=descriptor["expect"],
            status=status,
            candidate_count=count,
            resolved_count=len(resolved),
            resolved_tokens=[e["token"] for e in resolved],
            reason=reason,
            pin_present=True,
            pin_resolved=(status == "resolved"),
            pin_attributes=attrs,
            next_step=next_step,
        )

    if count == 0:
        trace = _trace(
            "pin_stale", [],
            reason=f"Pinned {target} not found: recorded attributes {attrs!r} match no candidate.",
            next_step="The pinned geometry is gone. Re-select the target explicitly.",
        )
        raise SelectorAmbiguityError(
            f"Pinned {target} is stale: recorded geometry not found.", trace
        )

    if count > 1:
        trace = _trace(
            "pin_ambiguous", matches,
            reason=f"Pinned {target} matches {count} candidates: the model changed under the pin.",
            next_step="A topology change duplicated the pinned geometry. Re-select explicitly.",
        )
        raise SelectorAmbiguityError(
            f"Pinned {target} is ambiguous: {count} candidates match.", trace
        )

    trace = _trace("resolved", matches, reason=None, next_step=None)
    return {"tokens": [e["token"] for e in matches], "entities": matches}, trace


def _filter_max_face_perimeter(
    normal_axis: str,
    pool: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return linear perimeter edges on the body's maximum face for an axis."""
    bounds = _axis_bounds(pool)
    if bounds is None:
        return []

    max_value = bounds[normal_axis][1]
    face_axes = sorted(_VALID_CARTESIAN_AXES - {normal_axis})
    result: list[dict[str, Any]] = []
    for edge in pool:
        endpoints = _edge_endpoints(edge)
        if endpoints is None or edge.get("type") != "linear":
            continue
        start, end = endpoints
        if not (
            abs(float(start[normal_axis]) - max_value) <= _POSITION_TOLERANCE
            and abs(float(end[normal_axis]) - max_value) <= _POSITION_TOLERANCE
        ):
            continue

        for edge_axis in face_axes:
            other_axis = face_axes[1] if edge_axis == face_axes[0] else face_axes[0]
            if not _edge_parallel_to_axis(edge, edge_axis):
                continue
            other_min, other_max = bounds[other_axis]
            coordinate = float(start[other_axis])
            if (
                abs(coordinate - other_min) <= _POSITION_TOLERANCE
                or abs(coordinate - other_max) <= _POSITION_TOLERANCE
            ):
                result.append(edge)
                break
    return result
