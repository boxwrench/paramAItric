# Freeform Checklist

Use this at session start, before each mutation, and during recovery.

## Session Start

- write a shallow feature manifest
- make each feature measurable
- decide what final body-count contract should hold
- identify which features may be deferred and which may not

## Before Each Mutation

- state the single next mutation
- state why it is the smallest safe next step
- state what verification should prove immediately after it
- inspect first if plane, direction, body targeting, or booleans are involved

## Commit Gate

- did the mutation complete without health failure
- is body count what you expected
- did the expected geometric change actually happen
- does the result move a manifest item toward resolved status
- if not, do not commit progression

## Recovery

- do not guess blindly while locked
- inspect scene, body, face, or edge data first
- identify the narrowest failure cause
- retry narrowly, roll back, or defer explicitly
- do not build further on top of unhealthy topology

## Session End

- every manifest item is resolved or explicitly deferred
- no leftover helper or tooling bodies remain unless intended
- final geometry matches the intended part contract
- anything deferred is recorded with reason

## Promotion Gate

- has the recipe succeeded repeatedly in live Fusion
- can the manifest be reduced to deterministic inputs and checks
- does it complete without recovery loops
- would a structured workflow be clearly more reliable than keeping it freeform
