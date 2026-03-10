<p align="center">
  <img src="readmelogo.png" alt="ParamAItric" width="800"/>
</p>

# ParamAItric

CAD with questionable intelligence.

ParamAItric is a tool-focused AI-assisted CAD layer for Autodesk Fusion 360.

It exposes a constrained MCP interface for reliable parametric part generation, using validated workflow stages instead of open-ended CAD automation. 

**Not a programmer? No problem.** ParamAItric is designed to help operators, technicians, and hobbyists generate functional replacement parts and brackets. **[Read the full Installation Guide for beginners here.](INSTALL.md)**

## What It Includes

- Fusion add-in bridge (loopback HTTP plus Fusion main-thread execution)
- MCP server for input validation, workflow orchestration, and verification
- Read-only inspection tools for body, face, and edge geometry
- Local regression tests and a live smoke runner
- Packaged MCP stdio entrypoint for desktop hosts (Claude Desktop, Cursor, etc.)

## Current Capability (Broad)

Validated workflow families currently cover:

- flat utility parts (spacers, plates, holes, slots, recesses)
- bracket family (plain, mounting-hole, filleted, chamfered)
- enclosure and lid paths (open box, matched lid, shelled enclosure)
- cylindrical and revolve-driven utility parts (solid/hollow cylinders, socketed handle-style parts)

## Operating Model

Each workflow follows the same reliability contract:

1. validate schema before CAD operations
2. execute explicit stages in order
3. verify geometry at milestones
4. stop on failed verification with structured failure context
5. export STL from the validated body

---

## Quick Start (For Advanced Users)

*For step-by-step instructions with explanations, see [INSTALL.md](INSTALL.md).*

**1. Set up the Python Environment**
```bash
git clone https://github.com/your-username/paramAItric.git
cd paramAItric
python -m venv .venv

# Activate venv
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -e .[dev]
```

**2. Start the Fusion 360 Bridge**
Open Fusion 360 -> Utilities -> Scripts and Add-Ins -> Click the green `+` next to Add-Ins -> Select the `fusion_addin` folder in this repo -> Click `Run`.

**3. Configure your MCP Client (e.g., Claude Desktop)**
Add the following to your `claude_desktop_config.json` (adjust paths for your OS/directory):
```json
{
  "mcpServers": {
    "paramaitric": {
      "command": "C:\\absolute\\path\\to\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.mcp_entrypoint"],
      "cwd": "C:\\absolute\\path\\to\\paramAItric"
    }
  }
}
```

**4. Run Tests / Smoke Check**
```bash
pytest
python scripts/fusion_smoke_test.py --workflow spacer
```

---

## Canonical docs

- [INSTALL.md](INSTALL.md): Comprehensive setup guide for all skill levels.
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): product goals, scope, operating modes, and success criteria
- [ARCHITECTURE.md](ARCHITECTURE.md): system boundaries, execution model, and safety constraints
- [HOST_INTEGRATION.md](HOST_INTEGRATION.md): intended MCP host integration model and transport direction
- [WORKFLOW_STRATEGY.md](WORKFLOW_STRATEGY.md): how workflow capability should expand
- [BEST_PRACTICES.md](BEST_PRACTICES.md): living workflow and prompting contract
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md): current roadmap, validated state, and active priorities
- [docs/dev-log.md](docs/dev-log.md): execution evidence and validation log

<p align="center">
  <img src="small logo.png" alt="ParamAItric logo" width="200"/>
</p>
