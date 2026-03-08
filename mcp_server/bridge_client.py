from __future__ import annotations

import json
from urllib import error, request

from mcp_server.schemas import CommandEnvelope


class BridgeClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8123") -> None:
        self.base_url = base_url.rstrip("/")

    def health(self) -> dict:
        try:
            with request.urlopen(f"{self.base_url}/health", timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
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
            with request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise RuntimeError(f"Bridge command failed: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError("Fusion bridge is not reachable.") from exc
