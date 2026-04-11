# Workflow Migration Strategy

This document provides a comprehensive strategy for migrating workflows from the monolithic `server.py` to the mixin architecture, incorporating lessons learned from both manual and scripted approaches.

## Lessons Learned

### Manual Migration (First 3 Workflows)

**What we did:**
- Extracted line ranges using `sed`
- Manually fixed indentation
- Copy-pasted into mixin files
- Tested immediately after each insertion

**Results:**
- Time: ~2 hours for 3 workflows
- Errors: Indentation issues, parameter mismatches, missing imports
- Success rate: 100% eventually, but multiple iterations per workflow

**Key insight:** Manual works but doesn't scale. Tedious, error-prone, mentally draining.

### Scripted Migration (Failed Attempts)

**Attempt 1: Regex-based extraction**
```python
# Used regex to find method boundaries
pattern = r'def _create_.*?(?=\ndef |\Z)'
```
**Failed:** Python methods can't be reliably parsed with regex. Nested functions, decorators, multi-line strings all break simple patterns.

**Attempt 2: Line number extraction**
```bash
sed -n '4884,5074p' server.py
```
**Failed:** Line numbers drift as server.py changes. Hardcoded ranges break. Methods have variable lengths.

**Attempt 3: Indentation-based detection**
```python
# Look for 4-space indent + def
if re.match(r'    def [^_]', line):
    # End of previous method
```
**Failed:** Doesn't account for decorators, docstrings, or nested classes.

**Key insight:** Text-based extraction is fragile. Need AST (Abstract Syntax Tree) parsing.

### Working Approach (Boilerplate + AST)

**What we did:**
1. Generate clean boilerplate with `migrate_workflows.py`
2. Extract complete methods using AST (`extract_workflow_fixed.py`)
3. Extract helpers with `extract_helpers.py`
4. Insert with automated indentation (`insert_into_plates.py`)

**Results:**
- Time: ~20 minutes for 9 workflows
- Errors: Zero (after script debugging)
- Success rate: 100% first try

**Key insight:** AST guarantees complete extraction. Boilerplate provides structure. Automation ensures consistency.

## Workflow Categorization

Not all workflows are equal. Categorize before choosing approach:

### Category 1: Simple Inline (Tier 1)
**Characteristics:**
- Public method validates input and has inline implementation
- No shared helpers needed
- Single-purpose, self-contained

**Examples:**
- `create_plate_with_hole` - validates, then inline stage sequence
- `create_bracket` - validates, then inline stage sequence

**Best approach:** Manual or boilerplate + copy-paste
**Time:** 5-10 minutes

### Category 2: Delegated with Helpers (Tier 2)
**Characteristics:**
- Public method validates, delegates to private `_create_*_workflow`
- Uses shared helper methods
- Common pattern: base plate + cuts

**Examples:**
- `create_spacer` → `_create_rectangular_prism_workflow`
- `create_counterbored_plate` → `_create_counterbored_plate_workflow` + `_run_circle_cut_stage`

**Best approach:** Boilerplate + AST extraction + helper extraction
**Time:** 2 minutes (automated)

### Category 3: Complex Multi-Stage (Tier 3)
**Characteristics:**
- Multiple private methods
- Complex stage sequencing
- May use multiple helpers
- Conditional logic (if/else based on parameters)

**Examples:**
- `create_box_with_lid` - creates multiple bodies
- `create_cable_gland_plate` - conditional mounting holes
- `create_slotted_mounting_plate` - multiple cut stages

**Best approach:** Boilerplate + AST extraction + manual review
**Time:** 5 minutes + review time

### Category 4: Unique/Special (Tier 4)
**Characteristics:**
- Doesn't fit existing patterns
- Custom geometry creation
- Special verification logic

**Examples:**
- `create_strut_channel_bracket`
- `create_ratchet_wheel`
- `create_tube_mounting_plate` (combines cylinder + plate patterns)

**Best approach:** Manual migration with custom logic
**Time:** 20-60 minutes

