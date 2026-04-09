# SelectionTrace design for ParamAItric's geometry-diagnostics layer

**ParamAItric needs a structured selection-tracing system that records what the AI intended to target, what the kernel actually resolved, and why the resolution succeeded or failed.** This report proposes a `SelectionTrace` schema, emission rules, and a minimal first implementation grounded in the project's existing verification trust model and its emerging semantic-selector architecture. The design treats traces not as generic log lines but as high-signal diagnostic records that feed directly into the system's staged verification gates, freeform session audits, and failure-recovery loops. Every recommendation below is anchored in specific architectural decisions already documented in the repository.

---

## Why selection tracing is the missing link in ParamAItric's verification stack

ParamAItric's four-layer architecture (AI host → MCP server → loopback HTTP bridge → Fusion 360 add-in via CustomEvent) creates a long signal chain between human intent and geometric reality. The Verification Trust Model establishes a rigorous hierarchy for *validating geometry after it exists*—`healthState` hard gates, `isSolid` checks, high-accuracy volume deltas. But the system currently lacks a structured mechanism for recording *how geometry was targeted before an operation executed*. This gap matters for three concrete reasons.

First, the Topological Naming Problem (TNP) makes entity resolution inherently unstable. The Verification Trust Model explicitly warns that "entity tokens act as temporary memory pointers and are routinely destroyed upon topology rebuilds" and that face/edge counts are "the most dangerous signals" due to TNP volatility (`docs/VERIFICATION_POLICY.md`). When a fillet operation selects the wrong edge because a prior boolean invalidated an entity token, the system currently has no structured record of what was attempted versus what was resolved. The failure surfaces only as a downstream `healthState` warning—a symptom, not a root cause.

Second, the project is actively moving toward semantic selectors inspired by CadQuery's string syntax (`">Z"`, `"|X"`) and build123d's `ShapeList` operators (`faces().sort_by(Axis.Z)[-1]`). The Python CAD SYNTHESIS document (`internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`) ranks "Robust Topology Selectors" as the **#1 inspiration priority** for ParamAItric. The build123d Integration Research further recommends "implementing semantic selection" as the "most critical conceptual feature to borrow." A semantic selector that fails silently—resolving to the wrong face without explanation—defeats the purpose of the entire abstraction. Traces make semantic resolution explainable.

Third, the freeform session model follows an Interactive Theorem Proving (ITP) paradigm where the AI proposes discrete "tactics" (mutations) that the kernel evaluates against a goal state. Each tactic involves targeting specific geometry. The one-mutation-then-verify discipline (`docs/FREEFORM_PLAYBOOK.md`) creates a natural emission point: every tactic attempt should produce a trace of what was selected and why, paired with the verification outcome of what happened after.

---

## Proposed SelectionTrace schema

The schema separates three concerns: **intent** (what the AI asked for), **resolution** (what the system found), and **geometric context** (measurable properties of the resolved entity). This mirrors the project's existing signal trust taxonomy, where intent is heuristic (Tier 4), resolution status is exact-but-contextual (Tier 2), and geometric descriptors range from exact kernel facts (Tier 1) to approximate estimates (Tier 3).

### Required fields (always present)

| Field | Type | Purpose |
|:------|:-----|:--------|
| `trace_id` | `str` (UUID) | Unique identifier for correlation across verification outputs and failure reports |
| `timestamp` | `str` (ISO 8601) | Millisecond-precision emission time |
| `session_id` | `str` | Freeform session identifier; `null` for structured workflows |
| `step_index` | `int` | Mutation step number within the session (0-indexed) |
| `operation` | `str` | The operation that required selection (e.g., `"extrude_cut"`, `"fillet"`, `"chamfer"`) |
| `selector_intent` | `SelectorIntent` | Structured record of what was requested (see below) |
| `resolution_status` | `enum` | One of: `"resolved"`, `"ambiguous"`, `"not_found"`, `"error"` |
| `resolved_entities` | `list[ResolvedEntity]` | What was actually found (may be empty on failure) |
| `resolution_ms` | `float` | Time spent resolving the selection |

