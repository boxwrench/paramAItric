# Deep Research on Advanced “How-To” Patterns for AI CAD Agents Building Mechanical Assemblies

## Semantic entity targeting and the persistent naming problem

Parametric CAD systems built on boundary representations (B-Reps) routinely **split, merge, or delete faces/edges** as the model history is recomputed, which means that “Face17” or “edge index 42” is not a stable reference after edits. This long-studied class of failures is commonly described as the **persistent naming problem** (a.k.a. topological naming problem): features that reference topological entities can become ambiguous or invalid as the model evolves. citeturn10search9turn10search6turn10search14

A key architectural implication for your agent is that “topological entity abstraction” is not optional—**it is the core reliability layer**. Academic and industrial work repeatedly converges on the idea that stable referencing must be grounded in **semantics** (design intent / constraints) and **geometry- and history-aware matching**, not just opaque IDs. citeturn10search9turn10search6turn10search14

### What “stable naming” looks like in real CAD kernels and workbenches

One widely cited strategy is to store a selection not as “Face7”, but as something that can be recomputed from modeling provenance, such as “the face created by operation X that came from input edge Y”, plus enough context to rematch when topology changes. This approach appears explicitly in the documentation of entity["organization","Open CASCADE Technology","cad kernel occt"]’s OCAF framework: its **Topological Naming mechanism** is described as depending on (1) **history of the modeling operation**, (2) registering the result and necessary history data, and (3) **selection/recomputation** of the “selected sub-shape” after recompute—i.e., it is inherently a *re-identification* pipeline, not a permanent ID. citeturn0search1turn8view3

In the open-source CAD ecosystem, entity["organization","FreeCAD","open-source cad project"]’s longstanding naming instability has been discussed publicly as a major adoption barrier. entity["company","Ondsel","freecad company"] (authors entity["people","Brad Collette","ondsel cto"] and entity["people","Rebecca Dodd","ondsel writer"]) explains why the issue is “ubiquitous” in parametric CAD, why it can only be mitigated, and why solutions tend to be pervasive and risky to merge. citeturn10search7turn24view1

A concrete “how” example of a mitigation is the topological naming work by entity["people","realthunder","freecad developer"] (documented in the FreeCAD Assembly3 wiki): the algorithm generates names using **shape modeling history** provided by OCCT maker classes such as `BRepBuilderAPI_MakeShape`, relying on mappings from input elements to output or modified elements, while noting that not all modeling classes expose history uniformly. This is a practical, implementation-driven version of the “history + recomputation” concept described in kernel literature. citeturn0search4turn8view2

### What this means for your agent: “semantic handles” beat “human-readable tokens”

Your agent wants to say: *“Sketch on the face with the highest Z-value”* instead of *“Sketch on face token abc123”*. This is exactly aligned with the consensus in persistent naming research: references must be expressed in a way that can be **regenerated, validated, and disambiguated** when geometry changes. One influential CAD paper argues that repeatedly adding more naming heuristics only solves a fraction of the problem; instead, it advocates (a) referring to **persistent entities in the parametric definition domain** and (b) **ascertaining that the semantics still hold** at each evaluation step—i.e., a built-in verification loop. citeturn10search9turn10search14

#### A practical hybrid strategy that maps cleanly to CAD APIs

In practice, the most robust pattern is to store **two layers** of reference for every “important” entity:

**Layer A: Best-available persistent token (when provided by the CAD system).**  
In entity["company","Autodesk","cad software vendor"]’s Fusion API, faces can expose an `entityToken` intended to be saved and later resolved back to the “same face” using `Design.findEntityByToken`. Autodesk explicitly warns that the string itself can differ over time even for the same entity, and therefore should never be compared as a string—only resolved back to entities and compared by meaning. citeturn4search1turn8view0

**Layer B: A semantic descriptor that can re-find the entity if the token fails or becomes ambiguous.**  
A “semantic descriptor” is a structured predicate like:

- surface kind: planar / cylindrical / conical / etc.  
- orientation: “normal approximately +Up”  
- extremum: “max along +Up within ε of part bounding box max”  
- role: “top_face_of_shell_A”  
- tie-breakers: largest area among candidates, closest centroid to (x,y), adjacency to feature edge loop, etc.

This design directly implements “maintain semantics each step” from the CAD literature. citeturn10search9turn10search6turn0search1

#### How to compute semantic descriptors in Fusion-style B-Rep APIs (example mechanics)

Fusion’s API exposes stable geometric probes you can use for semantic selection. For instance, `BRepFace.pointOnFace` provides a point lying on the face. citeturn0search34  
Then, Autodesk’s own “Hole and Pocket Recognition” sample illustrates using `face.evaluator.getNormalAtPoint(face.pointOnFace)` to obtain a normal and classify faces by orientation/role, and it uses face/edge bounding boxes to compare extents. citeturn16search27turn11search15

