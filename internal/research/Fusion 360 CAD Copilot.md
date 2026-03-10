> Reference note: this file is a preserved draft and not a canonical project specification.
> Use the repo root docs for the current source of truth: `README.md`, `PROJECT_CONTEXT.md`, `ARCHITECTURE.md`, and `DEVELOPMENT_PLAN.md`.
# Building a Fusion 360 CAD Copilot on Windows with MCP and a Local HTTP Bridge

## Executive summary

A practical, high-success path to a local “CAD copilot” on a Windows gaming laptop is to keep **all CAD mutations inside Fusion’s Python runtime** (an add-in), while exposing a **small, typed, safety-gated tool surface** to whichever agent host you prefer (Claude / Gemini / Codex). The most reliable architecture is:

- **Fusion add-in** hosts a **loopback-only HTTP server** and **queues requests**.
- A **Fusion CustomEvent** drains that queue on Fusion’s UI thread (because most Fusion API calls are *not thread safe* and can crash Fusion if invoked from other threads). citeturn5view0
- A separate **Python MCP server** (stdio) exposes “CAD tools” (create_sketch, extrude, export, etc.) with **JSON Schema** and forwards those calls to the local HTTP bridge.
- The agent host (Claude/Gemini/Codex) discovers tools via MCP and chains calls. MCP is JSON-RPC based and supports **stdio** and **Streamable HTTP** transports. citeturn27view0turn27view1

This report provides a step-by-step build plan in **three modes** (Work, Utility, Creative) and **three development passes** (phase one minimal, phase two intermediate, phase three advanced), plus starter code, schemas, guardrails, tests, logging, and a roadmap for CNC prep and other expansions.

## Architecture and key implementation constraints

### Why the Fusion-side HTTP server must be “queue + custom event”
A common “gotcha” in Fusion automation is that background threads are useful for I/O (like listening on a socket), but **Fusion API calls are generally not thread safe**. Autodesk University material explicitly warns that most Fusion API calls are not thread safe and that some UI API calls can crash Fusion; it recommends **Custom Events** to communicate from a background thread to the UI thread. citeturn5view0turn5view1turn5view2

So the HTTP server thread should do *only*:
- parse/validate request,
- enqueue a job,
- trigger a CustomEvent, and
- wait for a result.

The CustomEvent handler (running on Fusion’s UI thread) should do *only*:
- execute Fusion API mutations,
- capture entity tokens/results/errors,
- respond.

This design is the single biggest factor that makes the “local HTTP bridge” approach “very likely to succeed.” citeturn5view0turn5view1turn5view2

### Reference strategy: entity tokens, not Python object pointers
Across process boundaries (MCP server ↔ Fusion add-in), you need stable references. Fusion exposes **entityToken** for many entities; you can store a token and later recover the entity with `Design.findEntityByToken`. Autodesk docs also warn token strings can differ over time and should not be directly compared; you should always resolve tokens back to entities. citeturn30search16turn30search1

### Core dataflow

```mermaid
flowchart LR
  A[Agent host\nClaude / Gemini / Codex] -->|MCP stdio\nJSON-RPC tools/call| B[Python MCP Server\nTool definitions + schemas]
  B -->|HTTP POST 127.0.0.1:7432| C[Fusion Add-in\nLocal HTTP bridge thread]
  C -->|enqueue job + fireCustomEvent| D[Fusion UI thread\nCustomEvent handler]
  D -->|Fusion API calls| E[Design state\nSketches / Features / Bodies]
  D -->|result (tokens, summaries)| C
  C -->|HTTP response| B
  B -->|tool result| A
```

MCP itself uses **JSON-RPC** and defines **stdio** (subprocess, newline-delimited messages) and **Streamable HTTP** transports; stdio is recommended whenever possible. citeturn27view0turn27view1

## Project setup and scaffolding on Windows

### Folder and repo structure (recommended)
This mirrors Autodesk University testing guidance that emphasizes project structure (tests alongside add-in) and using Python’s built-in `unittest`. citeturn17view0turn17view1

```
fusion-copilot/
  fusion_addin/
    FusionCopilot.manifest
    FusionCopilot.py              # run/stop: registers CustomEvent + starts server
    copilot_http.py               # HTTP server + request parsing (no Fusion API calls)
    dispatcher.py                 # queue + job registry + CustomEvent fire pattern
    ops/
      sketch_ops.py               # create_sketch, draw primitives, list_profiles
      feature_ops.py              # extrude, loft, fillet, chamfer, shell
      export_ops.py               # export STL/STEP
      utility_ops.py              # convert bodies→components, rename, materials (phase two/three)
    resources/                    # icons, optional palette UI
  mcp_server/
    pyproject.toml
    src/fusion_mcp/
      server.py                   # FastMCP tools -> HTTP forwarder
      http_client.py              # retries, timeouts, auth header
      schemas.py                  # centralized JSON Schema fragments
      guardrails.py               # allowlists, path restrictions, rate limits
      logging.py
    tests/
      test_schemas.py
      test_http_client.py
      test_tool_routing.py
  shared/
    tool_schemas.json             # generated snapshot of tool definitions (optional)
    examples/
      workflows.md
      prompts.md
  .gitignore
  README.md
```

### Install and run the Fusion add-in
Fusion scripts & add-ins are managed via the “Scripts and Add-Ins” dialog, can be set to run on startup, and can be linked from any folder via the dialog. citeturn25view1  
The Python add-in template uses `run(context)` and `stop(context)` as the lifecycle entrypoints. citeturn25view0

