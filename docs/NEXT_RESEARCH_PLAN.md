# Next Research Plan

Status: active

## Current status

The first two highest-priority research passes now have reviewed internal synthesis:

- semantic selector design
  - reviewed bundle: `internal/research/selector-foundations-2026-04-08/`
  - synthesis memo: `internal/research/selector-foundations-2026-04-08/SYNTHESIS.md`
- Python CAD inspiration research
  - reviewed bundle: `internal/research/python-cad-inspiration-2026-04-07/`
  - synthesis memo: `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`

The practical outcome so far is that Phase 1 implementation should now focus on:

- a small deterministic selector vocabulary
- add-in-side selector resolution
- explicit cardinality guards
- lightweight `SelectionTrace` diagnostics

This document remains the canonical sequence for the remaining open research questions and follow-on passes.

## Purpose

This document turns the latest research synthesis into a practical follow-on plan.

The goal is not more broad scanning. The goal is targeted research that directly improves ParamAItric's next internal design pass.

This plan ranks the highest-value research topics, explains why they matter, and provides paste-ready prompt text for each one.

## External research use

These prompts are meant to be usable outside this session.

That means every prompt should assume:

- the researcher does not know this conversation
- the researcher does not know ParamAItric's architecture unless the prompt states it
- the researcher needs explicit sources, not just general instructions to "read the repo"

Use the prompts below as standalone prompts. Do not remove the source lists unless you are replacing them with a better explicit set.

## Shared repo context

Repository:

- ParamAItric: https://github.com/boxwrench/paramAItric

GitHub file URL pattern for repo sources:

- `https://github.com/boxwrench/paramAItric/blob/master/<path>`

Examples:

- `https://github.com/boxwrench/paramAItric/blob/master/README.md`
- `https://github.com/boxwrench/paramAItric/blob/master/docs/VERIFICATION_POLICY.md`
- `https://github.com/boxwrench/paramAItric/blob/master/mcp_server/workflow_registry.py`

Shared context that should usually be included in follow-on research:

- ParamAItric is an AI-first CAD system aimed at turning human intent into editable Fusion 360 geometry.
- It is not trying to become a general-purpose CAD library.
- It currently owns the MCP-facing tool surface, workflow validation, verification and recovery logic, and the Fusion 360 bridge/add-in execution path.
- The current strategic rule is: improve ParamAItric's own abstractions without introducing a new runtime geometry dependency.

Core repo sources that external research should use first:

- `README.md`
- `ARCHITECTURE.md`
- `BEST_PRACTICES.md`
- `docs/AI_CONTEXT.md`
- `docs/VERIFICATION_POLICY.md`
- `docs/AI_CAD_PLAYBOOK.md`
- `docs/FREEFORM_PLAYBOOK.md`
- `docs/FREEFORM_CHECKLIST.md`
- `docs/NEXT_PHASE_PLAN.md`
- `docs/RESEARCH_TRACKS.md`

Core implementation sources that are often relevant:

- `mcp_server/tool_specs.py`
- `mcp_server/server.py`
- `mcp_server/workflow_registry.py`
- `mcp_server/workflows/`
- `mcp_server/freeform.py`
- `mcp_server/sessions/freeform.py`
- `fusion_addin/dispatcher.py`
- `fusion_addin/http_bridge.py`
- `fusion_addin/ops/live_ops.py`
- `fusion_addin/bootstrap.py`

Supporting internal synthesis source:

- `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`

When using an external LLM, explicitly say:

- "Do not assume any prior chat context."
- "Use the repo and source list below as your starting point."
- "If a claim depends on a repo file, cite the file path."

## How the ranking works

Each topic is weighted on a 10-point scale using three factors:

- leverage
  How much this research can improve ParamAItric's core reliability and product clarity
- dependency value
  How much later design or implementation work depends on having this answer first
- execution readiness
  How easy it is to turn the result into concrete design or code decisions soon

The ranking is intentionally biased toward:

- selector reliability
- explainability of geometry decisions
- editability of generated Fusion models
- improved internal abstractions without introducing a new runtime dependency

## Weighted priority list

