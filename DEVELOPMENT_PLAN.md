# ParamAItric Development Plan

## Status

The initial code scaffold exists, and the first real live Fusion vertical slice for `spacer` has now been validated end-to-end through STL export. The next implementation work should expand that slice carefully, harden error handling, and extend the workflow catalog without widening scope prematurely.

## Pass 1: Core modeling

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
- `list_profiles`
- `extrude_profile`
- `get_scene_info`
- `export_stl`
- `create_spacer`

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

- Add structured timeout and cancellation behavior around bridge requests and long-running Fusion operations.
- Wrap bridge failures in `mcp_server.server.create_spacer()` into `WorkflowFailure` so callers always get structured partial-state errors.
- Make `BridgeClient` timeouts configurable instead of hardcoding a single request timeout.
- Replace brittle mock profile token parsing in `fusion_addin/ops/mock_ops.py` with a delimiter-safe token format or explicit structured mapping.
- Stop rebuilding a fresh registry in `mock_ops.get_workflow_catalog()` and use the injected workflow registry consistently.
- Revisit live profile caching so cached transient profile objects are minimized or replaced with safer re-resolution behavior after timeline changes.
- Add a second real-Fusion smoke path on `xz` or `yz` to validate plane-aware reporting outside the narrow XY case.
- Start the first `bracket` live slice using the same staged validation contract as `spacer`.
- Extend the smoke test script and live validation to cover `two_hole_mounting_bracket` end-to-end.

## Test backlog

- Add adversarial concurrency tests around dispatcher queuing and repeated bridge submissions.
- Add end-to-end error propagation tests that cover operation failure through dispatcher, HTTP bridge, bridge client, and MCP workflow layers.
- ~~Add explicit security tests for path traversal and allowlist enforcement in both mock and live export paths.~~ Done: `test_export_path_rejects_paths_outside_allowed_roots` covers export path allowlist enforcement.
- Add timeout and hang tests for the bridge and workflow layers.
- Remove monkeypatch-style test mutations that can leak state across tests, especially in `tests/test_workflow.py`.