For samples and typical filesystem locations on Windows, Autodesk provides the default directories (and explains how to install samples so Fusion discovers them). citeturn33search21

### Configure your MCP host (host-agnostic)
You will run the MCP server as a **local stdio process**. All three hosts below support local MCP servers, but differ in guardrails and ergonomics:

- **Claude Code** supports adding a local stdio MCP server and describes stdio vs HTTP transport options and scopes. citeturn10view0  
- **Gemini CLI** supports MCP servers via `settings.json`, including trust/confirm behavior and include/exclude tool filtering. citeturn11view0  
- **Codex** supports MCP servers in its CLI and IDE extension, and documents configuration, allow/deny lists, and approval/sandbox controls. citeturn12view0turn12view1turn12view2  

## Phased implementation plan by mode

This section is organized as **phase one minimal**, **phase two intermediate**, **phase three advanced**. Each phase is subdivided into the three operating modes you requested: **Work**, **Utility**, **Creative**.

A key principle across all modes: MCP guidance stresses user consent and control, tool safety, and that tool invocations should have a human-in-the-loop capability—especially for sensitive or destructive operations. citeturn9view0turn27view1

### Phase one minimal

**Objective:** Verify end-to-end wiring (host → MCP → HTTP → Fusion → export) with a small tool surface that is hard to misuse.

#### Work mode
**Goals**
Build simple, reliable mechanical parts for printing: plates, brackets, spacers, simple enclosures; always end with STL export. Use only “planar sketch → extrude → fillet/chamfer optional → export.” The Fusion API is designed to let programs perform the same operations as the interactive UI. citeturn33search11turn35search14

**Required tools/endpoints (subset)**
- MCP tools: `get_design_summary`, `new_design`, `create_sketch`, `sketch_draw_center_rectangle`, `sketch_draw_circle`, `sketch_list_profiles`, `extrude_profile`, `export_model`
- HTTP: `GET /health`, `POST /v1/exec`

**Safety/guardrails**
- Only allow **NewBody** feature operations; no cut/combine.
- Export path restricted to a single base directory (e.g., `Documents\FusionCopilot\exports`).
- Rate-limit: 1 in-flight job, 5 jobs/minute.
- Require explicit approval in the host UI for `export_model` (because it writes files). MCP security guidance recommends confirmation prompts for sensitive operations and logging/audit. citeturn9view0turn26view0

**Error-recovery patterns**
- If `profiles` list is empty: return a structured error (“no closed profile”) and suggest adding constraints / closing loop.
- If token resolution fails (invalid token): tell the agent to call `get_design_summary` and re-select/create.

**Testing checklist**
- Fusion add-in starts/stops cleanly (no hang on close). Background threads can prevent Fusion/Python from closing; daemon threads may be appropriate if cleanup is minimal. citeturn5view0
- `/health` responds in <100ms.
- `new_design` creates a design document (verify active product is Design).
- Circle + rectangle sketch creates at least one profile.
- Extrude creates a body.
- Export writes STL (validate file exists). Fusion’s ExportManager sample demonstrates STL export via `exportManager.createSTLExportOptions` and `execute`. citeturn8view0

**Example end-to-end workflow (prompt + expected tool chain)**  
Prompt:
> “Make a 90mm × 40mm × 6mm mounting plate with 4 holes (Ø5mm) on a 70mm × 20mm rectangle pattern centered on origin. Export STL.”

Expected MCP call chain (illustrative):
1. `new_design()`
2. `create_sketch(plane="xy")`
3. `sketch_draw_center_rectangle(center=[0,0], width="90 mm", height="40 mm")` citeturn32search33  
4. `sketch_draw_circle(center=[-35,-10], radius="2.5 mm")`
5. `sketch_draw_circle(center=[ 35,-10], radius="2.5 mm")`
6. `sketch_draw_circle(center=[-35, 10], radius="2.5 mm")`
7. `sketch_draw_circle(center=[ 35, 10], radius="2.5 mm")`
8. `sketch_list_profiles(sketch_token=…)`
9. `extrude_profile(profile_token=…, distance="6 mm", operation="new_body")` citeturn31search0turn31search10  
10. (optional) `export_model(format="stl", …)` citeturn8view0  

#### Utility mode
**Goals**
Phase one utility tasks are “read-only + light housekeeping”: list bodies, list sketches, show tokens, basic metadata. Avoid destructive changes until phase two.

**Required tools/endpoints**
- MCP tools: `get_design_summary`, `list_entities` (read-only flavor), `export_model` (optional)
- HTTP: `GET /v1/state` (optional convenience), `POST /v1/exec`

**Safety/guardrails**
- Explicitly label tools as read-only where possible; clients may use these annotations (but treat annotations as untrusted from unknown servers). citeturn9view0turn27view1  
- No rename, no component conversion, no material changes.

**Error-recovery patterns**
- If active design is missing: return “No active design” and instruct to run `new_design` or open a design.

**Testing checklist**
- Listing does not crash on large designs (limit output size; paginate/trim).
- entityToken returned for each listed entity when available. citeturn30search16

**Example workflow**
Prompt:
> “What bodies exist in my current design? Give me tokens and bounding boxes.”

Expected chain:
1. `get_design_summary()`
2. `list_entities(kind="bodies", include_tokens=true, include_bbox=true)`

