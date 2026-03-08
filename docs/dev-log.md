# ParamAItric Dev Log

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
