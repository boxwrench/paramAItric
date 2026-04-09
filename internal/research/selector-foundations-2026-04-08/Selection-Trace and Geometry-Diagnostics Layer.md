# Deep Technical Research and Design Analysis for ParamAItric’s Selection-Trace and Geometry-Diagnostics Layer

## Executive Summary

**Observed facts (repo-grounded):** ParamAItric is explicitly designed around a constrained tool surface, staged execution, and verification-as-a-protocol-result (not “best-effort automation”). citeturn47view0turn48view0turn50view2 The system boundary is a four-part pipeline (AI host → MCP server → loopback HTTP → Fusion add-in), and Fusion mutations must run on Fusion’s main thread. citeturn47view2turn14view1turn23view2 Cross-call references use Fusion entity tokens and should be treated as opaque references (not parsed semantic IDs). citeturn47view2 The verification policy formalizes tiered signals and emphasizes provenance; “diagnostics” (Tier 2) explicitly includes topology-fragile clues like face/edge counts, bounding boxes, and visual impressions. citeturn48view0turn51view0

**Informed inferences (from the repo’s current behavior):** ParamAItric already contains multiple *implicit* selection mechanisms that are critical but under-explained in outputs:
- Server-side semantic face selection (`find_face`) chooses a face by bounding-box extremes from `get_body_faces`. citeturn11view2turn52view0
- Add-in side “finish” operations select edges by internal heuristics (`apply_fillet`, `apply_chamfer` with `edge_selection`). citeturn31view2turn27view8turn52view0
- Add-in side `apply_shell` selects a “top planar face” by scanning faces, filtering by planar + positive Z normal, then maximizing face bounding-box `max_z`. citeturn39view0turn52view0
- Freeform replay already has a *token-rebinding* selection mechanism for profiles based on recorded profile index/dimensions. citeturn49view2turn50view2

**Recommendations (high-level):** Implement a **SelectionTrace** as a *Tier 2 diagnostic artifact with provenance*, emitted at every non-trivial selection boundary (semantic selector resolution, heuristic edge/face selection, token rebinding), and attach it in a structured way that supports:
- verification gating explanations (why a selection is trusted or risky),
- failure recovery (what to inspect next),
- auditability and workflow hardening (what selection patterns repeatedly cause drift). citeturn48view0turn51view0turn49view0

**Minimal, high-value v1**: instrument **three** places first:
1) `mcp_server/primitives/core.py::find_face` (semantic selector resolution) citeturn11view2turn52view0  
2) `fusion_addin/ops/live_ops.py::apply_shell` (face-to-remove selection) citeturn39view0turn52view0  
3) `fusion_addin/ops/live_ops.py::apply_fillet` and `apply_chamfer` (heuristic edge selection) citeturn31view2turn27view8  

These three cover the repo’s most error-prone “geometry targeting” decisions (faces/edges) and align with the freeform guidance that booleans/targeting/direction require inspection and careful verification. citeturn49view0turn51view0

A required source (`internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`) was **not found in the public repository tree** under `internal/research/` on `master`. citeturn7view0 The analysis below relies on the other required repo sources.

## Why Selection Tracing Matters in ParamAItric

**Observed facts (repo-grounded):** ParamAItric’s core reliability contract is: validate → execute staged steps → verify → stop with structured failure context rather than compounding errors. citeturn47view0turn47view2turn50view2 The verification policy explicitly warns against collapsing all verification into a single bucket and requires verifications to be provenance-aware (what produced the signal, its stability, and whether it’s safe to hard-gate). citeturn48view0 Freeform guidance mandates inspection before risky mutations (plane/direction/booleans/body targeting) and treats booleans as high-risk drift points. citeturn49view0turn51view0

**Informed inferences:** Selection is the *bridge* between “structured intent” and kernel-executed geometry. When selection is wrong, the system can still “succeed” syntactically (a cut happens, a chamfer is applied), but the outcome is semantically incorrect—exactly the kind of silent drift the playbook warns against. citeturn51view0turn48view0 Additionally, because ParamAItric emphasizes entity-token references and replay/rollback, selection must remain debuggable under topology/timeline changes; selection traces provide the evidence needed to decide whether a failure is:
- incorrect selector intent,
- an ambiguous candidate set,
- topology instability causing token staleness,
- or an add-in heuristic mismatch. citeturn47view2turn48view0turn50view2

