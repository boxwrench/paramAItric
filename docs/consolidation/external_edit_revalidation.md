# SolidCraft native external-edit revalidation

Implemented on the experimental opt-in SolidCraft path. This extends the existing
`cad_build` tool, keeps the five-tool surface, and preserves Fusion as default.
The initial scope is the centered-hole plate and flat XY L-profile with equal-width
legs. Accepted native documents remain immutable; editing one still invalidates
its hash. This workflow gives users a separate copy instead of weakening that rule.

## Describe → create → edit a copy → explicitly revalidate

1. Create the part normally and keep its returned `revision_id`.
2. Ask ParamAItric for a native editing copy:

```json
{
  "workflow": "plate_with_hole",
  "revision_id": "solidcraft-RETURNED_PARENT",
  "external_edit": {"action": "prepare"}
}
```

The response is **not an accepted revision**. It returns an `edit_id` and a
`document_path` inside a new `edit-*` folder under the configured output root.
Open that copy in the existing SolidCraft desktop application. Change named user
parameters (`width`, `height`, `thickness`, and `hole_diameter` or `leg`), then save
it at the returned path. Never edit `artifacts.native` in an accepted revision.

3. Deliberately submit the copy and declare the intended changes:

```json
{
  "workflow": "plate_with_hole",
  "revision_id": "solidcraft-RETURNED_PARENT",
  "parameters": {"width_cm": 100, "units": "mm"},
  "external_edit": {"action": "revalidate", "edit_id": "edit-RETURNED_COPY"}
}
```

The `_cm` names retain the existing product API; `units` controls conversion.
Unspecified dimensions must retain their accepted parent values. For the L-profile,
use `workflow: bracket` and initially change width 50→70 mm. The plate proof uses
80→100 mm, with the centered 10 mm hole moving from (40,30) to (50,30) mm.

4. Only after every required check passes does ParamAItric return a **new**
immutable revision. It has a new `revision_id`, `parent_revision_id`, verified
native/STEP/STL paths and source/provenance hashes. `cad_inspect/get_revision`
hash-checks the whole evidence set and independently rereads the exported geometry.
The parent and editable copy are preserved. Revalidation can be repeated deliberately;
it never silently updates an accepted revision.

The product accepts returned IDs, not arbitrary source/destination paths. A browser
editor may download a new native file; the user must save/copy it back to the
prepared `document_path` before submission. There is no automatic Downloads scan
or adoption of unrelated local CAD files.

## Supported native changes

Only named user dimension literals may change. Native mm, cm or inch literal
expressions are allowed while the document and parameter units remain mm. Parameter
relationships, sketch constraints, feature definitions, dependency references,
feature order and identities must match the accepted recipe after allowed changes.
The hole's `width/2` and `height/2` relationships must survive.

Do not replace driven sketch expressions with constants. Extra parameters,
constraint changes, feature renames/additions/deletions, imported static solids,
fillets, folded angles, suppressed features, unit-system changes and missing or
underconstrained history are outside this first contract. A visually identical
solid with a different history is rejected. These restrictions can expand only
with a concrete qualified recipe/editor contract.

Dimensions remain finite, positive and at most 10,000 mm; the bore or leg must
fit strictly inside the envelope. The size limit is an execution guard, not a
manufacturing or structural suitability claim.

## What the implementation verifies

- `_record` validates the accepted parent and its saved hashes before preparation,
  before submission and again before acceptance. An altered parent is refused;
  the application does not repair or rewrite it.
- A preparation manifest binds the copy ID to the parent native hash and family.
  Only its fixed `part.solidcraft` file is read. No-follow directory/file descriptors,
  ordinary-file checks, hard-link refusal, stable metadata and an 8 MiB bound reject
  unsafe/changing inputs before native execution. Manifest reads are bounded too.
- The candidate is snapshotted to a new revision directory. The submitted bytes
  remain an independently hashed artifact. Workspaces and accepted files are
  never granted to native workers for writing.
- The existing native parameter-edit path regenerates an allowed-change reference
  from a copy of the parent. This reuses SolidCraft's solver/history and the existing
  verified execution path; it adds no CAD IR or parameter implementation.
- Both reference and candidate are inspected through supported public native JSON
  export. All authored fields are compared, including complete feature definitions
  and sketch constraints/geometry. Only document display name and approved literal
  expression spelling are normalized; numerical serialization tolerance is 1e-7.
  Evaluated parameter values must separately match the declared dimensions.
- Recipe sketches must be solved, fully constrained and have zero degrees of freedom.
  Native payload/timeline/parameter/sketch errors block progression even if `isError`
  is false. A matching bounding box alone never qualifies a document.
- The actual candidate is exported, independently checked, saved as native, closed,
  cold-reopened in another process, checked against the history again, exported and
  independently checked again. The reference cannot substitute for candidate proof.
