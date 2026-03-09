<p align="center">
  <img src="readmelogo.png" alt="ParamAItric" width="800"/>
</p>

# ParamAItric

CAD with questionable intelligence.

ParamAItric is an AI-assisted CAD project for Autodesk Fusion 360. It is focused on narrow, reliable parametric workflows for useful mechanical parts, not broad autonomous CAD.

The operating model is explicit:

- staged workflows
- schema validation before CAD operations
- verification after geometry milestones
- repeatable smoke automation
- small useful part families over general-purpose modeling

## Current status

The repo currently includes:

- a Fusion 360 add-in with a loopback HTTP bridge
- an MCP-side workflow server layer
- regression tests around the workflow and live adapter behavior
- a repeatable live smoke runner

Current suite baseline: `234 passed`, with the existing `TestFusionApiAdapter` pytest collection warning.

The current validated live paths are:

- `spacer`
- `bracket` L-profile workflow on `xy` and `xz`
- `mounting_bracket` workflow on `xy`
- `two_hole_mounting_bracket` workflow on `xy`
- `plate_with_hole`
- `two_hole_plate`
- `filleted_bracket`

`simple_enclosure` exists as a mock-only workflow and is not yet live-validated.

`slotted_mount` is now implemented and test-covered as the next placement-focused slice, but it is not yet live-validated.

The project has moved beyond scaffold proof. The current phase is a validated workflow family plus use-and-fix: keep a small dependable catalog working well enough for real parts, then let real use expose the next gaps.

## Live smoke test

Once the Fusion add-in is running in `live` mode, use the smoke runner:

```text
python scripts/fusion_smoke_test.py --workflow spacer

python scripts/fusion_smoke_test.py --workflow bracket --plane xz --width-cm 4.0 --height-cm 2.0 --thickness-cm 0.75 --leg-thickness-cm 0.5 --output-path manual_test_output\live_smoke_bracket_l_xz.stl

python scripts/fusion_smoke_test.py --workflow mounting_bracket --plane xy --width-cm 4.0 --height-cm 2.0 --thickness-cm 0.75 --leg-thickness-cm 0.5 --hole-diameter-cm 0.4 --hole-center-x-cm 0.25 --hole-center-y-cm 1.5 --output-path manual_test_output\live_smoke_mounting_bracket_xy.stl

python scripts/fusion_smoke_test.py --workflow two_hole_mounting_bracket --plane xy --width-cm 4.0 --height-cm 2.0 --thickness-cm 0.75 --leg-thickness-cm 0.5 --hole-diameter-cm 0.4 --hole-center-x-cm 0.25 --hole-center-y-cm 1.5 --second-hole-center-x-cm 0.25 --second-hole-center-y-cm 0.75 --output-path manual_test_output\live_smoke_two_hole_mounting_bracket_xy.stl

python scripts/fusion_smoke_test.py --workflow plate_with_hole --plate-width-cm 4.0 --plate-height-cm 2.5 --plate-thickness-cm 0.4 --hole-diameter-cm 0.6 --hole-center-x-cm 2.0 --hole-center-y-cm 1.25 --output-path manual_test_output\live_smoke_plate_with_hole.stl

python scripts/fusion_smoke_test.py --workflow two_hole_plate --plane xy --width-cm 4.0 --height-cm 2.0 --thickness-cm 0.4 --hole-diameter-cm 0.4 --hole-center-y-cm 1.0 --edge-offset-x-cm 0.75 --output-path manual_test_output\live_smoke_two_hole_plate.stl

python scripts/fusion_smoke_test.py --workflow slotted_mount --plane xy --width-cm 4.0 --height-cm 2.0 --thickness-cm 0.4 --slot-length-cm 1.5 --slot-width-cm 0.5 --slot-center-x-cm 2.0 --slot-center-y-cm 1.0 --output-path manual_test_output\live_smoke_slotted_mount.stl

python scripts/fusion_smoke_test.py --workflow filleted_bracket --plane xy --width-cm 4.0 --height-cm 2.0 --thickness-cm 0.75 --leg-thickness-cm 0.5 --fillet-radius-cm 0.2 --output-path manual_test_output\live_smoke_filleted_bracket.stl
```

The script stops on the first failure, verifies the returned geometry instead of only printing it, and now fails fast if the loaded Fusion add-in exposes a stale workflow catalog.

## Canonical docs

- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): product goals, scope, operating modes, and success criteria
- [ARCHITECTURE.md](ARCHITECTURE.md): system boundaries, execution model, and safety constraints
- [HOST_INTEGRATION.md](HOST_INTEGRATION.md): intended MCP host integration model and transport direction
- [WORKFLOW_STRATEGY.md](WORKFLOW_STRATEGY.md): how workflow capability should expand
- [BEST_PRACTICES.md](BEST_PRACTICES.md): living workflow and prompting contract
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md): current roadmap, validated state, and active priorities
- [docs/dev-log.md](docs/dev-log.md): execution evidence and validation log

## Research

Supporting research notes live under [`docs/research`](docs/research). They are reference material, not the source of truth.

<p align="center">
  <img src="small logo.png" alt="ParamAItric logo" width="200"/>
</p>
