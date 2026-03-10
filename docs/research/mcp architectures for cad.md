# Deep research on MCP server architectures for CAD automation

## Landscape and integration topologies observed in open-source CAD MCP servers

The entity["organization","Model Context Protocol","llm tool integration protocol"] (MCP) ecosystem is centered on a standardized way for LLM clients to call **tools**, read **resources**, and reuse **prompts**, so the system can ground an agent in external state instead of free-text guessing. The official project describes MCP as “an open protocol that enables seamless integration between LLM applications and external data sources and tools,” and notes it is hosted by entity["organization","The Linux Foundation","open source consortium"]. citeturn29view2turn29view0

Across the CAD-focused repositories reviewed, implementations cluster into three practical topologies:

**In-process CAD add-in + out-of-process MCP server (bridge architecture).**  
This is the most common pattern for GUI CAD apps where the API must run in the application’s main/UI thread. For example, one Fusion implementation explicitly separates a server component that “handles HTTP calls to [the] Fusion add-in” from add-in code that uses a “custom event handler” and “task queue” to satisfy main-thread constraints. citeturn22view0

**Out-of-process RPC to a CAD-side bridge (bridge + adapter variants).**  
For FreeCAD, multiple projects implement a dedicated bridge running inside FreeCAD (GUI or headless), while the MCP process uses RPC (XML-RPC / JSON-RPC socket / embedded) to issue commands and pull results back. The “bridge with adapter” framing is documented explicitly in the FreeCAD Robust MCP architecture writeup, including multiple deployment modes and an abstract bridge interface. citeturn5view1turn11view5

**CLI-wrapped CAD (deterministic compiler/render loop).**  
For OpenSCAD-style workflows, the MCP server can expose a deterministic tool surface by invoking the CLI compiler and returning exit codes, stdout/stderr, and generated artifacts (STL/3MF/PNG). The openscad-mcp project emphasizes a “stable, minimal, deterministic, and local-first” tool surface and provides explicit `validate_scad` and rendering tools. citeturn3view14turn6view0

A key cross-cutting operational detail appears in the MCP build-server guidance: **stdio-based MCP servers must never write regular logs to stdout**, because it corrupts JSON-RPC messages; logs should go to stderr or files. For CAD automation, where verbose diagnostics are valuable, this matters directly to reliability and error propagation. citeturn30view0turn30view3

## Anti-hallucination patterns and verification or commit gates

The core failure mode you called out—**CAD operations that fail silently** (or succeed but produce geometry somewhere unintended)—is treated less as a “prompt problem” and more as a **state-management + verification** problem in the strongest repositories.

### Prompt-level state machines and forced verification loops

A particularly explicit approach is to encode a *workflow state machine* in a “skill” / instruction document used by the client (rather than relying only on code). In the ClaudeFusion360MCP skill guide:

- Every session starts with a mandatory “Vision-First Verification” protocol before any commands run, including checking the visible CAD state and calling design inspection tools, explicitly to avoid “phantom issues” from stale state. citeturn26view0turn8view0  
- It also codifies a “Never auto-join” / “Join should be the final step” protocol that functions as a **commit gate** requiring user verification before irreversible merges, and recommends using undo/rebuild if errors are caught late. citeturn26view6turn26view5  
- It treats face/edge references as unstable across modeling steps (fillet/chamfer/shell/extrude), requiring immediate re-query after each operation and re-identification by geometry rather than index. This is a direct “hallucination prevention” mechanism: it forces the agent to ground each subsequent step in **fresh state** rather than assumed indices. citeturn26view4  

A companion “spatial awareness” doc turns geometry placement into a repeated loop: **declare intent → query current geometry → predict location/bounds → execute → re-measure** (plus a library of real error cases). This is not just advice; it’s an explicit “never assume spatial relationships—verify them programmatically” doctrine. citeturn9view2turn9view0

### Tool-surface level verification gates

Other projects implement verification more directly in the tool surface:

- **OpenSCAD MCP**: `validate_scad` provides `ok`, `exit_code`, `stdout`, `stderr`, and parsed `diagnostics`, making compilation an explicit gate before export. citeturn6view0  
  - Export and render calls accept options like `hardwarnings`, `check_parameters`, and `check_parameter_ranges`, which—architecturally—enable a “warnings are failures” mode and parameter validation before costly rendering. citeturn6view0  
