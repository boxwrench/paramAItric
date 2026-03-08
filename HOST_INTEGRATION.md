# ParamAItric Host Integration

## Principle

ParamAItric is intended to be host-agnostic. The MCP boundary is the integration point. Tool definitions, workflow verification, staged validation, and the Fusion bridge should remain the same regardless of which AI client drives the system.

Host choice should be a configuration decision, not a code fork.

## Current repo status

The current repository includes the Fusion add-in bridge, the MCP-side workflow layer, and the live smoke runner.

The host-facing MCP transport packaging is still follow-on work. In other words:

- the workflow and validation layer exists
- the Fusion bridge integration exists
- a packaged stdio or HTTP MCP entrypoint is not yet part of the current implementation

This document describes the intended integration direction.

## Intended transport model

ParamAItric should eventually expose the same workflow surface through two MCP transport modes:

### stdio

Preferred for local development and local desktop AI hosts.

Why:

- simplest setup
- no port management
- good fit when the AI host runs on the same machine as Fusion 360

### HTTP

Useful for hosts that cannot launch a local subprocess or need a persistent MCP endpoint.

Why:

- works better for API-driven or remotely orchestrated agents
- separates server lifecycle from client lifecycle

## Transport rules

When the host-facing MCP server is added, these rules should hold:

- stdio and HTTP must share the same tool definitions
- stdio and HTTP must share the same workflow verification rules
- transport choice must not change Fusion-side behavior
- stdout must remain clean in stdio mode so protocol messages are not corrupted

## Integration priority

The sensible order for host integration work is:

1. stdio first
2. one local host validated end to end
3. one second host validated against the same workflow
4. HTTP transport added only after the local path is stable

## What should stay invariant across hosts

- tool schemas
- workflow stage ordering
- verification behavior
- `WorkflowFailure` structure
- entity token resolution
- bridge protocol to the Fusion add-in
- export path allowlisting

If those invariants hold, host support is an integration problem rather than a product-definition problem.
