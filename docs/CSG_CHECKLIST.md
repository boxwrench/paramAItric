# CSG Checklist

Use this when planning or reviewing a structured workflow or a deterministic `create_*` slice.

## Before Modeling

- classify the part into the right construction archetype
- confirm the part can be built with current primitives
- write the intended stage sequence before coding
- validate critical dimensions, offsets, and clearances up front
- identify the expected body count after each major stage

## During Modeling

- add only one meaningful geometric idea per workflow slice
- prefer simple solids plus cutters over trying to sketch the final shape directly
- verify bounding box and body count after each major body or cut stage
- treat non-XY plane work as high risk and check coordinate mapping explicitly
- use epsilon overlap for booleans and through-cuts when needed

## Verification

- verify clean start state
- verify milestone geometry after each major stage
- verify final body count, dimensions, and export path before export
- stop on failed verification instead of improvising more geometry

## Review Gate

- is this a reusable deterministic pattern rather than a one-off experiment
- does the workflow add one new concept instead of several at once
- are the stage names and intent aligned with actual behavior
- do tests prove the geometry contract, not just `ok == True`

## Default Output Shape

1. validate inputs
2. create sketch on the intended plane
3. build one milestone
4. verify
5. build next milestone
6. verify
7. export only after final checks pass
