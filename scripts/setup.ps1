<#
.SYNOPSIS
    One-command bootstrap for ParamAItric (Windows / Fusion 360).
.DESCRIPTION
    Run this from a cloned checkout. It creates or reuses .venv, upgrades pip,
    installs ParamAItric in editable mode, links the Fusion 360 add-in, writes
    the Claude Desktop MCP config, and finishes with a setup health check.
    Safe to re-run at any time.
.PARAMETER SkipAddin
    Skip linking the Fusion 360 add-in.
.PARAMETER SkipClaudeConfig
    Skip writing/merging the Claude Desktop MCP config (--write-claude-config).
.EXAMPLE
    .\scripts\setup.ps1
.EXAMPLE
    .\scripts\setup.ps1 -SkipAddin
#>
[CmdletBinding()]
param(
    [switch]$SkipAddin,
    [switch]$SkipClaudeConfig
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Message)
    Write-Host "WARNING: $Message" -ForegroundColor Yellow
}

function Fail {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

# Repo root = this script's directory's parent.
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
    Fail "This does not look like a ParamAItric checkout (no pyproject.toml found at $RepoRoot)."
}

Write-Step "Checking for Python 3.11+"
$PythonCmd = $null
foreach ($candidate in @("python", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $PythonCmd = $candidate
        break
    }
}
if (-not $PythonCmd) {
    Fail "Python was not found on PATH. Install Python 3.11+ from https://www.python.org/downloads/ (check 'Add python.exe to PATH'), then re-run this script."
}

$versionOutput = (& $PythonCmd --version) 2>&1
if ($versionOutput -match "(\d+)\.(\d+)\.(\d+)") {
    $verMajor = [int]$Matches[1]
    $verMinor = [int]$Matches[2]
    if ($verMajor -lt 3 -or ($verMajor -eq 3 -and $verMinor -lt 11)) {
        Fail "Python 3.11+ is required, found $versionOutput. Install a newer Python from https://www.python.org/downloads/."
    }
} else {
    Write-Warn "Could not parse Python version output '$versionOutput'; continuing anyway."
}

$VenvDir = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Step "Creating virtual environment at .venv"
    & $PythonCmd -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Fail "Failed to create the virtual environment." }
} else {
    Write-Step "Reusing existing virtual environment at .venv"
}

if (-not (Test-Path $VenvPython)) {
    Fail "Virtual environment python not found at $VenvPython after creation."
}

Write-Step "Upgrading pip"
& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Fail "Failed to upgrade pip in .venv." }

Write-Step "Installing ParamAItric (pip install -e .)"
& $VenvPython -m pip install -e $RepoRoot
if ($LASTEXITCODE -ne 0) { Fail "Failed to install ParamAItric. Check the pip output above." }

$InstallHelper = Join-Path $RepoRoot "scripts\install_paramaitric.py"

if (-not $SkipAddin) {
    Write-Step "Linking the Fusion 360 add-in"
    & $VenvPython $InstallHelper --install-addin
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Could not link the Fusion add-in automatically (see message above). Retry later with:"
        Write-Host "  .venv\Scripts\python.exe scripts\install_paramaitric.py --install-addin" -ForegroundColor Yellow
    }
} else {
    Write-Step "Skipping Fusion add-in link (-SkipAddin)"
}

if (-not $SkipClaudeConfig) {
    Write-Step "Writing Claude Desktop MCP config"
    & $VenvPython $InstallHelper --write-claude-config -y
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Could not update the Claude Desktop config automatically. Retry later with:"
        Write-Host "  .venv\Scripts\python.exe scripts\install_paramaitric.py --write-claude-config" -ForegroundColor Yellow
    }
} else {
    Write-Step "Skipping Claude Desktop config (-SkipClaudeConfig)"
}

Write-Step "Running final setup check"
& $VenvPython $InstallHelper --check
$CheckExit = $LASTEXITCODE

Write-Host ""
if ($CheckExit -eq 0) {
    Write-Host "Setup complete." -ForegroundColor Green
    Write-Host "Next: open Fusion 360 -> Utilities -> Scripts and Add-Ins -> Add-Ins -> FusionAIBridge -> Run (tick 'Run on Startup'), then restart Claude Desktop."
} else {
    Write-Warn "Setup finished with warnings/failures above."
    Write-Host "Run this any time to see full details:"
    Write-Host "  .venv\Scripts\python.exe scripts\install_paramaitric.py --check" -ForegroundColor Yellow
}

exit $CheckExit
