# Reproduce and continue the Utility plate integration

The user reprioritized [SolidCraft evaluation](solidcraft_evaluation.md) ahead of
new cadgen recipes on 2026-10-14. These commands preserve/reproduce the OCCT
reference; do not expand its part families while the foundation decision is open.

See [architecture](architecture.md) for ownership and [capabilities](capability_matrix.md)
for demonstrated scope. Run from the repo root. Network is needed for initial
dependency/browser acquisition; CAD construction itself is local CPU work.

## Provision the supported worker

```bash
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -e '.[dev]'
uv venv .external-resources/cad-env --python 3.13
uv pip install --python .external-resources/cad-env/bin/python \
  -r cad_backends/cadgen/requirements.lock.txt
```

The worker environment is separate from the MCP environment. Fusion installation
continues to use [INSTALL.md](../../INSTALL.md). Do not configure the existing HTTP
runtime profile as `cadgen`: no cadgen bridge endpoint exists.

The downloaded wheel cache can provision without a package index:

```bash
python3 scripts/prepare_cad_resources.py --verify-only
uv pip install --python .external-resources/cad-env/bin/python \
  --no-index --find-links .external-resources/wheels \
  -r cad_backends/cadgen/requirements.lock.txt
```

See [resource preparation](../../resources/README.md) to redownload/cache for a new
machine. An offline machine also needs its Python interpreter and, for snapshots,
the matching browser/runtime libraries; wheels alone do not supply those.

## Configure the existing guided product tools

Set these environment variables in the existing ParamAItric MCP server configuration:

```text
PARAMAITRIC_CAD_BACKEND=cadgen
PARAMAITRIC_CAD_PYTHON=<absolute path to the dedicated CAD environment's python>
PARAMAITRIC_CAD_OUTPUT_ROOT=<absolute allowed export folder>
```

The MCP command stays `python -m mcp_server.mcp_entrypoint`. No additional cadgen
agent server is needed. Selecting cadgen exposes the same five guided tools, with
requirements/discovery scoped to the centered plate. Explicit CAD environment
selection overrides the profile's CAD bridge choice; inference/profile choices
remain independent. Unset it or select `fusion` to retain the original default path.
`cad_health` probes the actual worker/kernel; missing configuration or unsupported
versions fail explicitly. Existing `doctor --profile` remains the Fusion/profile
diagnostic path; do not interpret it as a cadgen qualification.

Initial `cad_build` uses `workflow: plate_with_hole` and the existing plate parameter
schema with optional `output_path`. Omit it to use the configured root automatically;
bare filenames are interpreted there, and explicit paths must stay inside it.
Use returned artifact paths, because each build owns a new revision folder. To edit, call the
same tool with the returned `revision_id` and only changed dimension fields:

```json
{
  "payload": {
    "workflow": "plate_with_hole",
    "revision_id": "plate-example1",
    "parameters": {"width_cm": 100, "units": "mm"}
  }
}
```

The existing `_cm` field names accept the selected units, as in the Fusion schema.
Replace `plate-example1` with the exact returned ID.
Width/height changes recalculate the bore center. Edit supports width, height,
thickness and diameter; off-center/new-feature changes are rejected.
Use `cad_inspect` with `operation: get_revision` and `parameters: {revision_id: ...}`
to remeasure the final exported STEP. Accepted revision records survive restart;
reopening checks all artifact hashes before inspection or replay. External edits
or missing files fail with `verification_failed` at `revision_integrity`: build a
new revision from measured parameters rather than trusting the altered export.
Historical records without explicit `acceptance: accepted` cannot be reopened;
retain them as evidence and regenerate using the current guided workflow.
MCP cancellation signals the worker using a request-local event; acceptance is
atomically published only if cancellation has not already won the commit race.
Late cancellation returns the committed result. Concurrent build
or inspection transactions are rejected. Failed/abandoned outputs stay available
for diagnosis; no unsupported request falls back to Fusion.

The actual MCP stdio proof supplies these settings itself:

```bash
.venv/bin/python -m evaluations.utility_guided \
  --python "$PWD/.external-resources/cad-env/bin/python" \
  --output-root "$PWD/manual_test_output/utility-guided"
```

It verifies the five-tool surface, actual build, retained edit, saved exported STEP,
default destination selection, unsupported-workflow rejection and modified STEP/STL
hash rejection. The lower-level geometry tests also exercise malformed STEP parsing. No language model
participates. The smoke driver has a 120-second limit.

