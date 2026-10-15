# Server contract regression suite

[`solidcraft_guided`](solidcraft_guided.py) executes the experimental SolidCraft
bridge through the same five MCP tools, saving native and STEP/STL evidence,
replaying width edits and rejecting tampered artifacts. It requires the pinned
CLI and separate OCCT environment. See [setup and limits](../docs/consolidation/solidcraft_integration.md).
`tests/test_solidcraft_runtime.py` keeps synthetic contract guards distinct from
two explicitly gated real native geometry/cancellation tests.

The original 17 cases remain unchanged. The separate
[`utility_plate`](utility_plate.py) runner executes the backend-neutral plate and
parameter-edit proof against explicit cadgen/build123d or limited Fusion adapters.
See [the integration runbook](../docs/consolidation/integration_plan.md).
Its real geometry gate is opt-in with `PARAMAITRIC_CAD_PYTHON`; absent runtime means
a skipped test, never a fabricated geometry pass. Model-in-loop evidence remains separate.

[`utility_guided`](utility_guided.py) additionally drives an actual MCP stdio client
through the five guided tools, exercising real open-backend build/edit/exported STEP
inspection, automatic output-folder selection and negative unsupported/modified
STEP/STL checks. Its result records
the exact source commit and hashes; it does not score model behavior.

[`utility_qualification`](utility_qualification.py) collects the real guided proof,
host CPU/kernel/installed GPU facts, per-request wall times, existing viewer URLs
and a read-only Fusion health probe. It deliberately leaves interactive/target
qualification incomplete; see [the qualification checklist](../docs/consolidation/qualification.md).

A small, versioned regression harness that replays representative requests
against the paramAItric MCP tool server and checks the results. This is the
Stage 0 harness from `ROADMAP.md`.

**What this tests, and what it doesn't:** this suite exercises *server*
behavior given a known tool name and a known set of arguments — schema
validity, argument normalization, tool routing, geometry facts, and
structured-error shape. It does not send anything through a model. A real
agent/model evaluation (e.g. does Qwen3.5 9B pick the right tool from a
natural-language request?) is a separate, not-yet-built capability — see
"Current milestone" in `ROADMAP.md` and Stage 3.

## Tiers

Each case declares a `tier`:

- **contract** – Runs against the MOCK bridge (no Fusion needed). Verifies that
  a well-formed request maps to the right tool, normalizes correctly, produces
  the expected geometry facts, and exports an STL.
- **safety** – Runs against the MOCK bridge. Verifies that an unsafe or
  impossible request *fails safely*: a structured error with the right
  classification, not a crash or bad geometry.
- **live_fusion** – Requires a running Fusion session. Defined but **skipped**
  on hosts without Fusion (no live cases ship yet).

Each case also declares a `disposition` (the succeed-or-fail-safely flag):
`succeed` or `fail_safely`.

## Cases

Cases live as JSON files in `cases/` and are loaded by
`evaluations.cases.load_cases`. Each records the original natural-language
request, the workflow/tool it should map to, the measurements a host must
extract, the arguments the runner passes, the contract for how a correct host
should normalize the request, the geometry facts to verify, and (for safety
cases) the target structured-error shape.

The literal `{tmp}` placeholder in an `output_path` is substituted with the
system temp directory at run time.

## Normalization gaps

Safety cases record the Stage 1 target error shape (fields like `recoverable`).
Fields defined in the target but not yet emitted by the server are recorded per
case as `normalization_gaps`. Gaps are **reported, not failed** – they track
work that has not landed yet without breaking the harness.

## Reproducibility metadata

Every result carries `ReproducibilityMetadata`: repo commit, model,
quantization, tool profile, inference backend, hardware, driver, context size,
temperature, and the case id. For mock runs these default to `mock`/`full` and
can be overridden via `PARAMAITRIC_EVAL_*` environment variables.

## Running

```bash
# Run every case; writes results/<case_id>.json and prints a summary table.
python -m evaluations.runner
```

Exit code is `0` when no case failed (skipped cases do not fail the run) and `1`
otherwise. Results are written to `results/`; manually captured Claude baselines
belong in `expected/`.

The harness is also exercised by `tests/test_evaluations.py` in the main pytest
suite.