#### Creative mode
**Goals**
Phase one creative is still “safe primitives”: revolve a spline profile into a vase-like form, shell it, export.

**Required tools/endpoints**
- MCP tools: add `sketch_draw_spline_fit`, `revolve_profile`, `shell_body` (if implemented early)
- HTTP: `POST /v1/exec`

**Safety/guardrails**
- Enforce max dimensions (e.g., 250mm bounding box) to prevent runaway geometry.
- Require one confirmation before shell (can fail; may create thin-walled self-intersections).

**Error-recovery patterns**
- If revolve fails: agent should simplify spline or reduce points.

**Testing checklist**
- Spline sketch produces a profile.
- Revolve creates a surface/body.

**Example workflow**
Prompt:
> “Design a simple vase: 160mm tall, ~80mm max diameter, 2.4mm wall, export STL.”

Expected chain:
1. `new_design()`
2. `create_sketch(plane="xz")`
3. `sketch_draw_spline_fit(points=[…])`
4. `sketch_draw_line(…)` (close profile)
5. `sketch_list_profiles(…)`
6. `revolve_profile(profile_token=…, axis="y", angle="360 deg")`
7. `shell_body(body_token=…, thickness="2.4 mm")`
8. `export_model(format="stl", …)`

### Phase two intermediate

**Objective:** Make the copilot productive for real projects: robust references (entity tokens everywhere), limited destructive operations, and better geometry tools (patterns, fillets/chamfers, lofts).

#### Work mode
**Goals**
- Common mechanical patterns: bolt circles, grids, ribs, bosses.
- Add rectangular patterns and chamfers/fillets.
- Maintain predictability: still prefer sketch + extrude.

Rectangular pattern creation is demonstrated in Autodesk samples (rectangular pattern features, quantities/distances via ValueInput strings). citeturn31search17  
Chamfer edge sets accept edges and a `ValueInput`, and note that `ValueInput` strings can include units (or default units apply). citeturn36view2

**Required tools/endpoints (added)**
- MCP tools: add `pattern_rectangular`, `chamfer_edges`, `fillet_edges`
- HTTP: same `/v1/exec`

**Safety/guardrails**
- Allow `cut` extrudes only if:
  - target bodies are explicitly provided (tokens), and
  - the cut depth is bounded, and
  - user approval is required (host confirmation).
- Any timeline-affecting ops should be single “transaction” jobs (see error recovery below).

**Error-recovery patterns**
- **Transactional job pattern:** If a multi-step tool fails mid-way (e.g., pattern created but fillet fails), return a structured “partial completion” result listing what succeeded and what entity tokens were created, so the agent can decide whether to undo or continue.

**Testing checklist**
- Pattern tool creates correct count.
- Chamfer tool succeeds on a known test body edge set.
- Export produces valid STL with expected refinement options (Fusion sample shows STL export options like binary format and mesh refinement). citeturn8view0

**Example workflow**
Prompt:
> “Create a grid of 12 bosses on a plate, then chamfer all boss top edges 0.8mm.”

Expected chain:
1. `new_design()`
2. (sketch + extrude base plate)
3. (sketch boss circle + extrude boss)
4. `pattern_rectangular(entities=[boss_body_token], x_qty=…, x_spacing=…, y_qty=…, y_spacing=…)` citeturn31search17  
5. `chamfer_edges(edges=[…], distance="0.8 mm", tangent_chain=true)` citeturn36view2  

#### Utility mode
**Goals**
Automate the “CAD hygiene” tasks you cited:
- Convert bodies → components
- Standardize names
- Export STEP/STL for downstream (print/CNC)
- Prepare for CAM workflows (phase three expands)

**Required tools/endpoints (added)**
- MCP tools: `convert_bodies_to_components`, `rename_entity`, `export_model(format="step"| "stl")`

**Safety/guardrails**
- Require user approval for:
  - component conversion (it changes structure),
  - renaming large batches (over N entities),
  - exporting outside the allowed directory.
- Keep an allowlist of operations per mode. MCP best practices recommend scope minimization and careful consent for powerful local servers. citeturn26view0turn9view0

**Error-recovery patterns**
- If conversion breaks token references (some objects disappear when bodies are converted to components), instruct agent to refresh by re-listing entities and re-resolving tokens. Shell docs explicitly warn that after creating a component from a body, the original body/faces no longer exist, and you may need timeline roll or re-query. citeturn35search18

**Testing checklist**
- On a test design with multiple bodies, run conversion and verify:
  - bodies moved under separate components,
  - no duplicate names,
  - key tokens returned for new components/bodies.

**Example workflow**
Prompt:
> “Convert all bodies into components, name them with a prefix ‘CNC_’, then export STEP.”

Expected chain:
1. `get_design_summary()`
2. `list_entities(kind="bodies")`
3. `convert_bodies_to_components(body_tokens=[…], naming_rule="CNC_{index}")`
4. `export_model(format="step", target="design", path=…)` citeturn8view0  

#### Creative mode
**Goals**
Add loft-based and form-based (organic) capabilities:
- Multi-profile lofts
- Controlled splines
- Optional T-spline form feature primitives (phase three deepens)

Autodesk’s Loft Feature API Sample demonstrates creating offset construction planes and lofting profiles via `loftFeatures.createInput` and `loftSections.add(profile)`. citeturn34view1turn35search24

**Required tools/endpoints (added)**
- MCP tools: `create_construction_plane_offset`, `loft_profiles`, `sketch_draw_spline_fit`
- HTTP: same `/v1/exec`