The `SelectorIntent` sub-record captures the AI's targeting request:

```
SelectorIntent:
  selector_type: "semantic" | "attribute_lookup" | "entity_token" | "index" | "composite"
  raw_expression: str          # The selector as expressed by the AI (e.g., ">Z", "top_mounting_flange")
  target_entity_class: str     # "Face" | "Edge" | "Body" | "Profile" | "Vertex"
  target_count: int | null     # Expected number of matches (null = any)
```

Each `ResolvedEntity` records what the system actually found:

```
ResolvedEntity:
  entity_type: str             # "BRepFace" | "BRepEdge" | "BRepBody" | "Profile"
  entity_token: str | null     # Ephemeral token (diagnostic only, per VERIFICATION_POLICY)
  geometry_type: str | null    # "Plane" | "Cylinder" | "Sphere" | "Cone" | "BSpline" | "Line" | "Circle"
  semantic_attributes: dict    # Any ParamAItric_Semantic attributes attached (e.g., {"ParamAItric_Semantic": "top_mounting_flange"})
```

### Conditional geometric descriptors (emitted based on verbosity level)

These fields are expensive to compute but provide the debugging signal that matters most during failure analysis. They should always be emitted when `resolution_status != "resolved"`, and optionally when a configurable `trace_verbosity` flag is set to `"detailed"`.

| Field | Type | When to emit | Trust tier |
|:------|:-----|:-------------|:-----------|
| `normal_vector` | `[float, float, float]` | Faces only; always on failure | Tier 1 (exact kernel) |
| `centroid` | `[float, float, float]` | All entity types; always on failure | Tier 1 |
| `area_mm2` | `float` | Faces; detailed mode | Tier 1 (with HighCalculationAccuracy) |
| `length_mm` | `float` | Edges; detailed mode | Tier 1 |
| `bounding_box` | `{min: [x,y,z], max: [x,y,z]}` | All; always on failure | Tier 2 (exact but context-sensitive) |
| `candidate_count` | `int` | Semantic/composite selectors | Lightweight diagnostic |
| `parent_body_token` | `str` | All; always | Tier 2 (ephemeral) |

**Geometric descriptors worth recording versus those to avoid:** Normal vectors and centroids are **high-value, low-cost** signals—they are exact kernel facts that directly answer "did the selector find the face pointing up?" without topology count volatility. Face area (with `HighCalculationAccuracy`) is useful for distinguishing sliver faces from intentional geometry. Edge length similarly detects degenerate edges. AABB is cheap and useful as a spatial fingerprint. By contrast, **face/edge counts on the parent body should never be recorded in SelectionTrace**—the Verification Trust Model explicitly classifies these as unstable and "highly deceptive" due to TNP. Entity tokens should be recorded only as opaque diagnostic correlation IDs, never as stable references.

---

## Example traces for current operation types

### Successful freeform extrude-cut with semantic selector

```json
{
  "trace_id": "a7f3c891-...",
  "timestamp": "2026-04-08T14:32:01.447Z",
  "session_id": "freeform-session-0042",
  "step_index": 3,
  "operation": "extrude_cut",
  "selector_intent": {
    "selector_type": "semantic",
    "raw_expression": ">Z",
    "target_entity_class": "Face",
    "target_count": 1
  },
  "resolution_status": "resolved",
  "resolved_entities": [{
    "entity_type": "BRepFace",
    "entity_token": "eJy0zk1...",
    "geometry_type": "Plane",
    "semantic_attributes": {"ParamAItric_Semantic": "top_face"}
  }],
  "resolution_ms": 2.3
}
```

This trace is compact—no geometric descriptors needed because the resolution succeeded cleanly. The `raw_expression` of `">Z"` directly maps to the CadQuery-inspired string selector syntax the system is adopting.

### Failed fillet with ambiguous edge resolution

