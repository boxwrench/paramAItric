# Fusion 360 Validation — Next Steps (for the machine with Fusion)

This is a hands-on checklist for validating the work that landed in the recent sessions, to be
run on the machine that actually has Autodesk Fusion 360. Everything below was built and unit-tested
on a machine **without** Fusion, so the live behaviors here are the genuinely unverified part.

**What landed that needs a live look:**
1. **Selector foundations** — `find_face` was retrofitted to route through a deterministic selector
   layer (`resolve_selector`) that resolves against live B-Rep add-in-side and fails closed on
   ambiguity. The **live add-in handler for `resolve_selector` has never run against real Fusion
   geometry.** This is the #1 thing to validate.
2. **Fuzzy-intent discovery** — a new `recommend_workflow` tool maps a loose request ("something to
   hold a pipe to a wall") to ranked workflow candidates with starting dimensions, then you
   confirm before building. Pure logic is tested; the end-to-end *experience* through your AI host
   is worth trying live.

---

## 0. Get the machine in sync

- [ ] `git pull` on `master` (brings all the new code + this checklist).
- [ ] Refresh the Python install in the repo's venv: `pip install -e .`
- [ ] **Reload the Fusion add-in from this checkout — do not skip.** The live add-in code
      (`fusion_addin/ops/live_ops.py`) changed this session, and a stale loaded add-in will not have
      the new `resolve_selector` handler. In Fusion: **Utilities → Scripts and Add-Ins → Add-Ins
      tab → select `FusionAIBridge` → Stop, then Run again.**
- [ ] Confirm Fusion is open and the add-in shows as running.
- [ ] (Optional) `private/` is gitignored and will **not** arrive via `git pull` — copy it over
      manually if you want your `reference_parts/` specs there. **Not required for any step below**
      (discovery's example dimensions are hand-seeded into the code).

---

## 1. Connectivity sanity check

- [ ] In your AI host (Claude Desktop / Cursor), ask: *"Run the ParamAItric health check and tell me
      the operating mode."* Expect a healthy response naming the live bridge.

---

## 2. Regression smoke — confirm the bridge + workflows still build after this session

These run full workflows end-to-end against the live bridge. They do **not** exercise `find_face`,
but they confirm nothing else regressed. STLs land in `manual_test_output/`.

- [ ] `python scripts/fusion_smoke_test.py --workflow cylinder`
- [ ] `python scripts/fusion_smoke_test.py --workflow tube`
- [ ] Confirm each completes and writes its STL; eyeball the bodies in Fusion.

---

## 3. Validate the live selector path (the #1 unverified piece) — via your AI host

No workflow auto-calls `find_face`, so the smoke runner can't cover this. Drive it directly:

- [ ] Ask the AI: *"Create a simple bracket, then use `find_face` to find its top face. Show me the
      full result including the selection_trace."*
- [ ] **Expect:** a `face_token` plus a `selection_trace` with `status: "resolved"`,
      `kind: "normal_axis"`, `resolved_count: 1`, and a sensible `candidate_count`.
- [ ] Try a couple more directions (`bottom`, `right`) the same way; each should resolve to exactly
      one face.
- [ ] **Failure mode to watch for:** if `selection_trace.status` comes back `"error"` or `"empty"`,
      the live `get_body_faces` / `get_body_edges` adapter in `live_ops.py` is returning a dict shape
      the resolver doesn't expect (it needs `token`, `type`, `normal_vector`, `area_cm2` on faces).
      That mismatch is the thing to debug — capture the raw trace and the face list.

---

## 4. Try the new discovery experience end-to-end — via your AI host

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

## 5. Record what you found

- [ ] Add a dated entry to `docs/dev-log.md` capturing: the `find_face` live `selection_trace`
      result (paste the trace), the regression-smoke outcomes, and how the discovery flow felt.
      This closes the long-open Phase-1 "Task 8 / live smoke" evidence gap.

---

## Don't be alarmed by

- **35 pre-existing pytest failures** (enclosure `NotImplementedError` stubs + one freeform
  session-state bug). They predate all this work and are unrelated — `python3 -m pytest` will show
  `485 passed, 35 failed`. That's the expected baseline.
- **Missing `private/` and the two strategy docs after `git pull`** — they were intentionally made
  local-only (gitignored). Copy `private/` over manually if you want it; nothing here depends on it.
