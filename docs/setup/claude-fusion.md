# Setup — Iteration I1: `claude-fusion` (current, working)

The reference implementation: Claude Desktop (or Cursor) → MCP → ParamAItric server →
Fusion add-in on Windows. This is the quality baseline every other iteration is
measured against.

**This iteration is fully documented already:**

- Novice guide: [`QUICKSTART.md`](../../QUICKSTART.md) (~15 min, plain language)
- Full guide with all options: [`INSTALL.md`](../../INSTALL.md)
- Host-agnostic integration principles: [`HOST_INTEGRATION.md`](../../HOST_INTEGRATION.md)

## Condensed flow

1. Install Fusion 360, Python 3.11+, Git, Claude Desktop.
2. ```bash
   git clone https://github.com/boxwrench/paramAItric.git
   cd paramAItric
   python -m venv .venv && .venv\Scripts\activate
   pip install -e .
   python scripts/install_paramaitric.py --install-addin
   python scripts/install_paramaitric.py --write-claude-config
   ```
3. In Fusion: Utilities → Scripts and Add-Ins → **FusionAIBridge** → Run (tick "Run on
   Startup"). Restart Claude Desktop.
4. Verify: ask Claude to *"Call the ParamAItric getting_started tool."*
   Troubleshoot with `python scripts/install_paramaitric.py --check`.

Exports land in `Documents\ParamAItric Exports`.

## Profile

Once runtime profiles land (Roadmap Stage 1), this iteration is
`local_app/profiles/claude-fusion.json`; until then, MCP host config carries the setup.
