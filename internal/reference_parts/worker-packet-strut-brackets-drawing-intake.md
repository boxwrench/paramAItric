# Worker Packet: Strut Brackets And Mounts Drawing Intake

## Objective

Acquire an assortment of 10 fresh drawing-backed reference artifacts for strut brackets and mounting accessories.

This is an intake task only.
Do not implement workflows.
Do not rewrite canon docs.

## Read First

- `internal/reference_parts/REFERENCE_INTAKE_CHECKLIST.md`
- `internal/reference_parts/TEMPLATE.reference-intake.md`
- `internal/reference_parts/TEMPLATE.part-spec.md`
- `internal/reference-sourcing-strategy.md`
- `internal/reference_parts/PRIVATE_INTAKE_LAYOUT.md`

## Family

- strut brackets and mounts

## Target Mix

Prefer a practical assortment such as:

- angle brackets
- flat joining plates
- corner brackets
- pipe or conduit clamps for strut
- beam or channel attachment brackets
- post bases or wall mounts
- offset mounting brackets
- multi-hole support brackets

## Drawing Requirement

Each kept candidate must have a locally staged drawing artifact.

Accepted drawing artifacts:

- dimensioned PDF technical drawing
- 2D DXF or DWG
- official drawing sheet or equivalent

Not enough:

- product-page dimensions alone
- copied dimension tables
- `.url` files
- summarized notes
- derived text without a local drawing file

## Source Priority

Use this order only:

1. official manufacturer drawing
2. official distributor/configurator drawing
3. supplier-backed CAD platform drawing only if the first two fail

## Required Outputs

Tracked:

- 10 intake notes:
  - `internal/reference_parts/intake-<artifact>.md`

Private:

- local drawing files under `private/reference_intake/strut-brackets-and-mounts/raw/<artifact>/`
- derived text under `private/reference_intake/strut-brackets-and-mounts/derived/<artifact>/` if useful
- additive updates to `private/reference_intake/strut-brackets-and-mounts/manifest.json`

Optional tracked outputs:

- up to 3 normalized part specs, but only for the strongest and clearest candidates

## Normalized Part Spec Rule

Draft normalized part specs only when:

- the drawing artifact is locally staged
- the geometry is clear enough to fill the spec without repeated rereads
- the candidate looks plausibly implementable or strategically important

Do not draft all 10 normalized specs by default.
For this packet, 0 to 3 normalized specs is the right range.

## Preservation Rule

Treat the manifest as append-only unless a migration is explicitly authorized.

- read the current manifest before editing it
- preserve prior entries
- add new entries or update matching entries in place
- if the current shape conflicts with your intended update, stop and report the mismatch

## Status Rules

- `identified_only`
  - source found, no local files staged
- `identified_but_missing_drawing`
  - dimensions found, but no local drawing artifact staged
- `complete`
  - local drawing artifact exists
  - derived file exists locally if claimed
  - intake note points to the local files

## Required Closeout Verification

Before reporting completion:

- list the exact local drawing files created
- list any derived files created
- verify those files exist locally
- state how many of the 10 are truly drawing-backed complete

## Stop Conditions

Stop when any one of these is true:

1. 10 drawing-backed artifacts are complete
2. 120 minutes is spent and fewer than 10 drawing-backed artifacts are found
3. source quality is too weak and the task needs orchestrator review

## Report Back With

- the 10 artifacts acquired
- exact local drawing file paths
- a short category breakdown of the assortment
- the 1 to 3 strongest candidates for future workflow slices
- whether any normalized part specs were drafted
- any source friction that suggests process improvement
