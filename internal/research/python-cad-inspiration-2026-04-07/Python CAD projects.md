# Python CAD projects that should shape ParamAItric's next evolution

**build123d and CadQuery contain the highest-density design inspiration for ParamAItric's near-term architecture, while FreeCAD offers the deepest lessons on the exact problems ParamAItric will face at scale.** SolidPython2 and pythonOCC sit at opposite extremes—one too high-level (CSG transpilation) and one too low-level (raw kernel bindings)—but each contributes a narrow, specific insight. The five projects collectively demonstrate that the hardest unsolved problem in programmatic CAD is stable geometry referencing across mutations, and that the most productive architectural pattern for AI-driven CAD is a semantic intermediate representation that decouples intent from execution. ParamAItric already owns the pieces that matter most—MCP integration, Fusion 360 bridge execution, verification gating, and recovery logic—but its internal geometry abstractions and selector strategies can be dramatically improved by borrowing specific patterns without adopting any external dependency.

---

## 1. Executive summary

- **build123d is ParamAItric's single most valuable reference.** Its semantic `ShapeList` selectors (`faces().filter_by(Axis.Z)[-1]`, `edges(Select.LAST)`) directly solve the topology naming fragility that ParamAItric already identifies as a critical vulnerability. Its dual builder/algebra API demonstrates two co-equal paradigms for AI code generation.

- **CadQuery's string selector DSL and tag system offer an alternative selector language** that is more compact than build123d's method chains and may be better suited for constrained LLM token budgets. The `tag()`/`workplaneFromTagged()` bookmark pattern maps directly to ParamAItric's need to track named states across mutations.

- **FreeCAD's Topological Naming Problem solution is the most relevant architectural lesson** in the entire landscape. Its element-map approach—encoding creation history into topology names—is the open-source state-of-art for the exact problem ParamAItric battles via custom Fusion API Attributes.

- **FreeCAD's expression engine and property system** demonstrate how parametric dependencies can be tracked as a DAG with change propagation, a model ParamAItric should study for its own parameter-driven workflows.

- **build123d's `BasePartObject` subclassing pattern** is the cleanest approach to reusable parameterized part recipes and should directly inform ParamAItric's "part template" strategy for LLM-generated components.

- **SolidPython2's extension architecture** (core ~1000 lines, everything else layered as extensions) is an elegant model for keeping ParamAItric's own tool surface minimal and composable, even though the CSG paradigm itself is irrelevant.

- **SolidPython2's operator overloading for CSG** (`+`, `-`, `&`) is worth studying as a compact notation for boolean intent that LLMs handle well, but the lack of topology queries and fillets makes the CSG paradigm fundamentally incompatible with ParamAItric's B-rep requirements.

- **pythonOCC is relevant only as kernel literacy.** Understanding how `TopExp_Explorer` iterates B-rep topology and how `BRepFilletAPI_MakeFillet` works helps ParamAItric's team reason about what happens beneath both Fusion's ASM kernel and OCCT-based libraries.

- **No project should be adopted as a runtime dependency.** Every library either outputs static geometry (destroying Fusion timeline editability) or introduces kernel mismatch risk with Fusion's ASM engine.

- **The highest-value near-term action** is designing a semantic selector system for ParamAItric's Fusion add-in that translates build123d-style semantic queries into Fusion B-rep entity resolution at runtime.

- **ParamAItric's verification trust model is already more sophisticated than any testing approach found in these five projects.** This is a genuine competitive advantage that should be preserved and deepened, not diluted by adopting external validation patterns.

- **The concept of a ParamAItric Intermediate Representation (IR)**—where the LLM generates a high-level pseudo-DSL inspired by build123d syntax, which is then compiled to Fusion API calls—emerges as the strongest architectural direction from this landscape review.

---

## 2. Candidate comparison table

