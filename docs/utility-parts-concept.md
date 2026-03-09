# ParamAItric - Utility and Maintenance Parts Concept

## Status

This is a non-canonical reference note. The canonical project definition remains in [PROJECT_CONTEXT.md](/C:/Github/paramAItric/PROJECT_CONTEXT.md).

Its purpose is to inform workflow priorities, test direction, and real-part template selection without changing the core architectural contract.

## Problem

Water treatment, wastewater, and general utility infrastructure depend on small parts that are cheap to manufacture but expensive or slow to replace through normal procurement.

Common examples:

- a molded valve handle fails and the vendor only sells the full valve assembly
- a discontinued mounting bracket turns into a long backorder item
- a simple adapter plate is needed to mate new equipment to an old footprint

These parts are usually:

- geometrically simple
- defined by a small number of measurable dimensions
- expensive because of niche supply, not geometry complexity
- needed quickly because equipment downtime matters
- candidates for improvement over the original part

## Thesis

ParamAItric already covers many of the geometry families these parts belong to:

- brackets
- plates
- spacers
- cut features
- edge finishing
- simple box and lid forms

The missing layer is practical context:

- which part family to target first
- which interface dimensions matter most
- which environment or material questions an AI host should ask up front

The core repo should stay generic. The utility-part lane should drive template choice, test cases, and prompt guidance, not force the MCP server to become a material expert system.

## Target part families

### Valve components

- quarter-turn ball valve handles
- valve stem socket replacements
- butterfly valve handle extensions
- gate valve handwheel replacements

### Mounting and brackets

- instrument mounting brackets
- pipe clamp adapters for non-standard outside diameters
- panel mounting brackets
- sensor clips and holders
- equipment shims and spacers

### Enclosures and covers

- field instrument covers
- terminal block covers
- splash guards
- sight glass guards

### Adapters and fittings

- pipe-to-instrument adapter plates
- pump base adapter plates
- flange gasket retainers
- drain funnel adapters

### Labels and tags

- equipment identification tags
- valve position indicators
- sample point labels

## First template candidate

A valve handle or stem-socket replacement is a strong early template because it sits close to the repo's current validated vocabulary:

- sketch
- profile resolution
- extrusion
- cut
- fillet
- export

Candidate parameters:

- stem width
- stem depth
- socket type
- lever length
- lever thickness
- fillet radius
- clearance

This is useful because it tests a real failure mode while still reusing mostly proven operations.

## Material and environment guidance

Material and print guidance should stay outside the core CAD tool surface unless it forces a geometry change.

The AI host should ask about:

- part function
- indoor or outdoor use
- chemical exposure
- temperature range
- mechanical load
- regulatory constraints

The AI host can then recommend:

- primary filament
- backup filament
- wall or fillet adjustments
- print orientation
- infill and perimeter guidance
- post-processing when relevant

This is a prompt and reference-doc layer, not a new ParamAItric server feature.

## Dimensional reference sources

Useful sources for real-part templates:

- manufacturer exploded diagrams and dimensional drawings
- McMaster-Carr dimensions and CAD references for standard interfaces
- direct caliper measurements of the actual mating part

The rule for fit-critical parts is simple: nominal data is useful, but the actual interface should be measured whenever possible.

## What this means for workflows

The workflow engine should stay generic.

Real-part templates should usually be built as parameterized compositions of existing validated stages. A new template should only force a new primitive when the required geometry genuinely falls outside the current stage library.

Useful immediate directions:

- handle or socket geometry that reuses cut and fillet stages
- adapter plates that reuse validated plate and hole placement stages
- covers and guards that stay close to the current box-family lane

## What this means for tests

Tests should increasingly reflect real part risk:

- fit-critical interface dimensions
- clearances and tolerance defaults
- wall-thickness or reinforcement bounds
- failure cases tied to the motivating part
- repeatable routing through existing validated stages

The preferred pattern is not "add more geometry for coverage." The preferred pattern is "prove that a real replacement-part template fits, fails clearly, and stays inside the staged workflow contract."

## Relationship to core

This concept informs the project but does not redefine it.

- ParamAItric remains a constrained workflow system, not general AI CAD
- workflow templates should remain generic enough to reuse across domains
- material intelligence stays in prompts and docs unless geometry requires an explicit parameter
- the immediate focus remains dependable workflows, clear verification, and real usefulness

## Longer-range implications

The same architecture leaves room for later expansions, but they are not immediate priorities:

- additional CAD backends that implement the same operation contract
- STEP export and other fabrication-oriented outputs
- CNC and CAM follow-on work with much stricter verification gates
- broader workshop pipelines that choose between print, machine, or outsource paths
