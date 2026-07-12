# ParamAItric Pi harness

A prewired, opinionated [Pi](https://pi.dev) agent that drives ParamAItric's
guided CAD tools with a local model served by [Lemonade](https://lemonade-server.ai).
The point: **we control the harness, so we control the system prompt and the tool
schema.** A small local model (e.g. Qwen3.5-9B) only ever sees five well-described
CAD tools and a task-specific system prompt — nothing else in its world.

This harness targets the `lemonade-cuda-fusion` runtime profile (Windows + NVIDIA).

## What's in the box

| File | Role |
|------|------|
| `.pi/SYSTEM.md` | Replaces Pi's default prompt with the ParamAItric CAD-operator prompt (auto-loaded when Pi runs from the repo root). |
| `.pi/mcp.json` | Registers the ParamAItric MCP server (`python -m mcp_server.mcp_entrypoint`, guided profile) with `pi-mcp-adapter`; `directTools: true` + `toolPrefix: none` surface the five `cad_*` tools as first-class Pi tools. |
| `pi/paramaitric-pi.ps1` | Launcher. Runs Pi from the repo root with built-in tools, context files, and skills disabled, Qwen thinking off, and only the CAD tools available. Interactive or headless (`-Prompt`, `-Json`). |

## One-time setup

1. **Lemonade Server** — install and start it, install the CUDA backend, and pull
   the model (see `docs/setup/lemonade-fusion.md` for the exact `lemonade pull`
   command and how to register a custom Hugging Face GGUF such as
   `unsloth/Qwen3.5-9B-MTP-GGUF`).
2. **Pi + extensions**:
   ```powershell
   npm install -g @earendil-works/pi-coding-agent
   pi install git:github.com/lemonade-sdk/lemonade-pi-plugin@main   # Lemonade as a Pi provider
   pi install npm:pi-mcp-adapter                                    # MCP -> Pi tools
   ```
3. **Register the provider** — start `pi`, run `/login`, pick **Lemonade**, accept
   the discovered `http://localhost:13305`, and enter a non-empty API key (a dummy
   like `lemonade` is fine). This registers the served models.
4. **Fusion** — have Fusion open with the ParamAItric add-in running (the bridge on
   `127.0.0.1:8123`), same as the `claude-fusion` baseline.

## Run it

```powershell
# Interactive:
.\pi\paramaitric-pi.ps1

# Headless (prints result):
.\pi\paramaitric-pi.ps1 -Prompt "Make a 40 mm square spacer 10 mm thick."

# Headless with JSON event stream (for eval capture):
.\pi\paramaitric-pi.ps1 -Prompt "Make a 40x40x10 mm spacer." -Json

# Override the model id if you registered it under a different name:
.\pi\paramaitric-pi.ps1 -Model user.Qwen3.5-9B
```

## First-run note (MCP tool cache)

`pi-mcp-adapter` populates its direct-tool cache in the background on the first
session, so the `cad_*` tools may not appear as first-class tools until the cache
warms. If the model reports no CAD tools on the very first run, run `/mcp reconnect
paramaitric` once in an interactive session (or just send a second prompt) and the
five tools will register. The `keep-alive` lifecycle in `.pi/mcp.json` keeps the
server (and the Fusion bridge session) connected.

## Why these flags

- `--no-builtin-tools` removes `read/bash/edit/write/grep/find/ls` — a CAD operator
  needs none of them, and a small model shouldn't be tempted by them.
- `--no-context-files --no-skills` keeps the model's world to exactly the system
  prompt plus the CAD tools.
- `--thinking off` stops Qwen3 from spending its token budget on hidden reasoning
  (which otherwise returns empty tool calls).
- `--approve` trusts the project `.pi/` files for the run (non-interactive modes
  don't prompt for trust).

To tighten further to exactly five tools once the cache is warm, set
`"disableProxyTool": true` in `.pi/mcp.json` (hides the `mcp` proxy tool).

## Capture evidence for the I2 record

`pi/run-i2-evidence.ps1` runs the success + fail-safely prompts headless (Pi JSON
event stream) and writes a self-documenting bundle to `i2-evidence/<timestamp>/`
(metadata, doctor output, both event streams, export listing, and a reviewer
checklist). Use it during the real I2 run so the milestone is self-documenting:

```powershell
./pi/run-i2-evidence.ps1
```

See [`i2-evidence/README.md`](../i2-evidence/README.md).
