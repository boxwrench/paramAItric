# Executive Summary

- **Treat guided freeform as a transactional “candidate → verify → commit” synthesis loop, not a chat loop.** This is closely analogous to counterexample-guided inductive synthesis (CEGIS): generate a candidate, run a checker, and use counterexamples (verification diffs) to refine the next step. citeturn25view1  
- **Make verification data a first-class artifact (“geometry observables”) with stable, cheap primitives:** body count, oriented/aligned bounding boxes, volume/mass/centroid, and topological counts (faces/edges/loops/shells) are already practical/standard in Fusion-based programmatic pipelines (e.g., Fusion 360 Gallery dataset metadata). citeturn20view1turn22view0turn9view2turn13search5turn9view5turn18view0  
- **Design manifests as executable contracts, not prose.** Each manifest item should specify (a) a geometry target, (b) an acceptance test expressed in measurable predicates, (c) dependencies, and (d) explicit deferral policy. This is directly motivated by how parametric CAD systems combine a *parametric definition* + a *B-rep result*; ambiguity in naming/references is a known core CAD problem (persistent naming). citeturn23search1turn28view0  
- **Assume “persistent naming / unstable references” is a primary failure mode and build for it.** Fusion exposes entity tokens for entities like faces; tokens are explicitly *not stable strings* and must be resolved via lookup, not compared. Also, B-rep entity IDs can map to multiple entities after splits. citeturn9view4turn15view4  
- **Add rollback checkpoints as a safety primitive, implemented as timeline-aware transactions.** Fusion custom-feature documentation highlights transaction boundaries, preview abort behavior, and why timeline rollback must be isolated using command steps. This same idea should underwrite “one mutation before verification” so recovery never requires re-generating geometry blindly. citeturn17search11  
- **Use CAD-kernel realities to guide reliability decisions:** Fusion/Inventor are built on Autodesk Shape Manager; kernel + proprietary feature tree separation affects what is verifiable from geometry alone (and what is lost in translation). This is directly relevant when you rely on geometry-derived audits rather than fully semantic feature trees. citeturn27view0turn27view1turn28view0  
- **Promote “inspection-first” behavior: measuring and interrogating B-rep should be the default before high-risk mutations (planes, normals, booleans).** Fusion APIs explicitly support oriented bounding boxes and minimum distance measurement across many geometry types; these map cleanly to your “inspection tools remain available while locked” concept. citeturn12view0turn12view1turn6search32turn28view0  
- **Make feature health a gating signal.** Fusion exposes `Feature.healthState` and feature-specific `errorOrWarningMessage` patterns; treat warning/error as hard blocks for commit unless explicitly deferred with rationale. citeturn15view0turn15view1  
- **Benchmarking should be spec-driven and regression-oriented, not “recipe replay.”** The Fusion 360 Gallery dataset and Gym demonstrate that sequential CAD construction is naturally modelable as stepwise decisions; your benchmarks should similarly define deterministic pass/fail predicates per step and at session end. citeturn21view0turn22view0  
- **Highest-leverage primitives for the next 1–3 cycles:** (1) rollback checkpoints + session replay, (2) stable reference handles (token + semantic selector), (3) a verification API returning structured diffs and counterexamples, (4) richer construction-plane and measurement primitives, (5) tooling to auto-promote stable recipes into deterministic macros with evidence. citeturn17search11turn15view4turn12view0turn15view2  

## Freeform Method Model

ParamAItric’s *guided freeform* mode is best modeled as **incremental program construction over a parametric CAD state**, gated by a verifier. In contrast to deterministic `create_*` workflows, guided freeform is operating in the regime where:

- the agent **does not know** the correct next step a priori,
- mistakes are expected,
- safety must be preserved by restricting the action surface (constrained primitives),
- progress must be measured against a **completion contract** (feature manifest),
- and **state transitions are explicit** (`AWAITING_MUTATION` ↔ `AWAITING_VERIFICATION`).

This matches a well-studied pattern in synthesis: generate a candidate, check it, and use the check result (including counterexamples) to drive the next candidate. In CEGIS, the candidate is a program and the checker is a validator; in guided freeform CAD, the candidate is a *single mutation* (primitive CAD step), and the checker is your verification system. citeturn25view1  

### Why a verifier-gated mutation loop is useful in CAD specifically

CAD modeling is not just geometry; it is **history + geometry + references**. Even in mature parametric modeling systems, there is a known duality: a **parametric definition** (feature/history) and a **boundary representation (B-rep)** of the resulting shape. A brittleness point is how references from parametric features map onto evolving B-rep entities (“persistent naming problem”). citeturn23search1turn28view0  

A verifier-gated approach is valuable here because:

- It treats **regeneration brittleness as normal**, not exceptional.
- It forces the agent to earn the right to proceed via checkable evidence, reducing “plausible but wrong” drift.
- It creates a natural locus for recovery: the system can lock, expose inspection APIs, and require the agent to reconcile mismatches using observations rather than speculation.  
- It aligns with how Fusion automation is already structured: features are API objects, and analysis (“inspecting the B-rep”) is a distinct capability from “creating features.” citeturn15view3turn28view0  

### What “guided freeform” is (and is not) in this research brief

This brief treats guided freeform as:

- **History-based parametric modeling through constrained primitives** (sketches, features, bodies, planes, booleans, patterns), plus inspection.
- **Strict step gating**: one mutation, then verification or recovery.
- A **manifest contract**: the session ends only when all target features are either satisfied or explicitly deferred with reason.

