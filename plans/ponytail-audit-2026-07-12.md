# ParamAItric — Ponytail/YAGNI audit synthesis (2026-07-12)

Entry point for the audit Keith ran on 2026-07-12. This is the authoritative
current-direction summary; it supersedes the "grow golden set toward 20" next
step from the 2026-07-11 handoff (that is now deferred to *after* the vertical
slice — see Next).

## Verdict

Core execution architecture is correctly engineered and stays. Over-planning is
concentrated at the perimeter (multi-backend, multi-host, multi-CAD, 7 profiles,
6 iterations, repeated milestone prose). **The one thing that matters next:**
prove a single trustworthy local-model → Fusion vertical slice before adding any
new backend, packaging, workflow family, evaluation framework, or hardware target.

Vertical slice: natural-language request → Pi → Lemonade/Qwen → guided MCP tools
→ real Fusion geometry → deterministic verification → STL export. Plus one
invalid request that fails safely.

## Now — milestone: one trustworthy local-model→Fusion vertical slice

Batch 1 — release-blocking integration fixes (mutation boundary):
1. Align client/server deadlines — `BridgeClient` default command timeout is 10s
   but the server dispatch deadline is 120s. Make the client timeout slightly
   longer than the server deadline.
2. Generate a request ID for every bridge mutation (normal workflow path sends none today).
3. On an earlier socket timeout, issue a best-effort **authenticated** cancel using the request ID.
4. Parse structured HTTP failures at the MCP boundary: 504/`classification=timeout` → timeout;
   409/`classification=cancelled` → cancelled; 401 → refresh file-derived token and retry once.
5. Do NOT refresh tokens supplied explicitly by the caller.
6. Give each `DispatchRequest` an internal lock; add an atomic `try_start()` so a
   request cancelled before execution can never begin (current check-cancel-then-set-started is racy).
7. Audit real Fusion mutation paths for cancellation checkpoints; treat cancel of a started op as best-effort until audited.
8. Token lifecycle: track whether a bridge instance owns the token file and only
   delete it if owned (a tokenized test bridge must not delete the shared real token);
   make the token path injectable in tests.
9. Add an authenticated, non-mutating bridge probe for doctor (doctor currently
   only checks the token file exists, not that the running bridge accepts it).
10. Wire the runtime profile's `cad_endpoint` into the active MCP server's `BridgeClient`
    (today doctor may validate one endpoint while MCP uses the default).

Batch 2 — guided-contract alignment:
11. Make `cad_inspect` genuinely read-only: restrict to `list_design_bodies`,
    `get_body_info`, `get_body_faces`, `get_body_edges`, `find_face`. Move
    `convert_bodies_to_components` (a mutation) out of `INSPECTION_TOOLS` into an
    explicit mutation/utility category (full profile only).
12. Make prompts profile-aware: one profile-aware tool-name mapping so guided
    prompts reference the guided facade (`cad_health`, `cad_recommend_workflow`,
    `cad_get_requirements`, `cad_build`, `cad_inspect`) not full-profile names
    (`health`, `create_*`, ...). Small mapping + a few formatting functions; not a framework.

Batch 3 — docs alignment (Finding 6):
13. Make `ROADMAP.md` the single authoritative milestone source with a compact
    "Working today / Current milestone / Blockers / Not in scope / Acceptance"
    block. Trim stale status prose from README, `docs/AI_CONTEXT.md`, I2 guide
    ("once it lands" wording). Consistently name the eval harness the
    **server contract regression suite** (it tests server behavior, not model behavior).
14. Label profiles by support status: reference (`claude-fusion`), current target
    (`lemonade-cuda-fusion`), next (`lemonade-vulkan-fusion`), planned/unsupported
    (Strix/ROCm/FreeCAD), parking lot (Fusion on Linux). Doctor distinguishes
    supported/experimental/planned/unknown; planned may parse but is not "release-ready".

Batch 4 — the real I2 proof: pin Pi + Lemonade versions, provider config, MCP
adapter; run one natural-language spacer request and one invalid request through
the real stack; record full reproducibility evidence + any manual intervention.

Batch 5 — confirmed safe cleanup (do AFTER the slice, or fold into docs work):
delete two superseded internal freeform runners; remove the no-op
`ParamAIToolServer = ParamAIToolServer` alias; remove obsolete status prose.

## Findings map (classification / priority)

1. Prove the real agent contract before expanding eval architecture — Clarify+Execute / Critical.
2. Authorization + deadline integration hardening — Protect / Critical (Batch 1).
3. `cad_inspect` must be genuinely read-only — Protect / High (Batch 2).
4. Guided prompts + guided tools share one vocabulary — Collapse / High (Batch 2).
5. Runtime profiles justified; make support status explicit + wire cad_endpoint — Clarify+Defer / Med-High.
6. One authoritative current milestone in docs — Clarify / Medium (Batch 3).
7. Small confirmed cleanup, don't lead with it — Delete / Low (Batch 5).
8. Keep the core safety/execution architecture — Keep / High.

## Keep (do not "refactor" without a concrete, evidenced need)

Fusion main-thread dispatch; MCP/Fusion process separation; strict schemas;
validation at host + bridge; geometry verification gates; structured error
envelopes; restricted file handling; selector diagnostics; explicit
mutation-vs-inspection categories; server contract tests; live Fusion smoke
tests; workflow-family mixin organization; runtime profiles as config records;
full + guided tool surfaces.

## Explicitly NOT in scope until the slice passes

FreeCAD support; native Linux packaging; Strix integration; Fusion on Linux;
local GUI; automatic backend selection; generalized model-evaluation platform;
new speculative workflow families; broad packaging/one-click infrastructure;
additional models before the first local baseline; generic cross-CAD abstraction.

## Note on the just-shipped 0d work

0d (commit `f6923d7`) added the server-side bounded wait + late-mutation policy.
Finding 2 is the **client-side** counterpart: the MCP `BridgeClient` 10s timeout
currently undercuts the 120s server deadline and sends no request ID, so a
timed-out mutation can still run server-side with no cancel issued. Batch 1
closes that gap and the dispatcher start/cancel race. This is the first real
work item for next session.
