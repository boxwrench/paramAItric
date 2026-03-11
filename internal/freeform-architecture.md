# Freeform Architecture

This note describes the freeform system itself.
It is separate from the recipe corpus, which exists to exercise and validate the system.

## Purpose

The freeform path is the exploratory generation lane alongside structured workflows.
It is for cases where the part should be built incrementally through guided mutation and inspection
instead of a fixed `create_*` macro.

## Core Contract

The freeform system enforces a strict loop:

1. start a session with a feature manifest
2. perform exactly one mutation
3. verify the result before any further mutation
4. repeat until the manifest is resolved
5. end the session through a compliance audit

This is not just logging. It is the control surface that prevents unchecked mutation chains.

## Main Runtime Pieces

- `mcp_server/freeform.py`
  - session state model
  - mutation / inspection / session tool allowlists
  - mutation log export format
- `mcp_server/server.py`
  - session lifecycle methods
  - lock enforcement between mutation and verification
  - compliance audit at session end
- inspection tools
  - used while locked to diagnose geometry before committing verification

## State Model

The session has two states:

- `AWAITING_MUTATION`
- `AWAITING_VERIFICATION`

Rules:

- a mutation moves the session to `AWAITING_VERIFICATION`
- no further mutation is allowed until `commit_verification` succeeds
- a failed verification keeps the session locked
- inspection calls remain allowed while locked

This gives the AI a recovery path without allowing it to bulldoze past a bad assumption.

## Feature Manifest

A session starts with `target_features`.

During the session:

- verification commits may mark features as resolved
- end-of-session audit checks that each target feature is either resolved or explicitly deferred

The manifest is the semantic completion contract for freeform generation.
Geometry checks alone are not enough, because the AI can make something plausible but incomplete.

## Tool Classes

The freeform path uses three classes of tools:

- mutation tools
  - change the CAD state
- inspection tools
  - observe the CAD state and support recovery
- session tools
  - start, commit, end, and export session state

The allowlists in `mcp_server/freeform.py` are part of the architecture, not just convenience.

## Relationship To Structured Workflows

Structured workflows and freeform sessions are parallel modes:

- structured workflows
  - fixed shape recipe
  - deterministic stage sequence
  - intended for reusable named parts
- freeform sessions
  - guided incremental construction
  - intended for exploratory or benchmark-driven part creation

The freeform path is not a replacement for workflows.
It is a proving ground for behaviors that may later become workflows.

## What Counts As Architecture vs Corpus

Architecture:

- session lifecycle
- state lock behavior
- tool allowlists
- manifest / resolve / defer rules
- verification commit semantics
- compliance audit semantics

Recipe corpus:

- the specific FM-A through FM-E cases
- their dimensions and manifests
- targeted failure modes
- live-test observations
- helper scripts that replay those cases

If a recipe changes, that does not necessarily change the architecture.
If the state contract changes, that is an architectural change.

## Current Weak Spots

- single active freeform session is owned directly by `ParamAIToolServer`
- session persistence is in-memory only
- recipe runners are still the main executable examples of freeform usage
- some desired geometry still depends on missing primitives such as angled planes or richer combine patterns

## Practical Rule

When documenting or discussing freeform:

- put system rules in this architecture note
- put operating guidance in `docs/FREEFORM_PLAYBOOK.md`
- put benchmark cases in `internal/test-recipes.md`
- put session-specific findings in handoff notes
