# ParamAItric Architecture

## Canonical model

ParamAItric uses a four-part execution path:

1. AI host
2. MCP-facing server layer
3. Fusion add-in HTTP bridge
4. Fusion API execution on the main thread

The MCP-facing server logic and the Fusion add-in are separate processes with separate responsibilities.

```text
AI host
  -> MCP-facing server
  -> loopback HTTP request
  -> Fusion add-in bridge
  -> CustomEvent handler on Fusion main thread
  -> Fusion API
```

## Responsibilities

### AI host

- discovers tools from the MCP-facing server
- chooses tool calls based on user prompts
- renders results back to the user

The AI host is not part of the ParamAItric codebase. The protocol boundary matters more than the specific client.

### MCP-facing server layer

- defines tool schemas
- validates arguments before they reach Fusion
- enforces workflow sequencing and verification
- forwards validated requests to the Fusion add-in
- translates execution results into structured tool responses

### Fusion add-in

- runs inside Fusion 360
- hosts a loopback-only HTTP listener
- queues incoming work
- fires a `CustomEvent` so Fusion API work executes on the main thread
- returns results, errors, and entity references

The add-in currently supports two startup modes:

- `mock`: default outside Fusion, used for local testing
- `live`: selected only when a real Fusion design context is available

## Host integration direction

ParamAItric is intended to be host-agnostic at the MCP boundary.

In practice, that means:

- the tool surface should not depend on a specific model vendor
- workflow verification rules should stay the same across hosts
- host transport concerns should stay outside the Fusion add-in

The current repo contains the MCP-side workflow and bridge logic, but not yet a packaged host-facing MCP transport entrypoint. Stdio and HTTP transport packaging are follow-on integration work, not a current claim about shipped behavior.

## Non-negotiable threading rule

Fusion API mutations must execute on Fusion's main thread. The HTTP listener can run on a background thread, but it must not call the Fusion API directly.

Required pattern:

1. HTTP listener receives a request.
2. Listener validates and enqueues the command.
3. Listener fires a `CustomEvent`.
4. The event handler runs on the Fusion main thread and performs the CAD operation.
5. The result is returned to the HTTP listener and then back to the MCP-facing server layer.

This is the most important architectural constraint in the project.

## V1 architectural defaults

The initial implementation should lock in a narrow execution model for reliability:

- one CAD mutation at a time
- structured tool chaining as the foundation
- no broad escape-hatch tools in the initial product shape
- entity-token-based references across calls
- higher-level templates built above low-level CAD primitives, not instead of them
- verification and readback tools available alongside mutation tools
- correction loops aimed at targeted follow-up changes, not open-ended autonomous retries

This keeps the first product pass aligned with functional parametric workflows instead of broad exploratory automation.

## Entity reference strategy

Cross-call references should use Fusion entity tokens, not live object handles.

- Created sketches, profiles, bodies, and features return stable identifiers derived from entity tokens.
- Later tool calls re-resolve those tokens through `Design.findEntityByToken()`.
- Token strings should be treated as opaque references, not compared as semantic IDs.

This avoids failures caused by stale object handles after timeline edits.

## Safety constraints

The architecture assumes multiple layers of validation:

- the MCP-facing server layer validates tool inputs and rejects malformed or unsafe requests early
- the Fusion add-in validates that referenced entities still exist
- file operations are restricted to allowlisted paths
- the HTTP bridge binds to loopback only
- risky operations remain gated by mode and, where appropriate, explicit confirmation

For v1, higher-level template behavior should remain in the MCP-facing layer so the Fusion add-in stays focused on validated low-level CAD execution.

## Workflow discipline

V1 should encode these rules directly:

1. Start from known state.
2. Perform one modeling milestone.
3. Verify the result before continuing.
4. Stop on failed verification instead of compounding errors.
5. Preserve the valid partial result and return a narrow next step for correction.

## Planned repository structure

The implementation should eventually settle into a structure similar to:

```text
fusion_addin/
  FusionAIBridge.py
  FusionAIBridge.manifest
  http_bridge.py
  dispatcher.py
  ops/

mcp_server/
  server.py
  bridge_client.py
  schemas.py
  tools/

tests/
docs/
  research/
```
