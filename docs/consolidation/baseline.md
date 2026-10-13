# Consolidation baseline — 2026-10-12

Rollback point: `235f696aae17463d214239c0aaadcda8ab4afbc5` (`master`). Work branch:
`consolidation/utility-backend-2026-10-12`. The checkout was clean before work.
No default branch merge, history rewrite, upstream fork, or source vendoring.

## Branch reconciliation

Inspected local `master` and remote-tracking `origin/lemonade-integration` at
`2b776264177d7849d052514e8f81218233e8ad4f` (no local branch of that name).
Neither is an ancestor of the other; merge base is
`f32aca03a2f613be68d1af41c2219258b0c8aea6`. Many equivalent changes have different
commit IDs. Commit names alone therefore do not establish inclusion.

The complete tree difference is ten files: README, ROADMAP, four branding images
plus the banner, `evaluations/runner/runner.py`, `mcp_server/operations.py`, and
`plans/B_VALIDATION_PLAN.md`. Master has the newer roadmap/FreeCAD validation plan,
demo link, deduplicated operation validation and hoisted fault-bridge import.
There is no additional backend implementation to merge from the integration tree.
Use master as baseline; preserve the other ref and its planning history unchanged.
These are locally available refs, not a claim that remote refs were freshly fetched.

## Behavior and evidence to preserve

- Existing public MCP schemas, full/guided surfaces, runtime activation and errors.
- Fusion loopback bridge authentication, main-thread dispatch, cancellation/deadline
  semantics and token ownership. Started-operation cancellation remains best effort.
- Validated workflow families, selector cardinality and attribute pinning.
- Freeform: one mutation, inspect/verify, commit, next mutation; failed gates lock.
- All 17 saved regression fixtures and four historical Claude/Fusion baseline records.
  Their metadata is historical evidence, not a fresh live validation on this host.
- Tier 0 gates, Tier 1 contextual audits, Tier 2 diagnostics and provenance.
- Editable intent cannot be inferred from a STEP/STL or a Fusion entity token.

Implemented: Fusion primitives/workflows, mock HTTP adapter, guided MCP, schema
normalization, profile routing, regression comparator, safety fixtures and Pi/I2
evidence harness. Mock geometry and STL placeholders are contract evidence only.
Experimental/planned: Target B FreeCAD bridge, native Linux CAD, Strix composition,
local-model acceptance. I2 Pi/Lemonade/Qwen → live Fusion proof is still absent.
The research syntheses and Target B plan remain preserved.

## Baseline tests before refactor

Environment: Linux x86_64, AMD Ryzen 7 9800X3D, CPython 3.13.12;
temporary test venv, editable ParamAItric 0.1.0, MCP 1.26.0, pytest 9.1.1.
System Python 3.12 had no pytest; bare `python` was unavailable.

`python -m pytest -q`: **793 passed, 5 xfailed, 2 failed**, 94.32 s, one warning.
Both failures were in `test_profile_activation.py`: tests attempted the profile's
fixed `127.0.0.1:8123` endpoint without provisioning a bridge. This is a pre-existing
test isolation problem, not evidence of live Fusion failure. Fix tests to inject
the existing mock-bridge fixture after activation; keep production routing intact.

The initial restricted run had 624 passes, 30 failures and 146 setup errors because
the mock bridge could not write its home-directory auth file. The meaningful run
above used the permissions needed by existing loopback/token-file tests.
Logs: `/tmp/paramaitric-baseline-pytest-full.log` and restricted diagnostic log
`/tmp/paramaitric-baseline-pytest.log` (local, not permanent repository evidence).

No live Fusion, Pi/Lemonade, FreeCAD, SMLib or GPU viewer test ran for this baseline.
Follow-up test results belong in the consolidation handoff, not in this baseline.
