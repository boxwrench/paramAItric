# Fusion 360 Hardware Tasklist

This checklist is for the machine that can actually run Autodesk Fusion 360. Everything here
requires live Fusion, the Fusion add-in, or an AI host connected to the live bridge.

## 0. Preflight

- [x] `git pull` on `master`.
- [x] `python scripts/install_paramaitric.py --check --no-color`.
- [ ] If the helper reports a missing venv, create it and install the repo:
      `python -m venv .venv`, activate it, then `pip install -e .[dev]`.
- [x] Reload the Fusion add-in from this checkout:
      **Utilities -> Scripts and Add-Ins -> Add-Ins -> FusionAIBridge -> Stop -> Run**.
- [x] Confirm Fusion is open and the add-in is running.
- [x] From the AI host, run the ParamAItric health check and confirm it reports the live bridge.

Stop here if the add-in is stale, the MCP server is using the wrong checkout, or the bridge is not
live. Those failures make every selector result untrustworthy.

## 1. Live Selector Evidence

- [x] Create a simple bracket or box body.
- [x] Run `find_face` for the top face and capture the full result.
- [x] Repeat for bottom and right faces.
- [x] Confirm each result includes:
      `face_token`, `selection_trace.status == "resolved"`, `kind == "normal_axis"`,
      `resolved_count == 1`, and a sensible `candidate_count`.
- [x] If any trace is `empty`, `ambiguous`, or `error`, capture the trace plus the raw face list.

## 2. Operation Trace Evidence

- [x] Apply a shell operation and capture the returned `selection_trace`.
- [x] Apply a fillet operation and capture the returned `selection_trace`.
- [x] Apply a chamfer operation and capture the returned `selection_trace`.
- [x] Confirm the shell trace resolves a face selector before mutation.
- [x] Confirm fillet/chamfer traces expose the extrusion-axis candidate boundary, and top-outer
      chamfers expose the exact maximum-face perimeter.

Interior fillet/chamfer traces narrow to extrusion-axis edges but do not yet distinguish the single
concave edge selected by the mutation. Top-outer chamfer traces resolve the exact perimeter.

## 3. Live Workflow Smokes

- [x] `python scripts/fusion_smoke_test.py --workflow cylinder`.
- [x] `python scripts/fusion_smoke_test.py --workflow tube`.
- [x] Optional: run `spacer` and `bracket` if time permits.
- [x] Confirm each smoke writes an STL to `manual_test_output/` and leaves sensible editable bodies
      in Fusion.

## 4. Discovery UX Check

- [x] Ask: "I need something to hold a pipe to a wall."
- [x] Expect `recommend_workflow` to propose `pipe_clamp_half` with starting dimensions and caveats,
      then wait for confirmation before building.
- [x] Confirm, optionally tweak one dimension, and verify the resulting STL/body.
- [x] Ask: "I need a herringbone gear."
- [x] Expect a no-confident-match response with available families, not a forced wrong workflow.

## 5. Evidence Capture

- [x] Add a dated entry to `docs/dev-log.md`.
- [x] Record Fusion version, date, checkout commit, and add-in reload confirmation.
- [x] Paste representative selector and operation traces.
- [x] Record smoke-test commands and pass/fail results.
- [x] Note any UX friction from the discovery flow.

