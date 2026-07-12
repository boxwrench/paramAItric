from __future__ import annotations

import json
import uuid
from pathlib import Path
from urllib import error, request

from fusion_addin.dispatcher import DEFAULT_DISPATCH_DEADLINE
from mcp_server.schemas import CommandEnvelope

# The client-side command timeout must stay strictly greater than the
# server's dispatch deadline: the server always resolves a /command request
# (with a 200, 504, or 409) before that deadline elapses, so a client timeout
# shorter than or equal to it could fire first and race the authoritative
# server response. The margin below is generous slack for network latency.
DEFAULT_COMMAND_TIMEOUT = DEFAULT_DISPATCH_DEADLINE + 5.0


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
        command_timeout: float = DEFAULT_COMMAND_TIMEOUT,
        auth_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.health_timeout = health_timeout
        self.command_timeout = command_timeout

        # Resolve the auth token lazily. Constructing a client without a
        # running bridge (e.g. during import, health checks, or tests) must
        # not fail; only authenticated calls (send/cancel) require the token.
        # Track whether the token was supplied explicitly (in which case we
        # must never silently overwrite it with the file contents) or was
        # derived from the on-disk token file (in which case it is safe to
        # refresh on a 401, since the file is the bridge's source of truth).
        self._auth_token = auth_token
        self._auth_token_explicit = auth_token is not None

    def _token_path(self) -> Path:
        return Path.home() / ".paramaitric_auth_token"

    def _resolve_auth_token(self) -> str:
        if self._auth_token is not None:
            return self._auth_token
        token_path = self._token_path()
        if not token_path.exists():
            raise RuntimeError(
                f"Auth token file not found at {token_path}. "
                "Is the Fusion bridge running? The bridge writes this "
                "file on startup."
            )
        self._auth_token = token_path.read_text(encoding="utf-8").strip()
        return self._auth_token

    def _refresh_auth_token(self) -> str | None:
        """Re-read the token file, discarding any cached (stale) token.

        Only meaningful when the token was file-derived; explicit tokens are
        never overwritten. Returns the refreshed token, or None if the
        refresh could not happen (explicit token, or file missing).
        """
        if self._auth_token_explicit:
            return None
        token_path = self._token_path()
        if not token_path.exists():
            return None
        self._auth_token = token_path.read_text(encoding="utf-8").strip()
        return self._auth_token

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-ParamAItric-Auth": self._resolve_auth_token(),
        }

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

    def send(self, envelope: CommandEnvelope, request_id: str | None = None) -> dict:
        # Every command gets a request_id -- generated here if the caller
        # didn't supply one -- so a client-side timeout has something to
        # target with a best-effort cancel (see _send_once below).
        if request_id is None:
            request_id = uuid.uuid4().hex
        payload_dict = {
            "command": envelope.command,
            "arguments": envelope.arguments,
            "request_id": request_id,
        }
        return self._send_once(payload_dict, request_id, allow_auth_retry=True)

    def _send_once(self, payload_dict: dict, request_id: str, *, allow_auth_retry: bool) -> dict:
        payload = json.dumps(payload_dict).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/command",
            data=payload,
            headers=self._auth_headers(),
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.command_timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raw_detail = exc.read().decode("utf-8")
            classification, message = self._parse_error_body(raw_detail)

            if exc.code == 401 and allow_auth_retry:
                refreshed = self._refresh_auth_token()
                if refreshed is not None:
                    return self._send_once(payload_dict, request_id, allow_auth_retry=False)

            if exc.code == 504 or classification == "timeout":
                raise BridgeTimeoutError(message or "Fusion bridge request timed out.") from exc
            if exc.code == 409 or classification == "cancelled":
                raise BridgeCancelledError(message or "Fusion bridge request was cancelled.") from exc
            if "cancelled" in raw_detail.lower():
                raise BridgeCancelledError("Fusion bridge request was cancelled.") from exc
            raise RuntimeError(f"Bridge command failed: {raw_detail}") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            if _is_timeout_error(exc):
                # Early socket-level timeout: the server may still be working
                # on this request. Issue a best-effort authenticated cancel
                # so it doesn't run (or keep running) unattended. A failure
                # here must never mask the original timeout.
                self._best_effort_cancel(request_id)
                raise BridgeTimeoutError("Fusion bridge request timed out.") from exc
            if _is_cancel_error(exc):
                raise BridgeCancelledError("Fusion bridge request was cancelled.") from exc
            raise RuntimeError("Fusion bridge is not reachable.") from exc

    def _best_effort_cancel(self, request_id: str) -> None:
        # This runs after the command already timed out (potentially the full
        # command_timeout), so bound the cancel with the short health_timeout
        # rather than command_timeout -- a wedged bridge must not block the
        # caller for another full command deadline.
        try:
            self.cancel(request_id, timeout=self.health_timeout)
        except Exception:
            pass

    @staticmethod
    def _parse_error_body(raw: str) -> tuple[str | None, str | None]:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None, None
        if not isinstance(data, dict):
            return None, None
        classification = data.get("classification")
        message = data.get("error")
        classification = classification if isinstance(classification, str) else None
        message = message if isinstance(message, str) else None
        return classification, message

    def cancel(self, request_id: str, timeout: float | None = None) -> dict:
        payload = json.dumps({"request_id": request_id}).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/cancel",
            data=payload,
            headers=self._auth_headers(),
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout if timeout is not None else self.command_timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise RuntimeError(f"Bridge cancel failed: {detail}") from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            if _is_timeout_error(exc):
                raise BridgeTimeoutError("Fusion bridge request timed out.") from exc
            if _is_cancel_error(exc):
                raise BridgeCancelledError("Fusion bridge request was cancelled.") from exc
            raise RuntimeError("Fusion bridge is not reachable.") from exc