This brief explicitly does **not** treat guided freeform as:
- text-to-mesh generation,
- organic sculpting,
- or unconstrained “generate a full model” autonomy.

## Relevant Prior Art

This section splits prior art into **directly relevant CAD / Fusion-adjacent evidence** and **adjacent-but-useful control-loop and verification thinking**. Cross-domain items are explicitly labeled as such.

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["Fusion 360 timeline feature history screenshot","boundary representation B-Rep topology faces edges loops diagram","Fusion 360 combine join cut intersect dialog","Fusion 360 sketch constraints fully constrained example"],"num_per_query":1}

### Directly relevant

**Fusion 360 Gallery Dataset + “Fusion 360 Gym”: sequential CAD as a decision process.**  
Willis et al. define a simple CAD “language” (sketch + extrude operations) and publish **8,625 human design sequences**, plus an environment (“Fusion 360 Gym”) that exposes sequential construction as a **Markov decision process**. While not your exact primitive set, it is strong direct evidence that (a) sequential CAD construction is a coherent workload, and (b) benchmarking can be spec’d as stepwise state transitions rather than end-only scoring. citeturn21view0turn22view0  

**Fusion 360 Gallery Assembly metadata: what’s practical to verify automatically.**  
The Assembly dataset documentation enumerates geometry/physics metadata that is immediately aligned with ParamAItric-style verifications: `vertex_count`, `edge_count`, `face_count`, `loop_count`, `shell_count`, `body_count`, `surface_types`, and a `bounding_box` for the assembly. This is direct evidence that these observables are both computable and useful at scale for CAD regression tasks. citeturn20view1turn22view0  

**B-rep and evaluation fundamentals in Fusion/Inventor automation.**  
Brian Ekins’ Autodesk University handout lays out the practical reality: solids are represented as **surfaces enclosing volume** (B-rep), and the kernel can compute mass properties because the volume is closed. It also emphasizes topology vs geometry and, critically for agent systems, how to **find faces/edges without manual selection**—exactly the difficulty your agent faces. citeturn28view0turn29view3turn29view2  

Two API-relevant points from this handout matter directly for guided freeform reliability:

- **Normals and evaluators:** The surface evaluator can compute normals and (for solids) normals are defined to point outward; evaluators are preferred over “raw geometry objects” because they account for the body context. citeturn29view2turn29view1  
- **“Tear-off” snapshot geometry objects:** geometry objects retrieved from the B-rep entity do **not** stay linked; they are snapshots and must be re-queried after edits. This is a common hidden failure mode in inspection/recovery logic. citeturn29view0turn29view3  

**Fusion APIs that support your verification and recovery primitives.**  
Key inspection-supporting API affordances include:

- **Mass/physical properties:** `BRepBody.physicalProperties` returns properties (area/density/mass/volume/moments) but uses low calculation accuracy by default; higher accuracy is available through APIs like `WorkingModel.physicalProperties` with an explicit accuracy setting (default is ±1% error margin). citeturn13search5turn9view5  
- **Bounding boxes:** `Component.boundingBox` (world-space bounding box) and `Component.orientedMinimumBoundingBox` (tight-fitting oriented bounding box for B-rep bodies, introduced Jan 2024) support robust dimensional checks even under rotations. citeturn13search8turn9view2  
- **More controlled oriented bounds:** `MeasureManager.getOrientedBoundingBox` can compute an oriented bounding box given explicit length/width direction vectors and requires perpendicular vectors (useful for “hole normal” discipline checks). citeturn12view0  
- **Distance inspection:** `MeasureManager.measureMinimumDistance` measures minimum distance and returns the two witness points, supporting clearance checks and “are these faces actually touching?” sanity tests. citeturn12view1  
- **Stable-ish references:** `BRepFace.entityToken` explicitly supports saving a token and later resolving via `Design.findEntityByToken`, with clear warnings about tokens as unstable strings. Additionally, `BRepBody.findByTempId` can retrieve all entities matching an ID (and documents the “multiple matches after split” case). citeturn9view4turn15view4  
- **Feature-level health gating:** `Feature.healthState` and feature-specific `errorOrWarningMessage` provide explicit signals for “the model is unhealthy” at the feature graph level. citeturn15view0turn15view1  
- **Construction plane richness:** The Construction Plane API sample demonstrates creating planes by offset, **by angle**, by tangent, by two planes, etc.—meaning “angled sketch planes” are not a speculative primitive; they exist and are scriptable. citeturn15view2  
- **Boolean semantics + pitfalls:** Fusion’s Combine tool has explicit semantics (Join/Cut/Intersect). Importantly, Cut can depend on **visibility** of bodies for which bodies “participate,” a sharp edge for agent systems. This needs to be modeled in verification and tool wrappers. citeturn18view0turn18view1  

**Custom features and transaction semantics: why rollback/checkpoints are realistic.**  
Fusion’s Custom Features documentation describes (a) grouping several features into one node, (b) compute/edit behavior, and—most relevant—how commands and preview use **transaction steps** and how timeline rollback interacts with aborted transactions. This is direct evidence that “checkpointing” is a natural concept in Fusion’s automation model, not an external invention. citeturn17search11  

### Adjacent but useful (explicitly inference)

**Persistent naming problem as the root of reference brittleness (cross-system, but CAD-direct).**  
Bidarra et al. characterize persistent naming as a serious difficulty in parametric solid modeling: referring to topological entities across edits can yield unpredictable behavior, even for simple changes. This is direct CAD evidence, and it motivates designing manifests and verifiers that do not assume stable face IDs. citeturn23search5  

