# ParamAItric Dev Log

Note: older entries may reference documents that now live under `docs/archive/`. Treat archived paths as historical context, not current guidance.

## 2026-07-02

### Live Fusion selector validation and oriented face-normal fix

Closed the Phase 1 live B-Rep validation gap on Fusion 2703.1.20 at checkout `a2fb12c`
(with the working-tree fix described below).

What live validation found and fixed:

- The bridge initially returned `mode: mock` because the add-in was started without an active
  Fusion Design. Opening a design and reloading the add-in restored `mode: live`.
- The first live selector run exposed a real adapter defect: opposite planar cap faces shared the
  underlying Plane's `+z` normal. Top selection was ambiguous with two candidates and bottom
  selection was empty.
- `FusionApiAdapter.get_body_faces` now reads the oriented B-Rep normal from
  `face.evaluator.getNormalAtPoint(face.pointOnFace)`, with an `isParamReversed` fallback.
- Added focused evaluator and fallback regression tests.
- Added development module refresh in `FusionAIBridge.py`; Fusion Stop -> Run now clears cached
  ParamAItric submodules, so code changes no longer require closing Fusion.

Representative post-fix selector evidence (entity tokens omitted):

```json
{
  "top": {"kind": "normal_axis", "axis": "+z", "status": "resolved", "candidate_count": 1, "resolved_count": 1},
  "bottom": {"kind": "normal_axis", "axis": "-z", "status": "resolved", "candidate_count": 1, "resolved_count": 1},
  "right": {"kind": "normal_axis", "axis": "+x", "status": "resolved", "candidate_count": 1, "resolved_count": 1}
}
```

Representative operation evidence:

```json
{
  "shell": {"applied": true, "kind": "normal_axis", "status": "resolved", "resolved_count": 1},
  "fillet": {"applied": true, "edge_count": 1, "kind": "geometry_type", "candidate_count": 18, "resolved_count": 18},
  "chamfer": {"applied": true, "edge_count": 1, "kind": "geometry_type", "candidate_count": 18, "resolved_count": 18}
}
```

Validation:

- `python scripts/fusion_smoke_test.py --workflow cylinder` -> passed; STL written.
- `python scripts/fusion_smoke_test.py --workflow tube` -> passed; STL written.
- Direct live selectors for top, bottom, and right -> all resolved exactly one face.
- Direct live shell, fillet, and chamfer -> all mutations succeeded and returned traces.
- `python -m pytest tests/test_fusion_api_adapter.py tests/test_selectors.py tests/test_find_face.py tests/test_addin_workflows.py -q`
  -> `89 passed`.
- `python -m pytest tests/test_fusion_api_adapter.py tests/test_addin_workflows.py tests/test_dispatcher.py -q`
  -> `70 passed`.

Remaining evidence gap:

- Discovery UX checks remain open; they are not part of the now-closed live selector/operation
  adapter validation.
- Fillet and chamfer traces prove the next roadmap priority: each mutation selected one edge while
  the diagnostic selector reported all 18 linear edges.

### Phase 1 continuation: richer edge diagnostics

Used the live evidence above to replace the all-linear-edge diagnostic boundary.

What changed:

- Added `axis_parallel`, a deterministic edge selector based on endpoint direction and a Cartesian
  axis. Fillet and interior-bracket chamfer traces derive the axis from the body's sketch plane.
- Added `max_face_perimeter`, a shallow body-relative selector that finds linear perimeter edges on
  the maximum face for an axis. Top-outer chamfer traces use this selector.
- Kept these as diagnostic selectors; mutation behavior remains in the existing Fusion adapter.

Validation:

- Focused suite: `100 passed` across selector, fillet, chamfer, add-in workflow, and Fusion adapter
  tests.
- Full suite: `531 passed, 7 failed`; failures are existing staged workflow gaps
  (`NotImplementedError` enclosure/flex wrappers and valve-handle cross-plane combine), not selector
  regressions.
- Live fillet: mutation applied to 1 edge; `axis_parallel` narrowed the trace from 18 to 6 edges.
- Live interior chamfer: mutation applied to 1 edge; `axis_parallel` narrowed the trace from 18 to
  6 edges.
- Live top-outer chamfer: mutation applied to 4 edges; `max_face_perimeter` resolved exactly 4
  edges.

Next Phase 1 item: attribute pinning with explicit stale/invalid handling.

## 2026-06-18

### Install UX polish and MCP tool-surface cleanup

Polished the setup helper and fixed a stale MCP entrypoint test that exposed a missing server
workflow wrapper.

What changed:

- Added `--check`, `--doctor`, `--no-color`, and optional `--write-claude-config` support to
  `scripts/install_paramaitric.py`.
- `--write-claude-config` merges only the `mcpServers.paramaitric` entry and preserves other
  Claude Desktop config keys/servers.
- Replaced the brittle MCP tool-count assertion with category-consistency checks.
- Added the missing `create_slotted_flex_panel` server wrapper and staged plate workflow so the
  MCP tool spec resolves to a callable method and the existing flex-panel regression passes.

Validation:

- `python3 -m pytest tests/test_slotted_flex_panel.py tests/test_mcp_entrypoint.py tests/test_install_paramaitric.py -q`
- Result: `12 passed`
- `python3 scripts/install_paramaitric.py --check --no-color`
- Result: setup summary printed successfully; virtualenv warning is expected in this checkout.

### Install UX: setup helper CLI

Added a dependency-free setup helper for first-run install UX.

What changed:

- Added `scripts/install_paramaitric.py`, a small terminal dashboard that checks Python, repo
  root, Fusion add-in folder, virtualenv presence, and MCP command resolution.
- The helper prints exact Claude Desktop JSON and Cursor command snippets for the current checkout
  instead of asking users to manually rewrite placeholder paths.
- Updated `INSTALL.md`, `README.md`, and `scripts/README.md` to route users through the helper.
- Added focused tests for config generation, platform-specific virtualenv paths, and dashboard
  output.

Validation:

- `python3 -m pytest tests/test_install_paramaitric.py -q`
- Result: `4 passed`
- `python3 scripts/install_paramaitric.py`
- Result: printed the setup dashboard and MCP config snippets successfully.

Note: `python3 -m pytest tests/test_install_paramaitric.py tests/test_mcp_entrypoint.py -q`
currently exposes an unrelated stale assertion in `tests/test_mcp_entrypoint.py`: the test expects
49 tools, while the current tool surface exposes 51.

### Documentation cleanup: stale planning state cleared

Cleared stale active-doc guidance after the selector/operation-diagnostic slice landed.

What changed:

- Updated `docs/NEXT_PHASE_PLAN.md` from the old 2026-04-08 roadmap timestamp to the current
  Phase 1 continuation plan.
- Split Phase 1 into a completed selector/trace slice and an active continuation slice:
  live Fusion validation, richer edge-loop/relational selectors, attribute pinning, stable
  reference policy, and narrow operation vocabulary.
- Marked `docs/superpowers/plans/2026-06-13-selector-foundations-phase1.md` as historical
  implementation provenance so its unchecked boxes are not mistaken for current work.
- Updated `docs/FUSION_VALIDATION_NEXT_STEPS.md` to include shell, fillet, and chamfer trace
  validation.
- Refreshed `README.md`, `docs/README.md`, `docs/AI_CONTEXT.md`, and
  `docs/NEXT_RESEARCH_PLAN.md` to point future sessions at the active roadmap and validation
  checklist.

### Phase 1 continuation: operation-level selection diagnostics

Continued the geometry-foundations roadmap instead of expanding workflow surface area.

What changed:

- Added additive `selection_trace` diagnostics to `apply_fillet`, `apply_chamfer`, and `apply_shell` results in both mock and live operation paths.
- Kept the selector vocabulary unchanged: shell traces use `face normal_axis +z`; fillet/chamfer traces use the current `edge geometry_type=linear` pool as a diagnostic boundary.
- Preserved mutation behavior and existing result fields; traces are diagnostic artifacts, not verification gates.
- Updated focused operation and live-registry tests to pin the returned trace shape.

Validation:

- `python3 -m pytest tests/test_fillet.py tests/test_chamfer.py tests/test_addin_workflows.py -q`
- Result: `50 passed`
- `python3 -m pytest tests/test_selectors.py tests/test_find_face.py tests/test_fillet.py tests/test_chamfer.py tests/test_addin_workflows.py -q`
- Result: `79 passed`

Remaining Phase 1 work:

- Live Fusion smoke validation still needs a running Fusion session.
- Fillet/chamfer edge traces are still coarse until the selector vocabulary grows edge-loop or relational selectors.
- Attribute pinning, reference-stability policy, and narrow operation vocabulary are still open.

## 2026-04-08

### Strategy reset: internal geometry foundations become the lead track

This session turned the recent research into an explicit change of direction for the repo.

The important outcome is not just "more research was reviewed." The important outcome is that the repo now has a clearer answer to what should happen next and why.

#### What changed

- Reframed the canonical roadmap around **internal geometry foundations first**
- Updated the core planning/context docs so they all tell the same story:
  - `docs/NEXT_PHASE_PLAN.md`
  - `docs/AI_CONTEXT.md`
  - `docs/RESEARCH_TRACKS.md`
  - `docs/AI_CAD_PLAYBOOK.md`
- Reviewed and synthesized two new internal research bundles:
  - Python CAD inspiration
  - selector foundations / selection tracing
- Added internal synthesis memos that preserve the strongest conclusions while trimming duplicate draft reports

#### Why the roadmap changed

The earlier roadmap was correctly identifying real problems:

- workflow discovery is weak
- there is no good local UI
- capability gaps still exist

But the newer research made a stronger architectural point:

- ParamAItric already has enough workflow and verification shape to benefit more from better geometry semantics than from more surface area.
- If selector determinism and reference stability are weak, adding more UI, more workflows, or more primitives mostly expands the reach of the same underlying reliability problem.
- If geometry targeting becomes more semantic, explainable, and stable first, then later work on intake, UI, threads, patterning, and richer workflows becomes easier to build and easier to trust.

This is now the main planning rationale for the repo.

#### Immediate task direction

The next implementation work should be judged against this sequence:

1. **Small deterministic selector vocabulary**
   - because ParamAItric needs a stable way to target faces and edges by meaning instead of implicit construction order or brittle heuristics
2. **Add-in-side selector resolution**
   - because live B-Rep topology only exists in Fusion, not in the MCP layer
3. **Explicit cardinality guards**
   - because the most dangerous selector failure is silently selecting the wrong thing when exactly one result was expected
4. **Minimal `SelectionTrace` diagnostics**
   - because selector behavior must be explainable before the system can be hardened confidently
5. **Instrumentation of current opaque selection points**
   - `find_face`, `apply_shell`, `apply_fillet`, `apply_chamfer`, and freeform mutation selection boundaries
   - because these are the current selection sites where wrong targeting can still hide inside otherwise "successful" operations
6. **Attribute pinning with validity checks**
   - because short-horizon references are useful, but they must be treated as fragile after topology changes

#### Why these tasks matter for future development

These are not isolated cleanup tasks. They are enabling tasks.

- Better selectors make later workflow recommendations more trustworthy because "recommended workflow" is less useful if geometry targeting inside the workflow is still opaque.
- Better selection diagnostics make the future UI more useful because the UI can surface real geometric reasoning instead of only generic success/failure status.
- Stronger reference handling is a prerequisite for richer topology-changing capabilities like patterning, lofts, sweeps, and threads.
- Cleaner selector and operation semantics are a prerequisite for reusable part-recipe structure, parameter relationships, and future internal abstraction work.
- Freeform can only expand safely once geometry targeting and failure explanation are stronger.

#### Guardrails reinforced by this session

- ParamAItric remains the controlled application.
- External Python CAD systems are design inspiration, not runtime dependencies.
- The selector system should stay small and deterministic in v1.
- `SelectionTrace` should stay a diagnostic artifact, not a second verification framework.
- This phase should optimize for reliability and explainability before broader capability growth.

#### New source material retained

- `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`
- `internal/research/selector-foundations-2026-04-08/SYNTHESIS.md`

These now serve as the internal research summaries for the roadmap reset.

## 2026-04-07

### Docs and research staging cleanup

Reorganized the repo documentation boundary after a temporary sync pass had moved canonical docs into a staging folder under `docs/`.

**What changed:**

- Restored canonical docs to `docs/`: `AI_CAD_PLAYBOOK.md`, `AI_CONTEXT.md`, `NEXT_PHASE_PLAN.md`, `POLE_MOUNT_DEMO.md`, `dev-log.md`, and `session-handoff-2026-03-29.md`
- Moved raw research source material into `internal/research/`
- Removed the temporary `docs/to-be-reviewed/` intake folder
- Removed the stray staged `.mcp.json` from docs
- Added `docs/RESEARCH_TRACKS.md` to track the major research lanes without turning `docs/` into a raw research archive
- Updated README canonical-doc links to include the research tracker and next-phase plan

