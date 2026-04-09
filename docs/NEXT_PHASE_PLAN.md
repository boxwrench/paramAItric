# ParamAItric — Next Phase Plan

> Updated 2026-04-08. This plan supersedes the earlier sequencing that prioritized
> intake, UI, and capability expansion ahead of internal geometry reliability work.

## Current State Summary

- ParamAItric already has the right product shape: AI host → MCP tool surface → validated workflow execution → Fusion-native editable output.
- The system already has strong architectural pieces: staged workflows, verification tiers, structured failure handling, and a constrained freeform lane.
- The next bottleneck is not primarily missing UI or missing feature count.
- The next bottleneck is internal geometry semantics: how the system selects, names, traces, and re-finds geometry after mutations.

**What is working:** The controlled Fusion-first architecture, workflow discipline, and verification-oriented product direction.
**What is limiting progress:** brittle geometry targeting, weak explainability of selections, uneven reference stability across mutations, and workflow structure that is still more ad hoc than it should be.

## Strategy Reset

Recent research changed the priority order.

ParamAItric should not spend its next major iteration primarily on:

- intake/discovery polish
- HTML UI
- new primitive surface area
- broader backend questions

ParamAItric should spend its next major iteration on a stronger internal geometry foundation:

- semantic selectors
- selection traces and diagnostics
- stable reference strategy across topology mutations
- a narrower internal operation vocabulary
- cleaner reusable part-recipe structure

This keeps ParamAItric as the controlled application and improves the exact thing the product depends on most: reliable translation from human intent to editable CAD actions.

## Planning Rules

These rules apply to the phases below:

- no external runtime geometry dependency
- no backend-neutral architecture work yet
- no major capability expansion before selector/reference reliability improves
- no treating workflow count as the main progress metric
- usability layers should build on stronger geometry semantics, not compensate for weak internals

---

## Why The Roadmap Changed

The earlier roadmap correctly identified real usability gaps, especially workflow discovery and interface limitations.

But the newer research showed a more leveraged conclusion:

- ParamAItric already has enough workflow and verification shape to benefit from better internal geometry abstractions.
- If selector determinism and reference stability are weak, adding more UI or more primitives mostly expands the surface area of the same underlying reliability problem.
- If selector determinism and reference stability improve first, later work on intake, UI, threads, patterns, and richer workflows becomes easier to explain, validate, and maintain.

The new roadmap therefore treats internal geometry semantics as the enabling layer for later UX and capability work.

---

## Phase 1 — Internal Geometry Foundations

**Goal:** Make geometry targeting semantic, explainable, and robust enough to support the next generation of workflows and tools.

| Task | Description | Effort |
|------|-------------|--------|
| 1a. Semantic selector vocabulary | Define the first internal selector set for faces and edges: examples include top face, largest planar face, circular edges on selected face, outer vertical edges, and similar deterministic selectors. | Medium |
| 1b. Selector composition rules | Define how selectors can chain, rank, group, and narrow candidates without becoming brittle or opaque. | Medium |
| 1c. `SelectionTrace` diagnostics | Every selector-dependent operation should be able to explain what it matched, why it matched, and what geometry facts supported the choice. | Medium |
| 1d. Stable reference strategy | Formalize how ParamAItric re-finds geometry after topology changes using tokens, bookmarks, attributes, and semantic re-resolution policies. | Medium |
| 1e. Verification integration | Align selector and reference work with the verification tiers in `docs/VERIFICATION_POLICY.md` so diagnostics remain high-signal and hard gates remain conservative. | Small |
| 1f. Narrow internal operation vocabulary | Define a small internal modeling vocabulary for operation intent: target, mode, placement, parameters, expected structural delta. | Medium |
| 1g. Shared boolean mode enum | Normalize add/cut/intersect/new-body intent behind a consistent internal vocabulary before exposing more modeling surface. | Small |

**Why this phase comes first:**

- It addresses the main current reliability ceiling.
- It benefits both structured workflows and guided freeform.
- It creates better prerequisites for later UI, recommendation, and capability work.

### Immediate execution slice

The first implementation pass inside Phase 1 should stay narrow.

These tasks are ordered on purpose.

