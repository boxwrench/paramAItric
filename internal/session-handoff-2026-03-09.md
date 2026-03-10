# Session Handoff: 2026-03-09 (Freeform State Machine Design)

## Repo

- Path: `./`
- Branch: `master`
- Remote: `origin https://github.com/boxwrench/paramAItric.git`
- Latest pushed commit: `4da0fa5` (McMaster validation script + YZ coordinate mapping)

## Current validated state

- 37 MCP tools: 2 status + 5 inspection + 30 workflow
- 25 workflow definitions in registry
- 435 tests passing (mock suite, no live Fusion required)
- MCP stdio packaging in place (`mcp_entrypoint.py`, `tool_specs.py`, `pyproject.toml`)

## What landed this session

1. **Triangular bracket and L-bracket with gusset workflows** — `draw_triangle` primitive, `combine_bodies` integration. Unit-tested, pending live validation.
2. **`convert_bodies_to_components` tool** — bodies to Fusion components, prerequisite for joints.
3. **`list_design_bodies` inspection tool** — body count + volume/face/edge per body. Enables the 3-layer post-cut verification pattern.
4. **McMaster Strut Channel Bracket experiment** (`scripts/validate_mcmaster_bracket.py`) — proved XZ/YZ coordinate mappings, exposed geometry translation failures (see diagnosis below).

## Multi-agent review consensus

Three independent AI reviewers (Claude, Gemini, Kimi) converged on priority and direction:

- **Gemini**: Identified AI overconfidence problem — agents chain 10 primitives blindly, silent failures compound. Proposed AWAITING_MUTATION / AWAITING_VERIFICATION state machine with `commit_verification` gating.
- **Claude**: Agreed on state machine, pushed back on freeform-only pivot. Proposed machine-checkable assertions (Option C) instead of freeform notes. Advocated parallel paths: keep existing workflows, add freeform as opt-in mode.
- **Kimi**: Rated architecture 5/5, identified server.py file size and workflow duplication as tech debt. Recommended "operation multipliers over more variants" — exactly the freeform argument.

---

## Priority 1: Diagnose the Strut Channel Bracket (current primitives)

### Why do this first
The bracket is the motivating problem for freeform mode. Before building new architecture, we need to know exactly what primitives are missing. Fix the script, discover the gaps, then build freeform to fill them.

### What went wrong (Gemini's diagnosis, confirmed)

The experimental script (`scripts/validate_mcmaster_bracket.py`) made **four geometry translation errors** when trying to recreate McMaster part 33125T421:

1. **Extrusion orientation is backwards.** The real bracket is 3.5" wide sheet metal bent into an L. The script sketched the L-profile (3.5" horizontal, 4.125" vertical) and extruded to only 1.625" depth — making the vertical leg 1.625" wide instead of 3.5". The correct approach: sketch a **cross-section** of the sheet metal bend (a thin L with 0.25" thickness), then extrude 3.5" to get the full width.

2. **Missing taper (trapezoid).** The real part's vertical leg tapers inward from top to bottom (trapezoid front face). The script produces a perfect rectangle. Would need triangular cuts on the front face or a `draw_polygon` / `draw_trapezoid` primitive.

3. **Vertical leg hole placement.** Because the width/depth were swapped, holes landed on the skinny 1.625" face instead of centered on the 3.5" face. This is a consequence of error #1.

4. **Sharp corner vs bend radius.** Real part is bent sheet metal with a smooth outer fillet. Script has a sharp 90-degree corner. Fixable with `apply_fillet` — we already have this.

### The YZ plane blocker (still unresolved)

Even with correct orientation, the vertical leg holes require YZ-plane cuts. Three attempts all produced "did not intersect" errors. The YZ plane extrude direction is **unconfirmed**. See `memory/strut_channel_bracket.md` for the full investigation log.

### Recommended fix sequence
1. Fix the L-profile orientation: sketch the thin cross-section, extrude to full 3.5" width
2. Resolve YZ plane extrude direction with probe tests (large distance, symmetric, through-all)
3. Add taper via triangular cuts on the front face (we have `draw_triangle`)
4. Add outer fillet with `apply_fillet`
5. Verify all 4 holes, volume, and bounding box

### What this teaches us about freeform
The script failure is exactly the kind of mistake an AI agent would make in freeform mode — and exactly what the verification loop would catch. After the first extrude, `commit_verification(expected_body_count=1, expected_volume_range=[...])` would force a bbox check. The AI would see the vertical leg is 1.625" wide instead of 3.5" and know to redo the sketch orientation. **This is the strongest argument for building the state machine.**

---

## Priority 2: Guided Freeform State Machine

### The problem it solves

AI agents are overconfident. Given a list of 10 primitive CAD operations, they execute all 10 in a burst. If step 2 fails silently, steps 3-10 operate on a broken model. By the end, the part is ruined and the agent is lost.

The current system has two modes: (a) pre-validated `create_*` workflows that are rigid but correct, and (b) raw primitive access with no guardrails. There's no middle ground for **novel parts** where the AI needs to figure out the steps but still needs supervision.

### Architecture: `FreeformSession` in `mcp_server/freeform.py`

New module — keeps server.py from growing further (addresses Kimi's file-size concern).

#### The two states

```
AWAITING_MUTATION ──[mutation tool]──> AWAITING_VERIFICATION
                                              │
                                  [commit_verification]
                                              │
AWAITING_MUTATION <────────────────────────────┘
```

- **AWAITING_MUTATION**: The AI may call exactly one tool that alters CAD geometry.
- **AWAITING_VERIFICATION**: The model is locked. Only inspection tools are allowed. The AI must verify before proceeding.

#### Tool classification

Already 90% done in `tool_specs.py`. Add a third category:

```python
MUTATION_TOOLS = {
    "create_sketch", "draw_rectangle", "draw_circle", "draw_triangle",
    "draw_slot", "draw_l_bracket_profile", "draw_revolve_profile",
    "extrude_profile", "apply_fillet", "apply_chamfer", "apply_shell",
    "cut_body_with_profile", "combine_bodies", "new_design",
}

INSPECTION_TOOLS = {
    "list_design_bodies", "get_body_info", "get_body_faces",
    "get_body_edges", "list_profiles", "get_scene_info", "health",
}
```

#### Commit verification with machine-checkable assertions (Option C)

Three options were considered for unlocking the state:
- **Option A** (implicit): any inspection call unlocks. Risk: AI calls inspection and ignores result.
- **Option B** (explicit notes): `commit_verification(notes="looks good")`. Risk: server can't validate prose.
- **Option C** (assertions + notes): chosen approach.

```python
commit_verification(
    expected_body_count: int,             # server checks vs list_design_bodies
    expected_volume_range: [min, max],    # server checks vs get_body_info (optional)
    notes: str                            # forces AI to articulate reasoning
) -> { "ok": True, "actual_body_count": N, "actual_volume_cm3": V }
```

The server calls the inspection tools **itself**, compares against the AI's stated expectations, and **refuses to unlock if they don't match**. This catches:
- Split bodies (body_count mismatch)
- Missing material (volume too low)
- Excess material (volume too high)
- The AI sleepwalking past problems ("looks good")

If assertions fail, the response includes the actual values and the state remains AWAITING_VERIFICATION. The AI must reassess and either call `commit_verification` with corrected expectations (acknowledging the unexpected state) or use inspection tools to understand what went wrong.

#### Session lifecycle

```python
start_freeform_session(design_name: str) -> { session_id, state: "AWAITING_MUTATION" }
# ... mutation/verification loop ...
end_freeform_session() -> { mutation_count, verification_log }
```

- Existing `create_*` workflows remain **ungated** — they are pre-validated recipes.
- Freeform mode is opt-in. When no session is active, primitives work as they do today (no breaking change).
- The session tracks a full mutation history: `[{tool, args, result, verification}]`.

#### Gating logic (in `mcp_entrypoint.py` or server dispatch)

```python
# pseudocode for the gate
if freeform_session is active:
    if tool_name in MUTATION_TOOLS:
        if session.state != AWAITING_MUTATION:
            raise "LOCKED: verify geometry before next mutation"
        result = execute(tool_name, payload)
        session.state = AWAITING_VERIFICATION
        session.pending_mutation = {tool_name, payload, result}
        return result
    elif tool_name == "commit_verification":
        assertions = validate_assertions(payload)
        if assertions.passed:
            session.state = AWAITING_MUTATION
            session.log.append(pending_mutation + assertions)
        return assertions
    elif tool_name in INSPECTION_TOOLS:
        return execute(tool_name, payload)  # always allowed
    elif tool_name in WORKFLOW_TOOLS:
        raise "Cannot use pre-built workflows inside a freeform session"
```

#### FreeformSession dataclass

```python
@dataclass
class FreeformSession:
    session_id: str
    design_name: str
    state: Literal["AWAITING_MUTATION", "AWAITING_VERIFICATION"]
    mutation_log: list[MutationRecord]    # tool, args, result, verification
    created_at: datetime
    active_body_tokens: list[str]         # tracked across mutations
```

Estimated size: ~200 lines in `mcp_server/freeform.py`, ~30 lines gate logic in entrypoint.

---

## Priority 2b: Freeform-to-Workflow Reverse Engineering

### The idea
When freeform mode successfully builds a novel part, the mutation log is a complete, verified record of every step. This log can be **reverse-engineered into a traditional `create_*` workflow**.

### How it works

1. AI uses freeform mode to design a tricky part (like the strut bracket)
2. Each step is verified — the log contains: tool calls, parameters, and passing assertions
3. After success, the log is essentially a **workflow recipe** with known-good dimensions
4. A developer (or AI) extracts the log into a parameterized `_create_xxx_workflow()` function
5. The new workflow gets unit tests, schema validation, and joins the `create_*` family

### Why this matters

- **Discovery tool**: freeform mode becomes how we find recipes for complex parts
- **Reduces risk**: the workflow is extracted from a proven sequence, not designed from scratch
- **Self-documenting**: the verification assertions become the workflow's geometry checks
- **Grows the catalog**: every successful freeform session is a candidate for a new workflow

### Implementation (later, not in first cut)

Add an `export_session_log()` tool that returns the mutation log in a structured format suitable for workflow extraction. This is a read-only operation on the session history — no new architecture needed.

```python
export_session_log(session_id: str) -> {
    "design_name": "Strut Channel Bracket",
    "steps": [
        {
            "step": 1,
            "tool": "create_sketch",
            "args": {"plane": "xy", "name": "Cross-section"},
            "verification": {"body_count": 0, "notes": "sketch only, no body yet"}
        },
        {
            "step": 2,
            "tool": "extrude_profile",
            "args": {"distance_cm": 8.89, ...},
            "verification": {"body_count": 1, "volume_range": [23.0, 24.0], "notes": "L solid, no holes yet"}
        },
        ...
    ]
}
```

---

## Tech debt notes (from Kimi review)

| Item | Severity | Action |
|------|----------|--------|
| server.py at ~6400 lines | Low | Freeform goes in `freeform.py`, not server.py. Workflow family split deferred. |
| Workflow stage duplication | Low | Freeform mode reduces need for more `create_*` variants. Pattern library deferred. |
| Mock vs live test parity | Medium | Standardize mock level. Not blocking. |
| YZ plane edge cases | Medium | Must resolve for strut bracket. Blocking Priority 1. |
| Cancel in-progress ops | Low | Cooperative only. Not blocking. |

---

## Next recommended execution order

1. Merge `freeform-state-machine` into `master`.
2. Extract the "AI CAD Playbook" from research docs into a bespoke constitutional document for AI hosts.
3. Implement `apply_as_built_joint` to enable multi-body assembly verification.
4. Pilot the "Workflow Compiler" by exporting a successful freeform session log as a reusable macro.

## Accomplishments (isolated branch `freeform-state-machine`)

1. **Guided Freeform State Machine (`mcp_server/freeform.py`):**
   - Implemented `AWAITING_MUTATION` -> `AWAITING_VERIFICATION` forced loop.
   - AI must use inspection tools and call `commit_verification` with machine-checkable assertions (e.g., `expected_body_count`) to unlock the next mutation.
   - Integrated logic into `server.py` and `mcp_entrypoint.py`.

2. **Semantic Face Selection (`find_face`):**
   - Added `find_face` tool supporting axis-aligned selectors: `top`, `bottom`, `left`, `right`, `front`, `back`.
   - Uses body centroid and face bounding box logic to provide stable face tokens even after mutations.

3. **Coordinate Mapping Codification (`geometry_utils.py`):**
   - Added `sketch_to_world` to implement the "Z-axis negation rule" for XZ and YZ planes.
   - Turns empirical "tribal knowledge" about Fusion's plane inversions into reusable code.

4. **Enriched Inspection:**
   - `list_design_bodies` now returns full `bounding_box` and `centroid` data per body.
   - Enables the "Measure/Predict/Verify" feedback loop for AI hosts.

5. **CSG Robustness:**
   - Merged Kimi's two-sided extent fix.
   - Defined `BOOLEAN_EPSILON_CM = 0.001` for future padding of coplanar surfaces.

## Deferred (unchanged)

- Rollback points / undo within freeform
- Angled sketch planes
- Threading
- Linear or circular patterns
- Assembly joints/constraints