**Recommendations:** Treat SelectionTrace as a **first-class diagnostic artifact** (Tier 2 by default) with:
- explicit **intent vs resolution** separation,
- **candidate set characterization** (size, ambiguity, key filters),
- **resolved entity descriptors** (just enough geometry to confirm correctness),
- explicit **provenance** and **risk flags** aligned with the verification tiers. citeturn48view0turn52view0turn51view0

## Proposed SelectionTrace Schema

**Observed facts (repo-grounded constraints):**
- Tokens are opaque and should not be compared as semantic IDs. citeturn47view2
- Inspection surfaces already exist that produce structured face/edge geometry summaries (face types, normals, areas, bounding boxes; edge points and lengths). citeturn52view0turn28view1turn28view3
- The system already represents “verification_signals” as tiered, provenance-annotated structures. citeturn50view2turn48view0

**Recommendation: a JSON-serializable SelectionTrace v1.0**  
Below is a practical schema intended to be:
- stable and compact,
- useful in both the MCP server and Fusion add-in layers,
- compatible with freeform session logs (which currently serialize mutation `args`, `result`, and `verification`). citeturn49view2turn50view2

### SelectionTrace object (v1)

**Always present fields (required now):**
- `schema_version`: `"1.0"`
- `trace_id`: UUID string (unique per trace)
- `emitted_at`: ISO-8601 timestamp
- `emitter`:
  - `layer`: `"mcp_server"` | `"fusion_addin"`
  - `path`: repo path + function name (e.g., `"mcp_server/primitives/core.py::find_face"`)
- `context`:
  - `tool`: MCP tool/command name (e.g., `"apply_shell"`, `"find_face"`) citeturn52view0
  - `mode`: `"freeform"` | `"workflow"` | `"utility"` (inferred from caller)
  - `session_id`: if freeform session is active citeturn49view4turn49view2
  - `step`: freeform mutation step number if available (from `MutationRecord.step`) citeturn49view2
  - `workflow_name` + `stage`: when running staged workflows (when available via `_bridge_step` usage pattern) citeturn14view1turn15view0turn19view2
- `selection`:
  - `kind`: `"face"` | `"edge"` | `"profile"` | `"body"` | `"component"` | `"sketch"`
  - `intent`: **what was asked for**
    - `selector_type`: `"token_direct"` | `"semantic_axis_extreme"` | `"heuristic_edge_set"` | `"dimension_match"` | `"rebind_profile"` | `"other"`
    - `selector`: canonical selector payload (string or structured dict)
    - `why`: short operator/agent rationale (not raw chat text; ideally a manifest-feature reference or stage rationale) citeturn51view0turn49view0
  - `scope`: **where the selection was applied**
    - `body_token` / `sketch_token` / `target_body_token` as relevant
  - `algorithm`: **how it was resolved**
    - `name`: stable identifier (e.g., `"axis_extreme_bbox"`, `"top_planar_face_max_z"`, `"edge_set_interior_bracket"`)
    - `inputs_summary`: minimal scalar inputs (e.g., plane, axis, expected dims)
    - `determinism`: `"deterministic"` or `"heuristic"`
  - `candidates`:
    - `candidate_count`: integer
    - `filters_applied`: list of `{filter, retained_count, rejected_count}` (counts only)
    - `ambiguity`: `{is_ambiguous: bool, reason: str | null}`
  - `resolved`:
    - `entity_kind`: `"face"`/`"edge"`/…
    - `entity_token`: token string
    - `descriptor`: small geometry descriptor (see next section)
  - `outcome`:
    - `status`: `"resolved"` | `"no_match"` | `"ambiguous"` | `"error"`
    - `error`: short message if applicable
  - `summary`: one-line, human-readable summary
  - `risk`:
    - `level`: `"low"` | `"medium"` | `"high"`
    - `flags`: small list of stable codes (e.g., `"MULTIPLE_CANDIDATES_CLOSE"`, `"TOPOLOGY_FRAGILE"`)
    - `suggested_next_inspection`: one of the inspection tools (e.g., `"get_body_faces"`, `"get_body_edges"`) citeturn52view0turn49view0

### Essential vs optional vs noisy fields

