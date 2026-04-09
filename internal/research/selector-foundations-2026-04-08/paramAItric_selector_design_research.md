# ParamAItric: First-Generation Semantic Selector System
## Design Research Report

**Date:** 2026-04-08  
**Scope:** First-pass implementation design for a semantic selector layer targeting faces, edges, bodies, and vertices inside ParamAItric's existing Fusion 360 / MCP architecture.  
**Primary sources:** ParamAItric Verification Trust Model (Google Doc), Fusion 360 B-Rep and Geometry API reference (official Autodesk), ParamAItric README and repository structure, Python CAD landscape review (prior session).  
**Source limitations:** `ARCHITECTURE.md`, `BEST_PRACTICES.md`, `live_ops.py`, `tool_specs.py`, `workflow_registry.py`, and `docs/` files were inaccessible via web fetch due to GitHub permissions. Claims about these files are inferred from README evidence and the Verification Trust Model. All inferences are labeled.

---

## 1. Executive Summary

- **The Verification Trust Model is the governing constraint for any selector design.** It defines hard gate, soft warning, and audit levels of geometric validation. Any selector that cannot guarantee that its resolution is auditable by the existing verification signals is not safe for first-generation production use.

- **ParamAItric's current geometry targeting is coordinate- and index-implicit.** Based on the live workflow catalog (`spacer`, `bracket`, `filleted_bracket`, `counterbored_plate`, etc.), geometry is targeted by construction-time knowledge: the feature that created a face is used immediately, in the same workflow step, without any persistent reference to the face across future steps. This is safe but brittle at scale — it does not generalize to multi-step cross-feature targeting.

- **The Topological Naming Problem is not yet a live crisis for ParamAItric — but it will be.** The current workflow family is shallow: each workflow creates a body and applies one to two features in sequence. When workflows become multi-step or chain-dependent, index-based face targeting will break silently. The selector system should be designed now to prevent that failure mode before it appears in production.

- **Three selector categories matter for first implementation:** positional (axis-aligned extrema), geometric-type (plane/cylinder/circle classification), and feature-association (faces returned directly by Fusion feature objects). These three cover ~90% of the operations needed by the validated workflow family.

- **Selectors must resolve inside the Fusion add-in, not in the MCP server.** The MCP server cannot hold live B-Rep object references. All selector evaluation — geometry queries, normal comparisons, area ranking — must execute in the add-in's Python process where Fusion API objects are live. The MCP layer should emit selector descriptors; the add-in resolves them.

- **The AI should never emit raw face/edge indices.** Indices (`faces[3]`, `edges[0]`) are the exact failure mode the selector system is designed to eliminate. Every AI-facing selector must be expressed as a semantic intent that the add-in can evaluate independently.

- **Fusion's `BRepFace.geometry.objectType` is the ground truth for surface type classification.** The geometry property returns `Plane`, `Cylinder`, `Cone`, `Sphere`, `Torus`, or `NurbsSurface`. This is the native Fusion equivalent of build123d's `filter_by(GeomType.PLANE)`. It should be the backbone of all type-based selectors.

- **Fusion's `BRepFace.area`, `BRepFace.centroid`, and `SurfaceEvaluator.getNormalAtPoint` are the ground truth for positional and size selectors.** These are stable, documented, officially supported API properties that do not depend on topology index stability.

- **Feature-association selectors are the safest and should be built first.** Fusion's `ExtrudeFeature.startFaces`, `ExtrudeFeature.endFaces`, `ExtrudeFeature.sideFaces`, and the generic `Feature.faces` collection return faces by feature provenance, not by index. These are operation-aware references equivalent to build123d's `Select.LAST` — they are immune to topology renumbering.

- **Selector results must be pinned immediately with Fusion API Attributes.** Every selected entity that will be referenced by a subsequent operation must receive a custom attribute (`paramAItric`, `selectorTarget`, `<semanticName>`) before the next feature executes. This converts a transient query result into a persistent name that survives recomputation.

- **ParamAItric should ship a selector vocabulary of exactly 12 named selectors in v1.** Anything beyond this risks combinatorial ambiguity, harder verification, and an AI that overfits on selector variety instead of generating correct geometry.

- **The most dangerous selectors are relational and cardinality-sensitive.** Selectors like "all vertical edges" or "all circular faces" return variable-length sets whose cardinality depends on model state. These are high-value but require explicit cardinality guards before any downstream operation can proceed.

---

## 2. Selector Taxonomy

### 2.1 The Five Category Framework

Based on analysis of the current ParamAItric workflow family, the Fusion B-Rep API surface, and the build123d/CadQuery landscape review, five selector categories are defined. Each is assessed for safety, Fusion API grounding, and fit with the current verification model.

```
CATEGORY A: Positional Selectors
  Resolve by axis-aligned geometry: highest, lowest, leftmost, rightmost, frontmost, rearmost
  Ground truth: face.centroid (Point3D), face normal vector from SurfaceEvaluator
  Risk level: LOW — single-result when geometry is well-formed; deterministic for typical prismatic solids

CATEGORY B: Geometric-Type Selectors
  Resolve by surface or edge geometry classification
  Ground truth: face.geometry.objectType (Plane / Cylinder / Cone / NurbsSurface)
              edge.geometry.objectType (Line3D / Circle3D / Arc3D / NurbsCurve3D)
  Risk level: LOW-MEDIUM — type is stable; cardinality is variable

CATEGORY C: Feature-Association Selectors
  Resolve by feature provenance: which feature created this face/edge
  Ground truth: ExtrudeFeature.endFaces, Feature.faces, HoleFeature.sideFaces
  Risk level: VERY LOW — immune to topology renumbering; must be used at feature creation time

CATEGORY D: Size/Rank Selectors
  Resolve by measured property (area, length, radius) with rank ordering
  Ground truth: face.area, edge.length, (circle geometry).radius
  Risk level: MEDIUM — requires stable geometry; breaks on near-equal sizes

CATEGORY E: Relational Selectors
  Resolve by topological or geometric relationship between entities
  Examples: edges adjacent to face, faces sharing an edge, coplanar faces
  Ground truth: BRepFace.edges, BRepEdge.faces, normal dot-product comparison
  Risk level: HIGH — graph traversal + relationship math; many failure modes
```

### 2.2 Sub-Categories by Topology Target

