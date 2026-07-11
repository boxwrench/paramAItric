from __future__ import annotations

# Whether a given failure classification is something the caller can act on and
# retry (fix input, reconnect the bridge) versus a failure that needs different
# handling before any retry makes sense. Used to fill ``recoverable`` when a
# raise site does not state it explicitly.
_RECOVERABLE_BY_CLASSIFICATION: dict[str, bool] = {
    "validation_error": True,
    "bridge_error": True,
    "timeout": True,
    "cancelled": True,
    "verification_failed": False,
    "state_drift": False,
    "unexpected_error": False,
}

# Plain-language "what to do next" used when a raise site does not supply its
# own next_step. Kept separate from validator messages (which tests pin) so the
# guidance can improve without changing pinned error text.
_NEXT_STEP_BY_CLASSIFICATION: dict[str, str] = {
    "validation_error": "Correct the reported value and resubmit the request.",
    "bridge_error": "Check that Fusion is running with the ParamAItric add-in, then retry.",
    "timeout": "Check if Fusion is responsive and retry.",
    "cancelled": "Re-issue the request when you are ready.",
    "verification_failed": "Review the reported geometry mismatch before retrying.",
    "state_drift": "Start from a clean Fusion document and retry.",
    "unexpected_error": "Retry; if it persists, report this with the stage and error.",
}


def default_recoverable(classification: str) -> bool:
    """Best-effort recoverability for a classification (defaults to False)."""
    return _RECOVERABLE_BY_CLASSIFICATION.get(classification, False)


def default_next_step(classification: str) -> str | None:
    """Best-effort next-step guidance for a classification, or None."""
    return _NEXT_STEP_BY_CLASSIFICATION.get(classification)


def structured_error(
    *,
    error: str,
    classification: str,
    stage: str | None,
    recoverable: bool | None = None,
    next_step: str | None = None,
    partial_result: dict | None = None,
) -> dict:
    """Build the canonical failure envelope shared by every host-facing path.

    Shape: ``{ok, classification, stage, error, recoverable, next_step,
    partial_result}``. No host ever parses a traceback: ``error`` is a plain
    message string only. ``recoverable`` and ``next_step`` fall back to
    classification-based defaults when not supplied.
    """
    return {
        "ok": False,
        "classification": classification,
        "stage": stage,
        "error": error,
        "recoverable": default_recoverable(classification) if recoverable is None else recoverable,
        "next_step": next_step if next_step is not None else default_next_step(classification),
        "partial_result": partial_result or {},
    }


class WorkflowFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        stage: str,
        classification: str,
        partial_result: dict | None = None,
        next_step: str | None = None,
        recoverable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.classification = classification
        self.partial_result = partial_result or {}
        self.next_step = next_step
        self.recoverable = recoverable

    def as_dict(self) -> dict:
        """Return the canonical structured-error envelope for this failure."""
        return structured_error(
            error=str(self),
            classification=self.classification,
            stage=self.stage,
            recoverable=self.recoverable,
            next_step=self.next_step,
            partial_result=self.partial_result,
        )


def error_from_exception(exc: Exception) -> dict:
    """Normalize any exception reaching a host boundary into the failure envelope.

    - ``WorkflowFailure`` keeps its own stage/classification/next_step.
    - ``ValueError`` (schema/input validation) becomes ``validation_error``.
    - Anything else becomes ``unexpected_error`` (message only, never a traceback).
    """
    if isinstance(exc, WorkflowFailure):
        return exc.as_dict()
    if isinstance(exc, ValueError):
        return structured_error(
            error=str(exc), classification="validation_error", stage="input_validation"
        )
    return structured_error(
        error=str(exc), classification="unexpected_error", stage="unknown"
    )
