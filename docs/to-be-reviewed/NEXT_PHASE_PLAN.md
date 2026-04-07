# ParamAItric — Next Phase Plan

> Captured 2026-03-29. Review of current state, identified gaps, research findings,
> and phased implementation plan for intake, interface, threading, and usability.

## Current State Summary

- 25+ validated workflows across 5 families (spacers/plates, brackets, cylinders, enclosures, specialty)
- 372 passing tests, mock + live smoke runners
- Mixin-based architecture, clean four-layer stack (AI → MCP → Server → Fusion Bridge)
- Multi-tier verification (hard gates, audits, diagnostics)
- Two lanes: structured deterministic workflows + guided freeform sessions

**What's working:** Workflow execution, verification, error handling, test coverage.
**What's not working well:** Intake, discovery, user interface, and workflow reference.

---

## Problem 1: Intake Is Broken

### Current Flow (and why it fails)

1. User describes a part in natural language to an AI agent
2. AI calls `workflow_catalog` → gets a **list of names only**, no metadata
3. AI must guess which workflow fits by reading tool_specs descriptions
4. If it guesses wrong, user must restart or drop into freeform
5. No structured way to go from vague intent to specific parameters

### What's Needed

A **discovery and recommendation layer** between "I need a part" and "run this workflow with these params":

- `workflow_catalog` should return intent, expected inputs, example dimensions, and typical use cases — not just names
- A `recommend_workflow` tool that takes intent + constraints → ranked suggestions with example params
- A **reference catalog** of common real-world parts with typical dimensions (not workflows — lookup data)
  - Example: "3/4-inch EMT pipe clamp → 26.7mm ID, 4mm wall, M4 bolt holes at 20mm spacing"
  - Reference gives AI and user a sanity check and starting point
  - Real parts can deviate — reference is for ideas, not copying

### Research: Intake Patterns from Other Tools

**McMaster-Carr drill-down pattern:**
- Category → Subcategory → Specifications → Exact part selection
- Filter by technical attributes, not free text
- Small diagrams embedded in filter options showing what each dimension means
- Discrete filter checkboxes, not sliders (engineering specs are discrete)

**OpenSCAD Customizer (auto-generated UI from annotations):**
```openscad
/* [Dimensions] */
height = 50;        // [10:100]              → slider
style = "round";    // [round, square, hex]  → dropdown
hollow = true;                               → checkbox
```
- Tab grouping via `/* [Tab Name] */` comments
- Parameter sets saved as JSON, loadable via CLI

**TinkerCAD Shape Generator pattern (deprecated but relevant):**
```javascript
params = [
    { "id": "radius", "displayName": "Radius", "type": "float",
      "rangeMin": 1, "rangeMax": 50, "default": 10 },
    { "id": "hollow", "displayName": "Hollow", "type": "bool", "default": false }
]
function process(params) {
    var shape = Solid.cylinder(params.radius, params.height, params.segments);
    if (params.hollow) {
        shape = shape.subtract(Solid.cylinder(params.radius * 0.8, ...));
    }
    return shape;
}
```
- Declare parameters with metadata (type, range, default, display name)
- System auto-generates the configuration UI
- This is directly applicable — paramAItric already has dataclass schemas with validation

**FreeCAD spreadsheet approach:**
- Parameters in spreadsheet cells with aliases
- Geometry references aliases: `Spreadsheet.bolt_diameter`
- Changing value updates all linked geometry

**Synthesis for paramAItric:**
- Schema dataclasses already define type, validation, defaults → extend with display metadata
- McMaster drill-down for workflow discovery (category → key dims → generate)
- TinkerCAD/OpenSCAD pattern for auto-generated parameter forms

---

## Problem 2: No Good Interface

### Current: AI Chat Only

The only way to use paramAItric is through an AI chat interface. No structured forms,
no visual preview, no parameter editor, no way to browse what's possible.

