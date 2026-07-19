# Target B Validation Plan — Test 1, Test 2, Compose

> Purpose: prove or kill target B (Qwen-class local model + FreeCAD, Strix Halo 128GB, Vulkan)
> without the intermediate iteration ladder. The two unknowns — model competence and CAD
> backend — are tested independently and in parallel. Compose only after both pass.
> Invariant 2 (model hosting and CAD execution are independent choices) is what makes
> this decomposition valid.

---

## Test 1 — Local model contract competence

**Question answered:** can a local MoE model correctly drive the ParamAItric tool surface?
No CAD, no Fusion, no FreeCAD. Model reasoning only.

**Hardware/stack:** Strix Halo, Ubuntu, llama.cpp Vulkan (RADV, current Mesa), served via
Lemonade. ROCm not required for this test.

### Prerequisites
- [ ] Mock backend answers `/health` and `/command` well enough to satisfy the MCP server
      for tier-1 (contract) cases — no geometry, canned verification responses.
- [ ] Constrained decoding wired: compile the Pydantic-derived tool schemas (already
      generated for MCP schema fidelity) into llama.cpp grammar / json_schema constraints
      so invalid JSON and hallucinated field names are impossible by construction.
- [ ] Runtime profile added: `lemonade-vulkan-mock` (or reuse an existing profile with
      backend=mock). `paramaitric doctor --profile lemonade-vulkan-mock` passes.

### Models under test
Per ROADMAP Stage 3, in order:

| Tier | Model | Why |
|---|---|---|
| Baseline | Qwen3.5 9B | spec'd first model; establishes the lower bound |
| Quality | gpt-oss 20B | spec'd second model; run after 9B results are recorded |

**Optional third row, if the spec'd models disappoint:** an MoE in the 30B-A3B class.
Rationale — Strix Halo is bandwidth-bound, so a model activating ~3B params per token
can generate faster than a dense 9B while carrying more total capacity. This is a
hardware-fit argument, not a reason to skip the spec'd models; run them first and let
the measured prefill/generation numbers decide whether the MoE row is worth adding.

### Matrix
Each model × each tool profile (`guided`, `full`) × all available tier-1 contract cases
(currently 4; grow the set as cases land — the matrix reruns cheaply).
Fixed: temperature 0, context ≥ 16k for `full` (the 34-tool schema block will not fit
comfortably in 8k), reproducibility metadata recorded per run exactly as specced in
ROADMAP Stage 0.

### Metrics (per run)
- workflow recommendation correct (vs Claude baseline)
- tool choice correct
- argument correctness after normalization (constrained decoding removes syntax errors;
  what remains is *semantic* error — wrong values, wrong fields chosen — which is the
  real signal)
- retries needed
- structured-error handling on the failure cases (invalid dims, bridge unavailable):
  model must surface the error and stop, not invent a workaround
- latency: prefill t/s and generation t/s separately (prefill dominates with large
  schema prompts; this decides guided-vs-full in practice)

### Pass / fail
- **Pass:** either spec'd model matches the Claude baseline on all contract cases in at
  least one profile, zero safety violations (no bypassed failures, no invented
  operations). Qwen3.5 9B passing `guided` is the cheapest win; gpt-oss 20B passing
  `full` is the stronger result.
- **Fail:** neither spec'd model matches baseline on contract cases even with
  constrained decoding — at which point run the optional MoE row before concluding.
  If that also fails, target B pauses; target A proceeds on cloud
  models and the golden set keeps growing until better local models exist. Do not
  proceed to Compose on a failed Test 1.

---

## Test 2 — FreeCAD backend process-model proof

**Question answered:** does a FreeCAD bridge speaking the existing contract actually work?
Driver is **Claude** (known-good model), so every failure is unambiguously the backend's.

**Scope guard:** this is ROADMAP Stage 5 step 1 only. It does **not** require the Stage 2
operation vocabulary — that gates the *workflow port*, not this proof.

### Architecture under test
```
ParamAItric MCP server → HTTP → FreeCAD bridge process → FreeCAD API / FreeCADCmd
```
FreeCAD (1.x — the toponaming mitigation matters later for stable references) runs as a
separate FreeCAD-owned process with its own Python. The ParamAItric venv never imports
FreeCAD. Bridge implements the same endpoints as the Fusion add-in: `/health`,
`/command`, `/cancel`, `/capabilities`.

