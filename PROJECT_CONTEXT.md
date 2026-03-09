# ParamAItric Project Context

## Purpose

ParamAItric connects AI agents to Autodesk Fusion 360 through a constrained workflow interface.

The goal is not full autonomous CAD. The goal is a reliable path from structured intent to editable Fusion geometry for useful mechanical work.

## Current state

This repository now includes a working Fusion add-in bridge, an MCP-side workflow layer, tests, and a repeatable live smoke runner.

The current validated live scope is:

- `spacer`
- `bracket` on `xy` and `xz`
- `mounting_bracket` on `xy`
- `two_hole_mounting_bracket` on `xy`
- `plate_with_hole`
- `filleted_bracket`

`simple_enclosure` exists but remains mock-only.

The project is no longer just proving the bridge. It is in a validated workflow family plus use-and-fix phase.

## Product shape

ParamAItric is organized around:

1. typed operations
2. named workflows built from those operations
3. verification and failure handling around each workflow stage

The product direction is functional parametric CAD for defined mechanical parts and fabrication-oriented outputs. ParamAItric is not trying to become general "AI CAD," and it is not prioritizing decorative or organic modeling as the core use case.

The working philosophy is:

- staged workflows outperform one-shot requests
- validation before CAD operations matters
- verification after each major step matters
- human correction loops are a normal operating model
- more complex workflows should be built from proven smaller workflow paths

## V1 shape

The practical v1 lane is still mechanical basics:

- plates
- brackets
- spacers
- simple enclosures
- basic hole and cutout patterns

The key difference now is phase, not philosophy. The repo has already proven several narrow live workflows. The next value should come from practical part families and use-driven gaps, not from expanding the catalog for its own sake.

## Operating modes

### Work Mode

Work Mode is the default. It is for deterministic part creation where predictability matters more than breadth.

Expected behavior:

- small tool surface
- strong validation
- explicit stage ordering
- verification checkpoints between milestones
- clear failures with partial progress preserved

### Utility Mode

Utility Mode is for automation around an existing design rather than geometry creation itself.

Expected behavior:

- low-risk operations
- clear reporting on what changed
- stronger file and path controls

### Creative Mode

Creative Mode is later-stage work for exploratory modeling after the reliable core is strong enough.

It is useful for evaluation and edge testing, but it is not the primary value proposition for this repo.

## Success criteria

The first success condition was narrow:

1. an AI agent can call a small set of tools through MCP
2. those tools can create a simple part inside Fusion 360
3. the part can be exported without manual CAD intervention

That threshold has now been crossed for a small family of mechanical workflows.

The next success condition is more practical:

- the workflows reliably generate the handful of parts that matter in real use
- failures are clear and recoverable
- outputs are dimensionally trustworthy

## Design principles

- Keep the workflow surface narrow and explicit.
- Prefer typed operations over broad natural-language commands.
- Treat staged build -> verify -> continue as the default pattern.
- Preserve clean partial results when a workflow fails.
- Expand only after the previous slice is stable.
- Let real parts drive the next workflow gaps.
- Keep the user in control of risky or destructive actions.