### Recommendation: Local HTML UI at `127.0.0.1:8123/ui`

The HTTP bridge already runs at `:8123`. Serve a lightweight HTML interface from it.

| Component | Purpose |
|-----------|---------|
| **Workflow browser** | Cards showing each workflow with sketch preview and typical use case |
| **Parameter form** | Auto-generated from schema dataclasses (type, range, default, display name) |
| **2D preview** | Simple SVG showing sketch profile with dimensions (no Fusion needed) |
| **Reference panel** | Common parts with typical dimensions, selectable as starting points |
| **Generate button** | Submits to existing workflow pipeline |
| **Status/log panel** | Shows stage progress and verification results |

**Why HTML over CLI:**
- Parametric CAD needs spatial/dimensional input — sliders, number fields, dropdowns
- Workflow browsing needs visual cards, not scrolling text
- SVG preview is trivial to compute from parameters
- The HTTP server already exists

**Key design principle:** This supplements AI chat, doesn't replace it. AI can still invoke
workflows via MCP. The HTML interface gives users a way to browse, configure, and launch directly.

### Part Request Intake Form

Structured fields for the HTML interface:

```
What does this part do?     [mount / enclose / connect / adapt / clamp / support]
What does it attach to?     [flat surface / pole/tube / rail / another part / nothing]
Approximate size            [length × width × height, or diameter × length]
Material/process            [FDM / resin / CNC / laser cut]
Key constraints             [must fit M3 bolts / must clear 25mm tube / etc.]
```

Maps to workflow recommendations. User picks a workflow, adjusts params, generates.

---

## Problem 3: Threading — Interior and Exterior at Different Pitch

### Research Findings: Fusion 360 Thread API

**Good news:** Fusion 360 has a built-in `ThreadFeatures` API. No need for helical sweeps for standard threads.

**API chain:** `ThreadDataQuery` → `ThreadInfo.create` → `ThreadFeatureInput` → `ThreadFeature`

**Key details:**
- `ThreadInfo.create` is the current static method (verified Aug 2025 Autodesk Help)
- `ThreadFeatures.createThreadInfo` is **retired** (marked retired Dec 2014, do not use)
- `isInternal` boolean controls interior (True = tapped hole) vs exterior (False = bolt)
- `isTapered` boolean for NPT/BSPT pipe threads; False for standard cylindrical
- `isRightHanded` boolean — True for standard right-hand threads
- Pitch is encoded in thread designation strings (e.g., "M10x1.5" = 1.5mm pitch)
- Query `allDesignations()` to find available pitch options for a thread type/size
- Thread types available: ISO Metric, ACME, UN/UNC/UNF, NPT, BSP, and custom XML

**Correct method signature:**
```python
threadInfo = adsk.fusion.ThreadInfo.create(
    isTapered=False,                    # True for NPT/BSPT
    isInternal=True,                    # True = tapped hole; False = bolt
    threadType="ISO Metric profile",    # from allThreadTypes
    threadDesignation="M6x1",           # encodes size + pitch
    threadClass="6H",                   # tolerance class
    isRightHanded=True                  # standard
)
```

**Working code pattern:**
```python
threadFeatures = rootComp.features.threadFeatures
threadDataQuery = threadFeatures.threadDataQuery

# Query available thread specs
threadTypes = threadDataQuery.allThreadTypes          # ["ISO Metric profile", "ACME", ...]
allSizes = threadDataQuery.allSizes(threadType)       # ["M3", "M4", "M5", ...]
allDesignations = threadDataQuery.allDesignations(threadType, threadSize)  # ["M6x1", ...]
allClasses = threadDataQuery.allClasses(isInternal, threadType, threadDesignation)

# Create thread info using current static method
threadInfo = adsk.fusion.ThreadInfo.create(False, True, "ISO Metric profile", "M6x1", "6H", True)

# Apply to cylindrical face
faces = adsk.core.ObjectCollection.create()
faces.add(cylindrical_face)
threadInput = threadFeatures.createInput(faces, threadInfo)
threadInput.isFullLength = False
threadInput.threadLength = adsk.core.ValueInput.createByReal(length_cm)
threadFeatures.add(threadInput)
```

