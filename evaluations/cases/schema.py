"""Frozen dataclasses and enums describing evaluation cases.

An evaluation case is a declarative record of a single request that the harness
replays against the MCP tool server. Cases are stored as JSON files in this
directory and loaded via :func:`load_cases`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path


class Tier(str, Enum):
    """Which regression tier a case belongs to."""

    CONTRACT = "contract"
    LIVE_FUSION = "live_fusion"
    SAFETY = "safety"


class Disposition(str, Enum):
    """Whether a case is expected to succeed or to fail safely.

    This encodes the succeed-or-fail-safely flag: a well-formed request should
    ``SUCCEED``, while an unsafe or impossible request should ``FAIL_SAFELY``
    (return a structured error rather than crashing or producing bad geometry).
    """

    SUCCEED = "succeed"
    FAIL_SAFELY = "fail_safely"


@dataclass(frozen=True)
class EvaluationCase:
    """A single, self-contained regression case.

    The fields capture everything the roadmap asks a case to record: the
    original natural-language request, the workflow and tool it should map to,
    the measurements a correct host must extract, the arguments the runner
    actually passes, the contract for how a correct host should normalize the
    request, the geometric facts to verify, and the target error shape for
    safety cases.
    """

    id: str
    tier: Tier
    disposition: Disposition
    original_request: str
    expected_workflow: str
    required_measurements: tuple[str, ...]
    expected_tool_call: str
    arguments: dict
    expected_normalized_arguments: dict
    expected_verification_facts: dict
    expected_export_type: str | None
    expected_error: dict | None
    bridge: str = "mock"
    notes: str = ""
    baseline_required: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "EvaluationCase":
        """Build a case from a decoded JSON object, coercing enum/tuple fields."""
        return cls(
            id=d["id"],
            tier=Tier(d["tier"]),
            disposition=Disposition(d["disposition"]),
            original_request=d["original_request"],
            expected_workflow=d["expected_workflow"],
            required_measurements=tuple(d.get("required_measurements", ())),
            expected_tool_call=d["expected_tool_call"],
            arguments=dict(d.get("arguments", {})),
            expected_normalized_arguments=dict(d.get("expected_normalized_arguments", {})),
            expected_verification_facts=dict(d.get("expected_verification_facts", {})),
            expected_export_type=d.get("expected_export_type"),
            expected_error=d.get("expected_error"),
            bridge=d.get("bridge", "mock"),
            notes=d.get("notes", ""),
            baseline_required=bool(d.get("baseline_required", False)),
        )


def _cases_directory() -> Path:
    """Return the directory holding the JSON case files."""
    return Path(__file__).resolve().parent


def load_cases(directory: str | os.PathLike[str] | None = None) -> list[EvaluationCase]:
    """Load every ``*.json`` case file from ``directory`` sorted by id."""
    base = Path(directory) if directory is not None else _cases_directory()
    cases: list[EvaluationCase] = []
    for path in sorted(base.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        cases.append(EvaluationCase.from_dict(payload))
    return sorted(cases, key=lambda case: case.id)
