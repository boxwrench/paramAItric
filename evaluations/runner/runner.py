"""Server regression harness that replays evaluation cases against the MCP tool server.

This harness directly invokes known workflow methods with resolved arguments to
verify that they execute correctly and return the expected geometry/files.
For a full end-to-end agent evaluation (which submits natural language requests
through the model/MCP and evaluates model tool selection, measurement extraction,
etc.), see the Agent contract harness (future expansion).
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
import tempfile

from evaluations.cases import Disposition, EvaluationCase, Tier, load_cases
from evaluations.runner.metadata import (
    ReproducibilityMetadata,
    ResultsRecord,
    utc_timestamp,
)
from evaluations.runner.metrics import derive_metrics
from fusion_addin.http_bridge import HTTPBridgeService
from mcp_server.bridge_client import BridgeClient
from mcp_server.errors import WorkflowFailure, structured_error
from mcp_server.mcp_entrypoint import call_tool
from mcp_server.server import ParamAIToolServer


# A dead TCP port (9 = discard) whose connection is refused, forcing the bridge
# client down its unavailable path for the bridge_unavailable safety case.
_UNAVAILABLE_BASE_URL = "http://127.0.0.1:9/"

_RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

_LIVE_FUSION_SKIP_REASON = (
    "Live-Fusion tier requires a running Fusion session; skipped on this host."
)

# Fields defined in the Stage 1 target error shape whose absence today is a
# recorded normalization gap rather than a failure.
_GAP_FIELDS = ("stage", "recoverable", "next_step")


def _invoke(server: ParamAIToolServer, method: str, payload: dict) -> dict:
    """Call ``server.method(payload)`` using the shared public host-boundary dispatcher."""
    return call_tool(server, method, payload)


def _assert_normalized_arguments(case: EvaluationCase, resolved_args: dict, tmp: str) -> dict:
    """Validate that the case's arguments normalize to the expected shape at the boundary."""
    from mcp_server.unit_normalization import normalize_workflow_units

    expected_normalized = copy.deepcopy(case.expected_normalized_arguments)
    output_path = expected_normalized.get("output_path")
    if isinstance(output_path, str):
        expected_normalized["output_path"] = output_path.replace("{tmp}", tmp)

    actual_normalized = normalize_workflow_units(resolved_args)
    passed = actual_normalized == expected_normalized
    detail = f"expected {expected_normalized}, got {actual_normalized}"
    return _assert("normalized_arguments_match", passed, detail)


def _resolve_arguments(case: EvaluationCase, tmp: str) -> dict:
    """Deep-copy the case arguments, substituting ``{tmp}`` in the output path."""
    resolved = copy.deepcopy(case.arguments)
    output_path = resolved.get("output_path")
    if isinstance(output_path, str):
        resolved["output_path"] = output_path.replace("{tmp}", tmp)
    return resolved


