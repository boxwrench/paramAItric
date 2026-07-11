"""Normalize user-selected workflow units to the server's centimeter contract."""
from __future__ import annotations


def normalize_workflow_units(payload: dict) -> dict:
    factors = {"cm": 1.0, "mm": 0.1, "in": 2.54}
    units = payload.get("units", "cm")
    if units not in factors:
        raise ValueError("units must be one of: cm, mm, in.")
    normalized = dict(payload)
    normalized.pop("units", None)
    for name, value in tuple(normalized.items()):
        if name.endswith("_cm") and isinstance(value, (int, float)) and not isinstance(value, bool):
            normalized[name] = float(value) * factors[units]
    return normalized
