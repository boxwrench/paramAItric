# ParamAItric Roadmap

> Updated 2026-10-14: the opt-in SolidCraft plate/L bridge is implemented;
> explicit native external-edit revalidation is implemented; the human/desktop UI
> and target qualification still precede a primary-engine decision.
> NVIDIA USD BRep/SMLib remains a separate gated research track.
> This is the authoritative roadmap. The prior roadmap is preserved verbatim in
> [the planning archive](docs/archive/planning/ROADMAP_pre_consolidation_2026-07-20.md).
> Historical research, the Lemonade specification and the Target B plan remain intact.

**Resumed 2026-10-14: SolidCraft evaluation takes priority.** Pause further custom
cadgen recipes and the bracket implementation below. Preserve the demonstrated
OCCT/Fusion paths as references. First evaluate whether SolidCraft can own native
parametric documents, modeling, editing, viewer and exports, leaving ParamAItric
focused on requirements and independent verification. No production pivot is
accepted without measured plate/bracket, native reopen/edit and failure evidence.
The [pause handoff](docs/consolidation/pause-2026-10-13.md) remains historical.

## Product direction

**ParamAItric Utility** turns measured utility/maintenance requirements into editable,
verified geometry: describe → specify → generate → verify → review → revise → export.
Consolidate mature open-source components, specialize in small mechanical parts,
validate independently, then simplify the product surface. Build neither a CAD
application nor a kernel. CPU geometry on AMD/Linux is a first-class configuration;
local inference and CAD execution remain independent choices.

ParamAItric owns requirements, validated recipes, operation sequencing, semantic
selection, verification, recovery and provenance. The backend owns execution.
One curated product tool surface remains; backend selection belongs to explicit
operator configuration, not the language model.

## What is demonstrated

| Path | Evidence | Limit |
|---|---|---|
| Existing Claude/Fusion I1 | Historical live workflow evidence and four saved Claude baselines; existing mock regression/safety suite retained | No fresh live Fusion session in this Linux assignment |
| Guided MCP/profiles/safety | Implemented schemas, units, profile activation, auth, deadlines, structured errors, semantic selectors and attribute pinning | Started Fusion cancellation is still best effort |
| Backend-neutral Utility plate | start/apply/read-back/export boundary; Fusion adapter uses existing gated primitives; contract tests | Neutral Fusion adapter freshly tested against mock, not live Fusion |
| cadgen/build123d plate | Real Linux CPU 80×60×5 mm plate, 10 mm centered bore; width edit to 100 mm; saved STEP read-back; STEP/STL and recipe retained | Tested actual guided MCP stdio; explicit selection, retained edits and exported STEP inspection; no model-in-loop evidence |
| cadgen viewer | 9800X3D AMD desktop: both models loaded and orbited, edge tooltips showed 80→100 mm width and 10 mm bore | Active browser renderer/API and Strix Halo interactive qualification remain unverified |
| SolidCraft opt-in bridge | Real guided MCP plate/L native build, reopen, width edit, independent STEP/STL checks, native checkpoint recovery and cancellation/integrity gates; full suite 905 passed / 5 expected failures | Experimental two-family scope; UI, Strix Halo and primary-engine promotion unqualified |
| SolidCraft external revalidation | Prepared native copies; declared dimension edits; full native-history comparison; new immutable revisions; actual OCCT read-back and twelve negative cases | Headless editor surrogate demonstrated; human/native desktop UI remains unrun |
| Downloaded runtime resources | 59 pinned wheels + 16 immutable upstream reference documents; checksums; offline install/kernel smoke | Wheels are Linux x86_64/Python 3.13; browser/interpreter provisioning separate |

Detailed evidence, dependencies and limitations live in
[the capability matrix](docs/consolidation/capability_matrix.md) and
[the handoff](docs/consolidation/handoff.md). Mock cases do not prove geometry;
viewing does not prove geometric accuracy; deterministic tests do not evaluate models.

## Current build milestone — SolidCraft consolidation gate

The frozen OCCT plate remains the working reference. The bounded SolidCraft
v0.11.1 experiment has independently verified plate and flat L-profile creation,
native reopen/edit, repeated regeneration, a specific fillet and STEP/STL outputs.
The [experimental opt-in bridge](docs/consolidation/solidcraft_integration.md) now
exposes both families through ParamAItric's existing five guided tools. It keeps
upstream MCP private, verifies every modeling stage and a cold native reopen,
hashes accepted native/exports and reuses atomic cancellation/acceptance.
Fusion remains the default; this is not target/UI or primary-engine qualification.

