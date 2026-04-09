# Selector Foundations Intake Synthesis

Date: 2026-04-08
Status: reviewed intake bundle, trimmed to high-value references

## Purpose

This memo consolidates the useful conclusions from the selector and selection-trace intake that landed in this folder.

The goal is not to preserve every alternate report. The goal is to preserve:

- the most actionable selector conclusions
- the parts of the research that directly inform ParamAItric's next internal design pass
- the guardrails that keep the selector system small, deterministic, and compatible with the current Fusion-first architecture

This memo is the working summary for the bundle. The remaining retained notes stay only where they add substantial implementation value beyond what is captured here.

## Retained source notes

These are the source notes worth keeping after review:

- [paramAItric_selector_design_research.md](./paramAItric_selector_design_research.md)
  Why it stays:
  It is the strongest selector memo in the bundle. It has the clearest practical structure for ParamAItric: a ranked v1 selector vocabulary, composition rules, explicit failure modes, a sensible AI-facing vs internal-only split, and a narrow phased implementation plan.

- [SelectionTrace design.md](./SelectionTrace%20design.md)
  Why it stays:
  It is the strongest trace memo in the bundle. It stays close to ParamAItric's verification model, keeps the trace diagnostic instead of turning it into a second verification system, and proposes a realistic minimal first implementation.

- [Selection-Trace and Geometry-Diagnostics Layer.md](./Selection-Trace%20and%20Geometry-Diagnostics%20Layer.md)
  Why it stays:
  It is the most repo-grounded trace note. It points to concrete current selection sites that matter immediately: `find_face`, `apply_shell`, `apply_fillet`, and `apply_chamfer`.

## Removed as redundant or lower-value

These files were reviewed but are not needed as retained research assets:

- `ParamAItric Semantic Selector Design.md`
  It contains some useful architectural instincts, especially the AI-facing vs internal-only split, but it drifts into overbuilt AST machinery and has weak citation quality. The strongest practical conclusions are already preserved in the retained selector memo.

- `ParamAItric Selection Trace Design.md`
  It overlaps heavily with the stronger trace memos but pushes premature ideas such as affinity scores, topology fingerprints, and larger telemetry structures that are not appropriate for a first implementation.

- `First-Generation Semantic Selector System.md`
  It is another alternate selector memo with weaker grounding, citation noise, and less practical implementation guidance than the retained notes.

- `../SelectionTrace design.zip`
  It is the transport bundle, not the durable source material.

## High-level synthesis

The bundle is highly consistent on the main strategic point:

- ParamAItric should build a small first-generation semantic selector layer now.
- Selector resolution belongs in the Fusion add-in, not in the MCP server.
- Selection should be treated as a deterministic query-and-guard step, not as an implicit side effect hidden inside operations.
- ParamAItric should add a lightweight `SelectionTrace` diagnostic artifact now, but keep it diagnostic and provenance-aware rather than turning it into a second verification framework.

The strongest common conclusion is this:

ParamAItric does not need a broad selector language first. It needs a small deterministic selector vocabulary, explicit cardinality contracts, and a trace layer that explains intent versus resolution at the exact places where geometry targeting is currently opaque.

That is the main practical value of this intake.

## Weighted actionable conclusions

The weights below are relative implementation priority scores for ParamAItric, on a 10-point scale.

### 1. Build selector resolution inside the Fusion add-in

Weight: 10.0

Conclusion:
Selector evaluation must happen where live Fusion topology exists. The MCP layer should pass selector descriptors; the Fusion add-in should resolve them against live B-Rep objects.

Why this ranks first:

- It is the cleanest architecture boundary in the bundle.
- It fits the repo's actual runtime model.
- It prevents the MCP server from pretending it can safely reason over stale or abstracted topology.

Why the conclusion is well-supported:

- [paramAItric_selector_design_research.md](./paramAItric_selector_design_research.md) is strongest here and ties selector resolution directly to the add-in.
- [Selection-Trace and Geometry-Diagnostics Layer.md](./Selection-Trace%20and%20Geometry-Diagnostics%20Layer.md) supports this by identifying current add-in selection sites that need tracing.

Recommended scope:

- Keep selector descriptors JSON-serializable at the bridge boundary.
- Evaluate, guard, and pin inside the Fusion add-in only.

### 2. Ship a small deterministic v1 selector vocabulary

Weight: 9.7

Conclusion:
The first selector release should be narrow and high-signal, not expressive for its own sake.

Why this ranks near the top:

- It turns the roadmap shift into a concrete implementation slice.
- It prevents the selector layer from becoming another broad abstraction project before ParamAItric has validated the core mechanics.

Recommended v1 emphasis:

- `body_by_name` or `body_by_attribute`
- `face_by_feature_role`
- `face_by_normal_axis` or top-planar-face style selector
- `edge_by_loop_type`
- `edge_by_geometry_type`
- limited area- or length-rank selectors only where ties are guarded

Why the conclusion is well-supported:

- [paramAItric_selector_design_research.md](./paramAItric_selector_design_research.md) provides the clearest ranked vocabulary and explicit “do now / later / avoid” structure.
- The trace memos indirectly support this by emphasizing ambiguity, candidate count, and explainability.

### 3. Make cardinality explicit on every selector

Weight: 9.4

Conclusion:
Every selector invocation should declare whether it expects one entity or many. Ambiguity should fail closed when singleton semantics are required.

