# Faust Benchmark Findings

Status: research note, not product doctrine

## Why This Exists

These notes summarize a hands-on benchmark of Faust's Fusion 360 MCP server with Gemini as the host on Windows, using live Fusion 360 runs. The goal was not to copy Faust's product direction. The goal was to learn what already works, what breaks, and what should influence ParamAItric.

## High-Confidence Findings

### The bridge works
- Gemini can drive Fusion 360 end to end through Faust.
- The local bridge and MCP loop are viable for real iterative CAD work.
- This was proven on actual geometry creation, editing, export, and verification runs.

### Staged workflows matter more than one-shot prompting
- Broad, all-in-one prompts increased errors, stalls, and cleanup problems.
- Breaking work into phases improved success materially.
- The best pattern was:
  1. clear and verify scene
  2. build one milestone
  3. verify
  4. continue

### Structured geometry is the strongest lane
- Stronger benchmark categories:
  - cube
  - sphere
  - bracket
  - vase/container forms
  - mug body and handle
  - box + lid
  - jar + lid
  - nested polygon fidgets
  - stylized planetary gears
- Weaker categories:
  - curved decorative text
  - organic branching cleanup
  - thread creation

### Human-in-the-loop review is the right operating model
- Gemini/Faust can get to a strong first-pass geometry.
- A human can then measure, inspect, and request narrow corrections.
- This is much more viable than expecting one-shot manufacturable correctness.

### Broad tool availability did not itself break sessions
- Having many tools enabled did not automatically degrade results.
- Failures were more strongly associated with:
  - unreliable individual tool implementations
  - weak verification
  - over-broad tasks
  - too many dependent operations in one run

## Recurring Weak Points

- `delete_all` is unreliable.
- `create_parameter` often needs fallback.
- `export_step` is unreliable enough to distrust.
- `measure_distance` and some inspection helpers are shaky.
- `create_thread` is not proven for functional closure work.
- Fusion can hang if too many dependent operations are pushed in one run.
- Cleanup/hygiene degrades on more organic or messy tasks.

## What Worked Well Enough To Matter

### Containers and closures
- Box + lid worked when staged.
- Jar + lid worked when staged.
- Thread phase did not.

### Decorative but structured forms
- Vases worked once explicit open-top verification was required.
- Mug plus handle worked with a narrow recovery pass.
- Nested rings worked well when built sketch-first and extruded one body at a time.

### Complex assemblies
- A stylized planetary gear set was created as a coherent multi-body assembly.
- It was not proof of production-grade gear correctness, but it was a strong stress-test pass for structured multi-part geometry.

## What This Suggests For ParamAItric

- The promising product lane is narrower, safer, and more functional than broad "AI for all CAD."
- Workflow control matters more than raw tool count.
- Validation and state awareness should be first-class.
- ParamAItric should optimize for:
  - defined mechanical workflows
  - explicit step sequences
  - typed operations
  - verification after each major step
  - clear human correction loops

## Working Hypotheses

- ParamAItric should likely narrow workflow scope before it narrows tool count.
- A smaller product tool surface may still be desirable, but mainly for predictability and validation, not because tool abundance alone is harmful.
- Reliable mechanical-part workflows are a better v1 than decorative or freeform generation.
- Organic/freeform capabilities are useful as edge tests, not as the primary value proposition.

## Open Questions

- How narrow should the first ParamAItric workflow set actually be?
- Which validations should be built into every workflow by default?
- Should ParamAItric expose many typed tools internally but only a small number of higher-level user workflows?
- How much correction should the agent attempt autonomously before asking for human confirmation?

## Bottom Line

Faust is useful as a benchmark and may be useful on real projects. The key takeaway for ParamAItric is not "copy Faust." The key takeaway is that live AI-assisted Fusion work is already viable when the workflow is constrained, verified, and treated as co-design rather than full autonomy.