**Essential (required now):** everything listed above. The key is that *intent*, *algorithm*, and *resolved descriptor* are always present; without those, the trace is not actionable.

**Optional later (high value, but not required in v1):**
- `candidates.top_k`: up to K=3 candidate summaries (token + 1–2 scalars + score/reason)
- `timing_ms`: resolution time (useful later for performance budgets)
- `stability_notes`: structured note about topology sensitivity (maps to verification-tier guidance) citeturn48view0turn51view0
- `checks`: list of small pass/fail checks that could be promoted to Tier 0 in narrow workflows (e.g., “exactly one profile matched expected dims”)—mirrors existing “expected body count” hard gates. citeturn50view2turn19view2

**Avoid (anti-noise):**
- full candidate dumps for large bodies (thousands of edges/faces)
- raw mesh data / point clouds
- arbitrary “debug strings” without stable structure
- storing raw user prompts or full conversational context (privacy + irrelevance to geometry targeting)
- parsing token strings for semantics (explicitly discouraged by the architecture note) citeturn47view2

## Example Traces for Current Operation Types

**Observed facts (repo-grounded selection mechanisms):**
- `find_face` selects a face by axis extreme using each face bounding box. citeturn11view2
- `apply_shell` selects the “top planar face” by planar geometry + positive Z normal + max bounding-box `max_z`. citeturn39view0
- `apply_chamfer` selects edges based on `edge_selection` (`interior_bracket` vs `top_outer`). citeturn31view2turn27view8
- Mock inspection payloads show what a face descriptor can look like: `{type, normal_vector, area_cm2, bounding_box}` and edges can look like `{type, start_point, end_point, length_cm}`. citeturn28view1turn28view3
- Freeform replay rebinding selects profiles by remembered index first, then by matching width/height. citeturn50view2turn49view2

Below are illustrative **v1** traces (schema above), written as representative JSON shapes (not claiming current repo already outputs these).

### Semantic face selection: `find_face` (“top”)

- `tool`: `find_face` citeturn52view0turn11view2  
- `algorithm`: `axis_extreme_bbox` (uses face bounding boxes; chooses max Z for “top”) citeturn11view2turn28view1  
- **Resolved descriptor** should include: face token, face type, normal vector (if available), and bounding-box min/max.

**Why it’s high value:** when “top” accidentally resolves to an internal planar face (e.g., a pocket floor) after topology changes, the trace can show the candidate distribution and why the wrong face won.

### Heuristic face selection inside a mutation: `apply_shell` (open top)

- `tool`: `apply_shell` citeturn52view0turn39view0  
- Selection steps (observable): filter planar faces, filter positive Z normal, choose max `max_z`. citeturn39view0  
- Resolved descriptor: face token + `normal_vector.z` + `bounding_box.max_z`

**Why it’s high value:** shell failures are often “wrong face removed” or “no face matched”; tracing makes these distinguishable.

### Heuristic edge selection: `apply_chamfer` (`edge_selection = top_outer`)

- `tool`: `apply_chamfer` with `edge_selection` present; the add-in branches based on selector. citeturn27view8turn31view2  
- Resolved descriptor: a small list (or capped sample) of edge tokens and a count; optionally include lengths. (Edge descriptors exist in inspection surfaces already.) citeturn28view3turn52view0

**Why it’s high value:** chamfers/fillets failing due to selecting tiny edges, internal edges, or non-manifold edges becomes explainable (“picked 48 edges, many below min length; top_outer classification ambiguous”), rather than a generic “Chamfer operation failed.” citeturn31view2turn51view0

### Freeform replay “selection”: profile token rebinding

- Mechanism: `_rebind_profile_token` tries remembered profile index first, then falls back to matching expected width/height. citeturn50view2turn49view2  
- Trace should capture:
  - old profile token and new sketch token,
  - whether index-based rebind succeeded,
  - if dimension-match fallback was used and whether it was ambiguous.

**Why it’s high value:** replay drift becomes diagnosable (“profile ordering changed; dimension match ambiguous; need a stronger selector”).

## Emission Rules

**Observed facts (repo-grounded operational rules):** Freeform mode requires one mutation then verification; it encourages inspection before risky mutations (plane/direction/booleans/targeting) and treats failures as structured results with diagnostics. citeturn49view4turn49view0turn48view0turn51view0

