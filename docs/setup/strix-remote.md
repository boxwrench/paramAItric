# Setup — Iteration I4: `strix-remote` (laptop CAD + remote AMD inference)

> Status: **planned — Roadmap Stage 6.** Requires a working I2 (`lemonade-fusion`)
> laptop first. CAD stays on the laptop; only inference moves to the Strix Halo box.

```
Windows laptop                          Strix Halo (Ubuntu)
├── Fusion + add-in                     └── Lemonade + local model
├── ParamAItric MCP server                  (ROCm → Vulkan → CPU-diagnostic)
└── Pi  ──── LAN or SSH tunnel ────────────▶
```

This stage isolates AMD inference-hardware testing from any CAD migration.

## Prerequisites

1. Working I2 laptop ([guide](lemonade-fusion.md)).
2. Strix Halo machine on Ubuntu with ROCm-capable drivers.
3. Network path from laptop to Strix (same LAN or SSH tunnel).

## Steps

1. Install Lemonade on the Strix box; pull the same models used in I2 (Qwen3.5 9B
   first). Start with the **ROCm** backend (Lemonade's recommendation for Strix
   Point/Halo), Vulkan as fallback.
2. Expose the Lemonade endpoint to the laptop (LAN bind or SSH tunnel —
   ⏳ `scripts/connect_strix.ps1`).
3. On the laptop, switch the runtime profile to `lemonade-rocm-fusion-remote`; only
   `model_endpoint` and `inference_backend` change. No workflow, MCP, or Fusion
   changes.
4. ⏳ `paramaitric doctor --profile lemonade-rocm-fusion-remote` to verify the remote
   endpoint, model availability, and the local Fusion bridge.
5. Run the **identical golden evaluation set** used in I2; repeat through Vulkan;
   compare laptop-vs-Strix results (correctness must match; latency/token metrics may
   differ).

## Acceptance

Same evaluation contract as I2. Any correctness difference between local-CUDA and
remote-ROCm/Vulkan runs is a finding to investigate, not to tolerate.
