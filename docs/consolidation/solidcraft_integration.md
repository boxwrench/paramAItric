# Opt-in SolidCraft Utility bridge

The existing five guided tools can now create, revise and inspect two native
SolidCraft part families. Fusion remains the default; the cadgen plate remains a
frozen modeling reference. This is an experimental integration, not a production
engine switch or interactive UI qualification. See the earlier
[foundation evaluation](solidcraft_evaluation.md) for the native-engine evidence.

## Supported product contract

- `plate_with_hole` / `create_plate_with_hole`: rectangular XY plate, centered
  circular through-hole. Width/height edits move the center by native sketch
  expressions. Initial inputs include measured center coordinates; off-center
  requests are explicitly unsupported.
- `bracket` / `create_bracket`: flat XY L-profile extruded in +Z, equal-width
  legs. This is the historical fixture, without holes, fillets or a folded angle.
- Dimensions: finite, positive, at most 10,000 mm, with hole/leg strictly inside
  both outer dimensions. This numeric bound is an execution/input limit, not
  proof that every size is manufacturable. Fit-critical dimensions remain the
  user's measured requirements.
- Inputs retain existing `_cm` names; optional `units: mm|cm|in` converts them.
  Call `cad_get_requirements` for exact initial and edit schemas. No arbitrary
  commands, Python, arbitrary native-file imports or general feature edits are exposed.
- `output_path` is optional. A bare STL filename or path within the configured
  root is a destination hint; a unique owned revision folder holds all outputs.
  Returned paths are authoritative. Nothing overwrites a previous revision.
- Revise using `cad_build` with `workflow`, returned `revision_id` and changed
  dimension parameters. Edits open a copy of the accepted native document;
  they do not reconstruct it from STEP or rerun a saved Python artifact.
- Inspect with `cad_inspect` payload
  `{"operation":"get_revision","parameters":{"revision_id":"solidcraft-…"}}`.
  Native, exports and supporting evidence are hash-checked before inspection or
  edit. Modified accepted artifacts remain invalid. Use a separately prepared copy
  for the [explicit external-edit contract](external_edit_revalidation.md).

Multiple dimension changes are verified one at a time. Each intermediate part
must satisfy the recipe; if a coordinated edit would temporarily violate it,
submit a valid order of smaller edits or build a new part. No automatic recovery
can accept failed geometry.

## Setup and reproduce

Prepare the verified official native release and pinned independent reader using
[resources](../../resources/README.md) and the existing
[offline worker runbook](integration_plan.md). The native release is v0.11.1,
Linux x86_64; its CLI SHA-256 is checked at startup and before each native process.
The OCCT reader requires Python 3.13, cadgen 0.7.14, build123d 0.11.1 and
cadquery-ocp-novtk 7.9.3.1.1. No new mandatory product dependencies are installed.

```bash
python3 scripts/prepare_solidcraft_resources.py --verify-only
export PARAMAITRIC_CAD_BACKEND=solidcraft
export PARAMAITRIC_SOLIDCRAFT_CLI="$PWD/.external-resources/solidcraft/v0.11.1/solidcraft-0.11.1-linux-x86_64/bin/solidcraft-cli"
export PARAMAITRIC_CAD_PYTHON="$PWD/.external-resources/cad-env/bin/python"
export PARAMAITRIC_CAD_OUTPUT_ROOT="$PWD/manual_test_output/solidcraft-utility"
.venv/bin/python -m mcp_server.mcp_entrypoint
```

Configure that environment in the MCP host for actual use. Never register
SolidCraft's general MCP alongside the curated product tools and ask a language
model to choose an engine. Unset `PARAMAITRIC_CAD_BACKEND` to return to Fusion.

Developer proof through real MCP stdio:

```bash
.venv/bin/python -m evaluations.solidcraft_guided \
  --solidcraft-cli "$PARAMAITRIC_SOLIDCRAFT_CLI" \
  --cad-python "$PARAMAITRIC_CAD_PYTHON" \
  --output-root "$PWD/manual_test_output/solidcraft-guided"
# All regression gates, including the frozen cadgen geometry path:
.venv/bin/python -m pytest -q
```

Only `PARAMAITRIC_SOLIDCRAFT_CLI` and `PARAMAITRIC_CAD_PYTHON` enable the real
SolidCraft pytest gates; missing configuration produces skips, not geometry
passes. The original 17 fixture runner remains `python -m evaluations.runner`.
On constrained agent hosts, the established token-file/subprocess permissions
may be needed for the complete suite; see [baseline](baseline.md).

## Acceptance and failure boundary

`SolidCraftRuntime` reuses the existing Utility transaction lock, request-local
cancellation token and atomic acceptance publisher. The two command plans and
independent reader moved from the adoption experiment into
`cad_backends/solidcraft/`; compatibility entry points keep that experiment usable.
No generic CAD IR or new PlateBackend operations were added. The high-level native
intent path does not pretend to be a new implementation of every operation.

