from __future__ import annotations

from contextvars import ContextVar
from typing import Protocol


class CancellationAwareRequest(Protocol):
    @property
    def cancel_requested(self) -> bool: ...


class OperationCancelledError(RuntimeError):
    """Raised when a running Fusion-side command cooperatively stops on cancellation."""


_current_request: ContextVar[CancellationAwareRequest | None] = ContextVar(
    "paramaitric_current_request",
    default=None,
)


def set_current_request(request: CancellationAwareRequest | None):
    return _current_request.set(request)


def reset_current_request(token) -> None:
    _current_request.reset(token)


def cancellation_requested() -> bool:
    request = _current_request.get()
    if request is None:
        return False
    return request.cancel_requested


def raise_if_cancelled() -> None:
    if cancellation_requested():
        raise OperationCancelledError("Command was cancelled during execution.")