**Boundary going forward:**

- `docs/` = canonical, reviewed repo-facing documents
- `internal/research/` = staged research source material awaiting review or synthesis

**Notes:**

- `AI_CONTEXT.md` had one broken reference to a non-existent `docs/utility-parts-concept.md`; this was replaced with a pointer to `README.md`
- stale references to the old raw research path were updated to `internal/research/`

---

## 2026-03-29

### Planning session — comprehensive review, research, and NEXT_PHASE_PLAN

No code changes this session. Planning and research pass.

**Review scope:** Full repo exploration covering architecture, intake gaps, interface options,
threading feasibility, and available Fusion API surface.

**Research conducted:** Three consolidated reports on Fusion 360 Thread API, Fusion feature
API maturity, TinkerCAD shape generator patterns, and heat-set insert dimensions.
Research document: `internal/research/Comprehensive_Parametric_Design_Research_Consolidated.md`

**Key findings:**

1. **Thread API:** `ThreadInfo.create` (static) is the current method. `ThreadFeatures.createThreadInfo`
   is retired (marked retired Dec 2014). Different signature — takes `isTapered` and `isRightHanded`.
   STL export of modeled threads has a known gotcha: Fusion's document-level "Modeled" setting
   (moved from hole dialog in 2023) can silently override API-level settings. Must set both.

2. **Interior + exterior threads at different pitch:** Confirmed feasible — two separate
   `ThreadFeature` calls on the same body work when the thread regions don't intersect
   (e.g., bore face vs barrel face on a cap).

3. **Fusion feature API maturity:** Linear pattern, circular pattern, mirror, loft with guide
   rails, and sweep with guide rails are all confirmed mature with working `createInput`/`add`
   as of Nov 2025. These can be wrapped directly. Sheet metal flat pattern excluded — too fragile.

4. **Heat-set inserts:** CNC Kitchen and Ruthex dimensions are identical for M3–M6. Only M2
   differs (Ruthex 33% longer). Full reference table captured.

**New document created:** `docs/NEXT_PHASE_PLAN.md` — phased plan covering intake/discovery
improvements, HTML interface, threading (Phase 3), new Fusion-native primitives (Phase 4),
and workflow composition (Phase 5). Replaces the scattered roadmap notes in DEVELOPMENT_PLAN.md.

---

## 2026-03-27

### Fixed tube_mounting_plate verification - floating-point tolerance

**Issue:** The `create_tube_mounting_plate` workflow was failing verification with valid geometries due to exact equality checks on floating-point dimensions. When Fusion creates a 3.175 cm cylinder, floating-point arithmetic may produce 3.1749999... or 3.1750001..., causing strict equality comparisons to fail incorrectly.

**Fix:** Replaced exact equality check with tolerance-based comparison (0.01 cm = 0.1mm tolerance) in `_create_tube_mounting_plate_workflow()` at line 1664 of `mcp_server/workflows/cylinders.py`.

**Before:**
```python
if tube_actual_dimensions != tube_expected_dimensions:
    raise WorkflowFailure(...)
```

**After:**
```python
tolerance_cm = 0.01
dimensions_match = all(
    abs(tube_actual_dimensions[key] - tube_expected_dimensions[key]) < tolerance_cm
    for key in tube_expected_dimensions.keys()
)
if not dimensions_match:
    raise WorkflowFailure(...)
```

**Testing:** Validated with pole mount spec (4" × 3" plate, 0.75" ID socket, 1.5" tall) — workflow now passes verification successfully.

**Impact:** Improves robustness of tube_mounting_plate and any other workflows using exact floating-point dimension checks.

---

## 2026-03-14

### Major server.py refactoring - Mixin architecture

Refactored `mcp_server/server.py` from a 9,539-line monolith into a modular mixin architecture. This addresses long-standing maintainability issues and establishes a pattern for future workflow development.

#### Motivation

- `server.py` had grown to 131 methods across 9,500+ lines
- Merge conflicts were frequent when adding new workflows
- Code review was overwhelming due to file size
- No clear separation between infrastructure, primitives, and workflow families

#### New Architecture

Created `mcp_server/` subdirectories:

```
sessions/          # FreeformSessionManager - guided AI modeling mode
primitives/        # PrimitiveMixin - CAD primitives (create_sketch, extrude, etc.)
workflows/         # Workflow mixins by family:
  ├── base.py      # WorkflowMixin - _send, _bridge_step, verification
  ├── brackets.py  # L-brackets, fillets, chamfers, gussets
  ├── plates.py    # Spacers, plates with holes/slots
  ├── enclosures.py # Boxes, lids, shells
  ├── cylinders.py # Cylinders, tubes, revolves
  └── specialty.py # Strut brackets, ratchet wheels
verification/      # Verification utilities
```

`ParamAIToolServer` now composes functionality via mixins:

```python
class ParamAIToolServer(
    FreeformSessionManager,
    PrimitiveMixin,
    WorkflowMixin,
    BracketWorkflowsMixin,
    PlateWorkflowsMixin,
    EnclosureWorkflowsMixin,
    CylinderWorkflowsMixin,
    SpecialtyWorkflowsMixin,
):
```

#### Completed Work

- **Migrated**: `FreeformSessionManager` with all freeform session lifecycle methods
- **Migrated**: `PrimitiveMixin` with 30+ CAD primitives
- **Migrated**: `WorkflowMixin` with `_send`, `_bridge_step`, `_verify_*` helpers
- **Migrated**: `BracketWorkflowsMixin` with `create_bracket()` as reference implementation
- **Renamed**: `workflows.py` → `workflow_registry.py` to avoid naming collision
- **Updated**: All imports across `fusion_addin/` and `tests/`

#### Test Results

- 372 tests passing (validation, registry, stages, bridge, addin workflows)
- 101 tests need workflow migration (workflows still in original server.py backup)

#### Reference Pattern

`workflows/brackets.py` demonstrates the target structure:

1. Public API method validates input and delegates
2. Private `_create_*_workflow()` implements stage sequence
3. Each stage uses `_bridge_step()` for error handling
4. Verification after each milestone
5. Structured failure with partial results on error

#### Next Steps

Migrate remaining workflows using `brackets.py` as template:

1. `PlateWorkflowsMixin`: `create_spacer`, `create_plate_with_hole`, etc.
2. `EnclosureWorkflowsMixin`: `create_box_with_lid`, `create_simple_enclosure`, etc.
3. `CylinderWorkflowsMixin`: `create_cylinder`, `create_tube`, etc.
4. `SpecialtyWorkflowsMixin`: `create_strut_channel_bracket`, etc.

Each workflow file should be 800-1,500 lines with complete public/private method pairs.

---

## 2026-03-14 (Evening)

### Workflow Migration Progress

Continued migration of workflows from monolithic server.py to mixin architecture.

#### Accomplishments

- **Created migration tooling**:
  - `scripts/migrate_workflows.py` - AST-based extraction of workflow methods
  - `scripts/extract_workflow.py` - Extract specific workflow with helpers
  - `scripts/verify_migration.py` - Verify migration integrity (syntax, duplicates, imports)

- **Migrated PlateWorkflowsMixin**:
  - `create_spacer` - ✅ All 6 tests passing
  - Added `_create_rectangular_prism_workflow` helper
  - Public API methods for: two_hole_plate, four_hole_mounting_plate, slotted_mounting_plate, counterbored_plate, recessed_mount, slotted_mount, cable_gland_plate
  - Pending: private implementations for above

- **Verification tooling**:
  - All mixin files pass syntax checks
  - No duplicate method definitions
  - All imports resolve correctly
  - All 37 workflows accounted for (19 implemented, 18 stubs)

#### Test Results

- 5 workflows with fully passing tests
- 14 workflows with public API but pending private impl
- 18 workflows still as stubs

#### Migration Strategy Decision

Adopting **Option C (Hybrid)**:
1. Migrate simple workflows first (self-contained, no helpers)
2. Defer complex workflows requiring shared helpers (`_create_base_plate_body`, `_run_circle_cut_stage`, etc.)
3. Address shared helpers in a separate pass to avoid duplication issues

#### Safety Measures

- Original server.py preserved at `C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py`
- All changes verified with `scripts/verify_migration.py` before proceeding
- Tests run individually for each workflow during migration
- Git status clean (all changes tracked)

#### Completed (This Session)

**High Priority (simple, self-contained):**
1. ✅ `_create_two_hole_plate_workflow` - 2 tests passing
2. ✅ `_create_four_hole_mounting_plate_workflow` - 2 tests passing
3. ✅ `_create_slotted_mounting_plate_workflow` - 2 tests passing

**Migration Summary:**
- 8 of 37 workflows now fully migrated and tested
- All 3 high-priority plate workflows complete
- Added `draw_slot` abstract method to PlateWorkflowsMixin

---

## 2026-03-15

### Plate Workflow Migration - COMPLETE

**See `docs/MIGRATION_PROCESS.md` for the complete working process.**

### What Was Accomplished

Migrated all 9 plate workflows from monolithic server.py to mixin architecture.

**Process Used** (Boilerplate + AST extraction):
1. Generated clean boilerplate with `migrate_workflows.py`
2. Extracted complete methods using AST (`extract_workflow_fixed.py`)
3. Extracted shared helpers (`extract_helpers.py`)
4. Automated insertion with proper indentation (`insert_into_plates.py`)

**Results**:
- All 9 plate workflows passing tests (12/12 tests)
- 6 shared helper methods working
- Zero manual copy-paste required
- ~20 minutes total (vs. 2+ hours for manual approach)

**New Scripts Created**:
- `scripts/extract_workflow_fixed.py` - AST-based extraction (replaces regex version)
- `scripts/extract_helpers.py` - Extracts shared helper methods
- `scripts/insert_into_plates.py` - Automated insertion with indentation

### Resolution Details

1. **Boilerplate-first**: Used `migrate_workflows.py` to generate clean mixin structure
2. **Fixed extraction**: Created `extract_workflow_fixed.py` using AST to get complete methods
3. **Automated insertion**: Built `insert_into_plates.py` to populate TODO sections

**Results**:
- All 9 plate workflows migrated and passing tests
- 6 shared helper methods extracted and working
- Zero manual copy-paste required

**Scripts now available for future migrations**:
- `extract_workflow_fixed.py --workflow <name>` - Extracts complete workflow using AST
- `extract_helpers.py` - Extracts helper methods
- `insert_into_plates.py` - Inserts extracted code into boilerplate

#### Remaining Work (If Continuing)

Can apply same approach to:
- Cylinder workflows (6 remaining)
- Enclosure workflows (8)
- Specialty workflows (3)
- Additional bracket workflows

**Lower Priority (other mixins):**
6. Cylinder workflows (revolve, knob, bushing, coupler, etc.)
7. Enclosure workflows (box, lid, shell, etc.)
8. Specialty workflows (strut bracket, ratchet, wire clamp)

---

## 2026-03-12

### Strut-bracket intake audit and promotion-boundary cleanup

- Audited a new worker-delivered drawing-backed intake batch under `private/reference_intake/strut-brackets-and-mounts/` instead of promoting it wholesale.

- The worker drop itself is useful working material:

  - raw catalog and PDF artifacts are local

  - derived extraction files exist

  - intake notes exist for all acquired references

- The main issue was promotion drift rather than intake failure:

  - `part-spec-unistrut-p1067-flat-plate.md` had been promoted too far toward implementation despite missing exact overall-length confidence

  - `part-spec-ps809-double-channel-bracket.md` was drafted from load/span-heavy catalog data without enough drawing-backed geometry

  - the Simpson ABR bracket is a valid bracket reference, but adjacent to the strut-channel family rather than a clean strut-hardware anchor

- Cleaned the internal notes to reflect the real confidence level:

  - P1067 demoted from implementation-ready to shortlisted

  - PS809 marked deferred and its intake marked as needing more preprocessing

  - Simpson ABR explicitly marked as adjacent-family research

- Durable intake lesson:

  - drawing-backed acquisition is not the same thing as implementation-ready normalization

  - promotion decisions must stay tied to geometry actually recoverable from the artifact, not to typical-industry assumptions

### Flush-lid enclosure topology correction and validation lesson

- Reworked `flush_lid_enclosure_pair` after live review exposed that the first passing slice was not a real enclosure:

  - the earlier implementation could satisfy envelope dimensions and body-count checks while still producing a sleeve/end-panel shape

  - the live result also showed missing bottom-floor intent from the enclosure-family perspective