1. Validate all inputs before launching native code or making revision folders.
2. Launch a disposable native process group with a path grant only to its scratch
   revision folder. State/cache/temp directories are scoped there. Edits receive
   a hash-checked copy of the prior native document.
3. After each solid-producing stage or parameter mutation, inspect tool payloads,
   timeline errors, parameter errors/values and sketch solver failures. `isError`
   alone is insufficient. Independently read saved STEP/STL before another mutation.
4. Save `.solidcraft`, stop the process, reopen the native document in a new
   process, inspect its history/parameters, export and independently verify again.
5. Hash the native file, STEP, STL, parameters, fixed command transcript, runtime
   provenance and read-back evidence. Stage `geometry-verification.json`.
6. Kill/reap workers before publishing. The shared cancellation/commit lock
   atomically publishes `verification.json` as the sole acceptance marker.
   Cancellation before commit leaves no accepted revision. Cancellation after
   commit returns the accepted result, as on the existing open backend.

A failed parameter edit attempts native checkpoint restore plus independent
verification. Whether recovery succeeds or fails, that worker is discarded;
no later mutation or acceptance follows. Cancellation/timeout kills the group
without waiting for native protocol cooperation. The original accepted revision
is never granted to the worker for writing. Failed scratch directories/logs are
retained for diagnosis and may be removed manually when no request is active;
health and read-only inspection temporary directories always clean up.

The transaction wall limit is 120 s; each native/reader process has CPU 45 s,
address space 4 GiB, output-file size 64 MiB and no core dump. Protocol/read-back
buffers are bounded. This is process/resource isolation, **not an OS sandbox**.
Only repository-owned plans and fixed subprocess arguments run; arbitrary
model-generated source is never executed. Cancellation is observed by polling;
scratch writes around the request boundary can occur, but remain unaccepted.

The acceptance contract certifies recipe geometry, not structural safety or
material suitability. STEP checks use 0.01 mm dimensions, analytic volume within
max(0.01 mm³, 1 ppm), one valid solid, datum, centered cylindrical through-bore or
L-corner/material/void probes. STL checks include length/count, finite values,
envelope and signed volume within 0.1%; full manifold/self-intersection analysis
remains unqualified. Native measurements and screenshots remain diagnostics.

## Executed evidence

The [committed bridge evidence](evidence/solidcraft-guided-linux-2026-10-14.json)
records source `5905183`, two native families through actual MCP stdio,
80→100 mm plate / 50→70 mm L edits, cold independent STEP/STL checks and nine
negative checks, in 13.89 s. Eight source hashes and 28 accepted artifact hashes
were verified afterward. The edited native/STEP/STL copies are included alongside
the evidence. A separate controlled zero-width native fault independently verified
checkpoint recovery and preserved prior accepted artifacts.

Final suite on the bridge plus test-only `/proc` race fix `90ff09c`:
**905 passed, 5 expected failures, no skips**, 141.35 s, both CAD environments
enabled. Original fixtures: **17/17 passed**. New tests: 37 contract/process guards
and two real geometry/cancellation gates. Offline wheel build and isolated installed
imports/worker-file smoke passed. Sixteen pinned resource downloads verified.
Existing Pydantic settings and packaging license-format warnings remain.

This is Linux CPU evidence on the Ryzen 9800X3D host. No interactive SolidCraft UI,
Strix Halo, new live Fusion or model-in-loop evidence was run. GitHub connectivity
was unavailable; local validation does not establish remote CI or publication.

## Explicit external-edit integration

The [native edit/revalidation workflow](external_edit_revalidation.md) is now
implemented as `external_edit` prepare/revalidate modes of `cad_build`. It preserves
parents, binds copies to parent hashes, compares full native definitions against
an allowed-change reference and independently verifies the submitted geometry.
Revalidated revisions add four hashed source/history/provenance artifacts to the
existing seven. Old accepted revisions remain readable. A changed accepted artifact
is still rejected; arbitrary native CAD files are not adopted as recipes.

Current evidence: **953 tests passed / 5 expected failures**, 17 original fixtures
passed, and the [real native external loop](evidence/solidcraft-external-linux-2026-10-14.json)
passed both families and twelve failure cases in 30.47 s. This is an automated
headless editor surrogate, not a demonstrated human/desktop interaction.

## Next gate

Complete the existing SolidCraft desktop review/editing workflow on actual AMD
hardware, save/reopen and submit its edited native copies using the explicit
contract. The official web bundle now downloads/verifies and renders its start
screen; model editing could not be controlled through the available file chooser.
Native desktop control is disabled in this session. UI, human editing, renderer,
Strix Halo, fresh live Fusion parity and local-model I2 remain separate unrun gates.
The primary-engine decision remains pending; Fusion stays default. No custom UI,
new kernel or cadgen family expansion is part of this batch.
