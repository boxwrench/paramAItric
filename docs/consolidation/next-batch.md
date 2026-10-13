# Authorized next batch — Utility product plate

**Paused by the user for reboot, 2026-10-13.** Read
[pause-2026-10-13.md](pause-2026-10-13.md) before restarting services or work.

Completed software batch in `d9e7bcf`: full integration suite 823 passed, five
expected failures; actual MCP stdio geometry and final focused guards passed.
Hardware/live qualification remains the next bounded task.

Current qualification preparation is complete; the two environment gates remain
incomplete. Runbook: [qualification.md](qualification.md).

- [x] Add a reproducible collector with host facts, real guided CAD, wall times,
  viewer URLs and a read-only Fusion probe; never infer interactive success.
- [x] Guard the Fusion proof against mock health before mutation.
- [x] Exercise the existing viewer on the available AMD desktop; retain observed
  edge readings/screenshots separately from mandatory geometric evidence.
- [ ] Qualify Strix Halo interactive graphics/API/driver on the actual target.
- [ ] Capture fresh live Fusion geometry and compare explicitly available facts.

Actual collector run on `b6584a7`: real geometry passed, overall qualification
incomplete, Fusion unavailable. Focused tests: 34 passed, 1 real geometry test
skipped; the real path ran separately through MCP. No new part family was added.

October 13 review follow-up completed on the same branch:

- [x] Separate staged geometry from atomically published acceptance; cover both
  sides of the cancellation boundary and publication failures.
- [x] Enforce saved artifact hashes before inspection or parameter replay.
- [x] Align optional/default output handling and the open-backend request prompt.
- [x] Clean up failed health probes; rerun full regressions and real MCP proof.

Results: 843 passed / 5 expected failures, 17 original cases passed, real guided
stdio proof passed. See [updated handoff](handoff.md#review-corrections--2026-10-13).

Requested 2026-10-12: keep working, create/pursue the next logical tasks, and return
to this project in five hours. Active development branch:
`consolidation/utility-backend-2026-10-12`. Preserve master and all working Fusion
paths. No release, merge, new renderer, kernel, upstream fork or backend auto-selection.

- [x] A. Consolidate the foundation handoff and commit real geometry evidence.
- [x] B. Add explicit operator configuration for the open backend; route only the
  supported centered plate through the existing guided `cad_build` interface.
  Report actual health/requirements and reject unsupported workflows before mutation.
- [x] C. Add retained revision IDs, dimension-change replay and read-only inspection
  of saved exported geometry through the same curated tools. Preserve the centered
  hole relationship; reject unknown/critical unsupported changes.
- [x] D. Connect MCP request cancellation to the isolated worker, kill its process
  group and reject overlapping transactions. Keep Fusion cancellation unchanged.
- [x] E. Run public-schema/default-Fusion safety contracts, negative open-backend
  tests and real guided-build/edit/inspection geometry. Update evidence, docs and
  the precise next task; commit reviewable changes on this branch.

Timer: the one-shot `paramaitric-return-20261013.timer` fired its same-thread
follow-up at 2026-10-13 03:25:49 PDT and is inactive. No further return is scheduled;
wait for the user to resume after reboot.

Stop this batch after the centered plate product path and safety gates work.
Target Strix Halo graphics and fresh live Fusion evidence require those environments;
do not replace missing qualification with mock or CPU-only claims.