**Interior + exterior at different pitch (the stated use case):**
- Two separate `ThreadFeature` calls on the same body — works because the regions don't intersect
- Interior: `ThreadInfo.create(False, True, ...)` on the bore face (e.g., fine pitch M10x1)
- Exterior: `ThreadInfo.create(False, False, ...)` on the barrel face (e.g., coarse M10x1.5)
- Intersecting thread regions on the same face will fail — keep geometries separate

**⚠️ STL Export Gotcha (verified via community forums Dec 2023):**
Fusion's "Modeled" setting moved from the hole dialog to document-level settings in a 2023 update.
The document-level setting can silently override what the API requests, producing a smooth cylinder
with no thread geometry in the export. Must set both:
1. Document Settings → Threads → Modeled (not just cosmetic)
2. High-refinement export parameters: Deviation 0.025mm, Normal angle 5°, Min facet 0.025mm

**For complex/intersecting thread cases:** Use `TemporaryBRepManager.createHelixWire()` +
`PipeFeatures` or `SweepFeature`. Native `ThreadFeature` only for non-intersecting regions.

### Strategy: Fusion-First, Decipher Later

**Phase 1 approach:** Use Fusion's built-in `ThreadFeatures` API directly. Don't reinvent
thread geometry — Fusion already has the thread database, the profile math, and the modeled
geometry generation. Wrap it, expose it, ship it.

**Later:** Once threads work reliably through Fusion, reverse-engineer the patterns
(thread profiles, pitch math, helix geometry) so they can be reproduced in other backends
(OpenSCAD, CadQuery, direct STL generation). The Fusion implementation becomes the
reference implementation that we validate against.

### Helical Sweep (deferred — for custom/non-standard threads later)

`CoilFeatures` is read-only in Fusion API — no `createInput`/`add`. Proper workaround:
`TemporaryBRepManager.createHelixWire()` generates a true helix wire body, which can be
used as a sweep path via `PipeFeatures` or `SweepFeature`. This is more reliable than
generating math-based spline points. Still deferred — standard `ThreadFeatures` covers
most use cases first.

### Thread Reference Table (to include in reference catalog)

| Standard | Common Sizes | Pitch Range | Use Case |
|----------|-------------|-------------|----------|
| ISO Metric | M2–M20 | 0.4–2.5mm | General mechanical |
| UNC | #2–1" | 4.5–0.4mm (TPI) | US general purpose |
| UNF | #0–1.5" | Fine pitch | US precision |
| ACME | 1/4"–5" | Coarse | Lead screws, clamps |
| NPT | 1/8"–4" | Tapered | Pipe/plumbing |
| Garden Hose (GHT) | 3/4" | 11.5 TPI | Hose fittings |

---

## Phased Implementation Plan

### Phase 1 — Intake & Discovery (highest impact, lowest risk)

**Goal:** Fix the gap between "I need a part" and "run this workflow."

| Task | Description | Effort |
|------|-------------|--------|
| 1a. Enrich `workflow_catalog` | Return intent, input schema summary, example dimensions, typical use case per workflow. Data already exists in registry + schemas — surface it. | Small |
| 1b. Add `recommend_workflow` tool | Takes intent description + optional constraints → returns ranked workflow suggestions with example params. | Medium |
| 1c. Build reference catalog | `mcp_server/reference_catalog.py` — dataclass per part family with typical real-world dimensions, common hardware (M3 bolt = 3.4mm clearance hole, etc.). AI and UI both consume this. | Medium |
| 1d. Add schema display metadata | Extend schema dataclasses with `display_name`, `range_min`, `range_max`, `unit`, `group` fields. Powers both AI recommendations and HTML form generation. | Small |

