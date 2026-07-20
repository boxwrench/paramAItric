# ParamAItric Goal Batches

> Created 2026-07-19 on `lemonade-integration`. Derived from [`ROADMAP.md`](../ROADMAP.md)
> rev 3 and the repo state as of commit `a495c98`.
>
> These are **autonomous work orders**, sized for one Codex `/goal` run each. They are not
> a roadmap and do not supersede one. `ROADMAP.md` remains the single authoritative source
> of milestone status; this document only decomposes the *currently unblocked* slice of it
> into units an agent can finish and prove.

## Scope gate

`ROADMAP.md` declares one milestone — the I2 `lemonade-fusion` vertical slice (Stage 3) —
and states that nothing past it is worth doing until it passes once for real. This document
therefore covers only:

- **Stage 0 remainder** — golden evaluation set and its tooling
- **Stage 2** — geometry foundations, which the dependency graph runs *parallel* to Stage 3
- **Stage 3 preparation** — the parts that do not require Lemonade, a Pi, or live Fusion

Stages 4–9 are deliberately absent. Adding them would re-litigate a gate the
2026-07-12 audit (`ponytail-audit-2026-07-12.md`) already closed.

## The verifiability filter

Every goal here ends in a command that either exits zero or does not. Work that terminates
in *physical* verification — a live Fusion session, a Pi, a CUDA laptop, caliper
measurements — is not goal-able, because an autonomous agent cannot run it and a vaguely
scoped goal will claim it did anyway.

Where live work is genuinely needed, the goal's deliverable is a **ready-to-run artifact for
a human** — a checklist, a validator, a driver script. Never a claim that the live work
happened.

> `evaluations/BASELINE_CAPTURE.md` puts it directly: *"Claude drives interactively, so that
> baseline cannot be scripted — it has to be captured by hand"* and *"Do not invent baseline
> numbers."* A goal whose done-criteria include producing baselines would violate both.

---

## Standing rules

These apply to **every** goal below and are not repeated in each one.

1. **Never weaken a test to pass a goal.** Adding tests is expected. Deleting, skipping,
   loosening, or `xfail`-ing an existing passing test to make a criterion go green is a
   failed goal, not a completed one. The 5 existing strict-xfails are WIP stubs and stay
   strict.
2. **Never write to `evaluations/expected/`.** Those are hand-captured records of real
   Claude+Fusion runs. Goals read them, generate checklists that help a human produce more
   of them, and validate their shape — but never author their contents.
3. **Never edit `ROADMAP.md` or `docs/dev-log.md`.** The roadmap holds the success criteria
   goals are judged against; the dev-log holds hand-recorded validation evidence. A goal
   that can rewrite its own target is not measurable.
4. **Do not touch `fusion_addin/` or bridge auth/dispatch internals** — *except*
   `fusion_addin/ops/mock_ops.py`. Recently hardened, live-coupled, unverifiable in mock mode,
   high blast radius. The carve-out (added 2026-07-19) exists because `mock_ops.py` is the
   opposite of all four: pure Python, no Fusion API, fully mock-verifiable, and
   `tests/test_registry_parity.py` already treats mock/live divergence as a same-day failure.
   Changes to `fusion_addin/state.py` are permitted only when additive and defaulted, so the
   live path is unaffected.
5. **Report honestly.** If a criterion cannot be met, stop and say so with the failing
   output. A partially-met goal reported accurately is more useful than a completed-looking
   one that is not.
6. **Deterministic CAD logic stays outside the model** — inherited from `ROADMAP.md`
   standing rules. No goal introduces an arbitrary-script escape hatch.

### Baseline verification commands

Both must pass before any goal is called done:

```bash
python -m pytest tests/ -q          # 669 collected as of 2026-07-19; no unexpected failures
python -m evaluations.runner        # exits non-zero if any case fails
```

Do not hardcode the test count in any assertion — CI records it.

---

## Sequencing

```
Track A (evaluations)          Track B (geometry, parallel)

G1 comparator                  D1 reference policy  ✅ decided 2026-07-19
  ↓                                   ↓
G4 metrics record              G5 attribute pinning
                                      ↓
G2 safety cases  (independent) G6 operation vocabulary
G3 capture driver (independent)
```

