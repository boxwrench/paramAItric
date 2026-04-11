<p align="center">
  <img src="assets/images/readmelogo.png" alt="ParamAItric" width="800"/>
</p>

# ParamAItric

CAD with questionable intelligence.

ParamAItric is a tool-focused AI-assisted CAD layer for Autodesk Fusion 360.

It exposes a constrained MCP interface for reliable parametric part generation, using validated workflow stages instead of open-ended CAD automation.

The goal is not full autonomous CAD. The goal is a reliable path from structured intent to editable Fusion geometry for useful mechanical work — especially utility and maintenance parts: brackets, plates, covers, adapters, handles, and other small replacement parts that are simple to model but expensive or slow to procure.

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

## Operating Modes

### Work Mode

The default. Deterministic part creation where predictability matters more than breadth.

- small tool surface
- strong validation
- explicit stage ordering
- verification checkpoints between milestones
- clear failures with partial progress preserved

### Utility Operations Mode

Automation around an existing design rather than geometry creation. Lower-risk operational style.

- low-risk operations
- clear reporting on what changed
- stronger file and path controls

### Creative Mode

Later-stage exploratory modeling after the reliable core is strong enough. Useful for evaluation and edge testing, but not the primary value proposition.

## Design Philosophy

- staged workflows outperform one-shot requests
- validation before CAD operations matters
- verification after each major step matters
- human correction loops are a normal operating model
- more complex workflows should be built from proven smaller workflow paths
- keep the workflow surface narrow and explicit
- prefer typed operations over broad natural-language commands
- preserve clean partial results when a workflow fails
- expand only after the previous slice is stable
- let real parts drive the next workflow gaps
- keep the user in control of risky or destructive actions

---

## Quick Start (For Advanced Users)

*For step-by-step instructions with explanations, see [INSTALL.md](INSTALL.md).*

**1. Set up the Python Environment**
```bash
git clone https://github.com/boxwrench/paramAItric.git
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

- [docs/README.md](docs/README.md): short guide to current canon versus archived historical docs.
- [INSTALL.md](INSTALL.md): Comprehensive setup guide for all skill levels.
- [ARCHITECTURE.md](ARCHITECTURE.md): system boundaries, execution model, and safety constraints
- [HOST_INTEGRATION.md](HOST_INTEGRATION.md): intended MCP host integration model and transport direction
- [BEST_PRACTICES.md](BEST_PRACTICES.md): living workflow and prompting contract
- [docs/VERIFICATION_POLICY.md](docs/VERIFICATION_POLICY.md): adopted verification trust tiers and runtime-vs-audit policy
- [docs/CSG_CHECKLIST.md](docs/CSG_CHECKLIST.md): short deterministic workflow checklist for planning and review
- [docs/FREEFORM_PLAYBOOK.md](docs/FREEFORM_PLAYBOOK.md): guided freeform operating model, verification rules, and promotion standards
- [docs/FREEFORM_CHECKLIST.md](docs/FREEFORM_CHECKLIST.md): short guided freeform session checklist
- [docs/RESEARCH_TRACKS.md](docs/RESEARCH_TRACKS.md): synthesized tracker for major research lanes and why the roadmap changed
- [docs/NEXT_PHASE_PLAN.md](docs/NEXT_PHASE_PLAN.md): active roadmap, now led by internal geometry foundations
- [docs/NEXT_RESEARCH_PLAN.md](docs/NEXT_RESEARCH_PLAN.md): targeted research sequence for selector, reference, and workflow-architecture questions
- [docs/dev-log.md](docs/dev-log.md): execution evidence, validation results, and durable rationale changes

Internal working notes:
- [internal/freeform-architecture.md](internal/freeform-architecture.md): freeform session contract and architecture note
- [internal/test-recipes.md](internal/test-recipes.md): temporary structured and freeform recipe corpus used for validation sessions

<p align="center">
  <img src="assets/images/small-logo.png" alt="ParamAItric logo" width="200"/>
</p>
