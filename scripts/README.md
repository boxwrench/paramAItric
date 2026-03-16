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

## Migration Scripts

See [`docs/MIGRATION_PROCESS.md`](../docs/MIGRATION_PROCESS.md) and [`docs/MIGRATION_STRATEGY.md`](../docs/MIGRATION_STRATEGY.md) for comprehensive guides.

### Core Migration Tools

| Script | Purpose | Usage Example |
|--------|---------|---------------|
| `extract_workflow_fixed.py` | Extract complete workflow using AST | `python extract_workflow_fixed.py --workflow counterbored_plate` |
| `extract_helpers.py` | Extract shared helper methods | `python extract_helpers.py` |
| `insert_into_plates.py` | Insert workflows into boilerplate | `python insert_into_plates.py` |
| `migrate_workflows.py` | Generate clean boilerplate | `python migrate_workflows.py --output-dir /c/tmp/regenerate` |
| `verify_migration.py` | Validate migration integrity | `python verify_migration.py` |

### Legacy/Experimental Scripts

| Script | Status | Notes |
|--------|--------|-------|
| `extract_workflow.py` | legacy | Regex-based, use `extract_workflow_fixed.py` instead |
| `build_plates.py` | experimental | Early assembly attempt, superseded |
| `insert_workflows.py` | experimental | Generic insertion attempt |
| `rebuild_plates.py` | superseded | Manual rebuilding script |
| `rebuild_plates2.py` | superseded | Second iteration |
| `dedupe_methods.py` | utility | Method deduplication helper |
| `fix_plates.py` | one-time | Fixed specific plates.py corruption |

### Quick Migration Workflow

```bash
# 1. Generate boilerplate
python migrate_workflows.py --output-dir /c/tmp/regenerate
cp /c/tmp/regenerate/plates_migrated.py mcp_server/workflows/plates.py

# 2. Extract workflows
for wf in counterbored_plate recessed_mount slotted_mount; do
  python extract_workflow_fixed.py --workflow $wf > /c/tmp/wf_${wf}.py
done

# 3. Extract helpers
python extract_helpers.py

# 4. Insert into mixin
python insert_into_plates.py

# 5. Verify
python verify_migration.py
pytest tests/test_workflow.py -k "plate" -v
```