Separately, Fusion’s API fundamentals emphasize that objects expose `isValid` to indicate whether a reference has been invalidated. citeturn5search25turn25search10  
However, in practice, “valid reference” does not guarantee “still the intended face,” so you should treat `isValid` as a **necessary but not sufficient** condition and still verify semantics (normal/extrema/area). citeturn10search9turn4search1

#### Coordinate-system robustness: “highest Z” must become “highest along Up”

A subtle but important trap for AI spatial reasoning is assuming that “Up = +Z.” Fusion’s own onboarding material tells users to set a “default modeling orientation” (example: Y up). That means the meaning of “top” depends on the document’s chosen convention and/or the assembly/component context. citeturn13search16

**Agent implication:** implement semantic targeting in terms of an explicit **Up axis** in the current design context:

- Determine/track which axis is Up for the design session (or allow a user/system setting).
- When selecting “topmost,” compute projection `dot(point, UpVector)` and pick the maximum.

This avoids “wrong-plane” sketching failures that can look like hallucinations (“I cut a hole in the top face” but actually cut a side). citeturn13search16turn16search27

## FDM tolerance library and a mechanical fit playbook for printed assemblies

There is no single ISO-like standard for “FDM clearances” that applies across printers, slicers, materials, and part orientation; reputable guides repeatedly emphasize **calibration dependence** and process variability. citeturn8view13turn8view12turn15view4  
That said, several high-quality sources converge on actionable baseline numbers and—equally important—*design hacks that avoid needing perfect tolerances*.

### Canonical clearance baselines you can safely bake into an agent