**CEGIS / counterexample-driven loops (adjacent-domain inference).**  
CEGIS couples an inductive synthesizer with a validation procedure: failed validation yields a concrete witness (counterexample) that is fed back to refine the next candidate. Mapping to ParamAItric: a failed verification should yield a structured “counterexample” (which invariant failed, which bodies/faces witness it, what delta occurred), not a generic “failed.” This mapping is inference, but the loop pattern is concrete. citeturn25view1  

## Failure Taxonomy

The taxonomy below is engineered for **guided freeform CAD** where each step is a constrained mutation followed by verification. Classifications are:

- **Block:** must not commit; requires recovery or explicit deferral.
- **Warn:** can commit, but must be recorded; likely needs later correction or stronger verification.
- **Defer:** allowed only if the manifest explicitly permits deferral for that feature type and the audit records rationale and residual risk.

> Notes on evidence: The failure modes are grounded in CAD realities (B-rep duality, persistent naming, manifoldness, boolean semantics) and Fusion’s API affordances for detection (healthState, measure, bounding boxes, physical properties, entity token behavior). citeturn23search5turn29view3turn15view0turn12view1turn9view4turn18view0turn16view1  

| Failure mode | Description | Why it happens | How to detect (checkable signals) | Recovery pattern | Block/Warn/Defer |
|---|---|---|---|---|---|
| Wrong archetype choice | Agent selects an incorrect high-level construction strategy (e.g., builds bracket as single extrude when it needs multi-body + combine) | Under-specified manifest; insufficient early “shape signature” checks; premature commitment | Early “shape signature” mismatch: body count, OBB/AABB dimensions, volume range, face-type counts drift from expected envelope citeturn20view1turn9view2turn13search5 | **Rollback checkpoint** → run inspection to identify required operations → re-plan with explicit subgoals (manifest decomposition) | Block (unless manifest allows “exploratory branch” mode; inference) |
| Wrong sketch plane | Sketch created on incorrect plane/face, leading to mislocated features | Weak plane-selection discipline; unstable references; misunderstanding component coordinate frames | Bounding box/centroid shift inconsistent with intended step; face normals/evaluator-based orientation inconsistent (e.g., feature normal not aligned) citeturn12view0turn29view2turn29view1 | Rollback; re-select plane using explicit construction plane methods (offset/angle/tangent) rather than implicit face pick citeturn15view2 | Block |
| Wrong cut/extrude normal | Hole or cut direction is wrong (e.g., normal flipped or not perpendicular) | Ambiguous “side”; sketch plane orientation confusion; geometry-based assumptions | Use surface evaluators / geometry type checks; compare expected direction vectors (e.g., for OBB length/width vectors) citeturn12view0turn29view2 | Rollback; enforce a “normal discipline” verification that must pass before commit | Block |
| False confidence after plausible but incomplete geometry | The part looks plausible but missing required features / constraints | Over-reliance on visual plausibility; missing manifest-to-geometry linkage | Manifest items unresolved at audit; missing topological signatures (hole count/face types) citeturn20view1turn22view0turn13search2 | Lock session; run systematic inspection; require explicit “resolve or defer” at audit with reason | Block at end-of-session audit; Warn mid-session |
| Monotonic-volume assumption failure | Agent assumes volume changes monotonically or in expected direction; non-monotonic features break it (e.g., stepped boss plate) | Boolean/nonlinear operations; subtractive features; multi-body workflows | Track per-step Δvolume and ΔAABB/OBB; compare to expected sign/range per manifest stage citeturn13search5turn9view2turn9view5 | Add per-step “expected delta” constraints; if violated, rollback and re-run plan with explicit delta sign allowances | Warn if within bounds but unexpected; Block if outside tolerance |
| Uncombined multi-body artifacts | Ends with multiple bodies when design expects one, or leftover tooling bodies remain | Combine tool usage errors; “Keep Tools” semantics; visibility affecting Cut participation | Body count mismatch; boolean op not applied; audit check on `body_count` citeturn20view1turn18view0turn18view1 | Provide “combine-to-target” primitive with explicit target/tool sets; verify post-combine body count; ensure visibility rules are enforced/normalized | Block (if body-count contract exists) |
| Boolean ambiguity / failure | Combine fails (kernel can’t resolve), or produces unexpected topology | Sliver faces, near coincidence, non-manifold topology, singularities | Feature `healthState` warns/errors; end result fails manifoldness heuristics; boolean creates non-manifold edges or ambiguous topology citeturn15view0turn16view1 | Recovery: reorder timeline / split into helper bodies / add supporting features; if blocked, defer with explicit manufacturing risk | Block unless deferrable |
| Non-manifold / singularity-induced downstream errors | Geometry becomes non-manifold or includes singularities that break later ops (offsets/fillets) | Kernel limitations; pathological topology: edges shared by >2 faces, pinch vertices, convergent isocurves | Health warnings; explicit topology checks (edges shared by >2 faces); symptoms like failed fillet/offset; Fusion guidance highlights non-manifold conditions and mitigation (reorder timeline, create multiple bodies, temporary supporting features) citeturn16view1turn15view0 | Rollback; alter construction to avoid non-manifold; insert temporary features; consider boundary patch alternatives (surface workflows) | Block |
| Locked-state dead end | After a failed verification, the agent cannot proceed because it lacks tools to recover while locked | Insufficient inspection tools; no rollback; no “repair primitives” allowed in locked state | System state machine indicates stuck; repeated verification failures without new evidence | Add minimal recovery primitives allowed while locked: rollback-to-checkpoint, selection repair, manifest adjustment (deferral) with audit trail (inference) | Block |
| Target-feature drift | Agent progresses but gradually deviates from intended feature manifest (wrong offsets, wrong reference faces) | Unstable references; underspecified acceptance tests; “tear-off” geometry snapshots | Compare per-step observables against manifest tolerances; reference validation via token resolution (`entityToken` must be resolved, not compared) citeturn9view4turn29view0turn29view3 | Re-anchor references using semantic selectors (e.g., “largest planar face with normal +Z”); store both tokens and computed descriptors | Warn early; Block if drift exceeds bounds |
| Reference invalidation / topological naming break | Stored face/edge references no longer point to intended geometry after edits | Persistent naming problem; topology changes (split/merge faces) | Token resolution returns different entity than expected; `findByTempId` returns multiple matches; feature dependencies break; known parametric brittleness citeturn23search5turn9view4turn15view4 | Recovery by re-identification: semantic matching on surface type + normal + location + adjacency; then rebind tokens | Block if affects critical features; Defer if cosmetic and allowed |
| Visibility-dependent operation mismatch | Combine Cut affects unexpected bodies due to visibility rules | Fusion Combine behavior: bodies affected determined by visibility for cut operations | After Cut, unexpected body count/topology changes; mismatch against predicted delta; explicit note about visibility in Combine tips citeturn18view0 | Normalize visibility state in tool wrapper; make “visibility” an explicit input to mutation primitive | Block |

