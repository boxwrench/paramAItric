# ParamAItric Architecture

AI Agent
    │
    ▼
MCP Server
    │
    ▼
Local HTTP Bridge
    │
    ▼
Fusion 360 Python Add-in
    │
    ▼
Fusion API

AI agents call MCP tools.

The MCP server translates these calls into HTTP requests.

The Fusion add-in receives requests and executes modeling operations through the Fusion API.

Each operation returns stable entity tokens so future operations can reference geometry reliably.

This token-based referencing is critical because Fusion object handles often become invalid after timeline edits.

The system therefore stores entity tokens rather than direct object references.

Entity tokens can later be resolved through:

Design.findEntityByToken()

This allows modeling operations to chain safely across multiple tool calls.