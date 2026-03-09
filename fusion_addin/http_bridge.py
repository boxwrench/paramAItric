from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from fusion_addin.cancellation import OperationCancelledError
from fusion_addin.dispatcher import CommandDispatcher


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
        self._send_json(
            200,
            {
                "ok": True,
                "status": "ready",
                "mode": self.server.dispatcher.mode,
                "workflow_catalog": self.server.dispatcher.workflow_catalog(),
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/cancel":
            self._handle_cancel()
            return
        if self.path != "/command":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        command = payload["command"]
        arguments = payload.get("arguments", {})
        request_id = payload.get("request_id")

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
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        request_id = payload.get("request_id")
        if not isinstance(request_id, str) or not request_id.strip():
            self._send_json(400, {"ok": False, "error": "request_id is required."})
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
