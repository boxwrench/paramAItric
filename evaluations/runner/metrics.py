"""Deriving per-request metrics for an evaluation run.

The metric *definitions* live here so they are testable in isolation. The
runner (mock, no model) can determine only the post-execution metrics; the
model-in-the-loop ones stay ``None`` until a real Lemonade run. See
``RequestMetrics`` in ``metadata.py`` for the None-versus-zero discipline.
"""

from __future__ import annotations

from mcp_server.schema_generation import tool_input_schema

from evaluations.runner.metadata import RequestMetrics


def _valid_param_names(method_name: str) -> set[str] | None:
    """Return a tool's accepted payload field names, or None if it has no schema.

    ``mcp_server.schema_generation`` is the authority on what a valid field is;
    the generated payload schema is closed (``additionalProperties: False``), so
    its property keys are exactly the accepted arguments.
    """
    schema = tool_input_schema(method_name, method_name)
    if schema is None:
        return None
    payload = schema.get("properties", {}).get("payload", {})
    return set(payload.get("properties", {}).keys())


def hallucinated_params(method_name: str, args: dict) -> list[str]:
    """Return argument keys the model supplied that the tool's schema does not define.

    Sorted for determinism. An unknown tool (no generated schema) cannot be
    audited, so nothing is reported rather than flagging every key.
    """
    valid = _valid_param_names(method_name)
    if valid is None:
        return []
    return sorted(key for key in args if key not in valid)


def derive_metrics(disposition: str, assertions: list[dict]) -> RequestMetrics:
    """Populate the metrics a mock run can determine, leaving the rest None.

    Only post-execution facts are knowable without a model, and only for cases
    that produce geometry (succeed disposition). Everything model-in-the-loop —
    tool selection, JSON validity, retries, hallucinated params, latency,
    tokens — stays None under the mock bridge, to be filled by a real run.
    """
    metrics = RequestMetrics()
    if disposition != "succeed":
        # A fail-safely case produces no geometry; post-execution metrics are
        # not applicable and stay None.
        return metrics

    passed = {item["name"]: item["passed"] for item in assertions}

    if "workflow_matches" in passed:
        metrics.workflow_correct = passed["workflow_matches"]

    verification = [v for name, v in passed.items() if name.startswith("verification.")]
    if verification:
        metrics.verification_passed = all(verification)

    export = [v for name, v in passed.items() if name.startswith("export_")]
    if export:
        metrics.export_valid = all(export)

    return metrics
