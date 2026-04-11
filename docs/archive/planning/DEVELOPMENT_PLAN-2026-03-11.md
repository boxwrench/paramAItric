# ParamAItric Development Plan

## Documentation contract

- Treat this document as the current high-level roadmap, workflow strategy, and status doc.
- Treat `docs/dev-log.md` as the running execution log.
- Treat `BEST_PRACTICES.md` as the living real-world-use reference for prompting, staging, inputs, verification defaults, and failure handling.
- Update these documents only when the validated state, current phase, or active priorities materially change.

## Current status

Status refresh 2026-03-11:

- Current pushed baseline: `aad76e9` (`feat: harden freeform flow and refresh docs`).
- Latest targeted validation rerun on March 11, 2026: `18 passed`.
  - `tests/test_freeform.py`
  - `tests/test_mcp_entrypoint.py`
  - `tests/test_telescoping_containers.py`
  - `tests/test_slotted_flex_panel.py`
  - `tests/test_ratchet_wheel.py`
  - `tests/test_wire_clamp.py`
  - `tests/test_snap_fit_enclosure.py`
- Full suite was not rerun in the March 11 sweep.
- The current product shape is a small catalog of dependable Fusion workflows, not broad "AI CAD."
- Validation, failure handling, and smoke coverage are now materially stronger than the earlier scaffold phase.
- MCP packaging is now in place, and the inspection lane includes body, face, and edge reporting.
- The repo now has two lanes:
  - structured deterministic workflows
  - guided freeform sessions
- The current surface is now 25 workflow definitions, 30 MCP tools, and a live-validated path across enclosure, cylindrical, revolve, handle-family, and clamp-family work.
- `shell`, `cylinder`, `tube`, and `revolve` are now implemented and live-validated through practical workflows, not just primitive coverage.

Recent freeform hardening already landed:

- stricter manifest discipline for `target_features` and `resolved_features`
- required `expected_body_count` for `commit_verification`
- optional body-count delta and volume-delta-sign assertions
- structured `verification_diff` returned from `commit_verification`
- replay-based `rollback_freeform_session`
- refreshed freeform playbook and checklist docs

Validated live workflows:

- `spacer`
- `cylinder`
- `tube`
- `revolve`
- `tapered_knob_blank`
- `flanged_bushing`
- `pipe_clamp_half`
- `t_handle_with_square_socket`
- `bracket` on `xy` and `xz`
- `mounting_bracket` on `xy`
- `two_hole_mounting_bracket` on `xy`
- `plate_with_hole`
- `two_hole_plate`
- `slotted_mount`
- `four_hole_mounting_plate`
- `slotted_mounting_plate`
- `counterbored_plate`
- `recessed_mount`
- `open_box_body`
- `lid_for_box`
- `filleted_bracket`
- `chamfered_bracket`
- `simple_enclosure`
- `box_with_lid`
- `tube_mounting_plate`

Recent reliability gains already landed:

- structured `WorkflowFailure` wrapping with stage and partial-progress context
- timeout classification
- cancelled-request classification
- pending-request cancellation through the dispatcher and HTTP bridge
- bridge-client request-id support and explicit `cancel()`
- cooperative cancellation for already-started commands that observe the cancellation context

## Current phase

ParamAItric is now in a validated workflow family plus use-and-fix phase.

The goal is no longer to expand the catalog for its own sake. The goal is to keep a small workflow family dependable enough for real mechanical part work, then let real usage expose the next missing slice.

The planning lens for those next slices is utility and maintenance parts. That means real replacement handles, adapter plates, covers, and brackets should drive workflow and test selection, while the core workflow engine stays generic.

The plate and bracket family has already done most of its early job. Those variants helped validate circles, slots, local placement, fillets, chamfers, counterbores, and joined-body composition. The marginal value of another narrow plate or bracket variant is now lower than the value of adding a new reusable operation that multiplies what the existing families can do.

Working rules for this phase:

- prefer finishing practical in-flight slices before broadening scope
- add only one new geometric or placement idea per workflow slice
- favor part families over isolated novelty geometry
- keep reliability, validation, and verification ahead of geometry breadth
- keep material and environment recommendations in prompts and docs unless they force a geometry contract change

## Current priorities

1. Keep the canon aligned with reality.
2. Build the real-world workflow library from curated utility-part families instead of adding abstract benchmark geometry.
3. Prioritize new operation multipliers over more plate or bracket variants that reuse the same proven vocabulary.
4. Keep the `tube`, `revolve`, and handle/socket lane honest with real templates instead of backsliding into benchmark-only geometry.
5. Treat guided freeform as a hardened exploratory lane, not a replacement for structured workflows.
6. Harden only the areas that protect real use, such as profile re-resolution safety, offset-sketch reliability, joined-body targeting, chamfer/feature selection, operation-specific cancellation checks, and trustable rollback behavior.

## What counts as progress

A workflow path is proven only when:

- the stage sequence is explicit
- verification points are explicit
- failure boundaries are explicit
- the result is repeatable enough to trust as a base for the next workflow

Useful growth comes from reusing proven stages such as:

