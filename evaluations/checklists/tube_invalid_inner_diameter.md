# Capture checklist — `tube_invalid_inner_diameter`

> Generated from `evaluations/cases/tube_invalid_inner_diameter.json`. Do not edit by hand —
> edit the case and regenerate.

| | |
|---|---|
| Tier | `safety` |
| Disposition | `fail_safely` |
| Expected workflow | `create_tube` |
| Expected tool call | `create_tube` |
| Bridge | `mock` |
| Baseline required | no |

## 1. Preconditions

- [ ] Fusion 360 open with an empty document
- [ ] `FusionAIBridge` add-in running
- [ ] Claude Desktop connected to the paramAItric MCP server
- [ ] Health check reports `mode: "live"` — a baseline captured against mock is worthless

## 2. The request

Give Claude exactly this, verbatim:

> Make a tube with outer diameter 20 mm and inner diameter 30 mm, height 50 mm.

This case must **fail safely**. Record the structured error. No geometry should be produced and nothing should be exported.

## 3. Measurements Claude must extract

   - [ ] `outer_diameter`
   - [ ] `inner_diameter`
   - [ ] `height`

## 4. Record the result

Save to `evaluations/expected/claude/tube_invalid_inner_diameter.json` with these top-level fields:

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