```json
{
  "trace_id": "b8d4e702-...",
  "timestamp": "2026-04-08T14:32:04.891Z",
  "session_id": "freeform-session-0042",
  "step_index": 4,
  "operation": "fillet",
  "selector_intent": {
    "selector_type": "attribute_lookup",
    "raw_expression": "ParamAItric_Semantic=pocket_rim_edge",
    "target_entity_class": "Edge",
    "target_count": 4
  },
  "resolution_status": "ambiguous",
  "resolved_entities": [],
  "resolution_ms": 8.7,
  "candidate_count": 12,
  "failure_detail": "Attribute 'pocket_rim_edge' found on 12 edges after boolean split; expected 4. TNP likely split tagged edges during prior extrude_cut."
}
```

This trace captures the exact failure the Verification Trust Model warns about: attribute orphan behavior during topological splits. The `candidate_count` of 12 versus the expected 4 immediately signals that the boolean in step 3 fragmented the tagged edges. This is **the type of diagnostic data that transforms a mysterious fillet failure into an actionable debugging insight**.

### Structured workflow (create_box) with token resolution

```json
{
  "trace_id": "c9e5f813-...",
  "timestamp": "2026-04-08T14:35:12.004Z",
  "session_id": null,
  "step_index": 0,
  "operation": "create_box",
  "selector_intent": {
    "selector_type": "entity_token",
    "raw_expression": "resolve_profile(profileToken=eJy1...)",
    "target_entity_class": "Profile",
    "target_count": 1
  },
  "resolution_status": "resolved",
  "resolved_entities": [{
    "entity_type": "Profile",
    "entity_token": "eJy1...",
    "geometry_type": null,
    "semantic_attributes": {}
  }],
  "resolution_ms": 0.4
}
```

In structured `create_*` workflows, traces are lightweight because the execution order is deterministic and entity tokens are reliable within the fenced macro boundary. The Verification Trust Model confirms that "transient entityToken lookups" are "safely utilized" in structured workflows because "the timeline is strictly controlled."

---

## Emission rules aligned to the verification architecture

The trace emission strategy must respect the project's existing verification tier structure. The fundamental principle: **emit on every selection event in freeform sessions, emit selectively in structured workflows, and always emit on failure regardless of mode.**

**Rule 1: Freeform sessions emit traces on every selection.** The one-mutation-then-verify discipline creates a natural pairing: each step produces a `SelectionTrace` followed by a `VerificationResult`. These should be linked by `trace_id` and `step_index`. Since freeform sessions are "actively hostile to static ID tracking" (Verification Trust Model), the trace becomes the primary audit artifact for understanding what the AI targeted and whether it succeeded.

**Rule 2: Structured workflows emit traces only on failure or opt-in.** In `create_*` macros, entity resolution is deterministic and fast. Emitting traces on every selection adds noise without diagnostic value. Traces should fire automatically when `resolution_status != "resolved"`, and optionally when a `--trace-verbose` flag is set during development or debugging.

**Rule 3: Failed selections always emit with full geometric context.** When `resolution_status` is `"ambiguous"`, `"not_found"`, or `"error"`, the trace must include all conditional geometric descriptors (normal vectors, centroids, bounding boxes, candidate counts). This is the high-signal data that makes failure analysis actionable. The marginal compute cost of extracting a normal vector on a failure path is negligible compared to the debugging time saved.

**Rule 4: Traces are emitted before the operation executes, not after.** This is critical. If a fillet operation crashes Fusion's internal solver, the trace must already exist to explain what was selected. Post-operation emission risks losing diagnostic data on catastrophic failures. The trace captures "what was attempted"; the verification gate captures "what happened."

**Rule 5: Trace verbosity is session-scoped, not global.** A freeform session exploring complex boolean chains should default to `"detailed"` verbosity. A structured macro generating a simple spacer should default to `"minimal"`. This prevents trace volume from scaling with system throughput while ensuring high-risk operations get full diagnostic coverage.

---

## How traces integrate with verification, failure reports, and audit logs

### Verification output integration

Each verification gate result should include a `selection_trace_ref` field containing the `trace_id` of the selection that triggered the operation. When a hard gate fires—`healthState` warning, `isSolid == False`, or volume delta exceeding threshold—the associated `SelectionTrace` immediately provides the "what was the AI targeting when this broke?" context. This transforms the verification output from "Feature 7 is sick" to "Feature 7 is sick because the AI targeted a face via `>Z` semantic selector, resolved to BRepFace/Plane with centroid [50, 25, 30], and the subsequent extrude_cut produced a non-manifold result."

