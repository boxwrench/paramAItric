"""Baseline capture driver: checklists in, validation out.

Hand-captured Claude baselines live in ``evaluations/expected/claude/``. They
cannot be scripted — Claude drives Fusion interactively, so a human has to run
each case and record what actually happened (see ``BASELINE_CAPTURE.md``).

This module does the two things that *can* be automated around that manual step:

* :func:`render_checklist` turns a case into a capture checklist, derived from
  the case file itself so a checklist can never drift from the case it describes.
* :func:`validate_baseline` rejects a baseline that is malformed, missing
  reproducibility metadata, or inconsistent with its case — so a bad capture is
  caught here rather than silently poisoning every later comparison.

Nothing in this module writes to ``expected/``. Producing baseline *content* is
a human act, by design.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field, fields
import json
import os
from pathlib import Path

from evaluations.cases.schema import EvaluationCase, load_cases
from evaluations.runner.metadata import ReproducibilityMetadata

#: Top-level keys every hand-captured baseline must carry. Mirrors the shape of
#: ``ResultsRecord`` plus the capture-specific fields a live run adds.
REQUIRED_BASELINE_FIELDS: tuple[str, ...] = (
    "metadata",
    "case_id",
    "tier",
    "disposition",
    "status",
    "timestamp",
    "claude_tool_call",
    "claude_arguments",
    "actual_result",
    "assertions",
    "normalization_gaps",
    "capture_method",
)

#: Metadata keys required inside the ``metadata`` object. Derived from the
#: dataclass so the two cannot drift.
REQUIRED_METADATA_FIELDS: tuple[str, ...] = tuple(
    f.name for f in fields(ReproducibilityMetadata)
)


def _default_expected_directory() -> Path:
    """Return the canonical home of hand-captured Claude baselines."""
    return Path(__file__).resolve().parent / "expected" / "claude"


def missing_baselines(
    cases: list[EvaluationCase],
    expected_directory: str | os.PathLike[str] | None = None,
) -> list[EvaluationCase]:
    """Return the cases that have no captured baseline yet, in case order."""
    base = (
        Path(expected_directory)
        if expected_directory is not None
        else _default_expected_directory()
    )
    return [case for case in cases if not (base / f"{case.id}.json").exists()]


def render_checklist(case: EvaluationCase) -> str:
    """Render a Markdown capture checklist for one case.

    Every value comes from ``case``; nothing is hand-duplicated here. Editing a
    case file changes its checklist on the next render.
    """
    measurements = "\n".join(
        f"   - [ ] `{name}`" for name in case.required_measurements
    ) or "   - [ ] (none recorded on this case)"

    required_fields = "\n".join(f"- `{name}`" for name in REQUIRED_BASELINE_FIELDS)
    metadata_fields = "\n".join(f"- `{name}`" for name in REQUIRED_METADATA_FIELDS)

    disposition_note = (
        "This case must **succeed**. Record the geometry and the export path."
        if case.disposition.value == "succeed"
        else "This case must **fail safely**. Record the structured error. "
        "No geometry should be produced and nothing should be exported."
    )

    return f"""# Capture checklist — `{case.id}`

> Generated from `evaluations/cases/{case.id}.json`. Do not edit by hand —
> edit the case and regenerate.

| | |
|---|---|
| Tier | `{case.tier.value}` |
| Disposition | `{case.disposition.value}` |
| Expected workflow | `{case.expected_workflow}` |
| Expected tool call | `{case.expected_tool_call}` |
| Bridge | `{case.bridge}` |
| Baseline required | {"yes — representative part" if case.baseline_required else "no"} |

## 1. Preconditions

- [ ] Fusion 360 open with an empty document
- [ ] `FusionAIBridge` add-in running
- [ ] Claude Desktop connected to the paramAItric MCP server
- [ ] Health check reports `mode: "live"` — a baseline captured against mock is worthless

## 2. The request

Give Claude exactly this, verbatim:

> {case.original_request}

{disposition_note}

## 3. Measurements Claude must extract

{measurements}

## 4. Record the result

Save to `evaluations/expected/claude/{case.id}.json` with these top-level fields:

{required_fields}

The `metadata` object requires:

{metadata_fields}

## 5. Before you commit

- [ ] `python -m evaluations.baseline --validate` passes
- [ ] Every number came from what Fusion actually returned