Track A and Track B share no files and can run concurrently. Within Track A, G2 and G3 are
independent of everything and can start immediately. D1 is decided, so **all six goals are
unblocked** — the only ordering constraints left are G1 → G4 (shared record shape) and
G5 → G6 (both in the selector/geometry layer).

---

## G1 — Geometry-equivalence comparator ✅ DONE 2026-07-19

**Objective.** Implement the comparison the milestone's acceptance test already specifies but
nothing yet performs.

**Outcome.** Shipped as `evaluations/runner/comparison.py` (+46 tests) with
`python -m evaluations.runner --compare-to claude`. Fail-safely cases compare by error
classification rather than geometry — they have no geometry, and the geometric invariants
report `not_applicable`.

**Finding on first real run — open, not fixed here.** Comparing mock results against the live
Claude baselines reports 2 match / 2 mismatch, and both mismatches are genuine:

- ~~`plate_centered_hole_success` volume is **24.0 under the mock adapter versus 23.607
  live**. The mock adapter does not subtract hole volume.~~ **FIXED 2026-07-19** — the mock
  now tracks `removed_volume_cm3` per body and all three reporting paths route through one
  helper. See `tests/test_mock_cut_volume.py`.
- **Open:** mock results omit `body.operation`, which live results carry.
- **Open:** the live *spacer* baseline omits `body.plane` while the live *plate* baseline
  includes it — an inconsistency on the live side. Only a re-capture (or a fix in the
  workflow layer) can settle which shape is correct.

Neither open item is a comparator bug, so neither was worked around. Both are result-shape
asymmetries rather than geometric disagreement, and both keep `--compare-to claude` at
2 mismatches until resolved.

**Why now.** `ROADMAP.md` defines acceptance as results being *"geometry-equivalent to the
Claude baseline (bounding dimensions, body count, volume, features, placement, and
verification tier match within tolerance — not identical files or topology IDs)."*
`evaluations/runner/metadata.py:5` says records are written *"so baselines can be diffed"* —
but no diff exists. Until it does, the milestone has no mechanical pass/fail.

**Done when.**

- A new module (suggested: `evaluations/runner/comparison.py`) exposes a comparison of one
  `ResultsRecord` against one `expected/claude/<case_id>.json` baseline.
- It reports a per-invariant verdict across exactly the seven invariants the roadmap names:
  bounding dimensions, body count, volume, expected holes/cuts/features present, expected
  placement, verification tier passed, valid STEP/STL export.
- Tolerances are **explicit, named, and configurable** — not magic numbers inline. Dimensional
  and volumetric tolerances are separate values.
- Equivalence is never identity: differing topology IDs, entity tokens, feature ordering, or
  file bytes must not produce a mismatch. There is a test asserting exactly this.
- A missing baseline yields an explicit `no_baseline` verdict — never a silent pass.
- The runner grows a flag (suggested: `--compare-to claude`) that emits a comparison report
  for every case that has a baseline, and exits non-zero on any mismatch.

**Verification evidence.**

```bash
python -m pytest tests/ -q
python -m evaluations.runner --compare-to claude    # 4 cases compared, 11 no_baseline, exit 0
```

Plus a test per mismatch class: each of the seven invariants must have a test proving it can
*fail*, not only pass. A comparator that cannot fail is not a comparator.

**Boundaries.** Read `expected/` only. Do not change the `ResultsRecord` shape — G4 does that,
and racing it creates a conflict.

---

## G2 — Missing safety cases

**Objective.** Close the two tier-3 gaps in the golden set.

**Why now.** `ROADMAP.md` lists five failure/safety evaluations: invalid dimensions, bridge
unavailable, ambiguous request, unsupported request, verification failure. The repo has 7
`safety`-tier cases covering invalid dimensions, bridge unavailable, and unsupported plane —
but **ambiguous request** and **verification failure** are absent. Those two are the ones
that exercise the model's judgment rather than the validator's, which is precisely what a
local 9B model is most likely to get wrong.

