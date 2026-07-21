"""Backend-neutral internal operation vocabulary.

A workflow's geometric intent, expressed above the sketch/extrude primitives and
below any specific CAD backend. This is the minimal vocabulary the future CAD
backend protocol (Fusion today, FreeCAD later) must speak, so nothing here names
a backend, an entity token, or a Fusion concept.

The four operations are add / cut / intersect / new_body; each carries a target,
a placement, and a machine-checkable ``ExpectedDelta`` stating what the operation
should change. The delta vocabulary aligns with the freeform layer's existing
commit-verification signals (body-count delta, volume direction, feature
presence) so the two describe geometry the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

_VALID_PLANES: frozenset[str] = frozenset({"xy", "xz", "yz"})
_VALID_PROFILES: frozenset[str] = frozenset({"rectangle", "circle"})


class VolumeDelta(str, Enum):
    """Direction a solid's total volume should move under an operation."""

    INCREASE = "increase"
    DECREASE = "decrease"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class ExpectedDelta:
    """What an operation declares it will change, checkable against a real run.

    Same shape as the roadmap's verification invariants: a body-count delta, a
    volume direction, and the features that must be present afterward. ``check``
    reports one failure string per violated invariant (empty list == agreement),
    so a caller sees exactly which invariant an operation broke.
    """

    body_count_delta: int
    volume: VolumeDelta
    features_present: tuple[str, ...] = ()

    def check(
        self,
        *,
        body_count_delta: int,
        volume: VolumeDelta,
        features: Iterable[str],
    ) -> list[str]:
        """Return one failure message per violated invariant; empty == agreement."""
        failures: list[str] = []
        if body_count_delta != self.body_count_delta:
            failures.append(
                f"body_count_delta: expected {self.body_count_delta}, observed {body_count_delta}"
            )
        if volume != self.volume:
            failures.append(
                f"volume: expected {self.volume.value}, observed {volume.value}"
            )
        observed = set(features)
        for feature in self.features_present:
            if feature not in observed:
                failures.append(f"feature missing: {feature!r}")
        return failures


class OperationMode(str, Enum):
    """The four body-level operations a backend must speak."""

    NEW_BODY = "new_body"
    CUT = "cut"
    ADD = "add"
    INTERSECT = "intersect"


@dataclass(frozen=True)
class Placement:
    """Backend-neutral placement: a construction plane and an optional offset.

    Planes (xy / xz / yz) and offsets are universal CAD concepts, not Fusion
    ones — no face token or feature id appears here.
    """

    plane: str
    offset_cm: float = 0.0

    def __post_init__(self) -> None:
        if self.plane not in _VALID_PLANES:
            raise ValueError(
                f"plane must be one of {sorted(_VALID_PLANES)}, got {self.plane!r}"
            )


@dataclass(frozen=True)
class Target:
    """Backend-neutral geometry an operation produces or applies.

    A named profile (rectangle / circle), its positive dimensions, and a positive
    extent (extrusion depth). Enough to describe a prism or a cylindrical tool
    without naming a backend, an entity token, or a sketch/feature id.
    """

    profile: str
    dimensions_cm: dict[str, float]
    extent_cm: float

    def __post_init__(self) -> None:
        if self.profile not in _VALID_PROFILES:
            raise ValueError(
                f"profile must be one of {sorted(_VALID_PROFILES)}, got {self.profile!r}"
            )
        for name, value in self.dimensions_cm.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"dimension {name!r} must be a positive number, got {value!r}")
        if not isinstance(self.extent_cm, (int, float)) or isinstance(self.extent_cm, bool) or self.extent_cm <= 0:
            raise ValueError(f"extent_cm must be a positive number, got {self.extent_cm!r}")


@dataclass(frozen=True)
class Operation:
    """One body-level operation: what to do, to what, where, and what changes."""

    mode: OperationMode
    target: Target
    placement: Placement
    expected_delta: ExpectedDelta

    def __post_init__(self) -> None:
        if not isinstance(self.mode, OperationMode):
            raise ValueError(f"mode must be an OperationMode, got {self.mode!r}")