## Decision Tree

```
Start: Need to migrate workflow(s)
│
├─> Single workflow?
│   ├─> Simple inline (Tier 1)? ──> Manual copy-paste
│   └─> Complex (Tier 3-4)? ─────> Manual with attention
│
├─> Multiple workflows in same family?
│   ├─> All Tier 1? ─────────────> Manual or simple script
│   ├─> Mix of Tier 1-2? ────────> Boilerplate + AST extraction
│   └─> Any Tier 4? ─────────────> Extract Tier 1-3 automated, Tier 4 manual
│
└─> Whole mixin family (5+ workflows)?
    ├─> Plates/Cylinders (standard patterns)?
    │   └─> Boilerplate + AST extraction + helpers
    ├─> Brackets (mixed complexity)?
    │   └─> Boilerplate + per-workflow decision
    └─> Enclosures/Specialty (mostly Tier 3-4)?
        └─> Manual migration recommended
```

## Migration Approaches by Scale

### Scale 1: Single Workflow (< 5 minutes)

**When:** Hotfix, single missing workflow, quick addition

**Process:**
1. Find method in original server.py using AST or grep
2. Copy to clipboard
3. Paste into mixin file
4. Add 4-space indentation
5. Add abstract method declaration if needed
6. Test

**Tools:** Editor, grep, manual editing

### Scale 2: Workflow Family (20-60 minutes)

**When:** Migrating all plate workflows, all cylinder workflows

**Process:**
1. **Boilerplate**: `migrate_workflows.py --output-dir /c/tmp/regenerate`
2. **Extract**: `extract_workflow_fixed.py` for each workflow
3. **Helpers**: `extract_helpers.py` if needed
4. **Insert**: `insert_into_<mixin>.py` (adapted for target)
5. **Verify**: `verify_migration.py` + pytest

**Tools:** Full script suite, 5-10 minutes per workflow

### Scale 3: Bulk Migration (2-4 hours)

**When:** Migrating remaining 20+ workflows

**Process:**
1. **Categorize**: Run analysis to categorize all workflows
2. **Batch Tier 1-2**: Use boilerplate + AST approach
3. **Review Tier 3**: AST extraction + manual review
4. **Manual Tier 4**: Migrate one by one with custom logic
5. **Integration**: Combine all into final mixin files
6. **Full test**: Run complete test suite

**Tools:** All scripts + manual work for edge cases

## Risk Assessment

### High Risk (Manual Recommended)
- Workflows with complex conditional logic
- Workflows using features not in boilerplate
- Workflows with custom verification patterns
- **Mitigation:** Manual migration with thorough testing

### Medium Risk (AST + Review)
- Workflows using multiple helpers
- Workflows with nested function calls
- Workflows with many stages (>10)
- **Mitigation:** Automated extraction + manual review before test

### Low Risk (Full Automation)
- Standard plate patterns (base + cuts)
- Simple cylinder patterns
- Workflows following established patterns
- **Mitigation:** Full automation, spot-check tests

## Workflow Analysis for Remaining Work

Based on patterns observed, here's the categorization of remaining workflows:

### CylinderWorkflowsMixin (9 workflows)
| Workflow | Tier | Approach | Notes |
|----------|------|----------|-------|
| `create_cylinder` | 1 | ✓ Done | Simple inline |
| `create_tube` | 1 | ✓ Done | Simple inline |
| `create_revolve` | 2 | Automated | Uses `_create_revolved_body` |
| `create_tapered_knob_blank` | 2 | Automated | Standard revolve pattern |
| `create_flanged_bushing` | 2 | Automated | Multiple extrudes |
| `create_shaft_coupler` | 2 | Automated | Standard pattern |
| `create_pipe_clamp_half` | 3 | Automated + review | Complex geometry |
| `create_tube_mounting_plate` | 4 | Manual | Combines cylinder + plate |
| `create_t_handle_with_square_socket` | 3 | Automated + review | Multi-part |

**Recommended approach:** Boilerplate + AST for Tier 2-3, manual for Tier 4

