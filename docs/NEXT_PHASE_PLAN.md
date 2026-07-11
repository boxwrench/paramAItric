# ParamAItric — Next Phase Plan

> Updated 2026-07-11. This plan supersedes the earlier sequencing that prioritized
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

## Phase 0 — Trustworthy Distribution And Exposed Contract

**Goal:** Make the code users install, the tools hosts discover, and the local bridge boundary
match the reliability claims already made by the project.

This short cross-cutting phase was added after a repository review on 2026-07-11. It does not
replace the geometry-foundation priority below. The P0 items are release and trust blockers that
should be resolved before one-click packaging or a broader public tool surface; P1 items can run
alongside Phase 1 when they do not interrupt selector/reference work.

**Review baseline:** `pytest -q` passes with 545 tests, 5 strict expected failures, and 1 collection
warning. `compileall` and `pip check` pass. The review also reproduced a broken isolated wheel
import, four advertised but unimplemented MCP tools, and an import failure in the dormant
`mcp_server.verification` package.

| Order | Priority | Task | Evidence / reason | Done when |
|------|----------|------|-------------------|-----------|
| 0a | P0 | Repair distribution package discovery | `pyproject.toml` explicitly packages only four modules, omitting runtime packages including `mcp_server.primitives`, `mcp_server.sessions`, and `mcp_server.workflows`; the resulting wheel fails to import `mcp_server.server` outside the editable checkout. | Setuptools discovers all intended packages, build a wheel, install it into a clean environment, and smoke-test `python -m mcp_server.mcp_entrypoint` plus a server import. Keep this as an automated regression test. |
| 0b | P0 | Make tool and workflow availability truthful | `create_flush_lid_enclosure_pair`, `create_snap_fit_enclosure`, `create_telescoping_containers`, and `create_slotted_flex_panel` are registered and described as usable but currently raise raw `NotImplementedError`; their five tests are strict xfails. | Either implement and validate each tool or remove/hide it from the default MCP and workflow catalogs. Introduce explicit availability metadata if preview entries must remain discoverable, and ensure every advertised tool returns a structured result rather than an uncaught implementation exception. |
| 0c | P0 | Harden the loopback bridge mutation boundary | `/command` and `/cancel` trust any local POST, accept any content type, and have no request-size limit. A browser or unrelated local process should not be able to trigger CAD mutations merely because the service binds to loopback. | Mutation requests require an unguessable per-run credential or equivalently strong local authorization; reject unexpected `Origin`/content types; cap request bodies; validate envelope types; and add negative HTTP tests for unauthorized, cross-origin, malformed, and oversized requests. |
| 0d | P1 | Bound bridge waits and normalize protocol errors | JSON parsing and required-field access occur outside the handler's error boundary, while command handlers wait indefinitely for dispatcher completion. Client timeout does not guarantee the queued Fusion mutation stops. | Malformed requests always receive structured 4xx JSON, server-side waits have a defined timeout/cancellation policy, disconnected or timed-out requests cannot silently execute later without an explicit policy, and tests cover a stalled dispatch driver. |
| 0e | P1 | Add continuous integration and release gates | Local tests are strong, but the repo has no checked-in CI workflow, so packaging and collection regressions can land unnoticed. | CI runs supported Python versions, the full unit suite, compile/import checks, wheel build plus clean-install smoke, and a lightweight lint/static check. Publish coverage as a trend before choosing a hard threshold. |
| 0f | P1 | Repair or remove the dormant verification package | `import mcp_server.verification` fails because its `__init__.py` imports the nonexistent `mcp_server.verification.freeform`. | Restore the intended implementation or delete the dead package/export; add an import test so package surfaces cannot silently rot. |
| 0g | P1 | Remove the pytest collection warning | The helper class `TestFusionApiAdapter` defines `__init__`, so pytest tries and fails to collect it as a test class. | Rename it as a fake/fixture class or set `__test__ = False`; `pytest -q` completes with no collection warnings. |
| 0h | P1 | Complete open-source and package metadata | The README calls the project open source, but no license file is present; package metadata also lacks a README, project URLs, and an installed command entrypoint. | Choose and add the intended license, declare it and the README/URLs in `pyproject.toml`, and decide whether a `paramaitric` console script should wrap the module entrypoint. |
| 0i | P2 | Reconcile canonical documentation with shipped state | `ARCHITECTURE.md` still labels most workflow mixins as migration stubs, and the root handoff is dated March and presents old demo work as the next action. | Update or archive stale status sections, keep one canonical current-state page, and add a small docs freshness checklist to release work. |
| 0j | P2 | Reduce high-churn module size after behavior is gated | `fusion_addin/ops/live_ops.py`, `mcp_server/schemas.py`, and several workflow modules exceed 2,000 lines; repeated mixin dependency stubs and validation patterns increase review cost. | After Phase 1 contracts stabilize, split by operation/workflow domain, replace runtime `NotImplementedError` dependency stubs with typing protocols or shared bases, and keep parity/contract tests green through behavior-preserving moves. |

