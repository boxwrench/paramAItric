# Fusion 360 Hardware Tasklist

This checklist is for the machine that can actually run Autodesk Fusion 360. Everything here
requires live Fusion, the Fusion add-in, or an AI host connected to the live bridge.

## 0. Preflight

- [ ] `git pull` on `master`.
- [ ] `python scripts/install_paramaitric.py --check --no-color`.
- [ ] If the helper reports a missing venv, create it and install the repo:
      `python -m venv .venv`, activate it, then `pip install -e .[dev]`.
- [ ] Reload the Fusion add-in from this checkout:
      **Utilities -> Scripts and Add-Ins -> Add-Ins -> FusionAIBridge -> Stop -> Run**.
- [ ] Confirm Fusion is open and the add-in is running.
- [ ] From the AI host, run the ParamAItric health check and confirm it reports the live bridge.

Stop here if the add-in is stale, the MCP server is using the wrong checkout, or the bridge is not
live. Those failures make every selector result untrustworthy.

## 1. Live Selector Evidence

- [ ] Create a simple bracket or box body.
- [ ] Run `find_face` for the top face and capture the full result.
- [ ] Repeat for bottom and right faces.
- [ ] Confirm each result includes:
      `face_token`, `selection_trace.status == "resolved"`, `kind == "normal_axis"`,
      `resolved_count == 1`, and a sensible `candidate_count`.
- [ ] If any trace is `empty`, `ambiguous`, or `error`, capture the trace plus the raw face list.

## 2. Operation Trace Evidence

- [ ] Apply a shell operation and capture the returned `selection_trace`.
- [ ] Apply a fillet operation and capture the returned `selection_trace`.
- [ ] Apply a chamfer operation and capture the returned `selection_trace`.
- [ ] Confirm the shell trace resolves a face selector before mutation.
- [ ] Confirm fillet/chamfer traces expose the expected coarse linear-edge diagnostic boundary.

Fillet and chamfer traces are intentionally coarse right now. The goal is shape compatibility and
honest diagnostics, not full edge-loop intelligence yet.

## 3. Live Workflow Smokes

- [ ] `python scripts/fusion_smoke_test.py --workflow cylinder`.
- [ ] `python scripts/fusion_smoke_test.py --workflow tube`.
- [ ] Optional: run `spacer` and `bracket` if time permits.
- [ ] Confirm each smoke writes an STL to `manual_test_output/` and leaves sensible editable bodies
      in Fusion.

## 4. Discovery UX Check

- [ ] Ask: "I need something to hold a pipe to a wall."
- [ ] Expect `recommend_workflow` to propose `pipe_clamp_half` with starting dimensions and caveats,
      then wait for confirmation before building.
- [ ] Confirm, optionally tweak one dimension, and verify the resulting STL/body.
- [ ] Ask: "I need a herringbone gear."
- [ ] Expect a no-confident-match response with available families, not a forced wrong workflow.

## 5. Evidence Capture

- [ ] Add a dated entry to `docs/dev-log.md`.
- [ ] Record Fusion version, date, checkout commit, and add-in reload confirmation.
- [ ] Paste representative selector and operation traces.
- [ ] Record smoke-test commands and pass/fail results.
- [ ] Note any UX friction from the discovery flow.