**Decision:** retain the demonstrated bridge and explicit native-edit revalidation;
qualify the existing human/desktop UI loop before primary adoption. Freeze new
custom cadgen recipes. Do not rebuild a solver, feature timeline, native CAD
document system, viewer or exporter that the candidate already provides. The
[evaluation and remaining gates](docs/consolidation/solidcraft_evaluation.md) explain
why SolidCraft is promising and why it is not the production default yet.

Integration acceptance is implemented; required before primary-engine promotion:

1. Preserve default Fusion behavior, original 17 fixtures and the accepted OCCT
   plate/reference. See the integration handoff for the latest executed suite.
2. Route only the evaluated plate and L-profile through the same curated tools;
   keep upstream's general MCP surface behind ParamAItric's boundary.
3. Enforce input validation, timeline/parameter errors even with `isError: false`,
   independent geometry, immutable native/export artifacts and atomic acceptance.
4. Kill a disposable process group on cancellation: the experiment showed a native
   MCP cancellation notification did not stop the batch from saving afterward.
   Verify checkpoint recovery and original native-file preservation.
5. **Next:** qualify the existing SolidCraft desktop UI/human editing loop and target
   hardware separately. Official web startup is observed, but native desktop control
   is unavailable and the automated web file chooser is blocked. Neither startup
   nor headless native edits qualify human interaction. Local-model endpoints also
   refused connection; the optional model gate remains not_run.

Strix Halo graphics and fresh live Fusion reference runs remain independent,
nonblocking evidence tracks. No target/browser or live parity result is inferred
from the Ryzen desktop or headless candidate proof. The actionable checklist is
[the active batch](docs/consolidation/next-batch.md); older bracket implementation
instructions there are deferred, not an authorization to expand cadgen in parallel.

## Parallel retained milestone: I2 local model → Fusion

The historical I2 milestone remains **unproven**: one successful and one safely
rejected natural-language request through Pi + Lemonade + Qwen → guided MCP →
real Fusion, with verification, STL and reproducibility metadata.

This brief authorizes the independent open-CAD proof before I2 passes; it does not
turn I2 into completed evidence. The two tracks test different boundaries.

Remaining I2 gaps:

- Pin Pi/Lemonade versions, Pi↔MCP adapter, model/provider configuration and health
  command in `docs/setup/lemonade-fusion.md` (currently TBD).
- Run the actual stack against live Fusion and record the artifacts; no mock or
  deterministic tool replay counts as a natural-language success.
- Audit started-operation cancellation before calling it safe in general.
- Capture the remaining 13 historical Claude baseline records using
  `python -m evaluations.baseline --status`; four of 17 are currently recorded.
- Broader model acceptance remains: Claude completes supported requests; local
  model completes ≥10 of the first 12 supported golden requests without manual
  tool correction, with no bypassed verification or unsafe failure.

Geometry equivalence compares bounding dimensions, body count, volume, features,
placement, verification tier and export within stated tolerance; identical files,
entity tokens or topology ordering are not required. Missing facts/baselines remain
missing. The model-in-loop evaluation is a separate evidence gate.

## Sequenced implementation

1. **Consolidation foundation — complete.** Narrow backend interface, verified
   stage runner, isolated fixed recipe, explicit editability/artifacts, pinned
   dependencies and tests.
2. **Open Utility plate — complete on AMD desktop CPU.** Actual guided MCP build,
   saved STEP read-back, 80→100 mm edit, checked STEP/STL and retained revisions.
3. **SolidCraft foundation proof — bounded headless proof complete.** Native plate
   and flat L edit/reopen, independent OCCT read-back, STL checks and specific
   fillet/recovery are demonstrated. Native cancellation is a known failed gate;
   UI and general robustness remain unqualified.
4. **Thin SolidCraft bridge and external-edit revalidation — implemented/tested.**
   Existing five tools, native history/declared-parameter gates, independent candidate
   verification, immutable parents/provenance and atomic acceptance. Full suite:
   953 passed / 5 expected failures; real two-family loop and twelve failure cases
   passed. [Contract and evidence](docs/consolidation/external_edit_revalidation.md).
5. **Strix Halo and native/interactive UI qualification — parallel.** Record the
   actual same-run artifacts, renderer/API/driver where obtainable and timings.
6. **Fresh live Fusion reference — parallel/nonblocking.** A supported host is
   required; missing facts remain incomplete.
7. **NVIDIA USD BRep/SMLib — deferred isolated research.** Preserve the plan below;
   no production dependency or diversion from the SolidCraft decision.
