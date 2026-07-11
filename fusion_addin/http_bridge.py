from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from fusion_addin.cancellation import OperationCancelledError
from fusion_addin.dispatcher import CommandDispatcher


MAX_REQUEST_BODY_BYTES = 1024 * 1024


class BridgeHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], dispatcher: CommandDispatcher) -> None:
        super().__init__(server_address, BridgeRequestHandler)
        self.dispatcher = dispatcher


class BridgeRequestHandler(BaseHTTPRequestHandler):
    server: BridgeHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_error(404)
            return
        payload = {
            "ok": True,
            "status": "ready",
            "mode": self.server.dispatcher.mode,
            "workflow_catalog": self.server.dispatcher.workflow_catalog(),
        }
        if self.server.dispatcher.mode == "mock":
            payload["hint"] = (
                "Mock adapter active: no Fusion design was open when the add-in "
                "started. Open or create a design in Fusion and the bridge "
                "upgrades to live automatically."
            )
        self._send_json(200, payload)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/cancel":
            self._handle_cancel()
            return
        if self.path != "/command":
            self.send_error(404)
            return

        payload = self._read_json_object()
        if payload is None:
            return
        command = payload.get("command")
        arguments = payload.get("arguments", {})
        request_id = payload.get("request_id")
        if not isinstance(command, str) or not command.strip():
            self._send_invalid_request("command must be a non-empty string.")
            return
        if not isinstance(arguments, dict):
            self._send_invalid_request("arguments must be a JSON object.")
            return
        if request_id is not None and (not isinstance(request_id, str) or not request_id.strip()):
            self._send_invalid_request("request_id must be a non-empty string when provided.")
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
            self._send_json(409, {"ok": False, "command": command, "error": str(exc), "classification": "cancelled"})
        except Exception as exc:  # noqa: BLE001
            self._send_json(400, {"ok": False, "command": command, "error": str(exc)})

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
                },
            )
            return None
        if not content_length.isascii() or not content_length.isdigit():
            self._send_invalid_request("Content-Length must be a non-negative integer.")
            return None
        length = int(content_length)
        if length > MAX_REQUEST_BODY_BYTES:
            self._send_json(
                413,
                {
                    "ok": False,
                    "error": f"Request body exceeds the {MAX_REQUEST_BODY_BYTES}-byte limit.",
                    "classification": "request_too_large",
                },
            )
            return None

        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_invalid_request("Request body must be valid UTF-8 JSON.")
            return None
        if not isinstance(payload, dict):
            self._send_invalid_request("Request body must be a JSON object.")
            return None
        return payload

    def _send_invalid_request(self, message: str) -> None:
        self._send_json(
            400,
            {"ok": False, "error": message, "classification": "invalid_request"},
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
    def __init__(self, host: str = "127.0.0.1", port: int = 8123, dispatcher: CommandDispatcher | None = None) -> None:
        self.dispatcher = dispatcher or CommandDispatcher()
        self._server = BridgeHTTPServer((host, port), self.dispatcher)
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