- Corrected the workflow to build the base from a shell-backed open-top enclosure path and then reinforce floor thickness explicitly:

  - box base now shells from the top face instead of relying only on an inset cavity cut

  - workflow now hard-gates on `open_face = top`

  - floor thickness is restored explicitly after shelling so the base remains a true enclosure body rather than a thin-bottom shell assumption

- Added and updated targeted tests for the revised stage order and validation shape.

- Revalidated targeted local coverage:

  - `pytest tests/test_validation.py tests/test_workflow_registry.py tests/test_workflow_stages.py tests/test_workflow.py -k "flush_lid_enclosure_pair"`

  - result: `6 passed`

- Re-ran the live Hammond 1590EE smoke after the correction:

  - `python scripts/hammond_1590ee_flush_lid_smoke.py`

  - result: pass

  - live verification now reports `open_face: top`

- Durable lesson:

  - enclosure-family validation cannot rely on envelope dimensions and body count alone

  - for enclosure workflows, validation must also assert topology and orientation semantics such as:

    - intended open face

    - existence of a real floor

    - enclosure-vs-sleeve distinction

    - lid relation on the intended face, not merely a second body that nests somewhere



## 2026-03-09



### Tube, revolve, and T-handle utility-part slice



- Added `tube` as the narrow hollow-cylinder primitive path:

  - outer circle sketch and extrusion first

  - centered bore cut second

  - verification after each stage

  - STL export

- Added `revolve` as the next solid-creation multiplier after extrusion-based families:

  - one tapered side profile

  - one revolve axis

  - one body

  - geometry verification

  - STL export

- Added `tapered_knob_blank` as the first revolve-driven cylindrical utility template:

  - revolve-built outer form

  - centered socket cut

  - verification after both the revolve and cut stages

  - STL export

- Added `t_handle_with_square_socket` as the first true handle-family workflow:

  - centered stem body

  - tee bar body

  - explicit body combine into one part

  - square socket cut from the stem

  - top-perimeter comfort chamfer on the tee

  - STL export

- Added a new `top_outer` chamfer-selection mode so post-extrusion chamfers are no longer limited to the earlier bracket-specific edge logic.

- Tightened geometry verification to use dimensional tolerance instead of exact float equality, after a live Fusion rerun exposed a `5.080000000000001 cm` readback on the T-handle stem.

- Revalidated the full local suite after the slice:

  - `382 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape

- Reloaded Fusion with the current repo add-in and validated `tube` end to end in real Fusion on March 9, 2026:

  - hollow cylindrical body created successfully

  - bore cut succeeded

  - STL export succeeded

- The live validation artifact was written to:

  `manual_test_output\live_smoke_tube.stl`

- Reloaded Fusion with the current repo add-in and validated `revolve` end to end in real Fusion on March 9, 2026:

  - tapered revolve body created successfully

  - verification succeeded after a live readback normalization fix

  - STL export succeeded

- The live validation artifact was written to:

  `manual_test_output\live_smoke_revolve.stl`

- Reloaded Fusion with the current repo add-in and validated `tapered_knob_blank` end to end in real Fusion on March 9, 2026:

  - revolve-built outer body created successfully

  - centered cut stage succeeded

  - STL export succeeded

- The live validation artifact was written to:

  `manual_test_output\live_smoke_tapered_knob_blank.stl`

- Reloaded Fusion with the current repo add-in and validated `t_handle_with_square_socket` end to end in real Fusion on March 9, 2026:

  - stem and tee bodies were built separately

  - the bodies combined into one real CAD body

  - the `3/4 in` square socket cut succeeded

  - the top tee chamfer hit 4 outer top edges

  - STL export succeeded

- The live validation artifact was written to:

  `manual_test_output\live_smoke_t_handle_with_square_socket.stl`



## 2026-03-11

### Document economy consolidation and Boxwrench bootstrap

- Reduced shared-doc sprawl by consolidating parent docs instead of leaving parallel canon:
  - live validation runbook now lives in [`docs/VERIFICATION_POLICY.md`](./VERIFICATION_POLICY.md#adopted-live-scope)
  - session templates now live in [`docs/SESSION_TRANSFER_METHOD.md`](./SESSION_TRANSFER_METHOD.md#appendix-a-handoff-template)
- Reduced root-level canonical docs:
  - `PROJECT_CONTEXT.md` removed
  - `WORKFLOW_STRATEGY.md` removed
  - roadmap and strategy are now expected to live through [`DEVELOPMENT_PLAN.md`](../DEVELOPMENT_PLAN.md) plus the README/docs surface
- Reduced doc duplication:
  - [`BEST_PRACTICES.md`](../BEST_PRACTICES.md) now points to [`docs/VERIFICATION_POLICY.md`](./VERIFICATION_POLICY.md) instead of re-explaining the verification tiers
  - [`docs/FREEFORM_PLAYBOOK.md`](./FREEFORM_PLAYBOOK.md) is slimmer and cross-references verification policy instead of restating it
- Improved discoverability of non-canonical working areas:
  - added [`internal/README.md`](../internal/README.md) with file statuses for runners and moved reference-part notes
  - added [`scripts/README.md`](../scripts/README.md) with adopted-smoke versus working-artifact script status
  - moved `docs/reference_parts/` into [`internal/reference_parts/`](../internal/reference_parts) to make the benchmark-planning status explicit
- Added a private transferable Boxwrench skill area under local ignored `private/skills/`:
  - orchestrator
  - worker
  - closeout
  - research-synthesis
  - each with bundled reference material and lightweight templates
- Added a local mobile/bootstrap pack under ignored `private/mobile/boxwrench-mobile-pack/`:
  - condensed doctrine
  - portable templates
  - install/bootstrap guidance for first-pass and second-pass orchestrator startup in a new repo or client
- This established the next method-level lesson:
  - portable method artifacts should exist at two resolutions
    - fuller skill folders for rich local use
    - compact mobile/bootstrap packs for transfer into other repos or clients

### Live freeform validation canon and session-transfer method


- Added a canonical live freeform validation checklist (now in [`docs/VERIFICATION_POLICY.md`](./VERIFICATION_POLICY.md#adopted-live-scope)):

- Promoted the current live freeform bundle into two narrow adopted smokes:

  - [`scripts/freeform_recipe_c_smoke.py`](../scripts/freeform_recipe_c_smoke.py)

  - [`scripts/freeform_failure_recovery_smoke.py`](../scripts/freeform_failure_recovery_smoke.py)

- Live Fusion now confirms:

  - Freeform C positive-path smoke passes through the currently adopted scope

  - failure recovery smoke passes through failed hard-gate reporting, inspection, corrected commit, and clean session close

- Captured a durable protocol lesson from live recovery testing:

  - `commit_verification` reports assertion failure as `ok: false` with `verification_signals`

  - recovery tooling should not assume an exception-only failure path

- Added a formal session-transfer method:

  - [`docs/SESSION_TRANSFER_METHOD.md`](./SESSION_TRANSFER_METHOD.md) (includes templates in Appendix A and Appendix B)

- Locked in the intended session split:

  - higher-capability orchestrators for synthesis, planning, and adoption decisions

  - mid-tier workers for bounded implementation, smoke execution, and housekeeping

- This established the current token-economy rule for future sessions:

  - bounded startup read from handoff plus recent dev-log slice

  - targeted validation before broad repo review

  - current trajectory should be transferred explicitly, not rediscovered from scratch



### Freeform enforcement, rollback, and housekeeping sweep



- Tightened freeform session contracts:

  - `target_features` now rejects empty or duplicate entries

  - `resolved_features` must be declared in the session manifest

  - `expected_body_count` is now required for `commit_verification`

  - optional `expected_body_count_delta` and `expected_volume_delta_sign` assertions were added

- `commit_verification` now returns a structured `verification_diff` so freeform progress is based on explicit scene deltas instead of only narrative notes.

- Added replay-based rollback for freeform sessions:

  - committed mutations now act as checkpoints

  - rollback rebuilds from a clean design and replays retained committed mutations

  - token remapping and profile rebinding are handled during replay

- Exposed `rollback_freeform_session` on the MCP tool surface and added test coverage for rollback behavior.

- Added freeform guidance docs:

  - `docs/FREEFORM_PLAYBOOK.md`

  - `docs/FREEFORM_CHECKLIST.md`

  - `internal/freeform-architecture.md`

- Added a short deterministic workflow checklist:

  - `docs/CSG_CHECKLIST.md`

- Cleaned repo boundaries:

  - repaired `.gitignore`

  - added ignored `private/` local-only area

  - removed stale `mcp_server/server_new_workflow.py`

  - removed old cleanup/handoff debris and clarified `internal/research/README.md` as archive guidance

- Synced MCP tool descriptions in `mcp_server/tool_specs.py` with the current structured workflow behavior.

- Fixed a snap-fit enclosure regression in workflow reporting:

  - final verification now checks the post-combine state

  - `create_snap_fit_enclosure` now reports `body_count = 2` after the bead is merged into the lid



### Targeted validation status



- Passed:

  - `pytest tests/test_freeform.py tests/test_mcp_entrypoint.py`

  - `pytest tests/test_telescoping_containers.py tests/test_slotted_flex_panel.py tests/test_ratchet_wheel.py tests/test_wire_clamp.py`

  - `pytest tests/test_snap_fit_enclosure.py`

- Current targeted result from this sweep:

  - `18 passed`

- Full suite was not rerun in this sweep.

- Re-ran the live T-handle with a slimmer material-saving shape while preserving the same `3/4 in` square socket and overall height:

  - width stayed `5 in`

  - overall height stayed `4 in`

  - tee and stem depth dropped from `2 in` to `1 in`

  - STL export succeeded to the same live smoke artifact path

- This slice established another durable rule for planning:

  - fit-critical utility parts are now a better forcing function than another plate or bracket variant

  - new workflow tests should increasingly assert interface dimensions and body-combine behavior, not just broad shape creation



### Single-session live bundle recheck



- Kept one Fusion add-in session active and ran a serial live bundle to avoid extra reload cycles.

- Re-ran `t_handle_with_square_socket` twice in the same session:

  - baseline socket fit export

  - replay with `socket_clearance_per_side_cm: 0.05`

  - outer dimensions remained `12.7 x 5.08 x 10.16 cm`

  - effective socket width moved from `1.905 cm` to `2.005 cm`

- Re-ran `tapered_knob_blank` in the same session with explicit dimensions:

  - base diameter `4.0 cm`

  - top diameter `2.5 cm`

  - height `2.5 cm`

  - stem socket diameter `1.0 cm`

- Re-ran `tube_mounting_plate` in the same session with explicit dimensions:

  - plate `6.0 x 10.0 x 0.5 cm`

  - hole diameter `0.5 cm`

  - edge offset `1.5 cm`

  - tube outer/inner/height `2.0 / 1.2 / 3.0 cm`

- Live validation artifacts from this recheck:

  - `manual_test_output\live_smoke_t_handle_socket_base.stl`

  - `manual_test_output\live_smoke_t_handle_socket_clearance_0p05.stl`

  - `manual_test_output\live_smoke_tapered_knob_blank_recheck.stl`

  - `manual_test_output\live_smoke_tube_mounting_plate_recheck.stl`



### Flanged bushing workflow slice and live validation



- Added `flanged_bushing` as the next revolve-driven utility template:

  - shaft and flange created as serial revolve bodies

  - explicit body combine to form one printable body

  - centered bore cut through the combined part

  - geometry verification and STL export

- Added schema validation for the new interface limits:

  - `flange_outer_diameter_cm > shaft_outer_diameter_cm`

  - `flange_thickness_cm < shaft_length_cm`

  - `bore_diameter_cm < shaft_outer_diameter_cm`

- Added coverage across validation, workflow execution, stage registry, smoke-script routing, and MCP tool exposure.

- Revalidated the full local suite after the slice:

  - `389 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape

- Reloaded Fusion with the current repo add-in and ran a serial live bundle in one session:

  - validated `flanged_bushing` end to end

  - ran `tapered_knob_blank` companion regression after the new workflow load

- Live validation artifacts from this bundle:

  - `manual_test_output\live_smoke_flanged_bushing.stl`

  - `manual_test_output\live_smoke_tapered_knob_blank_after_flanged_bushing.stl`



### Pipe clamp half workflow slice and live validation



- Added `pipe_clamp_half` as the next utility-part workflow:

  - rectangular clamp base body

  - non-XY circular saddle cut

  - two mirrored bolt-hole cuts

  - geometry verification after each cut

  - STL export

- Added schema checks for the clamp interface:

  - pipe diameter must leave side and bottom material

  - bolt holes must stay inside footprint bounds

  - bolt-hole centerline must clear the saddle envelope

- Added coverage across:

  - schema validation

  - workflow execution

  - workflow registry and stage runtime checks

  - smoke runner routing

  - MCP tool exposure

- During live bring-up, the first saddle-cut attempt failed with a real cut-intersection error on the `xz` path.