## Design Implications For ParamAItric

This section translates the evidence above into concrete repo-relevant design implications, anchored on your existing concepts: mutation/inspection/session tool classes, the two-state machine, manifest contract, and compliance audit.

### Session state machine and tool allowlists

1) **Add an explicit “transaction boundary” abstraction around the single mutation.**  
Fusion scripting and custom feature workflows show that multiple low-level actions can be grouped into a single command transaction, and preview behavior can abort back to a step marker; timeline rollback has special constraints. Use this as the mental model: **a mutation is a transaction**, and verification either commits or rolls back to the last checkpoint. citeturn17search11  

2) **Tool allowlists should be state-dependent, but allow minimal recovery even while locked.**  
Your “inspection tools remain available while locked” is aligned with Fusion’s strong inspection APIs (distance measure, oriented bounds, B-rep interrogation). But the failure taxonomy shows you also need a *very small* set of “locked recovery tools” (e.g., rollback checkpoint, manifest deferral) to avoid dead ends. The need is inference; the feasibility is supported by Fusion’s transaction model and inspection affordances. citeturn17search11turn12view1turn12view0  

3) **Normalize risky UI-derived conditions into explicit tool parameters.**  
The Combine tool’s Cut operation has visibility-dependent participation semantics. If your agent can invisibly change visibility, your verifier must either (a) freeze visibility during guided freeform, or (b) include visibility state in the mutation contract and verification. citeturn18view0  

### Manifest handling: make the manifest executable and reference-safe

4) **Represent each feature target as “intent + acceptance test + evidence handle.”**  
Because “feature tree” intelligence is not fully recoverable from geometry (and cross-tool translation strips parametric intelligence), your manifest must define what you can check from the state you actually have: the Fusion model + API access. citeturn27view0turn28view0  

A practical manifest item shape for guided freeform:

- **Intent:** e.g., “Two mounting holes on face X, normal to plane, diameter D, spacing S.”
- **Acceptance test:** measurable predicates (counts, axes, bounding boxes, minimum distances).
- **Evidence handle(s):** resolved entity references (tokens) plus semantic descriptors for re-identification.

5) **Store references as “token + semantic selector,” never token-only.**  
Fusion entity tokens are explicitly not stable as strings and must not be compared; they must be resolved to entities for comparison. Also, temp IDs can map to multiple entities after splits. This supports a design where:  
- token lets you re-fetch “the same” entity when it still exists,  
- semantic selector re-identifies when the entity changed due to topological edits. citeturn9view4turn15view4turn23search5  

A semantic selector should be simple and robust:
- surface type (planar/cylindrical/etc),  
- approximate normal direction (for planar faces),  
- relative location (centroid or a point-on-face),  
- adjacency counts / expected area range.  
Fusion supports point-on-face sampling for faces, which helps build location descriptors. citeturn13search11turn29view2turn29view1  

### Verification APIs: structure, tiers, and counterexamples

6) **Define a two-tier verification system: step-verifier (fast) vs audit-verifier (deep).**  
Direct evidence shows many checks are cheap and stable:
- `body_count`, topological counts, surface type distributions, and bounding boxes are used as dataset-scale metadata. citeturn20view1turn22view0  
- Physical properties are available with explicit accuracy controls. citeturn9view5turn13search5  

Recommended tiers:

- **Tier 0 (commit gate, fast):**  
  - feature healthState must be OK (no warning/error) unless explicitly allowed citeturn15view0turn15view1  
  - body_count constraint citeturn20view1turn18view0  
  - AABB/OBB ranges on target component citeturn13search8turn9view2  
  - Δvolume/Δcentroid bounds (coarse) citeturn13search5turn9view5  

- **Tier 1 (audit, deeper):**  
  - face/edge/loop/shell counts and surface types citeturn20view1turn29view3  
  - manifoldness heuristics and known kernel pitfalls (non-manifold topology conditions) citeturn16view1  
  - targeted geometric validations (min distances/clearances; axis alignment) citeturn12view1turn12view0turn29view2  