| Rank | Research topic | Weight | Why it belongs here now |
|---|---|---:|---|
| 1 | Semantic selector design | 10.0 | This is the most leveraged improvement for reliable AI-driven geometry targeting. |
| 2 | Selection trace and geometry diagnostics | 9.4 | ParamAItric needs explainable selection behavior, not just successful selection behavior. |
| 3 | Stable reference strategy across topology mutations | 9.1 | This determines how robust selectors and workflows can actually be inside Fusion after real mutations. |
| 4 | Narrow internal operation vocabulary / IR | 8.4 | ParamAItric needs a cleaner internal modeling language before it expands deeper. |
| 5 | Reusable part-recipe architecture | 7.9 | Current workflow families will benefit from a more consistent reusable structure. |
| 6 | Parameter relationship and expression strategy | 7.3 | Editability improves when dimensions are linked by intent, not only literal values. |
| 7 | Fast-feedback geometry assertions and examples-as-tests | 6.8 | This supports iteration and confidence, but it should follow the selector/reference work first. |

## Recommended order

Work through the topics in this order:

1. semantic selector design
2. selection trace and diagnostics
3. stable reference strategy across mutations
4. narrow internal operation vocabulary / IR
5. reusable part-recipe architecture
6. parameter relationship and expression strategy
7. fast-feedback geometry assertions and examples-as-tests

## 1. Semantic selector design

### What this research should answer

- What selector vocabulary should ParamAItric support first
- Which selectors are deterministic enough for production use
- How selectors should compose
- How selectors should map to live Fusion topology safely
- Which selectors should remain internal versus AI-facing

### Expected output

- a selector design memo
- a ranked first-version selector vocabulary
- examples mapped to current workflow operations
- do-now / later / avoid guidance

### Prompt

```text
Conduct deep technical research and design analysis for ParamAItric's first-generation semantic selector system.

Do not assume any prior chat context.

Repository:
- ParamAItric: https://github.com/boxwrench/paramAItric

Context:
- ParamAItric is an AI-first CAD system that produces editable Fusion 360 geometry through a constrained MCP workflow surface.
- Product goal: human intent -> AI translation -> structured CAD operations -> Fusion 360 -> editable 3D object.
- ParamAItric currently owns the MCP-facing tool surface, workflow validation, verification and recovery logic, and the Fusion bridge/add-in execution path.
- The current architectural need is a stronger internal selector layer for faces, edges, bodies, and vertices.
- This research is not about adding a new CAD backend.
- This research is about making geometry targeting more semantic, deterministic, explainable, and robust inside ParamAItric's current architecture.

Required sources to read first:
- `README.md`
- `ARCHITECTURE.md`
- `BEST_PRACTICES.md`
- `docs/VERIFICATION_POLICY.md`
- `docs/AI_CAD_PLAYBOOK.md`
- `docs/RESEARCH_TRACKS.md`
- `mcp_server/tool_specs.py`
- `mcp_server/workflow_registry.py`
- `mcp_server/workflows/`
- `fusion_addin/ops/live_ops.py`
- `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`

Research goals:
1. Define the minimum useful selector vocabulary ParamAItric should support first.
2. Determine which selector types are safe and deterministic enough for early production use.
3. Recommend how selectors should compose.
4. Map selector concepts to Fusion topology realities and ParamAItric's current verification model.
5. Separate selectors that should be AI-facing from selectors that should remain internal implementation details.

Questions to answer:
1. What selector categories matter most for ParamAItric now?
   - positional selectors
   - geometric-type selectors
   - relational selectors
   - size/rank selectors
   - policy-based selectors
2. Which specific selectors are highest-value for first implementation?
   - examples: top face, largest planar face, outer vertical edges, circular edges on selected face
3. What selector combinations are safe and useful?
4. What are the main failure modes of semantic selection in a Fusion-driven system?
5. How should selector outputs be represented internally?
6. Which selectors should be:
   - do now
   - prototype later
   - avoid

Research method:
- Use the required repo sources above as your primary context.
- Focus on implementation relevance, not generic CAD theory.
- Separate:
  - observed facts
  - informed inferences
  - recommendations
- Cite relevant repo files by path when making repo-specific claims.

Deliver in this format:
1. Executive Summary
2. Selector Taxonomy
3. Ranked First-Version Selector Vocabulary
4. Selector Composition Rules
5. Failure Modes and Guardrails
6. Recommended Internal Representation
7. Recommended AI-Facing vs Internal-Only Split
8. Immediate Implementation Guidance
```