### Phase 2 — HTML Interface

**Goal:** Give users a visual way to browse, configure, and launch workflows.

| Task | Description | Effort |
|------|-------------|--------|
| 2a. Serve static HTML from bridge | Add `/ui` route to `http_bridge.py` serving a single-page app. | Small |
| 2b. Workflow browser page | Cards per workflow family, filterable by category. Uses enriched catalog from 1a. | Medium |
| 2c. Auto-generated parameter form | Reads schema metadata (from 1d) → renders input fields, sliders, dropdowns. | Medium |
| 2d. SVG sketch preview | Compute 2D profile from parameters, render as inline SVG with dimension annotations. | Medium |
| 2e. Reference panel | Show common parts from reference catalog (1c), click to populate form. | Small |
| 2f. Generate + status panel | POST to workflow endpoint, show stage progress, verification results. | Medium |

### Phase 3 — Threading (Fusion-first approach)

**Goal:** Add thread generation with independent interior/exterior pitch.
**Strategy:** Wrap Fusion's built-in `ThreadFeatures` API directly. Don't generate thread
geometry ourselves — use Fusion's thread database and modeled geometry. Decipher the
underlying patterns later for multi-backend support.

| Task | Description | Effort |
|------|-------------|--------|
| 3a. Add `apply_thread` primitive | New operation in `live_ops.py` wrapping `ThreadFeatures` API. Use `ThreadInfo.create` (static). Params: face, isTapered, isInternal, isRightHanded, threadType, designation, class, length. Also set document-level Modeled setting before export. | Medium |
| 3c. Thread query tools | `list_thread_types`, `list_thread_sizes`, `list_thread_designations` — expose `ThreadDataQuery` so AI and UI can discover available thread specs. | Small |
| 3d. Thread schemas | `CreateThreadedCylinderInput`, `CreateThreadedCapInput` with interior/exterior thread params. | Small |
| 3e. `threaded_cylinder` workflow | Extrude cylinder → apply external thread. Simplest thread case. | Medium |
| 3f. `threaded_cap` workflow | Bore + external barrel → interior thread on bore + exterior thread on barrel (different pitch). Your stated use case. | Medium |
| 3g. Thread reference table | Lookup data for common standards (ISO, UNC/UNF, ACME, NPT, GHT) with pitch and diameter. | Small |
| 3h. (Later) Decipher thread geometry | Reverse-engineer Fusion's thread profiles and pitch math so they can be reproduced in other CAD backends. | Large — deferred |

### Phase 4 — New Fusion-Native Primitives

**Goal:** Expose Fusion features that are now confirmed mature and wrappable.
These are all verified as having working `createInput`/`add` patterns in the Python API.

| Feature | API Status | What It Unlocks |
|---------|-----------|-----------------|
| **Linear Pattern** | Mature (enhanced Nov 2025) | N-hole plates, bolt rows, rib arrays |
| **Circular Pattern** | Mature (enhanced Nov 2025) | Bolt circles, radial fins, fan blades |
| **Mirror** | Mature | Symmetric brackets, bilateral parts |
| **Loft** | Mature | Profile transitions, tapered enclosures, ergonomic handles |
| **Sweep with guide rails** | Mature | Custom-path extrusions, gaskets, channels |

Sheet metal excluded — flat pattern API is too fragile for automation (crashes with multiple bodies).

| Task | Description | Effort |
|------|-------------|--------|
| 4a. `apply_linear_pattern` primitive | Wrap `LinearPatternFeatures`. Directly enables N-hole plates without separate workflows. | Small |
| 4b. `apply_circular_pattern` primitive | Wrap `CircularPatternFeatures`. Bolt circles, radial arrays. | Small |
| 4c. `mirror_feature` / `mirror_body` primitive | Wrap `MirrorFeatures`. Symmetric parts in one half the steps. | Small |
| 4d. `loft_profiles` primitive | Wrap `LoftFeatures` with guide rails. Opens up transition shapes. | Medium |
| 4e. `sweep_with_rail` primitive | Wrap `SweepFeatures` with guide rail. Custom-path extrusions. | Medium |
| 4f. Refactor N-hole plate workflows | Replace separate 2-hole/4-hole workflows with one parameterized workflow using linear/circular pattern. | Small (after 4a) |