7) **Return “structured counterexamples” from verification failures.**  
Borrowing from CEGIS, a failure should produce:
- the violated predicate,
- the concrete witness (body/face tokens, measured points/distances, offending bounding box/centroid),
- and a minimal diff summary (what changed since last checkpoint).  
This is inference as an engineering design, grounded in the fact that CEGIS relies on counterexamples to refine the generator. citeturn25view1  

### Inspection tools: practical recovery workflows

8) **Prefer evaluator-driven geometry checks over raw geometry “tear-offs.”**  
Ekins’ handout is explicit: raw geometry objects are snapshots (“tear off”) and normals from raw geometry are not guaranteed to reflect body context; evaluators incorporate body context and can guarantee outward-pointing normals for solids. For reliable inspection, always re-fetch geometry and prefer evaluator APIs. citeturn29view0turn29view1turn29view2  

9) **Add visualization aids for inspection-driven recovery (optional, but high leverage).**  
Fusion’s custom graphics documentation shows you can draw custom graphics entities, including using B-Rep bodies as graphics and leveraging Fusion’s level-of-detail meshing. This can support “highlight candidate faces/bodies” during locked inspection without changing geometry. citeturn11search10turn13search4turn29view3  

### Benchmark corpus and workflow promotion path

10) **Benchmarks should be defined as “manifest + allowed primitives + verification suite,” not just a recipe transcript.**  
The Fusion 360 Gym framing reinforces that sequential design can be represented as a controlled decision process; your benchmark harness should similarly enforce stepwise reproducibility and deterministic pass/fail. citeturn21view0turn22view0  

11) **Promotion from freeform → structured macros should be evidence-driven.**  
Fusion custom features exist precisely because “a logical feature spans multiple timeline nodes” and becomes hard to edit/maintain; your repo should promote patterns into deterministic macros when you can *prove* (via benchmark statistics and low variance outcomes) that the pattern is stable. citeturn17search11  

## Recommended Changes

| Priority | Recommendation | Why it matters | Expected impact | Implementation difficulty | Dependencies | Confidence | Direct evidence or inference |
|---|---|---|---|---|---|---|---|
| Now | Introduce **checkpointed rollback** as a first-class primitive (pre-mutation snapshot → post-mutation attempt → rollback on failure) | Eliminates locked-state dead ends; enables safe recovery; aligns with Fusion transaction/timeline realities citeturn17search11 | Very high reliability + recoverability | Medium (requires careful transaction/timeline handling) | Session state machine; logging; deterministic snapshot definition | High | Direct evidence (Fusion transaction model) + inference (repo architecture mapping) |
| Now | Implement a **verification API that returns structured diffs + witnesses** (counterexamples) | Turns failures into actionable feedback; reduces hallucinated recovery; mirrors proven synthesis loops citeturn25view1 | High (fewer retries, faster convergence) | Medium | Geometry observables extraction; schema | Medium | Inference (CEGIS mapping), supported by CEGIS evidence |
| Now | Add **Tier 0 commit gate**: feature `healthState` + body_count + OBB/AABB + Δvolume/Δcentroid bounds | Catches most catastrophic failures cheaply; avoids compounding errors over steps citeturn15view0turn20view1turn9view2turn9view5 | High | Low–Medium | Geometry observables; tolerances | High | Direct evidence (APIs + dataset metadata) |
| Now | Make **reference handles** be `entityToken + semantic selector` (never token-only), and build rebind logic | Persistent naming/references are expected failures; token strings are unstable; splits yield multiple matches citeturn9view4turn15view4turn23search5 | High | Medium–High | Selector design; face/edge descriptors; inspection functions | High | Direct evidence (token semantics) + direct CAD evidence (persistent naming paper) |
| Next | Expand inspection toolset: `measureMinimumDistance`, `getOrientedBoundingBox`, evaluator-based normals/areas | Directly supports your locked-state inspection-driven recovery; enables clearance, alignment, and plane/normal discipline checks citeturn12view1turn12view0turn29view2turn29view1 | High | Medium | Tool wrappers; stable selection inputs | High | Direct evidence (API docs) |
| Next | Add **construction plane primitives** (by angle/tangent/offset) explicitly to mutation allowlist | Fixes wrong-plane and wrong-normal failures; makes “angled sketch planes” a controlled primitive, not an ad-hoc choice citeturn15view2 | High | Medium | Plane selection policy; verification of resulting orientation | High | Direct evidence (API sample) |
| Next | Normalize visibility and boolean semantics in wrappers (e.g., Combine Cut visibility rule) and verify post-boolean invariants | Prevents invisible state from changing meaning of operations; reduces multi-body artifact rates citeturn18view0turn18view1 | Medium–High | Medium | Visibility controls; body set enumeration | Medium | Direct evidence (Combine doc) + inference (wrapper policy) |
| Next | Add an “audit-grade” verifier tier with topological counts + surface types + manifoldness heuristics | Closes gap where Tier 0 passes but geometry is subtly wrong; aligns with what’s used at dataset-scale for CAD analytics citeturn20view1turn16view1turn29view3 | Medium–High | Medium–High | Efficient topology traversal; tolerances | Medium | Direct evidence (metadata + non-manifold conditions) |
| Later | Integrate optional feature recognition checks (holes/pockets) where available (Manufacturing Extension) for richer manifest predicates | Provides semantic-level verification when you can use it; reduces need for fragile geometric inference for certain features citeturn13search2turn6search27 | Medium | High (license/extension dependency) | Manufacturing Extension availability; stable selection | Medium | Direct evidence (sample exists) + practical constraint risk |
| Later | Add “promotion pipeline” tooling: export logs + manifests + verified macro candidates | Makes promotion repeatable; supports evidence thresholds; reduces architecture drift between freeform and structured modes citeturn22view0turn17search11 | Medium–High | Medium | Logging format; macro DSL; benchmark infra | Medium | Inference, supported by dataset + custom feature motivations |

