# ParamAItric — AI Session Context

**Purpose of this document:** Give any AI assistant enough context to resume productive work on this repo in a single read. Keep it current. When the repo state changes materially, update this file.

---

## What This Project Is

ParamAItric is an MCP (Model Context Protocol) server that lets an AI host drive parametric CAD in Autodesk Fusion 360. The AI calls tools like `create_bracket`, `create_spacer`, or `create_cylinder` with structured parameters. The MCP server validates the input, executes a multi-step workflow via a loopback HTTP bridge to a Fusion 360 add-in, and returns the result including an STL export path.

**The real-world focus is utility and maintenance parts** — the kinds of simple, measurable, functional parts that water treatment plants, industrial facilities, and utility infrastructure depend on. These parts are geometrically simple but expensive through normal procurement because of niche supply and hardware monopolies. 3D printing them from parameterized CAD designs dramatically reduces cost and lead time, and enables material upgrades (e.g., chemical-resistant filaments over cast metal).

The project is open source. The canonical human context document is `docs/utility-parts-concept.md`.

---

## Architecture

### Stack

```
AI host (Claude, GPT, etc.)
  → MCP stdio interface (mcp_entrypoint.py)
  → ParamAIToolServer (mcp_server/server.py)
  → BridgeClient (mcp_server/bridge_client.py)
  → Loopback HTTP (localhost)
  → Fusion 360 add-in (fusion_addin/)
  → Fusion 360 API
```

### Server composition (mixin architecture)

`server.py` is 85 lines — just the class definition composing mixins:

```python
class ParamAIToolServer(
    FreeformSessionManager,    # mcp_server/sessions/
    PrimitiveMixin,            # mcp_server/primitives/
    WorkflowMixin,             # mcp_server/workflows/base.py
    BracketWorkflowsMixin,     # mcp_server/workflows/brackets.py
    PlateWorkflowsMixin,       # mcp_server/workflows/plates.py
    EnclosureWorkflowsMixin,   # mcp_server/workflows/enclosures.py
    CylinderWorkflowsMixin,    # mcp_server/workflows/cylinders.py
    SpecialtyWorkflowsMixin,   # mcp_server/workflows/specialty.py
):
```

Each mixin file is independent. Workflow implementations live in their family file. Shared infrastructure (bridge communication, error handling, common stage patterns) lives in `WorkflowMixin` (base.py).

### Key files

| File | Role |
|------|------|
| `mcp_server/server.py` | Class composition only — 85 lines |
| `mcp_server/mcp_entrypoint.py` | MCP stdio interface, tool routing, freeform gate |
| `mcp_server/workflows/base.py` | WorkflowMixin: `_send`, `_bridge_step`, `_create_rectangular_prism_workflow` |
| `mcp_server/workflows/plates.py` | 9 plate workflows — fully migrated, ~2100 lines |
| `mcp_server/workflows/cylinders.py` | 9 cylinder/revolve workflows — 2 migrated, 7 stubs |
| `mcp_server/workflows/brackets.py` | 7 bracket workflows — partially migrated |
| `mcp_server/workflows/enclosures.py` | 8 enclosure workflows — mostly stubs |
| `mcp_server/workflows/specialty.py` | 3 specialty workflows — stubs |
| `mcp_server/freeform.py` | FreeformSession state machine |
| `mcp_server/sessions/` | Session lifecycle management |
| `mcp_server/schemas.py` | Pydantic input schemas for all workflows |
| `mcp_server/tool_specs.py` | MCP tool surface definitions |
| `fusion_addin/` | Fusion 360 add-in (bridge listener) |
| `tests/` | 473 tests total |

---

## Current State (as of 2026-03-15)

### Test status

```
416 passing / 57 failing / 473 total
```

All 57 failures are `NotImplementedError` — stubs in unmigrated workflow families. No logic regressions. The migrated plate workflows are all correct: bit-for-bit identical to the original server.py verified by AST diff.

### Migration status

