# Worker Packet: Enclosure Drawing Intake Round 3

## Objective

Acquire exactly 3 fresh drawing-backed enclosure-family reference artifacts.

This is a drawing-first intake task.
Do not substitute product-page dimensions for drawings.
Do not implement workflows.
Do not rewrite canon docs.

## Read First

- `internal/reference_parts/REFERENCE_INTAKE_CHECKLIST.md`
- `internal/reference_parts/TEMPLATE.reference-intake.md`
- `internal/reference-sourcing-strategy.md`
- `internal/reference_parts/PRIVATE_INTAKE_LAYOUT.md`

## Goal Standard

Each kept candidate must have a locally staged drawing artifact.

Accepted drawing artifacts:

- dimensioned PDF technical drawing
- 2D DXF or DWG
- official drawing sheet or equivalent

Not enough:

- product-page dimensions alone
- copied dimension tables
- `.url` shortcut files
- summarized notes
- derived text without a local drawing file

## Source Priority

Use this order only:

1. official manufacturer drawing
2. official distributor/configurator drawing
3. supplier-backed CAD platform drawing only if the first two fail

## Target Family

- enclosures and covers

## Fresh Requests

Find 3 new drawing-backed candidates, preferably not the same artifacts already staged locally.

Preferred mix:

- one wall-mount or flanged enclosure with a real drawing
- one project/electronics enclosure with a real drawing
- one alternate closure style with a real drawing

## Required Outputs

Tracked:

- `internal/reference_parts/intake-<artifact>.md` for 3 fresh artifacts

Private:

- local drawing files under `private/reference_intake/enclosures-and-covers/raw/<artifact>/`
- derived text under `private/reference_intake/enclosures-and-covers/derived/<artifact>/` if useful
- additive updates to `private/reference_intake/enclosures-and-covers/manifest.json`

## Preservation Rule

Treat the manifest as append-only unless a migration is explicitly authorized.

- read the current manifest before editing it
- preserve prior entries
- add new entries or update matching entries in place
- if the current shape conflicts with your intended update, stop and report the mismatch

## Artifact Strength Rule

Only keep artifacts that are both:

- official or supplier-backed
- locally staged as drawings

If a candidate has good dimensions but no drawing, mark it `identified_but_missing_drawing` and do not count it toward the 3 completed artifacts.

## Required Closeout Verification

Before reporting completion:

- list the exact local drawing files created
- list any derived files created
- verify those files exist locally

Status rules:

- `identified_only`
  - source found, no local files staged
- `identified_but_missing_drawing`
  - dimensions found, but no local drawing artifact staged
- `derived_only_missing_raw`
  - derived notes exist, but no local drawing artifact staged
- `complete`
  - local drawing artifact exists
  - derived file exists locally if claimed
  - intake note points to the local files

## Stop Conditions

Stop when any one of these is true:

1. 3 fresh drawing-backed artifacts are complete
2. 90 minutes is spent and fewer than 3 drawing-backed artifacts are found
3. official sources are too sparse and the task needs orchestrator review

## Report Back With

- the 3 drawing artifacts acquired
- exact local drawing file paths
- why each was kept
- any candidates rejected because they lacked actual drawings
- any source friction that suggests process improvement
