# Freeform Playbook

## Purpose

This document is the actionable playbook for guided freeform work in ParamAItric.

It complements:

- `docs/AI_CAD_PLAYBOOK.md`
  - geometry-first CSG construction patterns
- `BEST_PRACTICES.md`
  - project-wide operating rules
- `internal/freeform-architecture.md`
  - the freeform runtime contract

This playbook is about how to operate inside the freeform loop:

- how to define a feature manifest
- how to choose the next mutation
- how to verify safely
- how to recover when wrong
- how to decide when freeform work is ready to become a structured workflow

Read this before running a freeform session or extending freeform system behavior.

---

## Core Frame

Guided freeform is not a chat loop.
It is a transactional modeling loop:

1. propose one candidate mutation
2. inspect the resulting geometry
3. verify against the manifest
4. commit only if the state is acceptable
5. repeat until every feature is resolved or explicitly deferred

The right mental model is:

- mutation = tactic
- verification = checker
- session state = gate

The agent is allowed to be flexible in proposing geometry.
The system must be strict about what counts as progress.

---

## Ground Truth Order

When freeform and intuition disagree, trust the kernel.

Use this evidence order:

1. feature or command health
2. body count and topological counts
3. body geometry observables
4. semantic selectors and face interrogation
5. screenshots or visual impressions

Visual checks are advisory only.
They can support diagnosis, but they do not overrule geometry observables from the CAD kernel.

---

## Geometry Observables

Treat these as the core freeform verification surface:

- body count
- face count
- edge count
- loop or shell count when available
- volume
- centroid
- axis-aligned bounding box
- oriented bounding box when available
- face type counts
- minimum distance or clearance when available
- feature health or warning state when available

Cheap, deterministic observables should gate progress.
More expensive or more derived checks should support deeper audit and diagnosis.

---

## Manifest Rules

A freeform manifest is a contract, not a wish list.

Every feature should be:

- shallow
- measurable
- independent when possible
- explicit about completion
- explicit about deferral if deferral is allowed

Good manifest item shape:

- feature name
- expected geometry outcome
- acceptance signal
- dependencies
- allowed deferral policy

Bad manifest items:

- "make it look right"
- "finish the part"
- "add all details"
- procedural instructions disguised as goals

Prefer:

- `L-profile body`
- `2 vertical leg holes`
- `center bore`
- `final body count = 1`

Not:

- `draw sketch`
- `extrude the rectangle`
- `combine the bodies`

The manifest should describe what must be true, not the exact sequence used to get there.

---

## Mutation Rules

### 1. One mutation only

A mutation is one geometry-changing step.
Do not chain dependent mutations before verification.

### 2. Prefer the smallest meaningful mutation

Good mutation size:

- create one body
- cut one feature
- combine one added body into the target
- apply one finish operation

Bad mutation size:

- build half the part and hope it worked
- batch multiple risky cuts into one unverified chain

### 3. Prefer relational setup over raw coordinate math

Large coordinate reasoning is fragile.
When possible, shift work toward:

- centered placement
- mirrored placement
- reference planes
- semantic face selection
- future sketch constraints

If the kernel can own the math, let it.

### 4. Inspect before risky mutations

Before mutations involving plane choice, direction, booleans, or body targeting:

- inspect the current body
- inspect relevant faces
- confirm expected body count
- confirm expected coordinate frame

### 5. Treat booleans as high-risk

Combine and cut operations are where freeform sessions most often drift into wrong topology.
Always verify immediately after them.

---

## Verification Tiers

See [`docs/VERIFICATION_POLICY.md`](./VERIFICATION_POLICY.md) for the full tier definitions (Tier 0: Hard Gates, Tier 1: Audit Checks, Tier 2: Diagnostics) and the adopted live scope.

In freeform context, the key operational rules are:

- **Tier 0** gates progression: body count, body-count delta, volume-delta sign, manifest envelope, feature health
- **Tier 1** gates session end: all features resolved or deferred, fit-critical dimensions, no leftover bodies
- **Tier 2** guides recovery only: screenshots, face/edge counts as drift clues, centroid drift as supporting evidence

Examples:

- after a cut, body count should still be `1`
- after a combine, body count should decrement as expected
- after a bore, volume should decrease
- after a boss addition, volume may increase

