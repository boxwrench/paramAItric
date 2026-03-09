# ParamAItric Workflow Strategy

## Core rule

ParamAItric should grow by accumulating validated workflow paths, not by assuming broader capability than the evidence supports.

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

1. edge-offset placement
2. mirrored or symmetric placement
3. secondary face-relative features
4. local-region placement inside an existing body shape
5. inter-part clearance and fit

This keeps growth tied to practical part generation instead of broad CAD coverage.

## Product implication

The system should keep a catalog of validated workflows and validated sub-stages.

Examples:

- `spacer` is a foundation workflow
- bracket and mounting workflows reuse the same staged contract with one added idea at a time
- `plate_with_hole` proves a narrow second-sketch cut path
- `filleted_bracket` proves a narrow post-extrusion feature stage
- `simple_enclosure` should remain staged body first, hollowing or mating logic second, verification between them

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
- let those parts reveal the next missing step
- broaden the catalog only when it supports practical generation or reusable multi-step patterns
