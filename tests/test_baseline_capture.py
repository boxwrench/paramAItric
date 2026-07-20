"""Tests for the baseline capture driver (goal G3).

Covers the ``baseline_required`` designation, the per-case capture checklist
generator, and the validator that guards hand-captured baselines in
``evaluations/expected/``.
"""

from __future__ import annotations

import pytest

from evaluations.baseline import (
    REQUIRED_BASELINE_FIELDS,
    REQUIRED_METADATA_FIELDS,
    missing_baselines,
    render_checklist,
    validate_baseline,
    validate_directory,
    main,
    write_checklists,
)
from evaluations.cases.schema import EvaluationCase, Tier, load_cases


def _minimal_case_dict(**overrides) -> dict:
    """Return a minimal valid case payload, with optional field overrides."""
    payload = {
        "id": "example_case",
        "tier": "contract",
        "disposition": "succeed",
        "original_request": "Make a 4 cm spacer.",
        "expected_workflow": "spacer",
        "required_measurements": ["width_cm"],
        "expected_tool_call": "create_spacer",
        "arguments": {"width_cm": 4.0},
        "expected_normalized_arguments": {},
        "expected_verification_facts": {},
        "expected_export_type": "stl",
        "expected_error": None,
    }
    payload.update(overrides)
    return payload


class TestBaselineRequiredField:
    """``baseline_required`` marks a case as needing a hand-captured baseline."""

    def test_defaults_to_false_when_absent(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict())

        assert case.baseline_required is False

    def test_reads_true_when_present(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict(baseline_required=True))

        assert case.baseline_required is True

    def test_is_independent_of_tier(self) -> None:
        """A contract-tier case may still require a live baseline.

        The two axes are separate: ``tier`` decides how a case executes,
        ``baseline_required`` decides whether it needs a captured reference.
        ``expected/claude/spacer_success.json`` is exactly this combination.
        """
        case = EvaluationCase.from_dict(
            _minimal_case_dict(tier="contract", baseline_required=True)
        )

        assert case.tier is Tier.CONTRACT
        assert case.baseline_required is True


class TestBaselineRequiredCases:
    """The six representative parts named in ROADMAP.md tier 2."""

    EXPECTED = {
        "spacer_success",
        "plate_centered_hole_success",
        "tube_success",
        "bracket_success",
        "filleted_bracket_success",
        "enclosure_success",
    }

    def test_exactly_the_six_representative_parts_are_marked(self) -> None:
        cases = load_cases()
        marked = {case.id for case in cases if case.baseline_required}

        assert marked == self.EXPECTED

    def test_marking_does_not_change_any_tier(self) -> None:
        """Guards the coverage regression that re-tiering would have caused."""
        cases = load_cases()
        tiers = {case.tier for case in cases}

        assert tiers == {Tier.CONTRACT, Tier.SAFETY}
        assert len([c for c in cases if c.tier is Tier.CONTRACT]) == 8
        assert len([c for c in cases if c.tier is Tier.SAFETY]) == 9


