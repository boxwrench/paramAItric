# Housekeeping checklist (2026-07-12)

A reviewed cleanup pass. Each item lists what it is, why, and its reference status
(checked against `tests/`, `mcp_server/`, `fusion_addin/`, `pyproject.toml`, and
`scripts/`). Nothing here is removed until the section is approved. Research notes,
architecture docs, and the `docs/archive/` tree are intentionally **kept** — they are
decision history (per `plans/ponytail-audit-2026-07-12.md`, Research Disposition).

Status legend: `[ ]` proposed · `[x]` done · **APPROVED** = greenlit to execute.

---

## A. Dead one-off scripts in `scripts/` — proposed remove (0 live refs)

Migration is finished and archived under `docs/archive/migration/`; these are the
throwaway tooling from that era plus iterative plate builders. None are imported by
live code — only mentioned in docs (`dev-log.md`, archived handoffs, `scripts/README.md`,
`docs/AI_CONTEXT.md`).

- [ ] `scripts/build_plates_final.py` (0 refs anywhere)
- [ ] `scripts/fix_plates.py`
- [ ] `scripts/rebuild_plates.py`
- [ ] `scripts/rebuild_plates2.py`
- [ ] `scripts/insert_into_plates.py`
- [ ] `scripts/extract_workflow.py`
- [ ] `scripts/extract_workflow_fixed.py`  (duplicate of the above)
- [ ] `scripts/insert_workflows.py`
- [ ] `scripts/migrate_workflows.py`
- [ ] `scripts/verify_migration.py`
- [ ] `scripts/dedupe_methods.py`
- [ ] `scripts/extract_helpers.py`
- [ ] `scripts/test_yz_cut_fix.py`
- [ ] Trim references to the above in `scripts/README.md` and `docs/AI_CONTEXT.md`.

Keepers in `scripts/`: `install_paramaitric.py`, `fusion_smoke_test.py`, `setup.ps1`,
`setup.sh`, `cad.bat`, `cad_cli.py`, `scaffold_reference_intake.py`, and the live
`validate_*` / `*_smoke.py` scripts.

## B. Dead dev runners in `internal/` — **APPROVED** (0 refs; keep research/notes)

One-off manual runners with no references. The `internal/research/**`, `README.md`,
`freeform-architecture.md`, `reference-*.md`, and `test-recipes.md` are **kept**.

- [x] Removed all 15 runners (`agent_disciplined_strut`, `agent_freeform_emulator`,
      `freeform_a–e`, `live_recipe_validation`, `live_run_recipe1–5`,
      `official_macro_validation`, `visualize_r1_separated`) and trimmed the
      `internal/README.md` "Python Runners" table. Done 2026-07-12.

## C. Root-doc tombstones — proposed remove

- [ ] `DEVELOPMENT_PLAN.md` — body is "Legacy note."; superseded by `ROADMAP.md`.
- [ ] `paramaitric-handoff.md` — 0.5 KB redirect to an already-archived handoff.

## D. Doc consolidation — decision needed (no delete yet)

- [ ] `INSTALL.md` (9 KB) vs `QUICKSTART.md` (4 KB) vs `README.md` overlap. Decide the
      canonical onboarding path and cross-link the others (or merge QUICKSTART into
      README and keep INSTALL as the deep guide).

## E. `docs/` tidying — low priority

- [ ] `docs/superpowers/` (2 historical design docs) → move under `docs/archive/`
      (e.g. `docs/archive/design/`). The name is confusing at top level.
- [ ] `docs/SESSION_TRANSFER_METHOD.md` — likely superseded by the handoff/roadmap
      flow; confirm, then archive or keep.
- [ ] `docs/valve_specs/spec_extractor.py` — code living under `docs/`; consider
      moving to `scripts/` or a data module.

## F. Untracked

- [ ] `plans/cowork-session-handoff-2026-07-11.md` — superseded by
      `plans/ponytail-audit-2026-07-12.md`. Commit to history or delete.

## G. Healthy — no action

- `docs/archive/**` is well-organized (handoffs, migration, planning, examples).
- `.gitignore` covers `.venv`, `tmp*`, `__pycache__`, `.mcp.json`, `private/`, and
  local-only strategy docs.
- `i2-evidence/.gitignore` correctly ignores generated run bundles.
- `internal/research/**` is valuable decision history — keep.