| Project | Core modeling paradigm | Strongest abstractions | Most relevant inspiration for ParamAItric | Main mismatch or limitation | Near-term relevance |
|---|---|---|---|---|---|
| **build123d** | B-rep CAD-as-code via OCCT; dual builder (context managers) + algebra (operators) modes | ShapeList selectors with `filter_by`/`sort_by`/`group_by`; `BasePartObject` subclassing; Location arithmetic (`Plane * Pos * Rot * Shape`); `Mode` enum for implicit booleans | Semantic topology selection; context-managed builder state; parameterized part recipes via class inheritance; joint-based assembly declarations | Outputs static STEP/STL; no parametric timeline; OCCT kernel ≠ Fusion ASM kernel; boolean edge cases differ between kernels | **High** |
| **CadQuery** | Workplane-centric fluent API over OCCT; automatic stack-based iteration | String selector DSL (`">Z"`, `"|X"`, `"%CIRCLE"`); `tag()`/`workplaneFromTagged()` state bookmarks; construction geometry (`forConstruction=True`); constraint-based assembly solver | Compact selector syntax for LLM token efficiency; tag-based state persistence across operations; three-tier API layering (Fluent → Direct → OCCT) with escape hatches | Same static output problem as build123d; fluent chaining is harder for LLMs than block-structured code; string selectors lack IDE autocompletion | **High** |
| **FreeCAD** | Document-object model with feature tree DAG; property system + expression engine; Part (CSG) and PartDesign (feature-based) workbenches | TNP solution via element maps with history encoding; expression engine for parametric dependencies; `FeaturePython` proxy pattern for scripted parametric objects; App/Gui architectural split | TNP mitigation strategy; parametric dependency DAG; property-driven recomputation model; assembly joint types; geometry validation (`isValid`, `check()`) | Scripting API is verbose and fragile (magic strings like `"Part::Feature"`); PartDesign scripting especially painful; massive codebase with complex C++ core | **High** |
| **SolidPython2** | CSG tree builder → OpenSCAD transpiler; Python as host language for code generation | Extension architecture (~1000-line core + pluggable extensions); operator overloading for boolean algebra; fluent method chaining (`.up(10).rotateY(90)`); `__repr__` → generated code for REPL debugging | Extension architecture pattern for minimal, composable tool surface; transparent transpilation model; Python functions as reusable part definitions | No topology queries; no fillets/chamfers; no B-rep; no STEP export; fundamentally CSG-limited; irrelevant to manufacturing-grade CAD | **Low** |
| **pythonOCC** | Direct 1:1 SWIG bindings of OCCT C++ API; ~1000+ classes exposed verbatim | `TopologyExplorer` Pythonic iterator over B-rep; `ShapeFactory` convenience functions; full access to advanced OCCT algorithms (NURBS, surface analysis, HLR) | Kernel literacy for understanding what OCCT-based libraries do underneath; `TopologyExplorer` pattern for B-rep traversal; understanding B-rep construction pipeline (geometry → edge → wire → face → solid) | Non-Pythonic API; steep learning curve; no abstraction over OCCT complexity; entirely wrong level for AI code generation | **Low** |

---

## 3. Project-by-project review

### build123d: the most AI-compatible CAD DSL in the Python ecosystem

**What it is.** A Python B-rep CAD framework built on OCCT via `cadquery-ocp` bindings. Originally derived from CadQuery but extensively refactored into an independent system with two co-equal API modes: a builder mode using Python context managers and an algebra mode using operator overloading.

**What it does especially well.** build123d's **semantic topology selector system** is its crown achievement. Rather than referencing geometry by fragile indices (`Face6`, `Edge3`), it provides composable `ShapeList` pipelines: `part.faces().filter_by(Axis.Z).sort_by(SortBy.AREA)[-1]` reads like natural language and sidesteps the Topological Naming Problem entirely. The `Select.LAST` and `Select.NEW` modifiers allow operation-aware selection—"give me only the edges created by the last boolean operation"—which is exactly what an AI needs for follow-up operations like fillets. The **dimensional stratification** (1D `BuildLine` → 2D `BuildSketch` → 3D `BuildPart`) enforces a clean workflow progression that matches how LLMs naturally sequence CAD operations. The **`BasePartObject` subclassing pattern** lets custom parametric parts become first-class citizens with IDE autocompletion and full operator support.