### Failure report integration

When rollback is triggered, the failure report should embed the full `SelectionTrace` (including all geometric descriptors) alongside the verification gate that tripped. The combination of `selector_intent` + `resolved_entities` + `verification_failure_type` creates a structured root-cause chain. For the LLM's recovery loop, this chain should be serialized back into the MCP context window so the AI can reason about *why* its selection failed and propose an alternative tactic.

### Audit log integration

The session-ending compliance audit should include the complete ordered sequence of `SelectionTrace` records for the session. This serves two purposes: (1) it provides a full provenance chain for the generated geometry, answering "how did we arrive at this shape?", and (2) it enables post-hoc analysis of selector stability—if 40% of selections in a session were `"ambiguous"`, the workflow needs hardening.

### Freeform session log format

Each step in the freeform log should be a paired record:

```
FreeformStep:
  step_index: int
  selection_trace: SelectionTrace
  operation_params: dict
  verification_result: VerificationResult
  outcome: "committed" | "rolled_back" | "retried"
```

This pairing ensures that every mutation in the session is fully explainable: what was targeted, what was attempted, what was verified, and what happened. The ITP paradigm frames each step as a "tactic"—the trace is the tactic's argument, and the verification result is the kernel's judgment.

---

## Minimal first implementation that delivers high value

The implementation should follow the project's own prioritization framework from the Verification Trust Model: **Now / Next / Later**.

### Now (first implementation)

**Ship a `SelectionTrace` dataclass with required fields only.** Define the schema as a Python `dataclass` or `TypedDict` in the MCP server layer. Required fields: `trace_id`, `timestamp`, `session_id`, `step_index`, `operation`, `selector_intent` (as a flat dict initially), `resolution_status`, `resolved_count`, `resolution_ms`. Omit all conditional geometric descriptors in v1.

**Emit traces in freeform session mutations only.** Instrument the freeform session handler (`mcp_server/sessions/freeform.py`) to construct and emit a `SelectionTrace` before each mutation is dispatched to the Fusion add-in. This aligns with Rule 1 and targets the highest-risk workflow first.

**Emit on all selection failures in all modes.** Add trace emission to every code path where entity resolution returns null or multiple unexpected candidates. This covers the `resolve_profile()` and entity-token lookup patterns that exist in the operations layer (`fusion_addin/ops/live_ops.py`).

**Attach `trace_id` to verification gate outputs.** Modify the verification result structure to carry a `selection_trace_ref` field. This creates the correlation link between "what was selected" and "what the kernel thought about it" without requiring any changes to the verification logic itself.

**Store traces in the freeform session log.** Append each trace to the session's step history. No separate storage backend needed—traces live alongside the existing session state.

### Next (second iteration)

- Add conditional geometric descriptors (`normal_vector`, `centroid`, `bounding_box`) on failure paths
- Implement `SelectorIntent` as a structured sub-record with `selector_type` enum
- Add `semantic_attributes` extraction when attribute-based selectors are used
- Instrument structured `create_*` workflows with opt-in tracing
- Add `candidate_count` for semantic and composite selectors

### Later (once semantic selectors are production)

- Full `ResolvedEntity` sub-records with `geometry_type` classification
- Trace-level comparison: intent vs. resolved (automated mismatch detection)
- Trace aggregation analytics: selector failure rates per operation type
- Trace replay: re-run a session's selection sequence against a modified model to test selector stability

### Avoided (anti-patterns)

- **Topology counts in traces.** Face and edge counts are "the most dangerous signals" per the Verification Trust Model. Including them in traces would tempt consumers to rely on them for reasoning.
- **Mesh-derived signals.** Triangulated approximations are classified as inherently flawed for verification. No mesh data in traces.
- **Full B-Rep serialization.** Dumping the entire boundary representation into a trace record would create massive, unreadable diagnostic data. Traces should contain pointers and summaries, not geometry dumps.
- **Trace-as-verification-gate.** Traces are diagnostic records. They should never block operations or trigger rollbacks themselves. The verification trust model already defines what gates and checks exist; traces complement them, they do not replace them.