**Safety/guardrails**
- Cap loft section count and spline point count to avoid heavy failures.
- Always return intermediate tokens (planes, sketches, profiles) so the agent can repair.

**Error-recovery patterns**
- If loft fails due to self-intersection or invalid section order: suggest reordering sections, simplifying due to typical loft robustness issues (return the section tokens and the failure).

**Testing checklist**
- Loft sample scenario succeeds end-to-end (three circles on offset planes). citeturn34view1

**Example workflow**
Prompt:
> “Make a ‘twisted’ lamp shade by lofting 4 profiles at offsets, then export STL.”

Expected chain:
1. `new_design()`
2. for each z level: `create_construction_plane_offset(base_plane="xz", offset="…")`; `create_sketch(plane_token=…)`; draw profile
3. `loft_profiles(profile_tokens=[…], is_solid=false)` citeturn34view1  
4. `export_model(format="stl", …)` citeturn8view0  

### Phase three advanced

**Objective:** “Handle pretty much anything you’d do manually” by expanding tool coverage, adding a controlled “escape hatch” for generic API calls, and hardening reliability and safety.

#### Work mode
**Goals**
- Parametric templates (user parameters)
- Feature editing
- Multi-body boolean workflows (combine/cut)
- Better export and mesh controls

At this point, you can also integrate “design rules” (min wall thickness for FDM, max overhang angles, etc.) as a *policy layer* that runs before committing geometry.

**Required tools/endpoints (added)**
- MCP tools: `set_user_parameter`, `combine_bodies`, `select_by_query`, `validate_printability_basic`, `export_model` (enhanced)
- HTTP: optionally add `POST /v1/validate` to run non-mutating validations

**Safety/guardrails**
- Two-tier tool access:
  - **“Safe set”** (common CAD operations) always available.
  - **“Power tools”** (combine/cut across many bodies, batch edits) require per-call approval in the host.
- Strong input validation and rate limiting (explicitly listed as server requirements in MCP tool security considerations). citeturn9view0turn26view0

**Error-recovery patterns**
- Add a “checkpoint” concept:
  - Before risky operations, request explicit checkpoint approval and optionally auto-save to an archive path.
  - On failure, return “recommended rollback” instructions (e.g., Undo N steps).

**Testing checklist**
- Fuzz test tool argument validation (bad units, NaNs, empty tokens).
- Regression suite of 10 canonical mechanical parts.

#### Utility mode
**Goals**
Your CNC-prep examples become first-class:
- Convert bodies → components
- Sync physical material with appearance (or set directly)
- Prepare naming, component structure, and export packages

**Required tools/endpoints**
- MCP tools: `sync_physical_material_to_appearance`, `set_physical_material`, `set_appearance`, `batch_rename`, `export_package(zip=true)`

**Safety/guardrails**
- Restrict file reads/writes. If you need to work with local files, follow the same principle Autodesk describes for their Fusion Automation API extension: sandboxed or restricted directories for file access are a real constraint in some environments, and you should design your tool policy accordingly. citeturn22view0

**Error-recovery patterns**
- If appearance/material libraries differ across installs, fall back to “closest match” with an explicit report of what changed.

**Testing checklist**
- Run on a “messy” real project: 30+ bodies, varied appearances, confirm conversion and material mapping are consistent.

#### Creative mode
**Goals**
- Organic form exploration (loft/sweep, form features)
- Controlled randomness that still produces printable solids

Fusion supports creation of a FormFeature (T-spline) via API (`formFeatures.add`). citeturn32search22

**Required tools/endpoints**
- MCP tools: `create_form_feature`, `apply_form_edit`, `thicken_surface`, `generate_variations(seed=…)`

**Safety/guardrails**
- Require a “creative budget” (max operations, max faces, max runtime).
- Always end with a “make watertight + export” step.
- Human confirmation for large topology-changing operations.

**Error-recovery patterns**
- If a creative run hits complexity limits, agent should reduce resolution parameters and retry.

**Testing checklist**
- 3 canned creative builds:
  - vase
  - lampshade
  - decorative container with embossed text

## HTTP bridge and MCP tool schemas

### HTTP contract (recommended)
Use **one** execution endpoint to keep the Fusion add-in small and extensible.

**Endpoints**
- `GET /health` → add-in version, Fusion version, active document name
- `POST /v1/exec` → execute an operation by name (validated) and return structured results

**Request envelope**
```json
{
  "requestId": "uuid-string",
  "op": "extrude_profile",
  "args": { "profileToken": "…", "distance": "6 mm", "operation": "new_body" },
  "mode": "work",
  "dryRun": false
}
```

**Response envelope**
```json
{
  "requestId": "uuid-string",
  "ok": true,
  "result": { "bodyToken": "…", "featureToken": "…", "summary": "Extruded 6 mm" },
  "error": null,
  "telemetry": { "durationMs": 1432 }
}
```

### MCP server tool definitions (first twenty tools)

MCP tools are defined with `name`, `description`, and `inputSchema` (JSON Schema). MCP’s tools spec defines listing (`tools/list`), calling (`tools/call`), tool results, and error handling. citeturn9view0turn27view1

Below is a **starter set of twenty** tools that maps cleanly to Fusion API samples and is sufficient for phase one and most of phase two. (Phase three adds “power tools” and optional generic invocation.)