### Proof sequence (in order, each step must pass before the next)
1. `/health` returns capability-aware identity (backend=freecad, version, mode)
2. create document
3. create one *named* solid (single pad/box is fine)
4. save native `.FCStd`
5. export STEP and STL; both open in a viewer and report sane bbox/volume
6. close and reopen the document
7. re-resolve the named object from step 3 by name/reference — not by index
8. structured failure check: send one invalid command; bridge returns the standard
   `{ok, classification, stage, error, recoverable, next_step}` shape, never a traceback

### Pass / stop
- **Pass:** all 8 steps, on the Strix box (Linux-native is the point). Then and only
  then: write `cad_backends/protocol.py` from the Stage-2 vocabulary and port
  plate-with-centered-hole.
- **Stop (per existing roadmap stop rules):** any step requires `if fusion / if freecad`
  branching above the bridge, named-object re-resolution is unreliable, or the native
  doc isn't testably editable. A stopped Test 2 still delivers the true porting boundary.

---

## Compose gate

Run only when Test 1 and Test 2 have both passed.

- Stack: whichever model passed Test 1 (Vulkan) + FreeCAD bridge, one runtime profile,
  on the Strix box.
- Run the full golden set. Acceptance = existing Stage 3 bar: ≥10 of first 12 supported
  requests without manual tool correction; zero tolerance on safety; geometry-equivalent
  to Claude baseline per the existing invariant list (bbox/volume/body count/features,
  never file identity).
- **Triage on composed failure:** re-run the failing case with (a) Claude + FreeCAD and
  (b) local model + mock. Whichever leg reproduces the failure owns it. Only if *neither*
  leg reproduces it is the interaction itself the bug — that is the one situation where
  standing up lemonade+Fusion as a third reference configuration earns its keep.

---

## Optimizations (priority order)

1. **Constrained decoding** (prereq of Test 1, listed here because it's also a product
   feature): schema-compiled grammars eliminate the JSON-validity failure class for every
   local model, permanently. Highest-leverage single change for target B.
2. **Mock backend → CI.** Once the mock exists for Test 1, wire tier-1 contract cases
   into GitHub Actions. Every PR then regression-tests workflow recommendation, schema
   validity, and error shape with zero Fusion/FreeCAD dependency.
3. **Automated geometry equivalence via `trimesh`.** Volume, bbox, watertightness,
   component count on exported STLs — automates most of the tier-2 comparison against
   Claude baselines without opening a CAD app. Feeds both Test 2 step 5 and Compose.
4. **Profile/context tuning for prefill.** On bandwidth-limited unified memory, prefill
   cost of the 34-tool `full` schema block is the dominant latency term. Measure it in
   Test 1; if `full` prefill is painful, `guided` becomes the default local profile for
   latency reasons (not capability reasons) and `full` stays for cloud hosts.
   Vulkan for interactive generation; note ROCm remains an option specifically for
   batch eval runs (prefill-heavy) if eval throughput ever matters — keep it out of the
   product path.
5. **Security items gate Track A shipping, not a backlog:** per-run bridge auth with
   browser-origin protection, and dispatch deadlines with a late-mutation policy. A
   host-generic loopback server is a DNS-rebinding/CSRF target; close both before the
   `.mcpb` or any Codex-facing docs go out.
6. **Track A generic-host work** (parallel to all of the above, small): `--print codex`
   in the installer, one full workflow exercised from a non-Claude MCP host, `.mcpb`
   package for the claude-fusion flavor, Codex config snippet in INSTALL. Ships real
   users while B validates.
7. **Tag v0.1** once the golden set hits its target size, so `paramaitric_commit` in
   reproducibility metadata points at named releases instead of loose SHAs.
8. **Roadmap edit:** delete I6; mark I2/I4 as diagnostic configurations invoked only by
   the Compose triage rule; I3+I5 collapse into Test 2 → Compose. The dependency graph
   becomes: Stage 0/1 remainders → {Test 1 ∥ Test 2} → Compose → packaging.