```
Selector Target    Available API Surface             Safety
─────────────────────────────────────────────────────────────
BRepFace           geometry.objectType               Low risk
                   area                              Low risk  
                   centroid                          Low risk
                   SurfaceEvaluator.getNormalAtPoint Low risk
                   loops (inner/outer boundary)      Medium risk
                   body.faces (full enumeration)     Low risk
                   Feature.endFaces / startFaces     Very low risk

BRepEdge           geometry.objectType               Low risk
                   length                            Low risk
                   isDegenerate                      Low risk
                   face.edges (adjacency)            Medium risk
                   edge.faces (2 adjacent faces)     Medium risk

BRepVertex         geometry (Point3D)                Low risk
                   edges (connected edges)           Medium risk

BRepBody           faces / edges / vertices          Low risk (as containers)
                   isSolid                           Very low risk (verification use)
```

### 2.3 The Selector Resolution Pipeline

Every selector in ParamAItric must follow this pipeline. Deviation is not permitted.

```
1. DESCRIPTOR IN   → AI emits a named selector descriptor (JSON in MCP payload)
2. DISPATCH        → MCP server routes descriptor to Fusion add-in via HTTP bridge
3. RESOLVE         → Add-in evaluates selector against live BRep topology
4. GUARD           → Add-in checks result cardinality and geometry validity
5. PIN             → Add-in stamps Fusion Attribute on each selected entity
6. ACK             → Add-in returns entity count + attribute keys to MCP server
7. VERIFY          → Verification signals run (isSolid, face count delta, etc.)
8. CONSUME         → Next operation references pinned attribute keys, not live objects
```

---

## 3. Ranked First-Version Selector Vocabulary

The following 12 selectors constitute the recommended v1 vocabulary. They are ranked by value/safety ratio — highest value, lowest risk first.

### Tier 1: Implement Now (Safe, High-Value, Directly Needed)

**S-01: `face_by_normal_axis`**
```
Intent:    Select the single planar face whose outward normal is closest to a given axis direction
Syntax:    { "selector": "face_by_normal_axis", "axis": "+Z", "rank": "extreme" }
           rank options: "extreme" (most extreme), "second" (second most extreme)
Fusion:    face.geometry.objectType == Plane → SurfaceEvaluator.getNormalAtPoint(face.pointOnFace)
           Sort by normal.dot(axis_vector), take max
Guard:     Exactly one face must be planar with normal within 5° of axis; abort if tie
Use case:  "top face" (axis=+Z, rank=extreme), "bottom face" (axis=-Z), "front face" (axis=+Y)
Failure:   Tied normals on exactly parallel faces (e.g. symmetric channel) → cardinality error
Stability: HIGH — works for all prismatic parts in current workflow family
```

**S-02: `face_by_feature_role`**
```
Intent:    Select faces by their role in the feature that created them
Syntax:    { "selector": "face_by_feature_role", "feature_name": "Extrude1", "role": "end" }
           role options: "end", "start", "side", "all"
Fusion:    ExtrudeFeature.endFaces / startFaces / sideFaces / faces
           HoleFeature.sideFaces / startFaces
           Generic: Feature.faces
Guard:     Feature must exist by name; feature must have resolved at creation time
Use case:  "the top cap of the extrusion", "all hole walls", "the base face of the boss"
Failure:   Feature renamed or rolled back in timeline → name resolution fails
Stability: VERY HIGH — feature object reference is stable within a single workflow step
```

**S-03: `edge_by_loop_type`**
```
Intent:    Select all edges in a specific loop of a face (outer boundary or inner holes)
Syntax:    { "selector": "edge_by_loop_type", "face_selector": {...}, "loop": "outer" }
           loop options: "outer", "inner_all", "inner[0]"
Fusion:    face.loops → loop.isOuter → loop.edges
Guard:     Face selector must resolve first; inner loop index must exist
Use case:  "all edges on the outer perimeter of the top face", "the edges of the first hole loop"
Failure:   Face has multiple inner loops → inner[0] ambiguity; must use inner_all or explicit index
Stability: HIGH — loop structure is topologically stable for prismatic bodies
```

**S-04: `edge_by_geometry_type`**
```
Intent:    Select all edges on a face (or body) whose geometry matches a type
Syntax:    { "selector": "edge_by_geometry_type", "scope": "face_ref", "type": "circle" }
           type options: "line", "circle", "arc"
Fusion:    edge.geometry.objectType: Line3D / Circle3D / Arc3D
Guard:     Scope must resolve; result set may be empty (explicit empty guard)
Use case:  "all circular edges on the top face" (hole perimeters for fillet selection)
Failure:   Arcs and circles share objectType confusion (Arc3D vs Circle3D) — must test explicitly
Stability: MEDIUM-HIGH — geometry type is stable; count depends on model complexity
```

**S-05: `face_by_area_rank`**
```
Intent:    Select the Nth largest (or smallest) face of a specified geometry type
Syntax:    { "selector": "face_by_area_rank", "type": "plane", "rank": 1, "order": "desc" }
           rank: 1 = largest, 2 = second largest; order: "desc"=largest first, "asc"=smallest first
Fusion:    filter faces by geometry.objectType == Plane → sort by face.area → take rank N
Guard:     Must have at least N faces of the type; warn if top-2 areas are within 5% (ambiguity)
Use case:  "the largest flat face" (for sketch placement), "the smallest face" (pilot feature)
Failure:   Near-equal areas on symmetric parts → rank flip under numerical precision
Stability: MEDIUM — safe for asymmetric parts; risky for symmetric parts with equal-area faces
```

**S-06: `body_by_name`**
```
Intent:    Select a body by its Fusion name or by a ParamAItric-assigned attribute
Syntax:    { "selector": "body_by_name", "name": "Body1" }
           OR { "selector": "body_by_attribute", "key": "paramAItric.role", "value": "enclosure" }
Fusion:    component.bRepBodies.itemByName(name) OR iterate bodies checking attributes
Guard:     Name must exist; attribute match must be unique (abort if multiple match)
Use case:  Every multi-body workflow; body targeting before shell, combine, or section features
Failure:   Fusion auto-renames bodies on copy/paste; attribute key collision
Stability: HIGH for attribute-based; MEDIUM for name-based
```

### Tier 2: Implement Next (Valuable, Slightly More Complex)

