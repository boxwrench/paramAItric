"""Tests for the fuzzy-intent workflow discovery layer (mcp_server/discovery.py).

Pure / Fusion-free, mirroring tests/test_selectors.py. Covers:
  - intent -> workflow ranking (the core value)
  - synonym canonicalization (surface->wall, bore->hole)
  - constraints-as-filters
  - fail-closed "no_confident_match" with a families fallback
  - card<->registry consistency (no card names a non-existent workflow)
  - example_params are schema-valid (anything proposed actually builds)
  - the recommend_workflow server method + tool registration
"""
from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir

import pytest

from mcp_server.discovery import CARDS, WorkflowCard, recommend


# ---------------------------------------------------------------------------
# Ranking — intent maps to the right workflow
# ---------------------------------------------------------------------------

def test_pipe_wall_intent_ranks_pipe_clamp_first():
    result = recommend("I need to hold a pipe to a wall")
    assert result["candidates"], "expected at least one candidate"
    assert result["candidates"][0]["name"] == "pipe_clamp_half"
    assert result["match_trace"]["status"] == "matched"


def test_flat_spacer_intent_ranks_spacer_first():
    result = recommend("a flat spacer block")
    assert result["candidates"][0]["name"] == "spacer"


def test_candidate_includes_example_params_and_boundaries():
    top = recommend("hold a pipe to a wall")["candidates"][0]
    assert isinstance(top["example_params"], dict) and top["example_params"]
    assert top["not_for"], "candidate must relay honest boundaries"
    assert 0.0 < top["score"] <= 1.0
    assert top["matched_on"], "candidate must report what it matched on"


def test_results_limited_to_requested_count():
    result = recommend("flat plate with a hole", limit=2)
    assert len(result["candidates"]) <= 2


# ---------------------------------------------------------------------------
# Synonym canonicalization
# ---------------------------------------------------------------------------

def test_surface_is_treated_as_wall():
    # "surface" appears in no card; it must canonicalize to "wall" to match.
    result = recommend("fasten a pipe against a surface")
    assert result["candidates"][0]["name"] == "pipe_clamp_half"
    assert "wall" in result["candidates"][0]["matched_on"]


def test_bore_is_treated_as_hole():
    # "bore" must canonicalize to "hole" so a bored part matches hole workflows.
    result = recommend("a part with a bore")
    assert result["candidates"], "bore should match hole-bearing workflows"
    assert "hole" in result["candidates"][0]["matched_on"]


# ---------------------------------------------------------------------------
# Constraints as filters (hard gate, not scored away)
# ---------------------------------------------------------------------------

def test_family_constraint_restricts_pool():
    result = recommend("a part", constraints={"family": "clamps"})
    assert all(c["family"] == "clamps" for c in result["candidates"])


def test_family_constraint_excludes_other_families():
    # "flat plate" would normally match plate workflows, but a clamps filter excludes them.
    result = recommend("flat plate with a hole", constraints={"family": "clamps"})
    assert all(c["family"] == "clamps" for c in result["candidates"])
    assert "plate_with_hole" not in {c["name"] for c in result["candidates"]}


# ---------------------------------------------------------------------------
# Fail-closed on no confident match
# ---------------------------------------------------------------------------

def test_nonsense_intent_returns_no_confident_match_with_families():
    result = recommend("xyzzy quux flibbertigibbet")
    assert result["candidates"] == []
    assert result["match_trace"]["status"] == "no_confident_match"
    assert result["families"], "must offer the families that DO exist"


def test_match_trace_reports_intent_tokens_and_counts():
    result = recommend("hold a pipe to a wall")
    trace = result["match_trace"]
    assert "pipe" in trace["intent_tokens"]
    assert trace["considered"] >= 1
    assert trace["returned"] == len(result["candidates"])


# ---------------------------------------------------------------------------
# Card <-> registry consistency
# ---------------------------------------------------------------------------

def test_every_card_names_a_registered_workflow():
    from mcp_server.workflow_registry import build_default_registry

    registered = {w.name for w in build_default_registry().list()}
    for card in CARDS:
        assert card.name in registered, f"card {card.name!r} is not a registered workflow"


def test_card_names_are_unique():
    names = [c.name for c in CARDS]
    assert len(names) == len(set(names))


def test_cards_cover_multiple_families():
    families = {c.family for c in CARDS}
    assert {"flat_parts", "cylindrical", "brackets", "clamps"} <= families


# ---------------------------------------------------------------------------
# example_params are schema-valid -> anything proposed actually builds
# ---------------------------------------------------------------------------

# Map seeded card names to their input schema. The schema-validity test injects a
# throwaway allowlisted output_path; example_params hold only meaningful dimensions.
def _schema_for(name: str):
    from mcp_server.schemas import (
        CreateSpacerInput,
        CreatePlateWithHoleInput,
        CreateTwoHolePlateInput,
        CreateCylinderInput,
        CreateTubeInput,
        CreateBracketInput,
        CreateMountingBracketInput,
        CreatePipeClampHalfInput,
    )
    return {
        "spacer": CreateSpacerInput,
        "plate_with_hole": CreatePlateWithHoleInput,
        "two_hole_plate": CreateTwoHolePlateInput,
        "cylinder": CreateCylinderInput,
        "tube": CreateTubeInput,
        "bracket": CreateBracketInput,
        "mounting_bracket": CreateMountingBracketInput,
        "pipe_clamp_half": CreatePipeClampHalfInput,
    }[name]


def test_example_params_validate_against_schema():
    out = str(Path(gettempdir()) / "discovery_probe.stl")
    for card in CARDS:
        schema = _schema_for(card.name)
        # Should not raise: the seeded dims satisfy every cross-field constraint.
        schema.from_payload({**card.example_params, "output_path": out})


# ---------------------------------------------------------------------------
# Server method + tool registration
# ---------------------------------------------------------------------------

def test_server_recommend_workflow_passthrough():
    from mcp_server.server import ParamAIToolServer

    server = ParamAIToolServer()
    result = server.recommend_workflow({"intent": "hold a pipe to a wall"})
    assert result["candidates"][0]["name"] == "pipe_clamp_half"


def test_recommend_workflow_registered_as_tool():
    from mcp_server.tool_specs import ALL_TOOLS

    assert "recommend_workflow" in ALL_TOOLS
    assert ALL_TOOLS["recommend_workflow"].method == "recommend_workflow"
