<#
.SYNOPSIS
  Run the I2 vertical slice headless and capture a self-documenting evidence bundle.

.DESCRIPTION
  Drives the prewired ParamAItric Pi harness (Pi + Lemonade/Qwen -> guided MCP ->
  Fusion) for one success prompt and one fail-safely prompt in Pi's JSON event-stream
  mode, and records the reproducibility metadata the ROADMAP acceptance calls for.

  Writes an evidence folder: i2-evidence/<timestamp>/ containing
    metadata.json      reproducibility metadata (commit, versions, model, GPU, ...)
    doctor.txt         `paramaitric doctor --profile lemonade-cuda-fusion` output
    lemonade.txt       `lemonade status` (loaded model, device, recipe)
    success.jsonl      Pi JSON events for the success request
    fail_safely.jsonl  Pi JSON events for the invalid request
    exports.txt        listing of the STL export folder after the run
    run.md             human-readable summary tying it together

  Prerequisites: the harness is set up (pi/README.md) and Lemonade is serving the
  model with the CUDA backend, Fusion + add-in are running, and Pi is logged in to
  the Lemonade provider (`/login`).

.EXAMPLE
  .\pi\run-i2-evidence.ps1
  .\pi\run-i2-evidence.ps1 -Model user.Qwen3.5-9B
#>
param(
  [string]$Model = "user.Qwen3.5-9B",
  [string]$SuccessPrompt = "Make a 40 mm square spacer 10 mm thick.",
  [string]$FailPrompt = "Make a spacer 40 mm wide, 40 mm tall, and -5 mm thick.",
  [string]$OutDir
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Launcher = Join-Path $PSScriptRoot "paramaitric-pi.ps1"
$Bin = Join-Path $env:LOCALAPPDATA "lemonade_server\bin"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if (-not $OutDir) { $OutDir = Join-Path $Root "i2-evidence\$Stamp" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Safe([scriptblock]$b) { try { & $b } catch { "ERR: $($_.Exception.Message)" } }

Write-Host "Collecting reproducibility metadata..."
$gpu = Safe { Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match 'NVIDIA' } | Select-Object -First 1 }
$lemStatus = Safe { & "$Bin\lemonade.exe" status 2>&1 | Out-String }
$lemStatus | Out-File (Join-Path $OutDir "lemonade.txt") -Encoding utf8

$meta = [ordered]@{
  timestamp          = (Get-Date).ToString("o")
  paramaitric_commit = (Safe { git -C $Root rev-parse HEAD }).Trim()
  paramaitric_branch = (Safe { git -C $Root rev-parse --abbrev-ref HEAD }).Trim()
  pi_version         = (Safe { (cmd /c "pi --version 2>&1") | Select-Object -First 1 }).ToString().Trim()
  lemonade_version   = (Safe { (& "$Bin\lemonade.exe" --version 2>&1) | Select-Object -First 1 }).ToString().Trim()
  model              = $Model
  tool_profile       = "guided"
  runtime_profile    = "lemonade-cuda-fusion"
  inference_backend  = "llamacpp:cuda"
  hardware           = $gpu.Name
  driver_version     = $gpu.DriverVersion
  temperature        = 0
  thinking           = "off"
  success_prompt     = $SuccessPrompt
  fail_prompt        = $FailPrompt
  notes              = "quantization/context_size: see lemonade.txt (server-reported). Fill any blanks by hand."
}
$meta | ConvertTo-Json -Depth 4 | Out-File (Join-Path $OutDir "metadata.json") -Encoding utf8

Write-Host "Running doctor..."
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
Safe { & $venvPy -m mcp_server.doctor --profile lemonade-cuda-fusion 2>&1 | Out-String } |
  Out-File (Join-Path $OutDir "doctor.txt") -Encoding utf8

Write-Host "Running SUCCESS request through Pi (JSON mode)..."
Safe { & $Launcher -Model $Model -Prompt $SuccessPrompt -Json 2>&1 | Out-String } |
  Out-File (Join-Path $OutDir "success.jsonl") -Encoding utf8

Write-Host "Running FAIL-SAFELY request through Pi (JSON mode)..."
Safe { & $Launcher -Model $Model -Prompt $FailPrompt -Json 2>&1 | Out-String } |
  Out-File (Join-Path $OutDir "fail_safely.jsonl") -Encoding utf8

$exportDir = Join-Path $env:USERPROFILE "Documents\ParamAItric Exports"
Safe { Get-ChildItem $exportDir -Filter *.stl -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object Name, Length, LastWriteTime |
       Format-Table -AutoSize | Out-String } |
  Out-File (Join-Path $OutDir "exports.txt") -Encoding utf8

$runMd = @"
# I2 evidence run - $Stamp

- ParamAItric: $($meta.paramaitric_commit) ($($meta.paramaitric_branch))
- Pi: $($meta.pi_version)   Lemonade: $($meta.lemonade_version)
- Model: $($meta.model)   Backend: $($meta.inference_backend)   Thinking: $($meta.thinking)
- Hardware: $($meta.hardware)   Driver: $($meta.driver_version)

Files: metadata.json, doctor.txt, lemonade.txt, success.jsonl, fail_safely.jsonl, exports.txt

## Reviewer checklist
- [ ] success.jsonl: model called cad_health -> cad_recommend_workflow ->
      cad_get_requirements -> cad_build, with correct normalized args and no invented tools.
- [ ] cad_build returned ok:true with verification matching the requested dimensions.
- [ ] An STL appears in exports.txt with a fresh timestamp.
- [ ] fail_safely.jsonl: the invalid request was rejected with a structured error and
      NO geometry was produced.
- [ ] No manual tool correction was needed.
"@
$runMd | Out-File (Join-Path $OutDir "run.md") -Encoding utf8

Write-Host ""
Write-Host "Evidence bundle written to: $OutDir"
Get-ChildItem $OutDir | Select-Object Name, Length | Format-Table -AutoSize