### Phase 0 sequencing

1. Do 0a and 0b first so installation and discovery stop overstating what ships.
2. Do 0c before presenting the bridge as a safe local mutation service or adding a browser UI.
3. Land 0d–0h as narrow reliability/release slices alongside Phase 1.
4. Keep 0i and 0j opportunistic; do not let cleanup displace attribute pinning and stable-reference work.

### Phase 0 progress (2026-07-11)

- **0a implementation complete:** bounded recursive package discovery now includes all intended
  `fusion_addin` and `mcp_server` subpackages. A package-surface regression test landed, and a
  wheel was manually clean-installed and import-smoked. The automated clean-install CI gate remains
  part of 0e.
- **0b complete:** one shared availability policy now hides the four unfinished workflows from the
  default MCP surface, workflow registry, and Fusion catalog while retaining an explicit
  experimental opt-in for internal definition tests.
- **0f complete:** the unused `mcp_server.verification` package with its broken export was removed.
- **0g complete:** pytest no longer attempts to collect the Fusion adapter test helper.
- **0i current slice complete:** stale workflow-migration status was corrected and the March handoff
  was archived behind a short pointer to canonical current-state docs. A release-time freshness
  checklist can still be added with 0e.
- **0c request-validation slice complete:** bridge POSTs now require bounded JSON request bodies
  with validated envelope types and return structured errors for malformed or oversized input.
  Per-run authorization and browser-origin protection remain open.
- **0d protocol-error slice complete:** malformed command and cancellation requests no longer drop
  the connection without a JSON response. Server-side dispatch deadlines and late-mutation policy
  remain open.
- **0e minimal CI complete:** one Ubuntu/Python 3.12 GitHub Actions job runs the full suite, builds
  the wheel, clean-installs it, and smoke-tests nested imports. Matrices, coverage services, caching,
  and release automation are intentionally omitted for now.
- **0h metadata slice complete:** the package declares its README and project links and installs a
  `paramaitric` console entrypoint. License selection remains open.
- **Verification:** 554 tests pass, 5 unfinished-workflow tests remain strict xfails, `compileall`
  and `pip check` pass, and pytest reports no collection warning.

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

