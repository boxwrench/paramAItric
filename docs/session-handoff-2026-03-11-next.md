# Session Handoff - 2026-03-11

Use this only as a restart aid for the next coding session. Durable history belongs in `docs/dev-log.md`.

## Current repo state

- Branch: `master`
- Main push target: `origin/master`
- This sweep focused on:
  - freeform enforcement and rollback
  - structured recipe hardening follow-through
  - repo/doc housekeeping
  - cleaning the boundary between shared docs, research archive, and local-only R&D

## What landed in this sweep

### Freeform

- Stronger manifest discipline:
  - no duplicate/empty `target_features`
  - no resolving undeclared features
- Stronger commit discipline:
  - `expected_body_count` required
  - optional body-count delta and volume-delta-sign assertions
  - structured `verification_diff` returned from `commit_verification`
- Replay-based rollback:
  - `rollback_freeform_session`
  - replays committed mutations from a clean design
  - remaps tokens and rebinds profile tokens during replay

### Structured workflows

- Tool descriptions in `mcp_server/tool_specs.py` were synchronized with actual workflow behavior.
- `create_snap_fit_enclosure` was corrected to verify/report the final post-combine state correctly:
  - final `body_count` should be `2` (box + lid)

### Docs and housekeeping

- Added:
  - `docs/FREEFORM_PLAYBOOK.md`
  - `docs/FREEFORM_CHECKLIST.md`
  - `docs/CSG_CHECKLIST.md`
  - `internal/freeform-architecture.md`
- Repaired `.gitignore` and established ignored `private/` for local incubation.
- Removed stale/obsolete tracked artifacts:
  - `mcp_server/server_new_workflow.py`
  - older handoff/cleanup debris
- Clarified `internal/research/README.md` so `internal/research/` is treated as a shared archive, not current canon.

## Validation from this sweep

- Passed:
  - `pytest tests/test_freeform.py tests/test_mcp_entrypoint.py`
  - `pytest tests/test_telescoping_containers.py tests/test_slotted_flex_panel.py tests/test_ratchet_wheel.py tests/test_wire_clamp.py`
  - `pytest tests/test_snap_fit_enclosure.py`
- Effective targeted count:
  - `18 passed`
- Full suite not rerun.

## Things to keep in mind next session

- There was a lot of parallel/multiagent activity around recipe hardening and internal harness creation.
- The core committed path is cleaner now, but some `internal/` runners/harnesses should still be treated as working artifacts, not proof of full validation.
- If any of those internal scripts become operationally important, rerun them deliberately under the live Fusion bridge instead of assuming they still match the stricter freeform rules.

## Good next directions

### 1. Real-world workflow library

- Build a shopping-list-first corpus of real parts/families to parameterize.
- McMaster-Carr is a strong early source, but start with curated candidate lists and official downloads rather than raw scraping.

### 2. Meta workflow / skill capture

- The repo is demonstrating a reusable development method:
  - benchmark-first hardening
  - verification as product behavior
  - explicit recovery before wider autonomy
  - periodic clean sweeps to control drift
- That should eventually become a reusable skill or meta-workflow note for other projects.

## Local-only notes

- There is now a local ignored incubation area under `private/` for:
  - research prompts
  - R&D notes
  - possible development paths
  - spin-offs
- This is intentionally not part of the shared repo history.