> Note on schema volume: These schemas are intentionally tight. MCP security guidance recommends validating inputs, rate limiting, sanitizing outputs, logging, and explicit consent flows for sensitive ops. citeturn9view0turn26view0

#### Tool schema bundle (excerpt style, one per tool)

```json
{
  "tools": [
    {
      "name": "ping",
      "description": "Health check. Confirms the Fusion bridge is reachable.",
      "inputSchema": { "type": "object", "properties": {}, "required": [] }
    },
    {
      "name": "get_design_summary",
      "description": "Returns active design metadata and high-level entity counts.",
      "inputSchema": {
        "type": "object",
        "properties": { "includeTokens": { "type": "boolean", "default": false } },
        "required": []
      }
    },
    {
      "name": "new_design",
      "description": "Creates a new Fusion design document and makes it active.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "documentName": { "type": "string" },
          "units": { "type": "string", "enum": ["mm", "cm", "in"] }
        },
        "required": []
      }
    },
    {
      "name": "create_sketch",
      "description": "Creates a sketch on a construction plane.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "plane": { "type": "string", "enum": ["xy", "xz", "yz"] },
          "planeToken": { "type": "string", "description": "Alternative to plane enum." },
          "name": { "type": "string" }
        },
        "required": []
      }
    },
    {
      "name": "finish_sketch",
      "description": "Finishes a sketch (optional; many operations can proceed without explicit finish).",
      "inputSchema": {
        "type": "object",
        "properties": { "sketchToken": { "type": "string" } },
        "required": ["sketchToken"]
      }
    },
    {
      "name": "sketch_draw_line",
      "description": "Adds a line segment to a sketch.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "sketchToken": { "type": "string" },
          "start": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
          "end": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 }
        },
        "required": ["sketchToken", "start", "end"]
      }
    },
    {
      "name": "sketch_draw_circle",
      "description": "Adds a circle by center and radius.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "sketchToken": { "type": "string" },
          "center": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
          "radius": { "type": "string", "description": "Fusion ValueInput string, e.g. '5 mm'." }
        },
        "required": ["sketchToken", "center", "radius"]
      }
    },
    {
      "name": "sketch_draw_center_rectangle",
      "description": "Adds a center-point rectangle.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "sketchToken": { "type": "string" },
          "center": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
          "width": { "type": "string" },
          "height": { "type": "string" }
        },
        "required": ["sketchToken", "center", "width", "height"]
      }
    },
    {
      "name": "sketch_draw_arc_3pt",
      "description": "Adds a 3-point arc.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "sketchToken": { "type": "string" },
          "start": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
          "point": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
          "end": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 }
        },
        "required": ["sketchToken", "start", "point", "end"]
      }
    },
    {
      "name": "sketch_draw_spline_fit",
      "description": "Adds a fitted spline through points.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "sketchToken": { "type": "string" },
          "points": {
            "type": "array",
            "items": { "type": "array", "items": { "type": "number" }, "minItems": 2, "maxItems": 2 },
            "minItems": 3,
            "maxItems": 50
          }
        },
        "required": ["sketchToken", "points"]
      }
    },
    {
      "name": "sketch_list_profiles",
      "description": "Lists closed profiles in a sketch and returns tokens.",
      "inputSchema": {
        "type": "object",
        "properties": { "sketchToken": { "type": "string" } },
        "required": ["sketchToken"]
      }
    },
    {
      "name": "extrude_profile",
      "description": "Extrudes a profile by distance to create a body or cut. Uses Fusion input-object pattern.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "profileToken": { "type": "string" },
          "distance": { "type": "string" },
          "operation": { "type": "string", "enum": ["new_body", "cut", "join"] },
          "symmetric": { "type": "boolean", "default": false }
        },
        "required": ["profileToken", "distance", "operation"]
      }
    },
    {
      "name": "revolve_profile",
      "description": "Revolves a profile around an axis.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "profileToken": { "type": "string" },
          "axis": { "type": "string", "enum": ["x", "y", "z"] },
          "angle": { "type": "string", "default": "360 deg" },
          "operation": { "type": "string", "enum": ["new_body", "cut", "join"] }
        },
        "required": ["profileToken", "axis"]
      }
    },
    {
      "name": "loft_profiles",
      "description": "Lofts through multiple profiles (solid or surface).",
      "inputSchema": {
        "type": "object",
        "properties": {
          "profileTokens": { "type": "array", "items": { "type": "string" }, "minItems": 2, "maxItems": 10 },
          "isSolid": { "type": "boolean", "default": false }
        },
        "required": ["profileTokens"]
      }
    },
    {
      "name": "shell_body",
      "description": "Shells a body to a wall thickness.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "bodyToken": { "type": "string" },
          "thickness": { "type": "string" },
          "removeFaceTokens": { "type": "array", "items": { "type": "string" }, "default": [] }
        },
        "required": ["bodyToken", "thickness"]
      }
    },
    {
      "name": "fillet_edges",
      "description": "Adds a constant-radius fillet to edges (initial version).",
      "inputSchema": {
        "type": "object",
        "properties": {
          "edgeTokens": { "type": "array", "items": { "type": "string" }, "minItems": 1, "maxItems": 200 },
          "radius": { "type": "string" },
          "tangentChain": { "type": "boolean", "default": true }
        },
        "required": ["edgeTokens", "radius"]
      }
    },
    {
      "name": "chamfer_edges",
      "description": "Adds an equal-distance chamfer to edges.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "edgeTokens": { "type": "array", "items": { "type": "string" }, "minItems": 1, "maxItems": 200 },
          "distance": { "type": "string" },
          "tangentChain": { "type": "boolean", "default": true }
        },
        "required": ["edgeTokens", "distance"]
      }
    },
    {
      "name": "pattern_rectangular",
      "description": "Creates a rectangular pattern of entities/bodies along X/Y.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "entityTokens": { "type": "array", "items": { "type": "string" }, "minItems": 1, "maxItems": 20 },
          "xQuantity": { "type": "string" },
          "xDistance": { "type": "string" },
          "yQuantity": { "type": "string" },
          "yDistance": { "type": "string" }
        },
        "required": ["entityTokens", "xQuantity", "xDistance"]
      }
    },
    {
      "name": "convert_bodies_to_components",
      "description": "Utility: converts bodies to components (one body per component) and returns new tokens.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "bodyTokens": { "type": "array", "items": { "type": "string" }, "minItems": 1, "maxItems": 200 },
          "namingRule": { "type": "string", "default": "Component_{index}" }
        },
        "required": ["bodyTokens"]
      }
    },
    {
      "name": "export_model",
      "description": "Exports to STL or STEP using ExportManager.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "format": { "type": "string", "enum": ["stl", "step"] },
          "target": { "type": "string", "enum": ["design", "root_component", "body"] },
          "targetToken": { "type": "string" },
          "path": { "type": "string" },
          "stlBinary": { "type": "boolean", "default": true },
          "stlRefinement": { "type": "string", "enum": ["low", "medium", "high"], "default": "high" }
        },
        "required": ["format", "target", "path"]
      }
    }
  ]
}
```

