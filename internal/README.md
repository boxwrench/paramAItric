# Internal Working Artifacts

This folder is shared working space, not automatic canon.

Use it for:

- temporary validation harnesses
- freeform recipe replays
- exploratory runners
- architecture notes that are useful to contributors but are not user-facing product docs

Default rule:

- do not treat files here as adopted guidance just because they are tracked
- do not assume runners here still match the latest freeform or workflow contracts
- if an internal harness becomes operationally important, revalidate it deliberately and then either:
  - promote the behavior into tests or canon docs
  - or keep it clearly labeled as a working artifact

## File Status

### Docs

| File | Status | Notes |
|------|--------|-------|
| `freeform-architecture.md` | working-artifact | Architecture note for the freeform lane. Referenced from README. |
| `test-recipes.md` | working-artifact | Recipe corpus and validation cases. Broader than adopted live scope. Referenced from README. |

### Python Runners

Removed 2026-07-12 (see `HOUSEKEEPING.md`). These were one-off manual runners with no
references in live code. The promoted equivalents live in `scripts/` —
`freeform_recipe_c_smoke.py` and `freeform_failure_recovery_smoke.py` — and the
`test-recipes.md` corpus above records the recipe cases.

### Reference Parts

Reference-part intake material (vendor specs, intake notes, shortlists, scorecards) now lives in
**`private/reference_parts/`**, which is gitignored and local-only — it is benchmark planning
material containing third-party commercial part specs, not adopted canon and not for public
release. `scripts/scaffold_reference_intake.py` writes new intake notes there.

### Boundary Notes

- `internal/research/` — placeholder boundary note only; raw generated research lives in local `private/research/`