## 2. Selection trace and geometry diagnostics

### What this research should answer

- What a `SelectionTrace` should contain
- How much detail is useful versus noisy
- When traces should be emitted
- How traces should appear in verification, failures, and audits

### Expected output

- a selection-trace schema
- examples for several current operations
- guidelines for runtime emission and storage

### Prompt

```text
Conduct deep technical research and design analysis for ParamAItric's selection-trace and geometry-diagnostics layer.

Do not assume any prior chat context.

Repository:
- ParamAItric: https://github.com/boxwrench/paramAItric

Context:
- ParamAItric is moving toward a more semantic selector system.
- Product goal: human intent -> AI translation -> structured CAD operations -> Fusion 360 -> editable 3D object.
- The system already emphasizes staged verification and structured failure handling.
- To make geometry targeting explainable and debuggable, selections should produce structured traces.
- The goal is not generic logging. The goal is high-signal diagnostic data that supports verification, failure analysis, and future workflow hardening.

Required sources to read first:
- `README.md`
- `ARCHITECTURE.md`
- `docs/VERIFICATION_POLICY.md`
- `docs/FREEFORM_PLAYBOOK.md`
- `docs/FREEFORM_CHECKLIST.md`
- `mcp_server/freeform.py`
- `mcp_server/sessions/freeform.py`
- `mcp_server/tool_specs.py`
- `fusion_addin/ops/live_ops.py`
- `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`

Research goals:
1. Define what a SelectionTrace should contain.
2. Distinguish essential diagnostic fields from optional or noisy fields.
3. Determine when traces should be emitted automatically.
4. Determine how traces should interact with verification, audits, and structured failure output.
5. Recommend a minimal first implementation that gives high value without excessive logging overhead.

Questions to answer:
1. What fields should always be present in a SelectionTrace?
2. What geometric descriptors are worth recording?
3. How should traces describe selector intent versus actual resolved entities?
4. Which operations in ParamAItric most need tracing first?
5. How should traces be shown in:
   - verification outputs
   - failure reports
   - audit logs
   - freeform session logs
6. What should be:
   - required now
   - optional later
   - avoided

Research method:
- Use the required repo sources above as your primary context.
- Focus on practical schema design and debugging value.
- Separate:
  - observed facts
  - informed inferences
  - recommendations
- Cite relevant repo files by path when making repo-specific claims.

Deliver in this format:
1. Executive Summary
2. Why Selection Tracing Matters in ParamAItric
3. Proposed SelectionTrace Schema
4. Example Traces for Current Operation Types
5. Emission Rules
6. Reporting and UI/Audit Implications
7. Minimal First Implementation
8. Risks and Anti-Patterns
```

## 3. Stable reference strategy across topology mutations

### What this research should answer

- Which reference strategies survive which operation types
- Where entity tokens help
- Where attributes help
- Where geometry-based re-resolution is necessary
- Which operation classes are most dangerous

### Expected output

- a failure-mode matrix by operation type
- a recommended reference strategy matrix
- design guidance for selectors plus persistent references

### Prompt