**S-07: `face_by_normal_parallel`**
```
Intent:    Select all faces whose normal is parallel (or anti-parallel) to a given axis
Syntax:    { "selector": "face_by_normal_parallel", "axis": "Z", "include_antiparallel": true }
Fusion:    For each planar face: abs(normal.dot(axis_vector)) > cos(5°) threshold
Guard:     Result may be multi-face; must declare expected cardinality or use as set
Use case:  "all horizontal faces" (floor + ceiling of box), "all Z-normal faces for sketch ops"
Failure:   Returns both top and bottom on symmetric parts — must handle as a set, not singleton
Stability: MEDIUM — multi-result; consumer must handle set
```

**S-08: `edge_by_length_rank`**
```
Intent:    Select the Nth longest (or shortest) edge in a scope
Syntax:    { "selector": "edge_by_length_rank", "scope": "face_ref", "rank": 1, "order": "desc" }
Fusion:    edge.length property → sort → take rank N
Guard:     Warn if top-2 lengths are within 1% (ambiguity threshold)
Use case:  "the longest edge of the top face" (for shell thickness direction), "shortest edge" (fillet preview)
Failure:   Symmetric parts with equal-length edges → rank instability
Stability: MEDIUM
```

**S-09: `face_by_cylinder_axis`**
```
Intent:    Select cylindrical faces whose axis is parallel to a given direction
Syntax:    { "selector": "face_by_cylinder_axis", "axis": "Z" }
Fusion:    face.geometry.objectType == Cylinder → Cylinder.axisVector.dot(axis) > threshold
Guard:     Result may be multi-face (multiple holes); must declare whether singleton or set expected
Use case:  "all hole walls" (for thread or counterbore operations), "the boss cylinder"
Failure:   Angled cylinders (drafted holes) — axis direction check fails; must use tolerance band
Stability: MEDIUM — type check stable; count depends on model
```

**S-10: `vertex_by_position_rank`**
```
Intent:    Select the vertex with the extreme position along an axis
Syntax:    { "selector": "vertex_by_position_rank", "axis": "+Z", "rank": "max" }
Fusion:    vertex.geometry (Point3D) → sort by .z / .x / .y → take max or min
Guard:     Multiple vertices at same coordinate → cardinality error
Use case:  "top corner" for sketch point anchoring; "lowest point" for ground reference
Failure:   Flat surfaces have multiple co-planar vertices at same Z — multi-result
Stability: MEDIUM — useful for sharp-cornered solids; unreliable for symmetric parts
```

### Tier 3: Prototype Later (Complex or Context-Sensitive)

**S-11: `face_by_adjacency`**
```
Intent:    Select faces that share a specific edge with a reference face
Syntax:    { "selector": "face_by_adjacency", "reference_face": {...}, "shared_edge_type": "line" }
Fusion:    reference_face.edges → for each edge: edge.faces → filter out reference_face
Guard:     Result is a set; must guard on cardinality and edge type match
Use case:  "the four side walls adjacent to the top face" (for shell depth reference)
Failure:   Multi-body context; reference face not uniquely identified → wrong adjacency graph
Stability: LOW-MEDIUM — graph traversal is reliable but setup preconditions are fragile
```

**S-12: `edge_by_tangent_chain`**
```
Intent:    Select a chain of edges that are tangentially connected (G1 continuous)
Syntax:    { "selector": "edge_by_tangent_chain", "seed_edge": {...} }
Fusion:    edge.tangentEdges property (where available) OR manual G1 check via normal comparison
Guard:     Chain must terminate; cycles must be detected; max chain length guard
Use case:  "all edges of the fillet loop", "outer perimeter chain for sheet metal bend"
Failure:   Mixed tangent/non-tangent edges; Fusion's tangentEdges may not include all cases
Stability: LOW — complex traversal; Fusion API coverage of tangentEdges is incomplete
```

### Do Not Implement in v1

**Avoid: Spatial volume / bounding-box selectors**
```
These require computing the bounding box of topology subsets (not the full body), which Fusion
does not expose directly per-face. Approximating via centroid collection is imprecise and not
stable under model changes.
```

**Avoid: Text/name-based sketch or feature content selectors**
```
Selectors that find geometry by matching sketch point names, constraint names, or feature
parameter names are Fusion document model concerns, not B-Rep topology concerns. They belong
in a different layer (workflow registry) and should not be conflated with geometric selectors.
```

**Avoid: Nearest-to-point selectors**
```
Selecting "the face closest to point (x,y,z)" requires a spatial query (distance from point to
trimmed face, not just to the underlying infinite surface). Fusion's API does not provide this
directly. The approximation via centroid distance is unreliable for complex geometry.
```

**Avoid: Color / appearance selectors**
```
Fusion body/face appearances are user-visible metadata, not geometry. Using them as selection
criteria would make the selector system dependent on a fragile presentational layer.
```

---

## 4. Selector Composition Rules

### 4.1 The Two-Stage Composition Model

ParamAItric selectors compose in exactly two stages. More than two stages in a single operation should be flagged as a smell.

```
Stage 1: SCOPE REDUCTION
  Reduce from the full body topology to a candidate set
  Tools: body selector, feature-association selector, type selector
  Output: a BRepFaces collection, a BRepEdges collection, or a single body reference
  
Stage 2: REFINEMENT
  Further filter or rank the candidate set from Stage 1
  Tools: positional selector, size/rank selector, loop-type selector
  Output: a single entity OR a named set

Example (safe):
  Stage 1: face_by_feature_role(feature="Extrude1", role="end") → {top face, bottom face}
  Stage 2: face_by_normal_axis(from=stage1_result, axis="+Z", rank="extreme") → {top face}
  
Example (unsafe — too many stages):
  Stage 1: body_by_name("Body1")
  Stage 2: face_by_normal_parallel(axis="Z") → {all Z-faces}
  Stage 3: face_by_area_rank(from=stage2, rank=1) → largest Z-face
  Stage 4: edge_by_loop_type(from=stage3, loop="inner_all") → hole edges
  Stage 5: edge_by_length_rank(from=stage4, rank=1) → longest hole edge
  → Too deep; cardinality accumulates across 5 stages; failure mode is invisible
```

### 4.2 Composition Validity Rules

