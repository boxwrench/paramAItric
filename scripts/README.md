# Scripts

## Adopted Live Smokes

These are the adopted trust probes. See [`docs/VERIFICATION_POLICY.md`](../docs/VERIFICATION_POLICY.md) for the live checklist, scope boundary, and failure rules.

| Script | Path | Purpose |
|--------|------|---------|
| Recipe C smoke | `freeform_recipe_c_smoke.py` | Positive path: non-monotonic volume, body-count deltas, combine, audit reporting |
| Failure recovery smoke | `freeform_failure_recovery_smoke.py` | Negative path: failed hard-gate, inspection-before-recovery, corrected commit |

## Other Scripts

| Script | Status | Purpose |
|--------|--------|---------|
| `freeform_verification_smoke.py` | working-artifact | Earlier narrow verification smoke (sketch + rectangle). Not adopted. |
| `fusion_smoke_test.py` | active | General-purpose live smoke runner (`--workflow spacer`, etc.) |
| `hammond_1590ee_flush_lid_smoke.py` | active | Runs `flush_lid_enclosure_pair` with the current normalized Hammond 1590EE envelope and conservative closure assumptions. |
| `scaffold_reference_intake.py` | active | Creates tracked intake notes plus private raw/derived/scratch folders for reference-library candidates. |
| `test_yz_cut_fix.py` | exploratory | YZ plane cut investigation. Unconfirmed. |
| `validate_mcmaster_bracket.py` | in-progress | McMaster strut channel bracket validation. |
