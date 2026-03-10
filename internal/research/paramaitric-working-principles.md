# ParamAItric Working Principles

Status: provisional research note

## Intent

These are not fixed product rules. They are current working principles based on live Fusion benchmark evidence. They should be revised as more tests are run.

## 1. Treat workflow as the product

The most important lesson so far is that the workflow and step sequence matter as much as the available operations.

Useful default pattern:
1. establish clean scene state
2. build one milestone
3. verify
4. continue
5. clean up only after the milestone is known-good

ParamAItric should be opinionated about workflow sequencing, not just about which tools exist.

## 2. Optimize for first-pass usefulness, not one-shot perfection

The system does not need to be fully autonomous to be valuable.

A realistic and useful operating model is:
1. agent builds the first viable version
2. human inspects it
3. human requests narrow corrections
4. agent applies targeted revisions

This suggests ParamAItric should explicitly support correction loops rather than pretending every run should end as a final part.

## 3. Keep mechanical workflows central

The strongest evidence so far comes from:
- enclosures
- lids
- mugs and vessels
- brackets
- repeated patterned features
- structured assemblies

The weakest evidence so far comes from:
- freeform decorative detail
- curved decorative text
- organic branching cleanup
- threads

ParamAItric should stay centered on functional parametric CAD for mechanical parts and fabrication-oriented geometry.

## 4. Distinguish internal capability from exposed workflow

Broad tool availability did not by itself break sessions.

That suggests ParamAItric may eventually support a wider internal operation set than the user-facing workflow surface.

Working idea:
- internal layer: enough typed operations to solve real CAD tasks
- exposed layer: a smaller set of validated workflows and templates

## 5. Require verification as a normal step

Verification should not be optional cleanup. It should be part of the workflow.

Examples:
- verify body count
- verify names
- verify dimensions
- verify open-top state
- verify separate-vs-merged bodies
- verify no duplicate final candidates remain

ParamAItric should likely standardize a default verification checklist per workflow type.

## 6. Separate geometry correctness from world placement

Some benchmarks produced the right geometry in the wrong orientation or position.

That suggests ParamAItric should treat:
- geometric construction
- final placement/orientation

as separate concerns when helpful.

## 7. Preserve clean negative results

Not every failure should trigger endless retries.

Examples:
- thread creation repeatedly failed
- some organic builds became messy after too many recovery attempts

ParamAItric should know when to stop, preserve a clean partial result, and report that the workflow hit a limit.

## 8. Prefer staged multi-part builds

Multi-part fits and closures worked better when staged:
- body first
- mating part second
- fit or closure logic third

This should likely become a standard workflow rule in ParamAItric.

## 9. Design for human correction prompts

Good correction requests look like:
- increase clearance by 0.15 mm
- thicken handle root by 1 mm
- move pin radius outward by 0.2 mm
- keep names and only change fit geometry

ParamAItric should likely shape the UX around precise correction loops, not just initial requests.

## 10. Stay provisional

Current belief:
- workflow discipline, validation, and narrow mechanical workflows are the strongest path

But this is still a research conclusion, not a fixed law. New benchmarks may change where the best boundary really is.
