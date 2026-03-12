# Flanged Junction Box Body

## Family

- enclosure

## Status

- shortlisted

## Functional Intent

- protective enclosure body for a small electrical or control assembly
- mounts to a panel, wall, or frame through exterior ears or flanges
- protective and fit-critical at the enclosure envelope and mounting interface

## Normalized Dimensions

- overall envelope:
  - rectangular box body with open top
  - outer width, depth, and height required
- wall thickness:
  - uniform shell thickness required
- flange or ear dimensions:
  - ear projection from side walls required
  - ear thickness should match or deliberately differ from body wall or base thickness
  - ear width and hole center offset required
- bore or hole diameters:
  - mounting ear through-hole diameter required
- hole spacing / offsets:
  - left/right ear symmetry expected
  - vertical offset from box floor or top edge required
- depth / height relationships:
  - shell depth and open-top height required

## Fit-Critical Interfaces

- mounting hole diameter and spacing
- outer box envelope where installed space is constrained
- optional lid-mating rim if a follow-on lid is planned

## Body Intent

- intended final body count: 1
- helper or combined bodies:
  - shelled box body
  - two exterior ears that should be combined into one printable body

## Input Quality

- medium
- what is clear:
  - overall concept
  - one-body intent
  - shell plus exterior ears plus mounting holes
- what is inferred:
  - ears are symmetric
  - open-top body is the first slice
- what remains unknown:
  - exact ear placement convention
  - whether ears blend into side walls or base corners
  - whether there is a lid register feature on the body

## Workflow Mapping

- current reusable operations:
  - box-like outer body creation
  - shell
  - create offset or adjacent ear solids
  - combine bodies
  - through-hole cuts
- likely stage sequence:
  - new design
  - verify clean state
  - create outer box body
  - shell body
  - create first ear
  - mirror or create second ear
  - combine ears into body
  - cut mounting holes
  - verify geometry
  - export STL
- verification checkpoints:
  - body count after shell
  - body count after ear combines
  - outer width / depth / height
  - ear hole diameter and left/right placement

## Novelty Assessment

- one-new-operation
- if new: reliable workflow support for exterior ear placement on a shelled enclosure without brittle offset/sketch placement hacks

## Validation Notes

- easiest targeted tests:
  - schema validation for wall thickness and ear dimensions
  - workflow sequence and final body count
  - mounting-hole placement symmetry
- likely live smoke shape:
  - one medium rectangular box with two side ears and simple through-holes
- likely failure risks:
  - shell plus side-ear combine ordering
  - sketch placement for ears relative to a shelled body
  - selecting the correct body for hole cuts after combine

## Decision

- keep shortlisted
- reason:
  - strong family anchor, but likely depends on one reliable exterior-feature placement pattern that should be validated deliberately
