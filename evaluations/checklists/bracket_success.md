# Capture checklist — `bracket_success`

> Generated from `evaluations/cases/bracket_success.json`. Do not edit by hand —
> edit the case and regenerate.

| | |
|---|---|
| Tier | `contract` |
| Disposition | `succeed` |
| Expected workflow | `create_bracket` |
| Expected tool call | `create_bracket` |
| Bridge | `mock` |
| Baseline required | yes — representative part |

## 1. Preconditions

- [ ] Fusion 360 open with an empty document
- [ ] `FusionAIBridge` add-in running
- [ ] Claude Desktop connected to the paramAItric MCP server
- [ ] Health check reports `mode: "live"` — a baseline captured against mock is worthless

## 2. The request

Give Claude exactly this, verbatim:

> Make an L-bracket, 50 mm wide, 80 mm high, 5 mm thick, with a leg thickness of 5 mm.

This case must **succeed**. Record the geometry and the export path.

## 3. Measurements Claude must extract

   - [ ] `width`
   - [ ] `height`
   - [ ] `thickness`
   - [ ] `leg_thickness`

## 4. Record the result

Save to `evaluations/expected/claude/bracket_success.json` with these top-level fields:

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