### Phase 5 — Workflow Composition & Usability

**Goal:** Reduce rigidity of current workflow system.

| Task | Description | Effort |
|------|-------------|--------|
| 5a. Insert boss generator | Counterbore geometry for M2–M6 heat-set inserts using reference catalog data. | Small |
| 5b. Auto-suggest freeform on failure | When rigid workflow fails, offer guided freeform continuation instead of full restart. | Medium |
| 5c. Workflow chaining | Schema pattern for "build on previous output" — don't always start from clean design. | Large |
| 5d. Snap-fit parameter calculator | Wall thickness → deflection → snap beam dimensions for enclosure clips. | Medium |

---

## New Feature Ideas (Backlog)

Ranked by value vs complexity:

| Feature | Value | Complexity | Notes |
|---------|-------|------------|-------|
| Insert boss generator | High | Low | Reference data ready (CNC Kitchen/Ruthex table) |
| Linear/circular pattern primitives | High | Low | Fusion API confirmed mature — Phase 4 |
| Mirror primitive | High | Low | Fusion API confirmed mature — Phase 4 |
| Loft with guide rails | Medium | Medium | Fusion API confirmed mature — Phase 4 |
| Sweep with guide rails | Medium | Medium | Fusion API confirmed mature — Phase 4 |
| Keyed shaft/hub (D-shaft, keyway) | Medium | Medium | Common coupling |
| DXF/SVG import as sketch profile | High | Medium | Custom shapes without freeform |
| Part library export (save as reusable template) | Medium | Low | JSON recipe files |
| Fit-check tool ("will A fit inside B?") | Medium | Medium | Bounding box + clearance check |
| Dovetail / finger joints | Medium | Medium | Laser cut / woodworking joints |
| Gear generator (spur, herringbone) | Cool | High | Niche, complex profiles — loft/sweep helps |
| Multi-body assembly | High | High | Explicitly out of scope currently |

---

## Research Gaps — Potential Deep Research Topics

Research conducted 2026-03-29 resolved the following — no further research needed on these:

- ✅ **Thread API method** — `ThreadInfo.create` confirmed current, `createThreadInfo` retired
- ✅ **STL export reliability** — gotcha documented (document-level setting + export params)
- ✅ **Multi-thread on same body** — non-intersecting works; intersecting needs TemporaryBRepManager
- ✅ **Fusion feature API maturity** — Linear/circular pattern, mirror, loft, sweep all confirmed mature
- ✅ **Heat-set insert dimensions** — CNC Kitchen and Ruthex tables captured, M2–M8 covered
- ✅ **Sheet metal** — excluded, flat pattern API too fragile

**Remaining open research:**

1. **TinkerCAD community shape generators** — the original JS API had a community library of
   parametric parts. Recipes (gear generators, thread profiles, enclosure templates) could
   inform the reference catalog and workflow design. API is deprecated but patterns are relevant.
2. **Fusion thread XML custom additions** — if we ever need non-standard thread profiles,
   understand the XML schema rules and the ThreadKeeper add-in for persistence across updates.

---

## Relationship to Existing Docs

- **DEVELOPMENT_PLAN.md** — remains the high-level roadmap and status doc. Update its
  "Current priorities" section to reference this plan once implementation begins.
- **AI_CAD_PLAYBOOK.md** — update its "Deferred capabilities" section when threading lands.
- **BEST_PRACTICES.md** — add intake/discovery guidance once Phase 1 ships.
- **docs/dev-log.md** — log implementation sessions as they happen.