**Rule C-1: No implicit chaining across operations.** Each selector must be evaluated and pinned before the next operation begins. A selector chain that spans a feature creation boundary is forbidden — the intermediate topology state is undefined.

**Rule C-2: Stage 1 must always reduce body scope.** A selector chain that begins directly with a refinement selector (e.g., `face_by_area_rank` applied to the full body) is forbidden without an explicit body scope declaration. The full body is always the implicit scope if none is declared, but this must be made explicit in the descriptor.

**Rule C-3: Singleton vs. set must be declared.** Every selector invocation must declare `"expect": "one"` or `"expect": "many"`. If `"one"` is declared and the resolver returns multiple entities, the operation aborts. This is enforced by the add-in, not by the AI.

**Rule C-4: The AI must not compose selectors that depend on each other's count.** The AI cannot know how many faces a `face_by_normal_parallel` call will return for an arbitrary body. If the next operation's selector depends on a specific count from the previous selector, the AI is making an assumption about model state that it cannot verify.

**Rule C-5: Maximum composition depth is 2 stages.** The first stage returns a candidate collection. The second stage refines it. If a use case requires more than two stages, it is a signal that a named workflow step is needed, not a deeper selector chain.

**Rule C-6: Selectors may not reference each other's output during the same MCP tool call.** A tool call may contain one selector descriptor. The output of that selector call is pinned via attribute. The next tool call references the attribute key. This enforces synchronization and enables the verification layer to check each step.

### 4.3 Safe Composition Patterns

```
Pattern 1: Feature-then-refine (SAFEST)
  S-02 (feature_role) → S-03 (edge_by_loop_type)
  S-02 (feature_role) → S-01 (face_by_normal_axis) for disambiguation

Pattern 2: Type-then-rank (SAFE)
  S-04 (edge_by_geometry_type, type="circle") on a known face → filter by radius

Pattern 3: Body-then-type (SAFE for multi-body designs)
  S-06 (body_by_name) → S-07 (face_by_normal_parallel)
  S-06 (body_by_name) → S-05 (face_by_area_rank)

Pattern 4: Feature-then-type (SAFE)
  S-02 (feature_role, role="side") → S-04 (edge_by_geometry_type) to find fillet candidates
```

### 4.4 Dangerous Composition Patterns to Prohibit

```
Anti-Pattern 1: Rank-then-rank without type guard
  face_by_area_rank → edge_by_length_rank  (no type filter on either → operates on all geometry)
  Risk: Area rank picks a curved face; length rank operates on arc edges → wrong semantics

Anti-Pattern 2: Type selector with no scope
  edge_by_geometry_type(body-scope, type="circle")  (no feature or face scope)
  Risk: Returns all circular edges in the body; count is model-dependent; AI has no way to predict

Anti-Pattern 3: Positional selector on a curved body
  face_by_normal_axis(axis="+Z") on a body with rounded top
  Risk: Cylindrical/spherical faces have no single planar normal → no match OR wrong match

Anti-Pattern 4: Chained adjacency
  face_by_adjacency → face_by_adjacency  (neighbor of neighbor)
  Risk: O(N²) traversal; highly model-dependent; breaks on bodies with non-manifold patches
```

---

## 5. Failure Modes and Guardrails

This section maps selector failure modes to the Verification Trust Model's signal taxonomy. Each failure mode is assigned a detection tier.

### 5.1 Classification of Failure Modes

**Failure Mode F-01: Empty result (selector resolves to nothing)**
```
Trigger:   face_by_normal_axis(axis="+Z") on a body with no planar faces (e.g., sphere, fully rounded body)
Detection: Add-in returns empty collection; explicit guard raises OperatorError before any feature attempt
VTM tier:  Hard gate — operation is blocked; never reaches Fusion geometry execution
Mitigation: Pre-check geometry type before invoking positional selectors;
            add "requires_planar_faces" precondition annotation to S-01
```

**Failure Mode F-02: Ambiguous singleton (selector returns multiple when one expected)**
```
Trigger:   face_by_normal_axis on symmetric body with two equal-area top faces;
           face_by_area_rank on body where largest and second-largest are within 2%
Detection: Cardinality guard in add-in: if len(result) != 1 and expect=="one" → abort + log
VTM tier:  Hard gate — aborts before any mutation; returns specific disambiguation error
Mitigation: Require AI to specify a tiebreak selector; or require feature-association scoping first
```

**Failure Mode F-03: Wrong entity type selected (type confusion)**
```
Trigger:   edge_by_geometry_type(type="circle") returns Arc3D edges (partial circles) instead of full circles
           NurbsSurface face selected when Plane was expected (e.g., on a lofted body)
Detection: Add-in validates geometry.objectType of each result against declared expectation
VTM tier:  Hard gate — type mismatch is rejected before operation
Mitigation: S-04 must explicitly distinguish Circle3D vs Arc3D; expose both as selectable types
```

**Failure Mode F-04: Stale attribute reference (attribute key present but entity no longer matches)**
```
Trigger:   Feature rollback → timeline rebuild → face referenced by attribute no longer exists
           Body renaming → attribute search by name fails silently
Detection: Attribute lookup returns None; add-in must detect null reference and raise
VTM tier:  Hard gate — null reference caught before next operation; triggers recovery protocol
Mitigation: After every feature execution, run attribute validity check:
            for each pinned attribute, confirm entity.isValid and entity.body.isSolid
```

**Failure Mode F-05: Geometric precision near-miss (normal not quite matching)**
```
Trigger:   face_by_normal_axis on a face that is 4.9° off-axis (just inside the 5° tolerance)
           face_by_normal_parallel matches a near-vertical face that should be excluded
Detection: Not directly detected — wrong entity is selected but appears valid
VTM tier:  Soft warning — geometry passes isSolid but subsequent feature result is anomalous
Mitigation: Log selected face normal deviation in the audit trail;
            tighten tolerance to 3° for first-gen; make tolerance a configurable constant
```

**Failure Mode F-06: Area ranking flip under parameter change**
```
Trigger:   User changes width parameter in Fusion; second-largest face becomes largest;
           face_by_area_rank(rank=1) now selects the wrong face; next sketch goes on wrong face
Detection: Not detected at selection time; detected at downstream feature failure or visual review
VTM tier:  Audit level — requires explicit re-validation when user changes a Fusion parameter
Mitigation: Log area value at selection time alongside entity attribute;
            add area-drift check to the audit log: if area differs by >10% from pinned value → warn
```

