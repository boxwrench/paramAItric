# Unistrut P1067 Flat Plate Fitting

## Reference Artifact

- reference type: dimensioned PDF drawing / product catalog page
- reference strength: strong
- derived from: unistrut-p1067-flat-plate
- directly observed dimensions:
  - Width: 1-5/8" (41mm)
  - Thickness: 1/4" (6mm)
  - Hole diameter: 9/16" (14mm)
  - Hole spacing from end: 13/16" (21mm)
  - Hole spacing on center: 1-7/8" (48mm)
- inferred dimensions or relationships:
  - Overall length estimated from hole count and spacing
  - Material specification per ASTM A1011

## Family

- strut brackets and mounts

## Status

- shortlisted

## Functional Intent

- Splice/join two sections of Unistrut channel
- Mates with P1000, P1100, P2000, P3300, P4000, P5000, P5500 channels
- Structural - maintains continuity of channel runs
- Uses 1/2" fasteners with channel nuts

## Normalized Dimensions

- overall envelope:
  - Width: 1-5/8" (41mm)
  - Length: Not yet normalized from the artifact with enough confidence for implementation
  - Thickness: 1/4" (6mm)
- wall thickness: 1/4" (6mm) plate
- flange or ear dimensions: N/A - flat plate
- bore or hole diameters: 9/16" (14mm)
- hole spacing / offsets:
  - From end: 13/16" (21mm)
  - On center: 1-7/8" (48mm)
- depth / height relationships: Flat - no depth

## Fit-Critical Interfaces

- interface 1: Channel slot (via channel nut)
- interface 2: Opposing channel slot
- required clearance or tolerance notes:
  - 9/16" holes provide clearance for 1/2" bolts
  - Channel nut must engage slot through holes

## Body Intent

- intended final body count: 1
- any helper or combined bodies expected during workflow: None

## Input Quality

- strong
- what is clear: Width, thickness, hole diameter, and center-to-center spacing
- what is inferred: Overall length and exact edge-distance interpretation
- what remains unknown: Exact overall length, edge radius, surface finish spec

## Workflow Mapping

- current reusable operations:
  - Plate cutting to size
  - Hole pattern drilling/punching
  - Deburring
- likely stage sequence:
  1. Cut plate to length
  2. Drill/punch 4 holes per pattern
  3. Deburr edges
- verification checkpoints:
  - Hole diameter
  - Hole spacing
  - Overall width

## Novelty Assessment

- current-vocabulary
- All operations should be available in current workflow

## Validation Notes

- easiest targeted tests:
  - Verify hole spacing with gauge
  - Check fit with actual channel and channel nut
- likely live smoke shape: 4-hole flat plate with known width/thickness/hole pattern, pending exact overall length
- likely failure risks:
  - Hole position tolerance
  - Width tolerance for channel fit
  - Incorrect overall length if inferred instead of directly recovered

## Decision

- keep shortlisted
- reason: Strong candidate with a clear hole pattern, but exact overall length still needs to be recovered from the artifact before it is implementation-ready.