## Execute the internal geometry contract separately

```bash
.venv/bin/python -m evaluations.utility_plate \
  --backend cadgen --python "$PWD/.external-resources/cad-env/bin/python" \
  --output-root "$PWD/manual_test_output/utility-cadgen"

PARAMAITRIC_CAD_PYTHON="$PWD/.external-resources/cad-env/bin/python" \
  .venv/bin/python -m pytest -q
.venv/bin/python -m evaluations.runner
```

`evaluations.utility_plate` derives the first dimensions from the unchanged
`plate_centered_hole_success` fixture, builds 80×60×5 mm, edits width to 100 mm,
and regenerates with diameter 10 mm and center `width/2, height/2`. It writes
`smoke.json` with metadata, elapsed time, source/fixture hashes and separate initial
and edited evidence. Each revision keeps parameters, standalone recipe, runtime
versions, stage STEP files, final STEP/STL and verification records. Failed runs
return a structured error; they are not passing geometry evidence.

The normal suite skips the real gate when `PARAMAITRIC_CAD_PYTHON` is absent.
Mock contract tests and the 17 server fixtures never become real-geometry evidence.
The comparator reports unavailable measurements as incomplete. No model-in-loop
score is assigned to deterministic runs.

An explicit limited Fusion reference run is available on a real Fusion host:

```bash
.venv/bin/python -m evaluations.utility_plate --backend fusion \
  --endpoint http://127.0.0.1:8123 \
  --output-root "$PWD/manual_test_output/utility-fusion"
```

This starts a new active design twice; run it in a disposable validation session.
It exercises actual Fusion primitives through the neutral sequence, STL only, and
reports `limited_reference`, because current bridge inspection does not independently
measure bore geometry/native validity. Rerun the existing adopted live freeform smokes
and plate baseline on a supported Fusion machine before claiming live parity.

## Review using the existing viewer

```bash
DO_NOT_TRACK=1 .external-resources/cad-env/bin/cadgen viewer \
  --host 127.0.0.1 --json --detach
DO_NOT_TRACK=1 .external-resources/cad-env/bin/cadgen step snapshot \
  path/to/plate.step path/to/review.png
```

Read `url` from the viewer's JSON response, then open
`<url>?file=<URL-encoded absolute STEP path>`. Do not guess the port. The viewer
opens saved artifacts; it does not regenerate source. STEP supports topology
selection and measurements; STL is a visual mesh. Separate tabs can show previous
and edited models. A synchronized comparison/parameter form has not been built.
Parameter changes must pass through ParamAItric; viewer screenshots are not proof.

The published viewer and snapshots launched here. Interactive orbit/measurement
on the target Strix Halo AMD browser/driver remains to be qualified. Measure that
separately from CPU geometry latency and local inference performance.

## Exact next task

**Product:** Implement a second distinct, validated open-CAD part family now:
the existing flat L-profile bracket (`bracket_success.json`), followed by an
explicitly dimensioned mounting-hole variant and qualified fillet. Prove native
geometry, saved STEP read-back, safe parametric regeneration and export through
the existing guided MCP tools. The [active batch](next-batch.md) is the
implementation contract. Do not invent hole geometry or broaden the kernel
interface beyond necessary operations.

**Parallel target:** Run the [Strix Halo qualification](qualification.md)
collector and perform interactive checks on the actual Radeon 8060S host.
Record browser GPU/API/driver if verifiable and distinguish per-request wall
times from native kernel timing. Its status remains incomplete until that run.

**Independent reference:** When a supported live Fusion host is available,
capture the plate/bracket comparison under the live-mode preflight. Missing
measurements remain `incomplete`. Fusion access does not gate open-source
Utility development.

**Future kernel research:** NVIDIA [USD BRep/SMLib](https://github.com/NVIDIA-Omniverse/usd-brep)
is now a scheduled research evaluation after the bracket reference fixture,
not the currently executing OCCT kernel. See the
[roadmap's gated comparison](../../ROADMAP.md#experimental-kernel-track--nvidia-usd-brep--smlib).
No SMLib install, production adapter, upstream fork or HIP port is part of
this batch.

The centered plate's guided software integration remains complete and must
not regress: persisted edits, verified saved exports, cancellation, immutable
accepted revisions, and the original 17 contract/safety fixtures.
