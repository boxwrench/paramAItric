# Worker Packet: Enclosure Second Intake

## Objective

Acquire and normalize a second bounded set of enclosure-family reference artifacts without broad research drift.

This is an intake task only.
Do not implement workflows.
Do not rewrite canon docs.

Important:

- this packet should have been drawing-first
- future packets must require actual drawing acquisition, not just enough dimensions to write notes

## Context

The first intake round already has 3 official enclosure references processed:

- Hammond 1590EE
- OKW C2108082
- Polycase ZH family reference

This worker pass should gather a second set so the family comparison is less dependent on one manufacturer style.

## Read First

- `internal/reference_parts/REFERENCE_INTAKE_CHECKLIST.md`
- `internal/reference_parts/TEMPLATE.reference-intake.md`
- `internal/reference-sourcing-strategy.md`
- `internal/reference_parts/PRIVATE_INTAKE_LAYOUT.md`

## Source Priority

Use this order only:

1. official manufacturer artifact
2. official distributor or configurator artifact
3. supplier-backed CAD platform artifact only if the first two fail

Do not use weak or secondary sources as the primary artifact.

## Drawing Requirement

For this library, the target is a local drawing-backed reference artifact.

Acceptable completion artifacts:

- dimensioned PDF technical drawing
- 2D DXF or DWG
- official technical drawing sheet

Not sufficient for completion by themselves:

- product page dimensions alone
- copied or summarized dimension tables
- `.url` pointer files
- derived text without a local drawing artifact

## Target Family

- enclosures and covers

## Candidate Direction

Prefer a mix of:

- one wall-mount or flanged enclosure candidate
- one smaller electronics/project enclosure candidate
- one alternate closure style if clearly dimensioned

Avoid:

- highly custom assemblies
- overly feature-rich hinged/latch systems unless the drawing is exceptionally clean
- sources that require high-friction automation

## Required Outputs

Create exactly 3 new artifact-backed intake notes.

Expected tracked outputs:

- `internal/reference_parts/intake-<artifact>.md` for 3 artifacts

Expected private outputs:

- raw files under `private/reference_intake/enclosures-and-covers/raw/<artifact>/`
- derived text under `private/reference_intake/enclosures-and-covers/derived/<artifact>/`
- manifest updates in `private/reference_intake/enclosures-and-covers/manifest.json`

## Preservation Rule

Treat existing local coordination files as append-only unless the task explicitly authorizes a migration.

For `private/reference_intake/enclosures-and-covers/manifest.json`:

- read the current file before editing it
- preserve prior artifact entries
- add new entries or update matching entries in place
- do not replace the manifest schema unless explicitly asked
- if the current manifest shape conflicts with your intended update, stop and report the mismatch instead of rewriting it

## Allowed Tools And Method

- normal browsing
- occasional manual download
- local text extraction
- local note filling

Do not:

- do high-rate crawling
- bulk scrape
- try to mirror a library

## Artifact Strength Rule

Only keep artifacts that are at least `medium`, and prefer `strong`.

Strong means:

- dimensioned PDF drawing, or
- drawing plus clear product-page dimensions

Medium means:

- product page with dimensions but weaker drawing support

If an artifact is weak, discard it and move on.

## Stop Conditions

Stop when any one of these is true:

1. 3 good artifact-backed intake notes are complete
2. 90 minutes is spent and fewer than 3 strong artifacts are found
3. official sources are too sparse and the task needs orchestrator review

## Required Closeout Verification

Before reporting completion:

- list the exact local raw files created
- list the exact local derived files created
- verify those files exist locally

Status rules:

- `identified_only`
  - source found, but no local raw artifact staged
- `identified_but_missing_drawing`
  - candidate found and dimension data exists, but no local drawing artifact is staged
- `derived_only_missing_raw`
  - derived notes or extraction exist, but raw artifact is not staged locally
- `complete`
  - local drawing artifact exists
  - derived file exists locally if claimed
  - intake note points to the local files

Do not report `complete` if the local drawing artifact is missing.

## Report Back With

- the 3 artifacts acquired
- why each was kept
- which candidate seems strongest for a future workflow slice
- any source friction that suggests process improvement

## Nice-To-Have

- prefer sources not already used in the first intake round
- if a flanged wall-mount enclosure with a clean drawing is found, call it out explicitly