class TestRenderChecklist:
    """Checklists are derived from the case, so the two cannot drift apart."""

    def test_carries_the_request_verbatim(self) -> None:
        case = EvaluationCase.from_dict(
            _minimal_case_dict(original_request="Print me a spacer 40 mm square.")
        )

        assert "Print me a spacer 40 mm square." in render_checklist(case)

    def test_lists_every_required_measurement(self) -> None:
        case = EvaluationCase.from_dict(
            _minimal_case_dict(required_measurements=["width", "height", "thickness"])
        )

        checklist = render_checklist(case)

        for measurement in ("width", "height", "thickness"):
            assert measurement in checklist

    def test_names_the_expected_workflow_and_tool(self) -> None:
        case = EvaluationCase.from_dict(
            _minimal_case_dict(expected_workflow="spacer", expected_tool_call="create_spacer")
        )

        checklist = render_checklist(case)

        assert "spacer" in checklist
        assert "create_spacer" in checklist

    def test_lists_every_field_the_baseline_must_record(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict())

        checklist = render_checklist(case)

        for field in REQUIRED_BASELINE_FIELDS:
            assert field in checklist, f"checklist omits required field {field}"

    def test_warns_against_inventing_numbers(self) -> None:
        """BASELINE_CAPTURE.md's central rule must survive into every checklist."""
        checklist = render_checklist(EvaluationCase.from_dict(_minimal_case_dict()))

        assert "invent" in checklist.lower()

    def test_reflects_edited_case_without_code_change(self) -> None:
        """The anti-drift property: change the case, the checklist follows."""
        original = render_checklist(EvaluationCase.from_dict(_minimal_case_dict()))
        edited = render_checklist(
            EvaluationCase.from_dict(_minimal_case_dict(original_request="Something else."))
        )

        assert original != edited
        assert "Something else." in edited


class TestMissingBaselines:
    """Which cases still need a hand-captured Claude baseline."""

    def test_identifies_cases_with_no_baseline_file(self, tmp_path) -> None:
        cases = [
            EvaluationCase.from_dict(_minimal_case_dict(id="has_baseline")),
            EvaluationCase.from_dict(_minimal_case_dict(id="needs_baseline")),
        ]
        (tmp_path / "has_baseline.json").write_text("{}", encoding="utf-8")

        missing = missing_baselines(cases, tmp_path)

        assert [case.id for case in missing] == ["needs_baseline"]

    def test_empty_when_every_case_is_covered(self, tmp_path) -> None:
        cases = [EvaluationCase.from_dict(_minimal_case_dict(id="covered"))]
        (tmp_path / "covered.json").write_text("{}", encoding="utf-8")

        assert missing_baselines(cases, tmp_path) == []

    def test_real_repo_has_thirteen_cases_awaiting_capture(self) -> None:
        """17 cases, 4 captured baselines."""
        missing = missing_baselines(load_cases())

        assert len(missing) == 13


def _valid_baseline(case_id: str = "example_case", **overrides) -> dict:
    """Return a well-formed baseline payload for ``case_id``."""
    payload: dict = {name: "recorded" for name in REQUIRED_BASELINE_FIELDS}
    payload["metadata"] = {name: "recorded" for name in REQUIRED_METADATA_FIELDS}
    payload["metadata"]["evaluation_case"] = case_id
    payload["case_id"] = case_id
    payload["tier"] = "contract"
    payload["disposition"] = "succeed"
    payload.update(overrides)
    return payload


class TestValidateBaseline:
    """A malformed or inconsistent baseline must be rejected, not absorbed."""

    def test_accepts_a_well_formed_baseline(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict())

        result = validate_baseline(_valid_baseline(), case)

        assert result.ok
        assert result.problems == []

    @pytest.mark.parametrize("omitted", REQUIRED_BASELINE_FIELDS)
    def test_rejects_a_missing_top_level_field(self, omitted: str) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict())
        payload = _valid_baseline()
        del payload[omitted]

        result = validate_baseline(payload, case)

        assert not result.ok
        assert any(omitted in problem for problem in result.problems)

    def test_rejects_incomplete_reproducibility_metadata(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict())
        payload = _valid_baseline()
        del payload["metadata"]["model"]

        result = validate_baseline(payload, case)

        assert not result.ok
        assert any("model" in problem for problem in result.problems)

    def test_rejects_metadata_that_is_not_an_object(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict())

        result = validate_baseline(_valid_baseline(metadata="nope"), case)

        assert not result.ok

    def test_rejects_a_baseline_naming_a_different_case(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict(id="example_case"))

        result = validate_baseline(_valid_baseline(case_id="some_other_case"), case)

        assert not result.ok
        assert any("some_other_case" in problem for problem in result.problems)

    def test_rejects_a_tier_disagreeing_with_the_case(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict(tier="contract"))

        result = validate_baseline(_valid_baseline(tier="safety"), case)

        assert not result.ok
        assert any("tier" in problem for problem in result.problems)

    def test_rejects_a_disposition_disagreeing_with_the_case(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict(disposition="succeed"))

        result = validate_baseline(_valid_baseline(disposition="fail_safely"), case)

        assert not result.ok
        assert any("disposition" in problem for problem in result.problems)

    def test_reports_every_problem_not_just_the_first(self) -> None:
        case = EvaluationCase.from_dict(_minimal_case_dict())
        payload = _valid_baseline(case_id="wrong", tier="safety")

        result = validate_baseline(payload, case)

        assert len(result.problems) >= 2


