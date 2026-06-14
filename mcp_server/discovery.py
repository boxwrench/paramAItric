"""Fuzzy-intent workflow discovery for ParamAItric (Phase 3, Approach C).

Pure, Fusion-free, deterministic retrieval over workflow metadata "cards". This
module mirrors `mcp_server/selectors.py`: a deterministic core that produces an
*explainable* result, while the host LLM does the final fuzzy match + the
propose-then-confirm dialogue.

Public surface:
  - WorkflowCard (frozen dataclass) — discovery metadata, keyed by workflow name
  - CARDS — the seeded table of cards
  - recommend(intent, constraints, *, limit) -> dict — ranked candidate cards

`recommend` never picks for the user and never builds anything. It returns
structured candidate cards (with schema-valid example_params and honest `not_for`
boundaries) plus a diagnostic match_trace. On no confident match it fails closed:
empty candidates plus the families that *do* exist.

Design note: the spec floated collapsing pipe/tube/conduit as synonyms. We do NOT,
because `tube` and `cylinder` are their own workflows — collapsing would make those
cards fight the clamp card. Only unambiguous synonyms are applied (surface->wall,
bore->hole, light plurals).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowCard:
    """Discovery metadata for one buildable workflow.

    example_params holds only the meaningful dimensions (no output_path / sketch
    names); a test validates them against the workflow's input schema so anything
    the AI proposes is guaranteed to build.
    """

    name: str                  # MUST match a registered workflow (enforced by test)
    family: str                # categorical grouping; the constraint filter key
    summary: str               # one plain-language sentence
    use_when: tuple[str, ...]  # real-world need phrases — the primary match surface
    example_params: dict[str, Any]
    not_for: tuple[str, ...]   # honest boundaries, relayed verbatim


# ---------------------------------------------------------------------------
# Tokenization + synonyms
# ---------------------------------------------------------------------------

_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "to", "of", "for", "with", "and", "or", "i", "need",
    "want", "my", "me", "some", "in", "on", "at", "against", "through", "it",
    "that", "this", "please", "make", "create", "build", "can", "you", "into",
    "is", "be", "as", "by", "from", "one", "single",
})

# variant -> canonical token. Only unambiguous mappings (see module docstring).
_SYNONYMS: dict[str, str] = {
    "surface": "wall",
    "bore": "hole",
    "holes": "hole",
    "mounting": "mount",
    "brackets": "bracket",
    "clamps": "clamp",
    "clamping": "clamp",
    "plates": "plate",
    "rods": "rod",
    "pegs": "peg",
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _canon(word: str) -> str:
    return _SYNONYMS.get(word, word)


def _tokens(text: str) -> set[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords, canonicalize."""
    return {
        _canon(w)
        for w in _WORD_RE.findall(text.lower())
        if w not in _STOPWORDS
    }


def _phrase_tokens(phrases: tuple[str, ...]) -> set[str]:
    terms: set[str] = set()
    for phrase in phrases:
        terms |= _tokens(phrase)
    return terms


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def _score_card(intent: set[str], card: WorkflowCard) -> tuple[float, list[str]]:
    """Return (score in (0,1], matched_on) for a card, or (0.0, []) if no strong match.

    A card only qualifies when at least one intent term hits its `use_when` surface
    (the primary match surface). Summary terms add a weak bonus but cannot, on their
    own, make a card a candidate.
    """
    strong_terms = _phrase_tokens(card.use_when)
    weak_terms = _tokens(card.summary) | {card.family}

    matched_strong = intent & strong_terms
    if not matched_strong:
        return 0.0, []
    matched_weak = (intent & weak_terms) - matched_strong

    denom = 2 * max(len(intent), 1)
    score = (2 * len(matched_strong) + len(matched_weak)) / denom
    score = round(min(score, 1.0), 3)
    matched_on = sorted(matched_strong | matched_weak)
    return score, matched_on


def recommend(
    intent: str,
    constraints: dict[str, Any] | None = None,
    *,
    limit: int = 3,
    cards: tuple[WorkflowCard, ...] | None = None,
) -> dict[str, Any]:
    """Rank workflow cards against a fuzzy intent string. Pure; never builds anything.

    constraints supports the categorical {"family": <str>} filter (a hard gate
    applied before scoring). On no confident match, returns empty candidates and a
    `families` fallback list.
    """
    pool = CARDS if cards is None else cards
    constraints = constraints or {}

    family_filter = constraints.get("family")
    if family_filter is not None:
        pool = tuple(c for c in pool if c.family == family_filter)

    intent_tokens = _tokens(intent)

    scored: list[tuple[float, str, WorkflowCard, list[str]]] = []
    for card in pool:
        score, matched_on = _score_card(intent_tokens, card)
        if score > 0.0:
            scored.append((score, card.name, card, matched_on))

    # Highest score first; stable tie-break by name for determinism.
    scored.sort(key=lambda row: (-row[0], row[1]))
    top = scored[:limit]

    candidates = [
        {
            "name": card.name,
            "family": card.family,
            "summary": card.summary,
            "example_params": dict(card.example_params),
            "not_for": list(card.not_for),
            "score": score,
            "matched_on": matched_on,
        }
        for (score, _name, card, matched_on) in top
    ]

    status = "matched" if candidates else "no_confident_match"
    result: dict[str, Any] = {
        "candidates": candidates,
        "match_trace": {
            "intent_tokens": sorted(intent_tokens),
            "considered": len(pool),
            "returned": len(candidates),
            "status": status,
        },
    }
    if not candidates:
        result["families"] = sorted({c.family for c in (CARDS if cards is None else cards)})
    return result