**Reality check (2026-07-20).** The original criteria assumed both cases were *just JSON
files*. Reading the code disproved that — both need harness infrastructure, and one spec line
was self-contradictory:

- The **faithful mock always builds correct geometry** (body_count 1, matching dims), so no
  workflow input triggers `verification_failed`. Every test that reaches it corrupts a bridge
  response through an `InterceptingBridgeClient` that lives only in `tests/`. The runner knows
  two bridges — `mock` and `unavailable` — so verification failure needs a *fault-injecting
  bridge mode*.
- `recommend_workflow`'s `no_confident_match` is a deliberate **`ok:true`-shaped "fail closed
  to families"** response — no `ok` key, no `classification`. The runner's `succeed`/
  `fail_safely` assertion paths fit neither (they require `ok is True`/`ok is False`), and
  there is no `no_confident_match` classification. So the original "assert structured-error
  shape" line was wrong for this case: declining safely is a *success*, not an error.

Decision (2026-07-20): build the harness support, no server semantic change; model the
ambiguous case as a new **`declined`** disposition.

**Done when.**

- Two new cases exist in `evaluations/cases/`, tier `safety`, conforming to
  `evaluations/cases/schema.py`.
- A new `Disposition.DECLINED` exists. A declined case asserts the discovery contract for a
  request the system safely refuses to guess at: `match_trace.status == "no_confident_match"`,
  `candidates == []`, and a non-empty `families` fallback. No server change — the discovery
  layer's existing fail-closed behavior is correct as-is.
- **Ambiguous request** (disposition `declined`): a request that matches no workflow
  confidently. Expected behavior is the `no_confident_match` fallback — *not* a confident wrong
  pick, and *not* an error envelope.
- **Verification failure** (disposition `fail_safely`): geometry is produced but fails its
  verification check, via a fault-injecting bridge. Expected disposition is a structured
  failure (`classification == "verification_failed"`) that does **not** export and does **not**
  report success — the zero-tolerance path.
- The verification-failure case asserts the full structured-error shape `{ok, classification,
  stage, error, recoverable, next_step, partial_result}`. The declined case asserts the
  discovery contract above. Neither is a traceback or free text.
- The fault-injecting bridge is promoted from `tests/` into shared harness code the runner can
  use (removing the duplicated `InterceptingBridgeClient` copies).
- Both pass under `python -m evaluations.runner` in mock mode.

**Verification evidence.**

```bash
python -m pytest tests/ -q
python -m evaluations.runner        # 17 cases, all pass
```

**Boundaries.** Do not modify existing case files. If an existing case appears mis-tiered,
report it rather than re-tiering it. Runner, schema, and the promoted fault bridge are in
scope; `mcp_server` discovery/error semantics are **not** — the ambiguous case is expressed by
the harness, not by making the server treat a safe decline as an error. The `test_evaluations`
tier/count invariants are updated to admit the new disposition and cases (a re-spec, since the
counts change whenever cases are added, and `declined` is a legitimate new safety outcome).

---

## G3 — Baseline capture driver ✅ DONE 2026-07-19

**Objective.** Make the 11 missing Claude baselines cheap and safe for a *human* to capture.

**Outcome.** Shipped as `evaluations/baseline.py` (+43 tests). One spec correction during
implementation: criterion 1 originally called for re-tiering the 6 representative parts to
`live_fusion`, but `runner.py:176` *skips* that tier in mock mode — re-tiering would have cut
the fast tier from 15 running cases to 9. `tier` was conflating two independent axes, so the
6 parts are now marked with a separate `baseline_required` flag and all 15 cases still run.
`write_checklists` refuses any path under `expected/` structurally, rather than by
instruction.

**Why now.** 15 cases exist; only 4 have baselines in `expected/claude/`. The rest require
interactive Claude+Fusion runs. This is the single largest open item in Stage 0, and it is
entirely human work — so the goal is to reduce its cost and make malformed results
impossible to commit quietly.

**Done when.**

- The ~6 representative parts the roadmap names for tier 2 — spacer, plate with hole, tube,
  bracket, fillet/chamfer part, enclosure — are labeled tier `live_fusion`. The runner
  already counts this tier (`evaluations/runner/__main__.py`) but no case uses it. Re-tiering
  here is in scope and is the one exception to G2's boundary.
