# ParamAItric Development Plan

## Documentation contract

- Treat this document as the current high-level roadmap and status doc.
- Treat `docs/dev-log.md` as the running execution log.
- Update these two docs only when the validated state, current priorities, or completed work materially changes.
- Do not create a new backlog or status-tracking document unless these existing docs are clearly inadequate.

## Status

Status refresh 2026-03-08:

- Revalidated in the current shell environment after the repo-local temp-path harness fix.
- The full suite now passes at `198 passed`, with the same existing `TestFusionApiAdapter` collection warning.
- The full suite now passes at `207 passed`, with the same existing `TestFusionApiAdapter` collection warning.
- Workflow bridge/runtime failures are now wrapped into structured `WorkflowFailure` payloads with stage and partial-progress context.
- Bridge request timeouts now surface distinctly through the workflow layer as structured `WorkflowFailure(classification="timeout")` payloads with prior-stage context.
- Bridge request cancellations and aborted requests now surface distinctly through the workflow layer as structured `WorkflowFailure(classification="cancelled")` payloads with prior-stage context.
- Pending bridge commands can now be cancelled before execution through the Fusion-side dispatcher and HTTP bridge, so queued work no longer has to run once it is no longer wanted.
- The live smoke runner now verifies hole-profile topology for mounting workflows, and `two_hole_mounting_bracket` has been revalidated end to end in real Fusion with the strengthened smoke path.
- End-to-end error propagation is now covered for all workflow types across all stages, including a real-wire test that exercises the genuine HTTP 400 → RuntimeError → WorkflowFailure chain.
- `plate_with_hole` is registered as the first cut-extrusion workflow; `operation` parameter validation is in place at the schema, mock-ops, and live_ops layers; cut contract tests are passing.
- `create_plate_with_hole` is now implemented in the MCP workflow server with the same staged contract as the current bracket family: base body verify, second sketch, cut extrude, second verify, export.
- `live_ops.extrude_profile` now handles `operation="cut"` via `CutFeatureOperation`; `RecordingFakeFusionAdapter` updated to match.
- `plate_with_hole` is now validated end to end in real Fusion through STL export after reloading the add-in from the current repo state.
- `filleted_bracket` now has live `apply_fillet` support in `fusion_addin/ops/live_ops.py`, live-registry coverage, smoke-path coverage, and real Fusion end-to-end validation through STL export.
- The smoke runner now fails fast when `/health` does not expose the requested workflow, so stale live add-in reload problems are diagnosed before any modeling command is issued.

Seven workflows are registered: `spacer`, `bracket` (xy and xz), `mounting_bracket` (one hole, xy), `two_hole_mounting_bracket` (two holes, xy), `simple_enclosure` (mock only), `plate_with_hole` (live-validated cut workflow), and `filleted_bracket` (live-validated fillet workflow). The test suite covers 198 tests across mock ops, dispatcher concurrency, export path security, schema validation, workflow stage ordering, full-stack error propagation, cut extrusion contract, fillet contract, live-registry fillet routing, smoke-script routing, stale-catalog smoke guarding, and MCP-side cut-workflow orchestration — all passing without a live Fusion instance.

## Pass 1: Core modeling

Validated test coverage refresh: the current full-suite count is `177 passed`, which supersedes older references to lower counts elsewhere in this document.

Goal: harden and extend the validated chain from AI tool call to Fusion geometry to STL export.

Required deliverables:

- Fusion add-in skeleton with `run(context)` and `stop(context)`
- loopback-only HTTP bridge inside the add-in
- queue plus `CustomEvent` dispatch to the Fusion main thread
- MCP server with a minimal typed tool surface
- raw CAD primitives for sketch, profile, extrude/cut, and export flows
- a minimal template layer, with `spacer` as the first golden-path workflow
- basic smoke tests for bridge health and the first modeling flow

Pass 1 tool surface:

- `new_design`
- `create_sketch`
- `draw_rectangle`
- `draw_l_bracket_profile`
- `draw_circle`
- `list_profiles`
- `extrude_profile`
- `get_scene_info`
- `export_stl`
- `get_workflow_catalog`
- `create_spacer`
- `create_bracket`
- `create_mounting_bracket`
- `create_two_hole_mounting_bracket`
- `create_simple_enclosure`

