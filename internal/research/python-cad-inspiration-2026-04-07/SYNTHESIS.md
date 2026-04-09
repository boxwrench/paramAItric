# Python CAD Inspiration Intake Synthesis

Date: 2026-04-07
Status: reviewed intake bundle, trimmed to high-value references

## Purpose

This memo consolidates the useful conclusions from the Python CAD inspiration intake that landed in this folder.

The goal is not to preserve every report variant. The goal is to preserve:

- the most actionable conclusions
- the parts of the research that materially help ParamAItric now
- the guardrails that keep ParamAItric as the controlled application

This memo is the working summary for the bundle. The remaining source files in this folder are retained only where they add substantial architectural value beyond what is captured here.

## Retained source notes

These are the source notes worth keeping after review:

- [Python CAD projects.md](./Python%20CAD%20projects.md)
  Why it stays:
  It is the strongest cross-project comparison in the bundle. It gives the clearest first-pass ranking across build123d, CadQuery, FreeCAD, SolidPython2, and pythonOCC, and it consistently argues from ParamAItric's actual needs instead of drifting into generic tool praise.

- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md)
  Why it stays:
  It is the cleanest build123d-focused memo for direct design borrowing. It contains the best concrete list of patterns that can be ported without runtime dependency: selector wrappers, mode enums, location generators, part recipe structure, change detection, and geometric assertion patterns.

- [Architectural of build123d.md](./Architectural%20of%20build123d.md)
  Why it stays:
  It is the most repo-grounded note. It maps the build123d-inspired ideas onto ParamAItric's actual workflow and verification architecture, and it introduces the strongest practical near-term idea in the bundle: selection tracing as a first-class internal diagnostic.

## Removed as redundant or low-value

These files were reviewed but are not needed as retained research assets:

- `Pasted text.txt`
  It is the research prompt, not research output.

- `Python CAD Projects First-Pass Review for ParamAItric.docx`
  It is a formatted export of the same research lane, not unique content.

- `deep-research-report.md`
  It is a meta-review of the prompt/spec, not direct architectural input for ParamAItric.

- `deep-research-report (1).md`
  Same problem as above. Useful for improving future prompts, but not needed as a standing reference note in this bundle.

- `Python CAD Project Inspiration Review.md`
  It contains useful material, but its strongest conclusions are already covered more clearly by `Python CAD projects.md` and the retained build123d-focused memos.

- `ParamAItric and build123d Integration Research.md`
  It contains some useful observations, but it is more repetitive than the retained build123d notes and shows weaker sourcing discipline in places. Its practical conclusions are preserved below.

## High-level synthesis

The bundle is highly consistent on the main strategic point:

- ParamAItric should stay the controlled application.
- Mature Python CAD projects should be mined for modeling abstractions and workflow patterns.
- No external Python CAD project should become a runtime dependency at this stage.

The bundle is also consistent on where the best inspiration is concentrated:

- `build123d` is the strongest immediate design reference.
- `CadQuery` is the next most useful source, especially for selector syntax and tagged state.
- `FreeCAD` matters less as an API style reference and more as a source of lessons about topology identity, parametric dependencies, and recompute behavior.
- `SolidPython2` and `pythonOCC` are much narrower inputs.

The most important overall conclusion is this:

ParamAItric does not need more low-level geometry ambition right now as much as it needs better internal abstractions for selecting, naming, composing, and verifying geometry inside the system it already owns.

That is the common thread across the strongest research notes.

## Weighted actionable conclusions

The weights below are relative implementation priority scores for ParamAItric, on a 10-point scale.

### 1. Build a semantic selector layer inside ParamAItric

Weight: 10.0

Conclusion:
ParamAItric should add a first-class internal selector abstraction for faces, edges, bodies, and vertices, using geometric queries such as topmost, longest, circular, planar, parallel-to-axis, grouped-by-area, and similar deterministic filters.

Why this ranks first:

- This is the most repeated and strongest conclusion across the retained notes.
- It directly attacks one of the hardest practical CAD reliability problems: fragile geometry references after model mutation.
- It matches how an AI naturally reasons about geometry. The AI thinks in semantic terms like "top face" or "outer cylindrical face," not in brittle index references.
- It fits ParamAItric's current architecture because the system already has tokenized entities, inspection tools, and verified staged workflows. What is missing is a richer selection language layered over that machinery.

What this should mean in ParamAItric:

