# ParamAItric Workflow Strategy

## Core rule

ParamAItric should grow by accumulating validated workflow paths, not by assuming broader capability than the evidence supports.

This document is about choosing the next workflow families and template directions. The day-to-day prompting, staging, and input contract for real use belongs in `BEST_PRACTICES.md`.

The default pattern is:

1. find a narrow sequence that works reliably
2. standardize that sequence
3. verify it repeatedly
4. build the next layer of complexity on top of it

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

## Increment rule

Each new workflow slice should add one new idea only.

That new idea can be:

- a placement rule
- a sketch primitive
- a second-stage feature
- an inter-part fit relationship

It should not introduce several of those at once.

## Current expansion ladder

The preferred next progression for this repo is:

1. shelling a proven body shape
2. simple lid or press-fit relationships on that shelled shape
3. cylindrical base geometry, including hollow cylindrical forms
4. revolve-driven geometry that cannot be reached cleanly through stacked extrusions
5. fit-critical handled, socketed, or joined cylindrical parts
6. inter-part clearance and fit

This keeps growth tied to practical part generation instead of broad CAD coverage.

That ladder has now materially landed in the repo. As of March 9, 2026, `shell`, `simple_enclosure`, `cylinder`, `tube`, `revolve`, joined-body cylindrical composition, and one fit-critical handle/socket workflow are already in the validated path. The next ladder step should therefore emphasize practical fit and interface work, not another workflow variant that only recombines the same plate or bracket stages.

## Operation diversity rule

Once a workflow family has validated the current vocabulary, the next priority should shift from variant count to operation diversity.

In practice:

- another bracket or plate variant usually adds one narrowly useful endpoint
- a new operation such as `shell`, `combine_bodies`, or `revolve` multiplies what many existing workflow families can do
- workflow count is not the goal; reusable capability with explicit verification is the goal

The early plate and bracket family was still worthwhile because each slice validated a different primitive or sequencing rule. That remains the right pattern. The implication now is simply that the next big gains come from adding multipliers rather than more variants of the same family.

## Priority lens

The preferred real-world lens for choosing the next workflows is utility and maintenance parts.

That means the next templates should come from needs such as:

- valve handles and stem sockets
- instrument brackets and adapter plates
- covers, guards, and splash shields
- shims, spacers, and clamp-like fixtures

These are good targets because they are usually simple, measurable, and already near the validated geometry families in the repo.

## Product implication

The system should keep a catalog of validated workflows and validated sub-stages.

Examples:

- `spacer` is a foundation workflow
- bracket and mounting workflows reuse the same staged contract with one added idea at a time
- `plate_with_hole` proves a narrow second-sketch cut path
- `filleted_bracket` proves a narrow post-extrusion feature stage
- `chamfered_bracket` reuses that same post-extrusion stage shape with a different edge finish
- `simple_enclosure` should remain staged body first, hollowing or mating logic second, verification between them
- `tube_mounting_plate` shows that joined solids should stay true CAD bodies when the intended printed part is one part
- `t_handle_with_square_socket` shows that a real utility template should drive both geometry choice and fit-oriented verification

A domain template should usually be a composition and parameterization of those validated stages, not a new primitive. A valve handle, adapter plate, or equipment cover should only force a new primitive when the required geometry truly falls outside the existing staged vocabulary.

## Macros and freeform composition

The current `create_[part]` workflows should be treated as reference implementations, not as the final shape of the product.

They already encode:

- safe stage ordering
- verification checkpoints
- profile-selection rules
- narrow repairs for known Fusion quirks
- failure boundaries that preserve partial progress

That makes them useful training data for a later guided freeform mode. The repo should not skip straight from validated macros to unconstrained primitive composition, because that would throw away the product learning encoded in those staged paths.

The intended path is:

1. finish the missing high-value primitives and modifiers
2. keep strengthening inspection and verification as a self-check lane
3. expose guided primitive composition with mandatory verification checkpoints
4. keep the macros as known-good reference paths and fallback happy paths

## Anti-pattern

Do not treat new complexity as a single larger prompt or a single larger tool.

If a more complex workflow is needed, decompose it into already-proven stages plus the smallest new stage that must be learned next.

## Failure rule

When a workflow fails, preserve:

- the stage that failed
- the last known-good stage
- the partial result
- the next narrow correction step

That information is part of the product learning loop and should feed future workflow design.

## Current phase implication

Now that a small live workflow family is validated, progress should increasingly come from use and fix.

That means:

- pick real parts near the current family
- prefer parts with clear interface dimensions and known failure modes
- let tests mirror those interface and failure constraints
- let those parts reveal the next missing step
- broaden the catalog only when it supports practical generation or reusable multi-step patterns

## Deferred until forced by real use

These are reasonable future capabilities, but not the current strategic target:

- rollback points
- angled sketch planes
- threading
- component or assembly conversion
- linear or circular patterns

They should move forward only when a real part family or output requirement forces them.