- **Fusion/FreeCAD tool suites**: several servers explicitly list “validation tools” such as measurement, interference checks, timeline or state queries, and screenshots/camera control—i.e., they provide the primitives needed to implement “verify after each step” loops. citeturn3view7turn14view0  

### Reliability engineering gates (circuit breakers and fallbacks)

On the SolidWorks side, one TypeScript implementation emphasizes classic reliability mechanisms:

- “Circuit breaker pattern” (stop the bleeding after repeated failures, auto-recover), connection pooling, and an “intelligent fallback” ladder (Direct COM → dynamic VBA macro generation → emergency recovery suggestions). citeturn16view2turn3view15  
- It reframes a specific real-world failure mode (Node.js COM bridges failing at high parameter counts) into a routing rule: simple calls via COM, complex via macro generation. citeturn23search0turn16view0  

This architecture does two anti-hallucination things: (1) it reduces the chance the agent “thinks it executed” when calls fail; (2) it gives the system a deterministic fallback mechanism when the primary execution path is known to be brittle. citeturn16view2turn23search0

## Coordinate planes, coordinate systems, and spatial reasoning aids

Across CAD MCP servers, coordinate reasoning is addressed by combining **explicit plane semantics**, **standard views**, and **measurement-driven verification** rather than expecting the LLM to infer 3D placements from text.

### Explicit plane-to-world mapping and “gotcha” documentation

The strongest explicit treatment is again in the Fusion-oriented skill docs:

- The coordinate system is defined as right-handed and tied to the **Front view** mental model; XY/XZ/YZ plane usage is explained in terms of “ground plane / front wall / side wall.” citeturn8view0  
- Critically, it documents an “empirically verified” plane mapping rule for XZ/YZ sketches: when sketch coordinates map to world Z on those planes, the mapping is **negated** (the “Z-axis negation rule”), including concrete formulas for swapping/negating endpoints. citeturn9view2turn26view3  
- Offset planes are treated as first-class: offset on XY corresponds to world Z, offset on XZ corresponds to world Y, etc., turning “place a sketch at height” into a predictable parameter rather than ad-hoc transforms. citeturn9view2turn8view0  

From an architectural standpoint, the major insight is that coordinate-system handling isn’t only built into code; it is often **packaged as reusable guidance artifacts** (skill files) that operate like a deterministic “coordinate reasoning module” for the agent. citeturn4view5turn9view0

### View and camera tools as spatial grounding instruments

Several implementations treat “camera control + snapshot” as a primary grounding channel:

- The FreeCAD MCP server provides `get_view` to return screenshots of named canonical views (Isometric, Front, Top, Right, etc.) and also supports focusing on specific objects, while explicitly failing gracefully (text note) when the current view type cannot produce a screenshot (e.g., TechDraw/Spreadsheet). citeturn28view5turn28view1  
- OpenSCAD MCP exposes `render_preview` options including `camera`, `projection` (orthographic vs perspective), `viewall`, and `autocenter`, and can attach image content directly in tool results when artifacts are small enough—an architecture that is deliberately built for an “LLM looks at the preview, then adjusts parameters” loop. citeturn6view0  

### Programmatic plane handling in the CAD bridge layer

The FreeCAD Robust MCP architecture doc demonstrates how plane handling is often implemented concretely: creating a sketch by selecting a plane key ("XY"/"XZ"/"YZ") maps to a normal vector used to rotate the sketch placement, followed by document recompute. citeturn11view3turn10view10  

This is a useful general pattern for CAD MCP tooling: represent planes as **small enums** that map to explicit transform primitives, and always “commit” the transform via a recompute/regenerate step that can fail loudly. citeturn11view3turn10view10

## Assemblies, joints, and constraints across platforms

Assemblies expose a second class of “silent failure”: constraints can be accepted but under-defined, or mates/joints can attach unintended geometry when selection context is wrong.

### Fusion-centric assembly tool surfaces

The zkbkb Fusion MCP server explicitly includes “assembly tools” such as:

