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

import math
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