**Mapping to official API evidence (examples)**
- Sketch circle + extrude pattern is shown in Joint Sample and other samples. citeturn31search0turn31search10  
- Rectangular patterns using quantities/distances via `ValueInput.createByString` are shown in sample code. citeturn31search17  
- Loft through profiles is shown in the Loft Feature API Sample. citeturn34view1  
- Exporting STL/STEP is shown in ExportManager sample code. citeturn8view0  
- Chamfer tool signatures and unit-handling behavior for `ValueInput` are documented. citeturn36view2  

### Sample MCP tool-call sequence and expected HTTP forwarding
Your MCP server receives a `tools/call` for, say, `extrude_profile`. MCP defines `tools/call` and `CallToolResult` structure. citeturn9view0  
Your MCP server forwards:

```json
POST http://127.0.0.1:7432/v1/exec
{
  "requestId": "02f6…",
  "op": "extrude_profile",
  "args": { "profileToken": "…", "distance": "6 mm", "operation": "new_body" },
  "mode": "work"
}
```

Returns:

```json
{
  "requestId": "02f6…",
  "ok": true,
  "result": { "bodyToken": "…", "featureToken": "…", "summary": "Extruded 6 mm" },
  "error": null
}
```

Then the MCP server emits an MCP result:
- `content`: one short human-readable text block
- `structuredContent`: the JSON result (recommended by MCP tools spec for structured output). citeturn9view0

## Starter code snippets

These are **snippets**, not full libraries, focused on the core patterns that make the system stable.

### Fusion add-in: HTTP server thread + CustomEvent dispatcher

Fusion add-ins use `run(context)` and `stop(context)` lifecycle hooks. citeturn25view0  
Custom events are the recommended mechanism to communicate from background threads to the UI thread. citeturn5view1turn5view2

```python
# FusionCopilot.py (snippet)
import json, threading, traceback, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
import adsk.core, adsk.fusion

EVENT_ID = "fusion_copilot_dispatch"

_app = adsk.core.Application.get()
_ui = _app.userInterface

_job_lock = threading.Lock()
_jobs = {}  # requestId -> {"op": str, "args": dict, "done": Event, "result": dict}

_custom_event = None
_custom_handler = None
_httpd = None
_http_thread = None

def _enqueue_job(op: str, args: dict) -> str:
    request_id = str(uuid.uuid4())
    done = threading.Event()
    with _job_lock:
        _jobs[request_id] = {"op": op, "args": args, "done": done, "result": None}
    _app.fireCustomEvent(EVENT_ID, request_id)  # UI-thread execution
    return request_id

class _Dispatcher(adsk.core.CustomEventHandler):
    def notify(self, args: adsk.core.CustomEventArgs):
        request_id = args.additionalInfo
        with _job_lock:
            job = _jobs.get(request_id)
        if not job:
            return
        try:
            # IMPORTANT: All Fusion API calls happen here (UI thread).
            result = execute_op(job["op"], job["args"])
            payload = {"ok": True, "result": result, "error": None}
        except Exception:
            payload = {"ok": False, "result": None, "error": traceback.format_exc()}
        with _job_lock:
            job["result"] = payload
            job["done"].set()

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return
        self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path != "/v1/exec":
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        req = json.loads(body.decode("utf-8"))
        op = req.get("op")
        args = req.get("args") or {}
        rid = _enqueue_job(op, args)

        # Wait for completion (set a timeout you like)
        with _job_lock:
            done = _jobs[rid]["done"]
        if not done.wait(timeout=60):
            resp = {"requestId": rid, "ok": False, "error": "timeout", "result": None}
        else:
            with _job_lock:
                payload = _jobs[rid]["result"]
                del _jobs[rid]
            resp = {"requestId": rid, **payload}

        out = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

def run(context):
    global _custom_event, _custom_handler, _httpd, _http_thread
    _custom_event = _app.registerCustomEvent(EVENT_ID)
    _custom_handler = _Dispatcher()
    _custom_event.add(_custom_handler)

    _httpd = HTTPServer(("127.0.0.1", 7432), _Handler)
    _http_thread = threading.Thread(target=_httpd.serve_forever, daemon=True)
    _http_thread.start()
    _ui.messageBox("Fusion Copilot bridge started on 127.0.0.1:7432")

def stop(context):
    global _httpd, _custom_event
    try:
        if _httpd:
            _httpd.shutdown()
            _httpd.server_close()
    finally:
        if _custom_event:
            _app.unregisterCustomEvent(EVENT_ID)
```