# ---------------------------------------------------------------------------
# Seeded cards
#
# v1 seeds a representative subset across families. example_params are
# schema-valid (verified by tests/test_discovery.py). Remaining registered
# workflows are intentionally un-carded for now; coverage is tracked by the
# card<->registry consistency test, not silently assumed.
# ---------------------------------------------------------------------------

CARDS: tuple[WorkflowCard, ...] = (
    WorkflowCard(
        name="spacer",
        family="flat_parts",
        summary="A flat rectangular spacer or shim — a simple block of given width, depth, and thickness.",
        use_when=("flat rectangular spacer", "shim or standoff", "flat filler block", "rectangular flat part"),
        example_params={"width_cm": 4.0, "height_cm": 4.0, "thickness_cm": 0.5},
        not_for=("parts that need holes or features — use a plate workflow", "round parts"),
    ),
    WorkflowCard(
        name="plate_with_hole",
        family="flat_parts",
        summary="A flat plate with a single through hole at a chosen position.",
        use_when=("flat plate with a hole", "drilled flat plate", "panel with a bolt hole"),
        example_params={
            "width_cm": 8.0, "height_cm": 6.0, "thickness_cm": 0.5,
            "hole_diameter_cm": 1.0, "hole_center_x_cm": 4.0, "hole_center_y_cm": 3.0,
        },
        not_for=("more than one hole — use two_hole_plate or four_hole_mounting_plate", "round parts"),
    ),
    WorkflowCard(
        name="two_hole_plate",
        family="flat_parts",
        summary="A flat plate with two mirrored mounting holes.",
        use_when=("flat plate with two holes", "two hole mounting strip", "bar with a pair of bolt holes"),
        example_params={
            "width_cm": 10.0, "height_cm": 6.0, "thickness_cm": 0.5,
            "hole_diameter_cm": 1.0, "edge_offset_x_cm": 1.5, "hole_center_y_cm": 3.0,
        },
        not_for=("a single hole — use plate_with_hole", "four-hole patterns — use four_hole_mounting_plate"),
    ),
    WorkflowCard(
        name="cylinder",
        family="cylindrical",
        summary="A solid round cylinder — a rod, peg, or dowel of given diameter and height.",
        use_when=("solid round rod", "cylindrical peg or dowel", "round bar stock"),
        example_params={"diameter_cm": 3.0, "height_cm": 5.0},
        not_for=("hollow parts — use tube", "tapered parts — use revolve"),
    ),
    WorkflowCard(
        name="tube",
        family="cylindrical",
        summary="A hollow round tube — an outer cylinder with a centered bore through it.",
        use_when=("hollow tube", "round pipe with a bore", "sleeve or bushing tube"),
        example_params={"outer_diameter_cm": 4.0, "inner_diameter_cm": 2.5, "height_cm": 5.0},
        not_for=("solid parts — use cylinder", "a flange — use flanged_bushing"),
    ),
    WorkflowCard(
        name="bracket",
        family="brackets",
        summary="A plain L-shaped right-angle bracket with two legs.",
        use_when=("L bracket", "right angle bracket", "corner brace"),
        example_params={"width_cm": 5.0, "height_cm": 5.0, "thickness_cm": 0.4, "leg_thickness_cm": 0.6},
        not_for=("brackets with mounting holes — use mounting_bracket", "rounded or chamfered edges"),
    ),
    WorkflowCard(
        name="mounting_bracket",
        family="brackets",
        summary="An L-bracket with one mounting hole through a leg.",
        use_when=("L bracket with a mounting hole", "angle bracket with a bolt hole", "screw down corner bracket"),
        example_params={
            "width_cm": 5.0, "height_cm": 5.0, "thickness_cm": 0.4, "leg_thickness_cm": 1.0,
            "hole_diameter_cm": 0.5, "hole_center_x_cm": 0.5, "hole_center_y_cm": 2.5,
        },
        not_for=("two holes — use two_hole_mounting_bracket", "plain brackets — use bracket"),
    ),
    WorkflowCard(
        name="pipe_clamp_half",
        family="clamps",
        summary="One half of a two-piece clamp that wraps a round pipe and bolts to a flat wall.",
        use_when=("hold a pipe to a wall", "secure conduit or tubing", "pipe mount", "clamp round pipe"),
        example_params={
            "clamp_width_cm": 6.0, "clamp_length_cm": 4.0, "clamp_height_cm": 3.0,
            "pipe_outer_diameter_cm": 2.5, "bolt_hole_diameter_cm": 0.6,
            "bolt_hole_edge_offset_x_cm": 0.8, "bolt_hole_center_y_cm": 2.0,
        },
        not_for=("square or rectangular tube", "a complete clamp alone — you build two halves",
                 "load-bearing structural pipe supports"),
    ),
)
