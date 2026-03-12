# Verification Policy

This note defines the adopted verification trust model for ParamAItric.

It exists to keep "verification" from collapsing into one undifferentiated bucket of checks.
Different signals have different trust, cost, and stability.
The live validation runbook (adopted smokes, checklist, scope boundary, failure rules) is in [Adopted Live Scope](#adopted-live-scope).

## Core Rule

Verification must be provenance-aware.

Every verification signal should be understood in terms of:

- what produced it
- what accuracy or approximation mode it depends on
- how stable it is under topology and timeline change
- whether it is safe for runtime gating or only for audits

For ParamAItric, the important split is:

- exact kernel-backed facts
- exact but context-sensitive facts
- approximate geometric estimates
- heuristic or inferred signals

Do not promote a weaker signal into a hard gate just because it is easy to compute.

## Adopted Tiers

### Tier 0: Hard Gates

Use these to block progression in runtime loops.

Current intended use:

- feature error states when exposed reliably
- required entity-binding validity
- explicit structural delta assertions such as expected body count
- manifest-declared envelope or safety constraints

Properties:

- cheap
- replay-safe
- deterministic enough to trust in guided freeform

### Tier 1: Audit Checks

Use these for stronger end-state confidence and compliance review.

Typical examples:

- stronger envelope checks
- explicit-accuracy physical properties
- selective clearance checks
- interference checks
- final compliance against manifest intent

Properties:

- stronger than Tier 0
- often more expensive
- sometimes more context-sensitive

### Tier 2: Diagnostics

Use these to guide recovery, debugging, and regression triage.

Typical examples:

- face count
- edge count
- face-type distributions
- centroid drift heuristics
- coarse bounding boxes
- screenshots and visual impressions

Properties:

- useful
- often topology-fragile or weakly semantic
- not safe as correctness proofs on their own

## Current Repo Stance

Structured workflows and guided freeform should both use the same trust model, but not the same gate density.

- structured workflows
  - can promote more checks into Tier 0 when the workflow defines a narrow deterministic measurement context
- guided freeform
  - should keep Tier 0 smaller and more replay-safe
  - should rely on audits and diagnostics for richer understanding

## Immediate Implementation Direction

Near-term implementation should do these first:

1. expose verification signals explicitly in verification results
2. record each signal's tier, provenance, accuracy note, and pass/fail status
3. keep existing body-count and delta assertions, but stop treating them as the whole verification story
4. add feature-health hard gating only where the bridge can expose it reliably
5. keep topology-fragile counts diagnostic unless a workflow proves a narrower use

## Practical Rule

If a check is:

- cheap, deterministic, and replay-safe
  - it is a Tier 0 candidate
- strong but more expensive or context-sensitive
  - it belongs in Tier 1
- useful mostly for explanation, debugging, or weak correlation
  - it belongs in Tier 2

## Live Lessons

The March 11 live smokes added a few operational rules that matter in practice:

- verification failure is a structured result, not an exception path
- recovery logic must read `ok: false` and inspect returned `verification_signals`
- negative smokes should use deterministic, already-proven geometry steps
- live-adopted smoke scope should be stated explicitly when a larger recipe remains partially deferred

Do not design recovery flows that depend on exception-only behavior.
Treat failed verification as a first-class protocol result with diagnostics attached.

## Adopted Live Scope

The adopted live-validation bundle is intentionally narrow.
Use it when changing freeform session rules, `commit_verification`, rollback/recovery behavior, or promoting a freeform recipe.

### Current Adopted Smokes

- [`scripts/freeform_recipe_c_smoke.py`](../scripts/freeform_recipe_c_smoke.py)
  - positive path
  - verifies non-monotonic volume trajectory, body-count deltas, combine behavior, and audit-only volume reporting
- [`scripts/freeform_failure_recovery_smoke.py`](../scripts/freeform_failure_recovery_smoke.py)
  - negative path
  - verifies failed hard-gate reporting, inspection-before-recovery, and successful corrected commit

### Live Checklist

1. Reload Fusion with the add-in from the current checkout.
2. Confirm the bridge is up and serving the current repo code.
3. Run:
   - `python scripts/freeform_recipe_c_smoke.py`
   - `python scripts/freeform_failure_recovery_smoke.py`
4. Confirm both exit successfully.
5. Confirm the live output shows:
   - hard-gate signals for structural assertions
   - audit-only physical-property reporting
   - failed signal reporting on the recovery smoke
   - successful corrected commit after inspection
6. Record the result in [`docs/dev-log.md`](./dev-log.md).
7. If behavior changed, update [`docs/FREEFORM_PLAYBOOK.md`](./FREEFORM_PLAYBOOK.md) and [`internal/test-recipes.md`](../internal/test-recipes.md).

### Scope Boundary

- Freeform C is only live-adopted through:
  - base plate
  - corner holes
  - boss add/combine
  - boss bore
- The top chamfer remains deferred on that path.
- The failure smoke currently uses a deterministic single-body extrusion recovery path, not the fuller cube-plus-bore recipe concept.

### Failure Rules

If either smoke fails:

- do not promote new freeform guidance yet
- capture the exact failing stage and returned `verification_signals`
- note whether the failure is:
  - protocol drift
  - bridge/live drift
  - recipe drift
  - smoke-script drift
- write the failure shape into the active handoff doc before ending the session

Keep that boundary explicit.
Do not let "recipe idea" quietly turn into "live-validated canon."