- clean scene setup
- sketch creation
- deterministic profile selection
- single-body extrusion
- cut or fillet as a second-stage feature
- body-count and dimension verification
- export

## Workflow building blocks

The system should keep a catalog of validated workflows and validated sub-stages.

Current examples of how workflows build on each other:

- `spacer` is a foundation workflow
- bracket and mounting workflows reuse the same staged contract with one added idea at a time
- `plate_with_hole` proves a narrow second-sketch cut path
- `filleted_bracket` proves a narrow post-extrusion feature stage
- `chamfered_bracket` reuses that same post-extrusion stage shape with a different edge finish
- `simple_enclosure` should remain staged body first, hollowing or mating logic second, verification between them
- `tube_mounting_plate` shows that joined solids should stay true CAD bodies when the intended printed part is one part
- `t_handle_with_square_socket` shows that a real utility template should drive both geometry choice and fit-oriented verification

A domain template should usually be a composition and parameterization of those validated stages, not a new primitive. A valve handle, adapter plate, or equipment cover should only force a new primitive when the required geometry truly falls outside the existing staged vocabulary.

## Structured workflows and freeform composition

The current `create_[part]` workflows should be treated as reference implementations, not as the final shape of the product.

They already encode:

- safe stage ordering
- verification checkpoints
- profile-selection rules
- narrow repairs for known Fusion quirks
- failure boundaries that preserve partial progress

That makes them useful training data for the guided freeform lane. The repo should not skip straight from validated macros to unconstrained primitive composition, because that would throw away the product learning encoded in those staged paths.

The intended path is:

1. finish the missing high-value primitives and modifiers
2. keep strengthening inspection and verification as a self-check lane
3. expose guided primitive composition with mandatory verification checkpoints
4. keep the macros as known-good reference paths and fallback happy paths

## Target ladder

The next workflow targets should increase capability in a controlled order while staying reusable.

1. one or two more real enclosure-family templates that reuse `shell`
2. another fit-oriented cylindrical or handled-part template that builds on `tube`, `revolve`, and `combine_bodies`
3. lids, press-fit, or socket relationships where the real part requires them
4. guided freeform composition only after the current freeform lane proves repeatable against real parts and richer inspection primitives

Each target should add one new idea only:

- shelled enclosure variation or closure detail
- cylindrical or handled-part feature composition such as holes, chamfers, a joined sleeve, a through-bore, or a fit-critical socket
- fit and clearance relationships only when the chosen template requires them
- guided primitive composition only after inspection can act as a reliable self-check lane

## Near-term execution guidance

For the next slices:

- treat `shell`, `cylinder`, `tube`, `revolve`, and `combine_bodies` as the current reusable building blocks
- start new workflow-library slices from externally verifiable reference material with clear dimensions and constraints
- prefer the next missing operation multiplier over another plate or bracket variation that only rearranges known stages
- use enclosure, cylindrical, and handle/socket utility parts as the main proving ground before reopening broader template variety
- prefer utility and maintenance parts with measurable interfaces over abstract demo geometry
- keep live validation serial
- require schema validation before CAD ops
- require verification checkpoints after geometry creation
- record live evidence in `docs/dev-log.md`
- keep material, UV, chemical, and print-orientation guidance in docs or prompt context unless geometry needs an explicit new parameter

When combining features, prefer compositions such as:

- shell plus lid
- shell plus press-fit
- cylinder plus chamfer
- cylinder plus mounting holes
- cylinder plus through-bore
- plate plus joined cylindrical sleeve
- revolve plus fit-critical handle or socket geometry
- combined solids plus explicit socket or clearance verification

Real-part use should now be treated as a first-class input to planning. If a real part reveals a missing feature, prefer solving that gap over adding a broader standalone workflow.

Capture only the synthesized parameters, fit-critical relationships, and workflow-relevant geometry rules needed to reproduce a part family. Do not treat raw reference material as repo canon.

## Not current priorities

- broad "AI CAD" expansion
- decorative or organic geometry
- torus or other low-utility benchmark shapes
- third-party runtime dependencies
- new roadmap or backlog docs outside the existing canon
- a hard-coded material recommendation engine inside the MCP server
- angled sketch planes before the axis-aligned workflow families are saturated
- threading, where real FDM workflows usually prefer inserts or post-print tapping
- component or assembly conversion before STEP or assembly output becomes a real requirement
- linear or circular pattern features before real templates force them

## Active hardening backlog

- Revisit live profile caching and favor safer re-resolution behavior after timeline changes.
- Revisit offset-sketch handling only where real box-family use exposes failures.
- Add operation-specific cancellation checks only where a live step can run long enough to benefit from cooperative aborts.
- Add another live smoke path outside the narrow XY default only when it supports a practical workflow or catches a real regression.
- Deliberately revalidate any `internal/` harness that becomes operationally important before trusting it under the stricter March 11 freeform rules.

## Acceptance rule

Progress in this phase counts only if at least one of these gets better:

- a real useful part can now be produced
- a failure becomes clearer and more recoverable
- a validated workflow becomes more repeatable
- the repo's canonical guidance becomes more faithful to the actual operating model
- a utility-part template becomes easier to measure, fit-check, and reproduce