```text
Conduct deep technical research and design analysis for ParamAItric's stable reference strategy across topology mutations in Fusion-driven workflows.

Do not assume any prior chat context.

Repository:
- ParamAItric: https://github.com/boxwrench/paramAItric

Context:
- ParamAItric already uses entity references, staged workflows, and verification logic.
- Product goal: human intent -> AI translation -> structured CAD operations -> Fusion 360 -> editable 3D object.
- The system needs references that survive real geometry mutations inside Fusion-driven workflows.
- The next design challenge is to make references more robust across operations such as extrude, cut, fillet, chamfer, shell, pattern, and boolean operations.
- This research should focus on practical reference stability inside ParamAItric's existing Fusion-centered architecture.

Required sources to read first:
- `README.md`
- `ARCHITECTURE.md`
- `BEST_PRACTICES.md`
- `docs/VERIFICATION_POLICY.md`
- `docs/AI_CAD_PLAYBOOK.md`
- `mcp_server/workflow_registry.py`
- `mcp_server/workflows/`
- `mcp_server/tool_specs.py`
- `fusion_addin/ops/live_ops.py`
- `tests/test_fillet.py`
- `tests/test_chamfer.py`
- `tests/test_cut_extrusion.py`
- `tests/test_workflow_stages.py`
- `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`

Research goals:
1. Identify the major topology-mutation risks for ParamAItric's current workflow families.
2. Determine which reference strategies are reliable for which operation classes.
3. Clarify where persistent tokens are enough, where attribute-based identity helps, and where geometry re-resolution is required.
4. Recommend a reference strategy matrix that ParamAItric can adopt.

Questions to answer:
1. Which operation types most often invalidate or destabilize references?
2. For each operation type, how should ParamAItric prefer to reference geometry?
3. When should selectors be resolved fresh versus carried forward?
4. What should be the relationship between:
   - semantic selectors
   - entity tokens
   - custom attributes
   - before/after snapshots
5. Which failure modes should become explicit guardrails in workflow code?

Research method:
- Use the required repo sources above as your primary context.
- Focus on decision-ready guidance, not generic CAD references.
- Separate:
  - observed facts
  - informed inferences
  - recommendations
- Cite relevant repo files by path when making repo-specific claims.

Deliver in this format:
1. Executive Summary
2. Topology Mutation Risk Map
3. Operation-by-Operation Failure Matrix
4. Recommended Reference Strategy Matrix
5. Guardrails for Workflow Authors
6. Implications for Selector Design
7. Immediate Changes ParamAItric Should Make
```

## 4. Narrow internal operation vocabulary / IR

### What this research should answer

- What the minimum useful internal operation set is
- How internal operations should represent targets, parameters, boolean intent, and placement
- What should stay Fusion-specific versus generic
- What not to abstract yet

### Expected output

- a draft internal operation vocabulary
- sample operation schemas
- mapping examples from current workflows

### Prompt

```text
Conduct deep technical research and design analysis for a narrow internal operation vocabulary for ParamAItric.

Do not assume any prior chat context.

Repository:
- ParamAItric: https://github.com/boxwrench/paramAItric

Context:
- ParamAItric should remain a Fusion-centered, AI-first controlled application.
- Product goal: human intent -> AI translation -> structured CAD operations -> Fusion 360 -> editable 3D object.
- The system already has validated workflow families, freeform sessions, verification gates, and a Fusion bridge.
- The system does not need a full backend-neutral architecture yet.
- It does need a cleaner internal operation language so workflow logic, selector logic, boolean intent, and parameter structure become more coherent.

Required sources to read first:
- `README.md`
- `ARCHITECTURE.md`
- `BEST_PRACTICES.md`
- `docs/AI_CONTEXT.md`
- `docs/AI_CAD_PLAYBOOK.md`
- `docs/NEXT_PHASE_PLAN.md`
- `mcp_server/schemas.py`
- `mcp_server/tool_specs.py`
- `mcp_server/workflow_registry.py`
- `mcp_server/workflows/`
- `fusion_addin/ops/live_ops.py`
- `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`

Research goals:
1. Define the minimum useful internal operation set ParamAItric should support first.
2. Clarify how operations should encode:
   - target geometry
   - selector inputs
   - boolean intent
   - placement
   - parameters
3. Identify what should remain Fusion-specific for now.
4. Avoid premature abstraction.

Questions to answer:
1. What are the 5-10 highest-value internal operations ParamAItric should standardize first?
2. What fields should each operation schema include?
3. Which current workflow patterns can be normalized through this vocabulary?
4. What should not be abstracted yet?
5. How should this internal operation language relate to:
   - workflow schemas
   - verification rules
   - future selector logic

Research method:
- Use the required repo sources above as the primary source of truth.
- Keep the recommendation grounded in near-term implementation reality.
- Separate:
  - observed facts
  - informed inferences
  - recommendations
- Cite relevant repo files by path when making repo-specific claims.

Deliver in this format:
1. Executive Summary
2. Why ParamAItric Needs a Narrow Internal Vocabulary
3. Proposed Core Operation Set
4. Draft Schema Shape for Each Operation
5. What Stays Fusion-Specific
6. What To Delay
7. Workflow Mapping Examples
8. Recommended Adoption Path
```

