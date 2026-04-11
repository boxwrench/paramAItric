# Workflow Migration Process

This document describes the working process for migrating workflows from the monolithic `server.py` to the mixin architecture.

## Quick Reference

**When to use this process:**
- Migrating multiple workflows from the same family (plates, cylinders, enclosures, etc.)
- Need to extract shared helpers along with workflows
- Want automated insertion with proper indentation

**When NOT to use this process:**
- Single workflow migration (use manual extraction instead)
- Simple workflow with no dependencies (copy-paste is faster)
- Debugging/experimenting (overhead not worth it)

## Prerequisites

- Original server.py preserved at `C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py`
- Target mixin file exists (or use `migrate_workflows.py` to create)
- Tests exist for workflows being migrated

## The Process

### Step 1: Generate Clean Boilerplate

If the mixin file doesn't exist or is corrupted:

```bash
python scripts/migrate_workflows.py \
  --source C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py \
  --output-dir /c/tmp/regenerate
```

Copy the relevant file to the workflows directory:
```bash
cp /c/tmp/regenerate/plates_migrated.py mcp_server/workflows/plates.py
```

This creates a clean mixin file with:
- All imports
- Public API methods (calling missing private methods)
- Placeholder comments for TODO implementations
- Abstract method declarations

### Step 2: Extract Workflows

For each workflow to migrate:

```bash
python /c/tmp/extract_workflow_fixed.py --workflow <name> > /c/tmp/wf_<name>.py
```

Example:
```bash
for workflow in counterbored_plate two_hole_plate four_hole_mounting_plate; do
  python /c/tmp/extract_workflow_fixed.py --workflow $workflow > /c/tmp/wf_${workflow}.py
done
```

This extracts the complete `_create_<name>_workflow` method using AST.

### Step 3: Extract Shared Helpers (if needed)

If workflows depend on shared helpers:

```bash
python /c/tmp/extract_helpers.py
```

This extracts:
- `_create_base_plate_body`
- `_run_circle_cut_stage`
- `_run_rectangle_cut_stage`
- `_verify_body_against_expected_dimensions`
- `_matching_profiles_by_dimensions`
- `_select_profile_by_dimensions`

Outputs to `/c/tmp/helper_<name>.py`

### Step 4: Insert into Mixin

```bash
python /c/tmp/insert_into_plates.py
```

This:
- Reads all `/c/tmp/wf_*.py` files
- Reads all `/c/tmp/helper_*.py` files
- Indents code properly (4 spaces for class level)
- Inserts into correct sections
- Preserves boilerplate structure

### Step 5: Verify

```bash
# Check syntax and structure
python scripts/verify_migration.py

# Run tests for migrated workflows
pytest tests/test_workflow.py -k "<workflow_name>" -v
```

## Scripts Reference

### extract_workflow_fixed.py

**Purpose:** Extract a complete workflow method using AST

**Usage:**
```bash
python extract_workflow_fixed.py --workflow <name>
```

**Output:** Complete `_create_<name>_workflow` method, dedented (class-level indent removed)

**Why AST:** The original `extract_workflow.py` used regex which sometimes grabbed incomplete methods. AST guarantees complete method extraction by following Python's parse tree.

### extract_helpers.py

**Purpose:** Extract all shared helper methods

**Usage:**
```bash
python extract_helpers.py
```

**Output:** Six files in `/c/tmp/helper_*.py`

**When to run:** When migrating workflows that call shared helpers (most plate workflows)

### insert_into_plates.py

**Purpose:** Insert extracted code into boilerplate

**Usage:**
```bash
python insert_into_plates.py
```

**What it does:**
1. Reads all `/c/tmp/wf_*.py` files
2. Reads all `/c/tmp/helper_*.py` files
3. Indents each line with 4 spaces (for class body)
4. Inserts workflows into "Private workflow implementations" section
5. Inserts helpers into "Shared helper methods" section
6. Writes updated `mcp_server/workflows/plates.py`

**Note:** Currently hardcoded for plates.py. To adapt for other mixins:
- Update `plates_path` variable
- Update marker strings for section detection
- Update workflow list

## Troubleshooting

### "Syntax error after insertion"

Check that:
1. All workflow files in `/c/tmp/wf_*.py` are complete (have return statement at end)
2. No duplicate method names
3. Boilerplate file wasn't manually edited between steps

### "Missing helper method"

If a workflow calls a helper not in the standard list:
1. Add helper name to `extract_helpers.py` helpers list
2. Re-run `extract_helpers.py`
3. Re-run `insert_into_plates.py`

### "Test fails with AttributeError"

The public API method is calling a private method that wasn't inserted. Check:
1. Workflow was extracted: `ls /c/tmp/wf_<name>.py`
2. Insert script ran successfully
3. No naming mismatch (e.g., `two_hole_plate` vs `two_hole_mounting_plate`)

## Adapting for Other Mixins

To migrate cylinder workflows using same process:

1. **Create boilerplate:**
   ```bash
   python scripts/migrate_workflows.py --output-dir /c/tmp/regenerate
   cp /c/tmp/regenerate/cylinders_migrated.py mcp_server/workflows/cylinders.py
   ```

2. **Create adapted insertion script:**
   - Copy `insert_into_plates.py` to `insert_into_cylinders.py`
   - Update `plates_path` to `cylinders_path`
   - Update workflow list to cylinder workflows
   - Update helper list (cylinders have different helpers)

3. **Extract and insert:**
   ```bash
   # Extract workflows
   for workflow in cylinder tube revolve; do
     python /c/tmp/extract_workflow_fixed.py --workflow $workflow > /c/tmp/wf_${workflow}.py
   done

   # Insert
   python /c/tmp/insert_into_cylinders.py
   ```

## Migration Checklist

- [ ] Back up current mixin file (optional - boilerplate is clean)
- [ ] Generate fresh boilerplate
- [ ] Extract all workflows for this family
- [ ] Extract all helpers needed
- [ ] Run insertion script
- [ ] Verify syntax: `python -m py_compile mcp_server/workflows/<mixin>.py`
- [ ] Run verification: `python scripts/verify_migration.py`
- [ ] Run tests: `pytest tests/test_workflow.py -k "<family>" -v`
- [ ] Update WORKFLOW_MIGRATION_GUIDE.md status
- [ ] Update dev-log.md with progress

## Historical Context

**What didn't work:**
- Regex-based extraction (`extract_workflow.py`) - got incomplete methods
- Manual copy-paste with sed - indentation errors, took too long
- Batch migration without boilerplate - messy structure

**What worked:**
- AST-based extraction (guarantees complete methods)
- Boilerplate-first (clean structure)
- Automated insertion (consistent indentation)

**Time comparison:**
- Manual (first 3 workflows): ~2 hours, lots of errors
- This process (remaining 6 workflows): ~20 minutes, zero errors