Where `execute_op(op, args)` routes to your `ops/` modules and should:
- validate args,
- use `ValueInput.createByString` for units when appropriate (samples do this widely), citeturn31search17turn34view1  
- return `entityToken` strings for created entities. citeturn30search16

### MCP server: FastMCP tool definitions forwarding to HTTP

The MCP docs recommend using the official Python SDK and show `FastMCP` with tool decorators. citeturn13view0turn13view1  
For stdio servers, never print to stdout except MCP messages; log to stderr. citeturn13view0turn27view0

```python
# mcp_server/src/fusion_mcp/server.py (snippet)
import os, json
import httpx
from mcp.server.fastmcp import FastMCP

MCP_NAME = "fusion_copilot"
FUSION_URL = os.environ.get("FUSION_COPILOT_URL", "http://127.0.0.1:7432")

mcp = FastMCP(MCP_NAME, json_response=True)

async def _call_fusion(op: str, args: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{FUSION_URL}/v1/exec", json={"op": op, "args": args, "mode": "work"})
        r.raise_for_status()
        return r.json()

@mcp.tool()
async def ping() -> dict:
    """Health check: confirm the bridge is reachable."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{FUSION_URL}/health")
        r.raise_for_status()
        return {"status": "ok"}

@mcp.tool()
async def create_sketch(plane: str = "xy", name: str | None = None) -> dict:
    """Create a sketch on a construction plane."""
    resp = await _call_fusion("create_sketch", {"plane": plane, "name": name})
    if not resp.get("ok"):
        raise RuntimeError(resp.get("error"))
    return resp["result"]

if __name__ == "__main__":
    # Most hosts will run this as a stdio MCP server.
    mcp.run(transport="stdio")
```

To add tools quickly, keep the Fusion side “op router” stable and expand the MCP side with small wrappers.

## Guardrails, error recovery, and reliability engineering

### Why you should not “expose everything” by default
It’s technically possible to expose a *generic* “call any Fusion API method” tool (and third-party projects explicitly market that approach), but MCP guidance and host security models strongly push toward **scope minimization** and explicit consent, because tool invocation is effectively “code execution with side effects.” citeturn26view0turn9view0turn28view2

Practical reasons to limit tools early:
- **Safety:** Smaller surface = fewer ways to delete/overwrite designs.
- **Reliability:** LLMs plan better with a constrained, well-described toolbox; huge generic APIs increase hallucinated calls and fragile object graphs.
- **Debuggability:** When something fails, you want small, typed operations with clear error messages (MCP spec emphasizes validating inputs and structured error handling). citeturn9view0

A good compromise in phase three is:
- Keep a **“generic_invoke”** tool behind a strict approval policy and allowlist (e.g., only specific namespaces/methods).
- Prefer expanding the typed toolset over time for common workflows.

### Host-side approvals and safety controls
Different hosts offer different guardrail knobs:

- **Codex** documents sandbox modes, approval behavior, and warns about prompt injection when enabling network/web search; destructive tool calls can require approval if advertised as destructive. citeturn12view2turn12view3  
- **Gemini CLI** supports per-server trust (bypass confirmations), include/exclude tools, and environment sanitization/redaction; explicit env is required to pass sensitive vars. citeturn11view0  
- **Claude Code** supports local stdio servers and warns to trust servers you install; it also describes scopes and configuration patterns. citeturn10view0  

### Fusion-specific failure modes and recovery patterns
- **Threading issues / crashes:** Avoid Fusion API calls off the UI thread; use Custom Events. citeturn5view0turn5view1turn5view2  
- **Events not processing:** Calling `adsk.doEvents()` may cause pending events to be handled; useful when you need to keep UI responsive during long-running operations. citeturn29view0  
- **Invalid/stale references:** Use `entityToken` and validate `isValid` before using entities; if invalid, re-resolve or re-list. citeturn30search16turn33search6  
- **Output bloat:** Keep tool outputs short; return structured summaries and tokens, not giant geometry dumps.

### Logging and telemetry design
Minimum viable observability (do this early):
- Every request has a `requestId`.
- Log: `{timestamp, requestId, op, mode, args_hash, duration_ms, ok, error_class}`.
- Keep an on-disk rolling log (JSONL) and a “last 50 calls” in memory for quick inspection.

MCP specs explicitly encourage logging tool usage for audit, and host ecosystems increasingly support telemetry/OTel. citeturn9view0turn12view3

### Testing strategy
Autodesk University material on testing strategies calls out:
- structuring your add-in for unit testing,
- using Python’s `unittest`,
- mocking Fusion objects with a purpose-built mock library,
- and automating integration/UI tests for commands. citeturn17view0turn17view1turn17view2