- `create_component`, `insert_component_from_file`, `get_assembly_info`, plus constraint/joint creation (`create_mate_constraint`, `create_joint`), interference checks, and even exploded views/animation tools. citeturn12view7turn12view8  

This indicates a design philosophy: assemblies are not “scriptable later”; they are treated as a first-class tool category with dedicated introspection (`get_assembly_info`) and validation (`check_interference`). citeturn12view7turn12view8  

Separately, another Fusion MCP server advertises “Assembly Tools - Create components, manage occurrences, build joints” and “Validation Tools - Measure distances, check interference,” suggesting similar surface area even when the README is high-level. citeturn14view0

### FreeCAD and constraints

FreeCAD’s parametric model makes sketch constraints a crucial correctness locus. The FreeCAD Robust MCP architecture includes a `validate_model` tool with switches for `check_geometry` and `check_constraints`, explicitly naming constraints as a validation target. citeturn10view7turn11view4  

However, the same architecture doc is transparent that full “Assembly Support” is a planned feature (e.g., integrating with Assembly3/4 workbenches), implying that in current open-source MCP servers, FreeCAD assemblies may often be achieved either via executing Python/macros directly or via future work rather than fixed high-level tools. citeturn11view6

### SolidWorks: workflows, resources, and state inspection

The C# SolidWorks MCP server (SW_MCP) uses a notably explicit architecture split:

- **High-level deterministic workflow tools** (create part/assembly, create sketch on planes, create extrude, etc.).  
- **Dynamic API execution** for arbitrary method calls, but with honest limitations (“barely works” for complex calls, “depends on permissions,” “doesn’t work” due to selection maintenance).  
- **Resources for state inspection**, including a feature tree resource so the agent can read the model’s hierarchical state rather than guessing what features exist.  
- **API documentation search** as a built-in capability. citeturn25view0  

This “tools + resources + docs-search” trio is especially relevant to assemblies/constraints because mate/joint creation is highly selection-sensitive: exposing the feature tree and active document state provides the raw materials for verifying that the *intended* entities are selected and mated. citeturn25view0  

In the SolidworksMCP-TS system, assemblies are first-class (“create_assembly”), with validation tools like interference detection and bounding boxes. citeturn16view0turn16view1  

## Error propagation, main-thread constraints, and returning actionable failures

A consistent theme is that CAD APIs are often not thread-safe and must execute on the main application thread (or in a constrained GUI context). The architectural question is: “How do you accept async tool calls but execute safely and return errors reliably?”

### Fusion patterns: event-driven UI-thread execution with queues

One Fusion MCP repo states the constraint plainly: the API “requires all operations to run on the main UI thread,” and describes its solution as:

- Event-driven design via a CustomEvent system  
- A task queue for sequential execution  
- An async bridge (HTTP server) to accept MCP requests while the CAD add-in processes them in-order citeturn22view0  

This is a canonical pattern for GUI CAD: treat CAD operations as a **serialized command stream**, and treat the bridge as an **adapter** that converts async requests into scheduled main-thread jobs plus structured responses.

A different Fusion server emphasizes operational resilience by running “as a background thread in Fusion 360 to maintain responsiveness,” supporting both HTTP SSE and a file-based fallback channel for environments that can’t connect directly. citeturn15view0turn15view3  

### FreeCAD patterns: “execute in main thread,” capture outputs, timeouts, structured errors

The FreeCAD Robust MCP architecture doc provides unusually concrete mechanisms:

- It runs a socket server in a background thread and schedules execution back onto FreeCAD’s main thread using a timer mechanism (Qt). citeturn11view0turn10view4  
- It captures stdout/stderr during execution and returns those in structured results, which is critical when CAD APIs fail silently but still emit console diagnostics. citeturn11view1turn10view4  
- It enforces timeouts (both async wait_for and thread event wait). citeturn10view5turn10view4  
- It defines explicit error categories (ConnectionError, ExecutionError, TimeoutError, ValidationError) and shows an error response format that includes type, message, traceback, and contextual info like code snippets and line numbers. citeturn11view6turn10view1  

That error response design is one of the best examples of **propagating actionable failure back to the MCP caller**: it gives the agent enough evidence to branch (“retry,” “undo,” “rebuild,” “request user input”) rather than rationalizing over missing state. citeturn11view6turn10view2

