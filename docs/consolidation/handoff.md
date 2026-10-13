# Consolidation handoff — 2026-10-12

The requested foundation is implemented on
`consolidation/utility-backend-2026-10-12`, with a real Linux CPU plate/replay proof.
Master is unchanged. The authorized next product-integration batch is also complete;
its checklist is in [next-batch.md](next-batch.md).

The October 13 review corrections are implemented and locally validated on this
same branch. The merge remains unauthorized; master and releases are unchanged.

## Reviewable commits and changes

- `f26f356`: branch reconciliation, rollback commit and pre-refactor test baseline.
- `51e6b38`: neutral plate contract, product gates/replay, Fusion adapter, bounded
  cadgen/build123d worker, pinned requirements, regression and real geometry tests.
- `d3f9b26`: upstream resource lock, preparation/verification script, resource guide
  and ignored local wheel/reference cache.
- `ba2a880`: consolidation docs, preserved roadmap and initial geometry evidence.
- `d9e7bcf`: configured guided builds, retained edits, exported STEP inspection,
  transaction/cancellation guards and actual MCP stdio proof runner.
- Consolidation docs: architecture, dependency/capability matrix, integration plan,
  decisions, this handoff and real proof JSON. Canonical README/ARCHITECTURE/ROADMAP,
  docs/AI_CONTEXT/docs guide and evaluations guide updated. Prior roadmap archived
  verbatim; all existing research and Target B plan preserved.

Runtime changes: `cad_backends/{protocol,fusion}.py`,
`cad_backends/cadgen/{adapter,recipe}.py`, `mcp_server/utility_plate.py`, finite XY
placement in `mcp_server/operations.py`, and setuptools discovery/package data.
Tests: new `test_utility_plate.py` and `test_utility_runtime.py`, package-discovery
protection and two owned-bridge profile-test fixes. The guided MCP path now calls
the server’s one backend-aware dispatcher; conditional guards prevent fallback.
No production changes in `fusion_addin/`, BridgeClient, freeform mutation/session
code or legacy geometry workflow implementations.

## Review corrections — 2026-10-13

Code commit `344e898` closes all three P1 findings and the P2 cleanup finding:

- Geometry evidence now stages in `geometry-verification.json`. Only the guided
  runtime atomically publishes a complete accepted `verification.json` after the
  request's cancellation/commit lock resolves. Precommit cancellation leaves no
  reloadable accepted revision; late cancellation returns the committed result.
- Reopening checks all six artifact hashes and saved parameters before inspection
  or replay. Changed/missing STEP, STL, recipe, parameters, runtime or mesh evidence
  fails at `revision_integrity`; regenerate and verify a new revision.
- Open-backend schemas make `output_path` optional, bare filenames resolve within
  the configured root, and its CAD request prompt recommends automatic destination
  selection. Returned revision artifact paths remain authoritative. Fusion's
  default schema, destinations and prompt behavior are preserved.
- Health probe cleanup runs in `finally` on success and dependency/worker failure.

Validation: **843 passed, 5 xfailed** with both real CAD gates enabled (126.35 s);
focused run **55 passed**; unchanged **17/17 contract/safety cases passed**. The
existing Pydantic settings warning remains. The initial restricted subprocess run
stalled and was stopped; the supported-permission runs completed. Logs:
`/tmp/paramaitric-review-{targeted,full,evaluations}.log`.

The [new committed-code MCP stdio proof](evidence/plate-guided-review-linux-2026-10-13.json)
ran against `344e898` in **14.90 s**. It built without an output-path argument,
regenerated 80→100 mm width, remeasured the centered 10 mm through-hole and rejected
modified STEP and STL hashes. Both artifacts were restored after negative tests;
all source hashes and 12 artifact hashes were checked afterward. Outputs reside
in ignored `manual_test_output/utility-review-proof/`. This is headless CPU geometry
evidence on the existing Linux host; no new GPU, live Fusion or model-in-loop
qualification is claimed. Remote CI for these corrections has not been checked.

Compatibility: older records without explicit `acceptance: accepted` remain
historical evidence but are not automatically adopted as accepted revisions.
Regenerate them from measured parameters through the current guided workflow.

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

