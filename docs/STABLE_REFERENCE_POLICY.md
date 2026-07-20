# Stable Reference Policy

> Status: **ADOPTED 2026-07-19.** Required by `ROADMAP.md` Stage 2; specifies goal G5
> (attribute pinning) in [`plans/goals.md`](../plans/goals.md).

## Why this document exists

`mcp_server/selectors.py` resolves a *descriptor* (target / kind / scope / expect / params /
pin) against the faces and edges of a body, returning a result plus a `SelectionTrace`.
Today resolution is purely **semantic**: every call re-runs the filters and re-ranks the
candidate pool from scratch.

`validate_descriptor` already accepts a `pin` field and normalizes it, but line 243 notes it
is reserved and unused. Pinning would let a selection be recorded once and re-resolved later
by stored attributes rather than re-running the semantic query.

Both strategies fail differently, and the failures matter:

| Strategy | Fails when | Failure mode |
|---|---|---|
| **Re-resolve semantically** | Topology changed such that a *different* face now best matches | Silent — you get a valid selection of the wrong face |
| **Pin to attributes** | Topology changed such that the pinned face no longer matches | Loud — the pin does not resolve |

The dangerous one is the silent case. A fillet applied to "the largest planar face" after an
earlier cut changed which face is largest produces geometry that is wrong but passes every
structural check.

## The four available behaviors

- **Re-resolve semantically** — re-run the query, take today's answer.
- **Pin** — store distinguishing attributes at selection time, match against them later.
- **Bookmark** — record the resolved entity token and reuse it directly.
- **Hard-fail** — refuse to proceed, return a structured error, require the caller to
  re-select explicitly.

## Decision

**The governing principle: pinning is an opt-in assertion of stability, and once asserted it
is never silently downgraded.** A pin is the caller stating "this specific geometry must
still be there." If it isn't, the correct answer is an error — not a guess that happens to
be plausible.

### 1. Default — no pin present

**Re-resolve semantically, always.** Absence of a pin means the caller never asked for
stability, so they get today's best semantic answer. This is current behavior, so pinning
lands as a purely additive change and none of the existing workflows shift.

### 2. Stale pin — matches nothing

**Hard-fail, unconditionally.** No fallback to semantic resolution, under any operation,
mutating or not.

A stale pin means the recorded geometry is gone. Re-resolving at that point is guessing, and
a confident wrong face is the one failure this whole mechanism exists to prevent. This
follows `ROADMAP.md`'s rule that safety failures are zero-tolerance while pass thresholds are
tunable.

The failure is a structured error, consistent with the rest of the server: a classification,
the stale pin's recorded attributes, what was found instead, and a `next_step` directing the
caller to re-select explicitly. It is never a traceback and never a partial result.

The accepted cost: a long multi-stage workflow can halt on a pin that drifted for a benign
reason. That is deliberate. These workflows are deterministic recipes, not exploratory
sessions — if a pinned reference moved, the recipe is genuinely wrong, and halting is the
point rather than the price.

### 3. Ambiguous pin — matches more than one candidate

**Raise the existing `SelectorAmbiguityError`, with a distinct `SelectionTrace` status.**

Reusing the exception type means no consumer of `resolve()` needs a second error path.
Distinguishing the trace status separates two genuinely different problems, and therefore two
different `next_step` messages:

| Trace status | Meaning | Guidance to caller |
|---|---|---|
| `ambiguous` | The semantic query is too broad | Narrow the descriptor |
| `pin_ambiguous` | Pinned geometry was duplicated by a topology change | Re-select; the model changed under you |

### 4. Who pins

**The caller opts in, per descriptor.** `validate_descriptor` already accepts and normalizes
`pin` — the interface was built for this. Workflow authors decide where stability matters.

No auto-pinning. It would require the selector to understand stage lifetime (which it does
not) and would change behavior everywhere at once rather than where a human judged it
necessary.

## Consequences for implementation

- **There is no fallback branch.** Decisions 1, 2 and 4 together mean a descriptor either has
  a pin (strict) or does not (semantic). No code path re-resolves a pin semantically, so no
  such path should be written "just in case."
- **`SelectionTrace` gains pin visibility** — whether a pin was present, whether it resolved,
  and on failure what changed. Diagnostic quality is an explicit roadmap progress metric, and
  a hard-fail policy is only tolerable if the failure explains itself.
- **Two new trace statuses**: `pin_stale` and `pin_ambiguous`, alongside the existing
  `resolved` / `ambiguous` / `empty` / `error`.
- **Bookmarking is not adopted.** Storing raw entity tokens for later reuse is not part of
  this policy; pins match on recorded attributes, not identity.
