"""Fault-injecting bridge client for the evaluation harness.

The faithful mock bridge always builds correct geometry, so a verification
failure cannot arise from workflow input alone. This wraps a real
``BridgeClient`` and rewrites a chosen command's response, letting a safety case
exercise the ``verification_failed`` path deterministically.

Promoted here from ``tests/`` so the pytest suite and the evaluation runner
share one implementation instead of duplicating it.
"""

from __future__ import annotations

from typing import Callable

from mcp_server.bridge_client import BridgeClient
from mcp_server.schemas import CommandEnvelope

Interceptor = Callable[..., dict]


class InterceptingBridgeClient:
    """Duck-typed ``BridgeClient`` that can rewrite specific command responses.

    For any command with a registered interceptor, the interceptor decides the
    response (optionally delegating to the real client); all other commands pass
    straight through. A per-command call counter lets an interceptor act only on,
    say, the first call.
    """

    def __init__(
        self, base_url: str, interceptors: dict[str, Interceptor] | None = None
    ) -> None:
        self._client = BridgeClient(base_url)
        self._interceptors = interceptors or {}
        self._call_counts: dict[str, int] = {}

    def health(self) -> dict:
        return self._client.health()

    def send(self, envelope: CommandEnvelope) -> dict:
        command = envelope.command
        self._call_counts[command] = self._call_counts.get(command, 0) + 1
        interceptor = self._interceptors.get(command)
        if interceptor is not None:
            return interceptor(
                envelope=envelope,
                client=self._client,
                call_count=self._call_counts[command],
            )
        return self._client.send(envelope)


def corrupt_extrude_width(
    *, envelope: CommandEnvelope, client: BridgeClient, call_count: int
) -> dict:
    """Report an over-wide extruded body, which ``verify_dimensions`` rejects.

    The geometry is built correctly; only the reported width is corrupted, so the
    workflow reaches verification and fails there with ``verification_failed`` —
    exactly the safety path a verification-failure case must exercise.
    """
    _ = call_count
    result = client.send(envelope)
    return {
        **result,
        "result": {
            **result["result"],
            "body": {**result["result"]["body"], "width_cm": 999.0},
        },
    }


#: Named fault profiles a case can request through its ``bridge`` field.
_FAULTS: dict[str, dict[str, Interceptor]] = {
    "verification_dimensions": {"extrude_profile": corrupt_extrude_width},
}


def is_fault(bridge: str) -> bool:
    """Return whether ``bridge`` names a known fault profile."""
    return bridge in _FAULTS


def fault_bridge_client(base_url: str, fault: str) -> InterceptingBridgeClient:
    """Build an ``InterceptingBridgeClient`` for a named fault profile."""
    if fault not in _FAULTS:
        raise ValueError(
            f"Unknown bridge fault {fault!r}; known: {sorted(_FAULTS)}"
        )
    return InterceptingBridgeClient(base_url, interceptors=_FAULTS[fault])
