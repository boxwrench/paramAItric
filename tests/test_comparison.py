"""Tests for the geometry-equivalence comparator (goal G1).

ROADMAP.md defines milestone acceptance as results being "geometry-equivalent
to the Claude baseline ... within tolerance -- not identical files or topology
IDs". These tests pin that definition down: what counts as equivalent, what
counts as a mismatch, and what must never be compared at all.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from evaluations.cases.schema import EvaluationCase
from evaluations.runner.comparison import (
    INVARIANTS,
    ComparisonReport,
    Tolerances,
    Verdict,
    compare,
    compare_case,
)

BASELINE_DIR = Path(__file__).resolve().parents[1] / "evaluations" / "expected" / "claude"


def _case_dict(**overrides) -> dict:
    payload = {
        "id": "spacer_success",
        "tier": "contract",
        "disposition": "succeed",
        "original_request": "Print me a spacer 40 mm square and 10 mm thick.",
        "expected_workflow": "create_spacer",
        "required_measurements": ["width", "height", "thickness"],
        "expected_tool_call": "create_spacer",
        "arguments": {},
        "expected_normalized_arguments": {},
        "expected_verification_facts": {},
        "expected_export_type": "stl",
        "expected_error": None,
    }
    payload.update(overrides)
    return payload


def _case(**overrides) -> EvaluationCase:
    return EvaluationCase.from_dict(_case_dict(**overrides))


def _result(**overrides) -> dict:
    """A well-formed successful result, shaped like a real workflow return."""
    result = {
        "ok": True,
        "workflow": "create_spacer",
        "body": {
            "token": "TOKEN-AAA",
            "name": "Spacer",
            "plane": "xy",
            "operation": "new_body",
        },
        "verification": {
            "body_count": 1,
            "sketch_count": 1,
            "actual_width_cm": 4.0,
            "actual_height_cm": 4.0,
            "actual_thickness_cm": 1.0,
            "sketch_plane": "xy",
        },
        "export": {"output_path": r"C:\Users\me\Exports\spacer_success.stl"},
        "stages": [
            {"stage": "new_design", "status": "completed"},
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": {"bodies_info": [{"token": "TOKEN-AAA", "volume_cm3": 16.0}]},
            },
            {"stage": "export_stl", "status": "completed"},
        ],
    }
    result.update(overrides)
    return result


def _verdict_for(report: ComparisonReport, invariant: str) -> Verdict:
    for item in report.invariants:
        if item.name == invariant:
            return item.verdict
    raise AssertionError(f"report has no invariant named {invariant!r}")


class TestReportShape:
    """The report covers exactly the seven invariants ROADMAP.md names."""

    def test_the_seven_invariants_are_the_roadmap_seven(self) -> None:
        assert INVARIANTS == (
            "bounding_dimensions",
            "body_count",
            "volume",
            "features",
            "placement",
            "verification_tier",
            "export",
        )

    def test_identical_results_match_on_every_invariant(self) -> None:
        report = compare(_result(), _result(), _case())

        assert report.verdict is Verdict.MATCH
        assert {item.verdict for item in report.invariants} == {Verdict.MATCH}

    def test_every_invariant_is_reported_even_when_matching(self) -> None:
        report = compare(_result(), _result(), _case())

        assert [item.name for item in report.invariants] == list(INVARIANTS)

    def test_a_single_mismatch_makes_the_whole_report_mismatch(self) -> None:
        actual = _result()
        actual["verification"]["body_count"] = 2

        report = compare(actual, _result(), _case())

        assert report.verdict is Verdict.MISMATCH


class TestMissingBaseline:
    """An absent baseline is never a silent pass."""

    def test_compare_case_reports_no_baseline(self, tmp_path) -> None:
        report = compare_case(_case(id="uncaptured"), _result(), tmp_path)

        assert report.verdict is Verdict.NO_BASELINE

    def test_no_baseline_is_not_a_match(self, tmp_path) -> None:
        report = compare_case(_case(id="uncaptured"), _result(), tmp_path)

        assert report.verdict is not Verdict.MATCH


class TestBodyCount:
    """Body count must match exactly -- there is no tolerance on a count."""

    def test_matches_when_equal(self) -> None:
        report = compare(_result(), _result(), _case())

        assert _verdict_for(report, "body_count") is Verdict.MATCH

    def test_mismatches_when_a_body_splits(self) -> None:
        """The split-body failure mode: a cut produced two bodies, not one."""
        actual = _result()
        actual["verification"]["body_count"] = 2

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "body_count") is Verdict.MISMATCH

    def test_the_detail_names_both_numbers(self) -> None:
        actual = _result()
        actual["verification"]["body_count"] = 2

        report = compare(actual, _result(), _case())
        detail = next(i.detail for i in report.invariants if i.name == "body_count")

        assert "2" in detail and "1" in detail


class TestTolerances:
    """Tolerances are named and configurable, never inline magic numbers."""

    def test_dimension_and_volume_tolerances_are_separate(self) -> None:
        tolerances = Tolerances()

        assert hasattr(tolerances, "dimension_cm")
        assert hasattr(tolerances, "volume_relative")

    def test_a_dimension_within_tolerance_matches(self) -> None:
        actual = _result()
        actual["verification"]["actual_width_cm"] = 4.0 + 0.001

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "bounding_dimensions") is Verdict.MATCH

    def test_a_dimension_outside_tolerance_mismatches(self) -> None:
        actual = _result()
        actual["verification"]["actual_width_cm"] = 4.5

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "bounding_dimensions") is Verdict.MISMATCH

    def test_a_tighter_tolerance_can_turn_a_match_into_a_mismatch(self) -> None:
        actual = _result()
        actual["verification"]["actual_width_cm"] = 4.005

        lenient = compare(actual, _result(), _case(), Tolerances(dimension_cm=0.01))
        strict = compare(actual, _result(), _case(), Tolerances(dimension_cm=0.0001))

        assert _verdict_for(lenient, "bounding_dimensions") is Verdict.MATCH
        assert _verdict_for(strict, "bounding_dimensions") is Verdict.MISMATCH


class TestEquivalenceIsNotIdentity:
    """ROADMAP.md: never identical files, topology IDs, or feature ordering."""

    def test_different_topology_tokens_still_match(self) -> None:
        actual = _result()
        actual["body"]["token"] = "TOKEN-COMPLETELY-DIFFERENT"
        actual["stages"][1]["snapshot"]["bodies_info"][0]["token"] = "ALSO-DIFFERENT"

        report = compare(actual, _result(), _case())

        assert report.verdict is Verdict.MATCH

    def test_different_export_paths_still_match(self) -> None:
        actual = _result()
        actual["export"]["output_path"] = r"D:\somewhere\else\spacer_success.stl"

        report = compare(actual, _result(), _case())

        assert report.verdict is Verdict.MATCH

    def test_different_body_names_still_match(self) -> None:
        actual = _result()
        actual["body"]["name"] = "Body1"

        report = compare(actual, _result(), _case())

        assert report.verdict is Verdict.MATCH

    def test_extra_stages_still_match(self) -> None:
        """Feature ordering and stage count are not part of equivalence."""
        actual = _result()
        actual["stages"].insert(0, {"stage": "some_extra_step", "status": "completed"})

        report = compare(actual, _result(), _case())

        assert report.verdict is Verdict.MATCH

    def test_baseline_is_never_mutated(self) -> None:
        baseline = _result()
        untouched = copy.deepcopy(baseline)

        compare(_result(), baseline, _case())

        assert baseline == untouched


class TestEveryInvariantCanFail:
    """A comparator that cannot fail is not a comparator.

    One test per invariant, each mutating exactly the fact that invariant
    covers. Without these, a comparator hardcoded to return MATCH would pass
    every other test in this file.
    """

    def test_bounding_dimensions_can_fail(self) -> None:
        actual = _result()
        actual["verification"]["actual_thickness_cm"] = 2.0

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "bounding_dimensions") is Verdict.MISMATCH

    def test_body_count_can_fail(self) -> None:
        actual = _result()
        actual["verification"]["body_count"] = 3

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "body_count") is Verdict.MISMATCH

    def test_volume_can_fail(self) -> None:
        actual = _result()
        actual["stages"][1]["snapshot"]["bodies_info"][0]["volume_cm3"] = 24.0

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "volume") is Verdict.MISMATCH

    def test_volume_can_fail_on_body_count_of_volumes(self) -> None:
        actual = _result()
        actual["stages"][1]["snapshot"]["bodies_info"].append({"volume_cm3": 4.0})

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "volume") is Verdict.MISMATCH

    def test_features_can_fail_on_a_missing_feature(self) -> None:
        """The baseline cut a hole; this run did not."""
        baseline = _result()
        baseline["verification"]["hole_diameter_cm"] = 1.0

        report = compare(_result(), baseline, _case())

        assert _verdict_for(report, "features") is Verdict.MISMATCH

    def test_features_can_fail_on_a_wrong_feature_size(self) -> None:
        actual = _result()
        actual["verification"]["hole_diameter_cm"] = 2.0
        baseline = _result()
        baseline["verification"]["hole_diameter_cm"] = 1.0

        report = compare(actual, baseline, _case())

        assert _verdict_for(report, "features") is Verdict.MISMATCH

    def test_features_can_fail_on_a_wrong_operation(self) -> None:
        actual = _result()
        actual["body"]["operation"] = "cut"

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "features") is Verdict.MISMATCH

    def test_placement_can_fail(self) -> None:
        """Right geometry, wrong plane -- the classic silent-wrong-face outcome."""
        actual = _result()
        actual["verification"]["sketch_plane"] = "xz"
        actual["body"]["plane"] = "xz"

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "placement") is Verdict.MISMATCH

    def test_verification_tier_can_fail(self) -> None:
        """Geometry verification was skipped in this run."""
        actual = _result()
        actual["stages"] = [s for s in actual["stages"] if s["stage"] != "verify_geometry"]

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "verification_tier") is Verdict.MISMATCH

    def test_verification_tier_can_fail_when_verification_did_not_complete(self) -> None:
        actual = _result()
        actual["stages"][1]["status"] = "failed"

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "verification_tier") is Verdict.MISMATCH

    def test_export_can_fail_on_a_missing_export(self) -> None:
        actual = _result()
        actual["export"] = {}

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "export") is Verdict.MISMATCH

    def test_export_can_fail_on_the_wrong_format(self) -> None:
        actual = _result()
        actual["export"]["output_path"] = r"C:\out\spacer_success.step"

        report = compare(actual, _result(), _case())

        assert _verdict_for(report, "export") is Verdict.MISMATCH


class TestFailSafelyCases:
    """A case expected to fail has no geometry; compare the failure instead."""

    def _error(self, **overrides) -> dict:
        payload = {
            "ok": False,
            "error": "width_cm must be a positive number.",
            "classification": "validation_error",
        }
        payload.update(overrides)
        return payload

    def test_geometric_invariants_are_not_applicable(self) -> None:
        case = _case(id="invalid_dimensions", disposition="fail_safely")

        report = compare(self._error(), self._error(), case)

        for name in INVARIANTS:
            assert _verdict_for(report, name) is Verdict.NOT_APPLICABLE

    def test_same_failure_classification_matches(self) -> None:
        case = _case(id="invalid_dimensions", disposition="fail_safely")

        report = compare(self._error(), self._error(), case)

        assert report.verdict is Verdict.MATCH

    def test_different_failure_classification_mismatches(self) -> None:
        case = _case(id="invalid_dimensions", disposition="fail_safely")

        report = compare(
            self._error(classification="bridge_error"), self._error(), case
        )

        assert report.verdict is Verdict.MISMATCH

    def test_differing_error_wording_still_matches(self) -> None:
        """Message text is not a contract; classification is."""
        case = _case(id="invalid_dimensions", disposition="fail_safely")

        report = compare(
            self._error(error="Width must be positive."), self._error(), case
        )

        assert report.verdict is Verdict.MATCH

    def test_succeeding_when_the_baseline_failed_is_a_mismatch(self) -> None:
        """The dangerous direction: unsafe success where the baseline refused."""
        case = _case(id="invalid_dimensions", disposition="fail_safely")

        report = compare({"ok": True}, self._error(), case)

        assert report.verdict is Verdict.MISMATCH


class TestAgainstRealBaselines:
    """Integration: the comparator against the repo's captured baselines."""

    def test_a_baseline_compared_against_itself_matches(self) -> None:
        from evaluations.cases.schema import load_cases

        cases = {case.id: case for case in load_cases()}
        for case_id in ("spacer_success", "plate_centered_hole_success"):
            baseline = json.loads(
                (BASELINE_DIR / f"{case_id}.json").read_text(encoding="utf-8")
            )
            report = compare_case(cases[case_id], baseline["actual_result"])

            assert report.verdict is Verdict.MATCH, report.to_dict()

    def test_failure_baselines_compare_by_classification(self) -> None:
        from evaluations.cases.schema import load_cases

        cases = {case.id: case for case in load_cases()}
        for case_id in ("invalid_dimensions", "bridge_unavailable"):
            baseline = json.loads(
                (BASELINE_DIR / f"{case_id}.json").read_text(encoding="utf-8")
            )
            report = compare_case(cases[case_id], baseline["actual_result"])

            assert report.verdict is Verdict.MATCH, report.to_dict()

    def test_a_perturbed_baseline_is_caught(self) -> None:
        from evaluations.cases.schema import load_cases

        cases = {case.id: case for case in load_cases()}
        baseline = json.loads(
            (BASELINE_DIR / "spacer_success.json").read_text(encoding="utf-8")
        )
        perturbed = copy.deepcopy(baseline["actual_result"])
        perturbed["verification"]["actual_width_cm"] = 9.9

        report = compare_case(cases["spacer_success"], perturbed)

        assert report.verdict is Verdict.MISMATCH