**Do not invent baseline numbers.** If the run disagrees with what this case
predicts, record the real behavior and flag the mismatch — that discrepancy is
the signal this harness exists to catch.
"""


@dataclass
class ValidationResult:
    """Outcome of validating a single baseline file."""

    case_id: str
    ok: bool
    problems: list[str] = field(default_factory=list)


def _metadata_problems(metadata: object, case: EvaluationCase) -> list[str]:
    """Return every problem found in a baseline's ``metadata`` object."""
    if not isinstance(metadata, dict):
        return ["metadata must be a JSON object"]

    problems = [
        f"metadata is missing required field: {name}"
        for name in REQUIRED_METADATA_FIELDS
        if name not in metadata
    ]
    declared = metadata.get("evaluation_case")
    if declared is not None and declared != case.id:
        problems.append(
            f"metadata.evaluation_case is {declared!r}, expected {case.id!r}"
        )
    return problems


def validate_baseline(payload: dict, case: EvaluationCase) -> ValidationResult:
    """Check one decoded baseline against the case it claims to cover.

    Catches three classes of bad capture: absent top-level fields, absent or
    malformed reproducibility metadata, and disagreement with the case itself.
    All problems are collected — a caller fixing a baseline should see the whole
    list at once rather than rediscovering it one run at a time.
    """
    problems = [
        f"missing required field: {name}"
        for name in REQUIRED_BASELINE_FIELDS
        if name not in payload
    ]

    if "metadata" in payload:
        problems.extend(_metadata_problems(payload["metadata"], case))

    for name, expected in (
        ("case_id", case.id),
        ("tier", case.tier.value),
        ("disposition", case.disposition.value),
    ):
        if name in payload and payload[name] != expected:
            problems.append(f"{name} is {payload[name]!r}, expected {expected!r}")

    return ValidationResult(case_id=case.id, ok=not problems, problems=problems)


def validate_directory(
    cases: list[EvaluationCase],
    expected_directory: str | os.PathLike[str] | None = None,
) -> list[ValidationResult]:
    """Validate every baseline that exists for ``cases``.

    Cases without a captured baseline are skipped, not failed — an absent
    baseline is tracked by :func:`missing_baselines`, which is a different
    question from a bad one.
    """
    base = (
        Path(expected_directory)
        if expected_directory is not None
        else _default_expected_directory()
    )

    results: list[ValidationResult] = []
    for case in cases:
        path = base / f"{case.id}.json"
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            results.append(ValidationResult(case.id, False, [f"invalid JSON: {exc}"]))
            continue
        results.append(validate_baseline(payload, case))
    return results


def write_checklists(
    cases: list[EvaluationCase],
    output_directory: str | os.PathLike[str],
) -> list[Path]:
    """Write one Markdown checklist per case and return the paths written.

    Refuses to write anywhere under an ``expected`` directory. This tool exists
    to help a human produce baselines; authoring baseline content itself is not
    something it is permitted to do, and a structural guard is more reliable
    than a comment saying so.
    """
    target = Path(output_directory)
    if any(part == "expected" for part in target.resolve().parts):
        raise ValueError(
            f"refusing to write checklists into an 'expected' directory: {target}. "
            "Baseline content is captured by hand, never generated."
        )

    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for case in cases:
        path = target / f"{case.id}.md"
        path.write_text(render_checklist(case), encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m evaluations.baseline",
        description=(
            "Baseline capture driver. Reports which cases still need a "
            "hand-captured Claude baseline, generates per-case capture "
            "checklists, and validates the baselines that exist. Never writes "
            "baseline content."
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--status", action="store_true", help="report baseline coverage and exit"
    )
    group.add_argument(
        "--validate",
        action="store_true",
        help="validate every captured baseline; non-zero exit if any is bad",
    )
    group.add_argument(
        "--write-checklists",
        metavar="DIR",
        help="write a capture checklist for every case still missing a baseline",
    )
    args = parser.parse_args(argv)

    cases = load_cases()
    missing = missing_baselines(cases)

    if args.status:
        required = [case for case in cases if case.baseline_required]
        required_missing = [case for case in missing if case.baseline_required]
        print(f"cases:                {len(cases)}")
        print(f"baselines captured:   {len(cases) - len(missing)}")
        print(f"awaiting capture:     {len(missing)}")
        print(
            f"representative parts: {len(required)} "
            f"({len(required_missing)} still awaiting capture)"
        )
        for case in missing:
            mark = "*" if case.baseline_required else " "
            print(f"  {mark} {case.id}")
        print("\n* = representative part (ROADMAP.md tier 2)")
        return 0

    if args.validate:
        results = validate_directory(cases)
        failures = [result for result in results if not result.ok]
        for result in failures:
            print(f"FAIL {result.case_id}")
            for problem in result.problems:
                print(f"       {problem}")
        print(f"{len(results) - len(failures)}/{len(results)} baselines valid")
        return 1 if failures else 0

    written = write_checklists(missing, args.write_checklists)
    for path in written:
        print(f"wrote {path}")
    print(f"\n{len(written)} checklist(s) written to {args.write_checklists}")
    print("Capture is manual — see evaluations/BASELINE_CAPTURE.md.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