| Order | Task | Why it comes now | What it unlocks later |
|------|------|------------------|-----------------------|
| 1 | Define a minimal selector descriptor schema | ParamAItric needs one clear way to express targeting intent before selector logic spreads across more operations. | Consistent selector handling in workflows, freeform, and future UI/debug surfaces. |
| 2 | Build add-in-side selector resolution | Live topology exists in Fusion, not in the MCP layer. This is the correct execution boundary. | Safer semantic targeting, cleaner bridge contracts, and future reference re-resolution work. |
| 3 | Add explicit cardinality and type guards | The main early failure to prevent is silently selecting the wrong entity when one was expected. | More trustworthy workflow stages, clearer failure handling, and safer future selector expansion. |
| 4 | Ship a minimal `SelectionTrace` | Selector behavior must become explainable before it becomes broader. | Better recovery, auditability, workflow hardening, and future UI visibility into geometry decisions. |
| 5 | Instrument current opaque selector sites | The highest-value places are the selection points ParamAItric already hides behind heuristics. | Immediate visibility into `find_face`, `apply_shell`, `apply_fillet`, `apply_chamfer`, and freeform mutation targeting. |
| 6 | Add attribute pinning with validity checks | Short-horizon references are useful, but they need explicit invalidation checks after topology changes. | Stronger reference strategy, richer multi-step workflows, and safer topology-changing capabilities later. |

### Phase 1 rationale

This task stack is the bridge between research and implementation.

- It keeps the first selector release small and deterministic.
- It makes geometry targeting more explainable before adding more selector power.
- It gives later phases better foundations instead of forcing later UX and capability work to compensate for hidden geometry fragility.

### How Phase 1 links to later phases

- **Phase 2 — Workflow Architecture Hardening**
  - reusable part-recipe structure is easier once selectors, guards, and selection traces give workflows clearer internal contracts
- **Phase 3 — Intake and Workflow Discovery**
  - recommendations and examples become more trustworthy when the workflows behind them target geometry more reliably
- **Phase 4 — Local Interface**
  - the UI can surface meaningful geometric status and diagnostics instead of generic pass/fail output
- **Phase 5 — Capability Expansion**
  - threads, patterns, lofts, sweeps, and richer utility workflows all become less risky once reference handling and selector semantics are stronger

---

## Phase 2 — Workflow Architecture Hardening

**Goal:** Make existing and future workflow families easier to author, reuse, and validate.

| Task | Description | Effort |
|------|-------------|--------|
| 2a. Reusable part-recipe structure | Define a cleaner internal recipe shape for workflow families with named inputs, defaults, stage contracts, and verification outputs. | Medium |
| 2b. Dimensional workflow discipline | Codify lower-dimension-first modeling and "edge treatments last" as explicit workflow-authoring rules. | Small |
| 2c. Placement helpers | Add deterministic internal helpers for common layouts such as linear and simple polar placements. | Small |
| 2d. Parameter relationship strategy | Use expressions and linked dimensions where design intent is relational, but keep the first pass narrow and explainable. | Medium |
| 2e. State bookmarks and tags | Strengthen named intermediate states so workflows can refer to meaningful modeling stages, not only post-hoc entity lookup. | Medium |

**What this unlocks:**

- cleaner workflow implementations
- easier promotion of new part families
- better reuse across plates, brackets, cylinders, and enclosures
- less pressure to solve complexity by adding one-off workflow logic

---

## Phase 3 — Intake and Workflow Discovery

**Goal:** Fix the gap between "I need a part" and "run this workflow" after the geometry core is stronger.

| Task | Description | Effort |
|------|-------------|--------|
| 3a. Enrich `workflow_catalog` | Return intent, input schema summary, example dimensions, typical use cases, and workflow-family cues. | Small |
| 3b. Add `recommend_workflow` tool | Intent + constraints → ranked workflow suggestions with example params. | Medium |
| 3c. Build reference catalog | Real-world lookup data for common dimensions, hardware conventions, and reference starting points. | Medium |
| 3d. Add schema display metadata | Extend schema definitions with display and grouping metadata for both AI and future UI use. | Small |

**Why this is later now:**

- discovery gets easier once workflows have clearer internal structure
- examples and recommendations become more trustworthy once selector/reference behavior is more reliable

