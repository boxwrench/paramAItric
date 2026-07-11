"""Evaluation runner package.

Exposes the reproducibility metadata records and the case runner entry points.
"""

from __future__ import annotations

from evaluations.runner.metadata import (
    ReproducibilityMetadata,
    ResultsRecord,
    current_commit,
)
from evaluations.runner.runner import run_all, run_case

__all__ = [
    "ReproducibilityMetadata",
    "ResultsRecord",
    "current_commit",
    "run_all",
    "run_case",
]
