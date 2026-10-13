# Reproduce and continue the Utility plate integration

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
schema. The requested output path must sit in the configured root; use returned
artifact paths, because each build owns a new revision folder. To edit, call the
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
to remeasure the final exported STEP. Accepted revision records survive restart.
MCP cancellation signals the worker using a request-local event; concurrent build
or inspection transactions are rejected. Failed/abandoned outputs stay available
for diagnosis; no unsupported request falls back to Fusion.

The actual MCP stdio proof supplies these settings itself:

```bash
.venv/bin/python -m evaluations.utility_guided \
  --python "$PWD/.external-resources/cad-env/bin/python" \
  --output-root "$PWD/manual_test_output/utility-guided"
```

It verifies the five-tool surface, actual build, retained edit, saved exported STEP,
unsupported-workflow rejection and malformed-output rejection. No language model
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

Qualify this implemented guided plate path on **Strix Halo AMD/Linux graphics**:
run the same stdio/geometry proof, open both saved revisions in the existing viewer,
orbit and measure the bore/envelope, and record browser/GPU API/driver plus CPU timings.
Separately capture fresh Fusion plate/reference artifacts and compare common facts
with explicit missing-measurement status; do not invent live parity from historical
JSON or mock output. These hardware/live gates have not run in this assignment.

The software batch is complete: explicit routing, persisted edits, exported STEP
inspection, transaction/cancellation guards and default-Fusion regressions. No
overlapping CAD agent tool or automatic backend selection was added.

After that gate, add a spacer, basic L-bracket, bushing/adapter and pipe clamp in
increasing geometric difficulty, one independently verified family at a time.
