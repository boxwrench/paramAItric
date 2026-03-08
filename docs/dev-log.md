# ParamAItric Dev Log

## 2026-03-08

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
