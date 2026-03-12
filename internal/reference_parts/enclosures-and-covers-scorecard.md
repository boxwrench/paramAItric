# Enclosures And Covers Scorecard

Scores use the 1 to 5 rubric from [`../reference-library-implementation-plan.md`](../reference-library-implementation-plan.md).

## Candidates

| Candidate | Interface clarity | Dimension completeness | Fit-critical usefulness | Reuse of current operations | New geometry required | Validation tractability | Real-world utility | Total | Classification |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Flanged junction box body | 4 | 3 | 4 | 4 | 3 | 4 | 5 | 27 | one-new-operation |
| Friction-fit lid with stepped lip | 3 | 3 | 5 | 3 | 3 | 3 | 5 | 25 | one-new-operation |
| Terminal block splash shield | 2 | 2 | 3 | 3 | 2 | 2 | 4 | 18 | defer |

## Interpretation

- `flanged junction box body` is the best first family anchor.
- `friction-fit lid with stepped lip` is the strongest second slice after a box-body baseline exists.
- `terminal block splash shield` stays in the family, but should not lead.

## First Pivot Rule

If `flanged junction box body` can be expressed using the current enclosure and combine vocabulary with only a narrow ear-placement pattern, implement it directly.

If the work reveals that exterior ear placement on shelled bodies is unstable or too ad hoc, pivot the next task to validating that placement pattern as its own reusable workflow building block before continuing the family.

## Selected Next Target

- `flanged junction box body`

## Worker Brief Shape

- objective:
  - determine whether `flanged junction box body` fits current vocabulary or needs one explicit new placement primitive/pattern
- read first:
  - `internal/reference_parts/flanged-junction-box-body.md`
  - `DEVELOPMENT_PLAN.md`
  - relevant existing enclosure workflow code only
- validation:
  - targeted tests for the chosen path only
- stop conditions:
  - stop once the slice is classified as direct-implement vs primitive/pattern-pivot
