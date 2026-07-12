# Setup — Iteration I2: `lemonade-fusion` (Windows laptop, local model)

> Status: **Roadmap Stage 1 complete.** This guide has been updated to reflect implemented profile features.

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
| Pi version | TBD |
| Lemonade version | TBD |
| Pi MCP adapter / ParamAItric Pi extension used | TBD |
| Exact Pi installation command | TBD |
| Exact MCP configuration file (path + contents) | TBD |
| Exact Lemonade model-provider configuration | TBD |
| ParamAItric working directory | TBD |
| Pi general filesystem/shell tools enabled? | TBD — **disable for contest/demo mode** |
| Health-check command | TBD (`paramaitric doctor --profile lemonade-cuda-fusion` once it lands) |
| Known-good test prompt | TBD (spacer golden case) |

**Contest/demo mode:** disable unrelated agent tools and expose only the ParamAItric
CAD surface — safer behavior and fewer irrelevant choices for the 9B model.

## Steps

1. Install Lemonade; pull the first model: **Qwen3.5 9B (GGUF)**. Start the server
   with the CUDA backend and confirm the endpoint answers (default assumed
   `http://127.0.0.1:13305/api/v1`).
2. Point Pi's model provider at the Lemonade endpoint.
3. Connect Pi to the ParamAItric MCP server the same way any host does
   (`python -m mcp_server.mcp_entrypoint`, see [`HOST_INTEGRATION.md`](../../HOST_INTEGRATION.md)).
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
