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

| File | Status | Notes |
|------|--------|-------|
| `freeform_a_bracket.py` | exploratory | Freeform recipe A replay. Not promoted. |
| `freeform_b_cable_guide.py` | exploratory | Freeform recipe B replay. Not promoted. |
| `freeform_c_boss_plate.py` | superseded | Adopted version is `scripts/freeform_recipe_c_smoke.py`. |
| `freeform_d_lid_clips.py` | exploratory | Freeform recipe D replay. Not promoted. |
| `freeform_e_recovery.py` | superseded | Adopted version is `scripts/freeform_failure_recovery_smoke.py`. |
| `agent_disciplined_strut.py` | working-artifact | Strut channel bracket agent runner. |
| `agent_freeform_emulator.py` | working-artifact | Freeform emulator agent runner. |
| `live_recipe_validation.py` | working-artifact | Live recipe validation harness. |
| `live_run_recipe1.py` | working-artifact | Live workflow smoke for recipe 1. |
| `live_run_recipe2.py` | working-artifact | Live workflow smoke for recipe 2. |
| `live_run_recipe3.py` | working-artifact | Live workflow smoke for recipe 3. |
| `live_run_recipe4.py` | working-artifact | Live workflow smoke for recipe 4. |
| `live_run_recipe5.py` | working-artifact | Live workflow smoke for recipe 5. |
| `official_macro_validation.py` | working-artifact | Official workflow macro validation harness. |
| `visualize_r1_separated.py` | working-artifact | Recipe 1 visualization helper. |

### Reference Parts

| File | Status | Notes |
|------|--------|-------|
| `reference_parts/ideas.md` | working-artifact | Benchmark part ideas by category. Not adopted as targets. |
| `reference_parts/strut_channel_bracket_33125T421.md` | working-artifact | McMaster bracket dimensional spec. Linked from strut investigation. |
| `reference_parts/README.md` | working-artifact | Collection overview. Has a UTF-16 encoding issue — re-encode if promoting. |

Moved here from `docs/reference_parts/` — this is benchmark planning material, not adopted canon.

### Boundary Notes

- `internal/research/` — placeholder boundary note only; raw generated research lives in local `private/research/`