**Recommendations: automatic emission triggers (high-signal only)**

Emit a SelectionTrace automatically when **any** of the following occurs:

1) **Selector intent is semantic or heuristic**, not purely “token_direct.”  
This includes:
- `find_face` semantic selectors (`top/bottom/left/right/front/back`). citeturn52view0turn11view2
- `apply_shell` because it resolves a face to remove internally. citeturn39view0
- `apply_fillet` / `apply_chamfer` because they resolve an edge set internally (or by `edge_selection`). citeturn31view2turn27view8

2) **Candidate set size is not trivially 1**, or filtering is applied.  
Even if the algorithm is deterministic, if it chooses among many faces/edges/profiles, trace it.

3) **A selection boundary touches a high-risk operation class** (per freeform guidance): booleans and body targeting. citeturn51view0turn49view0  
In practice: cuts (especially when expected to preserve body count), combines, shells, and edge finishing.

4) **Any selection contributes to a failure path**:  
If the operation fails (exception or `ok: false` verification), include all selection traces produced since the last successful verification commit in the failure payload (see next section). citeturn48view0turn50view2

**Emission granularity recommendation:**  
- Default: **one trace per selection decision** (not per candidate).  
- Include `candidates.top_k` only when `risk.level != low` or `outcome.status != resolved`.

## Reporting and UI/Audit Implications

**Observed facts (repo-grounded output surfaces):**
- Freeform commit returns `verification_diff` and `verification_signals`, and on failure returns `ok: false` with rich structure and hints. citeturn49view4turn50view2
- Verification tiers explicitly reserve diagnostics for debugging/recovery. citeturn48view0turn51view0
- Freeform session logs already serialize each mutation’s `args`, `result`, and `verification`. citeturn49view2turn49view4
- Workflow failure infrastructure supports structured failure payloads via `WorkflowFailure.as_dict()` with `partial_result`. citeturn14view0turn10view0

**Recommendations: where traces should appear**

### Verification outputs
- **Do not** spam verification outputs with full traces by default.
- **Do** include:
  - a `diagnostics.selection_traces_summary` array in `commit_verification` responses (success or failure) containing `(trace_id, summary, risk.level)` for the *pending mutation*.  
  - optionally, include full traces behind an “expanded diagnostics” flag later.

This matches the repo’s “verification is provenance-aware” posture: traces are Tier 2 evidence supporting recovery, not a hard gate by default. citeturn48view0turn51view0

### Failure reports
For **structured failures** (workflow failure payloads or freeform verification failures), include:
- `diagnostics.selection_traces`: full list of traces produced since last stable checkpoint, capped (e.g., last 5 traces).
- `diagnostics.suspected_selection_trace_id`: when the failure classification is plausibly selection-related (e.g., shell could not find a top face; chamfer failed; unexpected body count after a cut). citeturn39view0turn50view2turn49view0

### Audit logs
Treat SelectionTrace as:
- `tier: diagnostic` (Tier 2) by default, with explicit `provenance` and `determinism` metadata. citeturn48view0turn50view2  
Over time, when a selection method is proven stable in a narrow workflow, a *derived check* might be promoted (e.g., “profile selection matched exactly one candidate”)—but the trace itself remains an audit artifact.

### Freeform session logs
Because the FreeformSession export includes the mutation `result`, embedding traces under a stable key (e.g., `result.diagnostics.selection_traces`) makes them automatically available in exported logs without changing log shape radically. citeturn49view2turn50view2

## Minimal First Implementation

**Observed facts (repo-grounded “first places to hook”):**
- `mcp_server/primitives/core.py::find_face` is already a semantic selector implementation that returns selected face token and face info. citeturn11view2turn52view0
- `fusion_addin/ops/live_ops.py::apply_shell` already contains an explicit internal face-selection loop with filters and a winner rule (planar + positive Z normal + max_z). citeturn39view0
- `fusion_addin/ops/live_ops.py::apply_fillet` / `apply_chamfer` already select an edge set but only return `edge_count` and (for chamfer) `edge_selection`. citeturn31view2turn27view8

**Recommendation: v1 implementation steps (minimal overhead, high value)**

1) **Define a shared SelectionTrace “wire format”**  
Create a small helper in both layers (can be duplicated initially), producing dicts that match the schema above and are JSON-serializable.

