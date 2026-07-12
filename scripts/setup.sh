#!/usr/bin/env bash
# One-command bootstrap for ParamAItric (Linux / macOS).
#
# Run this from a cloned checkout. It creates or reuses .venv, upgrades pip,
# installs ParamAItric in editable mode, links the Fusion 360 add-in (macOS
# only -- Fusion 360 has no native Linux build), writes the Claude Desktop
# MCP config, and finishes with a setup health check. Safe to re-run.
#
# Env vars:
#   SKIP_ADDIN=1          skip the Fusion add-in link step
#   SKIP_CLAUDE_CONFIG=1  skip writing the Claude Desktop MCP config
set -euo pipefail

step() { printf '\n==> %s\n' "$1"; }
warn() { printf 'WARNING: %s\n' "$1" >&2; }
fail() { printf 'ERROR: %s\n' "$1" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f "$REPO_ROOT/pyproject.toml" ]; then
    fail "This does not look like a ParamAItric checkout (no pyproject.toml found at $REPO_ROOT)."
fi

step "Checking for Python 3.11+"
PYTHON_BIN=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done
if [ -z "$PYTHON_BIN" ]; then
    fail "Python was not found on PATH. Install Python 3.11+ and re-run this script."
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
PY_MAJOR="$(echo "$PY_VERSION" | cut -d. -f1)"
PY_MINOR="$(echo "$PY_VERSION" | cut -d. -f2)"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    fail "Python 3.11+ is required, found $PY_VERSION."
fi

VENV_DIR="$REPO_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    step "Creating virtual environment at .venv"
    "$PYTHON_BIN" -m venv "$VENV_DIR" || fail "Failed to create the virtual environment."
else
    step "Reusing existing virtual environment at .venv"
fi

if [ ! -x "$VENV_PYTHON" ]; then
    fail "Virtual environment python not found at $VENV_PYTHON after creation."
fi

step "Upgrading pip"
"$VENV_PYTHON" -m pip install --upgrade pip || fail "Failed to upgrade pip in .venv."

step "Installing ParamAItric (pip install -e .)"
"$VENV_PYTHON" -m pip install -e "$REPO_ROOT" || fail "Failed to install ParamAItric. Check the pip output above."

INSTALL_HELPER="$REPO_ROOT/scripts/install_paramaitric.py"
UNAME_S="$(uname -s)"
SKIP_ADDIN="${SKIP_ADDIN:-0}"

if [ "$SKIP_ADDIN" != "1" ]; then
    case "$UNAME_S" in
        Darwin)
            step "Linking the Fusion 360 add-in"
            if ! "$VENV_PYTHON" "$INSTALL_HELPER" --install-addin; then
                warn "Could not link the Fusion add-in automatically. Retry later with:"
                printf '  .venv/bin/python scripts/install_paramaitric.py --install-addin\n' >&2
            fi
            ;;
        *)
            step "Skipping Fusion add-in link (Fusion 360 does not run on $UNAME_S)"
            ;;
    esac
else
    step "Skipping Fusion add-in link (SKIP_ADDIN=1)"
fi

SKIP_CLAUDE_CONFIG="${SKIP_CLAUDE_CONFIG:-0}"
if [ "$SKIP_CLAUDE_CONFIG" != "1" ]; then
    step "Writing Claude Desktop MCP config"
    if ! "$VENV_PYTHON" "$INSTALL_HELPER" --write-claude-config -y; then
        warn "Could not update the Claude Desktop config automatically. Retry later with:"
        printf '  .venv/bin/python scripts/install_paramaitric.py --write-claude-config\n' >&2
    fi
else
    step "Skipping Claude Desktop config (SKIP_CLAUDE_CONFIG=1)"
fi

step "Running final setup check"
set +e
"$VENV_PYTHON" "$INSTALL_HELPER" --check
CHECK_EXIT=$?
set -e

echo
if [ "$CHECK_EXIT" -eq 0 ]; then
    echo "Setup complete."
else
    warn "Setup finished with warnings/failures above."
    echo "Run this any time to see full details:"
    echo "  .venv/bin/python scripts/install_paramaitric.py --check"
fi

exit "$CHECK_EXIT"
