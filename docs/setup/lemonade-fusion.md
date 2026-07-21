# Setup — Iteration I2: `lemonade-fusion` (Windows laptop, local model)

> Support status: **current target** (Finding 5) — this is the iteration the current
> ROADMAP.md milestone is built around. The MCP-side plumbing it depends on (runtime
> profile activation including `cad_endpoint`, guided tool surface, per-run bridge auth,
> dispatch deadlines, doctor) is implemented. The stack is now installed and the model
> side is verified (Lemonade 10.10.0 serves a GGUF on the CUDA backend), and the
> prewired Pi harness ships in the repo (`.pi/`, `pi/`). What has **not** yet happened
> is one full natural-language request driven through Pi -> Lemonade/Qwen -> guided MCP
> -> Fusion end-to-end — see "Current blockers" in `ROADMAP.md`.

Everything runs on one Windows laptop with an NVIDIA GPU:

```
Windows laptop
├── Fusion + ParamAItric add-in     (unchanged from claude-fusion)
├── ParamAItric MCP server          (unchanged)
├── Pi                              (agent host, replaces Claude Desktop)
└── Lemonade                        (local model server)
```

## Prerequisites

1. A working `claude-fusion` install ([guide](claude-fusion.md)) — it stays installed;
   it is the regression baseline.
2. NVIDIA GPU with current drivers (CUDA first; Vulkan tested second).
3. Lemonade Server — https://lemonade-server.ai (standalone server install).
4. Pi agent host. **Do not fork Pi**; use its extension and model-provider mechanisms
   only.

## Pin before this guide is executable

This guide is not executable until the following are named and recorded (fill in at
implementation time; they become part of the reproducibility metadata):

| Item | Value |
|------|-------|
| Pi version | `@earendil-works/pi-coding-agent` 0.80.6 (npm global) |
| Lemonade version | Lemonade Server 10.10.0 (winget `AMD.LemonadeServer`), CUDA backend `llamacpp:cuda` (build `sm_120`, Blackwell/RTX 50-series) |
| Pi MCP adapter / ParamAItric Pi extension used | `pi-mcp-adapter` (`pi install npm:pi-mcp-adapter`) reading the repo's `.pi/mcp.json` |
| Exact Pi installation command | `npm install -g @earendil-works/pi-coding-agent` then `pi install git:github.com/lemonade-sdk/lemonade-pi-plugin@main` and `pi install npm:pi-mcp-adapter` |
| Exact MCP configuration file (path + contents) | `.pi/mcp.json` in the repo root (ships in git) — registers `paramaitric` -> `python -m mcp_server.mcp_entrypoint`, `PARAMAITRIC_PROFILE=lemonade-cuda-fusion`, `directTools: true`, `toolPrefix: none` |
| Exact Lemonade model-provider configuration | Lemonade Pi plugin (`lemonade-sdk/lemonade-pi-plugin`); register via `pi` -> `/login` -> Lemonade -> accept `http://localhost:13305`, dummy API key |
| ParamAItric working directory | repo root (the launcher sets `PARAMAITRIC_HOME` and runs Pi from there) |
| Pi general filesystem/shell tools enabled? | **No** — the harness launches with `--no-builtin-tools --no-context-files --no-skills`, so only the five `cad_*` tools are exposed (contest/demo mode by default) |
| Health-check command | `paramaitric doctor --profile lemonade-cuda-fusion` (implemented; run it and record the output here) |
| Known-good test prompt | `Make a 40 mm square spacer 10 mm thick.` (spacer golden case) |

The prewired harness lives in the repo: `.pi/SYSTEM.md`, `.pi/mcp.json`, and
`pi/paramaitric-pi.ps1` (launcher). See [`pi/README.md`](../../pi/README.md).

**Contest/demo mode:** disable unrelated agent tools and expose only the ParamAItric
CAD surface — safer behavior and fewer irrelevant choices for the 9B model.

## Serving the model on Lemonade

Install Lemonade (`winget install AMD.LemonadeServer`), start it (`LemonadeServer.exe`,
listens on `:13305`), and install the CUDA backend:

```
lemonade backends install llamacpp:cuda
```

Pull a model. A model that Lemonade lists by name pulls directly
(`lemonade pull Qwen3-8B-GGUF`). For a Hugging Face GGUF that is not in Lemonade's
catalog (e.g. a Qwen3.5 9B build), register it as a custom user model with an explicit
checkpoint + recipe — match the `:TAG` to the exact quant file you want:

```
lemonade pull user.Qwen3.5-9B --checkpoint main unsloth/Qwen3.5-9B-MTP-GGUF:Q4_K_M --recipe llamacpp
```

It loads on the CUDA backend (GPU). Confirm with `lemonade status` (model `Device`
should be `gpu`) and a quick completion against `http://localhost:13305/api/v1/chat/completions`.
Note: Qwen3 is a *thinking* model — the harness sets `--thinking off`; if you call the
API directly, prefix prompts with `/no_think` or give a generous `max_tokens`, or a
tiny budget returns empty text. If an MTP GGUF fails to load, fall back to a plain
`Qwen3.5-9B` GGUF.

## Steps

1. Serve the model on Lemonade (above), and point Pi's provider at it via the Lemonade
   Pi plugin (`pi` -> `/login` -> **Lemonade** -> accept `http://localhost:13305`).
2. Use the prewired harness (see [`pi/README.md`](../../pi/README.md)): it connects Pi
   to the ParamAItric MCP server (`python -m mcp_server.mcp_entrypoint`) via
   `pi-mcp-adapter` and `.pi/mcp.json`, exposing only the guided `cad_*` tools.
3. Launch: `./pi/paramaitric-pi.ps1` (interactive) or
   `./pi/paramaitric-pi.ps1 -Prompt "Make a 40 mm square spacer 10 mm thick." -Json`
   (headless, JSON event stream for eval capture).
4. Select the runtime profile `lemonade-cuda-fusion` (via environment variable `PARAMAITRIC_PROFILE` or `--profile` flag) and the
   **guided** tool profile (small-model surface: `cad_health`,
   `cad_recommend_workflow`, `cad_get_requirements`, `cad_build`, `cad_inspect`).
5. Verify with `paramaitric doctor --profile lemonade-cuda-fusion` (checks env,
   import, MCP startup, Lemonade endpoint + model, Fusion bridge, auth, export dir,
   one health call).
6. Run one golden workflow end-to-end, then the full evaluation set
   (`python -m evaluations.runner`).
7. Switch the profile to `lemonade-vulkan-fusion` and rerun the identical tests.
   The backend lives **only** in the profile — no code changes.

## Model order

1. Qwen3.5 9B → 2. gpt-oss 20B → 3. optional smaller model as lower bound.
CPU backend is a diagnostic fallback only.

## Acceptance

≥10 of the first 12 supported golden requests without manual tool correction; never
bypasses failed verification, never invents operations, fails safely on
invalid/unsupported; same final verified geometry as the Claude baseline.
