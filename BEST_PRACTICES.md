# ParamAItric Best Practices

## Purpose

Treat this as the live reference for real-world ParamAItric use.

It is where ParamAItric should capture the best-known prompting, staging, input contracts, verification defaults, and failure-handling rules as those improve through real workflows and real parts.

It serves two audiences at the same time:

- contributors extending the repo
- AI agents or hosts planning work against the repo

This document should stay short, opinionated, and easy to review. Change it when the project learns something durable, not for every temporary preference.

## Core rules

- Choose the narrowest existing workflow that can solve the task.
- Prefer a small useful part family over broader geometric coverage.
- Prefer real utility and maintenance parts with measurable interfaces over abstract benchmark geometry.
- Add only one new geometric or placement idea per workflow slice.
- When real use exposes a better prompting, staging, or input pattern, update this document.
- Write the stage sequence explicitly before implementing a new workflow.
- Validate dimensions, placement, and safety constraints before CAD operations run.
- Verify geometry after every major modeling milestone.
- Stop on failed verification instead of improvising wider retries.
- Preserve the last known-good partial result and report the narrowest corrective next step.
- Keep live smoke runs serial by default; the Fusion bridge is a single live execution path.
- After changing live add-in code, reload Fusion from the current checkout before trusting any live smoke rerun.
- Keep material, UV, chemical, and print-parameter recommendations in prompts or reference docs unless they change the geometry contract itself.
- Treat slicer-side union of overlapping meshes as a fallback for awkward print cases, not as the default geometry contract.

## Standard workflow shape

The default pattern is:

1. establish clean scene state
2. create the sketch on the intended plane or face
3. add one modeling milestone
4. verify the milestone
5. add the next feature only if the prior verification passed
6. verify again
7. export only after the final geometry checks pass

For most current mechanical workflows, that means a staged sequence close to:

1. `new_design`
2. `verify_clean_state`
3. `create_sketch`
4. sketch geometry creation
5. `list_profiles` or equivalent profile resolution
6. `extrude_profile`
7. `verify_geometry`
8. optional second sketch or feature stage
9. second verification
10. `export_stl`

## Validation before CAD ops

Validate numerically before sketch or body creation when possible.

Default expectations:

- positive, finite dimensions
- plane or face support is explicit
- hole centers, offsets, and clearances stay inside valid bounds
- fit-critical interfaces such as stem sockets, bolt patterns, mating surfaces, and wall thicknesses have explicit bounds
- new cuts or features are compatible with the current workflow stage
- output paths stay inside allowlisted locations

If a placement rule can be checked without Fusion, check it before sending the command.

## Verification after CAD ops

Every workflow should have a default verification checklist.

Use the smallest checklist that still makes the workflow trustworthy. Common checks are:

- expected sketch count
- expected profile count
- expected body count
- expected overall dimensions
- expected plane or face placement
- expected cut or fillet effect
- successful export artifact creation

Verification is part of the product, not cleanup.

If a workflow intentionally relies on slicer behavior rather than a true joined CAD body, call that out explicitly in prompts or docs. Do not let that assumption stay implicit.

## Failure handling

When a workflow fails, return enough structure for a narrow correction loop:

- failing stage
- failure classification
- last completed stage
- partial valid state
- suggested next step

Do not silently rebuild known-good geometry unless verification proves it is wrong.

## What counts as validated

A workflow should be called validated only after all of the following are true:

- schema validation covers its input contract
- mock or adapter-backed tests cover the stage sequence and failure cases
- the smoke runner can execute the path
- a serial live Fusion smoke run passes when a live path exists
- the artifact path or other evidence is recorded in `docs/dev-log.md`

## Workflow growth rules

Grow the catalog by increasing one dimension of difficulty at a time.

Preferred progression for this repo:

1. edge-offset placement
2. mirrored or symmetric placement
3. secondary face-relative features
4. local-region placement inside an existing body shape
5. inter-part fit and clearance relationships

Do not add unrelated geometry just because the API supports it.

## Real-part template rule

When a workflow is driven by a real replacement or maintenance part:

- keep the underlying CAD workflow generic and reusable
- separate interface dimensions from optional strength or clearance tuning
- keep environment and material advice outside the tool schema unless geometry must change because of it
- write tests around nominal fit, boundary clearances, and the specific failure mode that motivated the template
- prefer one practical template that reuses proven stages over a new primitive added without a real part need

## Current phase rule

The repo is now in a validated workflow family plus use-and-fix phase.

That means:

- finish practical in-flight slices before broadening scope
- let real part needs drive the next workflow expansions
- keep reliability and failure clarity ahead of geometry breadth

## Prompting guidance for AI hosts

When using ParamAItric from an AI prompt or host:

- identify the target workflow first
- identify the real part family and critical interface dimensions before proposing geometry changes
- stay inside validated scope unless the task is explicitly a new narrow slice
- state the intended stages before issuing commands when the workflow is new or modified
- verify after each major step instead of batching many dependent mutations
- ask for or propose the narrowest correction when verification fails

This repo should reward staged, testable execution rather than clever one-shot prompting.
