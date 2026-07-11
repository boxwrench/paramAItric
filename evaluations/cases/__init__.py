"""Evaluation case definitions and loader.

Re-exports the case dataclasses/enums from :mod:`evaluations.cases.schema` and
the :func:`load_cases` loader so callers can ``from evaluations.cases import
EvaluationCase, Tier, Disposition, load_cases``.
"""

from __future__ import annotations

from evaluations.cases.schema import (
    Disposition,
    EvaluationCase,
    Tier,
    load_cases,
)

__all__ = ["Disposition", "EvaluationCase", "Tier", "load_cases"]
