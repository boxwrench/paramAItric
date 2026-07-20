"""Geometry-equivalence comparison against a captured baseline.

``ROADMAP.md`` defines milestone acceptance as results being *geometry-equivalent*
to the Claude baseline — "bounding dimensions, body count, volume, features,
placement, and verification tier match within tolerance — not identical files or
topology IDs".

That distinction is the whole point of this module. Two runs of the same request
produce different entity tokens, different body names, different export paths and
possibly different stage ordering, and none of that is a difference that matters.
What matters is whether the engineering invariants agree. Everything here
compares the latter and deliberately ignores the former.

A case that is expected to fail safely has no geometry to compare; for those the
equivalent question is whether the same *kind* of structured failure occurred,
so the geometric invariants report ``NOT_APPLICABLE`` and the error shape is
compared instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path

from evaluations.cases.schema import Disposition, EvaluationCase

#: The seven invariants ROADMAP.md names, in the order it names them.
INVARIANTS: tuple[str, ...] = (
    "bounding_dimensions",
    "body_count",
    "volume",
    "features",
    "placement",
    "verification_tier",
    "export",
)

#: Verification keys that describe size, compared with the dimensional tolerance.
_DIMENSION_KEYS: tuple[str, ...] = (
    "actual_width_cm",
    "actual_height_cm",
    "actual_thickness_cm",
)

#: Verification keys consumed by other invariants, excluded from the feature set.
_NON_FEATURE_KEYS: frozenset[str] = frozenset(
    _DIMENSION_KEYS
    + (
        "expected_width_cm",
        "expected_height_cm",
        "expected_thickness_cm",
        "body_count",
        "sketch_count",
        "sketch_plane",
    )
)


class Verdict(str, Enum):
    """Outcome of comparing one invariant, or of a whole report."""

    MATCH = "match"
    MISMATCH = "mismatch"
    NO_BASELINE = "no_baseline"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class Tolerances:
    """How close counts as equal.

    Dimensions are absolute because CAD dimensions are authored in absolute
    units; volume is relative because volume error scales with part size, and a
    fixed cubic-centimetre budget would be far too tight for a large part and
    far too loose for a small one.
    """

    dimension_cm: float = 0.01
    volume_relative: float = 0.01


@dataclass(frozen=True)
class InvariantComparison:
    """The verdict for a single invariant, with a human-readable detail."""

    name: str
    verdict: Verdict
    detail: str


@dataclass
class ComparisonReport:
    """The result of comparing one run against one baseline."""

    case_id: str
    verdict: Verdict
    invariants: list[InvariantComparison] = field(default_factory=list)

    @property
    def mismatches(self) -> list[InvariantComparison]:
        """Return only the invariants that disagreed."""
        return [i for i in self.invariants if i.verdict is Verdict.MISMATCH]

    def to_dict(self) -> dict:
        """Return a JSON-serializable view of the report."""
        return {
            "case_id": self.case_id,
            "verdict": self.verdict.value,
            "invariants": [
                {"name": i.name, "verdict": i.verdict.value, "detail": i.detail}
                for i in self.invariants
            ],
        }


def _verification(result: dict) -> dict:
    return result.get("verification") or {}


def _body_volumes(result: dict) -> list[float]:
    """Return body volumes from the last snapshot that reports any.

    Reads the latest snapshot rather than a fixed stage index so that inserting
    or reordering stages does not change the answer.
    """
    volumes: list[float] = []
    for stage in result.get("stages") or []:
        bodies = (stage.get("snapshot") or {}).get("bodies_info") or []
        found = [b["volume_cm3"] for b in bodies if b.get("volume_cm3") is not None]
        if found:
            volumes = found
    return volumes


def _close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def _compare_bounding_dimensions(
    actual: dict, baseline: dict, tol: Tolerances
) -> InvariantComparison:
    a, b = _verification(actual), _verification(baseline)
    problems = []
    for key in _DIMENSION_KEYS:
        if key not in a and key not in b:
            continue
        av, bv = a.get(key), b.get(key)
        if av is None or bv is None:
            problems.append(f"{key}: {av} vs baseline {bv}")
        elif not _close(float(av), float(bv), tol.dimension_cm):
            problems.append(f"{key}: {av} vs baseline {bv}")
    if problems:
        return InvariantComparison(
            "bounding_dimensions", Verdict.MISMATCH, "; ".join(problems)
        )
    dims = ", ".join(f"{a[k]}" for k in _DIMENSION_KEYS if k in a)
    return InvariantComparison(
        "bounding_dimensions", Verdict.MATCH, dims or "no dimensions recorded"
    )


def _compare_body_count(actual: dict, baseline: dict, _tol: Tolerances) -> InvariantComparison:
    av = _verification(actual).get("body_count")
    bv = _verification(baseline).get("body_count")
    detail = f"{av} vs baseline {bv}"
    verdict = Verdict.MATCH if av == bv else Verdict.MISMATCH
    return InvariantComparison("body_count", verdict, detail)


def _compare_volume(actual: dict, baseline: dict, tol: Tolerances) -> InvariantComparison:
    av, bv = _body_volumes(actual), _body_volumes(baseline)
    if len(av) != len(bv):
        return InvariantComparison(
            "volume", Verdict.MISMATCH, f"{len(av)} bodies vs baseline {len(bv)}"
        )
    if not av:
        return InvariantComparison("volume", Verdict.MATCH, "no volumes recorded")
    problems = [
        f"{a} vs baseline {b}"
        for a, b in zip(sorted(av), sorted(bv))
        if not _close(a, b, abs(b) * tol.volume_relative)
    ]
    if problems:
        return InvariantComparison("volume", Verdict.MISMATCH, "; ".join(problems))
    return InvariantComparison("volume", Verdict.MATCH, f"{sorted(av)}")


def _feature_facts(result: dict) -> dict:
    facts = {
        key: value
        for key, value in _verification(result).items()
        if key not in _NON_FEATURE_KEYS
    }
    operation = (result.get("body") or {}).get("operation")
    if operation is not None:
        facts["operation"] = operation
    return facts


def _compare_features(actual: dict, baseline: dict, tol: Tolerances) -> InvariantComparison:
    a, b = _feature_facts(actual), _feature_facts(baseline)
    problems = []
    for key in sorted(set(a) | set(b)):
        av, bv = a.get(key), b.get(key)
        if key not in a or key not in b:
            problems.append(f"{key}: {av} vs baseline {bv}")
        elif isinstance(av, (int, float)) and isinstance(bv, (int, float)):
            if not _close(float(av), float(bv), tol.dimension_cm):
                problems.append(f"{key}: {av} vs baseline {bv}")
        elif av != bv:
            problems.append(f"{key}: {av!r} vs baseline {bv!r}")
    if problems:
        return InvariantComparison("features", Verdict.MISMATCH, "; ".join(problems))
    return InvariantComparison(
        "features", Verdict.MATCH, ", ".join(sorted(a)) or "no features recorded"
    )


def _placement_facts(result: dict) -> dict:
    return {
        "sketch_plane": _verification(result).get("sketch_plane"),
        "plane": (result.get("body") or {}).get("plane"),
    }


def _compare_placement(actual: dict, baseline: dict, _tol: Tolerances) -> InvariantComparison:
    a, b = _placement_facts(actual), _placement_facts(baseline)
    problems = [
        f"{key}: {a[key]!r} vs baseline {b[key]!r}" for key in a if a[key] != b[key]
    ]
    if problems:
        return InvariantComparison("placement", Verdict.MISMATCH, "; ".join(problems))
    return InvariantComparison(
        "placement", Verdict.MATCH, f"{a['sketch_plane'] or a['plane']}"
    )


def _verification_stages(result: dict) -> set[str]:
    """Return the names of completed verification stages."""
    return {
        stage.get("stage")
        for stage in result.get("stages") or []
        if str(stage.get("stage", "")).startswith("verify")
        and stage.get("status") == "completed"
    }


def _compare_verification_tier(
    actual: dict, baseline: dict, _tol: Tolerances
) -> InvariantComparison:
    a, b = _verification_stages(actual), _verification_stages(baseline)
    if a != b:
        return InvariantComparison(
            "verification_tier",
            Verdict.MISMATCH,
            f"{sorted(a)} vs baseline {sorted(b)}",
        )
    return InvariantComparison("verification_tier", Verdict.MATCH, f"{sorted(a)}")


def _export_extension(result: dict) -> str | None:
    path = (result.get("export") or {}).get("output_path")
    if not path:
        return None
    return Path(str(path).replace("\\", "/")).suffix.lower().lstrip(".") or None


def _compare_export(actual: dict, baseline: dict, _tol: Tolerances) -> InvariantComparison:
    """Compare export validity, never the path itself."""
    a, b = _export_extension(actual), _export_extension(baseline)
    if a != b:
        return InvariantComparison(
            "export", Verdict.MISMATCH, f"{a!r} vs baseline {b!r}"
        )
    return InvariantComparison("export", Verdict.MATCH, f"{a!r}")


_COMPARATORS = {
    "bounding_dimensions": _compare_bounding_dimensions,
    "body_count": _compare_body_count,
    "volume": _compare_volume,
    "features": _compare_features,
    "placement": _compare_placement,
    "verification_tier": _compare_verification_tier,
    "export": _compare_export,
}


def compare(
    actual: dict,
    baseline: dict,
    case: EvaluationCase,
    tolerances: Tolerances | None = None,
) -> ComparisonReport:
    """Compare one result against one baseline result for ``case``.

    Neither input is mutated.
    """
    tol = tolerances or Tolerances()

    if case.disposition is Disposition.FAIL_SAFELY:
        return _compare_failure(actual, baseline, case)

    invariants = [_COMPARATORS[name](actual, baseline, tol) for name in INVARIANTS]
    verdict = (
        Verdict.MISMATCH
        if any(i.verdict is Verdict.MISMATCH for i in invariants)
        else Verdict.MATCH
    )
    return ComparisonReport(case_id=case.id, verdict=verdict, invariants=invariants)


def _compare_failure(
    actual: dict, baseline: dict, case: EvaluationCase
) -> ComparisonReport:
    """Compare two fail-safely results by error shape, not geometry."""
    invariants = [
        InvariantComparison(name, Verdict.NOT_APPLICABLE, "case fails safely")
        for name in INVARIANTS
    ]

    problems = []
    if bool(actual.get("ok")) or bool(baseline.get("ok")):
        problems.append(f"ok: {actual.get('ok')!r} vs baseline {baseline.get('ok')!r}")
    if actual.get("classification") != baseline.get("classification"):
        problems.append(
            f"classification: {actual.get('classification')!r} vs "
            f"baseline {baseline.get('classification')!r}"
        )

    invariants.append(
        InvariantComparison(
            "failure_shape",
            Verdict.MISMATCH if problems else Verdict.MATCH,
            "; ".join(problems) or f"{actual.get('classification')!r}",
        )
    )
    verdict = Verdict.MISMATCH if problems else Verdict.MATCH
    return ComparisonReport(case_id=case.id, verdict=verdict, invariants=invariants)


def _default_expected_directory() -> Path:
    return Path(__file__).resolve().parents[1] / "expected" / "claude"


def compare_case(
    case: EvaluationCase,
    actual: dict,
    expected_directory: str | os.PathLike[str] | None = None,
    tolerances: Tolerances | None = None,
) -> ComparisonReport:
    """Compare ``actual`` against the captured baseline for ``case``.

    A case with no captured baseline yields an explicit ``NO_BASELINE`` verdict.
    It is never reported as a match — an uncaptured baseline is an open question,
    not a passing comparison.
    """
    base = (
        Path(expected_directory)
        if expected_directory is not None
        else _default_expected_directory()
    )
    path = base / f"{case.id}.json"
    if not path.exists():
        return ComparisonReport(
            case_id=case.id,
            verdict=Verdict.NO_BASELINE,
            invariants=[
                InvariantComparison(name, Verdict.NO_BASELINE, "no captured baseline")
                for name in INVARIANTS
            ],
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    return compare(actual, payload.get("actual_result") or {}, case, tolerances)


def compare_records(
    records,
    cases: list[EvaluationCase],
    expected_directory: str | os.PathLike[str] | None = None,
    tolerances: Tolerances | None = None,
) -> list[ComparisonReport]:
    """Compare a run's records against a captured baseline set.

    Returns one report per record, in record order. Records whose case has no
    captured baseline report ``NO_BASELINE`` rather than being dropped — the
    gap in coverage should be visible in the output, not silently absent.
    """
    by_id = {case.id: case for case in cases}
    reports: list[ComparisonReport] = []
    for record in records:
        case = by_id.get(record.case_id)
        if case is None:
            continue
        reports.append(
            compare_case(
                case,
                getattr(record, "actual_result", None) or {},
                expected_directory,
                tolerances,
            )
        )
    return reports