A lighter FreeCAD MCP server (neka-nat) shows a pragmatic variant: the MCP server uses XML-RPC to a FreeCAD addon and attempts to “ping” on startup, warning if FreeCAD is unavailable. It also wraps screenshot capture with defensive checks and returns an informative text note instead of raising when the active view cannot generate images. citeturn28view0turn28view1  

### OpenSCAD: exit codes as the simplest error contract

The OpenSCAD MCP server’s `validate_scad` and `export_model`/`render_preview` APIs expose `exit_code`, stdout/stderr, and diagnostics, so the failure contract is inherently explicit. It also documents that the server is local-first and invokes the OpenSCAD CLI (not arbitrary Python), framing security and error containment as part of the architecture. citeturn6view0turn6view1  

## Synthesis: the cleverest architectural decisions and safeguards to reuse

This section distills patterns that repeatedly showed up as “high leverage” for reducing hallucinations and stabilizing CAD automation.

### Treat “model state” as a first-class resource, not an implied side effect

The most robust systems expose explicit read tools/resources—design info, body info, feature trees, bounding boxes, measurement, and interference checks—so the agent can ground decisions in **observed state**, not guesses. This is explicit in the Fusion skill documents’ repeated “measure/predict/verify” loop, in SolidWorks servers that expose feature tree resources, and in OpenSCAD’s validate/render pipeline returning diagnostics. citeturn9view2turn25view0turn6view0  

### Use explicit gates for irreversible operations

Human verification gates (e.g., “never auto-join; ask user before combine/join”) are a simple but powerful safety device, especially when the CAD API’s selection/indexing is unstable. The Fusion skill guide formalizes this as a hard rule. citeturn26view6  

A more automated analogue is “validate then commit”: FreeCAD’s `validate_model` and OpenSCAD’s `validate_scad` are examples of explicit validation hooks you can require after each operation batch. citeturn10view7turn6view0  

### Encode coordinate reasoning as reusable, testable artifacts

The “Z-axis negation” plane mapping rule and coordinate mapping tables are a striking example of turning a subtle spatial bug into deterministic logic with examples and test cases. Architecturally, this suggests that your MCP system benefits from:

- A canonical coordinate mapping module (possibly unit-tested)  
- A prompt-side skill/instructions file that forces the agent to use that mapping  
- Measurement-based checks (e.g., bounding boxes) to validate outcomes citeturn9view2turn26view3turn9view0  

### Serialize CAD execution through a main-thread queue, but keep the bridge async

For GUI CAD, the well-supported pattern is: accept requests asynchronously in the MCP server (HTTP/stdio), but execute them **sequentially** via a CAD-side queue scheduled on the main/UI thread. This is described explicitly for Fusion (CustomEvent + task queue + async bridge). citeturn22view0  

FreeCAD Robust MCP shows the analogous approach (background thread server, schedule execution via Qt timer into main thread) plus timeouts and output capture. citeturn11view1turn10view4  

### Bake reliability engineering into the execution substrate

SolidworksMCP-TS demonstrates a mature stance: instead of pretending the COM layer is uniformly reliable, it includes:

- A circuit breaker (protects server and CAD session from repeated cascading failures)  
- Connection pooling (resource hygiene)  
- A route/fallback ladder that maps known-brittle operations to more reliable execution modes (dynamic VBA macro generation) citeturn16view2turn23search0  

This is effectively “anti-hallucination by design”: the system is built so that tool calls are less likely to fail or hang silently, and failures become structured and statistically tracked. citeturn16view0turn16view2  

### Ground API usage by shipping an API-docs MCP server alongside the CAD-control server

One Fusion-oriented project is explicitly an MCP server for **Fusion 360 Python API documentation** rather than direct CAD control: it can search/fetch docs, query a local API index, and generate add-in/script templates, including auto-updating its index by scraping official docs. citeturn7view3turn21search10  

Architecturally, pairing:
- a “CAD-control server” (execute operations) and  
- an “API-doc server” (ground code generation)  

creates a two-layer defense against hallucinated method names, parameters, and object models. citeturn7view3turn30view0