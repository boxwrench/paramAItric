# ParamAItric Community Add-in Integration Strategy

Status: future consideration

This document captures a potential expansion path for ParamAItric: leveraging community Fusion 360 add-ins as a source of domain-specific geometry expertise.

This is not current implementation work. It is a reference for when the core workflow catalog is stable enough to justify adding external capabilities.

## Why this matters

Community add-ins encode specialized domain knowledge that would be expensive to rebuild from scratch:

- gear generators
- thread profiles
- knurling patterns
- sheet metal helpers
- joinery templates
- enclosure generators
- airfoil profiles
- other domain-specific geometry workflows

Rebuilding all of that inside ParamAItric is neither realistic nor necessary.

At the same time, community add-ins are usually built for manual UI interaction, not AI-driven workflows. They often lack the validation, verification, failure boundaries, and deterministic operating model ParamAItric needs.

The default integration stance should be:

- treat community add-ins as reference implementations and geometry-pattern sources
- do not treat them as default runtime dependencies

## Integration approaches

### 1. Learn and reimplement

Preferred approach.

Study what a community add-in does at the Fusion API level. Extract the geometry logic, parameter calculations, and feature sequence. Reimplement that sequence as a ParamAItric tool with proper validation, verification, and error handling.

Advantages:

- full control over validation and failure handling
- clean fit with the staged workflow model
- no external runtime dependency
- testable in the normal ParamAItric promotion path
- resilient to upstream abandonment or API churn

Disadvantages:

- requires understanding someone else's code and assumptions
- more up-front work per capability
- may miss domain subtleties the original author learned over time

Use this when:

- the use case is recurrent and valuable
- reliability matters more than speed of integration
- the Fusion API path is understandable
- the result needs to remain editable and timeline-friendly

### 2. Wrap and call directly

If a community add-in exposes clean callable Python functions, ParamAItric could call those functions from inside the Fusion main-thread execution path after doing its own validation.

Advantages:

- faster integration when the add-in has a stable callable surface
- preserves the original author's domain logic directly
- less reimplementation work

Disadvantages:

- runtime dependency on a third-party add-in being installed and compatible
- fragile across upstream internal API changes
- harder to test outside live Fusion
- error handling quality depends on the external add-in

Use this when:

- the add-in is well-maintained
- the callable interface is stable
- reimplementation cost is unusually high
- the capability is experimental or Creative Mode-oriented rather than core Work Mode

### 3. Output capture

Run the community add-in manually or through its own UI, then use ParamAItric Utility Mode tools to inspect, rename, verify, and export the result.

Advantages:

- no code-level coupling
- works even for closed-source or UI-only add-ins
- still benefits from ParamAItric inspection and export discipline

Disadvantages:

- manual intervention remains in the loop
- breaks full end-to-end automation
- no direct programmatic parameter control

Use this when:

- the add-in is closed-source
- there is no callable API
- the geometry is a one-time input into a broader ParamAItric workflow

## Default rules

- Prefer reimplementation over wrapping.
- Extract the smallest reusable capability, not the whole add-in concept.
- Define the verification contract before adopting the capability.
- If a tool cannot be represented in mock or harness tests, it should not graduate to Work Mode.
- There is no unreviewed runtime execution path for third-party add-in code in Work Mode.

## Vetting checklist

Before adopting any community-derived capability, evaluate it against these criteria.

### Source quality

- Source code is available and readable.
- The code uses standard Fusion API patterns.
- Fusion mutations happen on the main thread.
- Error handling exists and is not silently suppressive.
- There are no unsafe environment assumptions or hardcoded paths.
- The license permits study and reimplementation.

### Geometry quality

- The result is editable and timeline-friendly.
- Parametric intent is preserved where appropriate.
- Sketches and features are structured sensibly.
- Bodies and features are named clearly.
- Construction geometry is used appropriately.
- The output is dimensionally correct for the intended use case.

### Reliability

- The add-in works on current Fusion versions.
- Edge cases are handled reasonably.
- Failure does not leave the design in an unrecoverable state.
- The capability has been exercised on at least the basic case ParamAItric would rely on.
- It does not conflict with ParamAItric's bridge or normal add-in behavior.

### Maintenance

- The repository has recent activity or is at least understandable enough to reimplement safely.
- The author or maintainer is identifiable.
- If the add-in is abandoned, the API patterns it uses are still stable enough to study and reimplement.

### Integration fit

- It fills a real gap in ParamAItric's workflow surface.
- It maps to an actual user need rather than novelty.
- It can be expressed as a typed operation with clear inputs and outputs.
- Its result can be verified programmatically.
- It fits an existing or planned workflow stage sequence.
- The intended operating mode is clear: Work, Utility, or Creative.

## Promotion path

Community-derived tools should follow the same promotion path as any other ParamAItric capability:

1. Prototype in Creative Mode with relaxed assumptions.
2. Harden in Utility Mode with input validation and output verification.
3. Promote to Work Mode only after repeated testing, handled edge cases, and stable verification checkpoints.

Tools that never graduate past Creative Mode can still be useful. The important rule is that they must not weaken the reliability of the core Work Mode surface.

## Candidate domains

Community add-ins that may complement ParamAItric's functional-print focus include:

- thread generation
- hole and bolt-circle patterns
- gear generators
- sheet metal helpers
- enclosure generators
- fastener and insert libraries
- text and labeling tools
- knurling and grip-pattern generators

Each candidate should pass the vetting checklist before integration work begins.

## What this is not

This is not a general plugin system.

ParamAItric should not load or execute arbitrary third-party add-in code at runtime without explicit review, validation, and workflow-level safeguards.

The goal is curated expansion of the tool surface using community knowledge as input, not dependency-driven feature sprawl.
