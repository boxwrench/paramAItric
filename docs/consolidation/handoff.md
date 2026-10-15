# Consolidation handoff — 2026-10-12

**Current follow-up, 2026-10-14:** the authorized experimental SolidCraft bridge
is implemented behind ParamAItric's existing five guided tools. Read
[setup and transaction contract](solidcraft_integration.md). Both plate/L-profile
native replay/reopen and cold independent STEP/STL verification execute; native
errors, process cancellation, artifact integrity and atomic acceptance are guarded.
Fusion remains default, new cadgen recipes remain frozen, and no UI/default-engine
promotion is claimed. The earlier [adoption proof](solidcraft_evaluation.md) remains
separate evidence. Next: existing SolidCraft UI/target AMD/Linux qualification,
then decide whether to promote the engine. External native edits require an
explicit revalidation contract before import/acceptance.

The requested foundation is implemented on
`consolidation/utility-backend-2026-10-12`, with a real Linux CPU plate/replay proof.
Master is unchanged. The authorized next product-integration batch is also complete;
its checklist is in [next-batch.md](next-batch.md).

The October 13 review corrections are implemented and locally validated on this
same branch. The merge remains unauthorized; master and releases are unchanged.

**Historical reboot pause (resumed 2026-10-14).** Prior implementation/evidence commits
are `b6584a7` / `e0fd511`. Read [the clean pause handoff](pause-2026-10-13.md)
for preserved resources, cleanup status and post-reboot commands. Its bracket-first
continuation was superseded by the SolidCraft evaluation above.

## SolidCraft bridge follow-up — 2026-10-14

Implementation `5905183` adds `cad_backends/solidcraft/` (two fixed native command
plans, bounded stdio worker and shared cold independent reader),
`mcp_server/solidcraft_runtime.py`, explicit environment selection in the existing
Utility dispatcher, a real five-tool proof runner and regression guards.
The adoption experiment imports the same installed plans/reader through retained
compatibility entry points; production code never imports evaluation modules.
No solver, native document implementation, viewer, kernel or generic CAD IR was
created. No mandatory dependency or upstream source was added.

`90ff09c` separately fixes a demonstrated test-only race in the old cadgen
cancellation assertion: a killed child can disappear while `/proc` is being read.
Fusion add-in/transport/freeform/session and cadgen execution files are unchanged.
The package wheel built offline and its isolated installed imports/worker files
passed. The known Pydantic warning and packaging license-format deprecation remain.

The actual MCP proof on `5905183` passed in **13.89 s**: 20 tool calls, plate
80→100 mm and L-profile 50→70 mm native edits, cold reopen/read-back and nine
negative checks. All eight captured source hashes and 28 accepted artifact hashes
were checked afterward. Edited native/STEP/STL copies are retained under
`evidence/solidcraft-guided-v0.11.1-artifacts/`. A separate controlled native
zero-width fault demonstrated actual checkpoint restore, cold independent
revalidation, no accepted failed revision and unchanged prior artifact hashes.
This bypasses input validation only inside the developer fault experiment;
normal invalid dimensions are rejected before native execution.

The 601-step native cancellation regression uses the product's process boundary;
synthetic tests separately exercise the precommit/late-cancel race, timeline,
parameter/sketch errors, verification refusal, health cleanup and all seven saved
artifact hashes. Native protocol cancellation itself is still unsupported upstream.
Scratch output is not acceptance, and cancellation polling is not instantaneous.

Final full suite: **905 passed / 5 expected failures / 0 skipped**, 141.35 s,
with both preserved cadgen and SolidCraft real CAD gates enabled. The unchanged
fixture runner passed **17/17** (8 contract, 9 safety; no live/model evidence).
The new bridge tests include 37 contract/process guards and two real native
geometry/cancellation gates. [Committed MCP and recovery evidence](evidence/solidcraft-guided-linux-2026-10-14.json).
Logs: `/tmp/paramaitric-solidcraft-{full-verified,fixtures,guided-committed,recovery,wheel,wheel-smoke}.log`.
The first restricted test attempts stalled and their two identified pytest
processes were stopped. Supported-permission runs completed. Two subsequent full
runs exposed the new/legacy `/proc` test race; both were corrected before this
passing run. These are test corrections, not geometry or Fusion regression fixes.
GitHub was unreachable during this batch; remote status/CI must not be inferred
from local test success. The earlier three adoption commits were also still local
at the start of this task. No master merge or release is authorized.

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

### Qualification preparation — 2026-10-13

Commit `b6584a7` adds `evaluations.utility_qualification`, per-request wall times
to the guided driver and a live-mode health gate before the Fusion reference
runner mutates a design. It reuses the published viewer and existing geometry
proof; no product/backend/Fusion execution behavior changed. See the
[target qualification checklist](qualification.md).

Executed focused qualification/neutral tests: **21 passed, 1 real-gate skipped**;
fixture harness: **13 passed**. The separate committed-code collector executed
real MCP geometry successfully in **14.74 s**, with initial and edited build calls
taking **6.01 s** each and saved-export inspection **1.20 s**. These are wall times,
not GPU performance or isolated CPU profiles. New snapshots were rendered and
visually reviewed, and both generated models opened in the viewer. Source and all
12 retained artifact hashes were verified. Record:
[desktop collection](evidence/plate-qualification-amd-desktop-2026-10-13.json).

Interactive Chrome review of both earlier retained plate revisions observed orbit,
80→100 mm external edge feedback and 10 mm bore tooltips. The
[UI observations](evidence/viewer-amd-desktop-2026-10-13/observations.json) bind
specific STEP hashes to three screenshots. Generic point picking also produced
approximate/coincident measurements; these were excluded from acceptance.

Actual host: **Ryzen 7 9800X3D**, Linux, three installed AMD graphics devices using
`amdgpu`. Active browser renderer/API/version remains unverified; browser policy
blocked its internal diagnostics page and no workaround was attempted. No Strix
Halo machine was available, and the local Fusion health probe refused connection.
The collector correctly leaves **qualification incomplete** and Fusion modeling
and parity **not_run**. Desktop evidence cannot pass either target gate. Logs:
`/tmp/paramaitric-qualification-{tests,fixtures,run}.log`.

Next: run the same collector and complete the manual checklist on actual Strix
Halo; capture a fresh live Fusion reference in a disposable validation design.
The newer remote plan through `0da0b0e` makes these independent, nonblocking tracks:
after the user's reboot pause, qualify the bounded flat L-profile bracket described
in [the active batch](next-batch.md) without waiting for target/Fusion availability.

### Preserved product decisions

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

The [active batch](next-batch.md) now moves from the implemented opt-in SolidCraft
bridge to existing UI/target qualification. Keep error normalization, immutable
artifacts, atomic acceptance and independent read-back as mandatory gates. Strix
Halo and live Fusion remain independent, unrun evidence tracks. Do not expand
cadgen part families while the primary-engine decision is open.

The one-shot `paramaitric-return-20261013.timer` fired the requested follow-up at
**2026-10-13 03:25:49 America/Los_Angeles** and is now inactive. No future automatic
project return is scheduled. The user resumed on 2026-10-14 under the SolidCraft
scope above; timer metadata remains in the ignored resource cache.
