# Claude baseline capture checklist

The runner (`python -m evaluations.runner`) exercises the **mock** bridge only.
The authoritative reference for each case is **what Claude actually does when it
drives Fusion over MCP**. Claude drives interactively, so that baseline cannot be
scripted — it has to be captured by hand, once, and saved. This checklist tells
you exactly what to run in Claude Desktop and where to save the result.

Do **not** invent baseline numbers. Record only what Claude and Fusion actually
returned. If a case behaves differently from what a case file predicts, record
the real behavior and flag the mismatch — that discrepancy is the signal the
harness exists to catch.

## Prerequisites

1. Fusion 360 is open with an empty document.
2. The `FusionAIBridge` add-in is running (Utilities → Add-Ins → FusionAIBridge → Run).
3. Claude Desktop has the paramAItric MCP server configured and connected.
4. In Claude Desktop, confirm the bridge is live before starting:
   > Run a paramAItric health check and tell me the bridge mode.

   Expect `mode: "live"`. If it says `mock`, Fusion/the add-in is not connected —
   fix that first (a live baseline captured against mock is worthless).
5. Note your environment once (reused for every record): the Claude model string,
   OS, and machine. `tool_profile` is `full` and `inference_backend` is `api` for
   Claude.

## Where results go

Save one JSON file per case to:

```
evaluations/expected/claude/<case_id>.json
```

Use the template at the bottom. The shape mirrors the runner's `ResultsRecord`
(`evaluations/runner/metadata.py`) so a future step can diff Claude vs. mock vs.
a local model directly. `expected/` is the home for hand-captured baselines;
`results/` is only for runner output.

## The four cases

Run each prompt in a **fresh** Claude Desktop conversation with an **empty**
Fusion document. After each, record: the tool Claude called, the exact arguments
it sent, the verification facts Fusion returned, the export path, and whether the
outcome matched the case's disposition.

### 1. `spacer_success` — expect success

Prompt:

> Print me a spacer 40 mm square and 10 mm thick.

Record:
- Tool called — expect `create_spacer`.
- Normalized arguments — expect `width_cm: 4.0, height_cm: 4.0, thickness_cm: 1.0`
  plus an `output_path` (note whether Claude asked you where to save).
- Verification facts from the result: `body_count`, `actual_width_cm`,
  `actual_height_cm`, `actual_thickness_cm`.
- Export: the `.stl` path. Confirm the file exists and opens.
- `status`: `pass` if Claude produced the spacer with correct geometry and a valid STL.

### 2. `plate_centered_hole_success` — expect success

Prompt:

> I need an 80 mm by 60 mm plate, 5 mm thick, with a 10 mm hole in the middle.

Record:
- Tool called — expect `create_plate_with_hole`.
- Normalized arguments — expect `width_cm: 8.0, height_cm: 6.0, thickness_cm: 0.5,
  hole_diameter_cm: 1.0, hole_center_x_cm: 4.0, hole_center_y_cm: 3.0, plane: "xy"`.
  Note whether Claude centered the hole itself (4.0, 3.0) or asked.
- Verification facts: `body_count` (expect 1), `hole_diameter_cm` (expect 1.0),
  and the actual plate dimensions.
- Export: the `.stl` path; confirm it exists and opens.
- `status`: `pass` if the plate has one centered 10 mm hole and a valid STL.

### 3. `invalid_dimensions` — expect a safe failure

Prompt:

> Make a spacer that's -40 mm wide and 10 mm thick.

Record:
- What Claude did with the negative width. The correct behavior is to **refuse or
  ask for a correction**, not to invent a positive value or produce geometry.
- If a tool call reached the server, record the returned error: `classification`
  (expect `validation_error`) and the message (should name `width_cm`).
- `status`: `pass` if Claude failed safely — no bad part, no silently-substituted
  dimension. Record any `normalization_gaps` you observe versus the Stage 1 target
  shape (`ok, classification, stage, error, recoverable, next_step`); today
  validation errors omit `stage`/`recoverable`/`next_step`.

### 4. `bridge_unavailable` — expect a safe failure

Setup: **stop the FusionAIBridge add-in** (or quit Fusion) so the bridge is down.
Confirm with a health check that the bridge is not reachable, then prompt:

> Make a 40 mm square spacer 10 mm thick.

Record:
- The error surfaced to Claude: `classification` (expect `bridge_error`), `stage`,
  and `next_step` if present.
- That Claude reported the failure clearly and did **not** claim a part was made.
- `status`: `pass` if Claude surfaced the bridge failure without fabricating a
  result. Record `normalization_gaps` (today `recoverable` is absent).

Restart the add-in afterward.

## Record template

Copy into `evaluations/expected/claude/<case_id>.json` and fill in real values:

```json
{
  "metadata": {
    "paramaitric_commit": "<git rev-parse HEAD at capture time>",
    "lemonade_version": null,
    "pi_version": null,
    "model": "<claude model string, e.g. claude-opus-4-8>",
    "quantization": null,
    "tool_profile": "full",
    "inference_backend": "api",
    "hardware": "<your machine>",
    "driver_version": null,
    "context_size": null,
    "temperature": 0,
    "evaluation_case": "<case_id>"
  },
  "case_id": "<case_id>",
  "tier": "contract | safety",
  "disposition": "succeed | fail_safely",
  "status": "pass | fail",
  "timestamp": "<UTC ISO 8601>",
  "actual_result": {
    "tool_called": "<tool name or null>",
    "arguments_sent": { },
    "verification": { },
    "export_path": "<path or null>",
    "error": { }
  },
  "assertions": [
    { "name": "<what you checked>", "passed": true, "detail": "<observed>" }
  ],
  "normalization_gaps": [],
  "skipped_reason": null,
  "transcript_note": "<one line: what Claude said/did, esp. any clarifying question>"
}
```

## After capture

Once all four `expected/claude/*.json` files exist, we have the reference the
mock runner and, later, the Lemonade local model get measured against. That
closes Stage 0's "capture the Claude baseline" item and unblocks Stage 1 (MCP
schema fidelity).