> **Status (updated 2026-07-02): selector, live validation, and richer edge-diagnostic slices LANDED; attribute pinning next.** The deterministic selector layer
> (`mcp_server/selectors.py`: `validate_descriptor`, `SelectionTrace`, `resolve` with fail-closed
> cardinality guards; face `normal_axis`/`largest_planar`, edge `geometry_type`/`longest`/
> `axis_parallel`/`max_face_perimeter`),
> the `resolve_selector` command in both registries, and the `find_face` retrofit are merged to
> `master`. As of 2026-06-18, `apply_shell`, `apply_fillet`, and `apply_chamfer` also return
> additive `selection_trace` diagnostics in mock and live registry paths. Live Fusion validation on
> 2026-07-02 fixed oriented B-Rep face normals and confirmed selector, shell, fillet, chamfer,
> cylinder, and tube paths. Fillet and chamfer traces now narrow by extrusion axis, while top-outer
> chamfers resolve the exact maximum-face perimeter. Remaining Phase-1 work: attribute pinning
> (descriptor `pin` reserved); reference-stability
> strategy; and narrow operation vocabulary. See `docs/dev-log.md` (2026-06-18) and
> `docs/superpowers/plans/2026-06-13-selector-foundations-phase1.md`.

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

### Completed Phase 1 slice

The first Phase 1 implementation pass stayed intentionally narrow and is now landed.

| Done | Task | Result |
|------|------|--------|
| Yes | Define a minimal selector descriptor schema | `mcp_server/selectors.py` validates JSON-serializable descriptors for face and edge selection. |
| Yes | Build add-in-side selector resolution | `resolve_selector` is registered in both mock and live operation registries. |
| Yes | Add explicit cardinality and type guards | Singleton ambiguity and empty matches fail closed before mutation. |
| Yes | Ship a minimal `SelectionTrace` | Selector results carry diagnostic traces without turning traces into verification gates. |
| Yes | Instrument current opaque selector sites | `find_face`, `apply_shell`, `apply_fillet`, and `apply_chamfer` now return additive selection traces. |
| Yes | Validate selectors and traces in live Fusion | Oriented top/bottom/right face selectors resolve one face each; shell, fillet, and chamfer traces were captured live. |
| Yes | Add richer edge diagnostics | `axis_parallel` narrows fillet/interior-chamfer candidates from 18 to 6; `max_face_perimeter` exactly matches the 4-edge top-outer chamfer set. |
| No | Add attribute pinning with validity checks | The descriptor field is reserved; implementation remains open. |

### Active continuation slice

These are the current Phase 1 implementation tasks. This section replaces the older unchecked
task list in `docs/superpowers/plans/2026-06-13-selector-foundations-phase1.md`.

| Order | Task | Why it comes now | Done when |
|------|------|------------------|-----------|
| 1 | Implement attribute pinning with validity checks | Short-horizon references are useful only if invalidation is explicit after topology changes. | Selectors can pin named references, detect invalid/stale pins, and fall back or fail closed according to policy. |
| 2 | Write the stable reference policy | Reference behavior needs a documented contract before more topology-changing operations land. | Active docs define when to use semantic re-resolution, pins, bookmarks, and hard failures. |
| 3 | Define the narrow internal operation vocabulary | Existing operations still encode modeling intent unevenly. | Add/cut/intersect/new-body and target/mode/placement/expected-delta language is consistent across new work. |

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
- `docs/UX_ROADMAP.md`
  - novice-experience backlog (install packaging, iteration flow, printability guardrails, error-message audit); complements Phases 3 and 4 rather than replacing them

---

## Deferred Questions

These topics remain real, but they should not drive the next implementation cycle:

- external runtime geometry dependencies
- backend-neutral execution architecture
- broad assembly/joint abstractions
- aggressive freeform expansion
- major interface work before selector/reference reliability improves

### Resolved: bridge ownership vs. the official Fusion MCP connector (2026-06-13)

Autodesk + Anthropic shipped an official first-party Fusion MCP connector on 2026-04-28. Decision:
**keep owning the bridge/add-in for now; do not reposition onto the official connector.** Reframe
ParamAItric as the reliability/selector/verification layer (the add-in is the current, necessary
execution substrate for add-in-side selector resolution). The decision flips only if the official
connector later exposes a stable, queryable topology surface `resolve()` can consume. This keeps
"external runtime geometry dependencies" and "backend-neutral execution architecture" above
correctly deferred. Full rationale: `docs/dev-log.md` 2026-06-13 strategic-fork entry.
