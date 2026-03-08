# ParamAItric Workflow Strategy

## Core rule

ParamAItric should grow by accumulating validated workflow paths, not by assuming broader capability than the evidence supports.

The practical lesson from benchmarking is simple:

1. find a narrow sequence that works reliably
2. standardize that sequence
3. verify it repeatedly
4. build the next layer of complexity on top of it

This means the product should optimize for workflow learning, not just tool availability.

## What counts as progress

A workflow path is considered proven only when:

- the step sequence is explicit
- verification points are explicit
- failure boundaries are explicit
- the result is repeatable enough to trust as a base for the next workflow

Useful growth comes from reusing proven stages such as:

- clean scene setup
- sketch creation
- deterministic profile selection
- single-body extrusion
- body-count verification
- dimension verification
- export

## Product implication

The system should keep a catalog of validated workflows and validated sub-stages.

Examples:

- `spacer` can be a foundation workflow
- `plate with holes` can build on the same sketch -> profile -> extrude -> verify pattern
- `bracket` can reuse the same base stages plus one or two additional validated feature stages
- `simple enclosure` should be staged body first, mating or hollowing logic second, verification between them

## Anti-pattern

Do not treat new complexity as a single larger prompt or a single larger tool.

If a more complex workflow is needed, it should be decomposed into already-proven stages plus the smallest new stage that must be learned next.

## Engineering rule

When a workflow fails, preserve:

- the stage that failed
- the last known-good stage
- the partial result
- the next narrow correction step

That information is part of the product learning loop and should feed future workflow design.
