# ParamAItric Architecture

## Canonical model

ParamAItric uses a four-part execution path:

1. AI host
2. MCP server
3. Fusion add-in HTTP bridge
4. Fusion API execution on the main thread

The MCP server and the Fusion add-in are separate processes with separate responsibilities.

```text
AI host
  -> MCP server
  -> loopback HTTP request
  -> Fusion add-in bridge
  -> CustomEvent handler on Fusion main thread
  -> Fusion API
```

## Responsibilities

### AI host

- discovers tools from the MCP server
- chooses tool calls based on user prompts
- renders results back to the user

### MCP server

- defines tool schemas
- validates arguments before they reach Fusion
- forwards validated requests to the Fusion add-in
- translates execution results into structured tool responses

### Fusion add-in

- runs inside Fusion 360
- hosts a loopback-only HTTP listener
- queues incoming work
- fires a `CustomEvent` so Fusion API work executes on the main thread
- returns results, errors, and entity references

The scaffold currently supports two startup modes:

- `mock`: default outside Fusion, used for local workflow and bridge testing
- `live`: selected only when a real Fusion design context is available

## Non-negotiable threading rule

Fusion API mutations must execute on Fusion's main thread. The HTTP listener can run on a background thread, but it must not call the Fusion API directly.

Required pattern:

1. HTTP listener receives a request.
2. Listener validates and enqueues the command.
3. Listener fires a `CustomEvent`.
4. The event handler runs on the Fusion main thread and performs the CAD operation.
5. The result is returned to the HTTP listener and then back to the MCP server.

This is the most important architectural constraint in the entire project.

## V1 architectural defaults

The initial implementation should lock in a narrow execution model for reliability:

- one CAD mutation at a time
- structured tool chaining as the foundation
- no broad escape-hatch tools in the initial product shape
- entity-token-based references across calls
- higher-level templates built above low-level CAD primitives, not instead of them
- verification/readback tools available alongside mutation tools
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

- MCP server validates tool inputs and rejects malformed or unsafe requests early.
- Fusion add-in validates that referenced entities still exist.
- File operations are restricted to allowlisted paths.
- The HTTP bridge binds to loopback only.
- Risky operations remain gated by mode and, where appropriate, explicit confirmation.

For v1, higher-level template behavior should remain in the MCP/tool layer so the Fusion add-in stays focused on validated low-level CAD execution.

## Workflow discipline

The benchmark result is that workflow control matters more than prompt cleverness. V1 should encode these rules directly:

1. Start from known state.
2. Perform one modeling milestone.
3. Verify the result before continuing.
4. Stop on failed verification instead of compounding errors.
5. Preserve the valid partial result and return a narrow next step for correction.

## Planned repository structure

The implementation should eventually introduce a structure similar to:

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

This is a target layout, not a description of the current repo state.
