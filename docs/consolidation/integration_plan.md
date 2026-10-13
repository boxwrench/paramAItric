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

## Execute actual geometry and replay

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

Route the **existing guided `cad_build` centered plate workflow** to this backend
behind explicit operator configuration. Keep Fusion as default. Add a bounded
parameter-edit request retaining the revision record, and include validation
failures and review/export paths in the existing response envelope. Do not add an
overlapping cadgen agent tool or let a model select a backend.

Acceptance: same public guided tool/schema tests still pass; selected open backend
builds/replays this fixture with saved geometry checks; unsupported workflows fail
before mutation; existing freeform/Fusion paths stay gated. Cancellation must kill
the open worker without changing Fusion cancellation semantics. Then qualify the
viewer and smoke on Strix Halo. Do not expand to the other four families until this
one reaches the product surface and its errors are understandable.

After that gate, add a spacer, basic L-bracket, bushing/adapter and pipe clamp in
increasing geometric difficulty, one independently verified family at a time.
