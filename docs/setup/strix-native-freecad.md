# Setup — Iteration I5: `strix-native` (fully offline Linux stack)

> Status: **planned — Roadmap Stage 7.** Gated on the FreeCAD spike (Roadmap Stage 5)
> passing and I4 (`strix-remote`) results. This is the strongest-offline-claim
> configuration: **no cloud model, no Autodesk, no Windows.**

```
Strix Halo (Ubuntu)
├── Lemonade (ROCm → Vulkan)
├── Pi
├── ParamAItric MCP server
└── FreeCAD backend (same bridge contract as Fusion)
```

## Prerequisites

1. FreeCAD spike passed its acceptance criteria (no backend branching in shared
   workflows; editable native docs; validated STEP/STL; same structured errors).
2. I4 inference results recorded on this hardware.
3. FreeCAD installed on Ubuntu.

## Steps

1. Install ParamAItric on Ubuntu (venv + `pip install -e .`;
   ⏳ `scripts/start_linux.sh`).
2. ⏳ Install/enable the FreeCAD backend (`cad_backends/freecad/`) speaking the bridge
   contract: `GET /health`, `POST /command`, `POST /cancel`, `GET /capabilities`.
3. Install Pi and point it at the local Lemonade endpoint (ROCm backend).
4. Select profile `lemonade-rocm-freecad` (or `lemonade-vulkan-freecad`).
5. ⏳ `paramaitric doctor --profile lemonade-rocm-freecad`.
6. Run the golden evaluation set with the same verification contract as the laptop.

## Acceptance

- No cloud model connection, no Autodesk application, no Windows host required.
- Native `.FCStd` document (editable) plus `.STEP` and `.STL` output per part.
- Same evaluation and verification contract as the laptop iterations.

## Related experiments (I6, non-blocking)

Fusion-on-Linux via Wine is experimental (Autodesk does not support Linux); a Windows
VM is last-resort. Neither blocks this iteration — for an integrated-GPU Strix system,
native Windows or dual boot is a cleaner Fusion test environment than a VM.