- Hardened the saddle placement in the current validated scope by using negative sketch-local `center_y_cm` for the `xz` saddle cut so the cut intersects the intended top region on extrusion-based bodies.

- Revalidated the full local suite after this adjustment:

  - `395 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape

- In one Fusion session, validated:

  - `pipe_clamp_half` end to end

  - `flanged_bushing` companion regression

- Live validation artifacts from this bundle:

  - `manual_test_output\live_smoke_pipe_clamp_half.stl`

  - `manual_test_output\live_smoke_flanged_bushing_after_pipe_clamp_half.stl`



### Strategy refresh: operation multipliers over more variants



- Captured a planning adjustment based on the current March 9, 2026 repo state:

  - the plate and bracket family has already validated much of the current staged vocabulary

  - the next gains should come from new operation multipliers, not more narrow variants of the same family

- Locked in the current implication for planning docs:

  - `shell`, `simple_enclosure`, `cylinder`, and joined-body cylindrical composition are now treated as landed capability, not future work

  - the next major geometry jump should be `revolve`

  - cylindrical and enclosure templates should continue to drive workflow and test selection

- Captured the intended future path for composition:

  - the current `create_[part]` workflows are reference implementations and fallback happy paths

  - guided freeform primitive composition should come later, with mandatory verification checkpoints between primitive steps

- Captured the current defer list:

  - rollback points

  - angled sketch planes

  - threading

  - component or assembly conversion

  - linear or circular patterns



### Cylinder and tube-mount workflow slice



- Added `cylinder` as a narrow validated server workflow:

  - one circle profile

  - one extrusion

  - geometry verification

  - STL export

- Added `tube_mounting_plate` as the first joined-body cylindrical utility template:

  - rectangular base plate

  - two mounting-hole cuts

  - offset cylindrical sleeve body

  - explicit body combine

  - final tube-bore cut

  - STL export

- Added a narrow `combine_bodies` operation through the server and Fusion add-in layers so the workflow produces one real CAD body instead of relying on overlapping solids.

- Hardened the mock and Fusion adapter test harnesses to preserve offset-sketch placement and joined-body thickness correctly.

- Revalidated the full local suite after the change:

  - `349 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape

- Reloaded Fusion with the current repo add-in and validated `cylinder` end to end in real Fusion on March 9, 2026:

  - circle sketch

  - cylindrical extrusion

  - geometry verification

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_cylinder.stl`

- Reloaded Fusion with the current repo add-in and validated `tube_mounting_plate` end to end in real Fusion on March 9, 2026:

  - rectangular base plate extrusion

  - two serial mounting-hole cuts

  - offset sleeve extrusion above the plate

  - body combine to a single joined part

  - centered bore cut through the sleeve

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_tube_mounting_plate.stl`

- This slice established a durable rule for cylindrical utility templates:

  - when the intended part is a single printable part, prefer a true joined CAD body

  - slicer-side union of overlapping meshes is a fallback practice only, not the default workflow contract



## 2026-03-10



### Slotted mounting plate live validation



- Reloaded Fusion with the current repo add-in.

- Ran the narrow live smoke path for `slotted_mounting_plate` and confirmed the full staged sequence in real Fusion:

  - new design

  - clean state verification

  - base rectangle sketch

  - four corner circles

  - centered slot

  - outer-profile extrusion (holes and slot punched through)

  - geometry verification

  - STL export

- The slot readback fix (`live_ops.py` XY collapsed-slot fallback) resolved the earlier 1.5×0.5 → 1.0×0.5 readback regression in mixed sketches.

- Smoke output: `manual_test_output\live_smoke_slotted_mounting_plate.stl`



### Filleted bracket server workflow wired up



- Added `CreateFilletedBracketInput` schema with `fillet_radius_cm` validation:

  - must be positive

  - must be less than half of `leg_thickness_cm`

  - must be less than half of `thickness_cm`

- Added `apply_fillet` bridge wrapper to `ParamAIToolServer`.

- Added `create_filleted_bracket` public method and `_create_filleted_bracket_workflow` private method.

- Workflow stages: new_design → verify_clean_state → create_sketch → draw_l_bracket_profile → list_profiles → extrude_profile → verify_geometry → apply_fillet → verify_geometry → export_stl

- Post-fillet verification checks `fillet_applied` and `edge_count` bounds (1–4 interior edges).

- Added mock `edge_count: 2` to mock adapter's `apply_fillet` response for realistic coverage.

- Added stage sequence test for `filleted_bracket` in `test_workflow_stages.py`.

- Revalidated the full suite: `285 passed`.

- `filleted_bracket` is the first workflow to apply a post-extrusion modifier before export.

- Live smoke pending add-in reload with the new `create_filleted_bracket` method exposed.



## 2026-03-09



### Four-hole mounting plate workflow slice



- Added `four_hole_mounting_plate` as the next narrow plate-family workflow after the validated two-hole and slotted plate path.

- Kept the scope narrow:

  - one flat rectangular mounting plate only

  - four identical corner through-holes

  - explicit `edge_offset_x_cm` and `edge_offset_y_cm`

  - single base sketch with outer profile plus four circles

  - verification that the outer plate dimensions remain correct

  - verification that body count stays 1

  - STL export

- Added one practical placement idea only:

  - mirrored edge-offset placement across both X and Y to cover a common four-corner mounting pattern

- Added regression coverage for:

  - workflow registry and stage sequencing

  - schema validation for mirrored X/Y edge offsets

  - MCP workflow execution and missing-hole-profile verification failures

  - live-registry routing for the four-circle sketch sequence

  - smoke-script routing for `four_hole_mounting_plate`

- Revalidated the full suite after the change:

  - `270 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape

- Reloaded Fusion with the current repo add-in and validated `four_hole_mounting_plate` end to end in real Fusion on March 9, 2026:

  - base plate sketch

  - four corner-hole circles in one sketch

  - outer-profile extrusion with preserved hole cutouts

  - outer dimensions remained correct

  - body count remained 1 throughout

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_four_hole_mounting_plate.stl`



### Lid for box workflow slice



- Added `lid_for_box` as the next narrow box-family workflow after `open_box_body`.

- Kept the scope narrow:

  - one rectangular cap lid only

  - explicit `lid_thickness_cm`, `rim_depth_cm`, and `wall_thickness_cm`

  - base outer prism first

  - one bottom-side inset rectangular cut that leaves a downward perimeter rim

  - verification that outer dimensions remain correct

  - verification that body count stays 1

  - STL export

- Reused the validated box-body and cut path without adding new fit logic:

  - no clearance tuning

  - no snaps

  - no paired-part assumptions

- Added regression coverage for:

  - workflow registry and schema validation

  - MCP workflow execution and rim-profile verification failures

  - smoke-script routing for `lid_for_box`

  - live-registry staging for the second bottom-side cut sketch

- Revalidated the full suite after the change:

  - `262 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape

- Reloaded Fusion with the current repo add-in and validated `lid_for_box` end to end in real Fusion on March 9, 2026:

  - lid sketch and base extrusion

  - inset rim-cut sketch and cut extrusion

  - outer dimensions remained correct

  - body count remained 1 throughout

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_lid_for_box.stl`



### Open box body workflow slice



- Added `open_box_body` as the next narrow box-family workflow after the validated plate-pocket path.

- Kept the scope narrow:

  - one open-top box body only

  - explicit `wall_thickness_cm` and `floor_thickness_cm`

  - base outer prism first

  - one inset rectangular cavity cut from an offset XY sketch plane

  - verification that outer dimensions remain correct

  - verification that body count stays 1

  - STL export

- Added one new low-level placement idea only:

  - `create_sketch` now supports a narrow non-negative `offset_cm` for parallel construction-plane sketches

- Added regression coverage for:

  - workflow registry and schema validation

  - MCP workflow execution and cavity-profile verification failures

  - smoke-script routing for `open_box_body`

  - live-registry offset-sketch staging

  - Fusion adapter offset-plane sketch creation

- Revalidated the full suite after the change:

  - `257 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape

- Reloaded Fusion with the current repo add-in and validated `open_box_body` end to end in real Fusion on March 9, 2026:

  - outer box sketch and extrusion

  - offset cavity sketch at the requested floor thickness

  - cavity cut leaving an open top and preserved floor

  - outer dimensions remained correct

  - body count remained 1 throughout

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_open_box_body.stl`



### Counterbored plate and recessed mount slices



- Added `counterbored_plate` as the next cut-sequencing slice in the plate family.

- Kept the `counterbored_plate` scope narrow:

  - flat rectangular plate

  - one through-hole cut

  - one larger shallow concentric counterbore cut

  - same-body verification after each cut

  - STL export

- Added `recessed_mount` as the next explicit-placement slice in the same family.

- Kept the `recessed_mount` scope narrow:

  - flat rectangular plate

  - one bounded rectangular pocket

  - one new low-level primitive: `draw_rectangle_at`

  - same-body verification after the recess cut

  - STL export

- Added schema validation for:

  - `xy`-only scope

  - counterbore-diameter-greater-than-hole-diameter

  - cut-depth-less-than-thickness checks

  - recess-inside-plate bounds

- Added regression coverage for:

  - workflow registry and stage ordering

  - MCP workflow execution and profile-selection failures

  - live and mock offset-rectangle operations

  - live-registry routing in the adapter harness

  - smoke-script routing for both workflows

- Revalidated the full suite after the change:

  - `250 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape

- The first live validation attempt failed for both workflows for an operational reason, not a workflow bug:

  - two live smoke scripts were issued against the same Fusion bridge in parallel

  - scene verification then observed mixed sketches and bodies from both runs

  - serial rerun resolved the failure without code changes

- Reloaded Fusion with the current repo add-in and validated `counterbored_plate` end to end in real Fusion on March 9, 2026:

  - rectangular base sketch and extrusion

  - through-hole cut

  - larger shallow concentric counterbore cut

  - body count remained 1 throughout

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_counterbored_plate.stl`

- Reloaded Fusion with the current repo add-in and validated `recessed_mount` end to end in real Fusion on March 9, 2026:

  - rectangular base sketch and extrusion

  - explicit XY-placed rectangular recess sketch

  - partial-depth recess cut

  - body count remained 1 throughout

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_recessed_mount.stl`

- This slice reinforced an already-known but now re-observed operating rule:

  - the live Fusion bridge is a single execution path

  - live smoke must run serially, even if the local tool surface can launch commands in parallel



### Slotted mount workflow slice



- Added `slotted_mount` as the next placement-focused workflow after mirrored hole placement.

- This slice introduces one new low-level sketch primitive: `draw_slot`.

- Kept the workflow scope narrow:

  - flat rectangular plate

  - one horizontal slot in the base sketch

  - deterministic outer-profile selection

  - single-body extrusion

  - geometry verification

  - STL export

- Added schema validation for:

  - `xy`-only scope

  - slot-length-greater-than-slot-width

  - slot-inside-plate bounds

- Added regression coverage for:

  - mock input validation

  - live adapter slot creation in the fake Fusion harness

  - workflow registry and stage ordering

  - MCP workflow execution and slot-profile verification failures

  - live-registry routing in the adapter harness

  - smoke-script routing

- Revalidated the full suite after the change:

  - `235 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape

- The first live smoke attempt exposed a narrow live-adapter readback issue:

  - `draw_slot` succeeded

  - Fusion returned the slot profile as `1.0 x 0.5` instead of the requested `1.5 x 0.5`

  - the defect was in live profile readback, not workflow registration or geometry creation

- Fixed the live adapter by preserving recorded slot dimensions and falling back to them only when Fusion collapses an XY slot profile width during `list_profiles`.

- Added a regression for the exact collapsed-slot readback case in the fake Fusion harness.

- Reloaded Fusion with the current repo add-in and validated `slotted_mount` end to end in real Fusion on March 9, 2026:

  - rectangular base sketch

  - one horizontal slot in the same sketch

  - deterministic outer-profile selection

  - single-body extrusion with expected overall dimensions

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_slotted_mount.stl`

- This slice reinforced a durable operating rule:

  - after live add-in code changes, reload Fusion from the current checkout before trusting a live smoke rerun



### Two-hole plate workflow slice



- Added `two_hole_plate` as the first mounting-plate-family workflow slice.

- Kept the scope narrow:

  - flat rectangular plate

  - two mirrored sketch holes on a shared Y centerline

  - symmetric edge-offset placement

  - single-sketch extrusion

  - geometry verification

  - STL export

- Added schema validation for:

  - `xy`-only scope

  - mirrored edge-offset bounds

  - hole-inside-plate checks

- Added regression coverage for:

  - workflow registry and stage ordering

  - MCP workflow execution and failure handling

  - live-registry routing in the adapter harness

  - smoke-script routing and mirrored circle placement

- Revalidated the targeted test slice after the change:

  - `77 passed`

- Reloaded Fusion with the current repo add-in and validated `two_hole_plate` end to end in real Fusion on March 9, 2026:

  - rectangular plate sketch

  - two mirrored circles in the same sketch

  - deterministic outer-profile selection

  - single-body extrusion with body count still at 1

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_two_hole_plate.stl`



