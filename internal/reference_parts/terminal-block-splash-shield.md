# Terminal Block Splash Shield

## Family

- cover

## Status

- shortlisted

## Functional Intent

- open-backed protective cover for exposed terminal or DIN-mounted electrical hardware
- shields against incidental splash or touch while leaving wire access and mounting access open
- protective rather than high-precision fit-critical, but still constrained by mounting envelope

## Normalized Dimensions

- overall envelope:
  - width, height, and cover depth required
- wall thickness:
  - thin wall likely important
- flange or ear dimensions:
  - optional mounting tabs or side returns may be required
- bore or hole diameters:
  - optional mounting slots or holes
- hole spacing / offsets:
  - depends on hardware format
- depth / height relationships:
  - cover stand-off from protected hardware required
  - front opening or bottom opening dimensions may matter

## Fit-Critical Interfaces

- clearance over target hardware envelope
- access openings for wires or terminals
- optional mounting tab spacing

## Body Intent

- intended final body count: 1
- helper or combined bodies:
  - likely a single shell or bent-cover style body

## Input Quality

- weak to medium
- what is clear:
  - cover intent
  - open-backed and protective
- what is inferred:
  - rectangular or channel-like body is a likely first version
- what remains unknown:
  - exact mounting style
  - whether snap behavior is required
  - whether thin flex features are mandatory

## Workflow Mapping

- current reusable operations:
  - simple enclosure or shell-derived cover
  - cut openings
- likely stage sequence:
  - new design
  - verify clean state
  - create main cover body
  - shell or cut away open face
  - add or cut access openings
  - verify geometry
  - export STL
- verification checkpoints:
  - body count
  - cover envelope
  - open-face dimensions

## Novelty Assessment

- defer
- if new: likely requires better handling of thin-wall and possibly flex or snap assumptions

## Validation Notes

- easiest targeted tests:
  - envelope and wall-thickness validation
- likely live smoke shape:
  - simple U-shaped or open-backed shell cover
- likely failure risks:
  - underdefined geometry family
  - too many variants before a stable first archetype is chosen

## Decision

- defer
- reason:
  - useful family member, but too underdefined for the first slice and likely to pull in thin-wall behavior too early