2) **Instrument `find_face` in the MCP server (server-side trace emission)**  
In `mcp_server/primitives/core.py::find_face`, build a trace with:
- intent selector (`top/bottom/...`),
- candidate_count = len(faces),
- resolved face token,
- descriptor = face_info subset (token, type, bounding_box; normal if present). citeturn11view2turn28view1  
Return:
- existing fields (`face_token`, `selector`, `face_info`) plus
- `diagnostics: {selection_traces: [trace]}`.

3) **Instrument `apply_shell` in the Fusion add-in (add-in-side trace emission)**  
Inside the existing face loop:
- count how many faces were scanned,
- count how many were planar,
- count how many passed positive Z normal,
- record the winner’s `max_z` and token,
- set `risk.level = high` if no candidate or if multiple candidates share the same `max_z` within tolerance. citeturn39view0turn48view0  
Return `diagnostics.selection_traces`.

4) **Instrument edge selection for `apply_fillet` / `apply_chamfer`**  
Without changing geometry behavior:
- record `edge_selection` branch and edge_count (already returned),
- add `edge_tokens_sample` (first N=10 tokens) + `edge_count_total`,
- set risk flags if edge_count is unexpectedly large (e.g., > 50) or zero.

This is explicitly aligned with the repo’s stance that face/edge counts are useful diagnostics but topology-fragile; therefore this stays Tier 2 evidence. citeturn48view0turn51view0turn31view2

5) **Freeform integration (no new protocol required in v1)**  
Because freeform mutation logging already stores raw `result`, once traces are embedded into results, they will be preserved in the session log automatically. citeturn49view2turn49view4  
Optionally (still minimal), modify `commit_verification` to surface a *summary* of the pending mutation’s selection traces under the verification output, consistent with “diagnostics attached” guidance. citeturn48view0turn50view2

## Risks and Anti-Patterns

**Observed facts (repo-grounded):** The repo explicitly warns against conflating weak signals into hard gates, and calls out topology-fragile signals (like face/edge counts) as diagnostics rather than correctness proof. citeturn48view0turn51view0 It also emphasizes that entity tokens are opaque and exist to avoid stale handles after timeline edits. citeturn47view2turn50view2

**Risks (and how to avoid them):**

1) **Turning SelectionTrace into “generic logging”**  
Anti-pattern: dumping every candidate face/edge in full detail for every call.  
Mitigation: cap candidate detail, record counts and top-K only when risk is non-low.

2) **Accidentally promoting topology-fragile heuristics into Tier 0 gates**  
Anti-pattern: failing a workflow because “face_count changed.”  
Mitigation: keep selection traces Tier 2 by default; only promote narrow, proven checks (e.g., “exactly one profile matched expected dims”) into Tier 0, and record provenance/accuracy explicitly. citeturn48view0turn50view2

3) **Encoding semantics into tokens**  
Anti-pattern: parsing token strings or comparing them to infer identity.  
Mitigation: store tokens only as references; rely on descriptors + re-resolution via inspection tools. citeturn47view2turn52view0

4) **Performance and payload bloat across the MCP boundary**  
Anti-pattern: large traces slow down the loopback protocol and clutter host UI.  
Mitigation: provide summaries by default; include full traces only on failures or when explicitly requested.

5) **Privacy leakage through traces**  
Anti-pattern: storing raw user prompts or full conversation context in traces.  
Mitigation: store only manifest/stage references and short rationales tied to modeling steps (consistent with freeform manifest discipline). citeturn51view0turn49view0

**What should be required now / optional later / avoided (concise decision list):**

- **Required now:** intent vs resolved separation; algorithm name; scope tokens; candidate counts + filter counts; resolved descriptor (minimal geometry); one-line summary; risk flags; provenance/determinism tags aligned with verification policy. citeturn48view0turn51view0turn52view0
- **Optional later:** top-K candidates; timing; stability scoring; richer descriptors (centroid, OBB) when available; trace-to-verification linking and promotion of proven checks into Tier 0 for narrow workflows. citeturn48view0turn51view0
- **Avoid:** full candidate dumps, raw geometry arrays, token parsing, and any “free text debug logs” that cannot be machine-summarized or compared across runs. citeturn47view2turn48view0