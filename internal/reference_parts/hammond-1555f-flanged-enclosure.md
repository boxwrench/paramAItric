# Hammond 1555F Flanged Enclosure

## Reference Artifact

- reference type: dimensioned PDF drawing / technical specification sheet
- reference strength: strong
- derived from:
  - `internal/reference_parts/intake-hammond-1555f.md`
  - `private/reference_intake/enclosures-and-covers/raw/hammond-1555f/1555F.pdf`
  - `private/reference_intake/enclosures-and-covers/derived/hammond-1555f/1555F-dimension-extraction.txt`
- directly observed dimensions:
  - series includes multiple sizes, including:
    - `1555F`: `80 x 55 x 35 mm`
    - `1555F2`: `115 x 80 x 35 mm`
    - `1555F3`: `115 x 80 x 45 mm`
    - `1555F42`: `145 x 100 x 55 mm`
  - integrated mounting flanges in the lid
  - two-piece enclosure body and lid
  - assembly screws threaded into factory-tapped holes
- inferred dimensions or relationships:
  - flange hole placement is symmetric
  - first workflow slice can preserve flange presence and envelope even if internal boss detail is deferred
  - one representative size can anchor the first workflow while keeping the series as a future parameterized family

## Family

- enclosure

## Status

- selected

## Functional Intent

- wall-mount plastic enclosure for electronics or controls
- protects internal components while allowing direct surface mounting through integrated lid flanges
- fit-critical at outer envelope, mounting-flange layout, and lid-to-base closure relationship

## Normalized Dimensions

- overall envelope:
  - one representative first-slice size should be chosen from the series
  - recommended anchor size: `1555F2` or `1555F3` because they are large enough to show the wall-mount pattern clearly without being oversized
- wall thickness:
  - not fully extracted yet; likely secondary for the first family slice
- flange or ear dimensions:
  - integrated wall-mount flanges are the defining feature
  - flange hole pattern exists on the lid
- bore or hole diameters:
  - lid mounting and enclosure assembly screw holes are present
- hole spacing / offsets:
  - flange holes appear symmetric left/right
  - assembly screw positions are fixed by the enclosure series
- depth / height relationships:
  - lid and base meet in a lap-joint style construction
  - gasketed variants exist within the family

## Fit-Critical Interfaces

- overall outer envelope for installation space
- flange mounting-hole spacing and flange projection
- lid-to-base alignment

## Body Intent

- intended final body count: 2 major bodies
- helper or combined bodies expected during workflow:
  - base body
  - flanged lid body
- hardware remains reference data, not a first-slice printable target

## Input Quality

- strong
- what is clear:
  - two-piece box/lid structure
  - integrated mounting flange concept
  - representative family sizes
  - enclosure series identity
- what is inferred:
  - one representative size can stand in for the family anchor
  - flange-hole geometry can be included or narrowed depending on workflow complexity
- what remains unknown:
  - exact boss geometry
  - exact gasket groove details
  - detailed flange-hole offsets for every family size

## Workflow Mapping

- current reusable operations:
  - enclosure base body creation
  - lid creation
  - multi-body verification
- likely stage sequence:
  - new design
  - verify clean state
  - create base body
  - verify envelope
  - create flanged lid body
  - verify lid envelope and flange projection
  - optionally add flange-hole pattern
  - final verification with deterministic body spacing
  - export STL
- verification checkpoints:
  - base body count
  - final major body count = 2
  - body outer dimensions
  - lid dimensions
  - flange projection and flange-hole count if included

## Novelty Assessment

- one-new-operation
- if new: reliable lid-integrated wall-mount flange pattern with preserved enclosure-body relationship

## Validation Notes

- easiest targeted tests:
  - representative size envelope verification
  - final body count = 2
  - flange presence and symmetry
- likely live smoke shape:
  - one compact enclosure base plus separate lid with integrated flanges
- likely failure risks:
  - overcomplicating the first slice by trying to parameterize the whole family at once
  - under-specifying flange geometry if the drawing needs closer extraction
  - mixing wall-mount verification concerns into the simpler enclosure-body anchor

## Decision

- keep shortlisted
- reason:
  - high-value follow-on once a simpler screw-down enclosure pair is established
  - likely better as the second enclosure-family slice than the first because it adds mounting-flange behavior on top of the box/lid pattern
