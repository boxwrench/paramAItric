# Active next batch — SolidCraft consolidation proof

**Resumed and reprioritized by the user, 2026-10-14.** SolidCraft is the first
candidate for the complete CAD engine/document/UI role, not merely another backend.
Freeze further custom cadgen recipes; preserve the working OCCT and Fusion paths.

1. Pin an official SolidCraft release, license, public CLI/MCP/document interfaces
   and reported limitations. Download resources without vendoring or forking source.
2. Reproduce the centered-hole plate and flat L-profile bracket; independently
   reopen their exported STEP geometry in the retained OCCT reader.
3. Edit parameters, save/reopen native documents, repeat regeneration and verify
   dimensional relationships and editability, not just exported snapshots.
4. Exercise invalid dimensions, failed fillets, missing references, cancellation,
   rollback and repeated regeneration. Record failures and partial/unrun evidence.
5. Decide whether SolidCraft can replace planned modeling/document/viewer work;
   recommend a primary-engine pivot only if the evidence meets the product gates.
   Preserve one curated ParamAItric surface and independent acceptance/verification.

The previously authorized family implementation below is **deferred pending this
decision**. Strix Halo, live Fusion and SMLib remain separate tracks, not reasons
to expand this bounded evaluation.

Headless evaluation outcome: plate and L native reopen/edit/regeneration and
independent STEP/STL checks passed; a specific fillet and checkpoint recovery
passed. Native MCP cancellation did not stop a batch, and invalid parameter
errors require checking payload/timeline beyond `isError`. Interactive UI remains
unrun after a network download failure. See [the evidence/decision](solidcraft_evaluation.md).

**Next bounded task:** an opt-in SolidCraft execution bridge for these two cases,
reusing existing ParamAItric validation, atomic acceptance and artifact-integrity
gates, with disposable process cancellation and independent STEP read-back.
Do not change the production default or expand cadgen recipes during that task.

Updated 2026-10-13. This is the actionable implementation batch on
`consolidation/utility-backend-2026-10-12`; `master` remains unchanged.
The completed plate/consolidation batches and their evidence are recorded in
[handoff](handoff.md), [desktop qualification](qualification.md) and
[dev log](../dev-log.md). The prior one-shot timer is historical, not part of
the work plan.

## Deferred implementation track — prior cadgen second-family plan

**Goal:** Make the existing cadgen/build123d/OCCT path generate, revise and
independently verify a useful L-profile mounting bracket using the **same five
guided MCP tools** as the accepted centered plate. Work need not wait for
Strix Halo or a supported live Fusion host.

1. **Freeze the existing plate and regression baseline.** Run ordinary CI,
   the original 17 fixtures and, where the pinned worker is installed, the
   real guided build/edit/STEP inspection including modified-artifact and
   cancellation tests. Record exact runtime/commit.
2. **Specify the *actual* second shape.** Use
   `evaluations/cases/bracket_success.json`: a **flat XY L-shaped profile
   extruded 5 mm**, overall width 50 mm, height 80 mm and leg thickness 5 mm.
   This is not a folded 90-degree angle bracket. Carry over the existing
   `create_bracket` intent/schema where it applies. Do not claim mounting
   holes exist in this historical fixture.
3. **Prove basic L geometry and regeneration.** Add one narrow product-owned
   recipe and adapter operation(s) only as necessary. Verify via a cold saved
   STEP read-back: one valid solid, envelope, expected material volume (with
   declared geometric tolerance), and the inner L corner/leg dimensions.
   Save STEP/STL/source, hashes, accepted revisions and failure evidence.
   Change one width/leg dimension; verify intended relationships regenerate.
4. **Add a distinct dimensioned mounting-hole variant.** Record an explicit
   fixture defining hole count, centers, diameters, datum, edge clearance and
   through-depth. Validate fit before native calls. Verify each bore and
   location from saved geometry, not input echoes or visual screenshots.
5. **Qualify a fillet only after the preceding checks pass.** Use
   `filleted_bracket_success.json` as prior contract context (40 × 60 ×
   6 mm profile, 1.5 mm requested radius). Specify exactly which edge(s),
   selected by stable geometry criteria, are rounded. Confirm acceptable
   fillet geometry, preserved holes and validity after regeneration. If
   selection/measurement cannot be proven, leave filleting unsupported.
6. **Wire it into guided MCP and evaluation without fallback.** Discovery,
   requirements, `cad_build`, revision edit and `cad_inspect` must expose
   only qualified operations. Run positive, malformed, out-of-bounds,
   ambiguous-selection, cancellation, integrity and export tests.
   Preserve Fusion behavior and the existing plate path unchanged.

**Product acceptance:** A second genuinely different geometry family completes
create → cold read-back → verify → edit → export through the same open backend.
No broad operation-IR expansion, new renderer, kernel replacement or model-written
Python execution. A mock test or an empty adapter does not pass.

## Parallel hardware track — Strix Halo (independent gate)

On the actual Ryzen AI MAX+ 395 / Radeon 8060S machine, execute
[evaluations.utility_qualification](qualification.md). Retain the **same run's**
source commit, revision IDs, STEP hashes, interactive observations/screenshots,
renderer/API/driver where verifiable, CPU timing and exact measurements.
Do not reuse 9800X3D viewer evidence as a Strix pass. The collector's exit 0
means evidence captured, not hardware qualification. Keep browser graphics and
kernel CPU performance distinct.

This track does not block the second family implementation.

## Optional reference track — live Fusion (independent gate)

On a supported Fusion host only, use the read-only live-mode preflight then
capture disposable plate/bracket native outputs and comparison facts.
A missing Fusion host is `not_run`, not a regression or project blocker.
Missing bore/history measurements remain `incomplete`; no inferred parity.

## NVIDIA experimental kernel track — planned, not active production

Register NVIDIA's
[USD BRep / SMLib](https://github.com/NVIDIA-Omniverse/usd-brep) in the
[authoritative roadmap](../../ROADMAP.md#experimental-kernel-track--nvidia-usd-brep--smlib).

- **Now (research-only):** collect pinned upstream release/commit,
  license, build/runtime requirements, API mapping, known issues, object
  ownership/consuming-operation semantics and interoperability limits.
  Check the published bug tracker as well as `KNOWN_ISSUES.md`.
- **After the bracket reference geometry is stable:** separate CPU-only
  Python 3.12 environment where required, compare SMLib against accepted
  OCCT plate and bracket cases, including invalid inputs, booleans, fillets,
  healing/validity, cold OCCT interchange, dimensions, volume, reproducibility
  and measured wall time/memory.
- **Decision:** recommend an **opt-in** adapter only on demonstrated value and
  acceptable correctness/maintenance costs. Otherwise document why OCCT stays.
  Do not install SMLib into the pinned cadgen environment or alter shipping
  backend configuration during this batch.

## Agent deliverables and stop conditions

Deliver small reviewable commits; tests/evidence labeled as mock, headless
geometry, viewer/manual, Strix target or live Fusion; accurate docs; and an
updated handoff. The product and hardware/reference tracks have **separate**
pass/fail states. Never mark an unrun track green.

Stop speculative scope growth at the second qualified family. In particular:
no FreeCAD/SMLib production adapter, CUDA/HIP kernel port, general CAD IR,
upstream vendoring, cloud dependency, auto-backend choice, unbounded user code
or custom viewer for this batch.