- entity["company","Prusa Research","3d printer maker"] suggests an “initial good measurement” of **≥ 0.3 mm** clearance for movable parts, and notes typical accuracy of at least **0.2 mm** while warning that materials can warp/shrink. citeturn1search23turn8view12
- entity["company","UltiMaker","3d printing company"] recommends a **0.6 mm gap** when printing components together to ensure they will move after printing (print-in-place style). citeturn3search0turn8view14
- entity["company","Stratasys","3d printing company"] provides industrial FDM assembly guidance indicating that for printers without a stated achievable accuracy, clearance of **≥ 0.51 mm (0.020")** is required between components in X/Y, and Z clearance should be at least **double the layer thickness**; it also highlights that part orientation matters and that X/Y is typically the most accurate plane. citeturn3search4turn9view0turn9view1
- entity["company","Protolabs","digital manufacturing company"] frames tolerancing as “fit, function” driven and highlights that expected tolerance depends strongly on process and requirements (a good justification for an agent to store “intent” per interface). citeturn1search3turn15view4

### Snap-fit-specific tolerances and material recommendations

The Hubs/Protolabs Network snap-fit guide is unusually explicit:

- It states there are **no universal tolerance rules** for snap-fits because of calibration/material/process variability.
- It recommends nominal clearance of **0.5 mm for FDM** snap-fit connectors.
- It recommends tougher/ductile polymers such as **ABS, PETG, nylon**, while describing brittle polymers (like PLA) as less suitable for repeated cycling. citeturn1search16turn8view13

### Interference/press fits: the “don’t rely on perfect circles” playbook

For “press fit” behavior with FDM, sources increasingly recommend *geometric tricks* that create equivalent mechanical performance without demanding unattainably tight tolerances.

entity["company","AON3D","3d printer manufacturer"] provides a particularly practical “how-to” guide:

- It argues that **transition fit** is about the tightest dimensional tolerance consistently achievable with FDM and may require extensive calibration and test coupons.
- It proposes workarounds such as:
  - Using **hexagons or squares** instead of circular holes for press-fit shafts (reduces stretching needed and mitigates cracking/delamination).
  - Adding **crush ribs** to create controlled local deformation, including numerics:
    - Transition-fit crush ribs: taper by ~**2°** and add about **0.2 mm** vertical crush ribs around the circumference.
    - Press-fit crush ribs: add **0.2 mm** vertical crush ribs along the full shaft/hole length (better for one-time assemblies). citeturn3search26turn26view0
- It ties clearance fits to extrusion width: a general rule is **1–2× extrusion width** as clearance, with an explicit example (0.75 mm for a tighter sliding fit; 1.5 mm for freer running fit on a 0.75 mm extrusion width). citeturn3search26turn15view0

### A “bake-in” tolerance table for an AI agent

The table below is intentionally framed as **starting presets** + **what to do when you need tighter than FDM can reliably hold**, consistent with the sources above.

| Interface intent (agent-level) | “Default” starting gap / feature | Notes for PLA vs PETG vs ABS | Source-grounded fallback hack when you need tighter |
|---|---|---|---|
| Clearance fit for sliding / easy assembly | Start at **≥ 0.3 mm** clearance for movable interfaces (small parts), and increase toward **0.6 mm** for print-in-place or high-reliability movement | PLA is brittle for repeated flex; PETG/ABS more forgiving in motion interfaces | If sticking occurs, step toward extrusion-width-based clearance (1–2× extrusion width) rather than “guessing mm” | citeturn8view12turn8view14turn15view0 |
| Print-in-place joints (hinges, captive sliders) | **0.6 mm** gap is a conservative print-in-place “will move” target | Material shrink/warp can make gaps close, especially on larger parts | Ensure design allows support removal / avoid trapped support; orient mating surfaces in most accurate plane available | citeturn8view14turn9view0 |
| Snap-fit connectors | **0.5 mm** nominal clearance for FDM snap-fits | Prefer PETG/ABS/nylon for cycling; PLA risk of brittle failure | Reduce stress with fillets/tapers and alignment geometry; treat clearance as a parameter to tune per printer profile | citeturn8view13 |
| “Tight fit” / transition fit | Treat as the practical tight limit; requires calibration | Highly printer- and material-dependent | Use crush ribs + ~2° taper (below) instead of demanding perfect diameters | citeturn26view0turn15view4 |
| Press-fit / interference behavior | Avoid “perfect circle press-fit” as the primary plan | PLA cracks more easily; PETG/ABS tolerate local strain better | Use hex/square holes; add **0.2 mm** vertical crush ribs; add relief cuts/splits for serviceable fit | citeturn26view0turn8view13 |
| Industrial FDM assembly baseline | If no stated accuracy, **≥ 0.51 mm** in X/Y; Z clearance ≥ **2× layer thickness** | Industrial machines still depend on orientation and layer | Use the machine’s stated achievable accuracy table if available | citeturn9view0turn9view1 |

The biggest “agent design” takeaway is to store these as **named parameters** (e.g., `clearance_move_default`, `clearance_snapfit_fdm`) rather than hard-coding, because credible sources explicitly deny universality and emphasize calibration dependence. citeturn8view13turn8view12turn26view0

## Assemblies and joints versus boolean union

Your first report focused on unioning bodies (CSG), which is appropriate for single-part printable artifacts. But for “how” in advanced assemblies, **motion and constraints** require a different mental model: keep bodies separate, model them as components, and apply joints/constraints until the mechanism is verified—then optionally union for printing.

### Why joints require “separate bodies” in assembly-first CAD workflows

Fusion assembly workflows treat “components” as the units that can be constrained and animated. Tutorials and best-practice guidance consistently distinguish “bodies as modeling artifacts” from “components as assembly artifacts,” recommending components when parts must move relative to each other. citeturn2search31turn22search18turn22search11

For motion, Fusion’s “Joint” tool positions components and defines relative motion, while “As-Built Joint” is used when components are already positioned and you want to define motion without repositioning them. citeturn22search18turn22search0turn22search17  
The very existence of these commands is a clue to agent architecture: a “CSG union” destroys separability, so it should normally be deferred until after assembly/motion validation. citeturn22search18turn22search30

### Rigid groups and rigid joints as “assembly logic primitives”

Fusion’s “Rigid Group” command locks the relative position of selected components—effectively bundling them into one rigid cluster for higher-level kinematics. citeturn2search3turn8view16  
On the API side, Fusion exposes collections like `RigidGroups` with methods such as `add`, and objects maintain `isValid` like other API objects. citeturn2search9turn8view6turn25search10

This maps cleanly to an AI agent’s planning abstraction:

- **Rigid Group** ≈ “these parts are effectively one rigid body in the mechanism graph.”
- **Revolute/Slider/etc. Joint** ≈ “introduce a DOF edge between rigid clusters.”

### Evidence that “AI-orchestrated jointed assemblies” is feasible

The research paper *CLS-CAD: Synthesizing CAD Assemblies in Fusion 360* by entity["people","Constantin Chaumet","researcher"] and entity["people","Jakob Rehof","researcher"] describes a Fusion 360 plugin intended to reduce repetitive assembly creation. It supports annotating parts with types, managing subtype hierarchies, and **synthesizing assembly programs** that can generate “arbitrary open kinematic chain structures.” citeturn2academia36turn23view1

Even if your agent does not adopt their exact approach, this result strongly supports the idea that a CAD agent should explicitly model **kinematic structure** (graph or DSL) rather than collapsing everything into boolean unions early. citeturn23view1turn22search11

### Practical recommendation for your constrained-primitive agent

For 3D-printable mechanisms (hinges, latches, detents):

- Keep each mechanical part as a separate solid (or separate “component” if available).
- Define a joint graph (rigid groups + joints).
- Use clearance parameters from the FDM playbook above.
- Only at the end:
  - export as multi-body print (if printing separately), or
  - perform boolean union for “print-in-place” assemblies (while keeping a “joints” version for validation).

This “separate-then-union” flow is the best way to get both: (1) kinematic verification and (2) CSG manufacturability. citeturn22search18turn8view14turn9view0

## Multimodal camera automation for verification

If you want your agent to be robust against silent failures, the viewport becomes a *measurement instrument*: the agent should be able to generate **repeatable orthographic images** from known view directions after every major step.

### Fusion API building blocks for deterministic screenshots

In the Fusion API, the active view is accessible via `Application.activeViewport`. citeturn18search0turn19search2  
Autodesk provides a `Viewport.saveAsImageFile` capability that renders at a specified size (not merely scaling the existing viewport), supporting deterministic image generation for downstream vision checks. citeturn16search0  
To ensure the image reflects recent edits, Fusion offers `Viewport.refresh`, described as useful to force a refresh to see API edits. citeturn16search2turn6search27

On the camera side, the API has been evolving toward better determinism:

- `Camera.viewExtents` has been **retired** and replaced by `getExtents`/`setExtents`. citeturn19search1
- `Camera.setExtents` explicitly sets orthographic extents and documents how viewport aspect ratio affects the applied width/height. This is a strong primitive for “auto-frame” that is *math-stable* rather than UI-heuristic. citeturn19search0

### A robust “auto-frame + orthographic screenshot” procedure

A practical deterministic sequence for each view (Top/Front/Right/Iso variants) is:

1. Resolve a target set of bodies/components (the ones you want visible/verified).
2. Compute an oriented or axis-aligned bounding box in the correct context (Fusion exposes component bounding boxes and an oriented minimum bounding box). citeturn12search7turn12search8
3. Set camera type to Orthographic (Fusion exposes a camera type property in the camera API). citeturn7search1turn7search2
4. Set camera eye/target/up for the desired orthographic direction, then set extents using `Camera.setExtents` based on the bounding box projection plus margin. citeturn19search0turn20search1
5. Refresh the viewport, then save a high-resolution image using `saveAsImageFile`. citeturn16search2turn16search0turn18search0

This avoids dependence on interactive UI commands like “Fit,” making it better suited to an autonomous agent.

### Known pitfalls you should design around

Fusion API behavior around camera mode switching has had quirks in the wild; for instance, there are recent community reports of limitations toggling from orthographic back to perspective in some contexts. Treat camera switching as something to test and gate (e.g., verify camera state after setting). citeturn6search4turn5search6

Separately, multiple sources emphasize that user-facing camera settings may change depending on workspace/sketch mode; an agent should re-assert camera settings just before capture rather than assuming they persist. citeturn6search22turn6search32

## Synthesis: state management patterns that make these systems reliable

The four areas above converge on one “clever” meta-pattern: **make identity, fit, kinematics, and perception all first-class state**—and require each to pass verification before the agent proceeds.

### A reference design for “semantic-first” state objects

A robust agent typically needs explicit typed records such as:

- **EntityRef**: `{token?, semantic_descriptor, last_verified_at, confidence}`
- **InterfaceSpec**: `{intent: slip|snap|press|hinge, clearance_params, material_assumptions}`
- **AssemblyGraph**: `{rigid_groups, joints, DOF limits, grounded components}`
- **ViewSpec**: `{camera_pose, projection, extents_policy, image_size}`

This is essentially the CAD literature’s “verify semantics each step,” but implemented as a modern agent state system. citeturn10search9turn0search1turn19search0

### A “forced verification loop” that directly targets silent CAD failures

A minimal yet powerful commit gate for each modeling action is:

1. **Execute** the CAD operation (extrude/cut/joint/etc.).
2. **Re-resolve semantic entities** (token → entity → semantic check; fallback to semantic search).
3. **Measure invariants**: bounding box, face normal/orientation, presence/absence of features (e.g., hole recognition-type checks). citeturn4search1turn16search27turn12search7
4. **Render deterministic views** and compare against expected visual constraints (e.g., silhouette changed, hole appears in correct location) using the camera automation workflow above. citeturn16search0turn19search0
5. If any check fails or is ambiguous, **roll back or branch** and retry with a modified strategy (different face selection predicate, larger clearance, alternative press-fit hack like crush ribs).

This gating loop is not just “nice”—it is the direct practical answer to the persistent naming literature’s warning that purely internal naming schemes cannot generically guarantee correctness, and to manufacturing guidance that tolerances are calibration-dependent. citeturn10search9turn8view13turn26view0