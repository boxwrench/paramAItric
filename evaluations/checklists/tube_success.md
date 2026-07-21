# Capture checklist — `tube_success`

> Generated from `evaluations/cases/tube_success.json`. Do not edit by hand —
> edit the case and regenerate.

| | |
|---|---|
| Tier | `contract` |
| Disposition | `succeed` |
| Expected workflow | `create_tube` |
| Expected tool call | `create_tube` |
| Bridge | `mock` |
| Baseline required | yes — representative part |

## 1. Preconditions

- [ ] Fusion 360 open with an empty document
- [ ] `FusionAIBridge` add-in running
- [ ] Claude Desktop connected to the paramAItric MCP server
- [ ] Health check reports `mode: "live"` — a baseline captured against mock is worthless

## 2. The request

Give Claude exactly this, verbatim:

> Draw me a tube with outer diameter of 3 inches, inner diameter of 1.5 inches, and 12 inches tall.

This case must **succeed**. Record the geometry and the export path.

## 3. Measurements Claude must extract

   - [ ] `outer_diameter`
   - [ ] `inner_diameter`
   - [ ] `height`

## 4. Record the result

Save to `evaluations/expected/claude/tube_success.json` with these top-level fields:

- `metadata`
- `case_id`
- `tier`
- `disposition`
- `status`
- `timestamp`
- `claude_tool_call`
- `claude_arguments`
- `actual_result`
- `assertions`
- `normalization_gaps`
- `capture_method`

The `metadata` object requires:

- `paramaitric_commit`
- `lemonade_version`
- `pi_version`
- `model`
- `quantization`
- `tool_profile`
- `inference_backend`
- `hardware`
- `driver_version`
- `context_size`
- `temperature`
- `evaluation_case`

## 5. Before you commit

- [ ] `python -m evaluations.baseline --validate` passes
- [ ] Every number came from what Fusion actually returned

**Do not invent baseline numbers.** If the run disagrees with what this case
predicts, record the real behavior and flag the mismatch — that discrepancy is
the signal this harness exists to catch.