**Failure Mode F-07: Multi-body scope confusion**
```
Trigger:   face_by_normal_axis applied to component scope selects a face from the wrong body
Detection: Hard to detect; face is valid, isSolid passes, but operation targets wrong part
VTM tier:  Audit level — requires explicit body scope enforcement
Mitigation: All selectors MUST declare explicit body scope; implicit component-level scope is forbidden;
            body_by_name or body_by_attribute MUST precede any face or edge selector when multiple bodies exist
```

**Failure Mode F-08: Loop index out of bounds**
```
Trigger:   edge_by_loop_type(loop="inner[1]") on a face with only one inner loop
Detection: Index bounds check in add-in before traversal
VTM tier:  Hard gate — explicit bounds check raises before any access
Mitigation: Always query loop count before accessing by index; return loop count in selector response
```

**Failure Mode F-09: Tangent chain cycle or non-termination**
```
Trigger:   edge_by_tangent_chain on a body where tangent edges form a closed loop
Detection: Chain traversal exceeds max_edges constant (suggested: 64 edges) → abort
VTM tier:  Hard gate — max-depth guard prevents infinite loop
Mitigation: This is why S-12 is Tier 3; implement only after chain traversal is fully tested
```

### 5.2 Guardrails Summary Table

| Guardrail | Enforcement point | VTM tier |
|-----------|------------------|----------|
| Empty result check | Add-in, before any operation | Hard gate |
| Cardinality check (expect=one vs many) | Add-in, after resolution | Hard gate |
| Geometry type validation | Add-in, per entity in result | Hard gate |
| Body scope requirement | Add-in, before selector dispatch | Hard gate |
| Attribute validity after feature | Add-in, post-feature hook | Hard gate |
| Normal angle tolerance | Add-in, configurable constant | Hard gate |
| Area near-equal warning (5% band) | Add-in, logged | Soft warning |
| Area drift check (pinned vs current) | Add-in, audit pass | Audit |
| Normal deviation logging | Add-in, audit pass | Audit |
| Multi-body implicit scope | Add-in, policy enforcement | Hard gate |
| Loop index bounds | Add-in, before traversal | Hard gate |
| Chain max depth | Add-in, traversal guard | Hard gate |

---

## 6. Recommended Internal Representation

### 6.1 The Selector Descriptor (MCP → Add-in)

All selectors are expressed as JSON descriptors emitted by the MCP layer and consumed by the add-in resolver. The descriptor is not a Python object at the MCP layer — it is a declarative structure.

```json
{
  "selector": "face_by_normal_axis",
  "scope": {
    "body": { "selector": "body_by_name", "name": "Body1" }
  },
  "params": {
    "axis": "+Z",
    "rank": "extreme",
    "type_guard": "plane"
  },
  "expect": "one",
  "pin_as": "top_face"
}
```

**Fields:**
- `selector`: Named selector from the v1 vocabulary (string enum, validated before dispatch)
- `scope`: Optional nested selector establishing context (body, face, or feature); may be omitted when context is unambiguous (single-body design)
- `params`: Selector-specific parameters (axis, rank, type, etc.)
- `expect`: `"one"` | `"many"` — cardinality contract; enforced by add-in
- `pin_as`: The attribute key under which the resolved entity will be stored in Fusion Attributes; used by subsequent operations

### 6.2 The Selector Result (Add-in → MCP)

The add-in returns a structured result for every selector invocation. The result never contains live B-Rep object references — only metadata.

```json
{
  "selector": "face_by_normal_axis",
  "pin_as": "top_face",
  "status": "ok",
  "count": 1,
  "entities": [
    {
      "entity_type": "BRepFace",
      "attribute_key": "paramAItric.selectorTarget.top_face",
      "centroid": [2.0, 1.25, 0.5],
      "area": 10.0,
      "normal": [0.0, 0.0, 1.0],
      "geometry_type": "Plane",
      "body_name": "Body1"
    }
  ],
  "warnings": [],
  "guard_metadata": {
    "normal_deviation_deg": 0.0,
    "area_near_equal_warning": false,
    "candidate_count_before_refinement": 2
  }
}
```

**Design notes:**
- `centroid`, `normal`, `area`, `geometry_type` are logged at resolution time for the audit trail
- `attribute_key` is the stable handle used by subsequent operations — not a tempId, not an index
- `guard_metadata` feeds directly into the verification audit tier
- `status` can be `"ok"` | `"empty"` | `"ambiguous"` | `"type_mismatch"` | `"scope_error"`

### 6.3 The Internal `SelectorNode` Class (Add-in Python)

Inside the Fusion add-in, the selector system should be implemented as a resolver registry. This is an inferred recommendation based on the add-in's observed structure.

```python
# fusion_addin/selectors/resolver.py  (proposed new module)

class SelectorResult:
    """Returned by every resolver. Never holds live BRep references."""
    def __init__(self, entities, metadata, warnings):
        self.entities = entities          # list of SelectorEntity (frozen snapshot)
        self.metadata = metadata          # guard_metadata dict
        self.warnings = warnings          # list of warning strings
        self.status = "ok"

class SelectorEntity:
    """Frozen snapshot of a selected entity. All live references gone after __init__."""
    def __init__(self, brep_entity, pin_as):
        # Capture all needed metadata immediately
        self.entity_type = type(brep_entity).__name__
        self.attribute_key = f"paramAItric.selectorTarget.{pin_as}"
        self.centroid = _extract_centroid(brep_entity)
        self.area = getattr(brep_entity, 'area', None)
        self.normal = _extract_normal(brep_entity)
        self.geometry_type = brep_entity.geometry.objectType if hasattr(brep_entity, 'geometry') else None
        self.body_name = brep_entity.body.name if hasattr(brep_entity, 'body') else None
        # Pin immediately — attribute survives recomputation
        brep_entity.attributes.add("paramAItric", f"selectorTarget.{pin_as}", "1")

RESOLVER_REGISTRY = {
    "face_by_normal_axis":     _resolve_face_by_normal_axis,
    "face_by_feature_role":    _resolve_face_by_feature_role,
    "edge_by_loop_type":       _resolve_edge_by_loop_type,
    "edge_by_geometry_type":   _resolve_edge_by_geometry_type,
    "face_by_area_rank":       _resolve_face_by_area_rank,
    "body_by_name":            _resolve_body_by_name,
    "face_by_normal_parallel": _resolve_face_by_normal_parallel,
    "edge_by_length_rank":     _resolve_edge_by_length_rank,
    "face_by_cylinder_axis":   _resolve_face_by_cylinder_axis,
    "vertex_by_position_rank": _resolve_vertex_by_position_rank,
    "face_by_adjacency":       _resolve_face_by_adjacency,
    "edge_by_tangent_chain":   _resolve_edge_by_tangent_chain,
}

def resolve(descriptor: dict, component) -> SelectorResult:
    name = descriptor["selector"]
    resolver = RESOLVER_REGISTRY.get(name)
    if not resolver:
        raise ValueError(f"Unknown selector: {name}")
    scope = _resolve_scope(descriptor.get("scope"), component)
    result = resolver(descriptor["params"], scope, component)
    _enforce_cardinality(result, descriptor["expect"])
    return result
```