---

## Reference Rules

History-based CAD is reference fragile.
Assume topology can change under you.

Rules:

- do not treat face or edge references as permanently stable
- do not compare entity tokens as raw strings for identity
- prefer token plus semantic selector over token alone
- after topology-changing steps, re-inspect before trusting old references
- assume split or merged entities may invalidate naive targeting

Semantic selectors should be deterministic and simple.
Examples:

- top planar face
- largest planar face with +Z normal
- right outer cylindrical face

If a selector is ambiguous, it is not safe enough for gating.

---

## Recovery Rules

The locked phase exists for diagnosis, not panic.

When verification fails:

1. do not guess the next mutation
2. inspect the current scene
3. compare actual state to the manifest and to the last intended invariant
4. identify the narrowest failure cause
5. either retry with a corrected mutation, roll back, or defer

Common recovery patterns:

- wrong sketch plane
  - inspect face normals or bounds
  - re-create sketch on the correct plane
- wrong cut direction
  - inspect expected material removal
  - invert the direction or adjust target
- multi-body leftover
  - combine into the intended target
  - verify body count immediately
- non-monotonic volume surprise
  - inspect whether the feature intersected as intended
  - do not assume additive means larger or subtractive means smaller in every dimension
- manifest drift
  - stop iterating on the same feature blindly
  - resolve or defer explicitly

If the topology is unhealthy or references are too damaged, recover by rollback or restart.
Do not improvise on top of a corrupted state.

### Recovery Contract

The current freeform contract has a few live-validated details that matter:

- `commit_verification` reports assertion failure as `ok: false`
- failed commits should be handled by reading returned `verification_signals`
- after failure, use inspection tools before attempting the corrected commit
- recovery smokes should inject only one deliberate failure at a time

Do not write recovery tooling that assumes verification failure raises by default.
Handle the response payload as the primary failure interface.

---

## Failure Patterns To Expect

Expect these failure classes in freeform:

- wrong archetype choice
- wrong sketch plane
- wrong cut normal
- plausible but incomplete geometry
- non-monotonic volume surprises
- leftover multi-body artifacts
- broken or ambiguous references
- unhealthy topology after booleans or finishing steps
- target-feature drift

The system should be designed to detect these explicitly, not just tolerate them.

---

## Promotion Rules

Freeform is a proving ground, not the final home for repeated success cases.

Promote a freeform recipe into a structured `create_*` workflow only when:

1. the part intent is stable
2. the manifest can be reduced to deterministic inputs and checks
3. live runs are repeatable
4. the execution path no longer depends on inspection-recovery loops
5. the final geometry is topologically consistent across runs
6. the structured version is clearly more reliable than leaving it freeform

Do not promote just because a freeform session succeeded once.

---

## Benchmark Rules

Freeform benchmarks should measure trajectory quality, not just end-state plausibility.

Track:

- pass rate
- mutations to completion
- rollback count
- failure localization quality
- live versus mock differences
- reference break frequency
- audit deferral rate

Mock tests are useful for:

- state machine rules
- manifest parsing
- verification logic over synthetic observables

Live tests are required for:

- topology correctness
- boolean behavior
- real body metrics
- reference brittleness
- health-state behavior

## Live-Adopted Smokes

See the **Adopted Live Scope** section of [`docs/VERIFICATION_POLICY.md`](./VERIFICATION_POLICY.md) for the current adopted smokes, live checklist, scope boundary, and failure rules.

---

## Near-Term Priorities

The highest-leverage next additions for the freeform lane are:

1. richer measurement primitives
2. stronger token plus semantic-selector rebind strategy under topology change
3. deliberate live revalidation of benchmark recipes under the stricter March 11 contract
4. better promotion criteria for moving freeform wins into structured workflows
5. angled construction planes

Rollback checkpoints, structured verification diffs, and replay-based rollback are already landed.
The next gains should come from making the hardened loop more trustable in live use, not from broadening the primitive catalog without better recovery.

---

## Practical Default

If unsure, use this default posture:

1. define a shallow manifest
2. choose the smallest safe mutation
3. inspect immediately after the mutation
4. gate progress on deterministic observables
5. treat visual checks as advisory
6. recover narrowly or roll back
7. promote only after repeatable live success
