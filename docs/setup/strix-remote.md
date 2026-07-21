# Setup — Iteration I4: `strix-remote` (laptop CAD + remote AMD inference)

> Support status: **planned/unsupported** (Roadmap Stage 6, Finding 5) — out of scope
> until the I2 vertical-slice milestone in `ROADMAP.md` passes. Requires a working I2
> (`lemonade-fusion`) laptop first. CAD stays on the laptop; only inference moves to the
> Strix Halo box. The `lemonade-rocm-fusion-remote` / `lemonade-vulkan-fusion-remote`
> profiles may parse but are not release-ready.

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
3. SSH access from the laptop to the Strix box.

## Steps

1. Install Lemonade on the Strix box; pull the same models used in I2 (Qwen3.5 9B
   first). Start with the **ROCm** backend (Lemonade's recommendation for Strix
   Point/Halo), Vulkan as fallback.
2. Expose the Lemonade endpoint to the laptop. **Default: SSH tunnel** (keeps
   Lemonade bound to loopback on the Strix box; ⏳ `scripts/connect_strix.ps1` wraps
   this):

   ```powershell
   ssh -N -L 13306:127.0.0.1:13305 user@strix-host
   ```

   The laptop-side port is **13306**, not 13305 — the laptop's own local Lemonade
   instance (from I2) is still listening on 13305. Using a different port means you
   can switch between local NVIDIA and remote Strix inference without stopping
   either server.

   *Advanced alternative:* bind Lemonade to the LAN interface directly — only on a
   trusted network, since the endpoint is unauthenticated.
3. On the laptop, switch the runtime profile to `lemonade-rocm-fusion-remote`
   (Vulkan run: `lemonade-vulkan-fusion-remote`) with
   `"model_endpoint": "http://127.0.0.1:13306/api/v1"`; only `model_endpoint` and
   `inference_backend` change. No workflow, MCP, or Fusion changes.
4. ⏳ `paramaitric doctor --profile lemonade-rocm-fusion-remote` to verify the remote
   endpoint, model availability, and the local Fusion bridge.
5. Run the **identical golden evaluation set** used in I2; repeat through Vulkan;
   compare laptop-vs-Strix results (correctness must match; latency/token metrics may
   differ).

## Acceptance

Same evaluation contract as I2. Any correctness difference between local-CUDA and
remote-ROCm/Vulkan runs is a finding to investigate, not to tolerate.