class TestCompareRecords:
    """Comparing a whole run of records against a baseline set."""

    def test_reports_one_entry_per_record(self, tmp_path) -> None:
        from evaluations.cases.schema import load_cases
        from evaluations.runner.comparison import compare_records

        cases = load_cases()
        records = [_FakeRecord(case.id, _result()) for case in cases]

        reports = compare_records(records, cases, tmp_path)

        assert len(reports) == len(cases)

    def test_uncaptured_cases_report_no_baseline(self, tmp_path) -> None:
        from evaluations.cases.schema import load_cases
        from evaluations.runner.comparison import compare_records

        cases = load_cases()
        records = [_FakeRecord(case.id, _result()) for case in cases]

        reports = compare_records(records, cases, tmp_path)

        assert {r.verdict for r in reports} == {Verdict.NO_BASELINE}

    def test_against_the_real_baselines_four_are_compared(self) -> None:
        from evaluations.cases.schema import load_cases
        from evaluations.runner.comparison import compare_records

        cases = load_cases()
        records = [
            _FakeRecord(
                case.id,
                json.loads((BASELINE_DIR / f"{case.id}.json").read_text(encoding="utf-8"))[
                    "actual_result"
                ],
            )
            if (BASELINE_DIR / f"{case.id}.json").exists()
            else _FakeRecord(case.id, _result())
            for case in cases
        ]

        reports = compare_records(records, cases, BASELINE_DIR)

        compared = [r for r in reports if r.verdict is not Verdict.NO_BASELINE]
        assert len(compared) == 4
        assert {r.verdict for r in compared} == {Verdict.MATCH}