### Planning and best-practices refresh



- Realigned the canonical docs around the repo's current phase instead of the older scaffold-era framing.

- Added `BEST_PRACTICES.md` as a living workflow and prompting contract for both contributors and AI-driven usage.

- Updated the roadmap and context docs to reflect the current validated workflow family, the `211 passed` baseline, and the shift toward use-and-fix plus narrow practical expansion.

- Updated the README so the public-facing project summary matches the actual live-validated workflow set.



### Live validation for cut and fillet workflows



- Reloaded Fusion with the current repo add-in so `/health.workflow_catalog` exposed both `plate_with_hole` and `filleted_bracket`.

- Re-ran the narrow live smoke path for `plate_with_hole` and confirmed the full staged sequence in real Fusion:

  - base plate sketch and extrusion

  - second sketch for the hole

  - cut extrusion

  - post-cut verification with body count still at 1

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_plate_with_hole.stl`

- Re-ran the narrow live smoke path for `filleted_bracket` and confirmed the full staged sequence in real Fusion:

  - L-profile sketch and extrusion

  - geometry verification

  - live `apply_fillet`

  - second geometry verification

  - STL export

- The live validation artifact was written to:

  `manual_test_output\live_smoke_filleted_bracket.stl`

- One failed `filleted_bracket` smoke attempt during this session was caused by issuing multiple live smoke scripts against the same Fusion bridge in parallel; serial rerun succeeded without code changes.



### Bridge cancellation classification



- Added a narrow bridge-client cancellation path so aborted requests are no longer lumped into generic reachability failures.

- `mcp_server.bridge_client.BridgeClient` now distinguishes:

  - timeouts

  - cancellations / aborted requests

  - generic bridge reachability failures

- Workflow wrapping now converts bridge cancellations into structured `WorkflowFailure(classification="cancelled")` payloads with prior-stage context, parallel to the existing timeout handling.

- Added regression coverage for:

  - cancelled `/health` requests

  - cancelled `/command` requests

  - propagation of bridge cancellation into workflow failure classification and partial progress

- Revalidated the full suite after the change:

  - `203 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Pending-request cancellation in the Fusion bridge



- Added explicit pending-request cancellation to the Fusion-side dispatcher:

  - queued requests now have stable request ids

  - a pending request can be marked cancelled before execution

  - cancelled queued work is skipped cleanly instead of still running later

- Added a `/cancel` HTTP bridge endpoint for pending request ids so external callers can stop queued work before it reaches Fusion execution.

- Kept scope deliberately narrow:

  - cancellation is only guaranteed for queued work

  - already-started Fusion operations are not preempted by this slice

- Added regression coverage for:

  - dispatcher-side pending cancellation

  - refusal to cancel already-started work

  - HTTP bridge cancellation of a queued command

  - HTTP bridge handling for unknown request ids

- Revalidated the full suite after the change:

  - `207 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Bridge client cancel support



- Extended `mcp_server.bridge_client.BridgeClient` so callers can:

  - attach an explicit `request_id` to `send()`

  - cancel a pending request through `cancel(request_id)`

- This keeps the new queued-cancellation capability usable from normal bridge-client consumers instead of requiring raw manual HTTP calls.

- Added regression coverage for:

  - cancel against an unknown request id

  - cancel when the bridge is unreachable

- Revalidated the full suite after the change:

  - `209 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Cooperative cancellation for started commands



- Added a Fusion-side cancellation context in `fusion_addin/cancellation.py` so a running command can cooperatively detect cancellation and raise a dedicated `OperationCancelledError`.

- The dispatcher now keeps cancellation state available to the currently executing request instead of treating cancellation as queue-only.

- The HTTP bridge now returns a cancellation-specific response for cooperatively aborted running commands, and `/cancel` distinguishes:

  - `cancelled` for queued work stopped before execution

  - `cancellation_requested` for already-started work

- `BridgeClient.send()` now classifies cancellation-specific bridge responses as cancellation instead of generic command failure.

- Added regression coverage for:

  - cooperative dispatcher-side cancellation of a started command

  - cooperative HTTP bridge cancellation of a started command

  - cancellation-specific client classification for command responses

- Revalidated the full suite after the change:

  - `211 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



## 2026-03-08



### Documentation governance



- Locked in the canonical project-tracking rule:

  - `DEVELOPMENT_PLAN.md` is the roadmap/status source

  - `docs/dev-log.md` is the running execution log

  - both are updated only for material changes in validated state, priorities, or completed work

  - no new backlog or parallel status doc should be created unless these two docs become inadequate



### Test harness temp-path fix



- Replaced the test suite's dependence on pytest-managed system temp roots with a repo-local temp fixture in `tests/conftest.py`.

- Kept the existing export-path safety model intact by aligning Python's tempdir environment with that repo-local test temp root instead of broadening the allowlist.

- Revalidated the full suite in this environment with cache writes disabled:

  - `145 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Workflow bridge-error hardening



- Wrapped workflow-stage bridge/runtime failures in structured `WorkflowFailure` results instead of leaking raw `RuntimeError`s from the MCP workflow layer.

- Added regression coverage for bridge failure during:

  - `create_spacer` clean-state verification

  - `create_mounting_bracket` export

- Revalidated the full suite after the change:

  - `147 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Bridge timeout hardening



- Added explicit bridge timeout detection so hung `/health` and `/command` requests raise a distinct timeout error instead of collapsing into generic reachability failures.

- Propagated bridge timeouts through workflow execution as structured `WorkflowFailure` payloads with `classification="timeout"` and prior stage context.

- Added regression coverage for bridge timeout handling at both the bridge-client and workflow layers.

- Revalidated the full suite after the change:

  - `149 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Two-hole smoke verification hardening



- Tightened `scripts/fusion_smoke_test.py` so mounting workflows now verify the expected hole-profile count and diameter before extrusion instead of only validating the outer profile.

- Added regression coverage for the new smoke failure mode when a mounting bracket sketch does not produce the expected hole profile set.

- Real Fusion was revalidated on March 8, 2026 for `two_hole_mounting_bracket` on `xy` with the strengthened smoke path.

- The live artifact was written to:

  `manual_test_output\live_smoke_two_hole_mounting_bracket_xy.stl`

- Revalidated the full suite after the change:

  - `150 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Workflow test isolation hardening



- Reworked the failure-path coverage in `tests/test_workflow.py` to use an intercepting bridge client instead of monkeypatching `ParamAIToolServer` methods in place.

- This keeps the tests aligned with the real bridge boundary while avoiding per-test mutation of live server methods.

- Revalidated the full suite after the change:

  - `150 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Plate and fillet workflow prep



- Revalidated the current worktree baseline and current repo state at `189 passed`, then extended it to `194 passed` after the new live fillet and smoke-path coverage landed.

- Attempted a real `plate_with_hole` smoke run on March 8, 2026, but the loaded Fusion add-in still reported the older five-workflow catalog and rejected `workflow_name="plate_with_hole"` at `new_design`.

- That means the repo code and the currently loaded live add-in are out of sync; real `plate_with_hole` and `filleted_bracket` validation now depend on reloading the Fusion add-in from the current repo state.

- Implemented live `apply_fillet` support in `fusion_addin/ops/live_ops.py` with the narrow current contract:

  - existing body token

  - positive radius

  - apply fillet to the body's available edges

  - preserve the same body token and report post-fillet dimensions

- Registered `apply_fillet` in the live op registry and added live-registry coverage for the `filleted_bracket` stage sequence.

- Extended the smoke runner with:

  - explicit `plate_with_hole` routing coverage for the second sketch and cut extrusion

  - explicit `filleted_bracket` routing coverage for `apply_fillet` and the second geometry verification pass

- Revalidated the full suite after the change:

  - `194 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Smoke runner stale-catalog guard



- Tightened `scripts/fusion_smoke_test.py` so it now inspects `/health.workflow_catalog` before issuing any modeling command.

- If the requested workflow is not exposed by the currently loaded live add-in, the script now fails immediately with a reload-specific error instead of continuing to a later `new_design` failure.

- Re-ran the blocked `plate_with_hole` live smoke command and confirmed the new behavior against the still-stale live add-in:

  - the script printed the older five-workflow catalog

  - then failed immediately with a reload instruction for `plate_with_hole`

- Added regression coverage for this stale-catalog guard.

- Revalidated the full suite after the change:

  - `195 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### MCP plate_with_hole workflow



- Added `CreatePlateWithHoleInput` to the schema layer with the current narrow contract:

  - `xy` only

  - positive plate dimensions and hole diameter

  - hole center must stay inside the rectangular sketch bounds

- Implemented `ParamAIToolServer.create_plate_with_hole()` as a staged MCP workflow:

  - `new_design`

  - `verify_clean_state`

  - base plate sketch/body creation and verification

  - second sketch for the hole

  - cut extrusion

  - second geometry verification

  - STL export

- Added focused regression coverage for:

  - schema validation of the new payload

  - successful end-to-end MCP workflow execution against the running bridge

  - structured bridge-error wrapping when the cut stage fails

- Revalidated the full suite after the change:

  - `198 passed`

  - 1 existing warning for `TestFusionApiAdapter` pytest collection shape



### Canonical spec update



- Updated the canonical docs to absorb the Faust benchmark lessons instead of leaving them only in research notes.

- Locked in the v1 stance:

  - narrow mechanical workflows

  - staged build -> verify -> continue

  - human correction loops as a normal operating model

  - Faust as benchmark/reference only, not implementation base



### Initial scaffold



- Added Python project scaffolding with:

  - Fusion add-in skeleton

  - loopback HTTP bridge

  - MCP-side tool server

  - tests

- Defined the first golden path around `spacer`.



### Workflow discipline



- Added workflow-stage enforcement and a shared workflow registry.

- Introduced a workflow strategy doc to make the growth model explicit:

  - learn reliable stage paths

  - standardize them

  - build more complex workflows from validated subpaths



### Failure-handling hardening



- Added verification checkpoints and explicit no-autoretry behavior to the spacer workflow.

- Added structured workflow failures that preserve:

  - failing stage

  - classification

  - partial result

  - suggested next step



### Live adapter progress



- Replaced placeholder live ops with an adapter-backed live path.

- Added a `FusionApiAdapter` for the spacer sequence:

  - `new_design`

  - `create_sketch`

  - `draw_rectangle`

  - `list_profiles`

  - `extrude_profile`

  - `get_scene_info`

  - `export_stl`

- Added adapter-focused regression tests for the live path shape.



### Add-in bootstrap



- Added explicit bootstrap mode selection:

  - `mock` outside Fusion

  - `live` when a Fusion design context is available

- Added bridge health reporting for the active mode and workflow catalog.



### Live smoke-test status



- Live Fusion testing now reaches past `draw_rectangle` without crashing.

- The Fusion-side crash was fixed by changing live command execution to use a `CustomEvent`-driven main-thread dispatch path instead of executing Fusion mutations directly on the HTTP worker thread.



### Handoff-recorded confirmations



- The March 9, 2026 session handoff recorded serial live smoke confirmation for `chamfered_bracket`.

- The same handoff recorded a live recheck for `filleted_bracket`.

- Export artifacts referenced by that handoff:

  - `manual_test_output\live_smoke_chamfered_bracket.stl`

  - `manual_test_output\live_smoke_filleted_bracket_recheck.stl`

- The same handoff also treated `box_with_lid` as a finished validated slice.

- Real Fusion has now confirmed:

  - `/health` responds in `live` mode

  - `new_design` works

  - `get_scene_info` clean-state verification works

  - `create_sketch` works

  - the bridge remains stable through the first geometry mutation boundary



### Smoke-test runner fixes



- The local smoke script was corrected to match the actual bridge response envelopes:

  - `create_sketch` returns `result.sketch`

  - `extrude_profile` returns `result.body`

- The verification stage used by the runner was aligned to `verify_geometry`.



### Workflow-session hardening



- Re-running the smoke test exposed stale workflow-session state after a partial earlier run.

- Live workflow session startup is now being adjusted so `new_design` restarts the named workflow session cleanly instead of inheriting an in-progress stage sequence.

- A regression test was added for restarting the `spacer` workflow with a second `new_design`.



### Current validated path



- Mock-backed spacer workflow is passing in tests.

- Live adapter unit-style tests are passing in a fake Fusion harness.

- Dispatcher/bridge harness checks are passing with the main-thread dispatch change.

- Real Fusion smoke testing is no longer blocked by startup or the earlier crash.