def _assert(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _assertions_for_succeed(
    case: EvaluationCase, result: dict, resolved_args: dict
) -> list[dict]:
    assertions: list[dict] = []

    ok = result.get("ok") is True
    assertions.append(_assert("result_ok", ok, f"ok={result.get('ok')!r}"))

    workflow = result.get("workflow")
    assertions.append(
        _assert(
            "workflow_matches",
            workflow == case.expected_workflow,
            f"expected {case.expected_workflow!r}, got {workflow!r}",
        )
    )

    verification = result.get("verification", {}) if isinstance(result, dict) else {}
    for key, expected in case.expected_verification_facts.items():
        actual = verification.get(key)
        assertions.append(
            _assert(
                f"verification.{key}",
                actual == expected,
                f"expected {expected!r}, got {actual!r}",
            )
        )

    export = result.get("export", {}) if isinstance(result, dict) else {}
    output_path = export.get("output_path")
    exists = bool(output_path) and Path(output_path).exists()
    assertions.append(
        _assert("export_file_exists", exists, f"output_path={output_path!r}")
    )
    if case.expected_export_type is not None:
        suffix = f".{case.expected_export_type}"
        matches = bool(output_path) and str(output_path).endswith(suffix)
        assertions.append(
            _assert(
                "export_type_matches",
                matches,
                f"expected suffix {suffix!r}, got {output_path!r}",
            )
        )
    return assertions


def _assertions_for_fail_safely(case: EvaluationCase, result: dict) -> list[dict]:
    assertions: list[dict] = []
    expected_error = case.expected_error or {}

    not_ok = result.get("ok") is False
    assertions.append(_assert("result_not_ok", not_ok, f"ok={result.get('ok')!r}"))

    expected_classification = expected_error.get("classification")
    actual_classification = result.get("classification")
    assertions.append(
        _assert(
            "classification_matches",
            actual_classification == expected_classification,
            f"expected {expected_classification!r}, got {actual_classification!r}",
        )
    )

    error_contains = expected_error.get("error_contains")
    if error_contains:
        message = result.get("error", "")
        assertions.append(
            _assert(
                "error_contains",
                error_contains in message,
                f"expected {error_contains!r} in {message!r}",
            )
        )
    return assertions


def _assertions_for_declined(result: dict) -> list[dict]:
    """Assert a safely-declined discovery response.

    The system could not confidently map the request to any workflow, so it must
    decline — no confident pick — and offer the family fallback instead. This is
    a success of the safety design, not an error envelope.
    """
    trace = result.get("match_trace", {}) if isinstance(result, dict) else {}
    status = trace.get("status")
    candidates = result.get("candidates") if isinstance(result, dict) else None
    families = result.get("families") if isinstance(result, dict) else None
    return [
        _assert(
            "declined_no_confident_match",
            status == "no_confident_match",
            f"status={status!r}",
        ),
        _assert("declined_no_candidates", candidates == [], f"candidates={candidates!r}"),
        _assert("declined_offers_families", bool(families), f"families={families!r}"),
    ]


def _select_server(
    case: EvaluationCase,
    server: ParamAIToolServer,
    unavailable_server: ParamAIToolServer,
    base_url: str | None,
) -> ParamAIToolServer:
    """Pick the server whose bridge matches the case's declared bridge mode."""
    from evaluations.runner.fault_bridge import fault_bridge_client, is_fault

    if case.bridge == "unavailable":
        return unavailable_server
    if is_fault(case.bridge):
        if base_url is None:
            raise ValueError(
                f"case {case.id!r} needs bridge fault {case.bridge!r} but no base_url was given"
            )
        return ParamAIToolServer(fault_bridge_client(base_url, case.bridge))
    return server


def _normalization_gaps(case: EvaluationCase, result: dict) -> list[str]:
    """Fields the spec expects but that the current error shape omits/leaves None."""
    expected_error = case.expected_error or {}
    return [
        key
        for key in _GAP_FIELDS
        if key in expected_error
        and expected_error[key] is None
        and result.get(key) is None
    ]


def run_case(
    case: EvaluationCase,
    server: ParamAIToolServer,
    unavailable_server: ParamAIToolServer,
    tmp: str,
    base_url: str | None = None,
) -> ResultsRecord:
    """Run a single case and return its :class:`ResultsRecord`."""
    metadata = ReproducibilityMetadata.capture(case.id)

    if case.tier == Tier.LIVE_FUSION:
        return ResultsRecord(
            metadata=metadata,
            case_id=case.id,
            tier=case.tier.value,
            disposition=case.disposition.value,
            status="skipped",
            timestamp=utc_timestamp(),
            actual_result={},
            assertions=[],
            normalization_gaps=[],
            skipped_reason=_LIVE_FUSION_SKIP_REASON,
        )

    resolved_args = _resolve_arguments(case, tmp)
    chosen = _select_server(case, server, unavailable_server, base_url)
    result = _invoke(chosen, case.expected_tool_call, resolved_args)

    normalization_gaps: list[str] = []
    if case.disposition == Disposition.SUCCEED:
        assertions = _assertions_for_succeed(case, result, resolved_args)
    elif case.disposition == Disposition.DECLINED:
        assertions = _assertions_for_declined(result)
    else:
        assertions = _assertions_for_fail_safely(case, result)
        normalization_gaps = _normalization_gaps(case, result)

    if case.expected_normalized_arguments:
        assertions.append(_assert_normalized_arguments(case, resolved_args, tmp))

    status = "pass" if all(item["passed"] for item in assertions) else "fail"

    return ResultsRecord(
        metadata=metadata,
        case_id=case.id,
        tier=case.tier.value,
        disposition=case.disposition.value,
        status=status,
        timestamp=utc_timestamp(),
        actual_result=result,
        assertions=assertions,
        normalization_gaps=normalization_gaps,
        skipped_reason=None,
        metrics=derive_metrics(case.disposition.value, assertions),
    )


def run_all(
    cases: list[EvaluationCase] | None = None,
    results_dir: str | os.PathLike[str] | None = None,
) -> list[ResultsRecord]:
    """Run every case against one mock bridge, writing a record per case."""
    if cases is None:
        cases = load_cases()
    target_dir = Path(results_dir) if results_dir is not None else _RESULTS_DIR
    tmp = tempfile.gettempdir()

    service = HTTPBridgeService(port=0)
    service.start()
    host, port = service.address
    base_url = f"http://{host}:{port}"
    server = ParamAIToolServer(BridgeClient(base_url))
    unavailable_server = ParamAIToolServer(BridgeClient(_UNAVAILABLE_BASE_URL))

    records: list[ResultsRecord] = []
    try:
        for case in cases:
            record = run_case(case, server, unavailable_server, tmp, base_url=base_url)
            record.write(target_dir)
            records.append(record)
    finally:
        service.stop()
    return records
