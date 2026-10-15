# Utility hardware and Fusion qualification

This is the retained OCCT/reference qualification path. The active product track
now prioritizes [SolidCraft](solidcraft_evaluation.md); this collector does not
qualify SolidCraft's own interactive UI or imply a production-engine decision.

This gate follows the implemented plate and the October 13 correctness fixes.
The available host is AMD Ryzen 7 9800X3D/Linux with installed AMD graphics and
`amdgpu` drivers. It is not Strix Halo. Desktop viewer observations cannot qualify
Strix Halo, and installed GPU devices cannot identify the active browser renderer.

## Collect a reproducible target run

Use the isolated environments from [the integration runbook](integration_plan.md).
On the actual target machine:

```bash
.venv/bin/python -m evaluations.utility_qualification \
  --python "$PWD/.external-resources/cad-env/bin/python" \
  --output-root "$PWD/manual_test_output/qualification"
```

Optionally provide `--target-cpu` with the exact expected model string from the
intended target's hardware inventory. The collector records actual CPU/kernel,
installed graphics IDs/drivers, commit/source hashes, real MCP plate/replay proof,
per-request wall times, viewer URLs and a read-only Fusion health probe. Each run
gets a new directory. It launches the published viewer through its installed CLI;
no frontend is copied, embedded or replaced.

Exit zero means collection and viewer launch succeeded. The report deliberately
retains `qualification_status: incomplete`: headless geometry and launching a
viewer never pass the interactive or target hardware gates. Per-request times
include transport, process startup and computation; they are wall times, not GPU
benchmarks or profiled CPU time. Unavailable facts remain null/not_run.

## Perform and record the interactive checks

Open the returned initial and edited model URLs in the target browser. Record the
actual artifact hashes and browser version, target CPU, GPU/driver/rendering API
where verifiable, and evidence for:

1. Both STEP models load without a rendering error.
2. Dragging orbits each model; top, side and underside views remain usable.
3. The bore's edge tooltip reports 10 mm diameter for each revision.
4. External edge feedback reports 80→100 mm width, 60 mm height and 5 mm thickness.
5. Point measurements distinguish selected points/centers from edge properties;
   record snapping mode and selected entities. Imprecise cursor picks are not
   dimension acceptance evidence.
6. Previous and revised models can be reviewed separately and exported artifacts
   remain accessible. Parameter edits still run through ParamAItric.

Save screenshots and observation notes separately from the collector's report.
Viewer readings/screenshots are Tier 2 diagnostics; the mandatory saved-geometry
measurements remain authoritative. Do not promote manual observations into
machine-measured assertions or copy desktop results into a Strix Halo pass.

The local October 13 desktop check opened and orbited both retained review-proof
revisions and observed 80/100 mm width and 10 mm bore edge tooltips. Exact snapped
height/thickness and browser GPU/API qualification remain incomplete. The generic
two-point picker produced approximate distances when endpoints were selected by
cursor position; use exact edge feedback and kernel read-back for acceptance.
The browser security policy blocked its internal GPU diagnostics URL; no workaround
was attempted. The local Fusion health endpoint refused the connection.

## Fresh Fusion reference, separately

On a supported Fusion host with a disposable validation design, reload the current
add-in and run the documented `evaluations.utility_plate --backend fusion` command
in [the integration runbook](integration_plan.md). It starts two new active designs.
The runner now requires health `ok: true`, `backend: autodesk_fusion`, `mode: live`
before mutation; mock availability never creates live reference evidence.

Retain both exported STL files, recipes, hash records and reported geometry facts.
Compare initial and edited records using `evaluations.utility_plate.compare_measurements`.
Current Fusion facts omit independent bore/native-validity measurements, so the
comparison remains explicitly incomplete even if shared dimensions match. Fusion
native feature-history editability and stronger saved-artifact parity require
additional evidence. A reachable health endpoint alone proves neither.

## Next implementation gate

Strix Halo qualification and fresh Fusion reference capture are **independent
evidence gates**, not blockers for implementing the second open-source part
family. Keep their `not_run` / `incomplete` labels until the actual environments
are available.

Proceed now with the existing flat L-profile bracket fixture and a verified
parameter edit through the guided cadgen/build123d/OCCT path. Add dimensioned
mounting holes and a selected fillet as separately verified steps; do not imply
that the historical plain bracket fixture already contains holes or that a
flat extruded L-profile is a bent 90-degree bracket. See
[the active next batch](next-batch.md) for work orders and acceptance tests.

NVIDIA USD BRep/SMLib is explicitly on the
[research roadmap](../../ROADMAP.md#experimental-kernel-track--nvidia-usd-brep--smlib).
Document its upstream risks now and perform a strictly isolated CPU comparison
against the accepted OCCT fixtures **after** the bracket geometry stabilizes.
Do not make it a production dependency or introduce a new kernel/viewer during
the next product batch.
