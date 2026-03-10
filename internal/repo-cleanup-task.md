# ParamAItric Repository Cleanup & Refactor

**When to run:** After all test recipes in `docs/test-recipes.md` are implemented and their tests pass.

---

## Step 1 — Root Directory Cleanup

Delete all `tmp_*` directories from the repo root — they are local test artifacts and should never be committed:

```
tmp_codex_check, tmp_test_runtime, tmp_pytest, tmp_pytest_bracket_v1,
tmp_pytest_dispatch, tmp_pytest_hardening_a, tmp_pytest_live_fix,
tmp_pytest_nonxy_repair, tmp_pytest_nonxy_repair_one, tmp_pytest_profile_fix,
tmp_pytest_smoke_strict, tmp_pytest_workflow_restart, tmpf1fniv0j, tmpsq8tzm0q
```

Add to `.gitignore`:
```
tmp_*/
tmp*/
manual_test_output/
```

Consolidate logo assets — keep only `readmelogo.png` and `small logo.png`. Remove `Gemini_Generated_Image_*.png` and `readme logoplain.png` (duplicates).

---

## Step 2 — Move Root Docs into `docs/`

Move these files from root → `docs/`:
- `ARCHITECTURE.md`
- `DEVELOPMENT_PLAN.md`
- `HOST_INTEGRATION.md`
- `WORKFLOW_STRATEGY.md`
- `PROJECT_CONTEXT.md`

Keep at root (convention): `README.md`, `BEST_PRACTICES.md`, `INSTALL.md`, `pyproject.toml`

Update any cross-document links after moving.

---

## Step 3 — Split `mcp_server/server.py`

The file is 6700+ lines. Split workflow methods into a `workflows/` subpackage:

```
mcp_server/
├── server.py              # Core only: __init__, health, freeform session, find_face
├── workflows/
│   __init__.py            # exports all workflow methods
│   primitives.py          # spacer, cylinder, tube, revolve, tapered_knob, revolve variants
│   mechanical.py          # bracket, bushing, clamp, t_handle, pipe_clamp, mounting_plate
│   enclosures.py          # snap_fit_enclosure, telescoping_containers
│   patterns.py            # slotted_flex_panel, ratchet_wheel, wire_clamp (new recipes)
├── schemas.py             # unchanged
├── freeform.py            # unchanged
├── tool_specs.py          # unchanged
└── geometry_utils.py      # unchanged
```

`ParamAIToolServer` delegates to the workflow module methods — the public API stays identical so all tests pass without changes.

---

## Step 4 — Verify Nothing Broke

```
python -m pytest tests/ -q --no-header
```

Confirm same pass count as before refactor. Any regression = a broken import path in the split.

---

## Stop Condition

Report back with: final test count, list of moved files, and confirmation that `python -m pytest tests/ -q` is green.