## Executed foundation evidence (before review corrections)

| Check | Result |
|---|---|
| Full pre-refactor suite | 793 passed, 5 xfailed, 2 pre-existing profile isolation failures |
| Final foundation suite, real gate enabled | **809 passed, 5 xfailed**, no failures; 110.36 s |
| Full guided integration suite, both real gates enabled | **823 passed, 5 xfailed**, no failures; 129.31 s |
| Final focused runtime guards | 14 tests passed after record validation; 13 nongeometry guards passed after the final portable-schema refinement |
| Actual MCP stdio on committed `d9e7bcf` | Five tools; real build/edit/exported STEP inspection; unsupported/malformed output rejected; 15.83 s |
| Cancellation/timeout | MCP request-local event and actual parent/child process-group termination exercised |
| Original evaluation runner | **17/17 passed**: 8 contract, 9 safety, no live/model evidence |
| Real open-backend Linux smoke | Both plate builds and exports passed; offline-provisioned worker; 12.86 s total |
| Saved-artifact negative test | Malformed STEP rejected; required-verification failure prevents subsequent mutation/export |
| Dependency cache | 59 exact wheels installed with `--no-index`; unit cube measured 1 mm³ |
| Resource verification | 75 resource hashes verified: 59 wheels, 16 pinned reference documents |
| Existing viewer | Launched at returned local URL; both model snapshots generated and visually reviewed |
| Static checks | compileall and git diff whitespace checks passed |

One existing Pydantic settings forward-reference warning remains. Five legacy xfails
remain expected; they are not newly demonstrated functionality. Restricted token-file
tests need the permissions described in [baseline](baseline.md). A restricted
async/stdio attempt stalled before builds; only the identified test processes were
stopped and the supported-permission runs passed. No production blocker remains.

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

The [guided MCP proof](evidence/plate-guided-linux-2026-10-12.json) records committed
source `d9e7bcf`, the actual five-tool stdio surface and build/edit/export read-back.
Its malformed exported STEP was restored after the negative check. Both final
model snapshots were generated and reviewed.

Local artifacts: `manual_test_output/utility-cadgen-final/` and
`manual_test_output/utility-guided-release-proof/` (ignored).
The proof JSON retains their exact filenames and SHA-256 hashes; rerun the
[runbook](integration_plan.md) to reproduce artifacts on another checkout.
Local logs: `/tmp/paramaitric-final-pytest.log`, `/tmp/paramaitric-batch-full.log`,
`/tmp/paramaitric-batch-targeted-final.log`, `/tmp/paramaitric-batch-schema-final.log`
and `/tmp/paramaitric-batch-evaluations.log`.

## Preserved behavior and gaps

Fusion remains the default. Explicit cadgen configuration exposes the same five
guided tools with one qualified workflow and retained revision edits. Existing full/guided tool names/schemas, 17
fixtures, selectors, error contract, auth/threading/deadline/cancellation and
freeform verify/commit rules remain usable. The new neutral Fusion adapter is
mock-tested; fresh live Fusion validation remains a separate requirement.

Not demonstrated: native parameter-linked Fusion history, cross-backend saved
Fusion geometry parity, Strix Halo interactive AMD graphics, full STL manifold or
self-intersection qualification, I2 Pi/Lemonade/Qwen → live Fusion, FreeCAD bridge
or SMLib integration. No environmental blocker prevents the next product batch.

## Exact continuation

Run the implemented guided plate smoke and viewer orbit/measurement checks on
Strix Halo AMD/Linux, recording graphics API/driver and CPU timings. Capture fresh
live Fusion plate outputs and compare common facts with explicitly incomplete
measurements. The [software batch](next-batch.md) is complete; do not fabricate
hardware/live qualification or expand to all workflow families at once.

A one-shot local timer (`paramaitric-return-20261013.timer`) queues a follow-up in
the same Codex thread at **2026-10-13 03:25:49 America/Los_Angeles**. It depends on
the host/Codex service staying available; its metadata is in the ignored resource
cache. It does not merge, publish or change permission settings.
