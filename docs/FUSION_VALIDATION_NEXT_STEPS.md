# Fusion 360 Validation — Next Steps (for the machine with Fusion)

This is a hands-on checklist for validating the selector and discovery work on the machine that
actually has Autodesk Fusion 360. The selector and operation-diagnostic paths are unit-tested
without Fusion; the live B-Rep adapter behavior below is the genuinely unverified part.

For a compact execution checklist, use `docs/FUSION_HARDWARE_TASKLIST.md`. This document keeps the
additional context and expectations behind those steps.

**What landed that needs a live look:**
1. **Selector foundations** — `find_face` was retrofitted to route through a deterministic selector
   layer (`resolve_selector`) that resolves against live B-Rep add-in-side and fails closed on
   ambiguity. **Live Fusion evidence was captured on 2026-07-02.** The run found and fixed
   unoriented planar face normals; top, bottom, and right now each resolve one face.
2. **Operation-level selection traces** — `apply_shell`, `apply_fillet`, and `apply_chamfer` now
   return additive `selection_trace` diagnostics in both mock and live registry paths. These traces
   are diagnostic artifacts, not verification gates.
3. **Fuzzy-intent discovery** — a new `recommend_workflow` tool maps a loose request ("something to
   hold a pipe to a wall") to ranked workflow candidates with starting dimensions, then you
   confirm before building. Pure logic is tested; the end-to-end *experience* through your AI host
   is worth trying live.

---

## 0. Get the machine in sync

- [ ] `git pull` on `master` (brings all the new code + this checklist).
- [ ] Refresh the Python install in the repo's venv: `pip install -e .`
- [x] **Reload the Fusion add-in from this checkout — do not skip.** The live add-in code
      (`fusion_addin/ops/live_ops.py`) changed in the selector/trace sessions, and a stale loaded
      add-in will not have the new handlers. In Fusion: **Utilities → Scripts and Add-Ins →
      Add-Ins tab → select `FusionAIBridge` → Stop, then Run again.**
- [x] Confirm Fusion is open and the add-in shows as running.
- [ ] (Optional) `private/` is gitignored and will **not** arrive via `git pull` — copy it over
      manually if you want your `reference_parts/` specs there. **Not required for any step below**
      (discovery's example dimensions are hand-seeded into the code).

---

## 1. Connectivity sanity check

- [x] In your AI host (Claude Desktop / Cursor), ask: *"Run the ParamAItric health check and tell me
      the operating mode."* Expect a healthy response naming the live bridge.

---

## 2. Regression smoke — confirm the bridge + workflows still build after this session

These run full workflows end-to-end against the live bridge. They do **not** exercise `find_face`,
but they confirm nothing else regressed. STLs land in `manual_test_output/`.

- [x] `python scripts/fusion_smoke_test.py --workflow cylinder`
- [x] `python scripts/fusion_smoke_test.py --workflow tube`
- [ ] Confirm each completes and writes its STL; eyeball the bodies in Fusion.

---

## 3. Validate the live selector path (the #1 unverified piece) — via your AI host

No workflow auto-calls `find_face`, so the smoke runner can't cover this. Drive it directly:

- [x] Ask the AI: *"Create a simple bracket, then use `find_face` to find its top face. Show me the
      full result including the selection_trace."*
- [x] **Expect:** a `face_token` plus a `selection_trace` with `status: "resolved"`,
      `kind: "normal_axis"`, `resolved_count: 1`, and a sensible `candidate_count`.
- [x] Try a couple more directions (`bottom`, `right`) the same way; each should resolve to exactly
      one face.
- [x] **Failure mode to watch for:** if `selection_trace.status` comes back `"error"` or `"empty"`,
      the live `get_body_faces` / `get_body_edges` adapter in `live_ops.py` is returning a dict shape
      the resolver doesn't expect (it needs `token`, `type`, `normal_vector`, `area_cm2` on faces).
      That mismatch is the thing to debug — capture the raw trace and the face list.

---

## 4. Validate operation-level selection traces — via your AI host

These checks confirm the live registry returns the same trace shape the mock tests pin.

- [x] Create a simple box or bracket body.
- [x] Ask the AI to apply a shell operation and show the full result including `selection_trace`.
      Expect a resolved face trace for `normal_axis +z` before the shell mutation.
- [x] Ask the AI to apply a small fillet to a simple body and show the full result including
      `selection_trace`. Expect a resolved edge trace with
      `kind: "axis_parallel"` and the body's extrusion axis.
- [x] Ask the AI to apply a small chamfer to a simple body and show the full result including
      `selection_trace`. Expect `axis_parallel` for an interior bracket chamfer or
      `max_face_perimeter` for a top-outer chamfer.
- [x] Capture any mismatch between the trace shape in Fusion and the mock/unit-test trace shape.

Known limitation: interior fillet/chamfer traces narrow to extrusion-axis edges but do not yet
distinguish the single concave edge selected by the mutation. Top-outer chamfer traces match the
mutation edge set exactly.

---

## 5. Try the new discovery experience end-to-end — via your AI host

This is the headline UX from the recent design work (propose-then-confirm).

- [ ] **Fuzzy request:** *"I need something to hold a pipe to a wall."*
      Expect the AI to call `recommend_workflow`, then **propose** `pipe_clamp_half` with starting
      dimensions and the honest caveats ("it's one of two halves", "not for square tube") — and
      **wait** for your go-ahead rather than building immediately.
- [ ] **Confirm** (optionally tweak a dimension). Expect it to build `create_pipe_clamp_half`, verify
      geometry, and export an STL. Open the result in Fusion.
- [ ] **No-match case:** *"I need a herringbone gear."* Expect an honest *"no confident match — here
      are the families I can build"* rather than a forced wrong pick.
- [ ] Optionally try other fuzzy phrasings ("a flat plate with a hole", "an L bracket with a bolt
      hole") to feel out the matching.

---

## 6. Record what you found

- [x] Add a dated entry to `docs/dev-log.md` capturing: the `find_face` live `selection_trace`
      result, shell/fillet/chamfer trace results, the regression-smoke outcomes, and how the
      discovery flow felt. Paste representative traces. This closes the long-open Phase-1 live
      validation evidence gap.

---

## Don't be alarmed by

- **20 pre-existing pytest failures** from unmigrated enclosure and specialty workflow
  `NotImplementedError` stubs. They are unrelated to live selector validation — as of
  2026-06-18, `python3 -m pytest` shows `508 passed, 20 failed, 1 warning`.
- **Missing `private/` and the two strategy docs after `git pull`** — they were intentionally made
  local-only (gitignored). Copy `private/` over manually if you want it; nothing here depends on it.
