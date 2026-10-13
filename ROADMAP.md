# ParamAItric Roadmap

> Updated 2026-10-12: product consolidation and narrow open-source CAD foundation.
> This is the authoritative roadmap. The prior roadmap is preserved verbatim in
> [the planning archive](docs/archive/planning/ROADMAP_pre_consolidation_2026-07-20.md).
> Historical research, the Lemonade specification and the Target B plan remain intact.

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
| cadgen viewer | Published viewer launched; snapshots of both revisions reviewed | Interactive orbit/measurement on Strix Halo AMD graphics still unqualified |
| Downloaded runtime resources | 59 pinned wheels + 16 immutable upstream reference documents; checksums; offline install/kernel smoke | Wheels are Linux x86_64/Python 3.13; browser/interpreter provisioning separate |

Detailed evidence, dependencies and limitations live in
[the capability matrix](docs/consolidation/capability_matrix.md) and
[the handoff](docs/consolidation/handoff.md). Mock cases do not prove geometry;
viewing does not prove geometric accuracy; deterministic tests do not evaluate models.

## Current build milestone

The centered-hole plate is implemented on the existing guided surface, with explicit
open-backend configuration, retained edits, exported STEP inspection and cancellation
guards. Actual MCP stdio geometry passed; default Fusion regressions remain protected.

The current qualification milestone is **Strix Halo AMD/Linux viewer/graphics** and
fresh Fusion saved-geometry parity evidence. These live/hardware gates remain unrun.

The bounded next task and reproduction commands are in
[the integration runbook](docs/consolidation/integration_plan.md). Do not add another
CAD-agent interface. Do not claim other part families work on the open backend.

Gate:

1. Existing public schemas, guided tools and all 17 saved contract/safety cases remain usable.
2. The configured open backend executes the existing plate request against actual
   geometry, then edits width without hard-coding the bore coordinates.
3. Failed required verification prevents further mutation/export. Unsupported workflows
   fail before mutation. Missing measurement evidence is reported explicitly.
4. Source recipe, parameters, STEP, STL and verification/provenance records remain reviewable.
5. Cancel/timeout stops the open worker; Fusion threading/auth/mutation semantics stay intact.
6. Repeat CPU geometry and interactive viewer qualification on the target Strix Halo system.

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

1. **Consolidation foundation** — narrow backend interface, verified operation path,
   isolated fixed recipe, explicit editability/artifacts, pinned resources and tests.
   Implemented in this development branch; see consolidation docs for run evidence.
2. **Product plate slice** — implemented and exercised through actual guided MCP
   stdio, with explicit configuration, persisted edit/replay, exported STEP inspection
   and negative/cancellation tests. See the handoff for exact evidence.
3. **AMD/Linux qualification** — Strix Halo CPU timing, browser/driver orbit and
   selection/measurement smoke; record OS, graphics API/driver and package versions.
4. **Small Utility families** — spacer, basic L-bracket, bushing/adapter, pipe clamp,
   in increasing geometric difficulty. Each needs a recipe, placement/fit constraints,
   negative tests, saved-geometry checks, replay and exports before promotion.
5. **Packaging/simplification** — simplify installation and guided requirements only
   after the product slice passes. One-click hosts remain a later distribution goal.
6. **Optional native documents** — resume FreeCAD process-model validation when native
   sketch/feature-history editability offers a demonstrated benefit. It does not gate
   the current open-CAD proof.

G1–G6 geometry foundations and regression tooling remain landed: operation vocabulary,
geometry comparator, baseline tooling, safety fixtures, request metrics and attribute
pinning. Preserve their policies and existing live scope; do not infer every workflow
is validated merely because its helper or schema exists.

## Future research and explicit exclusions

[Target B validation](plans/B_VALIDATION_PLAN.md) and the FreeCAD bridge process plan
are retained research. Proposed bridge: separate FreeCAD-owned Python process, never
imported into the MCP venv; prove individual boundaries before composition. Prior
Target B labels such as “underway” are planning history, not new test results.

USD BRep/SMLib remains research: isolated future CPU kernel evaluation only, no
production dependency. Use the same utility fixture for exact/approximate measurement,
healing, tessellation and malformed-input qualification. No HIP/ROCm work without a
profiled GPU-relevant bottleneck.

Out of scope: universal IR, custom kernel/renderer, upstream forks/vendoring, full
FreeCAD integration, automatic multi-backend selection, cloud services, mandatory
remote inference, plugin marketplace and broad manufacturing automation.

Geometry verification is not structural certification, material suitability or proof
of safe use. ParamAItric should ask for missing fit-critical measurements.

## Canon and history

- [Consolidation architecture](docs/consolidation/architecture.md)
- [Capability/dependency evidence](docs/consolidation/capability_matrix.md)
- [Reproduction and next task](docs/consolidation/integration_plan.md)
- [Architectural decisions](docs/consolidation/decisions.md)
- [Branch/test baseline](docs/consolidation/baseline.md)
- [Verification policy](docs/VERIFICATION_POLICY.md)
- [Stable reference policy](docs/STABLE_REFERENCE_POLICY.md)
- [CAD playbook](docs/AI_CAD_PLAYBOOK.md)
- [Research index](internal/research/README.md)
- [Prior roadmap](docs/archive/planning/ROADMAP_pre_consolidation_2026-07-20.md)
- [Dev log](docs/dev-log.md)