8. **Further Utility families and packaging.** Proceed only on the selected
   foundation after the safety and adoption gates demonstrate a useful product.
9. **FreeCAD native-document option.** Retain historical research; do not build
   another document integration while evaluating SolidCraft's native history.

G1–G6 geometry foundations and regression tooling remain landed: operation vocabulary,
geometry comparator, baseline tooling, safety fixtures, request metrics and attribute
pinning. Preserve their policies and existing live scope; a helper or schema alone
does not make a workflow qualified.
## Experimental kernel track — NVIDIA USD BRep / SMLib

**Decision:** place [NVIDIA-Omniverse/usd-brep](https://github.com/NVIDIA-Omniverse/usd-brep)
on the research roadmap, **not** the shipping backend or the critical path for
the second Utility family. Its October 2026 public release offers a CPU-side
NURBS/BRep kernel and C++/Python interfaces, while documented and reported
geometry failures make qualification essential.

**Stage R0 — evidence intake (can run now, read-only):** record an exact upstream
commit/version/license and the API surface for solids, boolean cut/union, fillets,
validity, measurement, USD interchange and OCCT `.brep` exchange. Review
[KNOWN_ISSUES.md](https://github.com/NVIDIA-Omniverse/usd-brep/blob/main/KNOWN_ISSUES.md),
open bugs, destructive/consuming-operation and context/thread ownership semantics.
Compare Python/runtime requirements and distinguish CPU kernel from optional USD/
Hydra rendering. Write down what OCCT already does adequately.

**Stage R1 — isolated CPU spike (after the bracket fixture is stable):** use a
separate reproducible Python 3.12/build environment where required, never the
pinned cadgen Python 3.13 worker. Rebuild the exact accepted centered plate and
the same bracket geometry with SMLib. Capture multiple parameter variations,
validity/manifold or healing failures, hole and fillet topology, exact/approximate
volume and dimensions, and cold import/round-trip to OCCT where actually supported.
Measure CPU wall time and memory with matched conditions. Do not equate USD visual
success with valid fabricable solids or assume native STEP export.

**Stage R2 — decision:** compare to the current OCCT acceptance and negative
fixtures. Record reproducible parity, missing operations, crashes, ABI/build
burden, licensing and maintenance cost. Only propose an opt-in adapter if there
is a concrete benefit (reliability, accurate geometry, USD-native capability or
measured performance) and the same hard verification gates can be enforced.
Otherwise archive findings and retain OCCT. No kernel replacement, forced USD
pipeline, HIP/ROCm port or custom rendering work is authorized by this roadmap.

This track is **planned research**, not an implementation claim. Existing
ParamAItric evidence remains OCCT-based.

## Future research and explicit exclusions

[Target B validation](plans/B_VALIDATION_PLAN.md) and the FreeCAD bridge process plan
are retained research. Proposed bridge: separate FreeCAD-owned Python process, never
imported into the MCP venv; prove individual boundaries before composition. Prior
Target B labels such as “underway” are planning history, not new test results.

SMLib research is explicitly sequenced above: do not install it into the working
cadgen runtime or promote it without comparative geometry and failure evidence.
No HIP/ROCm work without a profiled GPU-relevant bottleneck.

Out of scope: universal IR, custom kernel/renderer, upstream forks/vendoring, full
FreeCAD integration, automatic multi-backend selection, cloud services, mandatory
remote inference, plugin marketplace and broad manufacturing automation.

Geometry verification is not structural certification, material suitability or proof
of safe use. ParamAItric should ask for missing fit-critical measurements.

## Canon and history

- [Consolidation architecture](docs/consolidation/architecture.md)
- [Capability/dependency evidence](docs/consolidation/capability_matrix.md)
- [Reproduction and next task](docs/consolidation/integration_plan.md)
- [Active implementation batch](docs/consolidation/next-batch.md)
- [Target hardware and Fusion qualification](docs/consolidation/qualification.md)
- [Architectural decisions](docs/consolidation/decisions.md)
- [Branch/test baseline](docs/consolidation/baseline.md)
- [Verification policy](docs/VERIFICATION_POLICY.md)
- [Stable reference policy](docs/STABLE_REFERENCE_POLICY.md)
- [CAD playbook](docs/AI_CAD_PLAYBOOK.md)
- [Research index](internal/research/README.md)
- [Prior roadmap](docs/archive/planning/ROADMAP_pre_consolidation_2026-07-20.md)
- [Dev log](docs/dev-log.md)