## 5. Reusable part-recipe architecture

### What this research should answer

- What a reusable part recipe should contain
- How recipes differ from current workflows and from freeform sessions
- How parameters, defaults, verification, and outputs should attach to a recipe

### Expected output

- a part-recipe template
- recommendations for refactoring current families
- guidance on boundaries between workflows and recipes

### Prompt

```text
Conduct deep technical research and design analysis for ParamAItric's reusable part-recipe architecture.

Do not assume any prior chat context.

Repository:
- ParamAItric: https://github.com/boxwrench/paramAItric

Context:
- ParamAItric already has validated workflow families.
- Product goal: human intent -> AI translation -> structured CAD operations -> Fusion 360 -> editable 3D object.
- The system currently has structured workflows and freeform sessions, but needs cleaner reusable architecture for repeatable part families.
- The next design need is a cleaner reusable structure for parameterized part definitions.
- This research should help ParamAItric reduce duplication, improve clarity, and produce more consistent editable output.

Required sources to read first:
- `README.md`
- `BEST_PRACTICES.md`
- `docs/AI_CONTEXT.md`
- `docs/AI_CAD_PLAYBOOK.md`
- `docs/NEXT_PHASE_PLAN.md`
- `mcp_server/workflow_registry.py`
- `mcp_server/workflows/base.py`
- `mcp_server/workflows/plates.py`
- `mcp_server/workflows/brackets.py`
- `mcp_server/workflows/cylinders.py`
- `mcp_server/workflows/enclosures.py`
- `mcp_server/workflows/specialty.py`
- `mcp_server/schemas.py`
- `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`

Research goals:
1. Define what a reusable part recipe should be in ParamAItric.
2. Distinguish recipes from workflows, macros, and freeform sessions.
3. Define the structure of a recipe:
   - inputs
   - defaults
   - constraints
   - stage sequence
   - verification hooks
   - outputs
4. Identify which current part families are the best first refactor candidates.

Questions to answer:
1. What should a recipe object contain?
2. How should recipes relate to schema definitions and parameter metadata?
3. How should verification be attached to recipes?
4. How should recipes support editability in Fusion?
5. Which current workflow families most need this refactor first?
6. What should remain workflow-specific and not become generic recipe machinery yet?

Research method:
- Use the required repo sources above as primary context.
- Focus on architecture and maintainability, not generic library design.
- Separate:
  - observed facts
  - informed inferences
  - recommendations
- Cite relevant repo files by path when making repo-specific claims.

Deliver in this format:
1. Executive Summary
2. Recipe Definition
3. Recipe vs Workflow vs Freeform Boundaries
4. Proposed Recipe Template
5. Best Refactor Candidates
6. Verification and Editability Implications
7. Recommended First Adoption Plan
```

## 6. Parameter relationship and expression strategy

### What this research should answer

- When to generate linked parameter expressions instead of isolated numeric values
- Which workflow families benefit most
- How to balance editability with simplicity

### Expected output

- expression-generation guidelines
- examples by part family
- do-now / later / avoid guidance

### Prompt