---

## Phase 4 — Local Interface

**Goal:** Add a visual local interface once the underlying workflow and geometry semantics are clearer.

| Task | Description | Effort |
|------|-------------|--------|
| 4a. Serve `/ui` from the bridge | Add a lightweight local web entrypoint from the existing bridge server. | Small |
| 4b. Workflow browser | Show workflow families, example intents, and previewable parameter sets. | Medium |
| 4c. Auto-generated parameter forms | Render forms from schema display metadata and workflow/reference metadata. | Medium |
| 4d. SVG or simple 2D previews | Provide lightweight dimensional previews without requiring a live Fusion preview step. | Medium |
| 4e. Reference panel | Show common dimension sets and starting points from the reference catalog. | Small |
| 4f. Status and verification panel | Surface stage progress, verification results, and selector/diagnostic output where useful. | Medium |

**Dependency note:** The UI should benefit from selector and diagnostic work, not hide the lack of it.

---

## Phase 5 — Capability Expansion On Top Of The Stronger Core

**Goal:** Expand modeling capability only after the internal geometry foundation is stronger.

### Threading

**Goal:** Add thread generation with independent interior/exterior pitch where it fits the stronger selection/reference model.

| Task | Description | Effort |
|------|-------------|--------|
| 5a. Add `apply_thread` primitive | Wrap Fusion `ThreadFeatures` behind the strengthened targeting and verification model. | Medium |
| 5b. Thread query tools | Expose available thread families, sizes, and designations for discovery. | Small |
| 5c. Thread schemas and workflows | Add `threaded_cylinder` and `threaded_cap` once the operation model is ready. | Medium |
| 5d. Thread reference data | Add common thread standard lookup data to the reference catalog. | Small |

### Patterning and symmetry primitives

| Task | Description | Effort |
|------|-------------|--------|
| 5e. Linear pattern primitive | Add once selector/reference semantics can target patterned geometry safely. | Small |
| 5f. Circular pattern primitive | Same rule as above. | Small |
| 5g. Mirror primitive | Same rule as above. | Small |
| 5h. Loft and sweep | Add only after the operation vocabulary and selector/reference model are ready for more complex topology shifts. | Medium |

### Follow-on workflow expansion

| Task | Description | Effort |
|------|-------------|--------|
| 5i. Refactor repetitive workflows | Replace one-off variants with parameterized families once the recipe structure is mature. | Medium |
| 5j. Insert bosses and other utility features | Add common utility-part patterns on top of the stronger recipe and reference architecture. | Medium |
| 5k. Freeform continuation on failure | Offer guided continuation only after diagnostics are strong enough to make it trustworthy. | Medium |

---

## Progress Signals

Near-term progress should be measured more by these outcomes:

- selector behavior is more deterministic and explainable
- failures return better geometry diagnostics
- workflows depend less on brittle ad hoc geometry assumptions
- reusable part families become easier to author and maintain

Progress should be measured less by these alone:

- raw workflow count
- raw primitive count
- existence of a UI before the core semantics are stronger

---

## Research Sequence That Supports This Plan

`docs/NEXT_RESEARCH_PLAN.md` now drives the unresolved questions in the correct order:

1. semantic selector design
2. selection trace and diagnostics
3. stable reference strategy across topology mutations
4. narrow internal operation vocabulary / IR
5. reusable part-recipe architecture
6. parameter relationship strategy
7. fast-feedback geometry assertions and example-based tests

This plan should be updated from those research outputs, not from broad ecosystem scanning.

---

## Relationship to Existing Docs

- `docs/AI_CONTEXT.md`
  - should mirror this priority order for session guidance
- `docs/RESEARCH_TRACKS.md`
  - should explain why the roadmap changed
- `docs/NEXT_RESEARCH_PLAN.md`
  - should drive the next unresolved design questions
- `docs/AI_CAD_PLAYBOOK.md`
  - should reflect the modeling discipline and selector/diagnostic direction without becoming another roadmap file

---

## Deferred Questions

These topics remain real, but they should not drive the next implementation cycle:

- external runtime geometry dependencies
- backend-neutral execution architecture
- broad assembly/joint abstractions
- aggressive freeform expansion
- major interface work before selector/reference reliability improves