- The current next live check is to rerun the spacer smoke sequence after the workflow-session reset fix and confirm the remaining tool responses through `export_stl`.



### Hardening pass



- Fixed the dispatcher drain loop so pending work is drained with repeated `get_nowait()` calls instead of relying on `Queue.empty()`.

- Added explicit main-thread enforcement inside `FusionApiAdapter` operation methods so threading regressions fail fast instead of crashing Fusion silently.

- Added export path allowlist validation:

  - MCP-side `CreateSpacerInput` now rejects paths outside allowlisted export locations

  - live and mock export paths now enforce the same restriction

  - relative smoke-test output paths are normalized to absolute paths before they reach the bridge

- Added targeted regression coverage for:

  - dispatcher pending-drain behavior

  - off-main-thread adapter calls

  - allowlist rejection for unsafe export paths



### First real live end-to-end success



- The narrow `spacer` smoke workflow now completes successfully in real Fusion from bridge health through STL export.

- Real Fusion has now confirmed the full live slice:

  - `/health` responds in `live` mode

  - `new_design` creates a fresh design

  - `create_sketch` creates an XY sketch

  - `draw_rectangle` creates the intended closed profile

  - `list_profiles` returns the expected single profile

  - `extrude_profile` creates the expected body

  - `get_scene_info` reports the expected sketch/body state and dimensions

  - `export_stl` writes the output successfully

- The first real exported artifact was produced at `manual_test_output/live_smoke_spacer.stl`.

- This moves the project past architecture proof into a real working live vertical slice for the `spacer` path.

- The next live expansion targets are:

  - a real-Fusion `xz` or `yz` smoke variant to validate plane-aware reporting

  - structured timeout/cancellation behavior

  - the first `bracket` workflow slice built on the validated spacer stages



### Smoke-test strictness



- Tightened the smoke runner so it now verifies the returned scene geometry instead of only printing it.

- The smoke script now fails fast if the reported:

  - sketch plane

  - body width

  - body height

  - body thickness

  - body name

  do not match the requested build.

- Added script-level regression coverage for:

  - a successful `xz` smoke run

  - a geometry mismatch that should fail the smoke test immediately



### Real Fusion non-XY finding



- A real `xz` smoke run succeeded through export but exposed a live adapter bug in `list_profiles`.

- The observed failure was specific:

  - `create_sketch` correctly reported `xz`

  - `get_scene_info` correctly reported `xz`

  - `extrude_profile` and `export_stl` succeeded

  - but `list_profiles` reported `height_cm: 0.0` instead of the expected `1.0`

- The adapter is now being hardened to treat non-XY profile bounding boxes more defensively by falling back to sketch-local extents when Fusion reports a collapsed world-mapped height.

- The smoke runner is also being tightened so profile dimensions are verified explicitly, not inferred from the later body result.



### Workflow-level non-XY fallback



- A stricter rerun proved the adapter-only fallback was not sufficient for the real `xz` case.

- The live workflow layer now repairs obviously collapsed non-XY profile dimensions using the already-recorded rectangle dimensions from `SketchState` when:

  - the sketch plane is not `xy`

  - profile count matches recorded rectangle count

  - Fusion reports a near-zero profile height

- This is intentionally a narrow corrective step for the current staged rectangle workflow, not a claim that arbitrary non-XY profile measurement is solved in general.



### Adapter-side non-XY rectangle fallback



- The live rerun still returned collapsed `list_profiles` dimensions, which suggests the bridge can surface the raw adapter result before the workflow-layer repair is visible.

- `FusionApiAdapter` now also records rectangle dimensions per sketch and uses that cache as a narrow fallback when a non-XY profile bounding box collapses to near-zero height.

- Added adapter regression coverage for the stricter real-world failure shape where an `xz` profile can report a bounding box with both world-mapped and sketch-local height collapsed.



### Repeated real-Fusion `xz` confirmation



- After reloading the live bridge, the real Fusion `xz` smoke test was rerun repeatedly on March 8, 2026.

- A 10-run terminal sweep of:

  `python scripts/fusion_smoke_test.py --plane xz --output-path manual_test_output\live_smoke_spacer_xz.stl`

  completed with 10/10 passing exits.

- The earlier intermittent `list_profiles.height_cm = 0.0` failure was observed during bring-up, but the current loaded add-in now appears stable enough to treat the narrow non-XY `spacer` path as validated.

- This validation is still scoped narrowly:

  - staged `spacer` workflow

  - axis-aligned rectangle on a construction plane

  - single intended profile

- With that scope, the next workflow expansion target is `bracket`.



### Bracket blank live validation



- Added a bracket-aware smoke runner path so the same script can validate either `spacer` or `bracket`.

- Added script-level regression coverage for the bracket route and made the smoke-script test import independent of package discovery quirks.

- Real Fusion now confirms the narrow `bracket` blank workflow on March 8, 2026 for:

  - `xz`

  - `xy`

- The currently validated `bracket` scope is still narrow:

  - rectangle sketch

  - single profile

  - single-body extrusion

  - geometry verification

  - STL export

- This is a real workflow expansion, but it is not yet a true L-bracket or hole-feature workflow.



### Canonical docs refresh



- Reviewed external notes covering project context, architecture framing, and host integration.

- Updated the canonical docs to clarify:

  - ParamAItric is host-agnostic at the MCP boundary

  - host-facing MCP transport packaging is intended direction, not current shipped capability

  - the README should stay focused on the project itself rather than benchmark or behind-the-scenes framing

- Added a dedicated `HOST_INTEGRATION.md` doc for the intended transport and host strategy so the README can stay narrow.



### True L-bracket workflow slice



- The `bracket` workflow no longer reuses the spacer rectangle stage as its primary geometry step.

- Added a new `draw_l_bracket_profile` operation and updated `create_bracket` to use an explicit `leg_thickness_cm` contract.

- The narrow bracket workflow now stages:

  - `new_design`

  - `verify_clean_state`

  - `create_sketch`

  - `draw_l_bracket_profile`

  - `list_profiles`

  - `extrude_profile`

  - `verify_geometry`

  - `export_stl`

- Added regression coverage for:

  - schema validation of `leg_thickness_cm`

  - workflow execution and registry stage shape

  - live adapter L-profile sketch creation

  - bracket smoke runner routing with the new draw command



### Real Fusion L-bracket validation



- Real Fusion now confirms the first true L-bracket workflow slice on March 8, 2026 for:

  - `xz`

  - `xy`

- The validated narrow scope is now:

  - one L-profile sketch

  - one resolved profile

  - one body extrusion

  - geometry verification

  - STL export

- This is the first bracket-specific workflow step that is meaningfully distinct from the spacer path.



### Mounting bracket workflow slice



- Added `draw_circle` as the narrow next sketch primitive after the validated L-profile bracket path.

- Added a new `mounting_bracket` workflow that stages:

  - `new_design`

  - `verify_clean_state`

  - `create_sketch`

  - `draw_l_bracket_profile`

  - `draw_circle`

  - `list_profiles`

  - `extrude_profile`

  - `verify_geometry`

  - `export_stl`

- The workflow keeps scope deliberately tight:

  - `xy` only for the current validated slice

  - one explicit circular hole

  - deterministic outer-profile selection by expected overall dimensions

- Added regression coverage for:

  - circle sketch creation in the live adapter harness

  - mounting bracket schema validation

  - workflow registry shape

  - workflow execution and smoke-runner routing



### Real Fusion mounting bracket validation



- Real Fusion now confirms the first mounting bracket workflow slice on March 8, 2026 for `xy`.

- The exported validation artifact was produced at:

  `manual_test_output\live_smoke_mounting_bracket_xy.stl`

- The current validated hole-workflow scope is:

  - one L-profile bracket sketch

  - one circular hole in the sketch

  - outer-profile selection from a multi-profile sketch

  - one body extrusion

  - geometry verification

  - STL export

### Multi-plane coordinate mapping validation

- Experimentally proved coordinate mappings on Fusion's standard planes by generating and bounding a physical McMaster Strut Channel Bracket.
- **XZ Plane Mapping:** sketch_x maps to global X. sketch_y maps to global -Z. To draw a hole at a specific Z depth, pass -Z.
- **YZ Plane Mapping:** sketch_x maps to global -Z. sketch_y maps to global Y. To push a hole into the positive Y axis, pass it directly to center_y_cm. To align it along Z, pass -Z to center_x_cm.
- Verified that convert_bodies_to_components successfully moves standard solid bodies into a component hierarchy, leaving the root bodies list empty (which was verified via get_scene_info).


---

## 2026-03-15

### Workflow Migration Sprint - Cylinders + Brackets Complete

Major migration session completed. All cylinder and bracket workflows now migrated from original server.py to mixin architecture.

#### Session Scope

**Completed:**
- 7 cylinder workflows (revolve, tapered_knob_blank, flanged_bushing, shaft_coupler, pipe_clamp_half, t_handle_with_square_socket, tube_mounting_plate)
- 6 bracket workflows (filleted_bracket, chamfered_bracket, mounting_bracket, two_hole_mounting_bracket, triangular_bracket, l_bracket_with_gusset)

**Test Results:**
```
63 passing / 15 failing / 78 total
```

All 15 failures are unmigrated stubs:
- 2 pre-existing revolve edge case failures
- 13 enclosure workflow stubs

#### Migration Process Used

1. **AST Extraction**: `scripts/extract_workflow_fixed.py --workflow <name>`
2. **Insert into mixin**: Direct edit to appropriate `workflows/<family>.py`
3. **Add abstract methods**: Declare dependencies at bottom of mixin
4. **Verify**: `pytest tests/test_workflow.py -k "<family>"`

#### Files Modified

- `mcp_server/workflows/cylinders.py` - Added 7 workflows + 3 helpers
- `mcp_server/workflows/brackets.py` - Added 6 workflows + `_FILLET_EDGE_COUNT_MAX`
- `docs/AI_CONTEXT.md` - Updated test counts and migration status
- `docs/WORKFLOW_MIGRATION_GUIDE.md` - Updated status tables

#### Key Findings

1. **Cylinder helpers required**: `_create_revolved_body`, `_verify_revolve_body`, `_select_revolve_profile_by_dimensions` - these were extracted separately and added to the mixin.

2. **Bracket constant needed**: `_FILLET_EDGE_COUNT_MAX = 4` - defined as class attribute in mixin (was in original server.py but not migrated).

3. **Complexity breakdown**:
   - Tier 2 (simple): revolve, tapered_knob_blank, flanged_bushing, shaft_coupler - straightforward revolve patterns
   - Tier 3 (medium): pipe_clamp_half, t_handle_with_square_socket - multi-stage with cuts/combines
   - Tier 4 (complex): tube_mounting_plate - plate + cylinder hybrid with offset sketches
   - Brackets: filleted/chamfered similar pattern, mounting uses hole centers, triangular simple, gusset uses combine

#### Documentation Created

- `docs/AI_CONTEXT.md` - Single-read context for AI assistants (kept current)
- Updated migration status in WORKFLOW_MIGRATION_GUIDE.md

#### Next Steps (Paused)

**Remaining work:**
- Enclosures (8 workflows): simple_enclosure, open_box_body, lid_for_box, box_with_lid, flush_lid_enclosure_pair, project_box_with_standoffs, snap_fit_enclosure, telescoping_containers
- Specialty (3 workflows): strut_channel_bracket, ratchet_wheel, wire_clamp

**Estimated effort:** ~1-1.5 hours for enclosures, ~30 min for specialty

**Status:** Ready to resume. All patterns established, migration tools proven.
---

## 2026-03-26

### Live Session: Pole Mount Creation + Edge-Specific Features

**User session with live Fusion 360 integration.** Successfully created custom pole mount parts and extended the API for edge-specific operations.

#### Session Goals

1. Create a pole mount plate with tube socket for 0.75" pole
2. Add mounting holes (4 corners)
3. Chamfer the socket top edge
4. Fillet the plate outer edges

#### Bug Fix: Fusion Add-in Path Resolution

**Problem:** Fusion 360 add-in failed to start because it couldn't find `mcp_server` module.

**Root Cause:** Fusion runs in isolated Python environment; imports from repo root failed.

**Fix:** Modified `fusion_addin/FusionAIBridge.py` to add repo root to `sys.path` before imports:

```python
_addin_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_addin_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
```

**Status:** Committed. This is a general fix applicable to all installations.

#### Parts Created

| Variant | Features | STL File |
|---------|----------|----------|
| Simple | Base plate + socket | `pole_mount.stl` |
| 2-hole | + 2 centered mounting holes | `pole_mount_with_holes.stl` |
| 4-hole | + 4 corner mounting holes | `pole_mount_4_holes.stl` |
| Full | + chamfer + fillet | `pole_mount_final.stl` |

