# Friction-Fit Lid With Stepped Lip

## Family

- cover

## Status

- shortlisted

## Functional Intent

- removable lid for a matching enclosure body
- closes the opening through a stepped lip that inserts into or over the box opening
- fit-critical at lip clearance, insertion depth, and overall cap dimensions

## Normalized Dimensions

- overall envelope:
  - lid outer width and depth required
  - lid top thickness required
- wall thickness:
  - lip thickness derived from mating clearance and box opening
- flange or ear dimensions:
  - optional outer cap overhang required
- bore or hole diameters:
  - none required for the base version
- hole spacing / offsets:
  - not required for the base version
- depth / height relationships:
  - stepped lip depth required
  - insertion clearance required between lid lip and mating wall

## Fit-Critical Interfaces

- lip outer dimensions relative to mating box opening
- clearance between lip and box wall
- stop depth or cap-overhang relationship

## Body Intent

- intended final body count: 1
- helper or combined bodies:
  - top plate body
  - stepped lip body or subtractive inset path depending on workflow shape

## Input Quality

- medium
- what is clear:
  - removable lid
  - stepped lip is the defining feature
  - fit gap matters
- what is inferred:
  - rectangular enclosure mate
  - symmetric lip
- what remains unknown:
  - insert-inside vs wrap-over geometry preference
  - target nominal clearance
  - whether corners need chamfer or radius relief

## Workflow Mapping

- current reusable operations:
  - rectangular lid body
  - inset step geometry
  - combine or cut path for lip formation
- likely stage sequence:
  - new design
  - verify clean state
  - create lid plate
  - create stepped lip geometry
  - combine or subtract to final lid shape
  - verify geometry
  - export STL
- verification checkpoints:
  - final body count
  - outer lid dimensions
  - lip dimensions and insertion depth
  - fit-gap assertions where expressible

## Novelty Assessment

- one-new-operation
- if new: explicit fit-gap and mating-lip workflow pattern for box/lid pairs

## Validation Notes

- easiest targeted tests:
  - schema validation for lip depth and clearance
  - geometry verification for lid outer size and lip size
- likely live smoke shape:
  - plain rectangular lid with one stepped inner lip
- likely failure risks:
  - encoding fit intent as stable parameters
  - deciding whether the first version should be insert-fit or wrap-over

## Decision

- keep shortlisted
- reason:
  - high value, but should follow a matching enclosure body so fit logic has a grounded mate
