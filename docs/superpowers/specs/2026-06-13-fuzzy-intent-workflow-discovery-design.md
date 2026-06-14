# Fuzzy-Intent Workflow Discovery — Design

**Date:** 2026-06-13
**Status:** Design approved; pending implementation plan.
**Scope owner decision:** Approach C (hybrid: enriched metadata cards + a deterministic
`recommend_workflow` tool; the LLM makes the final fuzzy match and proposes-then-confirms).

---

## Problem

The "using it once installed" experience is mediated entirely through the AI chat (ParamAItric
has no GUI yet — UI is roadmap Phase 4). The weakest moment in that loop is **discovery**: a user
does not know what they can ask for, and the AI is matching fuzzy human requests against a thin
catalog.

Today the discovery surface is:
- `WorkflowDefinition` (frozen dataclass: `name`, `intent`, `stages`, `extension_of`) — `intent`
  is a developer-flavored sentence with no examples, synonyms, boundaries, or parameter hints.
- ~15 `create_*` MCP tools, each with a terse one-line description.
- A `workflow_catalog` tool whose own description is *"Return the list of workflows registered in
  the Fusion add-in."*

There are no example dimensions, no "when to use this," no honest boundaries, and the human sees
no menu at all.

## Goal (the experience to build)

A user describes a need loosely (e.g. *"something to hold a pipe to a wall"*) → the AI confidently
maps it to the right workflow **and** realistic starting dimensions → **proposes and waits for
confirmation** → builds on the user's go-ahead.

Two halves: (1) pick the right *workflow*; (2) seed *sensible starting dimensions*.

**Interaction contract:** propose-then-confirm (chosen to honor the "keep the user in control"
principle). The AI never auto-builds from a fuzzy match.

## Why Approach C

- **A (enriched catalog, LLM does everything):** lightest, but puts the whole decision in the
  non-deterministic layer the project deliberately distrusts. Too loose for a reliability-first
  product.
- **B (server-side ranking is the arbiter):** most deterministic, but a naive keyword ranker is
  often *worse* than the LLM at fuzzy intent, and doing it well implies embeddings — a new runtime
  dependency, against current planning rules.
- **C (hybrid — chosen):** deterministic, testable *facts* (candidate set, exact example params,
  real boundaries) feed an *explainable* decision; the LLM does the one thing it is reliably good
  at (fuzzy language matching + natural-language proposal). This is the same split that just worked
  for `selectors.py`: a deterministic core feeding an explainable choice, without forcing a
  linguistic task to be fully deterministic.

## Architecture

`recommend_workflow` is pure reasoning over metadata — it never touches geometry — so it lives
**MCP-side and does NOT route through the Fusion bridge.** It mirrors `mcp_server/selectors.py`:
a pure, Fusion-free, fully unit-testable module.

```
mcp_server/discovery.py        ← NEW pure module (mirrors selectors.py)
    WorkflowCard               ← discovery metadata, keyed by workflow name
    CARDS                      ← the table of cards
    recommend(intent, constraints) -> ranked candidate cards   ← deterministic retrieval

mcp_server/tool_specs.py + mcp_entrypoint.py
    recommend_workflow         ← NEW MCP tool; calls discovery.recommend (no bridge call)
```

The existing `workflow_catalog` deliberately reflects *what the add-in actually has registered*
(ground truth for "what can run"). Discovery metadata is a richer **overlay** keyed to those same
names, kept honest by a test asserting every card name is a registered workflow — so the overlay
can never recommend something that cannot be built.

## Data model

```python
@dataclass(frozen=True)
class WorkflowCard:
    name: str                 # MUST match a registered workflow (enforced by test)
    family: str               # "clamps" | "brackets" | "enclosures" | "flat_parts" | "cylindrical" ...
    summary: str              # one plain-language sentence a non-engineer understands
    use_when: tuple[str, ...] # real-world need phrases + synonyms — the match surface
    example_params: dict      # a realistic, SCHEMA-VALID starting param set (enforced by test)
    not_for: tuple[str, ...]  # honest boundaries — relayed verbatim so the AI won't over-promise
```

Example:

```python
WorkflowCard(
    name="pipe_clamp_half",
    family="clamps",
    summary="One half of a two-piece clamp that wraps a round pipe and bolts to a flat surface.",
    use_when=("hold a pipe to a wall", "secure conduit or tubing", "pipe mount", "clamp round stock"),
    example_params={"bore_diameter_mm": 25.0, "band_width_mm": 20.0,
                    "wall_thickness_mm": 4.0, "bolt_hole_diameter_mm": 6.0},
    not_for=("square or rectangular tube", "a complete clamp on its own — you build two halves",
             "load-bearing structural pipe supports"),
)
```

Two deliberate, ParamAItric-flavored guardrails (the *facts* are deterministic; only the *match*
is fuzzy):

