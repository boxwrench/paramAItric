from __future__ import annotations

import json
from urllib import error, request

from mcp_server.schemas import CommandEnvelope


class BridgeTimeoutError(RuntimeError):
    """Raised when the Fusion bridge does not respond before the request timeout."""


class BridgeCancelledError(RuntimeError):
    """Raised when the bridge request is cancelled or aborted before completion."""


def _is_timeout_error(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, error.URLError):
        reason = exc.reason
        return isinstance(reason, TimeoutError) or "timed out" in str(reason).lower()
    return "timed out" in str(exc).lower()


def _is_cancel_error(exc: BaseException) -> bool:
    if isinstance(exc, KeyboardInterrupt):
        return True
    if isinstance(exc, error.URLError):
        reason = exc.reason
        if isinstance(reason, OSError) and getattr(reason, "winerror", None) == 995:
            return True
        message = str(reason).lower()
        return "cancel" in message or "aborted" in message
    if isinstance(exc, OSError) and getattr(exc, "winerror", None) == 995:
        return True
    message = str(exc).lower()
    return "cancel" in message or "aborted" in message


class BridgeClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8123",
        health_timeout: float = 5.0,
        command_timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.health_timeout = health_timeout
        self.command_timeout = command_timeout

    def health(self) -> dict:
        try:
            with request.urlopen(f"{self.base_url}/health", timeout=self.health_timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, OSError) as exc:
            if _is_timeout_error(exc):
                raise BridgeTimeoutError("Fusion bridge request timed out.") from exc
            if _is_cancel_error(exc):
                raise BridgeCancelledError("Fusion bridge request was cancelled.") from exc
            raise RuntimeError("Fusion bridge is not reachable.") from exc

    def workflow_catalog(self) -> list[dict]:
        health = self.health()
        return health.get("workflow_catalog", [])

    def send(self, envelope: CommandEnvelope) -> dict:
        payload = json.dumps({"command": envelope.command, "arguments": envelope.arguments}).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/command",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.command_timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise RuntimeError(f"Bridge command failed: {detail}") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            if _is_timeout_error(exc):
                raise BridgeTimeoutError("Fusion bridge request timed out.") from exc
            if _is_cancel_error(exc):
                raise BridgeCancelledError("Fusion bridge request was cancelled.") from exc
            raise RuntimeError("Fusion bridge is not reachable.") from exc