### 6.4 Attribute Key Convention

All ParamAItric selector attributes must follow this exact convention to avoid collision with Fusion built-in attributes and other add-ins:

```
Group:  "paramAItric"
Name:   "selectorTarget.<pin_as>"
Value:  "1"   (presence is the signal; value is a placeholder for future versioning)

Examples:
  paramAItric / selectorTarget.top_face        → pinned BRepFace
  paramAItric / selectorTarget.hole_edge_0     → first hole's circular edge
  paramAItric / selectorTarget.outer_body      → main enclosure body
  paramAItric / selectorTarget.extrude1_end    → end face of Extrude1
```

**Retrieval pattern in subsequent operations:**
```python
def find_by_pin(component, pin_as):
    attr_key = f"selectorTarget.{pin_as}"
    for body in component.bRepBodies:
        for face in body.faces:
            if face.attributes.itemByName("paramAItric", attr_key):
                return face
        for edge in body.edges:
            if edge.attributes.itemByName("paramAItric", attr_key):
                return edge
    return None  # triggers recovery protocol
```

---

## 7. Recommended AI-Facing vs Internal-Only Split

This split is the most important architectural decision in the selector system. It determines what vocabulary the AI must learn, what it can be tested against, and what can evolve without breaking the AI contract.

### 7.1 AI-Facing Surface (The "Public API")

These are the only selector constructs the AI should ever emit. They are simple, named, unambiguous, and directly mappable to the RESOLVER_REGISTRY.

```
AI-FACING SELECTORS (v1 vocabulary — 12 total)

S-01  face_by_normal_axis         axis: "+X"/"+Y"/"+Z"/"-X"/"-Y"/"-Z", rank: "extreme"/"second"
S-02  face_by_feature_role        feature_name: str, role: "end"/"start"/"side"/"all"
S-03  edge_by_loop_type           loop: "outer"/"inner_all"/"inner[N]"
S-04  edge_by_geometry_type       type: "line"/"circle"/"arc"
S-05  face_by_area_rank           type: "plane"/"any", rank: int, order: "desc"/"asc"
S-06  body_by_name                name: str
      body_by_attribute           key: str, value: str
S-07  face_by_normal_parallel     axis: "X"/"Y"/"Z", include_antiparallel: bool
S-08  edge_by_length_rank         rank: int, order: "desc"/"asc"
S-09  face_by_cylinder_axis       axis: "X"/"Y"/"Z"
S-10  vertex_by_position_rank     axis: "+X"/"+Y"/"+Z"/"-X"/"-Y"/"-Z", rank: "max"/"min"
S-11  face_by_adjacency           [Tier 3 — prototype; not in initial AI prompt]
S-12  edge_by_tangent_chain       [Tier 3 — prototype; not in initial AI prompt]
```

**What the AI is taught:**
- Selector names (enum vocabulary, no freeform strings)
- Required parameters for each (typed schema)
- `expect` field semantics (always declare cardinality)
- `pin_as` convention (snake_case semantic name: `top_face`, `hole_edge`, `side_wall`)
- That selectors are inputs to operations, not operations themselves
- That selectors cannot be chained within a single tool call

**What the AI is NOT taught:**
- Fusion API internals (`BRepFace`, `geometry.objectType`, `SurfaceEvaluator`)
- Attribute key format (the add-in manages this)
- Tolerance thresholds (these are policy, not AI concern)
- Internal result format (the AI receives only the `count` and `status` in the ack)

### 7.2 Internal-Only Implementation Details

These are implementation concerns that must never appear in the AI-facing interface or in the MCP tool specifications.

```
INTERNAL ONLY

- objectType comparison logic (geometry.objectType == adsk.core.Plane.classType())
- SurfaceEvaluator instantiation and normal vector computation
- Tolerance constants (NORMAL_ANGLE_TOLERANCE_DEG = 3.0, AREA_NEAR_EQUAL_PCT = 5.0)
- Attribute group name ("paramAItric") and key format
- BRepLoop traversal order and isOuter property
- Face area computation (face.area — internal to add-in)
- Centroid extraction (face.centroid — internal to add-in)
- Cardinality enforcement logic
- Recovery protocol when attribute lookup returns None
- Guard metadata structure (only a summary passes back to MCP)
- Scope resolution order (body → shell → faces/edges)
- TempId usage (prohibited for persistence; internal use only during a single transaction)
```

### 7.3 The AI Prompt Contract

The AI prompt (in `docs/AI_CAD_PLAYBOOK.md`, inferred) should state the following constraints for selector use:

```
1. You must always use a named selector from the vocabulary list.
2. You must never reference face indices, edge indices, or tempIds.
3. You must always declare "expect": "one" or "expect": "many".
4. You must always declare "pin_as" with a meaningful semantic name.
5. When multiple bodies exist, you must always scope with body_by_name or body_by_attribute first.
6. You must never chain selectors within a single tool call.
7. When you need to reference a previously selected entity, use its pin_as name, not a selector.
8. If a selector returns "ambiguous" or "empty" status, you must stop and request clarification.
```

---

## 8. Immediate Implementation Guidance

### 8.1 Build Order

The selector system should be built in this exact sequence. Each phase is independently testable.

