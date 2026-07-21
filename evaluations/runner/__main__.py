"""CLI entry point: ``python -m evaluations.runner``.

Runs every evaluation case, prints a one-line-per-case summary plus totals, and
exits non-zero if any case failed. Skipped cases do not cause a non-zero exit.

With ``--compare-to <name>`` it additionally compares each result against the
captured baselines in ``evaluations/expected/<name>/`` and reports per-invariant
geometry equivalence. A case with no captured baseline reports ``no_baseline``
and does not fail the run; a genuine mismatch does.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from evaluations.cases.schema import load_cases
from evaluations.runner.comparison import Verdict, compare_records
from evaluations.runner.runner import run_all


def _default_expected_root() -> Path:
    """Return ``evaluations/expected``, the parent of every baseline set."""
    return Path(__file__).resolve().parents[1] / "expected"


def _print_run_summary(records) -> tuple[int, str]:
    """Print the per-case table and totals. Returns (failed count, separator)."""
    header = f"{'id':<32} {'tier':<12} {'status':<8} gaps"
    print(header)
    separator = "-" * len(header)
    print(separator)
    for record in records:
        gaps = ",".join(record.normalization_gaps) if record.normalization_gaps else "-"
        print(f"{record.case_id:<32} {record.tier:<12} {record.status:<8} {gaps}")

    passed = sum(1 for r in records if r.status == "pass")
    failed = sum(1 for r in records if r.status == "fail")
    skipped = sum(1 for r in records if r.status == "skipped")
    contract = sum(1 for r in records if r.tier == "contract")
    safety = sum(1 for r in records if r.tier == "safety")
    live = sum(1 for r in records if r.tier == "live_fusion")

    print(separator)
    print(
        f"total={len(records)} pass={passed} fail={failed} skipped={skipped} "
        f"| contract={contract} safety={safety} live={live}"
    )
    return failed, separator


def _print_comparison(records, baseline_name: str, expected_root: Path, separator: str) -> int:
    """Print the comparison report. Returns the number of mismatching cases."""
    reports = compare_records(records, load_cases(), expected_root / baseline_name)

    print()
    print(f"comparison vs '{baseline_name}' baseline")
    print(separator)
    for report in reports:
        print(f"{report.case_id:<32} {report.verdict.value}")
        for invariant in report.mismatches:
            print(f"{'':<32}   {invariant.name}: {invariant.detail}")

    matched = sum(1 for r in reports if r.verdict is Verdict.MATCH)
    mismatched = sum(1 for r in reports if r.verdict is Verdict.MISMATCH)
    no_baseline = sum(1 for r in reports if r.verdict is Verdict.NO_BASELINE)

    print(separator)
    print(
        f"compared={matched + mismatched} match={matched} "
        f"mismatch={mismatched} no_baseline={no_baseline}"
    )
    if no_baseline:
        print(
            f"{no_baseline} case(s) have no captured baseline — "
            "see `python -m evaluations.baseline --status`."
        )
    return mismatched


def main(argv: list[str] | None = None, expected_root: Path | None = None) -> int:
    """Run all cases, print summaries, and return the process exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m evaluations.runner",
        description="Run the evaluation cases and optionally compare to a baseline.",
    )
    parser.add_argument(
        "--compare-to",
        metavar="NAME",
        help="compare results against evaluations/expected/NAME/ (e.g. 'claude')",
    )
    args = parser.parse_args(argv)

    records = run_all()
    failed, separator = _print_run_summary(records)

    mismatched = 0
    if args.compare_to:
        root = expected_root if expected_root is not None else _default_expected_root()
        mismatched = _print_comparison(records, args.compare_to, root, separator)

    return 0 if failed == 0 and mismatched == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