Why this matters:

- This is the cleanest guardrail against silent wrong-target selection.
- It is easy to implement compared with broader selector features.
- It aligns perfectly with ParamAItric's verification-first design.

Why the conclusion is well-supported:

- [paramAItric_selector_design_research.md](./paramAItric_selector_design_research.md) repeatedly treats cardinality as a first-class contract.
- The trace memos reinforce that ambiguity needs structured reporting, not silent fallback.

Recommended scope:

- `expect: "one"` or `expect: "many"` should be part of the selector descriptor.
- Any mismatch should abort before the mutation executes.

### 4. Introduce `SelectionTrace` as a Tier 2 diagnostic artifact

Weight: 9.2

Conclusion:
ParamAItric should add a small structured `SelectionTrace` object now, but keep it diagnostic and provenance-aware rather than using it as a hidden correctness gate.

Why this matters:

- It makes selector behavior explainable.
- It directly helps failure recovery, workflow hardening, and freeform debugging.
- It complements the existing verification policy instead of competing with it.

Why the conclusion is well-supported:

- [SelectionTrace design.md](./SelectionTrace%20design.md) is strongest here and stays disciplined about trace scope.
- [Selection-Trace and Geometry-Diagnostics Layer.md](./Selection-Trace%20and%20Geometry-Diagnostics%20Layer.md) maps the trace to concrete current operations and repo architecture.

Recommended v1 fields:

- trace id
- timestamp
- session/workflow context
- operation
- selector intent
- resolution status
- resolved count or resolved entity summary
- resolution time

Keep optional geometry descriptors for failure paths or verbose mode.

### 5. Instrument the current opaque selector sites first

Weight: 8.9

Conclusion:
The first instrumentation targets should be the places where ParamAItric already does implicit semantic or heuristic selection.

Best first targets:

- `find_face`
- `apply_shell`
- `apply_fillet`
- `apply_chamfer`
- freeform mutation selection boundaries

Why this matters:

- These are the current error-prone geometry targeting points.
- Instrumenting them first gives immediate visibility without requiring a fully generalized selector framework on day one.

Why the conclusion is well-supported:

- [Selection-Trace and Geometry-Diagnostics Layer.md](./Selection-Trace%20and%20Geometry-Diagnostics%20Layer.md) is strongest on this point.
- [SelectionTrace design.md](./SelectionTrace%20design.md) supports freeform-first trace emission.

### 6. Keep selector composition shallow

Weight: 8.4

Conclusion:
Two-stage selector composition is enough for a first implementation: scope reduction, then refinement.

Why this matters:

- It keeps selector behavior explainable.
- It prevents the system from hiding fragile topology assumptions inside deep selector chains.
- It encourages promoting complex repeated logic into named workflow steps instead of recursive selector machinery.

Why the conclusion is well-supported:

- [paramAItric_selector_design_research.md](./paramAItric_selector_design_research.md) is clearest here and gives strong composition rules.

Recommended rule:

- a selector should reduce scope, then refine
- anything deeper is a smell and should usually become a named helper or workflow-level operation

### 7. Use attribute pinning carefully, not as a magic persistence layer

Weight: 7.8

Conclusion:
Pinning resolved selections via attributes is useful, but only as a controlled short-horizon handoff mechanism with validity checks after topology changes.

Why this matters:

- It is practical for step-to-step reuse.
- It is still vulnerable to geometry splits, rebuilds, and stale assumptions.

Why the conclusion is well-supported:

- [paramAItric_selector_design_research.md](./paramAItric_selector_design_research.md) makes the best argument for immediate pinning plus validity checks.
- [SelectionTrace design.md](./SelectionTrace%20design.md) correctly warns against treating tokens as stable identity.

Recommended scope:

- pin selected entities with ParamAItric-owned attributes
- re-check validity after topology-changing operations
- never treat pinning as proof of long-horizon identity stability

## What not to adopt yet

These ideas appear in the bundle but should not drive the first implementation:

- deep recursive selector ASTs as the public contract
- affinity-score ranking systems
- topology fingerprint hashes
- broad relational selector families
- candidate-pool dumps as normal output
- full telemetry-style diagnostic payloads
- persistent cross-session selector semantics beyond narrow attribute- and token-based re-resolution

These are either premature, weakly grounded, or too heavy for the reliability-first slice ParamAItric needs now.

## Recommended first implementation slice

The best narrow implementation path from this intake is:

1. Define a minimal selector descriptor schema with:
   - selector kind
   - scope
   - expect one/many
   - optional pin name
2. Implement add-in-side resolution for:
   - body scoping
   - feature-role face selection
   - top-planar / axis-normal face selection
   - loop-type and geometry-type edge selection
3. Add cardinality and type guards before mutation execution.
4. Add a minimal `SelectionTrace` object.
5. Emit traces:
   - on all selector failures
   - on freeform selection steps
   - in the first key heuristic selector sites
6. Attach trace references to verification or failure outputs where relevant.

This is enough to materially improve explainability and reliability without overcommitting to a large abstraction surface.

## Practical effect on the roadmap

This intake does not change the roadmap direction established by the previous synthesis. It strengthens it.

It gives the roadmap a more concrete Phase 1 implementation shape:

- build selector resolution in the add-in
- keep the first selector vocabulary small
- enforce cardinality
- add minimal selection tracing
- instrument current opaque selection points first

That is the most important outcome of this bundle.