- **`example_params` is the seed for "sensible starting dimensions."** A test validates each card's
  `example_params` against that workflow's Pydantic schema, so anything the AI proposes is
  guaranteed to actually build. Hand-seeded now; real numbers can later be drawn from
  `reference_parts/` specs (Phase 3c hook, out of scope here).
- **`not_for` makes "honest boundaries" data, not vibes.** Even though the headline goal is fuzzy
  matching, carrying boundaries cheaply prevents the AI from confidently proposing the *wrong*
  match — the failure mode that erodes trust fastest.

## The `recommend_workflow` tool

**Signature:** `recommend_workflow(intent: str, constraints: dict | None = None) -> dict`

**Ranking — deterministic, stdlib only (no embeddings):**
1. Normalize `intent` to lowercase tokens (strip punctuation, drop stopwords).
2. Score each card by weighted term overlap against `use_when` (highest weight), `summary`, and
   `family`. A small built-in synonym map collapses obvious variants (pipe/tube/conduit, hole/bore,
   wall/surface).
3. Apply `constraints` as **filters, not scores** — a hard gate so a constraint cannot be scored
   away. v1 supports the categorical `{"family": "clamps"}` filter only (unambiguous against the
   card's `family` field). Numeric/range constraints (e.g. max bore) are deferred: cards do not yet
   declare queryable parameter ranges, only an `example_params` seed, so range filtering would be
   ambiguous. Add it alongside the Phase 3c reference-catalog work.
4. Return the top *N* (default 3) above a minimum threshold.

**Output — structured candidate cards the AI relays (it does NOT auto-pick):**
```json
{
  "candidates": [
    {"name": "pipe_clamp_half", "family": "clamps", "summary": "...",
     "example_params": {"...": "..."}, "not_for": ["..."],
     "score": 0.82, "matched_on": ["pipe", "wall"]}
  ],
  "match_trace": {"intent_tokens": ["hold", "pipe", "wall"], "considered": 15,
                  "returned": 1, "status": "matched"}
}
```

**Fail-closed on no confident match** (same instinct as the selector layer): if nothing clears the
threshold, return `candidates: []` with `match_trace.status: "no_confident_match"` and a `families`
list of what *does* exist. The AI then says *"I'm not sure I have a workflow for that — here are the
families I can build"* rather than forcing a bad pick. `matched_on` / `match_trace` is the discovery
analogue of `SelectionTrace`: explainable, diagnostic, not a gate.

## Interaction flow (propose-then-confirm)

Anchored by a short `BEST_PRACTICES.md` addition so any host model follows it:

1. Fuzzy request → AI calls `recommend_workflow`.
2. AI presents the top candidate(s): *"I think you want a `pipe_clamp_half` — ~25 mm bore, 20 mm
   band, bolts to a flat surface. Note: it's one of two halves, and not for square tube. Build it
   with these dims?"*
3. **AI waits.** On confirmation (and any dimension tweaks) → calls `create_pipe_clamp_half`.

The deterministic tool supplies the rails (which candidates, exact example params, real
boundaries); the LLM does the fuzzy final selection and the natural-language proposal.

## Verification & tests

All pure / Fusion-free, in the normal suite (mirrors `selectors.py` coverage):

1. **Card↔registry consistency** — every `WorkflowCard.name` is a registered workflow; flag any
   buildable `create_*` workflow with no card (coverage gaps visible, not silent).
2. **`example_params` are schema-valid** — each card's `example_params` validates against that
   workflow's Pydantic schema (the guarantee that anything proposed actually builds).
3. **Ranking unit tests** — known intents resolve to the expected top candidate ("hold a pipe to a
   wall" → `pipe_clamp_half`); constraints filter correctly; below-threshold intent returns
   `no_confident_match` with a non-empty `families` list.
4. **Synonym map tests** — pipe/tube/conduit, hole/bore collapse as intended.

## Scope boundaries

**In scope:** `mcp_server/discovery.py` (cards + `recommend`); the `recommend_workflow` MCP tool;
hand-seeded cards for the existing workflows; the `BEST_PRACTICES.md` propose-then-confirm note;
the four test groups above.

**Explicitly out (YAGNI / later phases):**
- Embeddings / semantic search — stdlib keyword scoring only.
- Auto-build — propose-then-confirm only.
- Full `workflow_catalog` enrichment (Phase 3a) — cards could back it later, not now.
- Reference-catalog sourcing of dims from `reference_parts/` (Phase 3c) — `example_params`
  hand-seeded for now.

## Sequencing note

This is roadmap **Phase 3** work (Intake & Workflow Discovery: enrich `workflow_catalog`, add
`recommend_workflow`), which the 2026-04-08 pivot deliberately placed *after* Phase 1 geometry
foundations. The design is ready whenever wanted; building it now pulls Phase 3 ahead of finishing
Phase 1. That is a planning-time call — this spec flags it rather than assuming it. See
`docs/NEXT_PHASE_PLAN.md` Phase 3 and `docs/dev-log.md`.
