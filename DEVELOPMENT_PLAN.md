# ParamAItric Development Plan

## Documentation contract

- Treat this document as the current high-level roadmap and status doc.
- Treat `docs/dev-log.md` as the running execution log.
- Treat `BEST_PRACTICES.md` as the living real-world-use reference for prompting, staging, inputs, verification defaults, and failure handling.
- Update these documents only when the validated state, current phase, or active priorities materially change.

## Current status

Status refresh 2026-03-09:

- Latest local suite run on March 9, 2026: `382 passed, 1 warning`.
- The current product shape is a small catalog of dependable Fusion workflows, not broad "AI CAD."
- Validation, failure handling, and smoke coverage are now materially stronger than the earlier scaffold phase.
- MCP packaging is now in place, and the inspection lane includes body, face, and edge reporting.
- The current surface is now 23 workflow definitions, 28 MCP tools, and a live-validated path across enclosure, cylindrical, revolve, and handle-family work.
- `shell`, `cylinder`, `tube`, and `revolve` are now implemented and live-validated through practical workflows, not just primitive coverage.

Validated live workflows:

- `spacer`
- `cylinder`
- `tube`
- `revolve`
- `tapered_knob_blank`
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
2. Prioritize new operation multipliers over more plate or bracket variants that reuse the same proven vocabulary.
3. Keep the `tube`, `revolve`, and handle/socket lane honest with real templates instead of backsliding into benchmark-only geometry.
4. Choose the next fit-critical utility template that reuses `revolve`, `combine_bodies`, chamfers, holes, lids, or press-fit relationships where they actually matter.
5. Open guided freeform primitive composition only after the primitive vocabulary and inspection checkpoints are strong enough to carry the same verification discipline as the current workflow macros.
6. Harden only the areas that protect real use, such as profile re-resolution safety, offset-sketch reliability, joined-body targeting, chamfer/feature selection, and operation-specific cancellation checks where they materially matter.

## Target ladder

The next workflow targets should increase capability in a controlled order while staying reusable.

1. one or two more real enclosure-family templates that reuse `shell`
2. another fit-oriented cylindrical or handled-part template that builds on `tube`, `revolve`, and `combine_bodies`
3. lids, press-fit, or socket relationships where the real part requires them
4. guided freeform composition with mandatory verification checkpoints between primitive steps

Each target should add one new idea only:

- shelled enclosure variation or closure detail
- cylindrical or handled-part feature composition such as holes, chamfers, a joined sleeve, a through-bore, or a fit-critical socket
- fit and clearance relationships only when the chosen template requires them
- guided primitive composition only after inspection can act as a reliable self-check lane

## Near-term execution guidance

For the next slices:

- treat `shell`, `cylinder`, `tube`, `revolve`, and `combine_bodies` as the current reusable building blocks
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

## Not current priorities

- broad "AI CAD" expansion
- decorative or organic geometry
- torus or other low-utility benchmark shapes
- third-party runtime dependencies
- new roadmap or backlog docs outside the existing canon
- a hard-coded material recommendation engine inside the MCP server
- rollback points before live use demonstrates a real need
- angled sketch planes before the axis-aligned workflow families are saturated
- threading, where real FDM workflows usually prefer inserts or post-print tapping
- component or assembly conversion before STEP or assembly output becomes a real requirement
- linear or circular pattern features before real templates force them

## Active hardening backlog

- Revisit live profile caching and favor safer re-resolution behavior after timeline changes.
- Revisit offset-sketch handling only where real box-family use exposes failures.
- Add operation-specific cancellation checks only where a live step can run long enough to benefit from cooperative aborts.
- Add another live smoke path outside the narrow XY default only when it supports a practical workflow or catches a real regression.

## Acceptance rule

Progress in this phase counts only if at least one of these gets better:

- a real useful part can now be produced
- a failure becomes clearer and more recoverable
- a validated workflow becomes more repeatable
- the repo's canonical guidance becomes more faithful to the actual operating model
- a utility-part template becomes easier to measure, fit-check, and reproduce