| Family | Workflows | Status |
|--------|-----------|--------|
| Plates | 9 | ✅ Fully migrated + tested |
| Cylinders | 9 | 2 migrated (cylinder, tube), 7 stubs |
| Brackets | 7 | Partially migrated — check brackets.py |
| Enclosures | 8 | `flush_lid_enclosure_pair` passes live smoke; others stubs |
| Specialty | 3 | All stubs (strut channel bracket, ratchet wheel, wire clamp) |

**Original server.py backup:** `C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py` (6,395 lines, pre-freeform state)

### Freeform session system

`mcp_server/freeform.py` implements a guided freeform mode with a two-state machine:

```
AWAITING_MUTATION → [mutation tool] → AWAITING_VERIFICATION
                                              ↓
                                   [commit_verification]
                                              ↓
AWAITING_MUTATION ←────────────────────────────
```

The AI must verify geometry (body count, volume range, notes) after every mutation before the next mutation is allowed. This catches silent failures that compound in multi-step sequences.

Freeform tests are currently failing — the session lifecycle has open issues. This is active work, not abandoned.

### Migration process (for remaining stubs)

AST-based extraction is proven and fast (~30 min per family):
1. `python scripts/migrate_workflows.py --family cylinders` — generates boilerplate with placeholders
2. `python scripts/extract_workflow_fixed.py --workflow create_cylinder_workflow` — extracts method from original
3. `python scripts/insert_into_plates.py` — inserts into boilerplate
4. `python scripts/verify_migration.py` — validates

Source for extraction: `C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py`

---

## What NOT to Revisit

These decisions are settled. Do not reopen without strong reason:

- **Mixin architecture**: correct for this codebase, working in production
- **AST extraction for migration**: proven safe, zero diffs on all plate workflows
- **Freeform as opt-in mode**: pre-built `create_*` workflows remain ungated; freeform is additive
- **Core server stays generic**: utility-part context lives in prompts and docs, not server logic
- **No material intelligence in the server**: material guidance is a prompt/reference layer

---

## Forward Progress Priorities

### Priority 1 — Clear the stub backlog (mechanical, ~2 hours)

Complete the remaining `NotImplementedError` stubs using the proven AST migration process. Ordered by dependency and complexity:

1. **Cylinders** — 7 remaining stubs (revolve, tapered knob, flanged bushing, shaft coupler, pipe clamp, tube mounting plate, t-handle). Clears 2 currently-failing plate tests (tube_mounting_plate depends on cylinder code).
2. **Brackets** — audit which are stubs, migrate remaining. Straightforward.
3. **Enclosures** — more complex (shell operations, multi-body). Migrate after cylinders and brackets are clean. `flush_lid_enclosure_pair` smoke tests pass; use that as the anchor for the family.
4. **Specialty** — strut channel bracket, ratchet wheel, wire clamp. Last.

**Goal:** Reach 473/473 tests passing before adding new features.

### Priority 2 — Stabilize freeform session tests

The freeform state machine is the most novel and valuable part of the product — it's what separates this from a basic CAD API wrapper. It should have solid test coverage. Fix the failing freeform tests before building on top of the system.

### Priority 3 — Utility part templates

Add real-world utility/maintenance part workflows grounded in specific parts. The valve handle / stem socket replacement is the priority first target (see `docs/utility-parts-concept.md`). These should:
- Be parameterized by fit-critical dimensions (stem width, socket depth, lever length)
- Include material guidance as a documentation layer, not schema parameters
- Have tests that reflect real failure modes (tight clearances, tolerance bounds)

Strong candidates from the utility-parts concept:
- Valve handle / stem socket replacement
- Instrument mounting bracket (pipe-to-instrument adapter)
- Pipe clamp for non-standard OD (expand the existing pipe_clamp_half)
- Panel mounting bracket with slot

### Priority 4 — Export session log (freeform → workflow path)

When freeform mode successfully builds a novel part, export the verified mutation log as a structured recipe. This is the path from "AI figured it out" to "repeatable parameterized workflow." See `docs/session-handoff-2026-03-09.md` for the original design.

