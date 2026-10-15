# Capability and dependency evidence — 2026-10-12

Evidence levels: **tested** means an actual run in this assignment; **historical**
means existing recorded results; **candidate** means upstream support, not a
ParamAItric integration pass; **research** is unqualified. Hardware scope matters.

| Capability | Fusion reference | cadgen / build123d / OCCT | FreeCAD | USD BRep / SMLib |
|---|---|---|---|---|
| Creation | Existing utility families; historical live smokes | Tested centered plate only; other families not translated | Candidate; no bridge implemented here | Research primitives/booleans/sweeps/fillets |
| Editing | Recipe replay in new adapter; existing workflows remain | Tested width 80→100 mm; hole center 40→50 mm | Native parameter/history editing upstream | Operations on BRep; no product parameter/history editing |
| Native BRep | Yes in Fusion | Yes, OCCT geometry; tested STEP read-back | Yes, OCCT upstream | Native NURBS/BRep upstream |
| Regeneration | New adapter numeric recipe; mock tested, fresh live proof pending | Tested saved recipe/parameter replay | Candidate via native document/bridge | Product recipe layer would be needed |
| Feature history | Fusion supports timeline; this contract does not certify linked native parameters | None promised; Python source recipe is editable | FCStd history/sketches upstream; unintegrated | No ParamAItric history contract |
| Export | Existing STL; new adapter STL only | Tested STEP + STL; upstream GLB/3MF available, not qualified here | STEP/STL upstream; not run here | USD/native BRep and OCCT interchange candidate; fabrication exports unqualified |
| Inspection | Scene/body read-back; missing validity/analytic bore facts in current bridge | Tested saved STEP envelope, volume, area, validity, circular bore rims | Candidate APIs | Queries; validity/measurement scope needs qualification |
| Linux | Fusion execution needs its supported host; Linux MCP client possible | Tested headless Linux x86_64 CPU worker | Linux upstream; Target B plan preserved | Linux build instructions upstream; not built here |
| AMD / GPU | Fusion host qualifications unchanged | Tested Ryzen 7 9800X3D CPU; no CUDA; graphics/Strix Halo pending | CPU geometry; viewer qualification pending | No mandatory CUDA in documented kernel build; AMD qualification not run |
| Limitations | Started cancellation best effort; native parameter links and new adapter live execution unproven | Only rectangle + centered circular cut; recipe, not native history; STL manifold check pending | Separate owned Python/process needed; integration/validation remains future | Build/OpenUSD complexity, consuming handles, healing/tessellation failures, approximation/invalid input qualification |
| Actual evidence | 17 unchanged mock cases; historical four Claude records; no fresh live Fusion | Real 80/100 mm plate through actual guided MCP stdio; retained edits, exported STEP inspection, STEP/STL; snapshots reviewed; viewer launched | Existing research + plan only | Upstream documentation evaluation only; no installed production dependency |

The new Fusion adapter reports limited capabilities rather than echoing requested
hole geometry as observed facts. Geometry equivalence involving missing facts is
`incomplete`, not `match`. Historical fixture JSON does not substitute for saved
Fusion geometry in a cross-backend proof.

## Tested runtime and resources

| Resource | Selected version | Constraint / qualification |
|---|---|---|
| ParamAItric MCP | 0.1.0; MCP 1.26.0 | Existing production dependency unchanged |
| CAD worker Python | 3.13.12 | Separate environment; Python 3.11+ supported upstream, other versions not run here |
| cadgen | 0.7.14 | Installed CAD skill's supported pin; upstream main reviewed at 0.7.21, not substituted silently |
| build123d | 0.11.1 | Runtime depends on the 0.11 series; deliberately pin before upgrades |
| cadquery-ocp-novtk | 7.9.3.1.1 | OCCT provider without VTK; CPU geometry |
| Playwright | 1.63.0 | Snapshot browser, separate from geometry proof |
| Node | Existing host runtime | Viewer/compile paths may need Node >=20; geometry worker does not |
| Transitive wheels | 59 exact distributions | `cad_backends/cadgen/requirements.lock.txt`; Linux x86_64/Python 3.13 local wheel cache |
| Reference documents | 16 files, four immutable upstream commits | `resources/upstreams.lock.json`; checksummed ignored cache |

All 59 cached wheels installed with `--no-index` into a fresh temporary environment;
the kernel imports and constructs a unit cube offline. Managed Python acquisition
and the first Playwright browser download are separate provisioning requirements.
The wheels are platform-specific, not portable to arbitrary CPUs/Python releases.