**Phase 0: Infrastructure (prerequisite — 1 to 2 days)**
```
- Create fusion_addin/selectors/__init__.py
- Create fusion_addin/selectors/resolver.py with:
  - SelectorResult and SelectorEntity dataclasses
  - resolve() dispatcher
  - RESOLVER_REGISTRY (stubs only)
  - _resolve_scope() function
  - _enforce_cardinality() function
  - find_by_pin() utility (attribute lookup)
- Add selector invocation endpoint to the HTTP bridge (live_ops.py)
  - New endpoint: POST /select → dispatch to resolver.resolve()
  - Returns SelectorResult as JSON
- Add selector tests to tests/ (mock-mode resolver returning synthetic results)
```

**Phase 1: Tier 1 Selectors (highest value — 3 to 5 days)**
```
Implement in this order:
1. body_by_name (S-06) — foundation; needed by all others in multi-body context
2. face_by_feature_role (S-02) — safest; uses Fusion's own feature face properties
3. face_by_normal_axis (S-01) — highest AI usage; covers "top face" use case
4. edge_by_geometry_type (S-04) — covers hole edge selection; needed for fillets
5. face_by_area_rank (S-05) — covers "largest flat face" use case

Test each with the existing filleted_bracket and counterbored_plate workflows.
Add smoke test variants that exercise each selector.
```

**Phase 2: Tier 2 Selectors and Composition (3 to 4 days)**
```
Implement:
6. edge_by_loop_type (S-03) — needed for perimeter fillet chains
7. face_by_normal_parallel (S-07) — needed for multi-face sketch targeting
8. face_by_cylinder_axis (S-09) — needed for counterbore and threading ops
9. edge_by_length_rank (S-08) — needed for asymmetric part edge selection

Add composition integration test:
  - S-06 (body_by_name) → S-01 (face_by_normal_axis) → S-03 (edge_by_loop_type)
  - Verify attribute chain: body attribute → face attribute → edge attributes
  - Verify that attribute lookup succeeds after a subsequent feature is added to the timeline
```

**Phase 3: Verification Integration (2 to 3 days)**
```
- Add guard_metadata to the verification audit log
- Add attribute validity check to the post-feature verification hook:
    for each attribute in the selector_audit_log:
        entity = find_by_pin(component, pin_as)
        if entity is None: raise VerificationError("Selector pin lost after feature")
- Add area drift check to audit pass
- Add normal deviation to audit log
- Update smoke runner to include selector validation step
```

**Phase 4: Tier 3 Selectors and AI prompt update (prototype — deferred)**
```
- Implement edge_by_loop_type inner loop handling (inner[N])
- Prototype face_by_adjacency with explicit adjacency tests
- Prototype edge_by_tangent_chain with max_depth guard
- Update AI_CAD_PLAYBOOK.md with full v1 vocabulary and examples
- Add few-shot selector examples to the AI system prompt
```

### 8.2 The Three Fusion API Facts Every Resolver Must Know

**Fact 1: Always use `face.geometry.objectType` with `classType()` comparison, never string comparison.**
```python
# Correct — Fusion API design pattern
import adsk.core
is_plane = face.geometry.objectType == adsk.core.Plane.classType()
is_cylinder = face.geometry.objectType == adsk.core.Cylinder.classType()

# Wrong — fragile string comparison
is_plane = "Plane" in face.geometry.objectType  # breaks across API versions
```

**Fact 2: Use `SurfaceEvaluator` from the face, not from the geometry object.**
```python
# Correct — evaluator from face accounts for B-Rep context (solid normal direction)
evaluator = face.evaluator  # adsk.core.SurfaceEvaluator
result, normal = evaluator.getNormalAtPoint(face.pointOnFace)

# Wrong — geometry object evaluator doesn't know it's part of a solid
normal = face.geometry.evaluator.getNormal(...)  # normal direction not guaranteed outward
```

**Fact 3: `face.centroid` is stable and fast. Use it for positional sorting.**
```python
# For face_by_normal_axis:
planar_faces = [f for f in body.faces if f.geometry.objectType == adsk.core.Plane.classType()]
evaluator = face.evaluator
_, normal = evaluator.getNormalAtPoint(face.pointOnFace)
dot = normal.x * axis_vector.x + normal.y * axis_vector.y + normal.z * axis_vector.z
# Sort by dot product, take max → the face most aligned with axis
```

### 8.3 Annotated Example: Implementing `face_by_normal_axis`

```python
def _resolve_face_by_normal_axis(params: dict, scope_body, component) -> SelectorResult:
    axis_str = params["axis"]           # e.g. "+Z"
    rank_str = params.get("rank", "extreme")  # "extreme" or "second"
    
    # Parse axis into vector
    axis_map = {
        "+X": (1,0,0), "-X": (-1,0,0),
        "+Y": (0,1,0), "-Y": (0,-1,0),
        "+Z": (0,0,1), "-Z": (0,0,-1),
    }
    ax, ay, az = axis_map[axis_str]
    
    # Gather candidates: only planar faces
    candidates = []
    for face in scope_body.faces:
        if face.geometry.objectType != adsk.core.Plane.classType():
            continue
        evaluator = face.evaluator
        ok, normal = evaluator.getNormalAtPoint(face.pointOnFace)
        if not ok:
            continue
        dot = normal.x*ax + normal.y*ay + normal.z*az
        angle_deg = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
        if angle_deg < NORMAL_ANGLE_TOLERANCE_DEG:  # within tolerance of axis
            candidates.append((dot, face, angle_deg))
    
    if not candidates:
        return SelectorResult([], {"reason": "no_planar_faces_aligned_with_axis"}, [])
    
    # Sort by dot product descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    # Warn if top-2 are within ambiguity threshold
    warnings = []
    if len(candidates) >= 2:
        if abs(candidates[0][0] - candidates[1][0]) < 0.001:
            warnings.append("Top two candidates have near-equal alignment — result may be ambiguous")
    
    # Select by rank
    idx = 0 if rank_str == "extreme" else 1
    if idx >= len(candidates):
        return SelectorResult([], {"reason": f"rank={rank_str} exceeds candidate count"}, [])
    
    selected_face = candidates[idx][1]
    deviation_deg = candidates[idx][2]
    
    entity = SelectorEntity(selected_face, params["pin_as"])
    return SelectorResult(
        [entity],
        {"normal_deviation_deg": deviation_deg, "candidate_count_before_refinement": len(candidates)},
        warnings
    )
```

