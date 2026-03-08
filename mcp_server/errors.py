from __future__ import annotations


class WorkflowFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        stage: str,
        classification: str,
        partial_result: dict | None = None,
        next_step: str | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.classification = classification
        self.partial_result = partial_result or {}
        self.next_step = next_step

    def as_dict(self) -> dict:
        payload = {
            "ok": False,
            "error": str(self),
            "stage": self.stage,
            "classification": self.classification,
            "partial_result": self.partial_result,
        }
        if self.next_step:
            payload["next_step"] = self.next_step
        return payload