### EnclosureWorkflowsMixin (8 workflows)
| Workflow | Tier | Approach | Notes |
|----------|------|----------|-------|
| `create_simple_enclosure` | 3 | Automated + review | Shell operation |
| `create_open_box_body` | 3 | Automated + review | Base + cut |
| `create_lid_for_box` | 3 | Automated + review | Paired with box |
| `create_box_with_lid` | 3 | Automated + review | Two bodies |
| `create_flush_lid_enclosure_pair` | 3 | Automated + review | Multi-part |
| `create_project_box_with_standoffs` | 4 | Manual | Standoffs + enclosure |
| `create_snap_fit_enclosure` | 4 | Manual | Snap features |
| `create_telescoping_containers` | 4 | Manual | Multi-container |

**Recommended approach:** Mostly Tier 3, needs review. Consider manual for half.

### BracketWorkflowsMixin (7 workflows)
| Workflow | Tier | Approach | Notes |
|----------|------|----------|-------|
| `create_bracket` | 1 | ✓ Done | Simple inline |
| `create_filleted_bracket` | 2 | Automated | Base + fillet |
| `create_chamfered_bracket` | 2 | Automated | Base + chamfer |
| `create_mounting_bracket` | 2 | Automated | Holes pattern |
| `create_two_hole_mounting_bracket` | 2 | Automated | Specific hole pattern |
| `create_triangular_bracket` | 3 | Automated + review | Different geometry |
| `create_l_bracket_with_gusset` | 3 | Automated + review | Gusset addition |

**Recommended approach:** Mostly Tier 2, good for automation

### SpecialtyWorkflowsMixin (3 workflows)
| Workflow | Tier | Approach | Notes |
|----------|------|----------|-------|
| `create_strut_channel_bracket` | 4 | Manual | Complex profile |
| `create_ratchet_wheel` | 4 | Manual | Specialized geometry |
| `create_wire_clamp` | 4 | Manual | Custom features |

**Recommended approach:** All Tier 4, manual migration

## Recommended Next Steps

### Option A: Continue with Cylinders (Recommended)
- 6 remaining workflows
- Mostly Tier 2 (automatable)
- Can adapt existing scripts
- Estimated time: 30 minutes

### Option B: Tackle Brackets
- 6 remaining workflows
- All Tier 2 (good for automation)
- Similar patterns to plates
- Estimated time: 30 minutes

### Option C: Pause and Document
- Current state is stable (9 workflows working)
- Good demonstration of process
- Can resume later with same approach

### Option D: Address Enclosures
- 8 workflows, mostly Tier 3-4
- More complex, needs attention
- Estimated time: 2-3 hours
- May require helper development

## Tool Evolution

As we migrate more families, scripts should evolve:

### Current State
- `extract_workflow_fixed.py` - Single workflow extraction
- `extract_helpers.py` - All plate helpers
- `insert_into_plates.py` - Plates-specific insertion

### Next Iteration
- `extract_workflows.py` - Batch workflow extraction
- `extract_helpers_family.py` - Family-specific helpers
- `insert_into_mixin.py` - Generic mixin insertion
- `analyze_workflows.py` - Auto-categorize workflows

### Future Vision
- `migrate_family.py --family cylinders` - One-command migration
- Interactive workflow categorization
- Automatic test generation
- Regression testing suite

## Success Metrics

Track these for each migration batch:

1. **Time per workflow**: Target < 5 minutes for Tier 2
2. **Test pass rate**: Target 100% before proceeding
3. **Manual interventions**: Track which workflows needed manual fix
4. **Script reliability**: Success rate of automated extraction

## Conclusion

The **Boilerplate + AST extraction** approach works for:
- Workflow families with shared patterns
- Tier 1-3 workflows
- Bulk migration scenarios

Manual approach still needed for:
- Tier 4 (unique/complex) workflows
- Initial script development
- Edge cases and debugging

The key is **categorization** - choose the right tool for the complexity level.
