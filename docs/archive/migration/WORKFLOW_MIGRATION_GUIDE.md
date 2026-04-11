# Workflow Migration Guide

This guide helps migrate remaining workflows from the original monolithic `server.py` to the new mixin architecture.

## Current Status (2026-03-15)

**Summary**: Plate and Cylinder workflows migration complete!

### ✅ Complete (tests passing)

**PlateWorkflowsMixin** - All 9 workflows migrated:
- `create_spacer`
- `create_plate_with_hole`
- `create_two_hole_plate`
- `create_four_hole_mounting_plate`
- `create_slotted_mounting_plate`
- `create_counterbored_plate`
- `create_recessed_mount`
- `create_slotted_mount`
- `create_cable_gland_plate`

**CylinderWorkflowsMixin** - All 9 workflows migrated:
- `create_cylinder`
- `create_tube`
- `create_revolve`
- `create_tapered_knob_blank`
- `create_flanged_bushing`
- `create_shaft_coupler`
- `create_pipe_clamp_half`
- `create_t_handle_with_square_socket`
- `create_tube_mounting_plate`

**BracketWorkflowsMixin** - All 7 workflows migrated:
- `create_bracket`
- `create_filleted_bracket`
- `create_chamfered_bracket`
- `create_mounting_bracket`
- `create_two_hole_mounting_bracket`
- `create_triangular_bracket`
- `create_l_bracket_with_gusset`

### 📋 Still Pending
- 8 enclosure workflows
- 3 specialty workflows

**Approach used**: Boilerplate-first + AST-based extraction
1. Generated clean boilerplate with `migrate_workflows.py`
2. Extracted complete methods using AST (`extract_workflow_fixed.py`)
3. Inserted with proper indentation (`insert_into_plates.py`)
4. Verified with `verify_migration.py` and tests

### ✅ Complete (tests passing)
- `create_bracket` (BracketWorkflowsMixin)
- `create_spacer` (PlateWorkflowsMixin)
- `create_plate_with_hole` (PlateWorkflowsMixin)
- `create_two_hole_plate` (PlateWorkflowsMixin)
- `create_four_hole_mounting_plate` (PlateWorkflowsMixin)
- `create_slotted_mounting_plate` (PlateWorkflowsMixin)
- `create_cylinder` (CylinderWorkflowsMixin)
- `create_tube` (CylinderWorkflowsMixin)

### 🟡 Partial (public API done, private impl pending)
- `create_counterbored_plate` (PlateWorkflowsMixin) - needs helpers
- `create_recessed_mount` (PlateWorkflowsMixin) - needs helpers
- `create_slotted_mount` (PlateWorkflowsMixin) - needs helpers
- `create_cable_gland_plate` (PlateWorkflowsMixin) - needs helpers

### 📋 Not Started (stubs only)
- All enclosure workflows (8)
- All cylinder workflows except cylinder/tube (6)
- All specialty workflows (3)
- `create_filleted_bracket`, `create_chamfered_bracket`, etc.

**Test Status**: 22 workflows with passing tests, 15 still stubs

## Migration Options (When Resuming)

### Option A: Fix Automated Extraction
**Approach**: Improve `extract_workflow.py` to use AST for complete method extraction
**Pros**: Fast, scalable, reproducible
**Cons**: Requires debugging indentation and dependency tracking
**Effort**: 2-3 hours to get script working reliably

### Option B: Manual One-by-One
**Approach**: Extract each workflow individually using verified line ranges
**Pros**: Guaranteed correct, immediate test feedback
**Cons**: Tedious, slower
**Effort**: 30 min per workflow × 29 remaining = 14-15 hours

### Option C: Boilerplate-First
**Approach**: Use `migrate_workflows.py` output, manually fill TODO sections
**Pros**: Clean structure, no extraction complexity
**Cons**: Still requires manual implementation of each workflow
**Effort**: 20 min per workflow × 29 remaining = 10 hours

### Option D: On-Demand Migration
**Approach**: Only migrate workflows as needed for new features
**Pros**: No upfront cost, focuses effort
**Cons**: May hit maintenance issues later
**Effort**: Variable

**Current Recommendation**: Option B for critical workflows (counterbored_plate, cable_gland_plate), Option D for remainder.

## Migration Checklist

Use this checklist for each workflow you migrate:

