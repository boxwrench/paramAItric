from __future__ import annotations

import hmac
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from fusion_addin.cancellation import OperationCancelledError
from fusion_addin.dispatcher import CommandDispatcher
from mcp_server.runtime_info import FUSION_BACKEND_ID, PARAMAITRIC_VERSION


MAX_REQUEST_BODY_BYTES = 1024 * 1024


class BridgeHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], dispatcher: CommandDispatcher, auth_token: str) -> None:
        super().__init__(server_address, BridgeRequestHandler)
        self.dispatcher = dispatcher
        self.auth_token = auth_token


class BridgeRequestHandler(BaseHTTPRequestHandler):
    server: BridgeHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_error(404)
            return
        workflow_catalog = self.server.dispatcher.workflow_catalog()
        payload = {
            "ok": True,
            "status": "ready",
            "backend": FUSION_BACKEND_ID,
            "version": PARAMAITRIC_VERSION,
            "mode": self.server.dispatcher.mode,
            "capabilities": self.server.dispatcher.registry.list_commands(),
            "workflow_count": len(workflow_catalog),
            "workflow_catalog": workflow_catalog,
        }
        if self.server.dispatcher.mode == "mock":
            payload["hint"] = (
                "Mock adapter active: no Fusion design was open when the add-in "
                "started. Open or create a design in Fusion and the bridge "
                "upgrades to live automatically."
            )
        self._send_json(200, payload)

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in ("/command", "/cancel"):
            self.send_error(404)
            return

        # 1. Origin protection: reject requests bearing Origin or Referer headers
        if "origin" in self.headers or "referer" in self.headers:
            self._send_json(
                403,
                {
                    "ok": False,
                    "error": "Access denied: cross-origin browser requests are prohibited.",
                    "classification": "unauthorized",
                    "recoverable": False,
                    "next_step": "Ensure requests are sent from a native client, not a web browser."
                }
            )
            return

        # 2. Token verification
        auth_header = self.headers.get("X-ParamAItric-Auth")
        if not auth_header or not hmac.compare_digest(auth_header, self.server.auth_token):
            self._send_json(
                401,
                {
                    "ok": False,
                    "error": "Access denied: invalid or missing authentication token.",
                    "classification": "unauthorized",
                    "recoverable": False,
                    "next_step": "Check that the client has read and is transmitting the current auth token."
                }
            )
            return

        if self.path == "/cancel":
            self._handle_cancel()
            return

        payload = self._read_json_object()
        if payload is None:
            return
        command = payload.get("command")
        arguments = payload.get("arguments", {})
        request_id = payload.get("request_id")
        if not isinstance(command, str) or not command.strip():
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": "command must be a non-empty string.",
                    "classification": "invalid_request",
                    "recoverable": False,
                    "next_step": "Provide a non-empty string command."
                }
            )
            return
        if not isinstance(arguments, dict):
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": "arguments must be a JSON object.",
                    "classification": "invalid_request",
                    "recoverable": False,
                    "next_step": "Provide an arguments JSON object."
                }
            )
            return
        if request_id is not None and (not isinstance(request_id, str) or not request_id.strip()):
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": "request_id must be a non-empty string when provided.",
                    "classification": "invalid_request",
                    "recoverable": False,
                    "next_step": "Provide a non-empty string request_id."
                }
            )
            return

        try:
            request = self.server.dispatcher.submit_async(command, arguments, request_id=request_id)
            request.done.wait()
            if request.error:
                raise request.error
            assert request.response is not None
            response = request.response
            self._send_json(200, response)
        except OperationCancelledError as exc:
            self._send_json(
                409,
                {
                    "ok": False,
                    "command": command,
                    "error": str(exc),
                    "classification": "cancelled",
                    "recoverable": True,
                    "next_step": "Retry the operation if needed."
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._send_json(
                400,
                {
                    "ok": False,
                    "command": command,
                    "error": str(exc),
                    "classification": "command_failed",
                    "recoverable": True,
                    "next_step": "Check parameters and design state before retrying."
                }
            )

    def _handle_cancel(self) -> None:
        payload = self._read_json_object()
        if payload is None:
            return
        request_id = payload.get("request_id")
        if not isinstance(request_id, str) or not request_id.strip():
            self._send_invalid_request("request_id must be a non-empty string.")
            return
        cancelled = self.server.dispatcher.cancel(request_id)
        if not cancelled:
            self._send_json(404, {"ok": False, "request_id": request_id, "error": "Request is not pending."})
            return
        status = "cancellation_requested" if request_id else "cancelled"
        request_state = self.server.dispatcher.request_status(request_id)
        if request_state == "cancelled":
            status = "cancelled"
        elif request_state == "cancellation_requested":
            status = "cancellation_requested"
        self._send_json(200, {"ok": True, "request_id": request_id, "status": status})

    def _read_json_object(self) -> dict | None:
        if self.headers.get_content_type() != "application/json":
            self._send_json(
                415,
                {
                    "ok": False,
                    "error": "Content-Type must be application/json.",
                    "classification": "invalid_request",
                    "recoverable": False,
                    "next_step": "Set Content-Type header to application/json."
                },
            )
            return None

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._send_json(
                411,
                {
                    "ok": False,
                    "error": "Content-Length is required.",
                    "classification": "invalid_request",
                    "recoverable": False,
                    "next_step": "Provide Content-Length header."
                },
            )
            return None
        if not content_length.isascii() or not content_length.isdigit():
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": "Content-Length must be a non-negative integer.",
                    "classification": "invalid_request",
                    "recoverable": False,
                    "next_step": "Provide a valid Content-Length header."
                },
            )
            return None
        length = int(content_length)
        if length > MAX_REQUEST_BODY_BYTES:
            self._send_json(
                413,
                {
                    "ok": False,
                    "error": f"Request body exceeds the {MAX_REQUEST_BODY_BYTES}-byte limit.",
                    "classification": "request_too_large",
                    "recoverable": False,
                    "next_step": "Reduce the size of the request payload."
                },
            )
            return None

        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": "Request body must be valid UTF-8 JSON.",
                    "classification": "invalid_request",
                    "recoverable": False,
                    "next_step": "Format the request payload as valid JSON."
                },
            )
            return None
        if not isinstance(payload, dict):
            self._send_json(
                400,
                {
                    "ok": False,
                    "error": "Request body must be a JSON object.",
                    "classification": "invalid_request",
                    "recoverable": False,
                    "next_step": "Format the request payload as a JSON object."
                },
            )
            return None
        return payload

    def _send_invalid_request(self, message: str) -> None:
        self._send_json(
            400,
            {
                "ok": False,
                "error": message,
                "classification": "invalid_request",
                "recoverable": False,
                "next_step": "Correct the request payload and headers."
            },
        )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        _ = (format, args)

    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class HTTPBridgeService:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8123,
        dispatcher: CommandDispatcher | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.dispatcher = dispatcher or CommandDispatcher()

        # Token-based auth setup
        if auth_token is not None:
            self.auth_token = auth_token
        else:
            self.auth_token = secrets.token_urlsafe(32)
            token_path = Path.home() / ".paramaitric_auth_token"
            try:
                if token_path.exists():
                    token_path.unlink()
                # Write token with owner-only permissions (0o600)
                fd = os.open(str(token_path), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
                with open(fd, "w", encoding="utf-8") as f:
                    f.write(self.auth_token)
                try:
                    os.chmod(str(token_path), 0o600)
                except Exception:
                    pass
            except Exception as exc:
                raise RuntimeError(f"Failed to initialize secure mutation boundary token: {exc}")

        self._server = BridgeHTTPServer((host, port), self.dispatcher, self.auth_token)
        self._thread: Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        return self._server.server_address

    def start(self) -> None:
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self.dispatcher.close()
        if self._thread:
            self._thread.join(timeout=1)

        # Clean up token file
        token_path = Path.home() / ".paramaitric_auth_token"
        try:
            if token_path.exists():
                token_path.unlink()
        except Exception:
            pass
