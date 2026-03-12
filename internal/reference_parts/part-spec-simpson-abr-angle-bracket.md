# Simpson ABR Reinforced Angle Bracket

## Reference Artifact

- reference type: dimensioned PDF technical data sheet
- reference strength: strong
- derived from: simpson-abr-angle-bracket
- directly observed dimensions:
  - Leg sizes: 90mm, 105mm
  - Material: Pre-galvanised mild steel
  - Hole diameter: 4.0mm for CNA nails
- inferred dimensions or relationships:
  - Hole spacing pattern (standard industry layout)
  - Material thickness estimated from gauge standards

## Family

- strut brackets and mounts

## Status

- shortlisted

## Functional Intent

- Provides structural connection between timber members at 90-degree angle
- Mates with timber beams, trusses, headers
- Structural - load bearing in shear and tension
- Reinforced ribs provide additional strength

## Normalized Dimensions

- overall envelope:
  - ABR90: 90mm x 90mm legs
  - ABR105: 105mm x 105mm legs
- wall thickness: Standard sheet steel (approx 2.0mm typical)
- flange or ear dimensions: N/A - angle configuration
- bore or hole diameters: 4.0mm for standard CNA nails
- hole spacing / offsets: Industry standard 4-10 hole patterns
- depth / height relationships: Rib height approximately 3-5mm

## Fit-Critical Interfaces

- interface 1: Timber support member (vertical leg)
- interface 2: Timber supported member (horizontal leg)
- required clearance or tolerance notes: None - surface mount

## Body Intent

- intended final body count: 1
- any helper or combined bodies expected during workflow: None

## Input Quality

- strong
- what is clear: Load capacities, material, available sizes, fastening options
- what is inferred: Exact hole positions, material thickness
- what remains unknown: Specific hole coordinates, bend radius
- family-fit note: Strong bracket reference, but adjacent to the strut family rather than a direct strut-channel fitting

## Workflow Mapping

- current reusable operations:
  - Sheet metal profile cutting
  - Hole pattern punching
  - Forming/bending at 90 degrees
  - Embossing/rib forming
- likely stage sequence:
  1. Blank with holes
  2. 90-degree bend
  3. Rib embossing
- verification checkpoints:
  - Hole alignment
  - Angle squareness
  - Rib height

## Novelty Assessment

- current-vocabulary / one-new-operation / defer
- one-new-operation: Embossed rib forming if not already available

## Validation Notes

- easiest targeted tests:
  - Verify hole spacing matches standard fastener patterns
  - Check angle tolerance
- likely live smoke shape: ABR90 or ABR105
- likely failure risks:
  - Rib forming depth
  - Material thinning at bend
  - Family drift if treated as a direct strut-hardware anchor

## Decision

- keep shortlisted
- reason: Strong adjacent bracket reference, but not a clean strut-channel fitting anchor. Keep as neighboring bracket research unless the family scope broadens.
