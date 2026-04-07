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

## Current State (as of 2026-03-29)

**Completed:** All 9 cylinder workflows migrated (revolve, tapered_knob_blank, flanged_bushing, shaft_coupler, pipe_clamp_half, t_handle_with_square_socket, tube_mounting_plate).

### Test status

```
443 passing / 30 failing / 473 total
```

30 failures are `NotImplementedError` — stubs in unmigrated workflow families (enclosures, specialty). No logic regressions.

### Migration status

| Family | Workflows | Status |
|--------|-----------|--------|
| Plates | 9 | ✅ Fully migrated + tested |
| Cylinders | 9 | ✅ Fully migrated + tested (17/19 tests passing) |
| Brackets | 7 | ✅ Fully migrated + tested (10/10 tests passing) |
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

See `docs/NEXT_PHASE_PLAN.md` for the full phased roadmap with implementation details.
Summary below.

### Priority 1 — Clear the stub backlog ✅ Cylinders + Brackets Complete

1. ✅ **Cylinders** — All 9 workflows migrated (2026-03-15). 17/19 tests passing.
2. ✅ **Brackets** — All 7 workflows migrated (2026-03-15). 10/10 tests passing.
3. **Enclosures** — 8 workflows, more complex (shell, multi-body). `flush_lid_enclosure_pair` smoke passes; use as anchor.
4. **Specialty** — strut channel bracket, ratchet wheel, wire clamp. Last.

**Goal:** Reach 473/473 tests passing before adding new features.

### Priority 2 — Intake & Discovery (NEXT_PHASE_PLAN Phase 1)

The gap between "I need a part" and "run this workflow" is the biggest usability problem.
- Enrich `workflow_catalog` to return metadata, not just names
- Add `recommend_workflow` tool (intent + constraints → ranked suggestions)
- Build reference catalog with typical real-world dimensions
- Extend schema dataclasses with display metadata (powers HTML form generation)

### Priority 3 — HTML Interface (NEXT_PHASE_PLAN Phase 2)

Serve a local web UI from the existing bridge at `127.0.0.1:8123/ui`. Auto-generate
forms from schema metadata. Workflow browser, SVG preview, reference panel, status log.

### Priority 4 — Threading (NEXT_PHASE_PLAN Phase 3)

Use Fusion's `ThreadFeatures` API with `ThreadInfo.create` (static method — `createThreadInfo`
is retired). Interior + exterior at different pitch confirmed feasible. Watch the
document-level "Modeled" setting for STL export.

### Priority 5 — New Fusion-native primitives (NEXT_PHASE_PLAN Phase 4)

Linear pattern, circular pattern, mirror, loft, sweep with guide rails — all confirmed
mature in Fusion API (Nov 2025). Wrap and expose. Linear/circular pattern directly
enables N-hole plate parameterization.

### Priority 6 — Utility part templates

Real-world parts that exercise the new capabilities once they land:
- Valve handle / stem socket replacement
- Instrument mounting bracket
- Pipe clamp for non-standard OD
- Threaded cap with dual-pitch threads

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
