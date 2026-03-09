# ParamAItric Development Plan

## Documentation contract

- Treat this document as the current high-level roadmap and status doc.
- Treat `docs/dev-log.md` as the running execution log.
- Treat `BEST_PRACTICES.md` as the living workflow and prompting contract.
- Update these documents only when the validated state, current phase, or active priorities materially change.

## Current status

Status refresh 2026-03-09:

- Current suite baseline: `234 passed`, with the existing `TestFusionApiAdapter` pytest collection warning.
- The current product shape is a small catalog of dependable Fusion workflows, not broad "AI CAD."
- Validation, failure handling, and smoke coverage are now materially stronger than the earlier scaffold phase.

Validated live workflows:

- `spacer`
- `bracket` on `xy` and `xz`
- `mounting_bracket` on `xy`
- `two_hole_mounting_bracket` on `xy`
- `plate_with_hole`
- `two_hole_plate`
- `filleted_bracket`

Current mock-only workflow:

- `simple_enclosure`

Implemented and test-covered, but not yet live-validated:

- `slotted_mount`

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

Working rules for this phase:

- prefer finishing practical in-flight slices before broadening scope
- add only one new geometric or placement idea per workflow slice
- favor part families over isolated novelty geometry
- keep reliability, validation, and verification ahead of geometry breadth

## Current priorities

1. Keep the canon aligned with reality.
2. Pick one or two real parts near the current bracket/plate family and let them drive the next gaps.
3. Harden only the areas that protect real use, such as profile re-resolution safety and operation-specific cancellation checks where they materially matter.

## Target ladder

The next workflow targets should increase step count and relative-placement difficulty in a controlled order.

1. `mounting_plate_family`
2. `slotted_mount`
3. `counterbored_plate` or `recessed_mount`
4. `open_box_body`
5. `lid_for_box`

Each target should add one new idea only:

- edge-offset placement
- mirrored or symmetric placement
- secondary face-relative features
- local-region placement inside an existing body shape
- inter-part clearance and fit

## Near-term execution guidance

For the next slices:

- stay near the current plate and bracket family first
- keep live validation serial
- require schema validation before CAD ops
- require verification checkpoints after geometry creation
- record live evidence in `docs/dev-log.md`

Real-part use should now be treated as a first-class input to planning. If a real part reveals a missing feature, prefer solving that gap over adding a broader standalone workflow.

## Not current priorities

- broad "AI CAD" expansion
- decorative or organic geometry
- torus or other low-utility benchmark shapes
- third-party runtime dependencies
- new roadmap or backlog docs outside the existing canon

## Active hardening backlog

- Revisit live profile caching and favor safer re-resolution behavior after timeline changes.
- Add operation-specific cancellation checks only where a live step can run long enough to benefit from cooperative aborts.
- Add another live smoke path outside the narrow XY default only when it supports a practical workflow or catches a real regression.

## Acceptance rule

Progress in this phase counts only if at least one of these gets better:

- a real useful part can now be produced
- a failure becomes clearer and more recoverable
- a validated workflow becomes more repeatable
- the repo's canonical guidance becomes more faithful to the actual operating model
