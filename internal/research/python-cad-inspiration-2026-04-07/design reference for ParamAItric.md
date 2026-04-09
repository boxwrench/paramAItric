# Build123d as a design reference for ParamAItric

**Build123d should serve as a design reference and selective idea source for ParamAItric—not a runtime dependency.** The two systems share overlapping geometric concerns but target fundamentally different kernels (OCCT vs. Fusion 360's ASM), making deep runtime coupling both technically risky and architecturally unnecessary. Build123d's greatest contributions to ParamAItric are conceptual: its **ShapeList selector system**, **Mode enum pattern**, **location generators**, and **reusable parametric-part recipe structure** are all kernel-independent ideas that can be ported without introducing any dependency. ParamAItric's verification trust model, dual-lane architecture, and Fusion-specific execution layer are substantially more sophisticated than anything in build123d's ecosystem and must remain fully owned. The recommended posture is **Option A now (reference only)** with a plausible upgrade path to **Option B (build123d-inspired internal abstraction layer)** if ParamAItric later needs backend neutrality.

---

## 1. Executive summary

- **Build123d is a mature (v0.10.0), well-architected Python CAD framework** built on OCCT, offering ~1.2k GitHub stars, Apache-2.0 license, dual API modes, and a clean module structure approaching its 1.0 API freeze.
- **ParamAItric operates on a fundamentally different kernel** (Fusion 360's ASM) and owns a verification trust model, dual-lane workflow architecture, and TNP-handling strategy that have no equivalent in build123d.
- **Build123d's selector system is the single most transferable pattern**—its ShapeList with `.sort_by()`, `.filter_by()`, `.group_by()` replaces fragile entity-token and face-index references with geometry-based queries, directly complementing ParamAItric's attribute-based persistent naming.
- **Six to eight build123d concepts can be borrowed today** as pure architectural patterns with zero runtime coupling and minimal engineering cost.
- **Runtime dependency on build123d would introduce OCCT as a transitive binary dependency**, adding ~400 MB of compiled OCCT bindings, a second geometric kernel with different tolerance behavior, and a maintenance surface ParamAItric cannot control.
- **The semantic gap between OCCT and ASM is non-trivial**: Fusion 360 has a parametric timeline, sketch constraint solver, multi-body component model, and T-spline support that build123d lacks. An IR bridging both would require significant abstraction work.
- **ParamAItric's MCP layer, verification contract, AI-facing tool surface, and Fusion bridge must remain 100% owned**—these are the product's core differentiators and cannot be delegated.
- **Recommended posture: build123d as reference only (Option A) now, with an internal abstraction layer (Option B) as a future evolution** if ParamAItric needs to support multiple backends.
- **A 30-day plan of selective borrowing** (selector patterns, Mode enum, location generators, testing assertions) delivers immediate value with minimal risk.
- **Deeper integration should only be considered** once ParamAItric has shipped v1.0, proven demand for non-Fusion backends, and built its own abstraction layer that could host multiple adapters.

---

## 2. Capability comparison table

| Area | build123d capability | ParamAItric current capability | Who is ahead | Why it matters |
|------|---------------------|-------------------------------|--------------|----------------|
| **Geometry primitives (3D)** | Box, Cylinder, Cone, Sphere, Torus, Wedge, CounterBoreHole, CounterSinkHole, Hole | Sketch + Extrude confirmed; Box-like primitives via macros | build123d | Richer primitive library reduces AI reasoning steps per part |
| **Geometry primitives (2D)** | 20+ sketch objects (Circle, Rectangle, Polygon, Slot variants, Text, etc.) | Sketches with profiles, constraints referenced in design docs | build123d | More sketch primitives = fewer custom sketch constructions |
| **Geometry primitives (1D)** | 25+ curve objects (Line, Arc variants, Spline, Bezier, Helix, Airfoil) | Not detailed in available docs | build123d | Curve primitives enable sweep/loft workflows |
| **Sketch → 3D workflow** | Strict 1D→2D→3D dimensional hierarchy with make_face→extrude pattern | Sketch-then-feature paradigm via Fusion 360 API | Comparable | Both enforce sketch-first discipline |
| **Selectors / topology references** | ShapeList with filter_by, sort_by, group_by; geometry-based queries; avoids TNP | Custom Attributes for persistent naming; entityToken for diagnostics; volume-delta verification | **Different strengths** | build123d avoids TNP via query; ParamAItric solves it via metadata injection. Complementary strategies. |
| **Fillet / chamfer** | Mature; works across 1D, 2D, 3D dimensions | Referenced in verification examples; implementation unknown | build123d (maturity) | Edge treatment is the most failure-prone CAD operation for AI |
| **Loft** | Full multi-section loft with ruled option via OCCT BRepOffsetAPI_ThruSections | Referenced in failure mode analysis | build123d (maturity) | Lofts generate the most sliver-face failures |
| **Revolve** | Full revolve around arbitrary axis | Not confirmed in design docs | build123d | Critical for turned parts |
| **Sweep** | Full sweep with transition, normal, binormal control | Referenced in body count context | build123d (maturity) | Sweep failures are common AI error source |
| **Shell / offset** | Full offset with configurable face openings | Not mentioned in design docs | build123d | Essential for enclosure/housing design |
| **Draft** | Draft angle on faces for manufacturing | Not mentioned | build123d | Manufacturing-oriented feature |
| **Boolean operations** | `+`/`-`/`&` operators; vectorized subtraction | Join, Cut, Intersect confirmed; volume-delta verification | ParamAItric (verification) | ParamAItric's boolean verification is unmatched |
| **Assemblies / joints** | 5 joint types (Rigid, Revolute, Linear, Cylindrical, Ball); anytree hierarchy | Multi-component awareness; interference analysis | build123d (API design) | Joint-driven assembly is cleaner than coordinate placement |
| **Export / import** | STEP, STL, 3MF, BREP, glTF, SVG, DXF; SVG-to-code translator | STL/OBJ export referenced; Fusion-native save | build123d (breadth) | ParamAItric's Fusion-native output is the actual product |
| **Verification / validation** | `is_valid`, volume/area/bounding_box assertions in tests | 4-tier trust model; hard gates; soft warnings; compliance audits; rollback | **ParamAItric** | ParamAItric's verification architecture is engineering-grade |
| **TNP handling** | Geometric-query selectors avoid the problem entirely | Custom Attributes + volume-delta gates; explicit TNP failure mode catalog | **ParamAItric** | ParamAItric treats TNP as a first-class engineering problem |
| **Testing infrastructure** | pytest + pytest-xdist; CI on 3 OS × 4 Python versions; mypy; benchmarks | Design philosophy: "must test against live Fusion 360" | build123d (automation) | ParamAItric needs a complementary fast-feedback test layer |
| **AI-facing tool surface** | None (developer-facing Python API) | Full MCP protocol; typed tools; prompt templates; resources | **ParamAItric** | This is ParamAItric's core differentiator |
| **Workflow orchestration** | Builder context managers; Mode enum | Dual-lane (structured macros + guided freeform); promotion pipeline | **ParamAItric** | ParamAItric's dual-lane architecture is unique in the ecosystem |
| **Code organization** | Clean module split: geometry, topology, objects, operations, builders, exporters | Layered: MCP → Workflow → Verification → Fusion Bridge | Comparable | Both are well-architected for their domain |

---

## 3. Transferable ideas for ParamAItric

### ShapeList selector pattern

**What build123d does:** Wraps topology collections (faces, edges, vertices) in a `ShapeList` subclass of Python `list` with `.sort_by(Axis.Z)`, `.filter_by(GeomType.CYLINDER)`, `.group_by(SortBy.AREA)`, and lambda predicates. Chains like `part.edges().filter_by(Axis.Z).sort_by(SortBy.LENGTH)[-1]` replace brittle ID-based selection with declarative geometric queries.

**Why it helps ParamAItric:** Directly complements the Custom Attributes strategy. When the AI needs to reference "the top face" or "the longest vertical edge," a geometric-query selector is more robust than name-based lookup and more AI-friendly than raw Fusion API iteration. The pattern works identically against `BRepBody.faces`, `BRepBody.edges`, and `BRepBody.vertices` in Fusion 360's API.

**How invasive:** Low. Implement a `FusionShapeList` class wrapping Fusion 360's `BRepFaces`/`BRepEdges` collections with the same `.sort_by()`, `.filter_by()`, `.group_by()` interface. ~200-400 lines of Python, no new dependencies.

**Recommended timing:** **Now.** This is the single highest-value pattern to borrow.

---

### Mode enum for boolean intent

**What build123d does:** Every geometric object and operation accepts a `mode` parameter: `Mode.ADD` (union, default), `Mode.SUBTRACT` (cut), `Mode.INTERSECT`, `Mode.REPLACE`, `Mode.PRIVATE` (create without combining). Hole objects default to `Mode.SUBTRACT`. This makes boolean intent explicit at creation time.

**Why it helps ParamAItric:** Eliminates an entire class of AI errors—the LLM never has to decide separately "create geometry, then boolean it." Intent is encoded in the operation itself. Maps directly to Fusion 360's `FeatureOperations.JoinFeatureOperation`, `CutFeatureOperation`, `IntersectFeatureOperation`, `NewBodyFeatureOperation`.

**How invasive:** Trivial. Define a Python enum. Thread it through the MCP tool parameters.

**Recommended timing:** **Now.**

---

### Location generators for pattern placement

**What build123d does:** Provides `GridLocations(dx, dy, nx, ny)`, `PolarLocations(radius, count, start_angle)`, and `HexLocations(spacing, nx, ny)` as composable location generators. These produce lists of transform matrices for placing repeated features.

**Why it helps ParamAItric:** AI-generated code for "6 holes equally spaced on a circle" is error-prone with manual trigonometry. Location generators make this a one-liner. Maps directly to Fusion 360's `RectangularPatternFeature` and `CircularPatternFeature`, but also works for sketch-level placement.

**How invasive:** Very low. Pure geometry utilities—~100 lines of math, no kernel dependency.

**Recommended timing:** **Now.**

---

### Reusable parametric part base classes

**What build123d does:** Defines `BasePartObject`, `BaseSketchObject`, `BaseLineObject` as abstract base classes that custom parametric parts inherit from. A `PlatonicSolid(face_count=12, diameter=50)` or `Punch(radius=0.8, size=1, blobs=3)` becomes a first-class geometric object usable identically to built-in primitives.

**Why it helps ParamAItric:** Enables a library of reusable "part recipes" that the AI can invoke by name with parameters. A `MountingBracket(width=50, hole_count=4)` recipe could encapsulate 15 Fusion operations into a single MCP tool call. This is the natural structure for ParamAItric's `create_*` macro library.

**How invasive:** Medium. Requires defining a base class contract, a registration mechanism, and MCP tool generation for each recipe. But the pattern is pure Python—no build123d dependency.

**Recommended timing:** **Now** (define the pattern); **ongoing** (populate the library).

---

### Dimensional hierarchy discipline (1D → 2D → 3D)

**What build123d does:** Enforces a strict progression: curves (1D) compose into sketches (2D) which extrude/revolve/sweep into parts (3D). The documentation explicitly states: "Always work in the lowest possible dimension."

**Why it helps ParamAItric:** Codifying this as an AI generation constraint prevents the most common failure mode—attempting 3D operations without properly closed 2D profiles. Build123d's "delay fillets and chamfers until last" rule is equally important: edge treatments are the most topology-disrupting operations and should always be the final step.

**How invasive:** Zero—this is a prompt engineering and workflow validation rule, not a code change.

**Recommended timing:** **Now.**

---

### Snapshot-based change detection

**What build123d does:** Compares topology before and after an operation: `edges_before = part.edges(); part = fillet(...); new_edges = part.edges() - edges_before`. This identifies exactly which edges were created by an operation without relying on stable IDs.

**Why it helps ParamAItric:** Enables the verification layer to answer "what changed?" after each mutation. Combined with ParamAItric's Custom Attributes, this creates a two-layer system: attributes for semantic identity, snapshots for structural change detection.

**How invasive:** Low. Implement set arithmetic on `FusionShapeList`. The Fusion 360 API supports entityToken comparison for set operations within a single timeline step.

**Recommended timing:** **Later** (after FusionShapeList is built).

---

### Volume / bounding-box / face-count test assertions

**What build123d does:** Tests validate geometric outcomes using `assertAlmostEqual(part.volume, 6.0, places=5)`, `assertEqual(len(box.faces()), 6)`, and `part.bounding_box().size`. These are the primary verification primitives in the test suite.

**Why it helps ParamAItric:** ParamAItric already uses these concepts in its verification trust model (volume deltas, AABB checks, face counts as diagnostics). Build123d's test patterns show how to structure a **fast-feedback test harness** using these same signals—complementing ParamAItric's requirement for live Fusion 360 testing.

**How invasive:** Low. These assertions already exist conceptually in ParamAItric's verification framework. The contribution is the testing structure, not the assertions.

**Recommended timing:** **Now** (for the test structure pattern).

---

### Joint-driven assembly pattern

**What build123d does:** Defines named joints on parts (`RigidJoint("hinge_attachment", to_part=box, joint_location=...)`) and connects them declaratively (`box.joints["hinge"].connect_to(lid.joints["hinge"], angle=120)`). Parts snap together via semantic connection points rather than coordinate placement.

**Why it helps ParamAItric:** Makes assembly-level AI generation dramatically simpler. Instead of "place component B at position (x, y, z) with rotation (rx, ry, rz)," the AI says "connect B's hinge to A's hinge at 120 degrees." Maps to Fusion 360's joint system but with a cleaner semantic interface.

**How invasive:** Medium. Requires defining a joint vocabulary for MCP tools and mapping to Fusion 360's `JointOrigin` and `Joint` API.

**Recommended timing:** **Later** (when assembly support is prioritized).

---

### Unit constants as multipliers

**What build123d does:** Defines `MM = 1`, `CM = 10`, `IN = 25.4` as multipliers: `diameter = 50 * MM`. This makes units explicit and eliminates ambiguity in parametric code.

**Why it helps ParamAItric:** AI-generated dimensions without explicit units are a common error source. Unit constants make every dimension self-documenting and enable unit conversion without parsing.

**How invasive:** Trivial. ~5 lines of Python.

**Recommended timing:** **Now.**

---

## 4. Things ParamAItric should not outsource

**MCP integration and AI-facing tool surface.** This is ParamAItric's product identity—the typed tool definitions, prompt templates, and resource schemas that make AI-to-CAD translation possible. Build123d has no AI-facing layer whatsoever. Every MCP tool, every parameter schema, every error message that the LLM sees must be ParamAItric-native.

**Verification and recovery contract.** ParamAItric's 4-tier verification trust model (exact kernel facts → exact-but-context-sensitive → approximate → heuristic) is engineering-grade work that took deep research into ASM kernel behavior. Build123d offers only `is_valid` and basic property checks. The hard-gate / soft-warning / compliance-audit / diagnostic-only classification, the "exactly one mutation before verification" rule, and the timeline-based rollback mechanism are core IP.

**Fusion 360 execution layer and timeline management.** The Fusion 360 add-in, main-thread execution bridge, timeline manipulation (`rollTo`), and ASM kernel interaction are tightly coupled to Fusion's specific API surface. Build123d's OCCT wrapping is irrelevant here. The Fusion bridge is where ParamAItric's reliability promise is fulfilled.

**Fusion-native editable output.** The product goal is "editable 3D object in Fusion 360." This means the output must be a native Fusion 360 design with a clean timeline, proper sketch constraints, and editable parameters—not an imported STEP file. Build123d cannot contribute to this requirement.

**Dual-lane workflow orchestration.** The structured-macro / guided-freeform architecture with promotion pipeline between lanes is a unique architectural pattern. Build123d's builder contexts are simpler and lack the verification checkpoints, session management, and promotion logic that make ParamAItric's workflow robust.

**Topological naming strategy.** ParamAItric's Custom Attribute injection strategy for persistent naming is Fusion-specific (uses Fusion 360's Attributes API). Build123d avoids TNP through a different mechanism (geometric query selectors). Both strategies are valuable—ParamAItric should borrow the geometric query concept—but the attribute persistence layer must remain fully owned.

**Human-in-the-loop safety and guardrails.** The classification of what the AI can and cannot do autonomously, the commit/rollback decision points, and the escalation to human review are product safety decisions. These cannot be delegated to a library.

---

## 5. Architectural options

### Option A: build123d as reference only

**Benefits:** Zero dependency risk. Zero maintenance burden. Full product control. ParamAItric borrows ideas (selector patterns, Mode enum, location generators) and implements them natively against the Fusion 360 API. Build123d serves as a design catalog—read its source, learn from its patterns, implement equivalents.

**Risks:** Slightly slower development—each pattern must be reimplemented rather than imported. Risk of reinventing suboptimally if build123d's solutions are not studied carefully enough.

**Engineering cost:** Low. The transferable patterns described in Section 3 collectively require ~1,000-2,000 lines of new Python code, all targeting Fusion 360's API.

**Control impact:** Maximum. ParamAItric owns every line of code.

**Recommendation:** **Recommended as the immediate posture.** This is the correct default for a project at ParamAItric's stage.

---

### Option B: build123d-inspired internal abstraction layer

**Benefits:** Creates a ParamAItric-native abstraction layer (not build123d code, but inspired by its patterns) that decouples the AI-facing tool surface from Fusion-specific implementation. This is essentially "write your own build123d-style API but targeting Fusion 360." Enables future backend portability without current dependency.

**Risks:** Premature abstraction. If ParamAItric only ever targets Fusion 360, this layer adds indirection without benefit. Risk of "astronaut architecture"—abstracting before the concrete requirements are understood.

**Engineering cost:** Medium. Requires designing an internal operation vocabulary (extrude, revolve, fillet, etc.) with typed parameters, then implementing each operation against Fusion 360's API. Approximately 3,000-5,000 lines for a useful subset.

**Control impact:** High. All code is ParamAItric-native. The abstraction exists for internal clarity, not external dependency.

**Recommendation:** **Recommended as a medium-term evolution** (3-6 months). The abstraction layer naturally emerges as ParamAItric's `create_*` macro library grows. Don't design it upfront—let it crystallize from the patterns that prove useful.

---

### Option C: build123d as dev/test sidecar backend

**Benefits:** Enables fast geometry prototyping and headless testing without requiring a running Fusion 360 instance. Developers could validate geometric logic against OCCT locally, then execute against Fusion 360 for production. CI pipelines could run geometry tests without Fusion 360 licenses.

**Risks:** **This is the highest-risk option.** OCCT and ASM are different kernels with different tolerance behaviors, different boolean algorithms, and different surface representations. A model that validates perfectly in build123d may fail in Fusion 360 due to sliver faces, tolerance mismatches, or ASM-specific edge cases. This creates a **false confidence problem** that directly contradicts ParamAItric's verification philosophy—the Verification Trust Model explicitly warns that "mock environments rarely simulate the brutal, non-linear realities of the ASM kernel." Running tests against a different kernel is precisely this anti-pattern.

**Engineering cost:** High. Requires building a dual-backend adapter, mapping every Fusion 360 operation to a build123d equivalent, and maintaining semantic parity as both systems evolve. Also adds ~400 MB of OCCT binary dependencies.

**Control impact:** Reduced. Build123d and cadquery-ocp become transitive dependencies with their own release cycles, breaking changes, and platform support matrix.

**Recommendation:** **Not recommended.** The kernel-mismatch problem makes this actively dangerous for a system whose core value proposition is engineering-grade geometric reliability.

---

### Option D: future backend-neutral ParamAItric IR with multiple adapters

**Benefits:** If ParamAItric eventually needs to target multiple backends (Fusion 360, Onshape, FreeCAD/OCCT, SolidWorks), a neutral intermediate representation would enable write-once-execute-anywhere parametric modeling. Build123d's operation vocabulary could inform the IR design.

**Risks:** Very high engineering cost. Each backend adapter must handle kernel-specific semantics (feature timelines, constraint solvers, body management) that differ fundamentally. The IR must be rich enough to express these differences without becoming a lowest-common-denominator abstraction that loses the unique capabilities of each backend.

**Engineering cost:** Very high. The IR design alone is a multi-month research project. Each backend adapter is a separate product-quality implementation. Maintaining semantic parity across backends as they evolve is an ongoing tax.

**Control impact:** Variable. The IR is ParamAItric-owned, but each backend adapter inherits the constraints and limitations of its target platform.

**Recommendation:** **Not recommended now. Monitor conditions described in Section 7.** If multiple backend demand materializes, begin with a minimal IR that covers the **20% of operations that produce 80% of parts** (sketch, extrude, fillet, chamfer, boolean, hole) rather than attempting comprehensive coverage.

The IR, if eventually built, should contain: an ordered sequence of typed operations (preserving Fusion-style timeline semantics), geometric-query selectors (inspired by build123d's ShapeList), explicit boolean mode per operation, and backend-specific escape hatches for capabilities that don't translate (T-splines, sketch constraints). It should **not** contain OCCT-specific topology types, kernel-specific tolerance parameters, or rendering/visualization data. The minimum viable slice to prove the concept would be: **Box + Hole + Fillet targeting both Fusion 360 and a headless OCCT backend**, validating volume equivalence within tolerance.

---

## 6. Recommended near-term plan (30 days)

**Week 1: Study and document.** Read build123d's `topology/composite.py` (ShapeList), `build_common.py` (Builder base class), `operations_generic.py` (fillet/chamfer/mirror/offset), and `operations_part.py` (extrude/revolve/loft/sweep). Document the patterns. No code changes yet. Pay special attention to how `ShapeList.filter_by()` uses lambdas and `GeomType` enums, how `sort_by()` projects onto axes, and how `group_by()` produces indexed sublists. Also study 3-4 example files in the `examples/` directory to see how real parts are built.

**Week 2: Implement FusionShapeList.** Build a `FusionShapeList` class that wraps Fusion 360's `BRepFaces`, `BRepEdges`, and `BRepVertices` with the same `.sort_by(axis)`, `.filter_by(geom_type)`, `.filter_by(lambda)`, `.group_by(axis)` interface. Use `face.geometry` type checking for `GeomType` filtering, `face.centroid` for axis sorting, and `face.area` / `edge.length` for property-based filtering. Write tests against a live Fusion 360 instance using a simple box-with-hole test model.

**Week 3: Implement Mode enum and location generators.** Define `ParamAItricMode` enum (`ADD`, `SUBTRACT`, `INTERSECT`, `NEW_BODY`, `PRIVATE`) mapping to Fusion 360's `FeatureOperations`. Build `GridLocations`, `PolarLocations`, and `HexLocations` as pure-math generators that return lists of `Matrix3D` transforms. Wire both into existing MCP tool parameters. Add unit constants (`MM`, `CM`, `IN`, `FT`).

**Week 4: Codify workflow rules and sketch the part-recipe pattern.** Add "delay fillets/chamfers" and "1D→2D→3D progression" as explicit validation rules in the workflow orchestration layer. Define a `BasePartRecipe` abstract class with a standard constructor signature `(parameters: dict, mode: ParamAItricMode)` and implement one example recipe (`SimpleEnclosure(width, height, depth, wall_thickness, corner_radius)`) to validate the pattern. Document the recipe structure for future expansion.

**Ongoing parallel track:** As new `create_*` macros are built, structure them using the patterns borrowed in weeks 2-4. Let the internal abstraction layer (Option B) emerge organically from recurring patterns in the macro library.

---

## 7. Long-term integration trigger points

Deeper integration with build123d (Options C or D) should only be considered when **all** of the following conditions are true:

**ParamAItric has shipped a production v1.0 targeting Fusion 360.** The core product must be proven before introducing backend complexity. Premature abstraction is the most common architectural mistake in early-stage systems.

**Concrete demand exists for a non-Fusion backend.** Actual users or customers have requested Onshape, FreeCAD, or headless OCCT support. Hypothetical demand does not justify the engineering cost.

**ParamAItric's internal abstraction layer (Option B) has naturally stabilized.** The `create_*` macro library has grown to 20+ operations, the `FusionShapeList` is battle-tested, and a clear operation vocabulary has emerged from usage patterns. This organic abstraction is the foundation any IR would build on.

**The Fusion 360 bridge has demonstrated the verification trust model in production.** Hard gates, soft warnings, and compliance audits are working reliably. The team understands, through operational experience, exactly which verification signals are kernel-specific and which are kernel-neutral.

**Build123d has released v1.0 with a stable API.** As of April 2026, build123d is at v0.10.0 and approaching its 1.0 API freeze. Depending on a pre-1.0 library for production infrastructure would introduce unnecessary churn.

**A quantified cost-benefit analysis shows the dual-backend maintenance burden is justified by revenue or user growth.** Each backend adapter is ~6 months of engineering and ongoing maintenance. This must be justified by concrete business metrics, not technical enthusiasm.

**Signal that ParamAItric is ready:** When a developer can describe, from memory, which 5 Fusion 360 API calls implement each `create_*` macro—and can articulate exactly which of those calls are ASM-specific vs. kernel-neutral—the team has the domain knowledge to design a meaningful IR.

---

## 8. Sources

### build123d sources
- Repository: https://github.com/gumyr/build123d (v0.10.0, Apache-2.0)
- Documentation: https://build123d.readthedocs.io/en/latest/
- Key source modules analyzed: `src/build123d/geometry.py`, `build_common.py`, `build_part.py`, `build_sketch.py`, `build_line.py`, `objects_part.py`, `objects_sketch.py`, `objects_curve.py`, `operations_generic.py`, `operations_part.py`, `operations_sketch.py`, `topology/` subpackage (shape_core.py, composite.py, zero_d.py, one_d.py, two_d.py, three_d.py), `joints.py`, `importers.py`, `exporters3d.py`, `exporters2d.py`
- Test infrastructure: `tests/` directory, pytest with pytest-xdist, GitHub Actions CI

### ParamAItric sources
- Repository: https://github.com/boxwrench/paramAItric (private repository; code not directly accessible)
- "ParamAItric Verification Trust Model: Strategic Framework for AI-Driven CAD Geometry Validation" (Google Drive, Keith Wilkinson, March 11, 2026) — primary architectural reference
- "Emergent Ventures Application" (Google Drive, Keith Wilkinson, April 4, 2026) — project context
- "Research Brief: ParamAItric Freeform CAD" (Google Drive, March 11, 2026) — referenced but content timed out
- "CAD Reference Intake Pipeline Research" (Google Drive, March 11, 2026) — referenced but content timed out
- "Fusion 360 API Research Questions" (Google Drive, March 10, 2026) — referenced but content timed out

### Fusion 360 ecosystem references
- Autodesk Fusion 360 API documentation (Feature.healthState, BRepBody.physicalProperties, BRepBody.isSolid, analyzeInterference, MeasureManager, Attributes API, Timeline API)
- Comparative analysis of 10+ public Fusion 360 MCP server implementations (Joe-Spencer, AuraFriday, rahayesj, JustusBraitinger, faust-machines, jaskirat1616, ArchimedesCrypto, sockcymbal, Misterbra, etc.)