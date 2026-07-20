from __future__ import annotations

import pytest

from evaluations.cases import Disposition, EvaluationCase, Tier, load_cases
from evaluations.runner.runner import run_all, run_case


_METRIC_KEYS = {
    "workflow_correct",
    "tool_correct",
    "json_valid",
    "retries",
    "hallucinated_params",
    "verification_passed",
    "export_valid",
    "latency_ms",
    "tokens",
}


def test_results_record_carries_request_metrics_none_by_default() -> None:
    from evaluations.runner.metadata import ReproducibilityMetadata, ResultsRecord

    record = ResultsRecord(
        metadata=ReproducibilityMetadata.capture("synthetic"),
        case_id="synthetic",
        tier="contract",
        disposition="succeed",
        status="pass",
        timestamp="t",
        actual_result={},
        assertions=[],
        normalization_gaps=[],
    )
    payload = record.to_dict()
    assert "metrics" in payload
    assert set(payload["metrics"].keys()) == _METRIC_KEYS
    # Every metric defaults to None — never 0/False/[], which would be
    # indistinguishable from a real measured value.
    assert all(payload["metrics"][key] is None for key in _METRIC_KEYS)


def test_hallucinated_params_flags_keys_absent_from_tool_schema() -> None:
    from evaluations.runner.metrics import hallucinated_params

    valid = {"width_cm": 2, "height_cm": 2, "thickness_cm": 1, "output_path": "s.stl"}
    # Nothing invented -> empty.
    assert hallucinated_params("create_spacer", valid) == []
    # `units` is a real generated field for create_ tools -> not flagged.
    assert hallucinated_params("create_spacer", {**valid, "units": "mm"}) == []
    # Keys the schema does not define -> flagged, sorted.
    assert hallucinated_params(
        "create_spacer", {**valid, "diameter_cm": 3, "bogus": 1}
    ) == ["bogus", "diameter_cm"]


def test_hallucinated_params_unknown_tool_reports_nothing() -> None:
    from evaluations.runner.metrics import hallucinated_params

    # No schema to audit against -> cannot detect, so report nothing rather
    # than flag everything.
    assert hallucinated_params("not_a_real_tool", {"anything": 1}) == []


def test_runner_populates_determinable_metrics_and_leaves_model_metrics_none(
    tmp_path,
) -> None:
    records = run_all(results_dir=tmp_path)
    by_id = {record.case_id: record for record in records}

    # A passing contract case: every post-execution metric is determined.
    spacer = by_id["spacer_success"]
    assert spacer.metrics.workflow_correct is True
    assert spacer.metrics.verification_passed is True
    assert spacer.metrics.export_valid is True
    # Model-in-the-loop metrics have no meaning under the mock bridge -> None,
    # never a fabricated 0/False/[].
    for attr in ("tool_correct", "json_valid", "retries",
                 "hallucinated_params", "latency_ms", "tokens"):
        assert getattr(spacer.metrics, attr) is None, attr

    # A fail-safely (safety) case produces no geometry -> all metrics None.
    safety = next(r for r in records if r.tier == Tier.SAFETY.value)
    for attr in _METRIC_KEYS:
        assert getattr(safety.metrics, attr) is None, attr


def test_fault_bridge_forces_verification_failure(running_bridge, tmp_path) -> None:
    from evaluations.runner.fault_bridge import fault_bridge_client
    from mcp_server.errors import WorkflowFailure
    from mcp_server.server import ParamAIToolServer

    _, base_url = running_bridge
    server = ParamAIToolServer(fault_bridge_client(base_url, "verification_dimensions"))

    with pytest.raises(WorkflowFailure) as exc:
        server.create_spacer(
            {
                "width_cm": 2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": str(tmp_path / "verif_fault.stl"),
            }
        )
    assert exc.value.classification == "verification_failed"


def _mock_server(base_url):
    from mcp_server.bridge_client import BridgeClient
    from mcp_server.server import ParamAIToolServer

    return ParamAIToolServer(BridgeClient(base_url))


