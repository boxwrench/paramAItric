# ParamAItric Roadmap

> Updated 2026-07-12 (rev 3 — reflects `lemonade-integration` through the SA-1..SA-3
> batches; see `plans/ponytail-audit-2026-07-12.md` for the audit that reordered this
> document around one milestone).
> This is the single canonical roadmap and the single authoritative source of milestone
> status. It consolidates and supersedes
> `docs/NEXT_PHASE_PLAN.md`, `docs/UX_ROADMAP.md`, `docs/NEXT_RESEARCH_PLAN.md`,
> `docs/RESEARCH_TRACKS.md`, `docs/FUSION_HARDWARE_TASKLIST.md`, and
> `docs/FUSION_VALIDATION_NEXT_STEPS.md` (all archived under `docs/archive/planning/`),
> and folds in the new direction from
> [`docs/Lemonade Integration Specification.pdf`](docs/Lemonade%20Integration%20Specification.pdf).

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

## Iterations and profile support status

Each iteration is a runnable configuration with its own setup guide (see `docs/setup/`).
Support status labels (Finding 5): **reference** (the baseline everything is checked
against), **current target** (this milestone's slice), **next** (immediately after),
**planned/unsupported** (may parse in the runtime-profile loader, but is not
release-ready — no reliability claim), **parking lot** (not being pursued right now).

| # | Iteration | Stack | Support status | Setup guide |
|---|-----------|-------|-----------------|-------------|
| I1 | `claude-fusion` | Claude Desktop/Cursor + MCP + Fusion (Windows) | **Reference — working today** | [`docs/setup/claude-fusion.md`](docs/setup/claude-fusion.md) |
| I2 | `lemonade-fusion` (`lemonade-cuda-fusion`) | Pi + Lemonade (CUDA) + Fusion, Windows laptop | **Current target — this milestone** | [`docs/setup/lemonade-fusion.md`](docs/setup/lemonade-fusion.md) |
| I2 | `lemonade-vulkan-fusion` | Pi + Lemonade (Vulkan) + Fusion, Windows laptop | **Next** — same guide, rerun after CUDA passes | [`docs/setup/lemonade-fusion.md`](docs/setup/lemonade-fusion.md) |
| I3 | `freecad-spike` | FreeCAD backend behind the same bridge contract, laptop | Planned/unsupported — gated dev-only spike | (dev-only; see Stage 5) |
| I4 | `strix-remote` (`lemonade-rocm-fusion-remote`, `lemonade-vulkan-fusion-remote`) | Laptop CAD + Pi ↔ Strix Halo Lemonade over LAN/SSH | Planned/unsupported | [`docs/setup/strix-remote.md`](docs/setup/strix-remote.md) |
| I5 | `strix-native` (`lemonade-rocm-freecad`, `lemonade-vulkan-freecad`) | Ubuntu Strix Halo: Lemonade + Pi + ParamAItric + FreeCAD, fully offline | Planned/unsupported | [`docs/setup/strix-native-freecad.md`](docs/setup/strix-native-freecad.md) |
| I6 | `fusion-on-linux` | Fusion via Wine or Windows VM | Parking lot | — |

Each **supported** iteration has a setup guide; I3 is a dev-only spike and I6 is
experimental. Runtime profile names follow the iteration stack:

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

Stage 2 (geometry foundations) gates only the FreeCAD spike — **I2 does not wait for
it**:

```
Stage 0 (baseline + quick wins)
   ↓
Stage 1 (local-model readiness)
   ↓
Stage 3 (I2: Lemonade + Fusion) ──────────→ Stage 6 (I4: Strix remote)
                                                        ↓
Stage 2 (geometry work, parallel) ─→ Stage 5 (I3: FreeCAD spike)
                                                        ↓
                              Stage 5 + Stage 6 ─→ Stage 7 (I5: Strix native)
                                                        ↓
                                             Stage 8 (I6, optional) → Stage 9
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

**Progress (2026-07-19):** the golden set now holds **15 cases** (8 contract, 7 safety), so
the 12–20 target is met by count; the remaining tier-3 gaps are *ambiguous request* and
*verification failure*. Also landed: the **geometry-equivalence comparator**
(`evaluations/runner/comparison.py`, `python -m evaluations.runner --compare-to claude`),
which implements the acceptance test's tolerance comparison, and the **baseline capture
driver** (`evaluations/baseline.py`). Open: **11 of 15 cases still lack hand-captured Claude
baselines** — run `python -m evaluations.baseline --status` for the current list. See
`plans/goals.md` for the work-order decomposition and `docs/dev-log.md` 2026-07-19 for
evidence.

| Task | Source | Effort |
|------|--------|--------|
| ✅ Create Lemonade integration branch (`lemonade-integration`) | Spec §11 | Quick |
| Golden evaluation set: 12–20 maintenance requests, **split into three tiers** (below). Each case records request, expected workflow, measurements, tool call, normalized args, verification facts, export type, succeed-or-fail-safely. Lives in `evaluations/`. *Harness + first 4 cases + Claude baseline done; 8–16 more cases open.* | Spec §4 | Medium |
| ✅ Evaluation-case schema + reproducibility metadata format (below) | Feedback 2026-07-11 | Small |
| ✅ Choose and add the open-source license — MIT (`LICENSE`, `pyproject.toml`) | Phase-0 backlog | Quick |
| ✅ Output filename auto-versioning (`bracket_v2.stl`) — never overwrite reprints (applies to user-visible export destinations; test/tempdir paths intentionally still overwrite) | UX #2 (partial) | Quick |
| ✅ Open-folder hand-off after export — export summary now carries export folders + per-OS open commands for the AI to suggest | UX #11 | Quick |
| ✅ Interim one-command bootstrap script (`scripts/setup.ps1` / `scripts/setup.sh`: venv → pip → `--install-addin` → `--write-claude-config -y` → `--check`) | UX #1 interim | Small |

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
complete test suite passes with no unexpected failures (CI records the current count —
do not hardcode it).

**Immediate next work unit:** the Stage-1 remainders (tool-surface gating, runtime-profile
activation, bridge auth, dispatch deadlines) are done — see "Current milestone" at the
top of this document. What remains for Stage 0 is expanding the golden set toward
12–20 cases (tier-1 contract cases plus the remaining tier-2 live parts — tube, bracket,
fillet/chamfer, enclosure — and tier-3 failure cases: ambiguous, unsupported,
verification failure) and capturing Claude baselines as cases land. This work is
deferred behind the Stage-3 vertical-slice milestone per the 2026-07-12 audit
(`plans/ponytail-audit-2026-07-12.md`), not abandoned.

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
| ✅ Optional `units` field ("mm"/"cm"/"in") normalized at the schema layer — rides along with the schema-generation work instead of being a separate pass | UX #6 folded into §5.1 | Small (as rider) |
| ✅ **Two tool profiles**: `full` (Claude, dev, large models — all tools, precise schemas) and `guided` (small models, novices — `cad_health`, `cad_recommend_workflow`, `cad_get_requirements`, `cad_build`, `cad_inspect`). Same underlying implementations; eval suite decides which the 9B model uses. | Spec §5.2 | Medium |
| ✅ **Structured errors everywhere**: `{ok, classification, stage, error, recoverable, next_step, partial_result}` — no host ever parses a traceback. Audit the most-hit validators and rewrite messages in plain language while normalizing. | Spec §5.3 + UX #4 | Small–Medium |
| ✅ **Capability-aware health**: report backend, version, mode, capabilities, workflow count; stop hardcoding "Fusion" in prompts | Spec §5.4 | Small |
| ✅ **`paramaitric doctor --profile <name>`**: extend the existing `install_paramaitric.py --check` probe to test Python env, package import, MCP startup, Lemonade endpoint + model, CAD backend reachability, bridge auth, export-dir write, one health call | Spec §5.5 (builds on shipped UX #8) | Small |
| ✅ Runtime-profile parsing and activation (`mcp_server/runtime_profiles_data/*.json`; name, export dir, tool surface, and `cad_endpoint` all wired into the running server) | Spec §3 | Small |
| ✅ **Per-run bridge authorization + browser-origin protection** (0c): per-run token via `secrets`, user-only storage, `hmac.compare_digest`, auth on by default, `Origin`/`Referer` rejection, content-type + body cap, structured 4xx envelopes | Phase-0 backlog / Spec §5.6 | Small–Medium |
| ✅ **Server-side dispatch deadlines + late-mutation policy** (0d): bounded waits with a configurable deadline; on expiry the request is cancelled via the existing token and any late completion is discarded; structured 504 timeout envelope | Phase-0 backlog / Spec §5.6 | Small |

### Stage 2 — Geometry foundations continuation (parallel track)

The pre-Lemonade roadmap's core insight stands and the spec explicitly endorses it
(§2.5): semantic selection, stable references, and a narrow operation vocabulary are
the most important internal work, and **gate the FreeCAD spike**. Selector layer,
`SelectionTrace`, live Fusion validation, and richer edge diagnostics have landed;
what remains:

| Task | Source | Effort |
|------|--------|--------|
| Attribute pinning with validity checks (detect stale pins after topology changes; fall back or fail closed by policy) | Phase-1 continuation | Medium |
| Written stable-reference policy (when to re-resolve semantically, pin, bookmark, or hard-fail) | Phase-1 continuation | Small |
| Narrow internal operation vocabulary (add/cut/intersect/new-body; target/mode/placement/expected-delta) — this becomes the minimal backend operation vocabulary the CAD backend protocol needs | Phase-1 continuation + Spec §11 batch 2 | Medium |

### Stage 3 — I2: Lemonade + Fusion on the NVIDIA laptop

| Task | Source | Effort |
|------|--------|--------|
| Install and validate Lemonade with CUDA; connect Pi to ParamAItric via MCP (no Pi fork — extension/provider mechanisms only) | Spec §6, §2.3 | Small |
| One golden Fusion workflow end-to-end with Qwen3.5 9B | Spec §11 | Small |
| Repeat through Vulkan (backend lives only in the profile) | Spec §6 | Quick |
| Expand to all golden cases; record per-request metrics (workflow/tool correctness, JSON validity, retries, hallucinated params, verification, export, latency, tokens) | Spec §6 | Medium |
| Test gpt-oss 20B after 9B results are recorded; optional smaller model as lower bound | Spec §6 | Small |

**Acceptance (9B):** ≥10 of the first 12 supported golden requests without manual tool
correction; **zero tolerance** for bypassing failed verification, inventing
operations, or unsafe failures; **geometry-equivalent** to the Claude baseline.

"Same geometry" means equivalent engineering invariants — never identical files,
topology IDs, entity tokens, or feature ordering:

- bounding dimensions within tolerance
- body count
- volume within tolerance
- expected holes/cuts/features present
- expected placement
- same verification tier passed
- valid STEP/STL export

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

### Stage 5 — I3: FreeCAD feasibility spike (gated by Stage 2)

Limited backend-contract spike, **not** a port. FreeCAD backend speaks the same bridge
contract (`/health`, `/command`, `/cancel`, `/capabilities`) with ~10 initial commands
(document/sketch/rectangle/circle/extrude/cut/inspect/export STL+STEP/save native).

1. **Process model first**: run FreeCAD as a separate FreeCAD-owned bridge process
   (`ParamAItric MCP server → HTTP → FreeCAD bridge process → FreeCAD API/FreeCADCmd`),
   keeping FreeCAD's Python environment away from the ParamAItric venv. Prove, in
   order: health response → create document → create one named solid → save `.FCStd`
   → export STEP/STL → close and reopen the document → resolve the named object
   again. This isolates installation and Python-runtime problems from workflow
   problems. **Small–Medium**
2. Write the CAD backend protocol (`cad_backends/protocol.py`) from the Stage-2
   operation vocabulary. **Medium**
3. Port exactly one workflow: **plate with centered hole** → valid `.FCStd` + `.STEP` +
   `.STL`, bounding box, volume, body count, hole verification. **Medium**
4. Only after success: **simple L-bracket** (multi-stage, edge/face selection, fillet). **Medium**

**Proceed when:** shared workflows run without backend branching, backend code stays
behind the interface, dimensions match, exports validate, failures use the same
structured error format, and the native doc is **testably editable**: changing a named
source parameter and recomputing actually updates the body.
**Stop when:** workflows need `if fusion / if freecad` branching, one basic workflow
forces MCP/agent rewrites, semantic selectors can't express stable geometry IDs, native
docs are unreliable, or the spike starts interfering with Fusion reliability work.
A stopped spike still delivers the true porting boundary.

### Stage 6 — I4: Strix Halo remote inference

CAD stays on the laptop; only inference moves. Install Lemonade on Strix Halo Ubuntu,
run ROCm first (Lemonade's recommendation for Strix), then Vulkan, CPU as diagnostic
fallback. Run the identical golden set; compare laptop vs Strix results. This isolates
hardware inference testing from CAD migration. **Small–Medium**

### Stage 7 — I5: Native Linux offline stack

Move the FreeCAD backend to Ubuntu (only if the Stage-5 spike passed). Target:
**no cloud model, no Autodesk, no Windows** — native CAD document + STEP + STL, same
evaluation and verification contract as the laptop. This is the strongest offline
claim and the headline product configuration. **Medium**

### Stage 8 — I6: Fusion-on-Linux experiments (optional, non-blocking)

Only after the native path is understood. Wine first (test startup, auth, graphics,
add-in loading, loopback bridge, main-thread events, export, update survival);
Windows VM as last resort. Failure here does not block anything. **Small–Large,
exploratory**

### Stage 9 — Packaging

- **Development packaging:** Python env, Pi integration, profiles, prompts, doctor,
  model setup instructions, Fusion add-in installer, FreeCAD backend when viable,
  evaluation suite.
- **Product packaging:** embeddable Lemonade, guided model download, one-command
  startup, automatic hardware/backend detection, Windows installer + Linux
  package/AppImage, offline docs, health dashboard, export history, backend selection.
  The `.mcpb` one-click Claude Desktop extension (old UX #1) becomes the
  `claude-fusion` flavor of this same packaging effort. **Large**

---

## Repository direction

Introduce directories incrementally as working implementations emerge — do **not**
move existing Fusion files to cosmetically match:

```
cad_backends/ (protocol.py, fusion/, freecad/, mock/)
local_app/    (prompts/, pi_extension/, doctor/)
mcp_server/   (runtime_profiles_data/, ...)
evaluations/  (cases/, expected/, results/, runner/)
scripts/      (start_windows.ps1, start_linux.sh, connect_strix.ps1, run_evaluations.py)
docs/         (LEMONADE_INTEGRATION.md, LOCAL_MODEL_EVALUATION.md, CAD_BACKEND_PROTOCOL.md, FREECAD_SPIKE.md)
```

## Standing rules

- Deterministic CAD logic stays outside the LLM: the model understands, selects,
  gathers, populates, interprets, explains — it never generates arbitrary scripts,
  guesses safety-critical dimensions, bypasses verification, continues past failed
  checks, or invents operations.
- Safety failures are zero-tolerance in every evaluation; pass thresholds are tunable,
  safety is not.
- Workflow count and primitive count are not progress metrics; selector determinism,
  diagnostic quality, and eval pass rates are.
- The official Autodesk Fusion MCP connector remains monitor-only (decision 2026-06-13);
  it becomes an adapter target only if it exposes a queryable topology surface.

## Where the old backlogs went

| Old doc | Disposition |
|---------|-------------|
| `NEXT_PHASE_PLAN.md` Phase 0 | Done items recorded there. License, bridge auth (0c), and dispatch deadlines (0d) landed → Stages 0–1 above. Module-size cleanup (0j) stays opportunistic and open. |
| `NEXT_PHASE_PLAN.md` Phase 1 | → Stage 2 (attribute pinning, reference policy, op vocabulary). |
| `NEXT_PHASE_PLAN.md` Phases 2–5 (workflow hardening, intake, local UI, threads/patterns/loft) | Deferred behind Stages 1–3; intake pieces that help small models moved into Stage 4. Local `/ui` and capability expansion resume after I2 is proven. |
| `UX_ROADMAP.md` | #1 → Stages 0 (interim script) + 9 (packaging); #2 → 0 (versioning) + 4 (iteration flow); #3, #9, #10, #12 → Stage 4; #4 → Stage 1 (structured errors); #6 → Stage 1 (schema fidelity); #5, #7, #8 shipped; #11 → Stage 0. |
| `NEXT_RESEARCH_PLAN.md` / `RESEARCH_TRACKS.md` | Research already converted to the Stage-2 implementation slice; remaining questions ride with their stages. Decision history preserved in archive + `docs/dev-log.md`. |
| `FUSION_HARDWARE_TASKLIST.md` / `FUSION_VALIDATION_NEXT_STEPS.md` | Completed live-validation checklists (2026-07-02 evidence in dev-log). The golden evaluation set (Stage 0) replaces ad-hoc hardware checklists. |
| `DEVELOPMENT_PLAN.md` | Legacy pointer; removed 2026-07-12 (this roadmap is the single source). |