## Primary sources reviewed

- [text-to-cad](https://github.com/earthtojake/text-to-cad),
  [cadgen runtime contract](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/README.md),
  [dependency bounds](https://github.com/earthtojake/text-to-cad/blob/24573128ceaab564f497d7c12f995c41784c9539/packages/cadgen/pyproject.toml).
  Source-driven execution, saved-artifact readers, derived store, viewer and snapshot
  surfaces are supplied by the published package. MIT; no monorepo fork.
- [build123d](https://github.com/gumyr/build123d/blob/f5cca68a7500ec452759a463010aced0cbbd278f/README.md)
  provides parametric BRep geometry on OCCT; Apache-2.0.
  [OCCT overview](https://dev.opencascade.org/doc/overview/html/index.html) documents
  native BRep, modeling algorithms and STEP exchange. Dependencies retain their
  own licenses; packaging requires carrying applicable notices.
- [FreeCAD](https://github.com/FreeCAD/FreeCAD/blob/8df06f6c0e31694e84c6dde86593a6df04701363/README.md)
  documents editable parameter history, sketches and platform support. Keep
  [Target B](../../plans/B_VALIDATION_PLAN.md) as future bridge qualification.
- [USD BRep build/license](https://github.com/NVIDIA-Omniverse/usd-brep/blob/c9c5979f04cea8c38213004d4f04df0dcfb40d05/README.md),
  [architecture](https://github.com/NVIDIA-Omniverse/usd-brep/blob/c9c5979f04cea8c38213004d4f04df0dcfb40d05/.agents/docs/OVERVIEW.md),
  [error/ownership guidance](https://github.com/NVIDIA-Omniverse/usd-brep/blob/c9c5979f04cea8c38213004d4f04df0dcfb40d05/.agents/docs/errors.md).
  Apache-2.0 modeling libraries with a separate Packman/OpenUSD/Python 3.12 build.
  Binding success/status, schema validity and geometric validity are separate checks.

SMLib's CPU suitability on AMD is an inference from its documented native kernel
build and absence of mandatory CUDA in that path, not a performance result. No HIP
port or executable adapter was added. Any later spike must use copies for consuming
booleans, isolate malformed inputs and compare exact/approximate measurements on
the same plate fixtures before becoming a dependency.
## SolidCraft foundation candidate (2026-10-14)

SolidCraft is being evaluated as the combined modeling/document/UI foundation,
not promoted as a fifth production adapter. New cadgen recipes are frozen.

| Capability | Evidence / limit |
|---|---|
| Parametric creation/edit | Real v0.11.1 plate and flat L-profile through upstream headless MCP; dimension relationships, repeats and edits verified independently |
| Native feature history | Opt-in guided bridge plus adoption experiment: `.solidcraft` saved, cold-opened in fresh processes, edited and re-exported; a selected fillet survives native reopen and a width edit |
| STEP/STL | 26 saved STEP reads in independent OCCT, plus finite/count/envelope/signed-volume STL checks; full mesh manifold/intersection not checked |
| Failure/recovery | Oversized fillet/missing references rejected; batch rollback/checkpoint recovery verified; width zero changes state and reports payload errors despite `isError: false` |
| Cancellation | MCP notification did not stop saving; isolated process-group kill stopped scratch work and preserved original native bytes; opt-in bridge now kills/reaps disposable groups and shares atomic acceptance; prior revisions remain immutable |
| External native editing | Prepared parent-bound copies and declared changes; full native JSON history comparison; new immutable revision and eleven artifact hashes; real native two-family revalidation tested |
| UI / hardware | Official pinned web start screen observed on AMD desktop; no model opened through UI; desktop control/automated chooser unavailable; renderer/Strix Halo/human editing not run |
| Adoption | Experimental bridge plus external revalidation behind five tools; 953 tests / 5 expected failures and real 30.47 s proof; Fusion default and frozen OCCT reference unchanged; human/UI promotion pending |

See [the evaluation](solidcraft_evaluation.md), [resource lock](../../resources/solidcraft.lock.json)
and [actual evidence](evidence/solidcraft-v0.11.1-linux-2026-10-14.json).

The [SolidCraft integration runbook](solidcraft_integration.md) describes the actual
product tool path and remaining revalidation/UI limits.

[External edit contract and qualification limits](external_edit_revalidation.md)
records the twelve real failure cases and separates native editor-surrogate
evidence from the incomplete desktop/human loop.