class _FakeRecord:
    """Minimal stand-in for ResultsRecord: only the fields comparison reads."""

    def __init__(self, case_id: str, actual_result: dict) -> None:
        self.case_id = case_id
        self.actual_result = actual_result


class TestRunnerComparisonFlag:
    """``python -m evaluations.runner --compare-to claude``."""

    def test_plain_run_still_returns_zero(self) -> None:
        from evaluations.runner.__main__ import main

        assert main([]) == 0

    def test_compare_to_claude_reports_the_known_mock_live_divergence(self, capsys) -> None:
        """Mock results still differ from the live Claude baselines -- in shape, not geometry.

        The volume divergence this test originally pinned is **fixed**: the mock
        adapter now subtracts cut volume, so plate_centered_hole_success reports
        23.607 on both sides. See tests/test_mock_cut_volume.py.

        What remains is result-shape asymmetry:

        * Mock results omit ``body.operation``; live results carry it.
        * The live spacer baseline omits ``body.plane`` while the live plate
          baseline includes it -- an inconsistency on the live side that only a
          re-capture can settle.

        Both are real and neither is a comparator bug, so the exit code stays
        non-zero. Update this test when the underlying truth changes; do not
        delete it to keep the run green.
        """
        from evaluations.runner.__main__ import main

        exit_code = main(["--compare-to", "claude"])
        out = capsys.readouterr().out

        assert exit_code == 1
        assert "compared=4" in out
        assert "no_baseline=13" in out
        assert "volume:" not in out, "the volume divergence is fixed; it must not reappear"
        assert "operation: None vs baseline" in out

    def test_the_two_failure_baselines_match(self, capsys) -> None:
        """Fail-safely cases compare by classification and do agree."""
        from evaluations.runner.__main__ import main

        main(["--compare-to", "claude"])
        out = capsys.readouterr().out

        assert "bridge_unavailable               match" in out
        assert "invalid_dimensions               match" in out

    def test_no_baseline_does_not_fail_the_run(self, tmp_path, capsys) -> None:
        """11 cases have no baseline; that is not a failure."""
        from evaluations.runner.__main__ import main

        (tmp_path / "empty").mkdir()

        assert main(["--compare-to", "empty"], expected_root=tmp_path) == 0
        assert "no_baseline" in capsys.readouterr().out

    def test_a_mismatch_makes_the_run_exit_non_zero(self, tmp_path, capsys) -> None:
        from evaluations.runner.__main__ import main

        fake = tmp_path / "perturbed"
        fake.mkdir()
        baseline = json.loads(
            (BASELINE_DIR / "spacer_success.json").read_text(encoding="utf-8")
        )
        baseline["actual_result"]["verification"]["actual_width_cm"] = 99.0
        (fake / "spacer_success.json").write_text(json.dumps(baseline), encoding="utf-8")

        exit_code = main(["--compare-to", "perturbed"], expected_root=tmp_path)

        assert exit_code == 1
        assert "mismatch" in capsys.readouterr().out.lower()