**Best ideas worth borrowing.**
- *Semantic selectors as the primary referencing strategy.* ParamAItric should build geometric evaluation functions in the Fusion add-in that resolve `filter_by(Axis.Z)[-1]` style queries against live B-rep topology at runtime, replacing index-based face targeting.
- *Context-managed builder state.* The `with BuildPart():` pattern naturally reduces LLM token consumption by ~60-80% compared to raw Fusion API verbosity and eliminates the need for the AI to track explicit object references.
- *`Mode` enum for implicit booleans.* Having `Hole` default to `Mode.SUBTRACT` and `Box` default to `Mode.ADD` eliminates an entire class of AI boolean-direction errors.
- *`BasePartObject` for reusable part recipes.* ParamAItric's LLM should generate parameterized classes whose `__init__` arguments map directly to Fusion 360 User Parameters.
- *Location arithmetic.* `Plane * Pos(x,y,z) * Rot(X=90) * Shape` is far more readable and composable than 4×4 transformation matrices, and LLMs handle this syntax reliably.

**What ParamAItric should not copy.** The implicit auto-registration of objects to the active builder context ("magic") can confuse debugging and error recovery. ParamAItric needs explicit control over what gets committed to the Fusion timeline. The OCCT kernel itself is irrelevant—ParamAItric targets Fusion's ASM kernel, and boolean operation edge cases differ significantly between the two kernels.

**Why it is strategically relevant.** build123d solves the LLM-to-CAD communication problem better than any other project in this landscape. Its syntax is essentially what an ideal "ParamAItric IR" would look like. The internal research doc on build123d integration already identifies this correctly—the value is in the DSL design patterns, not the runtime dependency.

**Influence category:** Geometry abstraction, selector/reference model, workflow abstraction.

---

### CadQuery: the selector pioneer with a tag-based state persistence model

**What it is.** A Python parametric CAD library built on OCCT with a jQuery-inspired fluent chaining API centered on the `Workplane` abstraction. Every operation returns a new Workplane, enabling method chaining: `Workplane("XY").box(1,2,3).faces(">Z").vertices().circle(0.5).cutThruAll()`.

**What it does especially well.** CadQuery's **string selector DSL** is the most compact geometry referencing system in the landscape. `">Z"` (farthest in Z), `"|X"` (parallel to X), `"%CIRCLE"` (circle type), and combinators like `"|Z or <Z"` pack enormous semantic content into minimal tokens. The **`tag()`/`workplaneFromTagged()` bookmark system** lets scripts name intermediate states and return to them later—a pattern that maps perfectly to tracking AI-generated features across a multi-step workflow. The **construction geometry** concept (`forConstruction=True`) cleanly separates reference geometry from final part geometry. The **constraint-based assembly solver** (using scipy optimization) demonstrates a declarative approach to assembly positioning where parts are constrained rather than manually positioned.

**Best ideas worth borrowing.**
- *String selector syntax for token-efficient LLM output.* Where build123d uses verbose method chains, CadQuery's `">Z"` is 3 characters. For constrained context windows, this compactness matters.
- *`tag()`/`workplaneFromTagged()` for named state persistence.* ParamAItric's "semantic target tracking via Attributes" strategy is essentially the same concept. CadQuery validates the pattern.
- *Construction geometry as a first-class concept.* Allowing the AI to create reference geometry that doesn't become part of the final solid prevents a class of errors where helper geometry accidentally unions with the part.
- *Three-tier API layering with escape hatches.* Fluent API for most work, Direct API (Shape classes) for intermediate control, raw OCCT for edge cases. ParamAItric should similarly layer its IR: high-level pseudo-DSL → structured Fusion commands → raw Fusion API fallback.
- *Auto-iteration over stack items.* When 4 vertices are selected, `.circle(0.5)` creates 4 circles automatically. This eliminates explicit for-loops that LLMs frequently get wrong.