**Specifications:**
- Plate: 4" × 3" × 0.25"
- Socket: 1.25" OD, 0.75" ID, 1.5" tall
- Wall thickness: 0.25"
- Mounting holes: 0.25" dia (#8 screw), 0.5" from edges
- Chamfer: 0.1" on socket top rim
- Fillet: 0.15" on plate outer edges

#### API Extension: Edge-Specific Operations

**Problem:** Existing `apply_fillet` and `apply_chamfer` use predefined edge selectors (`interior_bracket`, `top_outer`) that don't match pole mount geometry.

**Solution:** Added new commands that accept specific edge tokens:

**New Commands:**
- `apply_fillet_to_edges(body_token, edge_tokens, radius_cm)`
- `apply_chamfer_to_edges(body_token, edge_tokens, distance_cm)`

**Files Modified:**
- `fusion_addin/ops/live_ops.py` - Added `apply_fillet_to_edges()` and `apply_chamfer_to_edges()` to `FusionApiAdapter`
- `fusion_addin/ops/live_ops.py` - Added handler functions and registry entries
- `mcp_server/primitives/core.py` - Added mixin methods

**Usage Pattern:**
```python
# Get edges from body
edges = server.get_body_edges({"body_token": body_token})["result"]["body_edges"]

# Filter edges programmatically
socket_top_edges = [e for e in edges if is_at_socket_top(e)]

# Apply chamfer to specific edges
server.apply_chamfer_to_edges(
    body_token=body_token,
    edge_tokens=[e["token"] for e in socket_top_edges],
    distance_cm=0.254  # 0.1"
)
```

#### Technical Findings

1. **Edge Selection Strategy:**
   - Socket top edges: Circular edges at `z = plate_thickness + socket_height`
   - Plate outer edges: Linear edges spanning `z = 0` to `z = plate_thickness` on perimeter

2. **Edge Token Lifecycle:**
   - Edge tokens remain valid after geometry modifications
   - Must re-query edges after each fillet/chamfer operation for subsequent operations

3. **Workflow vs Manual:**
   - `tube_mounting_plate` workflow has strict geometric validation that failed
   - Manual step-by-step construction succeeded
   - Edge-specific operations required for non-standard geometry

#### Files Created During Session

- `make_pole_mount.py` - Initial attempt with workflow
- `make_pole_mount_manual.py` - Manual construction (successful)
- `make_pole_mount_with_holes.py` - 2-hole variant
- `make_pole_mount_4_holes.py` - 4-hole variant
- `make_pole_mount_chamfer_fillet.py` - Full variant
- `make_pole_mount_final.py` - Production version with edge selection
- `debug_edges.py` - Edge analysis tool

#### Verification

- All parts generated successfully in Fusion 360
- STL files exported and copied to Desktop
- Chamfer and fillet applied using new edge-specific API

#### Next Steps

1. Consider adding higher-level edge selectors for common patterns:
   - `socket_top` - Chamfer socket openings
   - `plate_perimeter` - Fillet plate edges
   
2. Document edge selection patterns in workflow guide

3. Potential workflow addition: `create_pole_mount` with parameterized socket/plate

---

---

## 2026-06-13 — Phase 1 Selector Foundations: first vertical slice landed

Implemented and merged to `master` (fast-forward, 8 commits, tip `0cf259b`) the first slice of the geometry-foundations pivot.

### What shipped
- `mcp_server/selectors.py` — pure, dependency-free deterministic selector layer:
  `validate_descriptor`, `SelectionTrace` (diagnostic only), `resolve` with fail-closed
  cardinality guards (`expect: one|many`), `SelectorAmbiguityError`. v1 vocabulary:
  face `normal_axis` / `largest_planar`, edge `geometry_type` / `longest`.
- `resolve_selector` command registered in both `fusion_addin/ops/mock_ops.py` and
  `live_ops.py` (thin delegation; live fetches list-shaped faces/edges from the adapter,
  mock unwraps the dict form). Live wiring verified to mirror the `get_body_faces`
  registration exactly.
- `find_face` (`mcp_server/primitives/core.py`) retrofitted off the bounding-box `max()`
  heuristic onto the selector path; now returns `selection_trace` (replacing `face_info`).
  The six directional selectors map to `normal_axis` axis descriptors.

### Evidence
- +27 new passing tests (`tests/test_selectors.py`, `tests/test_find_face.py`,
  additions to `tests/test_addin_workflows.py`); `test_freeform.py` key-rename.
- Regression: 35 pre-existing failures before → 35 after, identical set (enclosure
  `NotImplementedError` migration stubs + one pre-existing freeform session-state bug).
  Zero new failures. Passing count 438 → 465.
- Every task passed two-stage review (spec + quality); final holistic review: ready to merge.

### Still open
- **Task 8 (live Fusion smoke) NOT run** — needs a running Fusion session:
  `python scripts/fusion_smoke_test.py --workflow spacer`. Confirm `find_face` stages emit
  a `selection_trace` with `status: resolved` against real B-Rep.
- Deferred follow-ups (next slices): instrument `apply_chamfer`'s `"interior_bracket"`
  heuristic + `apply_fillet`/`apply_shell`; attribute pinning (descriptor `pin` field is
  reserved/carried but unused); `find_face` failure-path integration test.
- **Strategic fork still undecided:** keep owning the bridge/add-in vs. reposition
  ParamAItric as the reliability layer on top of the official Autodesk Fusion MCP connector
  (shipped 2026-04-28). See memory + RESEARCH_TRACKS.

Plan: `docs/superpowers/plans/2026-06-13-selector-foundations-phase1.md`

## 2026-06-13 — Strategic fork resolved: keep owning the bridge, reframe as the reliability layer

Decision made on the open fork from the entry above (official Autodesk Fusion MCP connector,
shipped 2026-04-28, reportedly works poorly).

**Decision:** Keep owning the bridge/add-in for now. Do **not** reposition onto the official
connector yet. Reframe ParamAItric's identity away from "an MCP bridge to Fusion" (commoditized)
toward "the reliability / selector / verification layer" — the add-in is just the current, and
currently necessary, execution substrate for that layer.

**Why:**
- Deterministic resolution requires add-in-side live B-Rep topology (faces with
  normals/areas, edges with types/lengths). That data only exists inside Fusion. The official
  connector shows no stable, queryable topology surface `resolve()` could consume, so
  repositioning today would surrender the exact execution boundary the selector thesis depends
  on — and import the instability of a surface we don't control.
- The transport is commoditized; the value layer (selectors, `SelectionTrace`, fail-closed
  cardinality guards, verification tiers) is not. Defend the value layer, not the dumb pipe.
- The Phase-1 design already made this cheap to defer: `selectors.py` is pure/transport-agnostic
  and the only execution coupling is the `resolve_selector` registration in `mock_ops`/`live_ops`.
  Porting onto the connector later is one new adapter, if it earns it.

**What flips the decision:** the day the official connector exposes a stable, enumerable topology
surface (faces-with-normals/areas, edges-with-types/lengths) that `resolve()` can run against.
Then the add-in becomes redundant transport and we add one more `resolve_selector` adapter.

**Standing principle going forward:** future selector/verification work targets the pure layer
and our own `live_ops`; keep `selectors.py` transport-agnostic; treat the official connector as a
future adapter target, not a dependency. Monitor it; don't build on it.

## 2026-06-14 — Fuzzy-intent workflow discovery (recommend_workflow) landed

Built the discovery design (`docs/superpowers/specs/2026-06-13-fuzzy-intent-workflow-discovery-design.md`,
Approach C) test-first. This pulls a slice of roadmap Phase 3 forward (a deliberate call — Phase 1
geometry foundations are not fully closed; see that spec's sequencing note).

### What shipped
- `mcp_server/discovery.py` — pure, Fusion-free, deterministic discovery layer mirroring
  `selectors.py`: `WorkflowCard` (name/family/summary/use_when/example_params/not_for), a seeded
  `CARDS` table (8 cards across flat_parts, cylindrical, brackets, clamps), and
  `recommend(intent, constraints, *, limit)` — weighted use_when overlap scoring, categorical
  `family` constraint as a hard filter, fail-closed `no_confident_match` with a `families`
  fallback, and a `match_trace` diagnostic (the discovery analogue of `SelectionTrace`).
- `recommend_workflow` MCP tool: `ToolSpec` in `tool_specs.py` STATUS_TOOLS + a pure
  `recommend_workflow(payload)` method on `PrimitiveMixin` (`primitives/core.py`) that never calls
  the bridge.
- `BEST_PRACTICES.md`: a "Matching fuzzy requests to workflows (discovery)" section anchoring the
  propose-then-confirm contract so any host model follows it.

### Evidence
- +16 passing tests (`tests/test_discovery.py`): ranking, synonym canonicalization (surface->wall,
  bore->hole), constraints-as-filters, fail-closed no-match + families, card<->registry
  consistency, example_params schema-validity (each seeded card's dims validate via the workflow's
  `*Input.from_payload` with an injected allowlisted output_path), and the server method + tool
  registration.
- Regression: 35 pre-existing failures before -> 35 after (identical set). Zero new failures.
  Passing count 469 -> 485.

### Notes / deltas from the spec
- Deliberately did NOT collapse pipe/tube/conduit as synonyms (the spec floated it): `tube` and
  `cylinder` are their own workflows, so collapsing would make those cards fight the clamp card.
  Only unambiguous synonyms applied.
- `example_params` carry only meaningful dimensions (no output_path/sketch names); the schema-valid
  test injects a throwaway allowlisted output_path. Units are `_cm` (the schema convention), not
  the `_mm` used in the spec's illustrative example.
- v1 seeds 8 of 38 registered workflows; remaining workflows are intentionally un-carded and the
  gap is tracked by the consistency test, not silently assumed.

### Could not run
- The user cannot test on a machine with Fusion 360. Not a blocker here: this entire layer is pure
  MCP-side and fully covered by the offline pytest suite. No live smoke applies.

Spec: `docs/superpowers/specs/2026-06-13-fuzzy-intent-workflow-discovery-design.md`

## 2026-06-18 — Offline cleanup before live Fusion validation

Completed the non-Fusion cleanup that could be verified locally before moving the remaining
selector evidence work to the Fusion 360 machine.

### What changed
- Freeform session state now records mutation commands through the manager path, remembers
  `list_profiles` observations, and blocks a second mutation until commit verification advances the
  session state.
- Workflow bridge responses now normalize legacy/synthetic `{"result": ...}` interceptor shapes
  into successful workflow responses before checking the `ok` flag. This keeps older tests and
  hand-written bridge shims compatible with the current workflow failure classifier.
- Revolve workflow verification now accepts the live half-profile width that Fusion can report for
  revolve sketches, while still validating final body axis and dimensions.
- Added `docs/FUSION_HARDWARE_TASKLIST.md` as the compact checklist for the machine that can run
  Fusion 360.

### Evidence
- `python3 -m pytest tests/test_freeform.py tests/test_workflow.py::test_workflow_failure_includes_partial_state_on_dirty_scene tests/test_workflow.py::test_create_revolve_accepts_live_half_profile_width tests/test_workflow.py::test_create_revolve_fails_when_revolve_result_is_invalid -q`
  passes.
- Full offline baseline after cleanup: `508 passed, 20 failed, 1 warning`.
- Remaining failures are unmigrated enclosure and specialty workflow stubs:
  `create_open_box_body`, `create_simple_enclosure`, `create_lid_for_box`,
  `create_box_with_lid`, `create_flush_lid_enclosure_pair`,
  `create_project_box_with_standoffs`, `create_snap_fit_enclosure`,
  `create_telescoping_containers`, `create_strut_channel_bracket`,
  `create_ratchet_wheel`, and `create_wire_clamp`.

### Still needs Fusion 360 hardware
- Live selector evidence for `find_face` against real B-Rep topology.
- Live operation trace evidence for shell, fillet, and chamfer.
- Live smoke tests and discovery UX checks from `docs/FUSION_HARDWARE_TASKLIST.md`.

## 2026-07-10 — Live Fusion validation session (hardware tasklist complete)

Machine with Fusion 360, checkout `a2fb12c` plus the staged workflow/selector work from the
previous offline sessions.

### Environment repair before anything ran
- Fusion was loading a **stale March 7 physical copy** of the add-in from
  `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` (two copies: `FusionAIBridge` and
  `fusion_addin`). Neither could work: their entrypoints resolve the repo root to the AddIns
  folder, where `mcp_server` does not exist, so `Run` died on import before binding the port.
  The failure is silent from the outside — no listener on 8123, no obvious error.
- Fix: moved both copies to `AddIns_stale_backup_2026-07-10/` and registered
  `C:\Github\paramAItric\fusion_addin` directly via green **+** per INSTALL.md, with
  **Run on Startup** enabled so the bridge comes up with Fusion from now on.
- Note: the old handoff doc pointed at port 8000; the bridge listens on **8123**.

### Live workflow smokes (all pass, STLs in manual_test_output/)
- `spacer` → `live_smoke_spacer.stl`
- `bracket` → `live_smoke_bracket.stl`
- `triangular_bracket` → first live validation: 8 stages, body_count=1, dims 2.00x1.00x0.50.
  `draw_triangle` primitive confirmed against real Fusion.
- `l_bracket_with_gusset` → first live validation: 15 stages, body_count=1, dims 5.00x4.00x0.40,
  gusset 1.50 cm. Confirms `draw_triangle` + `combine_bodies` join into a single body live.
- `pipe_clamp_half` (discovery confirmation build, pipe diameter tweaked 2.5 → 3.0 cm)
  → `live_smoke_pipe_clamp_half.stl`.

### Discovery UX check (section 4)
- "I need something to hold a pipe to a wall" → `pipe_clamp_half` top candidate, score 0.75,
  matched_on [hold, pipe, wall], honest `not_for` list, realistic example_params. PASS.
- "I need a herringbone gear" → `no_confident_match` with families
  [brackets, clamps, cylindrical, flat_parts], no forced candidate. PASS.
- Friction notes: `recommend_workflow` takes `intent`, not `description` (error message is clear,
  but hosts guessing the key will hit it); `l_bracket_with_gusset` smoke requires five explicit
  dimension flags with no defaults.

### valve_handle investigation (new WIP from plans/priority_3_utility_parts.md)
- `create_valve_handle` fails on BOTH adapters, differently:
  - Live: `draw_polygon` was never added to `live_ops.py` → "Unknown command: draw_polygon" at
    `draw_socket_profile`. The primitive exists only in `mock_ops.py` and `primitives/core.py`.
  - Mock: `combine_bodies` requires same-plane bodies; the design combines an XY socket with a
    YZ lever → fails at `combine_bodies`.
- Also blocked on the still-unconfirmed YZ-plane extrude convention (see strut bracket notes).
- Both valve tests marked strict xfail with reasons; finishing the feature needs a live
  `draw_polygon` op, cross-plane mock combine, and YZ-plane validation.
- Follow-up idea: a mock/live registry parity test would have caught the `draw_polygon` drift
  at commit time.

### Test suite
- Marked the 5 remaining unmigrated-stub tests (`slotted_flex_panel`, `snap_fit_enclosure`,
  `telescoping_containers`, `flush_lid_enclosure_pair` x2) and the 2 valve_handle tests as
  `strict=True` xfail so the suite is green again and stale markers self-report when the
  workflows land.
- Result: **531 passed, 7 xfailed** (was 531 passed / 7 failed).

## 2026-07-11 — valve_handle complete: YZ convention solved, draw_polygon live, workflow geometry redesigned

Session goal: clear all three valve_handle blockers from the 2026-07-10 entry. All cleared;
`valve_handle` is now live-validated end-to-end with verified geometry.

### YZ plane convention (live-confirmed via asymmetric probe)
- Probe: 3×1 rectangle (draw_rectangle anchors at sketch origin), extrude 0.5 — three distinct
  dims let the world bbox identify every axis mapping including signs.
- Result: **sketch-X → -worldZ (negated), sketch-Y → +worldY, extrude fires +X;
  `offset_cm` moves the plane in +X.**
- Unifying rule across all planes: extrude always fires along the plane's positive world normal
  (XY→+Z, XZ→+Y, YZ→+X); exactly one sketch axis is negated per non-XY plane (right-handedness).
- Implication: the old strut-bracket "did not intersect" failures were not a convention problem;
  `scripts/validate_mcmaster_bracket.py` deserves a re-run with the confirmed mapping.

### draw_polygon in live_ops (all five layers)
- Added protocol stub, FusionApiAdapter implementation (vertex at angle 0, circumradius),
  registry entry, module-level wrapper, and RecordingFakeFusionAdapter support.
- Live-validated: hex prism R=1.0 h=0.5 → volume 1.2990 cm³ vs analytic (3√3/2)R²h = 1.2990,
  delta 0.0000. Volume is the strongest cheap check — bbox can't distinguish hexagon from circle.
- Fidelity fix found during validation: recorded profile bounds must be the TRUE polygon bbox
  (hex = 2R × √3R, not 2R × 2R) — live Fusion reports the true bbox in list_profiles, so mock
  and workflow expectations now compute it the same way.

### Registry parity test (tests/test_registry_parity.py)
- New test diffs mock vs live command registries; drift is now a same-day suite failure.
- Immediately caught a SECOND drift in the opposite direction: `apply_fillet_to_edges` and
  `apply_chamfer_to_edges` were live-only (used by examples/pole_mount). Added mock
  implementations with edge-token validation.

### Mock cross-plane combine_bodies
- Mock now unions world-axis extents (via the live-confirmed plane mappings) and expresses the
  result back in the target body's plane frame. Same-plane path byte-identical (5 workflows
  depend on its arithmetic).

