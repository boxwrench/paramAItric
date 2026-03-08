# ParamAItric Project Context

## Purpose

ParamAItric is an internal project to connect AI agents to Autodesk Fusion 360 through a constrained tool interface. The near-term goal is not full autonomous CAD. It is a reliable path from natural-language intent to simple, editable Fusion geometry.

The system is intended to let an AI:

- create and edit sketches
- generate simple solid features
- automate repetitive CAD preparation tasks
- export artifacts for fabrication or review

## Current state

This repository now includes an initial implementation scaffold for the Fusion add-in bridge, MCP-side tool server, and tests. The current code is a mock-backed first slice intended to lock the interfaces and workflow discipline before full Fusion API integration.

## Product shape

The product is organized around a small typed tool surface exposed to AI agents through MCP. The CAD mutations happen inside Fusion 360 through its Python API. The project expands capability in stages so early workflows stay predictable.

The primary product direction is functional parametric CAD for defined mechanical parts and fabrication-oriented outputs. ParamAItric is not trying to be a general "AI for all CAD" layer, and it is not prioritizing Blender-style creative 3D workflows as the core use case.

The intended stack is:

1. Core layer: small typed CAD operations.
2. User layer: a few named templates built on top of those operations.
3. Later UX layer: broader natural-language requests that compile down to the structured chain.

Benchmark evidence from Faust reinforces three operating assumptions for v1:

- staged workflows outperform one-shot requests
- verification after each major step materially improves reliability
- human correction loops are the normal operating model, not a fallback of last resort
- complex workflows should be built from proven smaller workflow paths rather than attempted whole at once

Primary target workflows:

- simple 3D-printable mechanical parts
- repetitive CAD housekeeping and export tasks
- later-stage exploratory geometry generation

## V1 target

The explicit v1 target is mechanical basics:

- plates
- brackets
- spacers
- simple enclosures
- basic hole patterns and cutouts

These workflows are narrow enough to be testable and reliable while still covering useful functional-print work.

## Operating modes

### Work Mode

Work Mode is the default operating mode. It is for deterministic part creation where predictability matters more than breadth.

Typical outputs:

- brackets
- spacers
- mounts
- plates
- simple enclosures

Expected behavior:

- small tool surface
- tight validation
- minimal batch behavior
- easy-to-understand failures
- verification checkpoints between major milestones
- no automatic rebuild of already valid geometry unless verification proves it is wrong

### Utility Mode

Utility Mode is for automation around an existing design rather than geometry creation itself.

Typical outputs:

- renamed entities
- component cleanup
- material and appearance assignment
- exports for STL, STEP, or DXF
- basic manufacturing prep

Expected behavior:

- mostly low-risk operations
- stronger file and path controls
- clear reporting on what changed

### Creative Mode

Creative Mode is for exploratory modeling once the reliable core exists.

Typical outputs:

- lofted or patterned variations
- decorative or organic geometry
- design-space exploration

Expected behavior:

- broader tool surface
- more tolerant failure handling
- controlled experimentation rather than guaranteed success

Creative and organic modeling remain later-stage work. They are useful for evaluation and edge testing, but they are not the primary v1 value proposition.

## Success criteria

The first meaningful success condition is narrow:

1. An AI agent can call a small set of tools through MCP.
2. Those tools can create a simple part inside Fusion 360.
3. The resulting part can be exported as STL without manual intervention.

The first coded workflow should be a low-ambiguity mechanical part. `Spacer` is the default golden path because it exercises sketch creation, profile resolution, extrusion, verification, and STL export without requiring early fit logic.

Longer term, success means the system can support both reliable CAD work and controlled experimentation without losing safety or recoverability.

## External references

Existing Fusion MCP projects can be used as benchmarks and implementation references, but they are not the product definition for ParamAItric. Blender-side MCP projects are useful inspiration for workflow ergonomics and packaging, yet Fusion remains the core substrate because functional parametric work is the primary target.

## Design principles

- Keep the first tool surface small.
- Prefer explicit, typed operations over broad natural-language commands.
- Expand only after the previous pass is stable.
- Keep the user in control of risky or destructive actions.
- Optimize for reliable mechanical-part workflows before broader creative capability.
- Preserve a slightly self-aware tone without letting branding get in the way of engineering clarity.
- Treat staged build -> verify -> continue as the default workflow pattern.
- Preserve clean partial results when a workflow fails instead of retrying indefinitely.
- Expand complexity by composing validated sub-workflows rather than broadening prompts blindly.