A pragmatic split:
- **Unit tests (CI-friendly):** MCP server schema validation, request routing, retries/backoff, path sanitization.
- **Integration tests (local machine):** A “test runner” command in the add-in runs known modeling scripts and asserts expected entity counts/tokens.
- **Manual smoke tests:** 3 canonical workflows (work/utility/creative) after any major change.

### Local dev workflow (Windows)
- Edit add-in files in your editor; reload add-in from the Scripts and Add-Ins dialog (Fusion supports start/stop, and can run on startup). citeturn25view1  
- For debugging, Autodesk describes launching Visual Studio Code debugging directly from the Scripts and Add-Ins dialog’s Debug option. citeturn18view0  

## Host options, alternatives, and expansion roadmap

### Host comparison tables

#### Runtime comparison (using MCP servers)

| Host | MCP support style | Best for | Safety controls | Notes |
|---|---|---|---|---|
| Claude Code | Local stdio + remote HTTP MCP servers citeturn10view0 | Conversational + code-aware workflows | Prompts approval; warns to trust servers citeturn10view0 | Great for iterative tool building if you live in terminal |
| Gemini CLI | MCP in `settings.json`, trust + include/exclude tools citeturn11view0 | Fast local iteration, configurable confirmations | Trust flag bypasses confirms; include/exclude tools; env redaction citeturn11view0 | Strong config surface for controlling tool exposure |
| Codex (CLI / IDE ext) | MCP stdio + Streamable HTTP; shared config citeturn12view0 | “Agentic” coding + operational guardrails | Sandbox + approval policies; network/web search cautions citeturn12view2turn12view3 | Best if you want strong safety/telemetry primitives |

#### Development-assistance comparison (building the copilot)

| Host | Strengths for building the system | Weaknesses |
|---|---|---|
| Claude Code | Excellent at refactors + explaining MCP configs and tool design patterns citeturn10view0 | Depends on your plan/limits; toolchain differs from GUI Claude Desktop |
| Gemini CLI | Tight MCP tooling documentation and configuration controls citeturn11view0 | Requires comfort with CLI workflows |
| Codex | Strong sandboxing/approvals model; config granularity; OTel observability support citeturn12view1turn12view2turn12view3 | You’ll want to tune approvals to avoid friction during rapid CAD iteration |

### Better alternatives than “Fusion add-in + HTTP + MCP”?
For a **local** CAD copilot controlling the desktop app, the Fusion Python add-in route is the most direct and matches official extensibility patterns (scripts/add-ins, Python/C++ APIs). citeturn25view1turn24view0

Alternatives that may complement (not replace) your build:

- **Fusion Automation API (cloud / headless-ish workflows):** Autodesk notes that the Automation API for Fusion (public beta) currently supports TypeScript and not fully on desktop, and provides tools like a VS Code extension for local and remote runs. citeturn7view0turn22view0  
  Use this when you want batch processing on a server, or CI-like execution that doesn’t rely on your interactive desktop session.
- **Prebuilt MCP-to-Fusion bridges:** entity["company","AuraFriday","mcp toolchain vendor"] markets MCP-Link and related Fusion MCP tooling, including claims of exposing broad Fusion control and working with multiple AI hosts. Treat third-party “expose everything” bridges as powerful but higher-risk; you still want your own guardrails or at least understand the security posture. citeturn28view0turn28view2  

### Expansion roadmap for future capabilities
This roadmap’s ordering matches what tends to be “high leverage” for 3D printing + CNC prep, while keeping the model’s action space understandable.

**CNC prep**
- Body → component conversion + naming templates (phase two)
- Material/appearance synchronization tools (phase three)
- Automated setup creation, stock assignment, and NC program exports (requires CAM API tool surface; add carefully and with approvals)

**Better surfacing / organic modeling**
- Loft rails/centerline options (build on loft sample patterns) citeturn34view1turn35search24  
- Sweep and multi-rail sweep samples exist in Fusion API samples; add as phase three “creative power tools.” citeturn33search14  
- FormFeature/T-spline primitives for “vibe and make something creative” workflows citeturn32search22  

**Automation API integration**
- Use Automation API for Fusion for batch generation and regression checking (especially for long-running “generate 200 variants” jobs), while keeping local MCP copilot for interactive design. Autodesk’s guidance highlights TypeScript-only support and tooling for local/remote runs. citeturn7view0turn22view0  

**Hardening**
- Formal schema validation on both MCP server and Fusion add-in
- Strict file sandboxing for exports (path allowlists)
- Host-side tool allowlists/denylists and “untrusted vs trusted” server settings (particularly easy in Gemini CLI and Codex). citeturn11view0turn12view1turn12view2  

## Appendix: citation-backed “official facts” checklist

- Fusion add-ins run via `run/stop`, can auto-load, and are managed in Scripts and Add-Ins. citeturn25view0turn25view1  
- Fusion API supports Python/C++ on desktop and is meant to replicate interactive operations programmatically. citeturn24view0turn33search11  
- ExportManager can export STL/STEP and other formats via `create…ExportOptions` and `execute`. citeturn8view0  
- Most Fusion API calls are not thread safe; Custom Events are the recommended cross-thread mechanism. citeturn5view0turn5view1turn5view2  
- MCP uses JSON-RPC and defines stdio + Streamable HTTP transports; local servers should bind to localhost and implement protections (e.g., origin validation for HTTP). citeturn27view0turn9view0  
- Claude Code, Gemini CLI, and Codex document MCP server configuration and tool controls. citeturn10view0turn11view0turn12view0turn12view1
