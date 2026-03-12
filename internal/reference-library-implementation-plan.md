# Reference Library Implementation Plan

This is an intermediate working plan for building a token-efficient part-family library from normalized reference inputs.

It is not canonical product guidance.
Use it to coordinate orchestrator work, worker execution, scripted preprocessing, and promotion decisions.

## Purpose

Build a repeatable intake-to-workflow pipeline that:

- starts from externally verifiable reference material
- converts raw inputs into normalized part-family notes
- keeps raw source material out of shared canon
- minimizes repeated AI interpretation work
- selects high-value workflow slices that fit the current validated vocabulary

## Success Criteria

The plan is working when:

- implementation candidates are backed by explicit reference artifacts
- candidate parts can be added through a stable template
- family shortlists can be compared without rereading raw material
- worker tasks are small, explicit, and validation-bound
- routine preprocessing is handled by scripts or fixed algorithms where possible
- only synthesized geometry rules and constraints are promoted into shared tracked docs

## Roles

### Orchestrator

Use for:

- choosing families and priorities
- defining intake rules
- synthesizing normalized specs from reviewed inputs
- scoring and selecting candidates
- deciding what is canon vs working artifact vs private raw input
- writing worker-safe tasks and stop conditions

Should produce:

- family shortlist docs
- normalized part specs
- task briefs
- promotion decisions
- updated handoff context

### Worker

Use for:

- bounded spec extraction from already-selected material
- template filling
- small doc maintenance
- implementing one workflow slice
- writing targeted tests
- running targeted validation and live smokes
- reporting drift or ambiguity

Should not do by default:

- broad research sprees
- canon rewrites without explicit tasking
- open-ended source interpretation across many candidates

### Scripted / Algorithmic Support

Use for:

- file conversion
- text extraction
- page splitting
- image cropping
- folder indexing
- checklist generation
- candidate scoring from explicit rubric fields
- consistency checks over normalized spec files

Do not use scripts for:

- final judgment about fit-critical interpretation
- ambiguous geometry reconstruction
- promotion decisions

## Resource Types

### Preferred Inputs

- dimensioned PDF drawings
- orthographic drawings with callouts
- dimension tables
- clean assembly instructions with labeled parts
- exploded diagrams with part callouts
- structured screenshots from viewers

### Acceptable but Weaker Inputs

- marketing sheets with partial dimensions
- assembly diagrams without full dimensions
- screenshots of CAD listings

### Weak Inputs

- plain photos
- unlabeled renders
- low-resolution scans with missing callouts

## Conversion Strategy

Convert inputs into forms that reduce future token use.

### Recommended Conversions

- PDF to plain text for dimension tables and searchable notes
- PDF pages to images for view-by-view review
- multi-page packets split into one file per relevant page
- cropped images for isolated parts or views
- normalized markdown spec files for final repo use

### Exploded Diagram Handling

Exploded diagrams are useful for:

- separating candidate parts
- inferring body-count intent
- identifying mating relationships
- spotting repeat parts and symmetry

Exploded diagrams are weak for:

- exact dimensions without callouts
- exact feature depths
- tolerance extraction

Default rule:

- use exploded diagrams to identify candidate parts and interfaces
- do not treat them as sufficient geometry definition on their own

## Shared vs Private Boundary

Shared tracked space should contain:

- normalized family shortlists
- normalized part specs
- scoring results
- workflow mapping notes
- implementation and validation results

Private local space may contain:

- raw input packets
- screenshots
- extracted page images
- temporary OCR output
- rough scratch notes
- local intake manifests

Do not promote raw packets into shared canon.

## File Layout

### Shared tracked

- `internal/reference_parts/README.md`
- `internal/reference_parts/TEMPLATE.part-spec.md`
- `internal/reference_parts/TEMPLATE.reference-intake.md`
- `internal/reference_parts/<family>-shortlist.md`
- `internal/reference_parts/<part-name>.md`
- `internal/reference_parts/<family>-scorecard.md`

### Private local

- `private/reference_intake/<family>/raw/`
- `private/reference_intake/<family>/derived/`
- `private/reference_intake/<family>/scratch/`
- `private/reference_intake/<family>/manifest.json`

## Work Phases

### Phase 1: Intake Method

Goal:

- define file handling and normalization rules

Tasks:

- pick one family
- collect a small candidate set
- convert raw material into stable reviewable forms
- record candidate artifact state in a local intake manifest
- write one reference-intake note per candidate artifact
- write one shortlist file

