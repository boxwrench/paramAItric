<p align="center">
  <img src="readmelogo.png" alt="ParamAItric" width="800"/>
</p>

# ParamAItric

CAD with questionable intelligence.

ParamAItric is an AI-assisted CAD project for Autodesk Fusion 360. It is focused on reliable parametric workflows for simple mechanical parts, not broad autonomous CAD.

The near-term goal is straightforward: take structured AI tool calls, create editable Fusion geometry, verify the result, and export fabrication-ready files.

## Current status

The repo currently includes:

- a Fusion 360 add-in with a loopback HTTP bridge
- an MCP-side workflow server layer
- regression tests around the workflow and live adapter behavior
- a repeatable live smoke runner

The current validated live paths are:

- `spacer`
- `bracket` blank on `xy` and `xz`

`bracket` is still a narrow rectangular-prism workflow at this stage. It is not yet a full L-bracket or hole-feature workflow.

## Live smoke test

Once the Fusion add-in is running in `live` mode, use the smoke runner:

```text
python scripts/fusion_smoke_test.py --workflow spacer
python scripts/fusion_smoke_test.py --workflow bracket --plane xz --output-path manual_test_output\live_smoke_bracket_xz.stl
```

The script stops on the first failure and prints each response payload so live Fusion mismatches are easy to inspect.

## Canonical docs

- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): product goals, scope, operating modes, and success criteria
- [ARCHITECTURE.md](ARCHITECTURE.md): system boundaries, execution model, and safety constraints
- [HOST_INTEGRATION.md](HOST_INTEGRATION.md): intended MCP host integration model and transport direction
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md): phased implementation plan
- [WORKFLOW_STRATEGY.md](WORKFLOW_STRATEGY.md): how workflow capability should expand

## Research

Supporting research notes live under [`docs/research`](docs/research). They are reference material, not the source of truth.

<p align="center">
  <img src="small logo.png" alt="ParamAItric logo" width="200"/>
</p>
