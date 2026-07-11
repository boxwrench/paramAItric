"""CLI entry point: ``python -m evaluations.runner``.

Runs every evaluation case, prints a one-line-per-case summary plus totals, and
exits non-zero if any case failed. Skipped cases do not cause a non-zero exit.
"""

from __future__ import annotations

import sys

from evaluations.runner.runner import run_all


def main() -> int:
    """Run all cases, print a summary table, and return the process exit code."""
    records = run_all()

    header = f"{'id':<32} {'tier':<12} {'status':<8} gaps"
    print(header)
    print("-" * len(header))
    for record in records:
        gaps = ",".join(record.normalization_gaps) if record.normalization_gaps else "-"
        print(f"{record.case_id:<32} {record.tier:<12} {record.status:<8} {gaps}")

    passed = sum(1 for r in records if r.status == "pass")
    failed = sum(1 for r in records if r.status == "fail")
    skipped = sum(1 for r in records if r.status == "skipped")
    contract = sum(1 for r in records if r.tier == "contract")
    safety = sum(1 for r in records if r.tier == "safety")
    live = sum(1 for r in records if r.tier == "live_fusion")

    print("-" * len(header))
    print(
        f"total={len(records)} pass={passed} fail={failed} skipped={skipped} "
        f"| contract={contract} safety={safety} live={live}"
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