- Create a `FusionShapeList`-style wrapper or equivalent internal abstraction around live Fusion topology.
- Support deterministic methods like `filter_by`, `sort_by`, `group_by`, and policy-based selectors.
- Keep entity tokens and current verification rules as the source of runtime truth. The selector layer should improve targeting, not replace verification.

Why the conclusion is well-supported:

- [Python CAD projects.md](./Python%20CAD%20projects.md) treats semantic topology selectors as the single highest-value idea across the entire candidate set.
- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md) explicitly identifies the `ShapeList` selector pattern as the highest-value idea to port now.
- [Architectural of build123d.md](./Architectural%20of%20build123d.md) argues that ParamAItric should borrow build123d's selection algebra while keeping its token-and-verification runtime model.

Recommended scope:

- Start with face and edge selectors only.
- Focus on selectors already implied by current operations: top face, outer edges, interior edges, circular edges, planar faces, vertical edges, largest face, newest edges where feasible.

### 2. Add selection tracing and explainable selection diagnostics

Weight: 9.5

Conclusion:
Every operation that selects geometry should be able to emit a structured trace describing what it selected, why it selected it, and what geometric facts supported that choice.

Why this ranks second:

- The selector layer is much more valuable if it is inspectable.
- ParamAItric's product promise is not just geometry creation. It is controlled, debuggable, recoverable geometry creation.
- Selection trace data would improve failure diagnosis, freeform recovery, verification reporting, and promotion of new workflow logic.

What this should mean in ParamAItric:

- Create an internal `SelectionTrace` object or equivalent payload.
- Include selected tokens, selector policy name, derived geometric descriptors, and the operation that consumed the result.
- Surface this data in structured failure context and optional audit logs.

Why the conclusion is well-supported:

- [Architectural of build123d.md](./Architectural%20of%20build123d.md) is the clearest source for this idea and frames it as the safest near-term way to adopt external modeling lessons.
- [Python CAD projects.md](./Python%20CAD%20projects.md) repeatedly emphasizes that selectors only become robust when they are coupled to stable reasoning and runtime-safe verification.
- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md) supports this indirectly through snapshot-based change detection and geometry-assertion patterns.

Recommended scope:

- Start with `apply_fillet`, `apply_chamfer`, semantic face finding, and any cut/extrude helper that chooses a face or edge set by policy.

### 3. Make boolean intent explicit with a shared mode enum

Weight: 8.8

Conclusion:
ParamAItric should standardize boolean intent through an internal enum or equivalent shared vocabulary such as add, subtract, intersect, replace, and private/new-body.

Why this ranks high:

- It is conceptually simple.
- It reduces an entire class of AI mistakes where geometry creation and boolean combination are treated as separate uncertain decisions.
- It aligns with how high-level CAD libraries successfully compress modeling intent.

What this should mean in ParamAItric:

- Define a canonical boolean mode vocabulary used across workflow internals and, where appropriate, AI-facing tool parameters.
- Map it consistently to Fusion operations such as join, cut, intersect, and new body.

Why the conclusion is well-supported:

- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md) identifies the mode-enum pattern as a trivial-to-port, high-value idea.
- [Python CAD projects.md](./Python%20CAD%20projects.md) ranks builder modes and boolean intent compression among the strongest practical borrowings from build123d-like systems.
- [Architectural of build123d.md](./Architectural%20of%20build123d.md) reinforces that ParamAItric needs better workflow composition ergonomics, not a new kernel.

Recommended scope:

- Introduce the enum internally first.
- Do not rush to expose every mode to end users until internal workflow usage is consistent.

### 4. Formalize dimensional workflow discipline

Weight: 8.5

Conclusion:
ParamAItric should codify and enforce the discipline of moving from lower dimension to higher dimension, and it should make "fillets/chamfers last" an explicit workflow rule rather than a soft habit.

Why this matters:

- It reduces invalid geometry and premature topology disruption.
- It is a low-cost reliability gain because it is mostly a workflow and validation rule, not a heavy implementation project.
- It gives the AI a stronger modeling grammar for safe sequence generation.

What this should mean in ParamAItric:

- Reinforce `1D -> 2D -> 3D` progression in workflow authoring rules and future freeform guidance.
- Treat edge treatments as end-of-sequence operations unless there is a specific approved exception.

Why the conclusion is well-supported:

- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md) calls this out directly as dimensional hierarchy discipline.
- [Python CAD projects.md](./Python%20CAD%20projects.md) consistently favors explicit design-intent progression over ad hoc mixed-dimension edits.
- [Architectural of build123d.md](./Architectural%20of%20build123d.md) supports staged, deterministic workflow construction as the right borrowable idea from mature CAD-as-code systems.

Recommended scope:

- Capture this as a formal workflow-authoring rule in internal design docs and future validation checks.

### 5. Introduce reusable part-recipe structure

Weight: 8.2

Conclusion:
ParamAItric should define a cleaner internal pattern for reusable parameterized part recipes, with named inputs, consistent defaults, and a stable execution shape.

Why this matters:

- ParamAItric is building repeatable part families. A stronger recipe structure reduces duplication and makes future AI-generated part definitions more coherent.
- This is more important than chasing many new primitives.
- It supports both structured workflows now and broader internal abstraction later.

What this should mean in ParamAItric:

- Treat reusable part families as first-class internal recipe objects or equivalent structured definitions.
- Keep inputs explicit and map them cleanly to Fusion parameters, workflow stages, and verification outputs.

Why the conclusion is well-supported:

- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md) highlights reusable parametric part base classes as one of the cleanest ideas to borrow.
- [Python CAD projects.md](./Python%20CAD%20projects.md) ranks parameterized part recipes via class inheritance among the top ideas worth porting.
- [Architectural of build123d.md](./Architectural%20of%20build123d.md) supports this indirectly through its emphasis on deterministic feature construction and explainable workflow staging.

Recommended scope:

- Apply first to existing high-repeat families like plates, brackets, cylinders, and enclosures.

### 6. Add location generators and explicit placement helpers

Weight: 7.9

Conclusion:
ParamAItric should add a small set of explicit placement helpers for repeated geometry and pattern placement, such as grid, polar, and linear placements.

Why this matters:

- It compresses common mechanical layout logic.
- It improves AI reliability by replacing repeated manual coordinate reasoning with named placement patterns.
- It is high value for practical parts and comparatively low complexity.

What this should mean in ParamAItric:

- Add internal placement utilities or workflow helpers for common distributions of holes, bosses, cutouts, and mounting features.
- Keep the first version narrow and deterministic.

Why the conclusion is well-supported:

- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md) identifies location generators as an immediate borrowable pattern.
- [Python CAD projects.md](./Python%20CAD%20projects.md) repeatedly favors geometry composition helpers that reduce prompt and code complexity.

Recommended scope:

- Start with rectangular arrays and simple polar arrays.

### 7. Strengthen stable state references with bookmarks and tags

Weight: 7.6

Conclusion:
ParamAItric should strengthen its persistent reference strategy with named intermediate states or bookmarks, not just post-hoc entity lookup.

Why this matters:

- It reduces the need to repeatedly rediscover geometry after each mutation.
- It makes long workflow sequences easier to reason about and easier to debug.
- It complements, rather than replaces, semantic selectors and token persistence.

What this should mean in ParamAItric:

- Allow internal workflow stages to intentionally mark useful states, sketches, faces, or contexts for later reuse.
- Use this selectively. Not every step needs a bookmark.

Why the conclusion is well-supported:

- [Python CAD projects.md](./Python%20CAD%20projects.md) points to CadQuery-style tags and workplane bookmarks as a strong design pattern.
- [Architectural of build123d.md](./Architectural%20of%20build123d.md) reinforces that better deterministic selection and workflow state handling are more valuable than deeper backend experimentation right now.

Recommended scope:

- Use bookmarks first for complex multistep workflows where the same reference context is revisited.

### 8. Generate linked parameter expressions instead of isolated numbers where appropriate

Weight: 7.2

Conclusion:
ParamAItric should prefer parameter relationships where the design intent is relational, not just literal.

Why this matters:

- It improves editability of the resulting Fusion model.
- It produces more genuinely parametric output instead of a pile of independent dimensions.
- It aligns with ParamAItric's product goal better than adding a new modeling backend would.

What this should mean in ParamAItric:

- Where appropriate, define dimensions in terms of named parameters or expressions rather than duplicating raw values.
- Use this deliberately in reusable part families, not indiscriminately everywhere.

Why the conclusion is well-supported:

- [Python CAD projects.md](./Python%20CAD%20projects.md) specifically calls out expression-linked parametric dependencies as worth studying from FreeCAD.
- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md) supports explicit units and parameter structure as part of clearer internal geometry logic.