```text
Conduct deep technical research and design analysis for ParamAItric's parameter relationship and expression strategy.

Do not assume any prior chat context.

Repository:
- ParamAItric: https://github.com/boxwrench/paramAItric

Context:
- ParamAItric's product goal is editable Fusion geometry.
- ParamAItric is an AI-first CAD system, not a generic CAD library.
- It already has structured workflow families and needs clearer guidance on when relational dimensions improve editability versus when they just add complexity.
- Editability improves when dimensions reflect design intent and relationships, not just literal isolated numbers.
- This research should determine where expression-linked parameters provide real value and where they would just add complexity.

Required sources to read first:
- `README.md`
- `BEST_PRACTICES.md`
- `docs/AI_CAD_PLAYBOOK.md`
- `docs/NEXT_PHASE_PLAN.md`
- `mcp_server/workflow_registry.py`
- `mcp_server/workflows/`
- `mcp_server/schemas.py`
- `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`

Research goals:
1. Determine when ParamAItric should generate parameter expressions instead of raw duplicated values.
2. Identify which workflow families benefit most.
3. Recommend conventions for readable, maintainable parameter relationships.
4. Avoid over-complicating simple parts.

Questions to answer:
1. What kinds of dimensional relationships are most useful in ParamAItric?
2. Which part families benefit most from linked parameters?
3. What naming and expression conventions should be used?
4. When should expressions be avoided?
5. How should expression use interact with verification and user editability?

Research method:
- Use the required repo sources above as primary context.
- Focus on practical rules that improve editability.
- Separate:
  - observed facts
  - informed inferences
  - recommendations
- Cite relevant repo files by path when making repo-specific claims.

Deliver in this format:
1. Executive Summary
2. Why Parameter Relationships Matter
3. Recommended Expression Use Cases
4. Families That Benefit Most
5. Naming and Readability Rules
6. Cases To Avoid
7. Immediate Adoption Guidance
```

## 7. Fast-feedback geometry assertions and examples-as-tests

### What this research should answer

- What lightweight invariant checks are worth standardizing
- Which example workflows should become test references
- How to complement live Fusion validation without pretending mocks are enough

### Expected output

- a lightweight assertion checklist
- candidate example workflows to lock in as test references
- guidance on what should and should not be tested this way

### Prompt

```text
Conduct deep technical research and design analysis for ParamAItric's fast-feedback geometry assertions and examples-as-tests strategy.

Do not assume any prior chat context.

Repository:
- ParamAItric: https://github.com/boxwrench/paramAItric

Context:
- ParamAItric already values verified, staged execution and live Fusion correctness.
- Product goal: human intent -> AI translation -> structured CAD operations -> Fusion 360 -> editable 3D object.
- The system needs a complementary fast-feedback layer, not a replacement for live Fusion verification.
- It can still benefit from a stronger lightweight test and assertion structure for workflow examples and geometry invariants.
- This research should not recommend replacing live Fusion validation with mocks. It should define a complementary fast-feedback layer.

Required sources to read first:
- `README.md`
- `BEST_PRACTICES.md`
- `docs/VERIFICATION_POLICY.md`
- `docs/AI_CAD_PLAYBOOK.md`
- `mcp_server/workflow_registry.py`
- `tests/test_workflow.py`
- `tests/test_workflow_stages.py`
- `tests/test_validation.py`
- `tests/test_input_validation.py`
- `tests/test_fillet.py`
- `tests/test_chamfer.py`
- `tests/test_cut_extrusion.py`
- `internal/research/python-cad-inspiration-2026-04-07/SYNTHESIS.md`

Research goals:
1. Identify which lightweight geometry assertions are most useful for ParamAItric.
2. Determine which example workflows should become stable reference examples.
3. Define how fast-feedback tests should complement, not replace, live verification.

Questions to answer:
1. Which invariants are worth checking consistently?
2. Which workflow families are the best candidates for example-based assertions?
3. What should this test layer validate versus leave to live Fusion verification?
4. How should failures be reported so they help workflow hardening?

Research method:
- Use the required repo sources above as primary context.
- Focus on practical, repeatable, low-noise checks.
- Separate:
  - observed facts
  - informed inferences
  - recommendations
- Cite relevant repo files by path when making repo-specific claims.

Deliver in this format:
1. Executive Summary
2. Role of Fast-Feedback Assertions
3. Recommended Assertion Checklist
4. Recommended Example Workflows
5. Relationship to Live Fusion Verification
6. Reporting Guidance
7. Adoption Plan
```

## Guardrail

This plan should remain constrained by one stable rule:

Borrow architecture patterns to strengthen ParamAItric's own internals.

Do not let subsequent research turn into premature dependency adoption, premature backend abstraction, or broad ecosystem wandering before selector and reference reliability are stronger.