def test_declined_case_passes_on_no_confident_match(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = _mock_server(base_url)
    case = EvaluationCase.from_dict(
        {
            "id": "synthetic_declined",
            "tier": "safety",
            "disposition": "declined",
            "original_request": "a decorative abstract sculpture of my feelings",
            "expected_workflow": "",
            "expected_tool_call": "recommend_workflow",
            "arguments": {"intent": "a decorative abstract sculpture of my feelings"},
            "expected_normalized_arguments": {},
            "expected_verification_facts": {},
            "expected_export_type": None,
            "expected_error": None,
        }
    )
    record = run_case(
        case, server=server, unavailable_server=server, tmp=str(tmp_path), base_url=base_url
    )
    assert record.status == "pass", record.assertions
    assert record.actual_result["match_trace"]["status"] == "no_confident_match"
    assert record.actual_result["candidates"] == []
    assert record.actual_result["families"]


def test_fault_bridge_case_reports_verification_failed(running_bridge, tmp_path) -> None:
    _, base_url = running_bridge
    server = _mock_server(base_url)
    case = EvaluationCase.from_dict(
        {
            "id": "synthetic_verif_fault",
            "tier": "safety",
            "disposition": "fail_safely",
            "original_request": "a spacer whose build silently goes wrong",
            "expected_workflow": "create_spacer",
            "expected_tool_call": "create_spacer",
            "arguments": {
                "width_cm": 2.0,
                "height_cm": 1.0,
                "thickness_cm": 0.5,
                "output_path": "{tmp}/synthetic_verif_fault.stl",
            },
            "expected_normalized_arguments": {},
            "expected_verification_facts": {},
            "expected_export_type": None,
            "expected_error": {"classification": "verification_failed"},
            "bridge": "verification_dimensions",
        }
    )
    record = run_case(
        case, server=server, unavailable_server=server, tmp=str(tmp_path), base_url=base_url
    )
    assert record.status == "pass", record.assertions
    assert record.actual_result["ok"] is False
    assert record.actual_result["classification"] == "verification_failed"


def test_case_loads_declined_disposition() -> None:
    from evaluations.cases import Disposition, EvaluationCase

    case = EvaluationCase.from_dict(
        {
            "id": "x",
            "tier": "safety",
            "disposition": "declined",
            "original_request": "vague",
            "expected_workflow": "",
            "expected_tool_call": "recommend_workflow",
            "arguments": {"intent": "vague"},
            "expected_normalized_arguments": {},
            "expected_verification_facts": {},
            "expected_export_type": None,
            "expected_error": None,
        }
    )
    assert case.disposition == Disposition.DECLINED


def test_load_cases_returns_all_cases_across_tiers() -> None:
    cases = load_cases()

    assert len(cases) == 17

    tiers = {case.tier for case in cases}
    assert tiers == {Tier.CONTRACT, Tier.SAFETY}

    contract = [case for case in cases if case.tier == Tier.CONTRACT]
    safety = [case for case in cases if case.tier == Tier.SAFETY]
    assert len(contract) == 8
    assert len(safety) == 9

    assert all(case.disposition == Disposition.SUCCEED for case in contract)
    # Safety cases fail safely or decline safely; declining is its own outcome.
    assert all(
        case.disposition in {Disposition.FAIL_SAFELY, Disposition.DECLINED}
        for case in safety
    )
    assert sum(case.disposition == Disposition.DECLINED for case in safety) == 1


def test_runner_contract_and_safety_cases_pass(tmp_path) -> None:
    records = run_all(results_dir=tmp_path)

    assert records
    for record in records:
        if record.status == "skipped":
            continue
        assert record.status == "pass", (record.case_id, record.assertions)


def test_results_record_has_full_reproducibility_metadata(tmp_path) -> None:
    records = run_all(results_dir=tmp_path)

    required_keys = {
        "paramaitric_commit",
        "lemonade_version",
        "pi_version",
        "model",
        "quantization",
        "tool_profile",
        "inference_backend",
        "hardware",
        "driver_version",
        "context_size",
        "temperature",
        "evaluation_case",
    }
    for record in records:
        metadata = record.to_dict()["metadata"]
        assert required_keys.issubset(metadata.keys())
        assert isinstance(metadata["paramaitric_commit"], str)
        assert metadata["paramaitric_commit"]


def test_safety_cases_expose_full_structured_error(tmp_path) -> None:
    records = run_all(results_dir=tmp_path)

    safety = [record for record in records if record.tier == Tier.SAFETY.value]
    assert len(safety) == 9

    fail_safely = [
        r for r in safety if r.disposition == Disposition.FAIL_SAFELY.value
    ]
    assert len(fail_safely) == 8
    for record in fail_safely:
        # Stage 1 landed: the structured error envelope is complete, so the
        # recoverable/stage/next_step normalization gaps are now closed.
        assert record.normalization_gaps == []
        result = record.actual_result
        assert result.get("ok") is False
        assert result.get("classification")
        assert result.get("recoverable") is not None
        assert result.get("stage") is not None
        assert "next_step" in result

    # The declined case is a safe refusal, not a structured error.
    declined = [r for r in safety if r.disposition == Disposition.DECLINED.value]
    assert len(declined) == 1
    assert declined[0].actual_result["match_trace"]["status"] == "no_confident_match"


def test_live_fusion_tier_is_defined_but_skipped() -> None:
    case = EvaluationCase.from_dict(
        {
            "id": "synthetic_live",
            "tier": "live_fusion",
            "disposition": "succeed",
            "original_request": "Make a spacer on a live Fusion session.",
            "expected_workflow": "create_spacer",
            "required_measurements": ["width", "height", "thickness"],
            "expected_tool_call": "create_spacer",
            "arguments": {},
            "expected_normalized_arguments": {},
            "expected_verification_facts": {},
            "expected_export_type": "stl",
            "expected_error": None,
        }
    )

    record = run_case(case, server=None, unavailable_server=None, tmp="/tmp")

    assert record.status == "skipped"
    assert record.skipped_reason is not None
    assert "Fusion" in record.skipped_reason
