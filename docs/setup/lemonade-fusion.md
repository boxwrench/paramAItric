# Setup — Iteration I2: `lemonade-fusion` (Windows laptop, local model)

> Status: **planned — Roadmap Stage 3.** This guide is written ahead of implementation
> so setup decisions are explicit; steps marked ⏳ depend on Stage 0–1 work landing.

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

## Steps

1. Install Lemonade; pull the first model: **Qwen3.5 9B (GGUF)**. Start the server
   with the CUDA backend and confirm the endpoint answers (default assumed
   `http://127.0.0.1:13305/api/v1`).
2. Point Pi's model provider at the Lemonade endpoint.
3. Connect Pi to the ParamAItric MCP server the same way any host does
   (`python -m mcp_server.mcp_entrypoint`, see [`HOST_INTEGRATION.md`](../../HOST_INTEGRATION.md)).
4. ⏳ Select the runtime profile `lemonade-cuda-fusion` (`local_app/profiles/`) and the
   **guided** tool profile (small-model surface: `cad_health`,
   `cad_recommend_workflow`, `cad_get_requirements`, `cad_build`, `cad_inspect`).
5. ⏳ Verify with `paramaitric doctor --profile lemonade-cuda-fusion` (checks env,
   import, MCP startup, Lemonade endpoint + model, Fusion bridge, auth, export dir,
   one health call). Until doctor lands: `install_paramaitric.py --check` + a manual
   request against the Lemonade endpoint.
6. Run one golden workflow end-to-end, then the full evaluation set
   (⏳ `scripts/run_evaluations.py`).
7. Switch the profile to `lemonade-vulkan-fusion` and rerun the identical tests.
   The backend lives **only** in the profile — no code changes.

## Model order

1. Qwen3.5 9B → 2. gpt-oss 20B → 3. optional smaller model as lower bound.
CPU backend is a diagnostic fallback only.

## Acceptance

≥10 of the first 12 supported golden requests without manual tool correction; never
bypasses failed verification, never invents operations, fails safely on
invalid/unsupported; same final verified geometry as the Claude baseline.