- A generator emits a per-case capture checklist from the case file itself — request text,
  required measurements, expected workflow, and the exact fields the baseline must record.
  Derived from the case, never hand-duplicated, so cases and checklists cannot drift.
- A validator rejects a baseline JSON that is malformed, missing required reproducibility
  metadata, or internally inconsistent with its case. It runs over `expected/claude/` and
  passes on the 4 existing baselines.
- Checklists are generated for all 11 cases currently lacking baselines.

**Done does NOT include.** Capturing any baseline. Zero new files in `expected/`. If the
agent produces baseline *content*, the goal has failed regardless of what else passed.

**Verification evidence.**

```bash
python -m pytest tests/ -q
python -m evaluations.runner
git status --porcelain evaluations/expected/    # MUST be empty
```

That last command is the real criterion. It is mechanical and unfakeable.

---

## G4 — Per-request metrics record

**Objective.** Extend the result record with the per-request metrics Stage 3 needs to compare
a local model against the Claude baseline.

**Why now.** `ROADMAP.md` Stage 3 requires recording *"workflow/tool correctness, JSON
validity, retries, hallucinated params, verification, export, latency, tokens."*
`ResultsRecord` currently carries none of these. Capturing them is pure harness work, fully
mock-verifiable, and must exist *before* the first Lemonade run — retrofitting metrics after
a run means re-running it.

**Done when.**

- `ResultsRecord` carries each named metric. Metrics unavailable in mock mode (latency under
  a mock bridge, token counts with no model) are `None`, explicitly — never `0`, which would
  be indistinguishable from a real zero.
- "Hallucinated params" has a written, testable definition: arguments the model supplied that
  are not in the tool's generated schema. `mcp_server/schema_generation.py` is the authority
  on what a valid field is.
- "Workflow correctness" and "tool correctness" are recorded separately. A model can pick the
  right workflow via the wrong tool, and that distinction matters for the guided profile.
- The runner populates every metric it can determine in mock mode.
- Existing records remain readable — additive change, no breakage of the 4 baselines.

**Verification evidence.**

```bash
python -m pytest tests/ -q
python -m evaluations.runner --compare-to claude    # still passes; G1 comparator unaffected
```

**Boundaries.** Runs **after G1**, not concurrently — both touch the record shape.

---

## D1 — Stable-reference policy ✅ DECIDED 2026-07-19

Not a Codex goal — a human design decision that defines what G5 implements. Satisfies the
`ROADMAP.md` Stage 2 item *"written stable-reference policy (when to re-resolve semantically,
pin, bookmark, or hard-fail)."*

**Adopted:** [`docs/STABLE_REFERENCE_POLICY.md`](../docs/STABLE_REFERENCE_POLICY.md).

Summary — pinning is an opt-in assertion of stability, never silently downgraded:

- No pin → re-resolve semantically (unchanged behavior)
- Stale pin → **hard-fail unconditionally**, no fallback, structured error
- Ambiguous pin → existing `SelectorAmbiguityError`, trace status `pin_ambiguous`
- Caller opts in per descriptor; no auto-pinning; bookmarking not adopted

**G5 is unblocked.**

---

## G5 — Attribute pinning with validity checks

**Objective.** Implement the pinning seam that `selectors.py` already reserves.

**Why now.** `mcp_server/selectors.py:243` reads: *"descriptor['pin'] is reserved for the
Phase 2 attribute-pinning work."* `validate_descriptor` already reserves a `pin` slot; nothing
consumes it. The seam is cut — this is the cheapest moment to build it. Note the slot currently
holds a placeholder **string** (an entity-token shape); the policy matches pins on *attributes*,
not identity, so this goal reshapes the field into a structured attribute record. That is the
one intended change to the descriptor's accepted shape.

**Specified by D1**, adopted 2026-07-19: `docs/STABLE_REFERENCE_POLICY.md`. Implement that
document exactly. Where this goal and the policy disagree, the policy wins.

**Done when.**

- A pin can be created from a resolved selection and re-resolved later by recorded
  attributes — not by entity token. Bookmarking is explicitly out of scope per the policy.