Recommended scope:

- Start with width/height/offset relationships in structured workflows rather than freeform sessions.

### 9. Plan for operation-aware change detection, but do it after selector basics

Weight: 6.8

Conclusion:
ParamAItric should eventually support "what changed in the last operation?" reasoning, but only after basic selector semantics and selection tracing are in place.

Why this matters:

- It is powerful for follow-up operations like fillets and chamfers on newly created edges.
- It is also technically trickier and more expensive than the higher-priority items above.

What this should mean in ParamAItric:

- Capture before/after topology snapshots for targeted operations.
- Use them to identify newly created or affected entities only when the result is deterministic enough to trust.

Why the conclusion is well-supported:

- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md) explicitly calls this snapshot-based change detection.
- [Python CAD projects.md](./Python%20CAD%20projects.md) treats operation-aware edge tracking as valuable but harder to port.
- [Architectural of build123d.md](./Architectural%20of%20build123d.md) correctly pushes toward explainable selection first, which is why this item ranks below the selector and trace work.

Recommended scope:

- Prototype on a narrow set of boolean and edge-treatment operations only.

### 10. Treat assembly and joint vocabulary as a later-phase borrow

Weight: 5.9

Conclusion:
Assembly and joint abstractions are promising, but they are not the highest-leverage near-term move for ParamAItric.

Why it ranks lower:

- It is useful.
- It is not where the current architecture is under the most pressure.
- ParamAItric will get more near-term value from better selection, parameter structure, and workflow composition than from early joint abstraction.

What this should mean in ParamAItric:

- Keep it on the roadmap.
- Do not prioritize it ahead of selector, tracing, and recipe cleanup.

Why the conclusion is well-supported:

- [Python CAD projects.md](./Python%20CAD%20projects.md) acknowledges joints and assemblies as useful but not the very first thing to port.
- [design reference for ParamAItric.md](./design%20reference%20for%20ParamAItric.md) marks joint-driven assembly patterns as later, not now.
- [Architectural of build123d.md](./Architectural%20of%20build123d.md) is even more conservative and focuses near-term effort on selection determinism.

## Strong guardrail conclusions

These are not implementation tasks, but they are stable conclusions that should constrain the work.

### A. Do not add an external runtime geometry dependency right now

Conclusion:
Do not make an external Python CAD framework part of ParamAItric's production execution path at this stage.

Why:

- It weakens control.
- It adds kernel mismatch risk.
- It distracts from the more urgent problem, which is strengthening ParamAItric's own internal modeling abstractions and verification clarity.

Support:

- All three retained source notes converge on this conclusion.

### B. Do not confuse richer geometry capability with better product direction

Conclusion:
ParamAItric does not primarily need a broader primitive catalog right now. It needs clearer and more reliable abstractions for turning intent into safe, editable, explainable geometry.

Why:

- The current product goal is not "be a full Python CAD library."
- The current goal is "be a reliable human-intent to Fusion workflow system."

Support:

- [Python CAD projects.md](./Python%20CAD%20projects.md) and [Architectural of build123d.md](./Architectural%20of%20build123d.md) are especially aligned on this.

### C. Borrow architecture patterns, not project boundaries

Conclusion:
Borrow selectors, recipe patterns, placement helpers, testing ideas, and workflow composition patterns. Do not borrow another project's mission or let another project's abstractions prematurely dictate ParamAItric's internal structure.

Why:

- This keeps the repo under control.
- It preserves the product boundary around MCP, Fusion execution, verification, and recoverability.

Support:

- This is the most stable strategic conclusion across the retained notes.

## Recommended implementation order

If this research is converted into real work, the best order is:

1. semantic selector layer
2. selection tracing
3. boolean mode normalization
4. workflow discipline codification
5. reusable part-recipe cleanup
6. location generators
7. bookmark/tag state references
8. expression-linked parameters
9. operation-aware change detection
10. assembly/joint vocabulary

## Why this bundle was worth keeping

The bundle did not produce a strong case for immediate integration with any external project.

It did produce a strong case for improving ParamAItric in specific, concrete ways:

- make geometry references more semantic
- make selection decisions more inspectable
- make workflow composition more explicit
- make reusable part definitions cleaner
- make common placement and boolean intent easier for the AI to express correctly

That is enough to materially influence the next internal design pass.
