# Priority 3: Utility Part Templates - Implementation Plan

## Objective
Build real-world replacement part workflows grounded in specific maintenance use cases. Start with valve handle replacement as the priority first target.

## Why Valve Handle First?

1. **Fits existing vocabulary**: Uses sketch, profile, extrude, cut, fillet
2. **Real failure mode**: Handle breaks, vendor only sells full valve assembly
3. **Fit-critical**: Socket must match stem dimensions exactly
4. **Common utility part**: Used across water treatment, industrial facilities

---

## Part Anatomy: Valve Handle

```
        Lever Arm (for turning)
              │
    ┌─────────┴─────────┐
    │                   │
    │    ┌───────┐      │
    │    │       │      │
    │    │ SOCKET│      │  ← Fits over valve stem
    │    │       │      │
    │    └───┬───┘      │
    │        │          │
    └────────┴──────────┘
         Set screw
          hole
```

### Socket Types
1. **Square** (most common for quarter-turn valves)
2. **Hex** (common for gas valves)
3. **Round with flat** (some industrial valves)
4. **Double-D** (specialty)

### Critical Dimensions
| Parameter | Description | Tolerance |
|-----------|-------------|-----------|
| `stem_width_cm` | Across flats (square/hex) or diameter | ±0.1mm |
| `stem_depth_cm` | How deep socket engages stem | ±0.5mm |
| `socket_type` | square, hex, round_flat | exact |
| `lever_length_cm` | Handle reach from center | ±1mm |
| `lever_thickness_cm` | Grip thickness | ±0.5mm |
| `lever_width_cm` | Width of lever arm | ±1mm |
| `fillet_radius_cm` | Stress relief at junction | ±0.5mm |
| `set_screw_diameter_cm` | Optional set screw | ±0.1mm |
| `clearance_cm` | Fit tolerance | ±0.05mm |

---

## Workflow Steps

### Phase 1: Socket Body
1. **Create sketch** on XY plane (socket profile)
2. **Draw socket shape** based on type:
   - Square: `draw_rectangle` + rotation OR `draw_polygon`
   - Hex: `draw_polygon` with 6 sides
   - Round with flat: `draw_circle` + `draw_rectangle` (cut)
3. **Extrude socket** to `stem_depth_cm`

### Phase 2: Lever Arm
**Option A: Additive (preferred)**
1. Create new sketch on YZ plane (side profile)
2. Draw lever profile (rectangle extending from socket)
3. Extrude symmetric to create lever
4. `combine_bodies` to merge

**Option B: Subtractive (if additive fails)**
1. Start with solid block
2. Cut socket cavity
3. Cut lever shape from block

### Phase 3: Set Screw Hole
1. Create sketch on appropriate plane
2. Draw circle for set screw
3. Extrude cut through socket wall

### Phase 4: Finishing
1. **Apply fillets** at socket-lever junction (stress relief)
2. **Verify geometry** (body count, dimensions)
3. **Export STL**

---

## New Primitives Required?

### Analysis: Can we build this with existing primitives?

**Current primitives:**
- `draw_rectangle` ✓
- `draw_circle` ✓
- `draw_triangle` ✓
- `extrude_profile` ✓
- `apply_fillet` ✓
- `combine_bodies` ✓

**Missing for socket shapes:**
- `draw_polygon` (for hex sockets, square with rotation)
- OR `draw_rectangle_at` with rotation capability

**Decision:** Need to add `draw_polygon` primitive for hexagonal sockets.

---

## Implementation Steps

### Step 1: Add `draw_polygon` Primitive (30 min)
**Files:**
- `mcp_server/primitives/core.py` - add method
- `fusion_addin/ops/mock_ops.py` - add mock implementation
- `fusion_addin/ops/live_ops.py` - add Fusion implementation

**Signature:**
```python
def draw_polygon(
    self,
    center_x_cm: float,
    center_y_cm: float,
    radius_cm: float,
    num_sides: int,
    sketch_token: str | None = None,
) -> dict:
    """Draw a regular polygon (for hex sockets, etc.)."""
```

### Step 2: Create Schema (20 min)
**File:** `mcp_server/schemas.py`

```python
@dataclass(frozen=True)
class CreateValveHandleInput:
    stem_width_cm: float  # Across flats
    stem_depth_cm: float
    socket_type: str  # "square", "hex", "round_flat"
    lever_length_cm: float
    lever_thickness_cm: float
    lever_width_cm: float
    fillet_radius_cm: float
    set_screw_diameter_cm: float | None = None
    clearance_cm: float = 0.05
    output_path: str
```

### Step 3: Implement Workflow (60 min)
**File:** `mcp_server/workflows/utility_parts.py` (new file)

```python
class UtilityPartsMixin:
    def create_valve_handle(self, payload: dict) -> dict:
        spec = CreateValveHandleInput.from_payload(payload)
        return self._create_valve_handle_workflow(spec)

    def _create_valve_handle_workflow(self, spec: CreateValveHandleInput) -> dict:
        # Implementation following steps above
```

### Step 4: Register Workflow (10 min)
**File:** `mcp_server/workflow_registry.py`

Add entry for "valve_handle" with stages list.

### Step 5: Tests (30 min)
**File:** `tests/test_valve_handle.py`

- Test valid input
- Test fit tolerance (clearance)
- Test stress relief (fillet presence)
- Test socket geometry matches type

### Step 6: Documentation (20 min)
**File:** Update relevant docs

- Add to `docs/utility-parts-concept.md`
- Create usage example for AI hosts

---

## Total Estimated Time

| Step | Time |
|------|------|
| draw_polygon primitive | 30 min |
| Schema | 20 min |
| Workflow implementation | 60 min |
| Registration | 10 min |
| Tests | 30 min |
| Documentation | 20 min |
| **Total** | **~3 hours** |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fusion API polygon drawing | Medium | Use circle + lines fallback if needed |
| Combine_bodies failures | Low | Already tested in standoffs workflow |
| Complex socket shapes | Medium | Start with square/hex only |

---

## Success Criteria

1. Workflow creates valve handle with correct socket geometry
2. Socket fits test stem with specified clearance
3. Lever has proper fillets for stress relief
4. All tests pass
5. Documentation includes AI host guidance on measuring stems

---

## Future Expansion

After valve handle:
1. **Instrument mounting bracket** - pipe-to-instrument adapter
2. **Pipe clamp adapter** - for non-standard OD
3. **Panel mounting bracket** - with slots
4. **Sight glass guard** - protective cover

Each follows same pattern: identify parameters, map to primitives, build workflow, test with real constraints.