Exit condition:

- at least 3 candidates in one family are backed by explicit reference artifacts and normalized enough to compare

### Phase 2: Candidate Normalization

Goal:

- turn each candidate into a compact reusable spec

Tasks:

- start from a specific reference artifact, not just a concept label
- fill the part-spec template
- extract only workflow-relevant geometry and interfaces
- mark unknowns explicitly
- classify input quality

Exit condition:

- each candidate can be understood without reopening the raw packet

### Phase 3: Scoring and Selection

Goal:

- choose the next implementation slice with low ambiguity

Tasks:

- score each candidate against the rubric
- map it to current validated operations
- tag it as:
  - `current-vocabulary`
  - `one-new-operation`
  - `defer`
- choose the best first slice

Exit condition:

- one candidate is selected with a clear reason and stop condition

### Phase 4: Workflow Delivery

Goal:

- implement one narrow workflow slice

Tasks:

- write schema changes
- implement workflow stages
- add targeted tests
- add live smoke if the slice qualifies
- record validation

Exit condition:

- the new slice passes targeted local validation and any required live smoke

### Phase 5: Feedback Loop

Goal:

- improve the intake method based on implementation friction

Tasks:

- note which fields were missing or over-specified
- refine the template
- refine the scoring rubric
- refine conversion scripts

Exit condition:

- the next intake cycle is cheaper and clearer

## Needs Checklist

Before selecting a part, confirm:

- a specific reference artifact exists
- functional intent is clear
- body-count intent is clear
- fit-critical interfaces are identifiable
- major dimensions are recoverable
- current-vocabulary mapping is plausible
- unknowns are bounded

For enclosure-family candidates, also confirm:

- the intended opening face is clear from the artifact
- the candidate can be validated as an enclosure body rather than a sleeve or cap-only shell
- floor and wall intent can be checked semantically, not only inferred from outer dimensions

If more than two major geometry unknowns remain, defer the part.

## Task Delegation Model

### Good Orchestrator Tasks

- create or revise shortlist files
- synthesize one normalized spec from reviewed material
- score and rank candidates
- decide whether a candidate is implement-now or defer
- write the worker brief for implementation

### Good Worker Tasks

- convert one selected packet into cropped/text-extracted working files
- fill one normalized spec from a preselected candidate
- implement one workflow slice from an approved spec
- add targeted tests for one slice
- run exact validation commands and report results

When workers update local coordination files such as intake manifests, they should preserve existing entries and treat those files as append-only unless a migration is explicitly authorized.

When a worker packet is for drawing-backed intake, the packet must define completion in terms of locally staged drawing artifacts, not just source identification or copied dimensions.

### Good Script Tasks

- rename and organize files
- split PDFs into per-page derivatives
- OCR tables into plain text
- generate spec skeleton files from a family shortlist
- update local intake manifest entries
- validate front-matter fields in normalized spec docs
- generate scorecard summaries from filled templates

## Token-Efficiency Rules

- review raw inputs once, then work from normalized specs
- do not promote a concept-level candidate into implementation without a backing reference artifact
- keep each normalized part spec short
- prefer fixed templates over freeform writeups
- prefer one family at a time
- prefer one selected implementation target at a time
- script repeated conversions and checks as soon as the pattern stabilizes
- do not carry low-value raw context into implementation sessions

## Scoring Rubric

Score each candidate from 1 to 5 on:

- interface clarity
- dimension completeness
- fit-critical usefulness
- reuse of current validated operations
- amount of new geometry required
- validation tractability
- real-world utility

Decision rule:

- high utility + high clarity + low novelty = implement first
- high utility + medium clarity + one new operation = keep near-term
- low clarity or high ambiguity = defer

## First Family Recommendation

Start with:

- enclosures and covers

Reason:

- aligns with the current development ladder
- reuses landed `shell` work
- supports multiple follow-on slices after the first body workflow

Suggested initial candidate set:

- flanged junction box body
- friction-fit lid with stepped lip
- terminal block splash shield

## Immediate Next Tasks

1. Add the reference-backed intake template and intake checklist.
2. Create the first family shortlist file for enclosures and covers.
3. Create reference-backed candidate notes for 3 initial artifacts.
4. Fill normalized part-spec files from those artifacts.
5. Fill a family scorecard and select the first implementation slice.