### 8.4 Integration with the Existing Verification Model

The selector system slots into the Verification Trust Model at three points:

```
BEFORE FEATURE EXECUTION
  → Selector resolution runs
  → Guard checks run (cardinality, type, scope)
  → Hard gate: any guard failure aborts operation, returns error to AI
  → Attributes pinned on valid results
  → Selector metadata logged to audit trail

AFTER FEATURE EXECUTION  
  → Existing verification signals run (isSolid, face count delta, volume delta)
  → ADDITIONAL: attribute validity check (all pinned selector entities still valid)
  → ADDITIONAL: area drift check (stored area vs current area within tolerance)
  → Soft warning if area drift detected
  → Hard gate if pinned attribute entity is gone (entity was consumed/modified by feature)

AUDIT PASS (existing pattern)
  → Selector metadata appended to audit log: normal_deviation_deg, area_near_equal_warning
  → Any soft warnings from selector resolution promoted to audit entries
  → Audit log available to human reviewer and to AI in recovery context
```

### 8.5 What Not to Build in Phase 1

- **Do not build a selector query language (DSL).** The 12-selector enum vocabulary is sufficient. A DSL adds parser complexity and creates ambiguity. Stick to named selectors with typed parameters.
- **Do not expose tempIds to the MCP layer.** TempIds are per-session and do not survive document save/reload. They are fine for single-transaction use inside the add-in but must never cross the HTTP bridge.
- **Do not build a visual selector debugger yet.** The audit log + attribute trail is sufficient for Phase 1 debugging. A visual layer (highlighting selected entities in the Fusion viewport) is a Phase 3 feature.
- **Do not try to make selectors persistent across Fusion sessions.** Attributes survive document save. The selector descriptors that generated them do not need to be re-runnable after session close. The attribute is the persistence primitive.
- **Do not build selector composition evaluation in the MCP server.** The MCP server is stateless with respect to Fusion topology. Scope resolution, cardinality checks, and attribute pinning all happen in the add-in where live B-Rep objects are accessible.

---

## Appendix A: Fusion B-Rep API Quick Reference for Selector Implementers

```
BRepFace properties used by selectors:
  face.geometry.objectType      → Plane / Cylinder / Cone / Sphere / Torus / NurbsSurface
  face.area                     → float (cm² in Fusion's internal units)
  face.centroid                 → Point3D (x, y, z in cm)
  face.pointOnFace              → Point3D (a guaranteed point on the face surface)
  face.evaluator                → SurfaceEvaluator (use for normals)
  face.loops                    → BRepLoops collection
  face.edges                    → BRepEdges collection
  face.body                     → parent BRepBody
  face.isParamReversed          → bool (face normal flipped from geometry default)
  face.attributes               → AttributeCollection (for pin storage)

BRepEdge properties used by selectors:
  edge.geometry.objectType      → Line3D / Circle3D / Arc3D / NurbsCurve3D / Ellipse3D
  edge.length                   → float (cm)
  edge.faces                    → BRepFaces (0, 1, or 2 adjacent faces)
  edge.isDegenerate             → bool (zero-length edges; filter these out)
  edge.startVertex / endVertex  → BRepVertex
  edge.attributes               → AttributeCollection

BRepVertex:
  vertex.geometry               → Point3D (x, y, z)
  vertex.edges                  → connected BRepEdges

SurfaceEvaluator (from face.evaluator):
  evaluator.getNormalAtPoint(point3D) → (bool, Vector3D)
  evaluator.getNormalAtParameter(point2D) → (bool, Vector3D)
  evaluator.parametricRange()   → BoundingBox2D

Feature face access (feature-association selectors):
  ExtrudeFeature.endFaces       → BRepFaces (cap face(s) at end of extrusion)
  ExtrudeFeature.startFaces     → BRepFaces (cap face(s) at start)
  ExtrudeFeature.sideFaces      → BRepFaces (wall faces around the extrusion perimeter)
  HoleFeature.sideFaces         → BRepFaces (cylindrical wall of the hole)
  Feature.faces                 → BRepFaces (all faces created or modified by the feature)

Attribute API:
  entity.attributes.add(group, name, value)   → creates/overwrites attribute
  entity.attributes.itemByName(group, name)    → returns Attribute or None
  app.findAttributes(group, name)              → searches entire document
```

---

## Appendix B: v1 Selector Vocabulary — Quick Reference Card

| ID | Name | Scope | Returns | Tier | Safe for production? |
|----|------|-------|---------|------|---------------------|
| S-01 | `face_by_normal_axis` | body | 1 face | 1 | Yes, with type guard |
| S-02 | `face_by_feature_role` | feature | 1-N faces | 1 | Yes — safest |
| S-03 | `edge_by_loop_type` | face | N edges | 1 | Yes, with loop guard |
| S-04 | `edge_by_geometry_type` | face/body | N edges | 1 | Yes, with scope |
| S-05 | `face_by_area_rank` | body | 1 face | 1 | Yes, with near-equal warning |
| S-06 | `body_by_name` / `body_by_attribute` | component | 1 body | 1 | Yes |
| S-07 | `face_by_normal_parallel` | body | N faces | 2 | Yes, declare expect=many |
| S-08 | `edge_by_length_rank` | face/body | 1 edge | 2 | Yes, with near-equal warning |
| S-09 | `face_by_cylinder_axis` | body | N faces | 2 | Yes, declare expect=many |
| S-10 | `vertex_by_position_rank` | body | 1 vertex | 2 | Conditional — prismatic only |
| S-11 | `face_by_adjacency` | face | N faces | 3 | Prototype — not production |
| S-12 | `edge_by_tangent_chain` | edge | N edges | 3 | Prototype — not production |

---

*Sources: ParamAItric Verification Trust Model (internal Google Doc, March 2026); Fusion 360 B-Rep and Geometry API Reference (Autodesk official documentation); ParamAItric README.md (boxwrench/paramAItric, GitHub); Autodesk AU2018 paper "Understanding Geometry and B-Rep in Inventor and Fusion 360" (ekinssolutions.com); build123d and CadQuery landscape review (prior session, April 2026). Files `ARCHITECTURE.md`, `BEST_PRACTICES.md`, `live_ops.py`, `tool_specs.py`, `workflow_registry.py` were inaccessible via web fetch; claims about those files are inferred from README context and marked accordingly.*