## Benchmark Strategy

A strong benchmark suite for guided freeform CAD must test **reliability under constrained primitives** and **recoverability under verifier gating**, not “how pretty the output looks.”

### Task categories

Benchmarks should be grouped by the capabilities they stress, with each case defined as:

- initial state (empty doc / template),
- allowed mutation primitives,
- manifest contract (acceptance tests, deferrals allowed),
- and deterministic verifications per step + at audit.

Recommended categories aligned to your FM-A…FM-E plus additional coverage:

- **Archetype discipline:** tests whether the agent chooses the correct high-level build strategy early (e.g., “bracket requires base + cutouts + fillets” vs “single extrude”).  
- **Plane/normal discipline:** asymmetric features where incorrect plane/normal yields plausible but wrong results; use OBB vector checks and evaluator normals where possible. citeturn12view0turn29view2  
- **Non-monotonic reasoning:** steps where volume must increase then decrease (boss plate with subtractive features); enforce Δvolume constraints. citeturn13search5turn9view5  
- **Multi-body correctness:** explicit combine workflows with body-count compliance; include visibility rule traps for Cut. citeturn18view0turn20view1  
- **Failure + recovery:** intentional wrong mutation, lock, inspection-driven recovery, rollback, and successful completion (your FM-E). The need is internal; the feasibility is supported by inspection APIs and transaction semantics. citeturn12view1turn17search11  
- **Reference brittleness:** cases where topology changes (splits/merges) should break naive references; require token + semantic rebind. citeturn23search5turn9view4turn15view4  
- **Kernel pathology:** non-manifold and singularity situations to ensure the system handles modeling failure gracefully and blocks unsafe commits. citeturn16view1turn15view0  

### Required failure-mode coverage

For each benchmark, explicitly tag which failure modes it is expected to trigger (at least one benchmark per high-severity failure in the taxonomy). Track:

- detection precision/recall for each failure type (did verifier catch it?),
- recovery success rate and number of rollback cycles,
- audit deferral correctness (if allowed).

### Mock-tested vs live-tested

Because CAD behavior depends on the kernel and feature regeneration, you need both:

**Mock-tested (fast CI):**
- session state machine invariants,
- manifest parsing and resolution logic,
- verification predicate evaluation *on synthetic observables*,
- log serialization and deterministic replay of tool calls.

**Live-tested (Fusion integration):**
- geometry observables extraction (physical properties, bounds, counts),
- reference token resolution and rebind,
- boolean semantics and visibility interactions,
- feature health state behavior and messages,
- construction plane creation and sketch placement.

The Fusion 360 Gallery Dataset underscores that large-scale CAD analytics is feasible, but it does not remove the need for live integration tests because your system depends on the real kernel and feature tree execution. citeturn22view0turn27view0turn17search11  

### Metrics for success and regression tracking

At minimum, track:

- **Pass rate** by benchmark and by category (per commit).
- **Mean mutations to completion** and distribution (p50/p90/p99).
- **Mean rollback count** (recoverability efficiency).
- **Verification failure localization quality** (how often the structured counterexample points to the correct cause; inference but measurable).
- **Drift metrics:** cumulative deviation of bounding box, volume, centroid relative to manifest tolerances over steps. citeturn9view2turn9view5  
- **Reference stability metrics:** rate of successful token resolution vs rebind; frequency of `findByTempId` multi-hit scenarios. citeturn9view4turn15view4  

## Promotion Rules

Promotion from freeform recipes to structured workflows should be treated as **compilation from “exploratory synthesis traces” into deterministic macros** with required evidence.

### Proposed explicit promotion rules

A freeform recipe becomes a structured workflow (`create_*` macro) only if all are true:

1) **Stable preconditions are enumerated.**  
The recipe must state (and the system must verify) the required starting conditions: design history mode expectations, target component/body existence, and required reference entities. (Inference, but aligns with parametric vs geometry reality and feature tree dependence.) citeturn27view0turn23search5  

2) **The recipe is reproducible under live testing.**  
Run the recipe N times (suggest N≥30) under identical starting docs and tool versions and achieve:  
- 0 catastrophic failures,  
- ≥(N−1) exact passes (allowing for minor numeric tolerance).  
(Inference; engineering threshold.)

3) **The recipe has a complete manifest with Tier 0 + audit verifications.**  
Promotion requires a manifest whose acceptance tests are all machine-checkable and rely on supported observables: bounds, physical properties, topology counts, feature health. citeturn20view1turn15view0turn13search5turn9view2  

4) **Reference strategy is robust.**  
Any reference to faces/edges must be expressed as token + semantic selector, and the macro must include rebind logic (or avoid fragile references) because persistent naming issues are endemic. citeturn23search5turn9view4turn29view0  

5) **Complex multi-node patterns are grouped intentionally.**  
If the “logical feature” spans multiple timeline nodes, structured promotion should consider grouping/abstraction: Fusion’s custom feature concept exists because multi-node logical features are hard to manage. (Inference for ParamAItric macros; direct evidence that the pain exists in Fusion.) citeturn17search11  