- A descriptor **without** a pin behaves exactly as it does today. Existing selector tests
  pass unmodified; that is the proof of no regression.
- A stale pin — one matching no candidate — **hard-fails unconditionally**, for every
  operation, mutating or not. The structured error carries the pin's recorded attributes,
  what was found instead, and a `next_step` directing explicit re-selection.
- A pin matching **more than one** candidate raises the existing `SelectorAmbiguityError`
  with trace status `pin_ambiguous` — distinct from the semantic path's `ambiguous`.
- `SelectionTrace` gains `pin_stale` and `pin_ambiguous` statuses and records whether a pin
  was present and whether it resolved.
- **No fallback code path exists.** The policy is strict opt-in with no semantic downgrade,
  so there is no branch that re-resolves a stale pin. Do not write one defensively.
- Tests cover: fresh pin resolves; stale pin hard-fails; pin against deleted geometry;
  pin duplicated by a symmetric change yields `pin_ambiguous`; pin survives an unrelated
  topology change; unpinned descriptor is unaffected throughout.

**Verification evidence.**

```bash
python -m pytest tests/ -q
```

**Boundaries.** `mcp_server/selectors.py` and its tests only. The `pin` field's shape **does**
change here — from the reserved placeholder string to a recorded-attribute record — because the
policy matches pins on attributes, not identity (`docs/STABLE_REFERENCE_POLICY.md`). Grep
confirms nothing outside `selectors.py` constructs a selector pin, so the change is contained.
The rest of the descriptor (target / kind / scope / expect / params) is settled — do not touch
it. One existing test, `test_pin_is_preserved_when_provided`, asserts the old string form and is
re-specified to the new shape; that is authorized here and is not a standing-rule-#1 violation,
because it re-specifies a reserved seam rather than loosening a behavioral guarantee.

---

## G6 — Narrow internal operation vocabulary

**Objective.** Define the minimal operation vocabulary that the future CAD backend protocol
will speak.

**Why now.** `ROADMAP.md` Stage 2 specifies add/cut/intersect/new-body with
target/mode/placement/expected-delta, and notes this *"becomes the minimal backend operation
vocabulary the CAD backend protocol needs."* It gates the FreeCAD spike (Stage 5). Building
it now, against Fusion only, is how you discover whether the abstraction is real or
Fusion-shaped.

**Done when.**

- A module defines the four operations with the four attributes, typed and validated.
- `expected-delta` is machine-checkable — it states what should change (body count, volume
  direction, feature presence) so an operation can be verified against its own declaration.
  This is the same shape as the roadmap's verification tiers, and G1's comparator is the
  reference for how invariants are expressed.
- **Exactly one** existing workflow is migrated to express itself in the vocabulary, proving
  it round-trips without behavior change. That workflow's existing tests pass unmodified —
  which is the proof of no behavior change.
- No Fusion-specific type, token, or concept appears in the vocabulary's public surface.

**Done does NOT include.** Migrating other workflows. One is the proof; the rest is a
separate decision made with the evidence this goal produces.

**Verification evidence.**

```bash
python -m pytest tests/ -q          # the migrated workflow's tests pass UNMODIFIED
python -m evaluations.runner
```

**Boundaries.** One workflow. If the migration reveals the vocabulary cannot express it,
**stop and report that** — a discovered abstraction failure is a successful outcome for this
goal and valuable input to Stage 5. Do not widen the vocabulary to force a fit.

---

## Deliberately not here

- **Started-operation cancellation checkpoints.** A named blocker in `ROADMAP.md`, but it
  requires `raise_if_cancelled()` inside real Fusion mutation paths — inside the excluded
  add-in/bridge zone, and unverifiable in mock mode. Stays human work.
- **Pinning down Pi/Lemonade versions.** The `TBD`s in `docs/setup/lemonade-fusion.md` need a
  human who has actually installed the stack. An agent would fill them with plausible
  version strings, which is worse than leaving them `TBD`.
- **Any live Fusion run, any Lemonade run, any baseline capture.**
- **Stages 4–9.** Behind the milestone gate.
