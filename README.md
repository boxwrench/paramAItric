<p align="center">
  <img src="readmelogo.png" alt="ParamAItric" width="800"/>
</p>

# ParamAItric

CAD with questionable intelligence.

ParamAItric is a draft AI-assisted CAD system for Autodesk Fusion 360. The intended architecture is a Fusion 360 add-in that exposes a loopback-only HTTP bridge, plus a separate MCP server that lets AI agents call typed CAD tools safely.

The project is optimized for functional prints and basic parametric CAD, not broad "AI for all CAD" and not Blender-style creative 3D as the primary use case. The near-term goal is reliable natural-language access to well-defined mechanical part workflows such as plates, brackets, spacers, and simple enclosures.

Current status: the repo now contains an initial implementation scaffold for the Fusion add-in bridge, MCP-side tool server, and tests, alongside the research and planning material. The scaffold is mock-backed and defines the first coded golden path rather than a full Fusion-integrated product.

The current implementation scaffold now establishes the first build slice:

- Python Fusion add-in skeleton with loopback HTTP bridge
- Python MCP-side tool server
- one-command-at-a-time dispatch model
- mock-backed golden-path workflow for creating and exporting a spacer

The add-in bootstrap now selects `mock` mode outside Fusion and reserves `live` mode for a real Fusion design context, so the bridge contract can be tested locally without pretending the live CAD path already exists.

## Positioning

Existing Fusion MCP repos such as Faust are useful implementation and benchmarking references, especially for validating a real Gemini-hosted workflow. ParamAItric is intended to diverge by keeping the tool surface narrower, the defaults safer, and the mechanical-part workflows more predictable.

## Intended product stack

The intended product shape is layered:

1. Core layer: small typed CAD operations for sketching, profile selection, feature creation, and export.
2. User layer: a few named part templates built on those operations.
3. Later UX layer: broader natural-language requests compiled into the structured tool chain.

The Faust benchmark reinforced this structure rather than changing it. The key implementation rule is that staged workflows and verification checkpoints are part of the product, not just prompting advice.

## Canonical docs

- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): product goals, intended users, operating modes, and success criteria.
- [ARCHITECTURE.md](ARCHITECTURE.md): system boundaries, threading model, token strategy, and safety constraints.
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md): phased implementation plan and the minimum first milestone.
- [WORKFLOW_STRATEGY.md](WORKFLOW_STRATEGY.md): how validated workflow paths should be learned, standardized, and extended.

## Research

Long-form build guides, notes, and overlapping drafts live under [`docs/research`](docs/research). They are supporting references, not the source of truth.

## Intended repository shape

The first implementation pass should introduce a structure close to:

```text
fusion_addin/
mcp_server/
docs/
  research/
tests/
```

<p align="center">
  <img src="small logo.png" alt="ParamAItric logo" width="200"/>
</p>
