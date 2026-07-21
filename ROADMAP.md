# ParamAItric Roadmap

> Updated 2026-07-20 (rev 3 — folded in target B validation plan; goals batch G1–G6 landed).
> This is the single canonical roadmap. It consolidates and supersedes
> [NEXT_PHASE_PLAN.md](file:///C:/GitHub/paramAItric/docs/archive/planning/NEXT_PHASE_PLAN.md),
> [UX_ROADMAP.md](file:///C:/GitHub/paramAItric/docs/archive/planning/UX_ROADMAP.md),
> [NEXT_RESEARCH_PLAN.md](file:///C:/GitHub/paramAItric/docs/archive/planning/NEXT_RESEARCH_PLAN.md),
> [RESEARCH_TRACKS.md](file:///C:/GitHub/paramAItric/docs/archive/planning/RESEARCH_TRACKS.md),
> [FUSION_HARDWARE_TASKLIST.md](file:///C:/GitHub/paramAItric/docs/archive/planning/FUSION_HARDWARE_TASKLIST.md), and
> [FUSION_VALIDATION_NEXT_STEPS.md](file:///C:/GitHub/paramAItric/docs/archive/planning/FUSION_VALIDATION_NEXT_STEPS.md)
> (all archived under the planning archive), and folds in the direction from
> [Lemonade Integration Specification.pdf](file:///C:/GitHub/paramAItric/docs/Lemonade%20Integration%20Specification.pdf).

## Current milestone (authoritative)

### Working today

- **I1 `claude-fusion`** (reference implementation): Claude Desktop/Cursor → MCP server
  → Fusion add-in on Windows. Structured errors, MCP schema fidelity, capability-aware
  health, `full` and `guided` tool profiles, `cad_inspect` is read-only.
- Runtime-profile activation is implemented end-to-end: active profile name, export
  directory, tool surface, and the active profile's `cad_endpoint` are all wired into
  the running MCP server (server's `BridgeClient` now honors
  `runtime_info.ACTIVE_PROFILE_CAD_ENDPOINT`).
- Mutation-boundary hardening has landed: per-run bridge auth with origin/content
  hardening, server-side dispatch deadlines with a late-mutation policy, client/server
  deadline alignment, per-request IDs, best-effort authenticated timeout-cancel, token
  lifecycle/ownership tracking, and an authenticated doctor probe.
- Dispatch start/cancel is atomic (`try_start()`): a request cancelled before execution
  can never begin.
- Guided prompts are profile-aware (map to `cad_health` / `cad_recommend_workflow` /
  `cad_get_requirements` / `cad_build` / `cad_inspect`, not full-profile tool names).
- The **server contract regression suite** (`evaluations/`) exercises the MCP server
  against known tool+args pairs in mock mode: schema validity, argument normalization,
  tool choice, and structured-error shape. It does not evaluate model behavior — that
  is a separate, not-yet-built evaluation.

### Current milestone

One reproducible **Pi + Lemonade + Qwen → guided MCP → Fusion** vertical slice:

1. One natural-language request succeeds end-to-end (guided tool surface, real Fusion
   geometry, verification, STL export).
2. One invalid request fails safely (structured error, no partial/corrupt geometry).

This is I2 (`lemonade-fusion`), Stage 3 below. Nothing past this milestone — additional
backends, hosts, CAD targets, or packaging — is worth doing until it passes once, for
real, with recorded reproducibility evidence.

### Current blockers

- **Started-operation cancellation is best-effort only.** No live/mock Fusion operation
  calls `raise_if_cancelled()` mid-execution, so cancelling a request whose dispatch has
  already reached `STARTED` can only mark status — it cannot interrupt in-flight Fusion
  API calls. Auditing real Fusion mutation paths for cancellation checkpoints is
  unresolved and blocks calling cancellation "safe" in the general case.
- **Pi + Lemonade integration details are unpinned.** Pi version, Lemonade version, the
  Pi↔MCP adapter mechanism, exact model-provider configuration, and the health-check
  command are all still `TBD` in `docs/setup/lemonade-fusion.md`.
- **The real I2 proof has not been run.** No natural-language request has yet gone
  through the actual Pi + Lemonade + Qwen stack against a live Fusion session; the
  milestone above is unproven until that run happens and is recorded.

### Explicitly not in scope (until the slice passes)

FreeCAD support; Strix Halo integration (remote or native); native Linux packaging;
Fusion on Linux; a local GUI; automatic backend selection; a generalized
agent/model-evaluation platform; new speculative workflow families; broad
packaging/one-click install infrastructure; additional models before the first local
baseline; generic cross-CAD abstraction.

### Acceptance test

Claude (`claude-fusion`) completes all supported golden cases; Lemonade/Qwen
(`lemonade-cuda-fusion`) completes ≥10 of the first 12 supported golden requests without
manual tool correction; zero tolerance for bypassing failed verification, inventing
operations, or unsafe failures on either path; results are geometry-equivalent to the
Claude baseline (bounding dimensions, body count, volume, features, placement, and
verification tier match within tolerance — not identical files or topology IDs); the
full test suite passes with no unexpected failures.

## North star

**ParamAItric Local**: a private maintenance CAD assistant that turns plain-language
descriptions and measurements into validated, editable, printable utility parts —
with **one verified workflow core, multiple model providers (Claude API / local via
Lemonade), multiple inference backends (CUDA / Vulkan / ROCm), and eventually multiple
CAD backends (Fusion / FreeCAD / mock)**.

Two invariants govern everything below:

1. **Claude + Fusion stays the reference implementation.** Local-model work must never
   weaken existing workflows, Fusion reliability, geometry verification, structured
   failures, STL export, or freeform safeguards. Every major local-model change is
   evaluated against the same requests using Claude.
2. **Model hosting and CAD execution are independent choices.** Changing the model
   endpoint must not touch CAD workflow code; changing the CAD backend must not touch
   the agent or model. Runtime profiles (JSON, outside the workflow core) carry all
   configuration.

## Iterations & Validation Configurations

We prove or kill **Target B** (local model + FreeCAD on Strix Halo) by decoupling model contract competence from the CAD backend, testing them in parallel, and composing them only after both pass.

| Config | Name | Stack | Role / Status | Reference |
|---|---|---|---|---|
| I1 | `claude-fusion` | Claude Desktop/Cursor + MCP + Fusion (Windows) | **Working today** (Track A Reference) | [claude-fusion.md](file:///C:/GitHub/paramAItric/docs/setup/claude-fusion.md) |
| I2 | `lemonade-fusion` | Pi + Lemonade (CUDA → Vulkan) + Fusion | Diagnostic reference for Compose triage | [lemonade-fusion.md](file:///C:/GitHub/paramAItric/docs/setup/lemonade-fusion.md) |
| I4 | `strix-remote` | Laptop CAD + Pi ↔ Strix Lemonade over LAN | Diagnostic reference for Compose triage | [strix-remote.md](file:///C:/GitHub/paramAItric/docs/setup/strix-remote.md) |
| — | **Test 1** | Local MoE/9B + Vulkan + Mock backend (no CAD) | Underway (Target B) | [B_VALIDATION_PLAN.md](file:///C:/GitHub/paramAItric/plans/B_VALIDATION_PLAN.md) |
| — | **Test 2** | Ubuntu Strix + FreeCAD Bridge (Claude driver) | Underway (Target B) | [B_VALIDATION_PLAN.md](file:///C:/GitHub/paramAItric/plans/B_VALIDATION_PLAN.md) |
| — | **Compose** | Vulkan model + Ubuntu FreeCAD Bridge (Strix offline) | Gate (Target B) | [B_VALIDATION_PLAN.md](file:///C:/GitHub/paramAItric/plans/B_VALIDATION_PLAN.md) |

Note: Legacy iteration `I3` (FreeCAD spike) and `I5` (Strix native) have collapsed into **Test 2** and **Compose**. Legacy experimental iteration `I6` (Fusion-on-Linux) has been deleted.

Each **supported** iteration has a setup guide; runtime profile names under [runtime_profiles_data/](file:///C:/GitHub/paramAItric/mcp_server/runtime_profiles_data/) follow the iteration stack:

```
Laptop:  claude-fusion, lemonade-cuda-fusion, lemonade-vulkan-fusion
Strix:   lemonade-rocm-fusion-remote, lemonade-vulkan-fusion-remote,
         lemonade-rocm-freecad, lemonade-vulkan-freecad
```

A profile parsing successfully in `mcp_server/runtime_profiles_data/` is not the same as
being release-ready: only `claude-fusion` (reference) and the `lemonade-*-fusion` laptop
profiles (current target / next) carry a reliability claim right now. Strix and FreeCAD
profiles are planned/unsupported — they may parse but nothing has validated them end to
end.

---

## The single flow

Effort tags: **Quick** (≤ half a day), **Small**, **Medium**, **Large**. Quick/Small
items that unblock later stages are pulled forward deliberately.

### Dependency graph

The revised path eliminates the intermediate iteration ladder. Stage 2 (geometry foundations) gates only Test 2 (FreeCAD backend proof):

```
Stage 0/1 Remainders (baseline & local-model readiness)
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
      Test 1                Test 2 (gated by Stage 2)
   (Local Model)      (FreeCAD backend)
  (Strix + Vulkan)    (Ubuntu process)
         │                     │
         └──────────┬──────────┘
                    ▼
                 Compose
             (Strix offline)
                    │
                    ▼
                Stage 7 (Packaging)
```

Stage 4 (intake/UX) slots in opportunistically once Stage 1 lands.

### Stage 0 — Golden baseline + quick wins (now)

Capture current Claude behavior as the regression contract *before* touching the host
interface, and knock out the cheap open items.

**Progress (2026-07-11):** the server contract regression suite (`evaluations/`) has
landed on `lemonade-integration`:
case schema, mock runner, reproducibility metadata, four initial cases
(spacer success, plate-with-hole success, invalid dimensions, bridge unavailable),
and the live-Fusion Claude baseline for all four (`evaluations/expected/claude/`).
Also landed 2026-07-11: filename auto-versioning, open-folder hand-off in export
summaries, `scripts/setup.ps1` / `setup.sh`, and the MIT license.

**Progress (2026-07-20):** the golden set now holds **17 cases** (8 contract, 9 safety); the
12–20 target is met and both tier-3 gaps (*ambiguous request*, *verification failure*) are
now closed (G2). Also landed across the goals batch: the **geometry-equivalence comparator**
(`evaluations/runner/comparison.py`, `python -m evaluations.runner --compare-to claude`), the
**baseline capture driver** (`evaluations/baseline.py`), **per-request metrics** (G4), and a
backend-neutral **operation vocabulary** (`mcp_server/operations.py`, G6). Open: **13 of 17
cases still lack hand-captured Claude baselines** — run `python -m evaluations.baseline --status`.
See `plans/goals.md` (all six goals done) and `docs/dev-log.md` 2026-07-19/20 for evidence.

| Task | Source | Effort |
|------|--------|--------|
| ✅ Create Lemonade integration branch (`lemonade-integration`) | Spec §11 | Quick |
| Golden evaluation set: 12–20 maintenance requests, **split into three tiers** (below). Each case records request, expected workflow, measurements, tool call, normalized args, verification facts, export type, succeed-or-fail-safely. Lives in [evaluations/](file:///C:/GitHub/paramAItric/evaluations/). *Harness + first 4 cases + Claude baseline done; 8–16 more cases open.* | Spec §4 | Medium |
| ✅ Evaluation-case schema + reproducibility metadata format (below) | Feedback 2026-07-11 | Small |
| ✅ Choose and add the open-source license — MIT ([LICENSE](file:///C:/GitHub/paramAItric/LICENSE), [pyproject.toml](file:///C:/GitHub/paramAItric/pyproject.toml)) | Phase-0 backlog | Quick |
| ✅ Output filename auto-versioning (`bracket_v2.stl`) — never overwrite reprints (applies to user-visible export destinations; test/tempdir paths intentionally still overwrite) | UX #2 (partial) | Quick |
| ✅ Open-folder hand-off after export — export summary now carries export folders + per-OS open commands for the AI to suggest | UX #11 | Quick |
| ✅ Interim one-command bootstrap script ([setup.ps1](file:///C:/GitHub/paramAItric/scripts/setup.ps1) / [setup.sh](file:///C:/GitHub/paramAItric/scripts/setup.sh): venv → pip → `--install-addin` → `--write-claude-config -y` → `--check`) | UX #1 interim | Small |

**Evaluation tiers** — not every case is a live Fusion test:

1. **Contract evaluations** (fast, mock mode): workflow recommendation, schema
   validity, argument normalization, tool choice, structured-error shape. This tier
   runs dozens of model tests rapidly without mutating Fusion.
2. **Live Fusion evaluations** (~6 representative parts, authoritative): spacer,
   plate with hole, tube, bracket, fillet/chamfer part, enclosure.
3. **Failure & safety evaluations**: invalid dimensions, bridge unavailable,
   ambiguous request, unsupported request, verification failure.

**Reproducibility metadata** — every evaluation result records:

```json
{
  "paramaitric_commit": "...", "lemonade_version": "...", "pi_version": "...",
  "model": "Qwen3.5-9B-GGUF", "quantization": "...", "tool_profile": "guided",
  "inference_backend": "cuda", "hardware": "...", "driver_version": "...",
  "context_size": 8192, "temperature": 0, "evaluation_case": "plate_centered_hole"
}
```

**Acceptance:** Claude completes all supported golden cases; unsupported/invalid
requests fail safely; files locatable and openable; verification recorded; the
complete test suite passes with no unexpected failures.

**Immediate next work unit:** the Stage-1 remainders (tool-surface gating, runtime-profile
activation, bridge auth, dispatch deadlines) are done — see "Current milestone" at the top of
this document. The golden set has reached 17 cases with both tier-3 gaps closed (G2), so what
remains for Stage 0 is capturing the 13 outstanding Claude baselines (human-only live-Fusion
work; `python -m evaluations.baseline --status`). This work is deferred behind the Stage-3
vertical-slice milestone per the 2026-07-12 audit (`plans/ponytail-audit-2026-07-12.md`), not
abandoned.

### Stage 1 — Local-model readiness (benefits every host, not just Lemonade)

**Progress (2026-07-11):** most of Stage 1 has landed on the `lemonade-integration`
branch (commits through `2e907e8`). **Done:** structured errors; MCP schema fidelity —
all 34 workflow tools advertise field names, types, required fields, defaults, common
numeric bounds, enums, and unit metadata, with the optional `units` selector
(`cm`/`mm`/`in`) normalized to centimeters before existing validators run and precise
fields still nested under the established `payload` envelope; capability-aware health
(backend identity, version, mode, command capabilities, workflow count; prompts no
longer assume a specific CAD backend); runtime-profile parsing with strict, path-safe
validation for the seven named stacks under `mcp_server/runtime_profiles_data/`,
packaged and consumed by doctor; `paramaitric doctor --profile <name>` checking
Python env, package imports, MCP startup, local model endpoint + model availability,
CAD backend reachability, bridge auth, export-dir write permissions, plus a
non-mutating health call; active runtime-profile activation (loaded via CLI or env);
and tool-surface gating for the `guided` profile. Also shipped: per-run bridge
authorization with browser-origin protection (0c), and server-side dispatch
deadlines with an explicit late-mutation policy (0d) — timed-out requests are
cancelled via the existing cancellation tokens and their late completions
discarded.

| Task | Source | Effort |
|------|--------|--------|
| ✅ **MCP schema fidelity**: generate precise input schemas (field names, types, ranges, units, enums) from existing Pydantic/workflow definitions instead of `payload: dict`. Highest-value single change for local models. | Spec §5.1 | Medium |
| ✅ Optional `units` field ("mm"/"cm"/"in") normalized at the schema layer | UX #6 folded into §5.1 | Small (as rider) |
| ✅ **Two tool profiles**: `full` (Claude, dev, large models) and `guided` (small models, novices). Same underlying implementations; eval suite decides which the 9B model uses. | Spec §5.2 | Medium |
| ✅ **Structured errors everywhere**: `{ok, classification, stage, error, recoverable, next_step, partial_result}` — no host ever parses a traceback. | Spec §5.3 + UX #4 | Small–Medium |
| ✅ **Capability-aware health**: report backend, version, mode, capabilities, workflow count; stop hardcoding "Fusion" in prompts | Spec §5.4 | Small |
| ✅ **`paramaitric doctor --profile <name>`**: extend the existing `install_paramaitric.py --check` probe to test Python env, package import, MCP startup, Lemonade endpoint + model, CAD backend reachability, bridge auth, export-dir write, one health call | Spec §5.5 (builds on shipped UX #8) | Small |
| ✅ Runtime-profile parsing and activation (`mcp_server/runtime_profiles_data/*.json`; name, export dir, tool surface, and `cad_endpoint` all wired into the running server) | Spec §3 | Small |
| ✅ **Per-run bridge authorization + browser-origin protection** (0c): per-run token via `secrets`, user-only storage, `hmac.compare_digest`, auth on by default, `Origin`/`Referer` rejection, content-type + body cap, structured 4xx envelopes | Phase-0 backlog / Spec §5.6 | Small–Medium |
| ✅ **Server-side dispatch deadlines + late-mutation policy** (0d): bounded waits with a configurable deadline; on expiry the request is cancelled via the existing token and any late completion is discarded; structured 504 timeout envelope | Phase-0 backlog / Spec §5.6 | Small |

### Stage 2 — Geometry foundations continuation (parallel track)

The pre-Lemonade roadmap's core insight stands and the spec explicitly endorses it
(§2.5): semantic selection, stable references, and a narrow operation vocabulary are
the most important internal work, and **gate Test 2 (FreeCAD backend proof)**. Selector layer,
`SelectionTrace`, live Fusion validation, and richer edge diagnostics have landed.
As of 2026-07-20 the remaining Stage 2 items below are **all complete** (see
`docs/dev-log.md` 2026-07-20 and `plans/goals.md`), so the Stage 2 gate on Test 2 (the
FreeCAD backend proof) is clear:

| Task | Source | Effort | Status |
|------|--------|--------|--------|
| Attribute pinning with validity checks (detect stale pins after topology changes; fall back or fail closed by policy) | Phase-1 continuation | Medium | ✅ Done 2026-07-20 (G5, `mcp_server/selectors.py`) |
| Written stable-reference policy (when to re-resolve semantically, pin, bookmark, or hard-fail) | Phase-1 continuation | Small | ✅ Done 2026-07-19 (D1, `docs/STABLE_REFERENCE_POLICY.md`) |
| Narrow internal operation vocabulary (add/cut/intersect/new-body; target/mode/placement/expected-delta) — this becomes the minimal backend operation vocabulary the CAD backend protocol needs | Phase-1 continuation + Spec §11 batch 2 | Medium | ✅ Done 2026-07-20 (G6, `mcp_server/operations.py`) |

### Stage 3 — Test 1: Local model contract competence

**Question answered:** can a local MoE model correctly drive the ParamAItric tool surface?
No CAD, no Fusion, no FreeCAD. Model reasoning only.

**Hardware/stack:** Strix Halo, Ubuntu, llama.cpp Vulkan (RADV, current Mesa), served via Lemonade. ROCm not required for this test.

| Task | Source | Effort |
|------|--------|--------|
| Mock backend answers `/health` and `/command` well enough to satisfy the MCP server for tier-1 (contract) cases | [B_VALIDATION_PLAN.md](file:///C:/GitHub/paramAItric/plans/B_VALIDATION_PLAN.md) | Small |
| Constrained decoding wired: compile Pydantic-derived tool schemas into llama.cpp grammar / json_schema constraints | [B_VALIDATION_PLAN.md](file:///C:/GitHub/paramAItric/plans/B_VALIDATION_PLAN.md) | Medium |
| Runtime profile added: `lemonade-vulkan-mock`. `paramaitric doctor --profile lemonade-vulkan-mock` passes | [B_VALIDATION_PLAN.md](file:///C:/GitHub/paramAItric/plans/B_VALIDATION_PLAN.md) | Small |
| Run test matrix (Qwen3.5 9B baseline vs gpt-oss 20B, optional 30B MoE) × (guided, full profiles) × tier-1 contract cases | [B_VALIDATION_PLAN.md](file:///C:/GitHub/paramAItric/plans/B_VALIDATION_PLAN.md) | Medium |

**Pass / fail:**
- **Pass:** either spec'd model matches the Claude baseline on all contract cases in at least one profile, zero safety violations. Qwen3.5 9B passing `guided` is the cheapest win; gpt-oss 20B passing `full` is the stronger result.
- **Fail:** neither spec'd model matches baseline on contract cases even with constrained decoding. Target B pauses on fail.

### Stage 4 — Intake & UX layer that compounds with local models

These items from the old UX backlog directly serve the guided profile and small-model
reliability, so they slot here rather than being deferred:

| Task | Source | Effort |
|------|--------|--------|
| Iterate-on-last-part flow (store last validated spec; delta requests like "make the hole 1 mm bigger") | UX #2 | Medium |
| Printability guardrails (warn, don't block: thin walls, tiny holes, nozzle-resolution features) returned in results | UX #3 | Medium |
| Replacement-part preset library / reference catalog (common dimensions, hardware conventions) | UX #10 + old Phase 3c | Medium |
| 3MF export option alongside STL | UX #9 | Small–Medium |
| Onboarding visuals in INSTALL (Fusion Add-Ins dialog, MCP indicator, first export) | UX #12 | Quick (needs manual capture) |

### Stage 5 — Test 2: FreeCAD backend process-model proof

**Question answered:** does a FreeCAD bridge speaking the existing contract actually work?
Driver is **Claude** (known-good model), so every failure is unambiguously the backend's.

**Scope guard:** this is ROADMAP Stage 5 step 1 only. It does **not** require the Stage 2
operation vocabulary — that gates the *workflow port*, not this proof.

#### Architecture under test
```
ParamAItric MCP server → HTTP → FreeCAD bridge process → FreeCAD API / FreeCADCmd
```
FreeCAD (1.x) runs as a separate FreeCAD-owned process with its own Python. The ParamAItric venv never imports FreeCAD. Bridge implements the same endpoints as the Fusion add-in: `/health`, `/command`, `/cancel`, `/capabilities`.

#### Proof sequence (in order, each step must pass before the next)
1. `/health` returns capability-aware identity (backend=freecad, version, mode)
2. create document
3. create one *named* solid (single pad/box is fine)
4. save native `.FCStd`
5. export STEP and STL; both open in a viewer and report sane bbox/volume
6. close and reopen the document
7. re-resolve the named object from step 3 by name/reference — not by index
8. structured failure check: send one invalid command; bridge returns the standard `{ok, classification, stage, error, recoverable, next_step}` shape, never a traceback

**Pass / stop:**
- **Pass:** all 8 steps, on the Strix box (Linux-native). Then and only then: write [protocol.py](file:///C:/GitHub/paramAItric/cad_backends/protocol.py) from the Stage-2 vocabulary and port plate-with-centered-hole.
- **Stop (per existing roadmap stop rules):** any step requires `if fusion / if freecad` branching above the bridge, named-object re-resolution is unreliable, or the native doc isn't testably editable.

### Stage 6 — Compose gate

Run only when Test 1 and Test 2 have both passed.

- **Stack:** whichever model passed Test 1 (Vulkan) + FreeCAD bridge, one runtime profile, on the Strix box.
- **Tasks:**
  - Run the full golden set. Acceptance = existing Stage 3 bar: ≥10 of first 12 supported requests without manual tool correction; zero tolerance on safety; geometry-equivalent to Claude baseline.
  - **Triage on composed failure:** re-run the failing case with (a) Claude + FreeCAD and (b) local model + mock. Whichever leg reproduces the failure owns it. Only if *neither* leg reproduces it is the interaction itself the bug.

### Stage 7 — Packaging

- **Development packaging:** Python env, Pi integration, profiles, prompts, doctor, model setup instructions, Fusion add-in installer, FreeCAD backend when viable, evaluation suite.
- **Product packaging:** embeddable Lemonade, guided model download, one-command startup, automatic hardware/backend detection, Windows installer + Linux package/AppImage, offline docs, health dashboard, export history, backend selection. The `.mcpb` one-click Claude Desktop extension (old UX #1) becomes the `claude-fusion` flavor of this same packaging effort. **Large**

---

## Repository direction

Introduce directories incrementally as working implementations emerge:

```
cad_backends/ (protocol.py, fusion/, freecad/, mock/)
local_app/    (prompts/, pi_extension/, doctor/)
mcp_server/   (runtime_profiles_data/, ...)
evaluations/  (cases/, expected/, results/, runner/)
scripts/      (start_windows.ps1, start_linux.sh, connect_strix.ps1, run_evaluations.py)
docs/         (LEMONADE_INTEGRATION.md, LOCAL_MODEL_EVALUATION.md, CAD_BACKEND_PROTOCOL.md, FREECAD_SPIKE.md)
```

## Standing rules

- Deterministic CAD logic stays outside the LLM: the model understands, selects, gathers, populates, interprets, explains — it never generates arbitrary scripts, guesses safety-critical dimensions, bypasses verification, continues past failed checks, or invents operations.
- Safety failures are zero-tolerance in every evaluation; pass thresholds are tunable, safety is not.
- Workflow count and primitive count are not progress metrics; selector determinism, diagnostic quality, and eval pass rates are.
- The official Autodesk Fusion MCP connector remains monitor-only (decision 2026-06-13); it becomes an adapter target only if it exposes a queryable topology surface.
- **Refactoring & Module Splitting (`0j`)**: Retain [schemas.py](file:///C:/GitHub/paramAItric/mcp_server/schemas.py) and [workflow_registry.py](file:///C:/GitHub/paramAItric/mcp_server/workflow_registry.py) as centralized files until **Test 1** and **Test 2** are completed. Do not perform structural module splitting during the validation phase to avoid introducing regressions, unless local model context/prefill limits in Test 1 force it.

## Where the old backlogs went

| Old doc | Disposition |
|---------|-------------|
| [NEXT_PHASE_PLAN.md](file:///C:/GitHub/paramAItric/docs/archive/planning/NEXT_PHASE_PLAN.md) Phase 0 | Done items recorded there; open remainders (license, bridge auth, dispatch deadlines, module-size cleanup) → Stages 0–1. 0j (module splitting) stays opportunistic. |
| [NEXT_PHASE_PLAN.md](file:///C:/GitHub/paramAItric/docs/archive/planning/NEXT_PHASE_PLAN.md) Phase 1 | → Stage 2 (attribute pinning, reference policy, op vocabulary) — all landed 2026-07-19/20 (G5/D1/G6). |
| [NEXT_PHASE_PLAN.md](file:///C:/GitHub/paramAItric/docs/archive/planning/NEXT_PHASE_PLAN.md) Phases 2–5 (workflow hardening, intake, local UI, threads/patterns/loft) | Deferred behind Stages 1–3; intake pieces that help small models moved into Stage 4. Local `/ui` and capability expansion resume after I2 is proven. |
| [UX_ROADMAP.md](file:///C:/GitHub/paramAItric/docs/archive/planning/UX_ROADMAP.md) | #1 → Stages 0 (interim script) + 7 (packaging); #2 → 0 (versioning) + 4 (iteration flow); #3, #9, #10, #12 → Stage 4; #4 → Stage 1 (structured errors); #6 → Stage 1 (schema fidelity); #5, #7, #8 shipped; #11 → Stage 0. |
| [NEXT_RESEARCH_PLAN.md](file:///C:/GitHub/paramAItric/docs/archive/planning/NEXT_RESEARCH_PLAN.md) / [RESEARCH_TRACKS.md](file:///C:/GitHub/paramAItric/docs/archive/planning/RESEARCH_TRACKS.md) | Research already converted to the Stage-2 implementation slice; remaining questions ride with their stages. Decision history preserved in archive + [dev-log.md](file:///C:/GitHub/paramAItric/docs/dev-log.md). |
| [FUSION_HARDWARE_TASKLIST.md](file:///C:/GitHub/paramAItric/docs/archive/planning/FUSION_HARDWARE_TASKLIST.md) / [FUSION_VALIDATION_NEXT_STEPS.md](file:///C:/GitHub/paramAItric/docs/archive/planning/FUSION_VALIDATION_NEXT_STEPS.md) | Completed live-validation checklists. The golden evaluation set (Stage 0) replaces ad-hoc hardware checklists. |
| `DEVELOPMENT_PLAN.md` | Legacy pointer; removed 2026-07-12 (this roadmap is the single source). |