class TestValidateDirectory:
    """Directory-level validation over captured baselines."""

    def test_skips_cases_with_no_baseline_file(self, tmp_path) -> None:
        cases = [EvaluationCase.from_dict(_minimal_case_dict(id="absent"))]

        assert validate_directory(cases, tmp_path) == []

    def test_reports_invalid_json_rather_than_raising(self, tmp_path) -> None:
        cases = [EvaluationCase.from_dict(_minimal_case_dict(id="broken"))]
        (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")

        results = validate_directory(cases, tmp_path)

        assert len(results) == 1
        assert not results[0].ok

    def test_the_four_existing_baselines_all_pass(self) -> None:
        """The real criterion: this must hold against the repo as it stands."""
        results = validate_directory(load_cases())

        assert len(results) == 4
        failures = {r.case_id: r.problems for r in results if not r.ok}
        assert failures == {}


class TestWriteChecklists:
    """Emitting checklists for the cases still awaiting capture."""

    def test_writes_one_file_per_case(self, tmp_path) -> None:
        cases = [
            EvaluationCase.from_dict(_minimal_case_dict(id="alpha")),
            EvaluationCase.from_dict(_minimal_case_dict(id="beta")),
        ]

        written = write_checklists(cases, tmp_path)

        assert {p.name for p in written} == {"alpha.md", "beta.md"}
        assert (tmp_path / "alpha.md").read_text(encoding="utf-8").startswith("#")

    def test_creates_the_output_directory(self, tmp_path) -> None:
        target = tmp_path / "nested" / "checklists"
        cases = [EvaluationCase.from_dict(_minimal_case_dict(id="alpha"))]

        write_checklists(cases, target)

        assert (target / "alpha.md").exists()

    def test_content_matches_render_checklist(self, tmp_path) -> None:
        """Files on disk are exactly the rendered checklist, no second code path."""
        case = EvaluationCase.from_dict(_minimal_case_dict(id="alpha"))

        write_checklists([case], tmp_path)

        assert (tmp_path / "alpha.md").read_text(encoding="utf-8") == render_checklist(case)

    def test_refuses_to_write_into_the_expected_directory(self, tmp_path) -> None:
        """Structural guard: this tool must never author baseline content."""
        cases = [EvaluationCase.from_dict(_minimal_case_dict(id="alpha"))]
        forbidden = tmp_path / "expected" / "claude"

        with pytest.raises(ValueError, match="expected"):
            write_checklists(cases, forbidden)

        assert not forbidden.exists()


class TestCommandLine:
    """``python -m evaluations.baseline``."""

    def test_validate_succeeds_against_the_real_repo(self, capsys) -> None:
        assert main(["--validate"]) == 0

    def test_write_checklists_emits_one_file_per_missing_case(self, tmp_path) -> None:
        exit_code = main(["--write-checklists", str(tmp_path)])

        assert exit_code == 0
        assert len(list(tmp_path.glob("*.md"))) == 13

    def test_status_reports_without_writing_anything(self, tmp_path, capsys) -> None:
        assert main(["--status"]) == 0

        out = capsys.readouterr().out
        assert "13" in out