6) **Benchmark evidence shows value.**  
Promotion must reduce cumulative benchmark cost: fewer rollbacks, higher pass rate, lower variance. If deterministic macro does not improve metrics, it stays freeform.

## Open Questions

### Must answer soon

- **What exact set of “geometry observables” will be your stable, versioned contract?** The Fusion 360 Gallery metadata suggests a strong starting set (counts, surface types, bounding box), but ParamAItric needs precise definitions and tolerances. citeturn20view1turn22view0  
- **How will semantic selectors be defined to avoid brittleness while remaining implementable?** E.g., “largest planar face with normal +Z” sounds easy, but needs deterministic tie-breakers and adjacency rules to handle topology changes. citeturn23search5turn29view3  
- **What is the minimal “locked recovery” toolset that preserves safety without reintroducing risk?** Rollback seems required, but what else (deferral edits, reference rebind) should be permitted while locked? (Inference.) citeturn17search11turn9view4  
- **How will you model Combine/Cut visibility semantics in your tool interface?** Should visibility be frozen, normalized, or made explicit? citeturn18view0turn18view1  
- **What is the exact promotion evidence threshold?** N-runs, tolerance thresholds, and regression requirements need to be codified for engineering velocity.

### Worth exploring later

- **Can Manufacturing Extension feature recognition (holes/pockets) be used as a semantic verifier for certain manifests?** This could reduce fragile geometric inference, but may limit availability. citeturn13search2turn6search27  
- **Can you adopt/align with public dataset schemas (Fusion 360 Gallery) for internal benchmarks?** This could improve interoperability and measurement reuse. citeturn22view0turn20view1  
- **Should you incorporate geometry-kernel pathology tests (non-manifold, singularities) as a formal benchmark class?** Fusion’s own guidance suggests this is a recurring source of modeling failures. citeturn16view1  

## Source Notes

- **Fusion 360 Gallery / Fusion 360 Gym paper (SIGGRAPH 2021; arXiv)** — *Academic paper*; direct evidence that sequential CAD construction can be formalized as a decision process, and that a dataset of 8,625 human sketch+extrude sequences exists for benchmarking sequential generation. **Direct CAD evidence.** citeturn21view0  
- **Fusion360GalleryDataset repository (Autodesk AI Lab)** — *Open-source dataset + tooling docs*; provides dataset sizes (assemblies, sequences, segmentation) and emphasizes sequential design data and per-face operation segmentation, relevant for benchmark design and potential manifest/verification features. **Direct CAD evidence.** citeturn22view0  
- **Fusion360GalleryDataset assembly metadata docs (GitHub)** — *Dataset schema documentation*; explicitly lists geometric/topological/physical metadata (counts, surface types, bounding box) aligning with ParamAItric verification metrics. **Direct CAD evidence.** citeturn20view1  
- **Fusion API docs: `BRepBody.physicalProperties`, `WorkingModel.physicalProperties`** — *Official API reference*; supports volume/mass/centroid/moments computations and exposes calculation accuracy controls and aggregate properties over object collections. **Direct CAD evidence.** citeturn13search5turn9view5  
- **Fusion API docs: bounding boxes and measurement (`Component.boundingBox`, `Component.orientedMinimumBoundingBox`, `MeasureManager.getOrientedBoundingBox`, `MeasureManager.measureMinimumDistance`)** — *Official API reference*; supports AABB/OBB inspection and distance witness points, enabling robust verifier checks and locked-state inspection tools. **Direct CAD evidence.** citeturn13search8turn9view2turn12view0turn12view1  
- **Fusion API docs: entity tokens and temp IDs (`BRepFace.entityToken`, `BRepBody.findByTempId`)** — *Official API reference*; documents token-string instability and multi-entity matches after splits, directly motivating reference-safe manifest design and rebind logic. **Direct CAD evidence.** citeturn9view4turn15view4  
- **Fusion API docs: feature health (`Feature.healthState`, `errorOrWarningMessage`)** — *Official API reference*; provides explicit health signals that should be gating checks for verifier commits. **Direct CAD evidence.** citeturn15view0turn15view1  
- **Fusion Help: Combine tool semantics and visibility rule** — *Official product documentation*; defines Join/Cut/Intersect and states that Cut participation depends on visibility, a critical pitfall for agent wrappers. **Direct CAD evidence.** citeturn18view0turn18view1  
- **Ekins AU handout: “Understanding Geometry and B-Rep in Inventor and Fusion 360”** — *Autodesk University technical handout*; explains B-rep representation, topology/geometry separation, evaluator usage, “tear-off” geometry snapshots, and temporary B-rep workflows. This directly supports inspection/recovery design and reference brittleness handling. **Direct CAD evidence.** citeturn28view0turn29view0turn29view2turn29view3  
- **Bidarra et al. (2005): persistent naming problem** — *Peer-reviewed CAD paper*; establishes persistent naming as a serious and inherent issue in parametric history-based modeling; directly motivates architecture that expects unstable references. **Direct CAD evidence.** citeturn23search5  
- **Fusion Custom Features documentation** — *Official developer documentation*; provides direct evidence about transaction boundaries, preview abort behavior, and timeline rollback issues—core to implementing safe checkpoints and replay. **Direct CAD evidence.** citeturn17search11  
- **Solar-Lezama (Sketch / CEGIS tech report)** — *Academic tech report (program synthesis)*; describes counterexample-guided inductive synthesis and the generator–validator loop; useful as an adjacent-domain pattern for structuring verifier-gated generation and returning counterexamples. **Adjacent-domain evidence (explicit inference for CAD mapping).** citeturn25view1  
- **Siemens white paper on CAD data integrity and kernel layers** — *Industry white paper*; concisely describes kernel vs proprietary feature-tree layers and notes Autodesk’s kernel lineage (ShapeManager derived from ACIS), relevant for what can/can’t be inferred from geometry alone. **Adjacent but strongly relevant engineering evidence.** citeturn27view0  
- **Machine Design article on ShapeManager/ACIS lineage** — *Industry trade publication*; corroborates Autodesk kernel lineage (ShapeManager based on ACIS 7 and Spatial/Dassault ties). **Adjacent evidence.** citeturn27view1  
- **Autodesk Fusion blog: singularities and non-manifold topology** — *Vendor technical blog/tutorial*; enumerates concrete non-manifold conditions (edge shared by >2 faces, pinch vertices) and practical mitigation (reorder timeline, multiple bodies, temporary supporting features). Useful for benchmark failure-mode design and verification heuristics. **Direct CAD evidence.** citeturn16view1  