- The input copy is reread before commit; drift rejects the result. Parent integrity,
  submitted snapshot integrity and all required geometry checks must still pass.
- The existing request lock, cancellation event, process limits and atomic acceptance
  publisher are reused. A failed/cancelled/interrupted job keeps diagnostics without
  an accepted `verification.json`. Every worker is killed/reaped before publication.

The whole revalidation shares a 120 s deadline including reference regeneration;
existing per-process CPU/memory/file bounds remain. Process isolation is not an OS
sandbox. No arbitrary generated code is executed and no general file importer is
exposed. The independent OCCT and STL checks retain the
[existing tolerances and limitations](solidcraft_integration.md#acceptance-and-failure-boundary).

Revalidated revisions hash eleven files: the existing seven plus submitted native
bytes, candidate/reference native definitions and external provenance. Provenance
records the parent revision/native hash, source-copy path/ID, submitted hash,
expected dimensions and native-history policy result. Old seven-file accepted
revisions remain usable. A later supported edit can use a revalidated revision as
its parent without discarding the earlier evidence chain.

## Reproducible evidence

[Committed real proof](evidence/solidcraft-external-linux-2026-10-14.json), source
`574f153`: **30.47 s**, two real native edit/revalidation round trips through the
existing five MCP tools. The edited native documents, submitted originals,
STEP/STL, native definitions and provenance are included in
`evidence/solidcraft-external-v0.11.1-artifacts/`. All **36 accepted artifact hashes**
and captured source hashes were verified afterward.

Twelve failure cases passed: invalid native dimensions; undeclared dimensions;
unsupported feature definition; broken parameter relationship; corrupted native;
missing history; unrelated static STEP import; invalid declared dimensions; altered
accepted parent; outside-directory write attempt; protocol cancellation after the
independent reader started; and forced termination of a real candidate reader.
The parent-corruption test deliberately injects corruption and restores its own
fixture afterward; the application only detects/refuses it. It does not repair an
accepted artifact. Other cases preserve prior bytes without restoration.

Final full suite: **953 passed / 5 expected failures / no skips**, 158.12 s, both
CAD environments enabled. New tests: **46 synthetic contract/policy guards and two
real native round trips**. Original fixture runner: **17/17 passed**. Offline wheel
build and isolated installed imports passed. Existing Pydantic/license-format
warnings remain.

```bash
# Set the same pinned CLI/CAD Python as the bridge runbook.
.venv/bin/python -m evaluations.solidcraft_external \
  --solidcraft-cli "$PARAMAITRIC_SOLIDCRAFT_CLI" \
  --cad-python "$PARAMAITRIC_CAD_PYTHON" \
  --output-root "$PWD/manual_test_output/solidcraft-external-proof"
.venv/bin/python -m pytest -q
```

The proof uses native MCP as an **external-editor surrogate**. It proves real CAD
editing, save/reopen and product revalidation; it is not a human or interactive
UI editing result. Synthetic tests and screenshots are separate evidence.

## Cancellation integration detail

The pinned MCP Python client does not send `notifications/cancelled` merely because
its local Python awaiter is cancelled. The real proof captures the JSON-RPC request
ID and explicitly sends that protocol notification. ParamAItric then stops the
worker and refuses acceptance. Hosts must propagate cancellation to the server;
locally forgetting a response is not a cancellation request. The original native
SolidCraft cancellation limitation remains contained behind ParamAItric's worker.

## UI, hardware and model gates

The [UI observations](evidence/solidcraft-external-ui-2026-10-14/observations.json)
record checksum-verified official web startup and its v0.11.1 screen. The bundle's
own build string (`0.11.1-9397f2ff4787ad87`) is retained separately from the native
release source ref; no identical compiled-source claim is inferred. The automated
file chooser did not become controllable. Desktop automation is unavailable in
this session. No part was opened or edited through that UI, and renderer/API/driver
remain unverified. A startup screenshot does not pass the editing gate.

Actual modeling host: Ryzen 7 9800X3D/Linux CPU; installed AMD device/driver facts
are recorded separately from active renderer evidence. Strix Halo/Radeon 8060S,
human native editing, graphics qualification and fresh live Fusion are **not_run**.
Both configured local-model endpoints refused connection; model-in-loop is
**not_run**. No model or inference stack was downloaded.

**Default decision: not qualified yet.** SolidCraft is the leading candidate and
native external revalidation is demonstrated, but the requested human/desktop UI
loop and target graphics gate remain incomplete. Fusion stays the default and
cadgen recipe expansion stays frozen.

Next: open the two prepared copies in the existing native app, observe visibility,
orbit, selection and dimensions, edit/save/reopen them, then submit through this
contract. Capture screenshots/renderer and bind them to the exact submitted hashes.
Do not create a new viewer or substitute headless edits for that evidence.
