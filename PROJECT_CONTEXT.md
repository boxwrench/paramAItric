# ParamAItric Project Context

## Purpose

ParamAItric connects AI agents to Autodesk Fusion 360 through a constrained workflow interface.

The goal is not full autonomous CAD. The goal is a reliable path from structured intent to editable Fusion geometry for useful mechanical work.

The emerging practical lane for that work is utility and facility maintenance parts: brackets, plates, covers, adapters, handles, and other small replacement parts that are simple to model but expensive or slow to procure.

## Current state

This repository now includes a working Fusion add-in bridge, an MCP-side workflow layer, a packaged MCP stdio entrypoint, read-only inspection tools, tests, and a repeatable live smoke runner.

The live-validated surface now spans the main bracket, plate, box-adjacent, and early cylindrical workflow families, plus the inspection lane and packaged MCP entrypoint. `box_with_lid` is treated as a finished validated multi-body slice, and `tube_mounting_plate` is the first live-validated joined-body cylindrical utility template.

Treat [DEVELOPMENT_PLAN.md](/C:/Github/paramAItric/DEVELOPMENT_PLAN.md) as the current status and priority doc, and treat [docs/dev-log.md](/C:/Github/paramAItric/docs/dev-log.md) as the dated evidence trail for exact validation claims.

The project is no longer just proving the bridge. It is in a validated workflow family plus use-and-fix phase.

That phase is now informed by a clearer real-world target: replacement and maintenance parts for utility, plant, and field equipment. See [docs/utility-parts-concept.md](/C:/Github/paramAItric/docs/utility-parts-concept.md) for the non-canonical concept note that informs workflow choice.

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
- domain-specific material and environment advice should live above the CAD tool surface as prompt knowledge, not as core geometry primitives

## V1 shape

The practical v1 lane is still mechanical basics:

- plates
- brackets
- spacers
- simple enclosures
- cylindrical utility parts
- basic hole and cutout patterns

The near-term template lens for those basics is utility and maintenance work:

- valve handles and stem sockets
- instrument brackets and adapter plates
- covers, guards, and splash shields
- shims, spacers, and clamp-like fixtures
- wall-mount sleeves and pole or conduit holders

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

### Utility Operations Mode

This mode is for automation around an existing design rather than geometry creation itself.

This is distinct from the utility-parts product lane described above. The lane is about what kinds of parts the project should prioritize. This mode is about a lower-risk operational style when acting on an existing design.

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
- a measured replacement part can move from intent to printable output on the same day

## Design principles

- Keep the workflow surface narrow and explicit.
- Prefer typed operations over broad natural-language commands.
- Treat staged build -> verify -> continue as the default pattern.
- Preserve clean partial results when a workflow fails.
- Expand only after the previous slice is stable.
- Let real parts drive the next workflow gaps.
- Keep the user in control of risky or destructive actions.
