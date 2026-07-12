<p align="center">
  <img src="assets/images/readmelogo.png" alt="ParamAItric" width="800"/>
</p>

# ParamAItric

AI-assisted CAD for functional parametric designs.

ParamAItric is a CAD tool for creating functional parts from structured dimensions and requirements.

It uses constrained MCP tools, staged workflows, and geometry verification instead of open-ended CAD automation. The current backend is Autodesk Fusion 360, with local-model and additional CAD-backend support in development.

The goal is not full autonomous CAD. The goal is a reliable path from structured intent to editable Fusion geometry for useful mechanical work — especially utility and maintenance parts: brackets, plates, covers, adapters, handles, and other small replacement parts that are simple to model but expensive or slow to procure.

ParamAItric is intended to help operators, technicians, and hobbyists generate functional replacement parts and brackets, but the current setup is still developer-style. Today it requires a local repo clone, Python environment setup, Fusion add-in installation, and MCP client configuration. **New users should start with the [installation guide](INSTALL.md), which walks through setup and building your first part step by step.**

## What It Includes

- Fusion add-in bridge (loopback HTTP plus Fusion main-thread execution)
- MCP server for input validation, workflow orchestration, and verification
- Read-only inspection tools for body, face, and edge geometry
- Local regression tests and a live smoke runner
- Packaged MCP stdio entrypoint for desktop hosts (Claude Desktop, Cursor, etc.)

## Current Product Shape

Today, ParamAItric is best understood as:

- a local Fusion 360 add-in
- a local MCP server launched from a repo clone
- a validated workflow library for dependable small mechanical parts

That makes the current experience suitable for builders, testers, and early adopters. It is not yet packaged as a one-click consumer install.

## Project Direction

The project direction is to keep the CAD core narrow and reliable while making installation and daily use much simpler for non-developers.

Near-term product direction:

- keep MCP tools as the stable backend contract
- add prompt-style entrypoints on top of those tools for easier host UX
- package ParamAItric as a Claude Desktop extension or similar one-click MCP install
- reduce or remove the need for users to manage Python environments manually
- make Fusion add-in setup and first-run health checks easier to understand

The target user flow should look more like:

1. install ParamAItric in Claude Desktop with one click
2. enable the Fusion add-in
3. ask for a part in plain language
4. review and export the result

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

## Getting started

ParamAItric currently runs as a local Fusion 360 add-in plus a local MCP server launched from a repo clone. Setup takes about 15 minutes and you only do it once.

**[INSTALL.md](INSTALL.md) is the single setup guide.** It covers prerequisites, the one-command bootstrap (`scripts/setup.ps1` / `scripts/setup.sh`), the manual step-by-step install, connecting your AI client, making your first part in plain language, and printing it.

The flow, in short:

1. Clone the repo and create a Python virtual environment.
2. Install and run the Fusion 360 add-in.
3. Point your MCP client (Claude Desktop, Cursor, etc.) at the local server.
4. Ask for a part in plain language, then review and export it.

See [INSTALL.md](INSTALL.md) for the exact commands.

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
- [ROADMAP.md](ROADMAP.md): the single canonical roadmap — iterations, stages, and where old plans went
- [docs/Lemonade Integration Specification.pdf](docs/Lemonade%20Integration%20Specification.pdf): local-LLM (Lemonade + Pi) integration spec driving the current direction
- [docs/setup/](docs/setup/): per-iteration setup guides (claude-fusion today; lemonade-fusion, strix-remote, strix-native planned)
- Superseded planning docs are preserved under [docs/archive/planning/](docs/archive/planning/)
- [docs/dev-log.md](docs/dev-log.md): execution evidence, validation results, and durable rationale changes

Internal working notes:
- [internal/freeform-architecture.md](internal/freeform-architecture.md): freeform session contract and architecture note
- [internal/test-recipes.md](internal/test-recipes.md): temporary structured and freeform recipe corpus used for validation sessions

<p align="center">
  <img src="assets/images/small-logo.png" alt="ParamAItric logo" width="200"/>
</p>
