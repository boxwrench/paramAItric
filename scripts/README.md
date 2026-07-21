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
| `install_paramaitric.py` | active | Dependency-free setup dashboard, `--check` doctor mode, Claude config writer, and MCP config snippet generator for Claude Desktop / Cursor. |
| `freeform_verification_smoke.py` | working-artifact | Earlier narrow verification smoke (sketch + rectangle). Not adopted. |
| `fusion_smoke_test.py` | active | General-purpose live smoke runner (`--workflow spacer`, etc.) |
| `hammond_1590ee_flush_lid_smoke.py` | active | Runs `flush_lid_enclosure_pair` with the current normalized Hammond 1590EE envelope and conservative closure assumptions. |
| `scaffold_reference_intake.py` | active | Creates tracked intake notes plus private raw/derived/scratch folders for reference-library candidates. |
| `validate_mcmaster_bracket.py` | in-progress | McMaster strut channel bracket validation. |

## Migration Scripts (removed 2026-07-12)

The one-time workflow-migration and plate-rebuild tooling was removed in the
housekeeping pass (see `../docs/archive/planning/HOUSEKEEPING.md`); it had no references in live code. The
migration process is preserved for history under
[`docs/archive/migration/`](../docs/archive/migration/), and the narrative is in
[`docs/dev-log.md`](../docs/dev-log.md).