## Structured Summary

```yaml
structured_summary:
  top_recommendations:
    - id: R1
      title: Add checkpointed rollback as a first-class primitive
      priority: Now
      impact: Very high reliability and recoverability; eliminates dead ends
      effort: Medium
      confidence: High
      evidence_type: direct
      short_rationale: Fusion’s transaction/timeline model supports safe rollback; recovery becomes deterministic instead of speculative.
    - id: R2
      title: Build a structured verification API that returns diffs and witnesses (counterexamples)
      priority: Now
      impact: High; faster convergence and fewer repeated failures
      effort: Medium
      confidence: Medium
      evidence_type: inference
      short_rationale: Mirrors CEGIS-style generator–checker loops; verification failures become actionable rather than vague.
    - id: R3
      title: Make geometry observables a versioned contract for Tier 0 commit gating and Tier 1 audit
      priority: Now
      impact: High; prevents compounding errors across steps
      effort: Low-Medium
      confidence: High
      evidence_type: direct
      short_rationale: Fusion APIs and Fusion 360 Gallery schemas show these observables are computable and useful at scale.
    - id: R4
      title: Represent references as token + semantic selector, with rebind logic
      priority: Now
      impact: High; reduces brittleness from persistent naming and topology changes
      effort: Medium-High
      confidence: High
      evidence_type: direct
      short_rationale: Entity tokens are not stable strings; topology edits can split entities; re-identification must be designed in.
    - id: R5
      title: Expand inspection and construction primitives (OBB, min distance, angled planes, evaluator normals)
      priority: Next
      impact: High; directly improves safe recovery and plane/normal discipline
      effort: Medium
      confidence: High
      evidence_type: direct
      short_rationale: These capabilities are explicit in Fusion APIs and map to common freeform failure modes.
  high_value_primitives:
    - primitive: rollback_checkpoint
      why: Enables safe recovery and prevents locked-state dead ends by making every mutation reversible
      priority: Now
    - primitive: structured_verification_diff
      why: Converts failures into precise feedback (what changed, what violated, where) enabling counterexample-driven retries
      priority: Now
    - primitive: token_plus_semantic_selector_rebind
      why: Mitigates persistent naming/reference brittleness across topology changes
      priority: Now
    - primitive: oriented_bounding_box_and_min_distance_inspection
      why: Supports robust dimensional/alignment/clearance checks and reduces wrong-plane/wrong-normal errors
      priority: Next
    - primitive: explicit_construction_plane_by_angle_tangent
      why: Makes angled-plane workflows controlled and verifiable instead of ad-hoc
      priority: Next
  benchmark_gaps:
    - gap: Reference-brittleness stress tests (topology splits/merges + rebind requirements)
      why_it_matters: Persistent naming issues are core CAD failure sources; benchmarks must force the system to prove robustness.
    - gap: Visibility-dependent boolean semantics cases
      why_it_matters: Combine Cut participation can change based on visibility; wrappers must either normalize or verify this explicitly.
    - gap: Non-manifold/singularity pathology suite
      why_it_matters: Kernel pathologies cause downstream feature failures; the agent must detect and recover or defer safely.
  promotion_criteria:
    - criterion: Stable, enumerated preconditions plus reproducible passes under live Fusion testing
      rationale: Prevents promoting brittle freeform traces into macros that fail under minor context variation.
    - criterion: Complete manifest with Tier 0 gating + Tier 1 audit checks
      rationale: Ensures structured workflows are verifiable and regressions are catchable.
    - criterion: Reference strategy is robust (token + semantic selector; rebind tested)
      rationale: Eliminates a major class of history-based CAD brittleness from promoted macros.
    - criterion: Demonstrated benchmark improvement (pass rate up, rollbacks down, variance down)
      rationale: Promotion should measurably improve reliability and engineering velocity.
  open_questions:
    must_answer_soon:
      - question: What is the exact, versioned set of geometry observables (and tolerances) that defines “verification contract”?
      - question: What semantic selectors will be standardized for re-identifying faces/bodies when references break?
      - question: What minimal locked-state recovery tools (beyond inspection) are allowed without compromising safety?
    worth_exploring_later:
      - question: Can Manufacturing Extension feature recognition be selectively used for semantic verification of holes/pockets?
      - question: Should internal benchmark schemas align with public Fusion 360 Gallery metadata for reuse and comparability?
      - question: How should kernel pathology (non-manifold, singularities) be incorporated into regression scoring?
```