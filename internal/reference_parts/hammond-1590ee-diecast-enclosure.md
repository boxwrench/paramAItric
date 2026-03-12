# Hammond 1590EE Diecast Enclosure

## Reference Artifact

- reference type: dimensioned PDF drawing
- reference strength: strong
- derived from:
  - `internal/reference_parts/intake-hammond-1590ee.md`
  - `private/reference_intake/enclosures-and-covers/raw/hammond-1590ee/1590EE.pdf`
  - `private/reference_intake/enclosures-and-covers/derived/hammond-1590ee/1590EE.txt`
- directly observed dimensions:
  - outer envelope about `200.20 x 120.20 mm`
  - inside length about `191.63 mm`
  - inside width about `111.63 mm`
  - inside height about `80.00 mm`
  - six cover screw holes
  - cover screw size `M3.5 x 12 mm`
- inferred dimensions or relationships:
  - box and lid wall thickness are derived from outer vs inner envelope
  - lid fastener pattern is symmetric
  - the first workflow slice can ignore cosmetic diecast rounding if interface geometry is preserved

## Family

- enclosure

## Status

- selected

## Functional Intent

- two-piece diecast utility enclosure for electronics or controls
- protects internal components and closes with a screw-fastened lid
- fit-critical at outer envelope, internal usable volume, and lid-to-box screw closure relationship

## Normalized Dimensions

- overall envelope:
  - outer body around `200.20 x 120.20 x 84.50 mm`
  - internal usable volume around `191.63 x 111.63 x 80.00 mm`
- wall thickness:
  - approximately `4.2 to 4.5 mm` from outer vs inner dimensions
- flange or ear dimensions:
  - none in the base reference
- bore or hole diameters:
  - six lid screw clearances / threaded closure points
  - drawing shows `6X` hole callouts with M3.5 thread context
- hole spacing / offsets:
  - six symmetric cover fastener locations distributed around the perimeter
- depth / height relationships:
  - lid sits above the main box body
  - liquid-resistant variant uses a gasketed closure path

## Fit-Critical Interfaces

- internal usable length / width / height
- lid-to-box closure alignment
- screw-fastener pattern for the six cover screws

## Body Intent

- intended final body count: 2 major bodies
- helper or combined bodies expected during workflow:
  - base body
  - lid body
- hardware is reference data, not part of the first printable workflow target

## Input Quality

- strong
- what is clear:
  - overall box/lid geometry
  - internal and external envelope
  - screw-fastened closure concept
  - body count
- what is inferred:
  - first workflow slice can treat corner radii and cosmetic diecast shaping as secondary
  - screw-hole pattern can be simplified or deferred in the first family anchor if needed
- what remains unknown:
  - exact boss geometry for the screw landing features
  - exact lid lip / recess cross-section
  - exact gasket groove geometry in the liquid-resistant variant

## Workflow Mapping

- current reusable operations:
  - open box body creation
  - lid creation
  - verification of outer and inner dimensions
  - multi-body export or verification
- likely stage sequence:
  - new design
  - verify clean state
  - create base enclosure body
  - verify body envelope and internal volume
  - create separate lid body
  - verify lid envelope
  - optionally add screw-hole pattern or landing geometry
  - final verification with deterministic part spacing for multi-body review
  - export STL
- verification checkpoints:
  - base body count
  - final major body count = 2
  - outer envelope
  - internal usable envelope
  - open face must be the large top face, not an end face
  - enclosure base must retain a real floor, not collapse into a sleeve or end-cap topology
  - lid dimensions
  - closure-hole count if closure geometry is included

## Novelty Assessment

- one-new-operation
- if new: reliable screw-fastened box-and-lid closure pattern with explicit lid/body alignment and optional fastener-hole placement

## Validation Notes

- easiest targeted tests:
  - nominal outer and inner dimension verification
  - expected final body count = 2
  - explicit top-opening assertion
  - explicit floor-presence / non-sleeve assertion
  - lid/body separation for verification layout
- likely live smoke shape:
  - one rectangular diecast-style top-opening box plus separate flush lid with preserved envelope
- likely failure risks:
  - deciding how much of the screw-fastening detail belongs in the first slice
  - preserving usable internal dimensions while adding a realistic top-face lid relationship
  - overcommitting to diecast cosmetic details too early

## Decision

- implement now
- reason:
  - strongest current drawing-backed family anchor for a screw-down enclosure pair
  - geometry is clearer and more bounded than the hinged references
  - a simplified first slice can preserve the important enclosure relationship without requiring every diecast detail on day one
