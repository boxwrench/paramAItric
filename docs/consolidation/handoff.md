# Consolidation handoff — 2026-10-12

The requested foundation is implemented on
`consolidation/utility-backend-2026-10-12`, with a real Linux CPU plate/replay proof.
Master is unchanged. The user authorized the next bounded product-integration batch;
track that work in [next-batch.md](next-batch.md).

## Reviewable commits and changes

- `f26f356`: branch reconciliation, rollback commit and pre-refactor test baseline.
- `51e6b38`: neutral plate contract, product gates/replay, Fusion adapter, bounded
  cadgen/build123d worker, pinned requirements, regression and real geometry tests.
- `d3f9b26`: upstream resource lock, preparation/verification script, resource guide
  and ignored local wheel/reference cache.
- Consolidation docs: architecture, dependency/capability matrix, integration plan,
  decisions, this handoff and real proof JSON. Canonical README/ARCHITECTURE/ROADMAP,
  docs/AI_CONTEXT/docs guide and evaluations guide updated. Prior roadmap archived
  verbatim; all existing research and Target B plan preserved.

Runtime changes: `cad_backends/{protocol,fusion}.py`,
`cad_backends/cadgen/{adapter,recipe}.py`, `mcp_server/utility_plate.py`, finite XY
placement in `mcp_server/operations.py`, and setuptools discovery/package data.
Tests: new `test_utility_plate.py`, package-discovery protection and two owned-bridge
profile-test fixes. No production changes in `fusion_addin/`, BridgeClient,
freeform mutation/session code or legacy workflow implementations.

## Architecture decisions

ParamAItric owns a centered-plate recipe and the stage acceptance contract. Backend
adapters own native execution/bindings. Operation results are read back and checked
before another mutation/export. Capabilities are explicit; missing bore/native
validity facts in Fusion cannot become a full proof. Editability is a retained source
recipe, not a claim of native sketch/history editability. STEP/STL alone are static.

Only two existing operation modes are translated. Open geometry uses public cadgen
build123d interfaces with mature OCCT construction/export/readers in a dedicated
worker. Native exporters avoid daemon work escaping execution limits. No upstream
source code, viewer/cache implementation, CUDA requirement or speculative framework
was added. See [decisions](decisions.md) and [architecture](architecture.md).

## Executed evidence

| Check | Result |
|---|---|
| Full pre-refactor suite | 793 passed, 5 xfailed, 2 pre-existing profile isolation failures |
| Final foundation suite, real gate enabled | **809 passed, 5 xfailed**, no failures; 110.36 s |
| Original evaluation runner | **17/17 passed**: 8 contract, 9 safety, no live/model evidence |
| Real open-backend Linux smoke | Both plate builds and exports passed; offline-provisioned worker; 12.86 s total |
| Saved-artifact negative test | Malformed STEP rejected; required-verification failure prevents subsequent mutation/export |
| Dependency cache | 59 exact wheels installed with `--no-index`; unit cube measured 1 mm³ |
| Resource verification | 75 resource hashes verified: 59 wheels, 16 pinned reference documents |
| Existing viewer | Launched at returned local URL; both model snapshots generated and visually reviewed |
| Static checks | compileall and git diff whitespace checks passed |

One existing Pydantic settings forward-reference warning remains. Five legacy xfails
remain expected; they are not newly demonstrated functionality. Restricted token-file
tests need the permissions described in [baseline](baseline.md).

The committed [real proof](evidence/plate-linux-2026-10-12.json) records source/fixture
hashes, runtime versions, artifact hashes, provenance-aware stage signals and:

| Revision | Envelope (mm) | Bore center (mm) | Diameter | Native volume (mm³) |
|---|---|---|---|---|
| Initial | 80×60×5 | 40,30 | 10 mm | 23607.30091830126 |
| Width edit | 100×60×5 | 50,30 | 10 mm | 29607.30091830126 |

Both have one valid solid and a through-hole. Final STEP was retained; binary STL
was independently parsed for finite coordinates, triangles, bounds and volume.
Source parameters retain the `width/2` relationship. The read-back is independent
of operation responses, but uses the same OCCT kernel, not another modeling kernel.

Local artifacts: `manual_test_output/utility-cadgen-final/` (ignored).
The proof JSON retains their exact filenames and SHA-256 hashes; rerun the
[runbook](integration_plan.md) to reproduce artifacts on another checkout.
Local logs: `/tmp/paramaitric-final-pytest.log`, `/tmp/paramaitric-evaluations.log`.

## Preserved behavior and gaps

Fusion remains the public default. Existing full/guided tool names/schemas, 17
fixtures, selectors, error contract, auth/threading/deadline/cancellation and
freeform verify/commit rules remain usable. The new neutral Fusion adapter is
mock-tested; fresh live Fusion validation remains a separate requirement.

Not demonstrated: native parameter-linked Fusion history, cross-backend saved
Fusion geometry parity, Strix Halo interactive AMD graphics, full STL manifold or
self-intersection qualification, I2 Pi/Lemonade/Qwen → live Fusion, FreeCAD bridge
or SMLib integration. No environmental blocker prevents the next product batch.

## Exact continuation

Connect this verified centered-plate path to the existing guided `cad_build` through
explicit operator configuration, preserve default Fusion routing, add revision
replay and read-only saved-model inspection, and exercise cancellation/negative
contracts before promoting the product slice. This is now the active
[authorized batch](next-batch.md), not an unbounded migration of every workflow.

A one-shot local timer (`paramaitric-return-20261013.timer`) queues a follow-up in
the same Codex thread at **2026-10-13 03:25:49 America/Los_Angeles**. It depends on
the host/Codex service staying available; its metadata is in the ignored resource
cache. It does not merge, publish or change permission settings.
