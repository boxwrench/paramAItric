<#
.SYNOPSIS
  Launch a locked-down ParamAItric CAD agent on Pi + Lemonade.

.DESCRIPTION
  Starts Pi from the repo root with the ParamAItric harness:
    - system prompt replaced by .pi/SYSTEM.md (CAD operator)
    - built-in tools (read/bash/edit/write/grep/find/ls) disabled
    - context files and skills disabled
    - only the ParamAItric guided MCP tools (cad_health / cad_recommend_workflow
      / cad_get_requirements / cad_build / cad_inspect) available, via
      pi-mcp-adapter reading .pi/mcp.json
    - Qwen thinking disabled for crisp tool calls

  Prerequisites (one-time, see pi/README.md):
    1. Lemonade Server running with the model pulled and the CUDA backend.
    2. `pi install npm:pi-mcp-adapter`  and  the Lemonade Pi plugin installed.
    3. `pi` -> `/login` -> Lemonade (registers the provider + models).

.PARAMETER Prompt
  If supplied, runs headless (non-interactive) and prints the result.

.PARAMETER Model
  Lemonade model id as registered (default: user.Qwen3.5-9B).

.PARAMETER Json
  With -Prompt, emit the Pi JSON event stream (for eval capture).

.EXAMPLE
  .\pi\paramaitric-pi.ps1
  .\pi\paramaitric-pi.ps1 -Prompt "Make a 40x40x10 mm spacer."
  .\pi\paramaitric-pi.ps1 -Prompt "Make a 40 mm square spacer 10 mm thick." -Json
#>
param(
  [string]$Prompt,
  [string]$Model = "user.Qwen3.5-9B",
  [switch]$Json
)
$ErrorActionPreference = "Stop"

# Repo root is the parent of this script's folder (pi/).
$Root = Split-Path -Parent $PSScriptRoot
$env:PARAMAITRIC_HOME = $Root

# Make the venv's python the one the MCP adapter spawns for the CAD server.
$venvScripts = Join-Path $Root ".venv\Scripts"
if (Test-Path $venvScripts) { $env:Path = "$venvScripts;$env:Path" }

# Deterministic / offline-friendly startup.
$env:PI_SKIP_VERSION_CHECK = "1"

Set-Location $Root

# Locked harness flags. .pi/SYSTEM.md is auto-loaded as the project system prompt.
$piArgs = @(
  "--provider", "lemonade",
  "--model", $Model,
  "--thinking", "off",
  "--no-builtin-tools",
  "--no-context-files",
  "--no-skills",
  "--approve"           # trust project .pi/ files (SYSTEM.md, mcp.json) for this run
)

if ($Prompt) {
  if ($Json) { $piArgs += @("--mode", "json") }
  else       { $piArgs += @("-p") }
  pi @piArgs $Prompt
} else {
  pi @piArgs
}