**What ParamAItric should not copy.** The fluent chaining API is actually harder for LLMs than block-structured code (build123d's context managers). Long chains create error propagation—if one step fails, the entire chain is invalid. CadQuery's string selectors, while compact, lack IDE autocompletion and type checking (build123d improved on this with enums). The constraint-based assembly solver, while elegant, is computationally expensive and Fusion 360 has its own joint solver that should be used natively.

**Why it is strategically relevant.** CadQuery provides the strongest evidence that compact selector DSLs are viable and productive. The tag system validates ParamAItric's attribute-based naming strategy. The `cqparts` library for reusable parts demonstrates that the Python CAD community has already solved the "part recipe" problem—ParamAItric should learn from it rather than reinventing it.

**Influence category:** Selector/reference model, API design, workflow abstraction.

---

### FreeCAD Python scripting: the deepest lessons on parametric CAD architecture

**What it is.** An open-source parametric CAD application with a Python scripting API that wraps a C++ core using OCCT. Its architecture separates data (App) from visualization (Gui), uses a document-object model with a feature tree DAG, and recently solved the Topological Naming Problem in v1.0.

**What it does especially well.** FreeCAD's **TNP solution** is the most sophisticated open-source approach to stable geometry referencing. Each shape carries an `ElementMap` encoding its creation history—which operations created or modified each face and edge. When topology changes, the system traces which new elements correspond to old references. This is stored as "shadow copies" in `PropertyLinkSub` for backward compatibility. The **expression engine** allows properties to reference other properties via formulas (`obj.setExpression('Height', 'OtherBox.Width * 2')`), creating a bidirectional dependency graph that automatically propagates changes. The **`FeaturePython` pattern** (Python proxy objects for C++ DocumentObjects) is an elegant extensibility mechanism where Python classes define `execute()` methods to regenerate geometry when parameters change.

**Best ideas worth borrowing.**
- *Element maps with history encoding for topology stability.* While ParamAItric uses custom Fusion Attributes for persistent naming, FreeCAD's approach of encoding creation history into element names is conceptually richer. ParamAItric should consider encoding "this face was created by extrude operation #3 from sketch edge #2" into its attribute metadata.
- *Expression engine for parametric dependencies.* ParamAItric's LLM-generated models should produce Fusion 360 User Parameters linked by expressions, not hardcoded values. FreeCAD's expression system demonstrates the pattern.
- *App/Gui split for headless operation.* ParamAItric already effectively has this (MCP server + Fusion add-in), but FreeCAD's clean architectural separation validates the approach and shows how to handle recomputation triggering.
- *`FeaturePython` proxy pattern.* The concept of a Python class that defines `execute()` to regenerate geometry based on typed properties is a clean model for ParamAItric's "part recipe" structure.
- *Geometry validation methods.* `shape.isValid()`, `shape.check()`, and `shape.fix()` demonstrate a three-tier validation approach (bool check → detailed diagnostics → attempted repair) that complements ParamAItric's hard-gate/soft-warning/audit framework.

**What ParamAItric should not copy.** FreeCAD's scripting API is notoriously verbose and fragile for programmatic use. Magic strings (`"Part::Feature"`, `"PartDesign::Body"`), manual `doc.recompute()` calls, and complex PartDesign setup sequences are anti-patterns for AI-driven generation. The two-workbench split (Part vs PartDesign) creates confusion that ParamAItric should avoid. FreeCAD's assembly story remains fragmented despite improvements in v1.0.

**Why it is strategically relevant.** FreeCAD is the only project in this landscape that has deeply confronted and shipped a solution for the Topological Naming Problem. Since TNP is identified in ParamAItric's own verification trust model as a fundamental challenge, FreeCAD's approach deserves careful study. The expression engine and property system also model how ParamAItric should think about parametric dependency tracking.

**Influence category:** Selector/reference model, execution architecture, testing/validation.

---

### SolidPython2: clean architecture, wrong paradigm

**What it is.** A Python-to-OpenSCAD transpiler that constructs an in-memory CSG tree and serializes it to OpenSCAD code. It does not evaluate geometry itself—OpenSCAD (backed by CGAL) handles all computation.

**What it does especially well.** SolidPython2's **extension architecture** is remarkably clean. The core is ~1000 lines providing a 1:1 mapping of OpenSCAD→Python. Everything else—operator overloading, method chaining, convenience functions, BOSL2 support—is implemented as pluggable extensions. This separation means the core is lightweight, testable, and stable while the ergonomics layer evolves independently. The **`__repr__` → generated code** feature provides instant REPL feedback showing exactly what the Python object tree will produce, which is excellent for debugging and testing. The **operator overloading** (`+` for union, `-` for difference, `&` for intersection) creates a natural algebraic notation that LLMs handle reliably.

**Best ideas worth borrowing.**
- *Extension architecture for tool surface management.* ParamAItric should keep its core MCP tool surface minimal and composable, with higher-level convenience patterns layered as optional modules—exactly the pattern SolidPython2 demonstrates.
- *Transparent transpilation as a debugging tool.* The idea that every intermediate object can render itself as its target representation (`__repr__` → OpenSCAD text) should inspire ParamAItric to make its IR inspectable—every IR node should be able to render itself as the Fusion API code it will produce.
- *Python functions as part definitions.* SolidPython2 proves that standard Python functions are sufficient for reusable parametric parts—no framework magic needed.

**What ParamAItric should not copy.** The entire CSG paradigm is fundamentally incompatible with ParamAItric's needs. CSG cannot do fillets, chamfers, or edge-specific operations. There are no topology queries, no face/edge selection, no STEP export. The coincident-face epsilon-offset problem is a constant source of frustration. SolidPython2 adds zero geometric capability over OpenSCAD—it's purely a syntax layer.

**Why it is not strategically relevant.** ParamAItric targets engineering-grade parametric B-rep modeling in Fusion 360. CSG's fundamental limitations (no fillets, no topology, mesh-only output) make SolidPython2 architecturally irrelevant to ParamAItric's geometry needs. However, the extension architecture pattern is a genuine contribution to the design conversation.

**Influence category:** Low-level architecture inspiration (extension pattern only).

---

### pythonOCC: the assembly language of Python CAD

**What it is.** Near-complete 1:1 Python bindings of the OCCT C++ library, auto-generated via SWIG. Wraps ~1000+ OCCT classes with identical C++ naming conventions (`BRepPrimAPI_MakeBox`, `gp_Pnt`).

**What it does especially well.** pythonOCC provides **the only way to access the full OCCT kernel from Python**. While CadQuery and build123d expose a curated subset, pythonOCC wraps everything: advanced NURBS surfaces, parametric curve evaluation, mesh generation, HLR algorithms, mass property analysis. The `TopologyExplorer` utility in `OCC.Extend` provides Pythonic iterators (`for face in TopologyExplorer(shape).faces()`) over B-rep topology, replacing verbose `TopExp_Explorer` loops. The `ShapeFactory` convenience module (`recognize_face()` identifying plane/cylinder/cone/sphere/torus surface types) demonstrates practical topology analysis patterns.

**Best ideas worth borrowing.**
- *`TopologyExplorer` pattern for B-rep traversal.* Understanding how to iterate faces, edges, vertices and query adjacency relationships (`.faces_from_edge()`, `.edges_from_vertex()`) is essential kernel literacy for anyone building semantic selectors.
- *`recognize_face()` for surface type classification.* ParamAItric's semantic selector system will need to classify face types (planar, cylindrical, conical) to resolve queries like "select all cylindrical faces." pythonOCC's approach demonstrates the pattern.
- *B-rep construction pipeline understanding.* The geometry → edge → wire → face → shell → solid hierarchy is universal across all B-rep kernels including Fusion's ASM. Understanding this pipeline improves ParamAItric's ability to diagnose failures.

**What ParamAItric should not copy.** The API style (`BRepPrimAPI_MakeBox`, `gp_Trsf`) is the antithesis of what an AI-facing tool surface should look like. No operator overloading, no builder patterns, no fluent interface. The documentation gap is severe—learning happens through examples rather than comprehensive guides. pythonOCC is the wrong level of abstraction for AI code generation.

**Why it is not strategically relevant for near-term.** ParamAItric doesn't need direct OCCT access—it targets Fusion's ASM kernel. pythonOCC's value is purely educational: understanding the B-rep concepts that underlie both OCCT-based libraries and Fusion's own kernel helps the team make better architectural decisions.

**Influence category:** Low-level kernel knowledge.

---

## 4. Ranked inspiration list: top 10 ideas ParamAItric should study first

| Rank | Idea | Source project | Why it matters for ParamAItric | Conceptual difficulty |
|------|------|---------------|-------------------------------|----------------------|
| **1** | **Semantic topology selectors** (`filter_by`, `sort_by`, `group_by` on ShapeLists) | build123d | Directly solves the Topological Naming Problem that ParamAItric's verification trust model identifies as a critical vulnerability. Eliminates index-based face/edge targeting that breaks across mutations. The LLM outputs semantic intent ("the highest Z face"), and the Fusion add-in resolves it geometrically at runtime. | **Medium** — requires writing geometric evaluation functions in the Fusion add-in to iterate B-rep and resolve semantic queries against live topology. |
| **2** | **Context-managed builder state** (`with BuildPart():` implicit running total) | build123d | Reduces LLM token consumption by 60-80% compared to raw Fusion API. Eliminates explicit object reference tracking that LLMs frequently lose in long sequences. Maps naturally to a ParamAItric IR where each `with` block becomes a scoped operation in the Fusion timeline. | **Medium** — requires building an AST parser that translates pseudo-DSL blocks into sequenced Fusion API calls. |
| **3** | **Tag-based state bookmarks** (`tag()`/`workplaneFromTagged()`) | CadQuery | Validates and extends ParamAItric's attribute-based persistent naming strategy. Named intermediate states let the AI return to a previous point in the modeling sequence without re-selecting geometry—critical for complex multi-feature parts. | **Low** — conceptually simple; maps directly to Fusion API Attributes that ParamAItric already uses. |
| **4** | **Element maps with creation history encoding** (TNP solution) | FreeCAD | The most sophisticated approach to stable geometry referencing in open-source CAD. Encoding "this face was created by operation X from edge Y" into ParamAItric's attribute metadata would make semantic target tracking dramatically more robust across complex boolean chains. | **High** — requires deep understanding of Fusion's ASM kernel behavior during topology rebuilds and careful design of history-encoding schemes. |
| **5** | **Parameterized part recipes via class inheritance** (`BasePartObject` subclassing) | build123d | Clean pattern for LLM-generated reusable components. `__init__` parameters map directly to Fusion 360 User Parameters, satisfying the "editable 3D object" requirement. Enables a library of AI-generated part templates that compose naturally. | **Low** — primarily a prompt engineering and AST design decision. |
| **6** | **Expression engine for parametric dependencies** (`setExpression('Height', 'OtherBox.Width * 2')`) | FreeCAD | ParamAItric should generate models where dimensions are linked by expressions, not hardcoded values. This makes the AI output genuinely parametric—a human engineer can change one dimension and the rest follow. Fusion 360 already supports expressions; ParamAItric just needs to generate them. | **Low** — Fusion's expression system already exists; ParamAItric's LLM just needs to be prompted to use it. |
| **7** | **Three-tier API layering with escape hatches** (Fluent → Direct → OCCT) | CadQuery | ParamAItric should layer its own IR similarly: high-level pseudo-DSL (AI generates) → structured Fusion commands (ParamAItric transpiles) → raw Fusion API (fallback for edge cases). Each layer provides more control at the cost of more verbosity. | **Medium** — architectural design decision with moderate implementation complexity. |
| **8** | **Operation-aware edge tracking** (`Select.LAST`, `Select.NEW`) | build123d | Selecting "only the edges created by the last boolean operation" eliminates the need for the AI to spatially describe intersection edges. Critical for fillet/chamfer operations that typically follow boolean cuts. | **High** — requires capturing B-rep state before an operation, executing it, and computing a topological set-difference to identify new entities. |
| **9** | **Extension architecture for minimal core** (~1000-line core + pluggable extensions) | SolidPython2 | ParamAItric's MCP tool surface should remain minimal and tightly controlled. Higher-level conveniences (part templates, workflow macros, assembly helpers) should be layered as optional extensions that don't bloat the core. | **Low** — architectural principle that guides codebase organization rather than requiring specific implementation. |
| **10** | **Transparent IR rendering for debugging** (`__repr__` → generated target code) | SolidPython2 | Every node in ParamAItric's IR should be able to render itself as the Fusion API code it will produce. This makes the translation layer inspectable and debuggable—critical when diagnosing why an AI-generated design fails at the Fusion execution stage. | **Low** — straightforward implementation of `__repr__` or `to_fusion_code()` methods on IR nodes. |

---

## 5. Recommended research priority

### Rank 1: build123d — study first and deepest

**Why this order makes sense.** build123d contains the highest density of directly transferable design patterns for ParamAItric's most pressing needs: semantic selectors, builder state management, and parameterized part recipes. The existing internal research document on build123d integration already establishes the framework—the next step is implementation-level study of specific build123d modules. build123d is also the most "AI-compatible" syntax in the landscape, making it the natural reference for ParamAItric's IR design.

**Questions for the next deeper pass:**
- How exactly does `ShapeList.filter_by()` resolve against live OCCT topology? What Fusion B-rep API calls would replicate this resolution?
- What is the precise internal state management of `BuildPart`/`BuildSketch`/`BuildLine` contexts? How does the "running total" merge implicit results?
- How does `Select.NEW` compute the topological delta? What is the performance cost?
- How does `BasePartObject.__init__` handle alignment, mode, and rotation—and how should ParamAItric's IR represent these?
- What are the actual failure modes of build123d's OCCT boolean operations, and how do they differ from Fusion ASM failures?

### Rank 2: CadQuery — study for selector language design and state management

**Why this order makes sense.** CadQuery's string selector DSL is more compact than build123d's method chains and may be better suited for token-constrained LLM output. The tag system validates the attribute-based naming approach. The `Sketch` API with mode parameter (`'a'`, `'s'`, `'i'`) offers an alternative to build123d's `Mode` enum. CadQuery is worth studying immediately after build123d because it provides alternative design choices for the same problems.

**Questions for the next deeper pass:**
- What is the complete grammar of CadQuery's string selector DSL? Can it be parsed by a simple regex, or does it require pyparsing?
- How does the `Workplane.tag()` system interact with undo/redo? What happens to tags when operations are rolled back?
- How does CadQuery's constraint-based assembly solver work mathematically? Is the scipy optimization approach robust enough for complex assemblies?
- What specific limitations of CadQuery motivated the creation of build123d? What did build123d change and why?

### Rank 3: FreeCAD — study for TNP solution and parametric dependency patterns

**Why this order makes sense.** FreeCAD addresses the deepest architectural challenge ParamAItric faces: stable geometry referencing across mutations. Its TNP solution represents years of engineering effort on exactly this problem. The expression engine and property system model how parametric dependencies should propagate. However, FreeCAD's scripting API is not a good syntax reference—it's too verbose and fragile—so it ranks below the DSL-focused projects.

**Questions for the next deeper pass:**
- What is the exact algorithm FreeCAD uses to generate element names that encode creation history?
- How does the `StringHasher` map long element names to integer IDs? What is the collision handling?
- How does the expression engine detect circular dependencies in the parametric DAG?
- When the TNP system fails to resolve a reference, what recovery strategies does FreeCAD employ?
- How does FreeCAD's `FeaturePython.execute()` pattern handle errors during recomputation?

### Rank 4: SolidPython2 — study only for extension architecture pattern

**Why this order makes sense.** SolidPython2's contribution to ParamAItric is narrow but real: the extension architecture demonstrates how to keep a core minimal while layering ergonomics. The transparent transpilation model (IR → target code rendering) is also worth a brief study. But the CSG paradigm and OpenSCAD dependency make everything else irrelevant.

**Questions for the next deeper pass:**
- How does SolidPython2's extension loading mechanism work? How are extensions discovered and registered?
- What is the exact structure of an `OpenSCADObject` node? How does the tree serialization work?
- How does the BOSL2 integration bridge Python objects to OpenSCAD library calls?

### Rank 5: pythonOCC — study only for kernel literacy

**Why this order makes sense.** pythonOCC is valuable exclusively as an educational resource for understanding B-rep concepts. The `TopologyExplorer` pattern and `recognize_face()` utility demonstrate practical topology analysis that ParamAItric's Fusion add-in will need to replicate. But the raw OCCT API style is inappropriate for AI code generation, and ParamAItric targets a different kernel.

**Questions for the next deeper pass:**
- How does `TopologyExplorer.faces_from_edge()` compute adjacency? What is the equivalent Fusion API call?
- How does `recognize_face()` classify surface types? What are the mathematical tests for plane/cylinder/cone/sphere/torus?
- What OCCT algorithms does build123d's `filter_by(GeomType.CIRCLE)` use under the hood?

---

## 6. Guardrails for ParamAItric

### What ParamAItric must continue to own

- **MCP integration layer.** The security broker between LLM and Fusion 360. No external CAD library should participate in this bidirectional communication channel.
- **Fusion 360 add-in execution bridge.** The final-mile translation of IR → Fusion API calls must remain native to ParamAItric. This is where editable, timeline-rich geometry is created. Outsourcing geometry compilation to any OCCT-based library would produce "dumb solids" that destroy the product's value proposition.
- **Verification trust model and hard gates.** ParamAItric's tiered verification system (FeatureHealthState, isSolid, high-accuracy volume deltas) is already more sophisticated than any testing approach in these five projects. This is a genuine competitive advantage.
- **Recovery logic and rollback.** Timeline-native rollback via `timelineObject.rollTo(True)` must remain ParamAItric-controlled. No external library understands Fusion's timeline semantics.
- **AI-facing tool surface and prompt architecture.** System prompts, few-shot examples, and chain-of-thought structures are core IP. They should reference ParamAItric's proprietary IR, not generic build123d or CadQuery scripting patterns.
- **Semantic target tracking via Fusion Attributes.** The custom attribute injection strategy for persistent naming is ParamAItric-specific and must remain owned.
- **Editable Fusion-native output.** The product's core deliverable—a timeline-rich, parametric, human-editable Fusion model—cannot be achieved by any external geometry library.

### What should remain inspiration only for now

- **build123d's `ShapeList` selector system.** Study and reimplement the concept as Fusion B-rep evaluation functions. Do not import build123d at runtime.
- **build123d's builder context managers.** Design a ParamAItric pseudo-DSL inspired by the syntax. Do not use build123d's actual `BuildPart` class.
- **CadQuery's string selector DSL.** Consider designing a compact selector notation for the ParamAItric IR. Do not import CadQuery's parser.
- **FreeCAD's TNP element maps.** Study the algorithm for encoding creation history. Implement an analogous scheme using Fusion Attributes. Do not depend on FreeCAD.
- **FreeCAD's expression engine.** Prompt the LLM to generate Fusion 360 expressions natively. Do not build a custom expression evaluator.
- **SolidPython2's extension architecture.** Apply the principle of minimal core + layered extensions to ParamAItric's codebase organization. Do not adopt the OpenSCAD transpilation model.
- **pythonOCC's `TopologyExplorer`.** Reimplement the topology traversal patterns using Fusion's `BRepBody`, `BRepFaces`, `BRepEdges` collections. Do not depend on OCCT bindings.
- **Any OCCT-based geometry kernel for runtime.** The OCCT kernel and Fusion's ASM kernel compute boolean operations differently. Mixing them would introduce subtle geometric discrepancies that corrupt the verification trust model.
- **Any static geometry output path (STEP/STL) as primary output.** Static exports destroy parametric editability and the Fusion timeline—the entire product value proposition.

---

## 7. Sources

### build123d
- GitHub repository: https://github.com/gumyr/build123d
- Official documentation: https://build123d.readthedocs.io/en/latest/
- Key pages studied: Introduction, Key Concepts (builder mode), Topology Selection and Exploration, Assemblies, Joint Tutorial, Introductory Examples, Objects, Import/Export, Tips/Best Practices

### CadQuery
- GitHub repository: https://github.com/CadQuery/cadquery
- Official documentation: https://cadquery.readthedocs.io/
- Key pages studied: CadQuery Primer, Selectors, Assemblies, Sketch API, Free Function API, Class Reference, API Reference

### FreeCAD
- GitHub repository: https://github.com/FreeCAD/FreeCAD
- API documentation: https://freecad.github.io/API/modules.html
- Key resources studied: FreeCAD Scripting tutorials, Topological Naming Problem wiki documentation, PartDesign scripting examples, Expression engine documentation, Assembly workbench documentation

### SolidPython2
- PyPI page: https://pypi.org/project/solidpython2/
- GitHub repository: https://github.com/jeff-dh/SolidPython (branch master-2.0.0-beta-dev)
- OpenSCAD reference: https://openscad.org/

### pythonOCC
- GitHub repository: https://github.com/tpaviot/pythonocc-core
- Documentation: https://pythonocc-core.readthedocs.io/
- Key modules studied: OCC.Core (SWIG bindings), OCC.Extend.TopologyUtils, OCC.Extend.ShapeFactory

### ParamAItric internal documents
- ParamAItric Verification Trust Model (internal Google Doc)
- ParamAItric and build123d Integration Research (internal Google Doc)