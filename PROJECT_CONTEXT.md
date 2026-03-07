# ParamAItric

ParamAItric is an AI-assisted CAD automation system for Autodesk Fusion 360.

The project allows large language models to design geometry inside Fusion by calling tools exposed through an MCP server.

The system architecture consists of three main layers:

1. Fusion 360 Python Add-in
2. Local HTTP Bridge
3. MCP Tool Server

AI agents communicate with the MCP server, which translates tool calls into requests to the Fusion add-in. The Fusion add-in then executes CAD operations through the Fusion Python API.

The design goal is to allow an AI to perform most modeling tasks that a human would normally do manually in Fusion.

However, the system is built incrementally to maintain reliability.

The project uses three operational modes.

---

## Work Mode

Reliable mechanical CAD operations.

Examples:
- brackets
- spacers
- enclosures
- mounts
- simple 3D printable parts

Allowed operations:

create_sketch  
draw_circle  
draw_rectangle  
draw_line  
extrude_profile  
shell_body  
fillet_edges  
export_stl

The goal is predictable modeling.

---

## Utility Mode

Workflow automation and CAD housekeeping.

Examples:

convert bodies to components  
set physical material  
set appearance  
rename bodies  
prepare parts for CNC  
export STEP/DXF/STL

This mode focuses on automating tedious manual work.

---

## Creative Mode

Experimental modeling.

Examples:

decorative vases  
generative shapes  
organic lofts  
design brainstorming

Allowed operations include splines, lofts, revolutions, and complex geometry chains.

Creative mode prioritizes exploration rather than strict reliability.

---

## Development Passes

The system is implemented in three major passes.

### Pass 1 — Core Modeling

Minimal reliable modeling pipeline.

Tools:

new_design  
create_sketch  
draw_circle  
draw_rectangle  
draw_line  
extrude_profile  
list_profiles  
export_stl

Goal:

Allow AI to generate simple printable parts.

---

### Pass 2 — Workflow Tools

Utilities and CAD automation.

Tools:

convert_bodies_to_components  
set_physical_material  
set_appearance  
rename_entities  
list_entities  
export_step

Goal:

Allow AI to automate design preparation and file management.

---

### Pass 3 — Advanced Modeling

Creative modeling capabilities.

Tools:

draw_spline  
loft_profiles  
revolve_profile  
pattern_features  
combine_bodies  
create_offset_planes

Goal:

Enable creative or complex design generation.

---

## Fusion Add-in Responsibilities

The Fusion add-in performs all CAD operations.

Responsibilities:

Start a local HTTP server  
Receive modeling commands  
Dispatch operations to the Fusion API  
Return entity tokens for created objects  
Log modeling operations

The add-in must ensure all Fusion API calls occur on the main thread.

---

## MCP Server Responsibilities

The MCP server exposes tool schemas to AI agents.

Responsibilities:

Define tool contracts  
Validate arguments  
Forward requests to the Fusion bridge  
Translate errors into recoverable messages

The MCP server must remain host-agnostic.

It should work with:

Claude  
Gemini  
ChatGPT  
local LLM agents

---

## Design Philosophy

ParamAItric intentionally limits early toolsets.

This improves reliability when AI agents chain tool calls.

Capabilities are expanded gradually as the system proves stable.

The long-term goal is to expose enough tools to perform most manual Fusion modeling tasks.

While still keeping the interface structured enough for AI agents to use effectively.

---

## Humor Policy

ParamAItric embraces a slightly self-deprecating tone.

This project acknowledges that serious CAD engineers may view AI-generated geometry with skepticism.

They are probably correct.

But the results can still be useful.