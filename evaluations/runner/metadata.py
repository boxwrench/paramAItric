"""Reproducibility metadata and per-case result records.

Every evaluation run captures enough context to reproduce it later: the repo
commit, the model and tool profile used, the inference backend, and the
hardware. Records are written to disk as JSON so baselines can be diffed across
runs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess


def current_commit() -> str:
    """Return the current git commit hash, or ``"unknown"`` on failure."""
    repo_root = Path(__file__).resolve().parents[2]
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return "unknown"
    commit = completed.stdout.strip()
    return commit or "unknown"


@dataclass
class ReproducibilityMetadata:
    """Context needed to reproduce a single evaluation run."""

    paramaitric_commit: str
    lemonade_version: str | None
    pi_version: str | None
    model: str
    quantization: str | None
    tool_profile: str
    inference_backend: str
    hardware: str | None
    driver_version: str | None
    context_size: int | None
    temperature: float
    evaluation_case: str

    @classmethod
    def capture(cls, evaluation_case: str, **overrides) -> "ReproducibilityMetadata":
        """Build metadata for a mock run, filling defaults from env and kwargs.

        Auto-fills the repo commit and sensible mock defaults. Each value can be
        overridden by a keyword argument, and the model/tool-profile/backend
        default may also come from the ``PARAMAITRIC_EVAL_*`` environment
        variables.
        """
        defaults: dict = {
            "paramaitric_commit": current_commit(),
            "lemonade_version": os.environ.get("PARAMAITRIC_EVAL_LEMONADE_VERSION"),
            "pi_version": os.environ.get("PARAMAITRIC_EVAL_PI_VERSION"),
            "model": os.environ.get("PARAMAITRIC_EVAL_MODEL", "mock"),
            "quantization": os.environ.get("PARAMAITRIC_EVAL_QUANTIZATION"),
            "tool_profile": os.environ.get("PARAMAITRIC_EVAL_TOOL_PROFILE", "full"),
            "inference_backend": os.environ.get("PARAMAITRIC_EVAL_BACKEND", "mock"),
            "hardware": os.environ.get("PARAMAITRIC_EVAL_HARDWARE"),
            "driver_version": os.environ.get("PARAMAITRIC_EVAL_DRIVER_VERSION"),
            "context_size": _int_or_none(os.environ.get("PARAMAITRIC_EVAL_CONTEXT_SIZE")),
            "temperature": _float_or_default(
                os.environ.get("PARAMAITRIC_EVAL_TEMPERATURE"), 0.0
            ),
            "evaluation_case": evaluation_case,
        }
        defaults.update(overrides)
        return cls(**defaults)

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary of the metadata."""
        return asdict(self)


@dataclass
class RequestMetrics:
    """Per-request metrics for one evaluation, comparing a model against baseline.

    Every field defaults to ``None`` and stays ``None`` until something can
    genuinely determine it. ``None`` means "not measured", explicitly distinct
    from a real ``0``/``False``/``[]``. Most of these are *model-in-the-loop*
    signals with no meaning under the mock bridge, where no model selects a tool,
    emits JSON, retries, or consumes tokens; the runner leaves those ``None`` and
    a real Lemonade run fills them.
    """

    # Determinable post-execution without a model:
    workflow_correct: bool | None = None
    verification_passed: bool | None = None
    export_valid: bool | None = None
    # Model-in-the-loop; None under the mock bridge:
    tool_correct: bool | None = None
    json_valid: bool | None = None
    retries: int | None = None
    hallucinated_params: list[str] | None = None
    latency_ms: float | None = None
    tokens: int | None = None

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary of all metrics."""
        return asdict(self)


@dataclass
class ResultsRecord:
    """The outcome of running a single evaluation case."""

    metadata: ReproducibilityMetadata
    case_id: str
    tier: str
    disposition: str
    status: str
    timestamp: str
    actual_result: dict
    assertions: list[dict]
    normalization_gaps: list[str]
    skipped_reason: str | None = None
    metrics: RequestMetrics = field(default_factory=RequestMetrics)

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary with nested metadata."""
        return {
            "metadata": self.metadata.to_dict(),
            "case_id": self.case_id,
            "tier": self.tier,
            "disposition": self.disposition,
            "status": self.status,
            "timestamp": self.timestamp,
            "actual_result": self.actual_result,
            "assertions": self.assertions,
            "normalization_gaps": self.normalization_gaps,
            "skipped_reason": self.skipped_reason,
            "metrics": self.metrics.to_dict(),
        }

    def write(self, directory: str | os.PathLike[str]) -> Path:
        """Write ``<case_id>.json`` into ``directory`` and return its path."""
        target_dir = Path(directory)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{self.case_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
            handle.write("\n")
        return path


def utc_timestamp() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _int_or_none(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _float_or_default(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default