### valve_handle geometry redesign (the big one)
- First live run exposed that "stages passed" ≠ "geometry right": the exported STL was 684 bytes
  = 12 triangles = a bare cuboid. Evidence via list_design_bodies: TWO bodies after a
  "successful" combine — the old design extruded the socket profile as a solid plug (a replica
  of the stem, not a handle) and placed the YZ lever at z ∈ [-6, -0.6], disjoint below the
  socket. The set-screw hole had pierced the lever (two sign bugs cancelling).
- Redesign, all on validated planes (no YZ needed): hub cylinder on XY (radius = socket
  circumradius + wall, height = stem_depth + 0.3 cap) → lever bar on offset XY sketch at the
  top of the hub, overlapping the hub axis → same-plane combine → socket cavity cut upward from
  the base plane via draw_polygon (blind socket, cap intact) → optional set-screw cross-hole on
  XZ at mid-cavity height (sign fixed: sketch-Y = -stem_depth/2 → world z = +stem_depth/2).
- Added `_verify_valve_handle_body_count` after combine and after each cut — the split/disjoint
  detector this bug demanded. Workflow registry stages updated to match.
- Live result (square socket, stem 0.8): body_count 1, bbox x[-0.901, 6.0] y[±0.901] z[0, 1.8]
  exactly matching design math, volume 9.709 cm³ vs analytic ≈9.71 (hub + lever − overlap −
  cavity − screw bore). Fillets now genuinely apply: the hollow geometry has interior cavity
  edges, which is what the live fillet selector needs.
- STLs: live_valve_handle_hex.stl (24 KB), live_valve_handle_square.stl (146 KB) in
  manual_test_output/. Runner: `scripts/validate_valve_handle_live.py` (supports
  --stem-width-cm etc. for measured dimensions later).

### Real-part status (docs/valve_specs/)
- Both Chemtrol and MA611AF specs still read `stem_across_flats_cm: 0.0  # MEASURE THIS`.
  The printable handle waits on caliper measurements; the pipeline is proven with test dims.
  Per the MA611AF post-mortem: print a test socket before the full handle.

### Test suite
- Valve xfail markers removed (strict markers flagged XPASS exactly as designed).
- Result: **534 passed, 5 xfailed** (remaining 5 = unmigrated stubs).

## 2026-07-11 (later) — friction fix: mock-to-live auto-upgrade

Symptom discovered during a demo rebuild: /health reported `mode: mock` even though Fusion was
open. Root cause: with "Run on Startup" the add-in boots on Fusion's home screen, where
`app.activeProduct` is None, so `bootstrap_addin` falls back to the mock adapter — and the mode
was decided exactly once, at startup. "Run on Startup" therefore always landed in mock, quietly
defeating its purpose; every Fusion launch needed a manual Stop/Run with a design focused.

Fix (three layers):
- `CommandDispatcher.try_upgrade_to_live()` — re-runs the bootstrap and swaps the registry,
  dispatch driver (inline → main-thread custom event), and design state in place. Driver swaps
  before registry so a mismatch never executes a live op off the main thread. Mock-era design
  state is discarded (its tokens mean nothing to live Fusion). Refuses to touch dispatchers
  built with an explicit registry_builder.
- `FusionAIBridge` registers a `documentActivated` watcher when the bridge boots in mock mode
  inside Fusion; the handler (which fires on the main thread) calls the upgrade and is a cheap
  no-op once live. Handler refs pinned at module scope (Fusion GCs unreferenced handlers);
  removed in stop().
- `/health` now includes a hint while in mock mode explaining the auto-upgrade.

Tests: tests/test_dispatcher_live_upgrade.py simulates the home-screen boot with a two-phase
fake bootstrap (mock until `open_design()`, live after). Covers the swap, state reset,
idempotence, and the custom-registry refusal. Suite: **538 passed, 5 xfailed**.

Not yet live-verified (requires a Fusion restart to reproduce the home-screen boot); next
Fusion launch is the real test — /health should read live as soon as any design opens.

## 2026-07-11 — Stage 1 MCP schema fidelity and units

- Added generated host-facing schemas for every dataclass-backed tool input.
- All 34 advertised workflow tools expose explicit field types, required fields,
  defaults, common numeric bounds, enum values, and per-dimension unit metadata.
- Preserved the outer `payload` object because the existing MCP contract and tests
  pin that envelope; fields inside it are now precise instead of an opaque object.
- Added optional `units` values `cm`, `mm`, and `in`. Numeric fields ending in
  `_cm` are copied and converted to centimeters before the existing validators and
  workflows execute; invalid units return the canonical validation-error envelope.
- Added precise manual schemas for discovery and inspection tools whose validation
  is not backed by a dataclass.
- Verification: schema inspection covered all 34 workflow tools; unit conversion
  and normalized invalid-unit behavior were exercised directly; full suite result
  was **568 passed, 5 xfailed**.

## 2026-07-11 — Stage 1 capability-aware health

- Extended the existing `/health` response additively with `backend`, `version`,
  `capabilities`, and `workflow_count`; all legacy fields and the mock-mode hint
  remain intact.
- Capabilities come from the active operation registry and remain sorted and
  deterministic. Workflow count is derived from the returned catalog rather than
  maintained separately.
- Added a shared runtime identity for the current Autodesk Fusion backend and the
  ParamAItric bridge version.
- Reframed host-facing health and build prompts around the configured CAD backend,
  while leaving current Fusion-specific onboarding and installation guidance honest.
- Parallel read-only audits mapped the compatibility contract, capability sources,
  and backend-specific language; an independent diff review found no blockers.
- Verification: direct HTTP health exercised backend/version/mode, all 28 active
  command capabilities, and all 34 workflows; focused suite **29 passed**; full
  suite **568 passed, 5 xfailed**.

## 2026-07-11 - Stage 1 runtime-profile parsing

- Added the seven canonical runtime profiles under `local_app/profiles/`, covering
  the Claude/Fusion baseline, local CUDA/Vulkan Fusion, remote ROCm/Vulkan Fusion,
  and native ROCm/Vulkan FreeCAD configurations.
- Added an immutable runtime-profile parser with deterministic discovery, safe
  profile-name handling, exact field validation, provider/backend/tool-profile
  checks, HTTP endpoint validation, `~` expansion for export directories, and
  contextual errors for missing or malformed JSON.
- Kept runtime choices outside workflow implementations and allowed callers to
  inject a profile directory so the same loader can serve tests and the upcoming
  `paramaitric doctor --profile <name>` command.
- Updated setup guidance now that the profile files exist; host-side profile
  selection remains a later integration step.
- Verification: focused runtime-profile suite **8 passed**; full suite
  **576 passed, 5 xfailed**.

## 2026-07-11 — Stage 1 paramaitric doctor command

- Implemented the `paramaitric doctor --profile <name>` subcommand inside the MCP server entrypoint (`mcp_server.mcp_entrypoint`).
- Created a self-contained diagnostic module `mcp_server/doctor.py` that verifies:
  1. Python environment (version >= 3.11).
  2. Package imports (verifying critical dependencies like `mcp` and `pydantic` can be imported).
  3. MCP startup (validating the server entrypoint executes successfully in a subprocess).
  4. Lemonade API & model availability (checking that local endpoints are reachable and the specified model is loaded).
  5. CAD backend reachability (probing the cad_endpoint).
  6. Bridge authorization status.
  7. Export directory write permissions.
  8. One non-mutating health call (retrieving mode, backend, and workflow counts).
- Intercepted the CLI `doctor` argument directly in `main()` so that running `paramaitric doctor --profile <name>` runs the doctor diagnostic pipeline.
- Verification: Added comprehensive unit tests in `tests/test_doctor.py` (12 tests passing); validated CLI locally against the `claude-fusion` and `lemonade-cuda-fusion` profiles; full suite **588 passed, 5 xfailed**.