Pass 1 should be optimized for mechanical basics rather than general CAD breadth. The first reliable workflows should cover plates, brackets, spacers, simple enclosures, and basic hole or cutout patterns.

Minimum first milestone:

1. Start Fusion with the add-in loaded.
2. Reach the MCP server from a local AI host.
3. Create a sketch.
4. Draw a closed profile.
5. Resolve the intended profile deterministically.
6. Extrude that profile into a solid body.
7. Verify body count and expected dimensions.
8. Export the part to STL.

Representative use cases:

- spacer
- bracket
- simple enclosure
- cylindrical adapter

Pass 1 workflow rules:

- one modeling milestone at a time
- verify after every major step
- do not rebuild valid geometry unless verification proves it is wrong
- stop cleanly on failed verification
- preserve partial valid state for human-directed correction
- treat each successful golden path as a reusable base for the next workflow rather than jumping to larger one-shot tasks

## Pass 2: Workflow automation

Goal: automate repetitive non-creative CAD tasks around an existing design.

Candidate tool surface:

- `convert_bodies_to_components`
- `set_physical_material`
- `set_appearance`
- `rename_entities`
- `list_entities`
- `export_step`

Expected outcomes:

- easier design cleanup
- faster export workflows
- better support for fabrication prep

Pass 2 should still stay focused on functional-print and fabrication utility work. Advanced creative geometry should not be pulled forward unless benchmark results show a concrete need that supports those workflows.

## Pass 3: Advanced and creative modeling

Goal: expand into broader geometry generation once the core path is reliable.

Candidate tool surface:

- `draw_spline`
- `loft_profiles`
- `revolve_profile`
- `pattern_features`
- `combine_bodies`
- `create_offset_planes`

Expected outcomes:

- exploratory geometry generation
- design variation workflows
- controlled experimentation in Creative Mode

This pass is explicitly later-stage work, not a requirement for the initial product thesis.

## Acceptance criteria by stage

Pass 1 exit target: a simple part can be generated and exported end-to-end without manual CAD intervention between tool calls across at least one validated live workflow and one follow-on workflow built from the same staged contract.

Pass 2 is complete when the system can reliably inspect, rename, prepare, and export an existing design.

Pass 3 is complete when advanced operations can be composed without undermining the reliability of Work Mode.

## Benchmark and evaluation loop

Before finalizing implementation details beyond the initial scaffold, use Faust with Gemini as a benchmark path to validate workflow assumptions. Treat Faust as the immediate utility path and reference implementation, not automatically as the product base.

Capture evaluation notes for each benchmark scenario:

- install and setup friction
- prompt quality needed to succeed
- tool-call reliability
- geometry correctness
- export success
- failure clarity and recoverability

Required benchmark cases:

- cube
- sphere
- bracket
- donut or torus-like part
- organic shape

For each case, record:

- prompt used
- tool sequence taken
- whether manual intervention was needed
- whether the final model is editable and dimensionally sane
- what failed, if anything
- whether the failure suggests a Faust limit, Gemini planning issue, or Fusion-side gap

## Implementation notes

- Build the smallest working path first.
- Keep Pass 1 tightly scoped even if later drafts describe broader capabilities.
- Treat Faust and other external repos as benchmark inputs, not as the product definition.
- Grow the workflow catalog by standardizing reliable stage sequences and composing from them.
- Treat the future code layout as:

```text
fusion_addin/
mcp_server/
tests/
docs/
  research/
```

## Near-term hardening backlog

These items are real follow-up work after the first successful live `spacer` smoke run:

- Update: workflow bridge-call failures are now wrapped into structured `WorkflowFailure` payloads with stage context and partial progress.
- Update: bridge request timeouts now surface distinctly through the workflow layer as `WorkflowFailure(classification="timeout")` with partial progress.
- Update: bridge request cancellations and aborted requests now surface distinctly through the workflow layer as `WorkflowFailure(classification="cancelled")` with partial progress.
- Add cancellation behavior around already-started long-running Fusion operations inside the Fusion add-in itself.
- ~~Make `BridgeClient` timeouts configurable instead of hardcoding a single request timeout.~~ Done: `health_timeout` and `command_timeout` are now constructor parameters.
- Replace brittle mock profile token parsing in `fusion_addin/ops/mock_ops.py` with a delimiter-safe token format or explicit structured mapping.
- ~~Stop rebuilding a fresh registry in `mock_ops.get_workflow_catalog()` and use the injected workflow registry consistently.~~ Done: `get_workflow_catalog` now closes over the already-built registry.
- Revisit live profile caching so cached transient profile objects are minimized or replaced with safer re-resolution behavior after timeline changes.
- Add a second real-Fusion smoke path on `xz` or `yz` to validate plane-aware reporting outside the narrow XY case.
- ~~Start the first `bracket` live slice using the same staged validation contract as `spacer`.~~ Done: bracket and mounting_bracket both validated live on xy; bracket also validated on xz.
- ~~Extend the smoke test script and live validation to cover `two_hole_mounting_bracket` end-to-end.~~ Done: the smoke runner now validates mounting-workflow hole profiles before extrusion, and a real Fusion two-hole smoke run passed on `xy`.

