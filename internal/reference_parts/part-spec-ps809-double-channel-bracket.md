# Power-Strut PS809 Double Channel Bracket

## Reference Artifact

- reference type: dimensioned PDF drawing / product catalog page
- reference strength: strong
- derived from: ps809-double-channel-bracket
- directly observed dimensions:
  - Available lengths: 12", 18", 24", 30", 36"
  - Uniform load ratings by size
  - Weight per 100 pieces
- inferred dimensions or relationships:
  - General dual-channel bracket intent only

## Family

- strut brackets and mounts

## Status

- deferred

## Functional Intent

- Connect two parallel channel sections at fixed spacing
- Mates with PS200, PS210, PS300, PS400, PS500 channel profiles
- Structural - maintains parallel channel alignment
- Supports equipment across dual channel rails

## Normalized Dimensions

- overall envelope:
  - Length: 12", 18", 24", 30", 36" options
  - Width: Not yet normalized from the artifact
- wall thickness: Not yet normalized from the artifact
- flange or ear dimensions:
  - General formed bracket geometry is implied, but leg/span dimensions are not yet normalized from the artifact
- bore or hole diameters: Not yet normalized from the artifact
- hole spacing / offsets: Not yet normalized from the artifact
- depth / height relationships: Not yet normalized from the artifact

## Fit-Critical Interfaces

- interface 1: Primary channel (via channel nut)
- interface 2: Secondary parallel channel (via channel nut)
- required clearance or tolerance notes:
  - Parallelism critical for proper fit
  - Channel spacing must match bracket width

## Body Intent

- intended final body count: 1
- any helper or combined bodies expected during workflow: None

## Input Quality

- strong
- what is clear: Length options, load table, and single-piece bracket intent
- what is inferred: Nearly all fit-critical geometry
- what remains unknown: Hole pattern, channel spacing, bend details, and specific forming geometry

## Workflow Mapping

- current reusable operations:
  - Sheet metal forming
  - Hole punching
  - Bend operations
- likely stage sequence:
  1. Blank with holes
  2. Form vertical legs
  3. Form horizontal span
- verification checkpoints:
  - Channel spacing accuracy
  - Hole alignment
  - Load rating verification

## Novelty Assessment

- defer
- The current artifact is strong for load/span characterization but too weak for geometry-backed workflow normalization

## Validation Notes

- easiest targeted tests:
  - Recover page crops or clearer geometry before drafting a normalized shape
  - Verify actual channel spacing from the source artifact
- likely live smoke shape: Not appropriate until the geometry is recovered from the drawing
- likely failure risks:
  - False confidence from typical strut assumptions
  - Wrong channel spacing or hole layout if normalized prematurely

## Decision

- defer
- reason: The current extraction is useful for load/span data, but it does not yet provide enough drawing-backed geometry for a normalized part spec.