---

## Risks and anti-patterns to guard against

**Risk 1: Trace inflation drowning useful signal.** The most dangerous evolution of a tracing system is becoming a generic logger. Every field added to `SelectionTrace` should pass the test: "Would this field change how an engineer debugs a selection failure or how the AI recovers from one?" If neither, it does not belong in the trace. The build123d research recommends that ParamAItric must "maintain a strict abstraction layer"—this applies to diagnostic data as much as to API surfaces.

**Risk 2: Treating entity tokens as stable references within traces.** The Verification Trust Model is unambiguous: tokens are "routinely destroyed upon topology rebuilds." If trace consumers start using `entity_token` values to compare entities across steps, they will encounter exactly the "Face Count Identity Trap" failure pattern described in the verification policy. Traces must document tokens as opaque correlation aids, never as stable identifiers. Consider marking the field with a `# DIAGNOSTIC_ONLY` annotation in the schema.

**Risk 3: Compute overhead from geometric descriptor extraction.** Normal vector and centroid extraction via the Fusion API is fast (microseconds). High-accuracy area computation is not—it requires `HighCalculationAccuracy` parameter invocation, which the Verification Trust Model identifies as "medium cost." The conditional emission rules (geometric descriptors on failure paths only, optional in detailed mode) keep this bounded. But if a pathological session generates 50 consecutive failures, the cumulative extraction cost could become noticeable. A per-session budget cap on detailed trace emissions (e.g., max 20 detailed traces before downgrading to minimal) is a reasonable safeguard.

**Risk 4: Coupling trace schema to selector implementation.** The semantic selector system is still being designed. If `SelectionTrace` is tightly coupled to a specific selector syntax (e.g., CadQuery string format), it will need to be rewritten when the selector API evolves. The `selector_intent.raw_expression` field should be an opaque string, and `selector_type` should be a loose enum that can accommodate new selector types without schema migration.

**Risk 5: Traces becoming a second verification system.** There is a subtle temptation to add "trace-based validation"—for example, failing an operation if the trace shows the selector resolved to a `BSpline` face when a `Plane` was expected. This creates a parallel verification path that competes with the established hard-gate architecture. The Verification Trust Model explicitly categorizes signals into gates, checks, and diagnostics. Traces belong to diagnostics. If a geometric property needs to block operations, it should be promoted to a verification gate through the established trust taxonomy, not backdoored through the trace system.

---

## What this report is based on and what it cannot confirm

**Observed facts** from retrieved documents: The four-layer architecture, dual-lane design, ITP-inspired freeform paradigm, verification trust taxonomy (four tiers), hard-gate definitions (`healthState`, `isSolid`, volume deltas), entity-token ephemerality, custom-attribute persistence strategy, TNP analysis, semantic-selector design direction, and build123d/CadQuery inspiration priorities are all directly documented in the Verification Trust Model (`docs/VERIFICATION_POLICY.md`), the Python CAD SYNTHESIS (`internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`), and the build123d Integration Research.

**Informed inferences:** The specific operation dispatch pattern (resolve tokens → validate → execute → return tokens + summary) is inferred from architectural descriptions in the Fusion 360 API Research document and the build123d Integration Research, which describe the canonical op structure. The session handler instrumentation recommendations are inferred from the documented session architecture rather than from reading the actual `mcp_server/sessions/freeform.py` source code.

**What could not be confirmed:** The GitHub repository (`boxwrench/paramAItric`) is private and inaccessible. The actual source code of `freeform.py`, `sessions/freeform.py`, `tool_specs.py`, `live_ops.py`, `README.md`, `ARCHITECTURE.md`, `FREEFORM_PLAYBOOK.md`, and `FREEFORM_CHECKLIST.md` was not directly read. Specific function signatures, existing data structures, current logging patterns, and actual dispatch mechanisms in the codebase could not be verified. The schema and emission rules proposed here are designed to be compatible with the documented architecture, but implementation details may require adjustment once the source files are consulted.