# ParamAItric — AI Session Context

**Purpose of this document:** Give any AI assistant enough context to resume productive work on this repo in a single read. Keep it current. When the repo state changes materially, update this file.

---

## What This Project Is

ParamAItric is an MCP (Model Context Protocol) server that lets an AI host drive parametric CAD in Autodesk Fusion 360. The AI calls tools like `create_bracket`, `create_spacer`, or `create_cylinder` with structured parameters. The MCP server validates the input, executes a multi-step workflow via a loopback HTTP bridge to a Fusion 360 add-in, and returns the result including an STL export path.

**The real-world focus is utility and maintenance parts** — the kinds of simple, measurable, functional parts that water treatment plants, industrial facilities, and utility infrastructure depend on. These parts are geometrically simple but expensive through normal procurement because of niche supply and hardware monopolies. 3D printing them from parameterized CAD designs dramatically reduces cost and lead time, and enables material upgrades (e.g., chemical-resistant filaments over cast metal).

The project is open source. For a human-facing overview, start with `README.md`.

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
| `mcp_server/workflows/plates.py` | Plate workflow family plus legacy migration surface and helpers |
| `mcp_server/workflows/cylinders.py` | Cylinder and revolve workflow family with mixed mature logic and legacy placeholder surface |
| `mcp_server/workflows/brackets.py` | Bracket workflow family with mixed mature logic and legacy placeholder surface |
| `mcp_server/workflows/enclosures.py` | Enclosure workflows — partial / placeholder-heavy |
| `mcp_server/workflows/specialty.py` | Specialty workflows — placeholder-heavy |
| `mcp_server/freeform.py` | FreeformSession state machine |
| `mcp_server/sessions/` | Session lifecycle management |
| `mcp_server/schemas.py` | Pydantic input schemas for all workflows |
| `mcp_server/tool_specs.py` | MCP tool surface definitions |
| `fusion_addin/` | Fusion 360 add-in (bridge listener) |
| `tests/` | Workflow, bridge, validation, and smoke coverage |

---

## Current State (as of 2026-04-08)

ParamAItric is past the "does the architecture make sense?" stage.

The main architecture is established:

- AI host -> MCP -> ParamAItric server -> bridge -> Fusion add-in
- structured workflow lane
- guided freeform lane
- staged verification with hard gates, audits, and diagnostics

The main issue is now internal reliability, not architectural direction.

More specifically:

- workflow families still contain uneven legacy migration state
- geometry targeting remains more brittle than the product needs
- selection decisions are not yet explained in a structured way
- topology mutations still put pressure on reference stability
- workflow structure is strong enough to improve, but still too ad hoc in places

### Current planning stance

The next major phase is no longer "add more surface area first."

The current roadmap now prioritizes:

1. semantic selectors
2. selection traces and geometry diagnostics
3. stable reference strategy across topology mutations
4. narrow internal operation vocabulary
5. reusable part-recipe structure

Intake/discovery, local UI, threading, and primitive expansion are still planned, but they now sit behind this internal geometry-foundation work.

### Workflow status

The repo has a meaningful workflow surface today, but workflow-family maturity is uneven.

- plates, cylinders, and brackets contain substantial implemented logic
- enclosures and specialty remain more partial
- several workflow-family files still include placeholder and legacy migration surface

This means the next milestone should not be judged only by "how many workflows exist."
It should be judged by whether the workflows are easier to target, debug, and extend safely.

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

Freeform remains active, but it should not become broader until selector diagnostics and reference stability improve.

---

## What NOT to Revisit

These decisions are settled. Do not reopen without strong reason:

- **Mixin architecture**: correct for this codebase, working in production
- **AST extraction for migration**: proven safe, zero diffs on all plate workflows
- **Freeform as opt-in mode**: pre-built `create_*` workflows remain ungated; freeform is additive
- **Core server stays generic**: utility-part context lives in prompts and docs, not server logic
- **No material intelligence in the server**: material guidance is a prompt/reference layer
- **No new runtime geometry dependency right now**: external Python CAD work is design inspiration, not an adoption decision