### Priority 5 — Demo-ready surface

A clean, reproducible demo sequence that shows:
1. AI receives a part description in natural language
2. AI calls paramAItric tools to design the part
3. Part is exported as STL
4. Printed part fits real mating hardware

Target part for the demo: a valve handle replacement with a known stem size. This is both a development milestone and a presentation artifact.

---

## Active Risks and Blockers

| Risk | Severity | Status |
|------|----------|--------|
| 57 failing tests (stubs) | Medium | Clear with migration sprint |
| Freeform session test failures | Medium | Active, investigate before building on freeform |
| YZ plane extrude direction | Medium | Unresolved — see session-handoff-2026-03-09.md. Blocks accurate strut bracket and some complex enclosures |
| MCP entrypoint test failure | Low | `test_exported_mcp_tools_resolve_to_server_methods` failing — likely a stub registration issue |

---

## Quick Start for AI Sessions

```bash
# Run all tests (see current status)
pytest tests/ -x

# Run tests for a specific workflow family
pytest tests/test_workflow.py -k "plate" -v

# Verify migration integrity
python scripts/verify_migration.py

# Generate boilerplate for migration
python scripts/migrate_workflows.py --output-dir /c/tmp/regenerate

# Extract a workflow from original server.py
python scripts/extract_workflow_fixed.py --workflow create_cylinder > /c/tmp/wf_cylinder.py
```

## Common Pitfalls for AI Assistants

1. **Modifying tests** — The 473 tests are the contract. If a test fails, fix the implementation, not the test.
2. **Regex-based extraction** — Never use regex to extract Python code. Always use `scripts/extract_workflow_fixed.py` which uses AST parsing.
3. **Relative imports** — All workflow mixins use absolute imports from `mcp_server.*`. Don't change to relative.
4. **Schema drift** — If adding a workflow, schema → mixin → tool_spec → test → registry. Skipping steps causes registration failures.
5. **Freeform vs pre-built** — Pre-built `create_*` workflows remain ungated. Freeform is an additive opt-in mode, not a replacement.

## Process Notes for AI Sessions

- **Read `docs/dev-log.md`** for session-by-session history of decisions and blockers
- **Read `docs/session-handoff-*.md`** for the most recent work state
- **Read `docs/VERIFICATION_POLICY.md`** before making any changes to the verification layer
- **Check `docs/WORKFLOW_MIGRATION_GUIDE.md`** for current migration status of all 37 workflows
- When adding a new workflow: schema in `schemas.py` → mixin method in appropriate family file → tool spec in `tool_specs.py` → test in `tests/test_workflow.py` → register in `workflow_registry.py`
- When extracting from original: use `scripts/extract_workflow_fixed.py`, never regex or manual copy
- **Do not modify tests** — they are the contract. If a test fails, fix the implementation.
- The `private/` directory contains reference intake material and career strategy — not for public release

## File Path Reference

| Description | Absolute Path |
|-------------|---------------|
| Original server.py (AST extraction source) | `C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py` |
| Current server.py (mixin composition) | `C:/Github/paramAItric/mcp_server/server.py` |
| Plates mixin (fully migrated) | `C:/Github/paramAItric/mcp_server/workflows/plates.py` |
| Cylinders mixin (partial) | `C:/Github/paramAItric/mcp_server/workflows/cylinders.py` |
| Workflow base mixin | `C:/Github/paramAItric/mcp_server/workflows/base.py` |
| Test suite | `C:/Github/paramAItric/tests/test_workflow.py` |
| Migration scripts | `C:/Github/paramAItric/scripts/` |

---

## What "Done" Looks Like

A session is successful if it leaves the repo in a better state on at least one of these axes:
1. More tests passing (stub backlog reduced)
2. A new real-world utility part workflow with passing tests
3. Freeform session stability improved
4. Demo sequence documented or executable

The treadmill trap: migrating stubs is necessary but not sufficient progress. Every session should also advance either a real-world workflow or the freeform system.