## Test backlog

- Update: bridge-to-workflow error propagation coverage is now in place for structured `WorkflowFailure` wrapping and partial-state reporting.
- Update: bridge and workflow timeout regression coverage is now in place for hung `/health`, hung `/command`, and timeout propagation into workflow failures.
- Update: bridge and workflow cancellation regression coverage is now in place for aborted `/health` and `/command` requests plus propagation into workflow failures.
- Update: dispatcher and HTTP bridge queue-cancellation regression coverage is now in place for pending requests cancelled before execution.
- ~~Add adversarial concurrency tests around dispatcher queuing and repeated bridge submissions.~~ Done: `test_dispatcher.py` covers Barrier-coordinated concurrent submissions, error-does-not-block-subsequent-commands, and repeated-submission state leak checks.
- ~~Add adversarial input validation tests for all mock ops commands.~~ Done: `test_input_validation.py` covers missing args, wrong types, zero/negative/NaN/inf values, nonexistent tokens.
- ~~Add end-to-end error propagation tests that cover operation failure through dispatcher, HTTP bridge, bridge client, and MCP workflow layers.~~ Done: `test_error_propagation.py` covers bridge errors and timeouts at every workflow stage for all five registered workflow types, plus one real-wire test that exercises the genuine HTTP 400 → RuntimeError → WorkflowFailure chain without Python-level injection.
- ~~Add explicit security tests for path traversal and allowlist enforcement in both mock and live export paths.~~ Done: `test_export_security.py` covers both schema layer and mock-ops layer allowlist enforcement.
- ~~Add workflow stage ordering enforcement tests.~~ Done: `test_workflow_stages.py` covers full-sequence, out-of-order, unknown-stage, and duplicate-stage cases for all 5 registered workflows (plate_with_hole covered separately in `test_cut_extrusion.py`).
- ~~Add operation parameter validation and cut extrusion contract tests.~~ Done: `_validate_extrude_operation()` in schemas.py, operation handling in mock_ops.py, and `test_cut_extrusion.py` covering schema validation, mock new_body/cut/invalid behavior, and plate_with_hole stage ordering.
- ~~Implement live_ops cut extrusion (Fusion API: `ExtrudeFeatureInput.operation = adsk.fusion.FeatureOperations.CutFeatureOperation`).~~ Done: `live_ops.extrude_profile` handles `operation="cut"` via `createInput`/`CutFeatureOperation`; `RecordingFakeFusionAdapter` and the extrude wrapper updated to match.
- ~~Validate the plate_with_hole workflow end-to-end in real Fusion through STL export once the live Fusion add-in is reloaded from the current repo state.~~ Done: real Fusion validation passed on March 9, 2026 after reloading the add-in from the current repo state; artifact written to `manual_test_output\live_smoke_plate_with_hole.stl`.
- ~~Validate the filleted_bracket workflow end-to-end in real Fusion through STL export once the live Fusion add-in is reloaded from the current repo state.~~ Done: real Fusion validation passed on March 9, 2026 after reloading the add-in from the current repo state; artifact written to `manual_test_output\live_smoke_filleted_bracket.stl`.
- ~~Add timeout and hang tests for the bridge and workflow layers.~~ Done: `test_bridge.py` and `test_workflow.py` cover hung bridge requests and structured workflow timeout propagation.
- ~~Remove monkeypatch-style test mutations that can leak state across tests, especially in `tests/test_workflow.py`.~~ Done: workflow failure-path tests now use an intercepting bridge client instead of mutating server methods in place.