---

## Forward Progress Priorities

See `docs/NEXT_PHASE_PLAN.md` for the full phased roadmap with implementation details.
Summary below.

### Priority 1 — Internal Geometry Foundations

This is now the top implementation priority.

- define a first semantic selector layer for faces and edges
- add structured selection traces and high-signal geometry diagnostics
- harden stable reference strategy across topology mutations
- introduce a narrower internal operation vocabulary and shared boolean intent

This work supports both structured workflows and freeform without changing the runtime architecture.

### Priority 2 — Workflow Architecture Hardening

- introduce reusable part-recipe structure
- codify dimensional workflow discipline
- add deterministic placement helpers
- use parameter relationships where design intent is relational

This is the path to cleaner workflow families, not just more workflow families.

### Priority 3 — Intake & Discovery

Still important, but no longer the lead phase:

- enrich `workflow_catalog`
- add `recommend_workflow`
- build a reference catalog
- add schema display metadata for both AI and future UI use

### Priority 4 — Local UI

Still planned:

- local `/ui` interface served from the bridge
- workflow browser
- auto-generated parameter forms
- simple preview and status surface

This should follow stronger workflow metadata and better internal diagnostics.

### Priority 5 — Capability Expansion

Threads, patterns, mirror, loft, sweep, and richer utility-part recipes remain valuable, but they should be layered on top of the stronger geometry core rather than used to define the next phase.

---

## Active Risks and Blockers

| Risk | Severity | Status |
|------|----------|--------|
| Geometry targeting remains too brittle | High | Main reason the roadmap shifted toward selector/reference work |
| Selection decisions are hard to explain | High | Limits debugging, recovery, and workflow hardening |
| Topology mutations can invalidate assumptions | High | Needs stronger reference strategy before more capability expansion |
| Workflow maturity is uneven across families | Medium | Important, but should be improved through stronger structure rather than count-chasing |
| Freeform session stability still matters | Medium | Keep constrained until diagnostics and references improve |

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

1. **Modifying tests** — The existing test suite is the contract. If a test fails, fix the implementation, not the test.
2. **Regex-based extraction** — Never use regex to extract Python code. Always use `scripts/extract_workflow_fixed.py` which uses AST parsing.
3. **Relative imports** — All workflow mixins use absolute imports from `mcp_server.*`. Don't change to relative.
4. **Schema drift** — If adding a workflow, schema → mixin → tool_spec → test → registry. Skipping steps causes registration failures.
5. **Freeform vs pre-built** — Pre-built `create_*` workflows remain ungated. Freeform is an additive opt-in mode, not a replacement.
6. **Roadmap drift** — Do not jump straight to new UI or new primitives without checking whether the underlying selector/reference assumptions are strong enough first.

## Process Notes for AI Sessions

- **Read `docs/dev-log.md`** for session-by-session history of decisions and blockers
- **Read `docs/session-handoff-*.md`** for the most recent work state
- **Read `docs/VERIFICATION_POLICY.md`** before making any changes to the verification layer
- **Read `docs/NEXT_RESEARCH_PLAN.md`** before planning foundational geometry work
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
| Plates workflow family | `C:/Github/paramAItric/mcp_server/workflows/plates.py` |
| Cylinders workflow family | `C:/Github/paramAItric/mcp_server/workflows/cylinders.py` |
| Workflow base mixin | `C:/Github/paramAItric/mcp_server/workflows/base.py` |
| Test suite | `C:/Github/paramAItric/tests/test_workflow.py` |
| Migration scripts | `C:/Github/paramAItric/scripts/` |

---

## What "Done" Looks Like

A session is successful if it leaves the repo in a better state on at least one of these axes:
1. Geometry targeting is more deterministic or more explainable
2. Reference stability improves after a topology-changing operation
3. Workflow structure becomes more reusable or easier to reason about
4. Verification results become more provenance-aware and useful for recovery
5. A real workflow or freeform path gets stronger because of the above

The treadmill trap is no longer just "migrating stubs forever." It is also "adding more surface area before the geometry foundation is ready."
