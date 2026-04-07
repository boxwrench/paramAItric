# Research Tracks

Status: active working tracker

## Why this exists

ParamAItric has already gone through multiple research passes that shaped the repo in different ways.

This document tracks the major research lanes, what each one was trying to answer, what repo artifacts came out of it, and what still needs follow-up.

This is not a raw research dump.

Use this doc to track synthesized direction and decision framing.

## Current research sequence

### 1. MCP integration research

Primary question:

- How should an AI host talk to a CAD system safely and in a host-agnostic way?

What it shaped:

- MCP-facing server architecture
- host/tool boundary
- loopback bridge pattern
- input validation and tool contract thinking

Main repo artifacts:

- `ARCHITECTURE.md`
- `HOST_INTEGRATION.md`
- `mcp_server/`
- `fusion_addin/http_bridge.py`
- `fusion_addin/dispatcher.py`

Current status:

- adopted into the main architecture

### 2. Parametric workflow research

Primary question:

- What narrow, repeatable workflow style can reliably produce useful mechanical parts?

Early framing:

- structured parametric workflows
- simple editable parts
- constrained, staged generation
- inspiration from approachable parametric systems such as Tinkercad-style task framing

What it shaped:

- workflow registry
- staged execution
- verification checkpoints
- narrow part families such as spacers, plates, brackets, cylinders, enclosures

Main repo artifacts:

- `DEVELOPMENT_PLAN.md`
- `BEST_PRACTICES.md`
- `docs/AI_CAD_PLAYBOOK.md`
- `docs/CSG_CHECKLIST.md`
- `mcp_server/workflow_registry.py`
- `mcp_server/workflows/`

Current status:

- core product direction, still expanding

### 3. Freeform research

Primary question:

- How much guided freeform modeling can be added without losing control, verification, or recoverability?

What it shaped:

- mutation / verification cycle thinking
- guided exploratory modeling
- promotion rules for freeform-derived patterns
- recovery-oriented operating discipline

Main repo artifacts:

- `docs/FREEFORM_PLAYBOOK.md`
- `docs/FREEFORM_CHECKLIST.md`
- `internal/freeform-architecture.md`
- `mcp_server/freeform.py`
- `mcp_server/sessions/freeform.py`

Current status:

- active but deliberately constrained

### 4. Python CAD inspiration research

Primary question:

- What can ParamAItric learn from mature Python CAD projects without giving up control of the application?

Current framing:

- use external Python CAD projects as design inspiration
- study abstractions, workflow patterns, selectors, reusable part structure, and testing approaches
- do not introduce a runtime dependency yet
- do not let another project dictate ParamAItric's product boundary at this stage

Initial conclusion:

- ParamAItric should remain a single controlled application
- external Python CAD projects are currently reference material, not the runtime architecture
- long-term backend or sidecar possibilities can be revisited later, after ParamAItric's own abstractions are more stable

Current status:

- new active research lane

## Python CAD inspiration: first-pass review scope

The first-pass review should cover a small set of mature Python CAD ecosystems and adjacent scripting/tooling references.

Primary goal:

- identify what can be borrowed as design inspiration for ParamAItric's own workflow and geometry architecture

Not the goal:

- replacing ParamAItric
- immediate backend integration
- introducing dependency-driven architecture too early

## What to extract from each project

For each reviewed project, capture:

- what it is
- modeling paradigm
- strongest abstractions
- geometry composition ideas worth borrowing
- selector / topology ideas worth borrowing
- reusable part-definition patterns
- testing or validation patterns
- what ParamAItric should not copy
- near-term value to ParamAItric
- adoption difficulty

## Expected output format for this research lane

Each reviewed project should produce a synthesized note with:

1. short project summary
2. strongest ideas worth borrowing
3. risks of copying blindly
4. likely influence on ParamAItric
5. recommendation:
   - borrow now
   - prototype later
   - monitor only

Then produce one comparison memo across the full set:

- comparison table
- ranked list of ideas to borrow now
- ranked list of ideas to prototype later
- explicit list of things ParamAItric should keep owning

## Guardrail for this lane

Borrow the modeling wisdom, not the runtime dependency.

At the current stage, ParamAItric should keep owning:

- MCP integration
- Fusion execution
- AI-facing workflow surface
- verification and recovery contract
- safety guardrails
- product direction

## Next actions

1. Run a first-pass review of a small set of mature Python CAD references.
2. Compare their modeling abstractions, workflow structure, and selector/reference approaches.
3. Review editable-document and scripting lessons from adjacent CAD environments where relevant.
4. Synthesize a comparison memo focused on what ParamAItric should borrow now.
5. Decide which ideas are worth prototyping internally without adding new runtime dependencies.
