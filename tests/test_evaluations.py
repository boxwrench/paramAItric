from __future__ import annotations

from evaluations.cases import Disposition, EvaluationCase, Tier, load_cases
from evaluations.runner.runner import run_all, run_case


def test_load_cases_returns_four_cases_across_tiers() -> None:
    cases = load_cases()

    assert len(cases) == 4

    tiers = {case.tier for case in cases}
    assert tiers == {Tier.CONTRACT, Tier.SAFETY}

    contract = [case for case in cases if case.tier == Tier.CONTRACT]
    safety = [case for case in cases if case.tier == Tier.SAFETY]
    assert len(contract) == 2
    assert len(safety) == 2

    assert all(case.disposition == Disposition.SUCCEED for case in contract)
    assert all(case.disposition == Disposition.FAIL_SAFELY for case in safety)


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
    assert len(safety) == 2
    for record in safety:
        # Stage 1 landed: the structured error envelope is complete, so the
        # recoverable/stage/next_step normalization gaps are now closed.
        assert record.normalization_gaps == []
        result = record.actual_result
        assert result.get("ok") is False
        assert result.get("classification")
        assert result.get("recoverable") is not None
        assert result.get("stage") is not None
        assert "next_step" in result


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