- [ ] Copy workflow methods from original server.py to appropriate mixin
- [ ] Update imports in the mixin file
- [ ] Add public API method to mixin class
- [ ] Ensure private implementation method follows naming convention
- [ ] Update `__all__` in `workflows/__init__.py` if adding new exports
- [ ] Run tests to verify: `pytest tests/test_workflow.py::test_create_<workflow_name> -v`
- [ ] Update this checklist when complete

## Migration Status

### PlateWorkflowsMixin (`workflows/plates.py`)

| Workflow | Status | Assigned To |
|----------|--------|-------------|
| `create_spacer` | ✅ Migrated | 2026-03-14 |
| `create_plate_with_hole` | ✅ Migrated | 2026-03-14 |
| `create_two_hole_plate` | ✅ Migrated | 2026-03-14 |
| `create_four_hole_mounting_plate` | ✅ Migrated | 2026-03-14 |
| `create_slotted_mounting_plate` | ✅ Migrated | 2026-03-14 |
| `create_counterbored_plate` | ✅ Migrated | 2026-03-14 |
| `create_recessed_mount` | ✅ Migrated | 2026-03-14 |
| `create_slotted_mount` | ✅ Migrated | 2026-03-14 |
| `create_cable_gland_plate` | ✅ Migrated | 2026-03-14 |

### EnclosureWorkflowsMixin (`workflows/enclosures.py`)

| Workflow | Status | Assigned To |
|----------|--------|-------------|
| `create_simple_enclosure` | 📋 Pending | |
| `create_open_box_body` | 📋 Pending | |
| `create_lid_for_box` | 📋 Pending | |
| `create_box_with_lid` | 📋 Pending | |
| `create_flush_lid_enclosure_pair` | 📋 Pending | |
| `create_project_box_with_standoffs` | 📋 Pending | |
| `create_snap_fit_enclosure` | 📋 Pending | |
| `create_telescoping_containers` | 📋 Pending | |

### CylinderWorkflowsMixin (`workflows/cylinders.py`)

| Workflow | Status | Assigned To |
|----------|--------|-------------|
| `create_cylinder` | ✅ Migrated | 2026-03-14 |
| `create_tube` | ✅ Migrated | 2026-03-14 |
| `create_revolve` | ✅ Migrated | 2026-03-15 |
| `create_tapered_knob_blank` | ✅ Migrated | 2026-03-15 |
| `create_flanged_bushing` | ✅ Migrated | 2026-03-15 |
| `create_shaft_coupler` | ✅ Migrated | 2026-03-15 |
| `create_pipe_clamp_half` | ✅ Migrated | 2026-03-15 |
| `create_tube_mounting_plate` | ✅ Migrated | 2026-03-15 |
| `create_t_handle_with_square_socket` | ✅ Migrated | 2026-03-15 |

### SpecialtyWorkflowsMixin (`workflows/specialty.py`)

| Workflow | Status | Assigned To |
|----------|--------|-------------|
| `create_strut_channel_bracket` | 📋 Pending | |
| `create_ratchet_wheel` | 📋 Pending | |
| `create_wire_clamp` | 📋 Pending | |

## Reference Implementation

Study `workflows/brackets.py` for the complete pattern:

```python
# 1. Import section
from __future__ import annotations
from typing import TYPE_CHECKING
from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import CreateBracketInput, VerificationSnapshot

# 2. Mixin class definition
class BracketWorkflowsMixin:
    """Mixin providing bracket-related CAD workflows."""

    # 3. Public API method
    def create_bracket(self, payload: dict) -> dict:
        """Create an L-bracket: sketch an L-profile, extrude, verify, export STL."""
        spec = CreateBracketInput.from_payload(payload)
        return self._create_l_bracket_workflow(...)

    # 4. Private implementation method
    def _create_l_bracket_workflow(self, ...) -> dict:
        """Core L-bracket workflow implementation."""
        stages: list[dict] = []
        workflow_definition = self.workflow_registry.get(workflow_name)

        # Stage sequence with verification
        self._bridge_step(stage="new_design", ...)
        # ... more stages ...

    # 5. Abstract method declarations (for type checking)
    def _bridge_step(self, *, stage, stages, action, ...):
        raise NotImplementedError
    def draw_rectangle(self, ...):
        raise NotImplementedError
    # ... etc
```

## Step-by-Step Migration

### Step 1: Locate Original Implementation

The original workflow implementations are still in the git history. To see them:

```bash
git show HEAD~1:mcp_server/server.py | grep -A 200 "def create_spacer"
```

### Step 2: Create Public API Method

In the appropriate mixin file, add:

```python
def create_spacer(self, payload: dict) -> dict:
    """Create a flat rectangular spacer: sketch, extrude, verify, export."""
    spec = CreateSpacerInput.from_payload(payload)
    return self._create_rectangular_prism_workflow(
        workflow_name="spacer",
        workflow_call_name="create_spacer",
        design_name="Spacer Workflow",
        sketch_plane="xy",
        sketch_name=spec.sketch_name,
        body_name=spec.body_name,
        width_cm=spec.width_cm,
        height_cm=spec.height_cm,
        thickness_cm=spec.thickness_cm,
        output_path=spec.output_path,
    )
```

### Step 3: Migrate Private Implementation

Copy the `_create_*_workflow` method from the original server.py. Update:
- Method signature to include `self`
- Any calls to use `self._bridge_step`, `self.create_sketch`, etc.
- Import references if needed

### Step 4: Update Abstract Methods

Add abstract method declarations at the bottom of the mixin for any primitives the workflow uses:

```python
def draw_circle(self, center_x_cm, center_y_cm, radius_cm, sketch_token=None):
    """Provided by PrimitiveMixin."""
    raise NotImplementedError
```

### Step 5: Test

Run the specific test for your workflow:

```bash
pytest tests/test_workflow.py::test_create_spacer_workflow_exports_stl -v
```

Run all tests for the mixin family:

```bash
pytest tests/test_workflow.py -k "spacer or plate" -v
```

## Common Patterns

### Simple Prism Workflow

Many workflows follow the "sketch rectangle → list profiles → extrude → verify → export" pattern:

```python
def _create_simple_prism_workflow(self, ...):
    stages = []
    workflow_definition = self.workflow_registry.get(workflow_name)

    self._bridge_step(stage="new_design", stages=stages, action=lambda: self.new_design(design_name))
    self._verify_clean_state(stages)

    sketch = self._bridge_step(stage="create_sketch", ...)
    sketch_token = sketch["result"]["sketch"]["token"]

    self._bridge_step(stage="draw_rectangle", ...)

    profiles = self._bridge_step(stage="list_profiles", ...)
    if len(profiles) != 1:
        raise WorkflowFailure(...)

    body = self._bridge_step(stage="extrude_profile", ...)

    self._verify_single_body(body, expected_dimensions, stages, workflow_name)

    exported = self._bridge_step(stage="export_stl", ...)

    return {"ok": True, "workflow": ..., "body": body, ...}
```

### Multi-Stage Workflow (with cuts)

For workflows that create a base body then cut features:

```python
def _create_plate_with_hole_workflow(self, spec):
    # Phase 1: Create base plate
    # ... create sketch, draw rectangle, extrude ...

    body = ...  # from extrude
    body_token = body["token"]

    # Phase 2: Cut the hole
    sketch2 = self._bridge_step(
        stage="create_sketch",
        action=lambda: self.create_sketch(
            plane="xy",  # or face-relative
            name="Hole Sketch",
            offset_cm=spec.thickness_cm,  # on top face
        )
    )
    # ... draw circle ...
    # ... extrude with operation="cut", target_body_token=body_token ...

    # Verify final geometry
```

### Multi-Body Workflow (box + lid)

For workflows that create multiple bodies:

```python
def _create_box_with_lid_workflow(self, spec):
    # Create box body
    # ...
    box_body = ...

    # Create lid body (new_body operation, not cut)
    # ...
    lid_body = ...

    # Export both
    box_export = self.export_stl(box_body["token"], box_output_path)
    lid_export = self.export_stl(lid_body["token"], lid_output_path)

    return {
        "ok": True,
        "bodies": [box_body, lid_body],
        "exports": [box_export, lid_export],
    }
```

## Helper Methods

The `WorkflowMixin` provides these helpers:

- `_verify_clean_state(stages)` - Verify design starts empty
- `_verify_single_body(body, expected, stages, name)` - Verify one body with dimensions
- `_bridge_step(stage, stages, action, partial_result, next_step)` - Execute with error handling

## Testing Tips

1. **Test incrementally**: Migrate one workflow, test it, commit, then move to the next
2. **Use specific tests**: `pytest tests/test_workflow.py::TEST_NAME -v`
3. **Watch for import errors**: Make sure all imports are updated
4. **Check abstract methods**: Ensure mixins declare primitives they use

## Getting Help

If a workflow is complex or unclear:
1. Check `workflows/brackets.py` for the reference pattern
2. Look at the original implementation in git history
3. Run the test with `-v --tb=long` to see the full error trace
4. Check ARCHITECTURE.md for the mixin architecture overview
