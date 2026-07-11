# UX Roadmap — Novice Friction Backlog

Target user: someone with little or no experience with AI, CLI, or Fusion 360 who needs a
simple replacement part, wants it made in Fusion, and wants a file ready for 3D printing.

Shipped in the July 2026 UX pass (commit `0ca3719`): user-visible export locations with a
default `Documents/ParamAItric Exports` folder and bare-filename support, units/export
guidance on every `create_*` tool description, a guided replacement-part intake prompt
(`cad_request`), `user_next_step` slicer hand-off in workflow results, `--install-addin`
auto-linking, and a novice `QUICKSTART.md`.

This file is the backlog of what was identified but **not** built. Ordered by expected
friction removed per unit of effort.

---

## Tier 1 — Highest impact

### 1. One-click install packaging (.mcpb Claude Desktop extension)
The single biggest remaining barrier. Today's install still needs Git, Python, a venv, and
a terminal. Package the MCP server as a Claude Desktop extension (`.mcpb`) with bundled
Python runtime so "install ParamAItric" is one click. The add-in link step
(`--install-addin`) stays, but the extension's first-run flow can invoke it.
Interim step with most of the value: a single `setup.ps1` / `setup.sh` bootstrap that does
clone → venv → pip install → `--install-addin` → `--write-claude-config` in one command.
**Effort:** Large (interim script: Small).

### 2. Iterate-on-last-part flow
Replacement parts rarely fit on the first print. Store the last workflow's validated spec
(per session or on disk) and support delta requests — "make the hole 1 mm bigger" —
without re-eliciting every dimension. Auto-version output filenames (`bracket_v2.stl`)
so reprints never overwrite and users can compare attempts.
**Effort:** Medium. Filename versioning alone: Small.

### 3. Printability guardrails before building
Novices don't know what won't print. At schema or workflow level, warn (not block) on:
walls thinner than ~0.08 cm, holes smaller than ~0.2 cm, features below typical nozzle
resolution, and unprintable aspect ratios. Return warnings in the result so the AI relays
them ("this wall will be fragile — want 1 mm more?").
**Effort:** Medium.

---

## Tier 2 — Meaningful polish

### 4. Novice-readable error audit
The export-path error was rewritten in plain language; the other ~200 `ValueError`
messages in `schemas.py` / `geometry_utils.py` were not. Audit the most-hit validators
(hole position, edge clearance, slot placement) and rewrite them so the AI can relay them
verbatim ("the hole is too close to the edge — move it at least 0.4 cm in").
**Effort:** Small–Medium, incremental.

### 5. Photo-based measurement intake
Claude hosts can see images. Extend the intake prompt: user photographs the broken part
next to a ruler or on grid paper; the AI reads approximate dimensions and confirms them.
No server code needed — this is prompt work plus a documented measuring technique in
QUICKSTART. Pairs well with the reference catalog (Phase 3c in NEXT_PHASE_PLAN).
**Effort:** Small.

### 6. mm-native inputs at the schema layer
Tool descriptions now teach the AI to convert mm→cm, but a silent 10x error still ruins a
part. Stronger fix: schemas accept an optional `units` field ("mm" | "cm" | "in") and
normalize internally, making the conversion mechanical instead of conversational.
Touches every spec class — sequence after Phase 2 workflow hardening to avoid churn.
**Effort:** Medium–Large.

### 7. First-run onboarding surface
A `getting_started` tool (or richer `health` response) that reports setup state in novice
language: bridge mode, what "mock" means ("Fusion isn't open yet — open it and I upgrade
automatically"), where exports go, and two example first prompts. Gives the AI something
concrete to say the very first time a user connects.
**Effort:** Small.

---

## Tier 3 — Nice to have

### 8. Doctor improvements in the install script
`--check` novice mode that explains failures in sentences rather than rows; detect whether
Fusion is running and the add-in is listening (ping the loopback `/health`) so setup
problems are diagnosed from one place.
**Effort:** Small.

### 9. 3MF export option
STL has no embedded units; some slicers guess wrong. Offer 3MF alongside STL where the
Fusion export manager supports it.
**Effort:** Small–Medium.

### 10. Replacement-part preset library
Curated parametric presets for the most common household/shop replacement parts (shelf
pins, drawer glides, appliance feet, knob blanks, hose clamps) with typical dimension
ranges. Feeds and is fed by the Phase 3c reference catalog.
**Effort:** Medium, content-heavy.

### 11. Open-folder hand-off
After export, optionally open the exports folder (or tell the AI the exact per-OS command
to suggest). Small, but closes the last gap between "file exists" and "user found it."
**Effort:** Small.

### 12. QUICKSTART visuals
Screenshots or short GIFs for the three moments novices stall: the Fusion Add-Ins dialog,
the Claude Desktop MCP indicator, and the first exported file in the exports folder.
**Effort:** Small, needs manual capture.

---

## Sequencing notes

- Items 1 and 6 are the two structural investments; everything else is incremental.
- Items 2, 3, and 4 compound: iteration + printability warnings + readable errors is what
  makes the *second* print succeed, which is where novices actually quit.
- Items 5, 7, 11, 12 are cheap wins suitable for filler sessions.
- Cross-references: NEXT_PHASE_PLAN Phase 3 (intake/discovery) covers recommend_workflow
  and the reference catalog; Phase 4 (local UI) may absorb items 7 and 11 if the `/ui`
  entrypoint lands first.
