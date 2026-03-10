# AI CAD Playbook

## Purpose

This document is a condensed, actionable reference for AI agents operating ParamAItric.
It distills research on CSG modeling, live benchmark findings, and proven workflow
patterns into rules and recipes an AI host can follow when planning and executing
CAD operations through the MCP tool surface.

Read this before planning a new part. Consult it when a workflow fails.

This complements `BEST_PRACTICES.md` (project-level rules) and `ARCHITECTURE.md`
(system-level contracts). It focuses specifically on **how to think about geometry**
within ParamAItric's constraint set.

---

## The Constraint Set

ParamAItric builds geometry using Constructive Solid Geometry (CSG). The available
primitives and operations are:

### Sketch Primitives
- Rectangle
- Circle
- Triangle
- Slot (rounded rectangle)
- L-bracket profile
- Revolve profile (Y-axis only, XY plane)

### Body Operations
- Extrude (new body or cut, on XY / XZ / YZ planes)
- Revolve (Y-axis, XY plane only)
- Combine bodies (boolean union)

### Finishing Operations
- Fillet (edge rounding)
- Chamfer (edge bevel)
- Shell (hollow out from a face)

### Inspection & Verification
- List profiles
- List design bodies (with bounding box and centroid)
- Get body info (volume, face count, edge count)
- Get body faces / edges
- Find face (semantic: top, bottom, left, right, front, back)

### What Is NOT Available
- Loft, sweep, spline, NURBS
- Arbitrary polyhedra
- Helical extrude
- Angled sketch planes (XY, XZ, YZ only)
- Linear or circular pattern operations
- Assembly joints or constraints

---

## Core Modeling Rules

### 1. Never draw the final shape — build it with cutters and masks

Complex geometry is constructed by combining simple solids with boolean operators.
The "hack" is the **sequence**, not the primitive. Think of each workflow as a
recipe of Add → Verify → Cut → Verify → Finish.

### 2. One mutation, then verify

In freeform mode, every geometry-altering operation must be followed by verification
before the next mutation. In pre-built workflows, this is enforced by the stage
structure. Never chain dependent operations without checking intermediate results.

### 3. Epsilon overlaps prevent silent failures

When two solids only touch along a face without volumetric overlap, boolean
operations can produce ambiguous or non-manifold geometry.

**Rules:**
- For union/combine: ensure intended joins have **positive overlap volume**
- For cut/difference: ensure cutters extend **slightly past** the target boundary
  so no coplanar residual surfaces remain
- The project constant is `BOOLEAN_EPSILON_CM = 0.001`

### 4. Extrusion orientation matters

This is the single most common source of geometry errors. Before extruding:

- **Decide which dimension is width, which is depth, which is height**
- A sheet-metal L-bracket is a thin cross-section extruded to full width, not a
  wide L-profile extruded to sheet thickness
- Verify the resulting bounding box immediately after extrusion

### 5. Plane coordinate mapping

Each sketch plane maps coordinates differently to world space:

| Sketch Plane | Sketch X → World | Sketch Y → World | Extrude → World |
|---|---|---|---|
| XY | +X | +Y | +Z |
| XZ | +X | **−Z** | +Y |
| YZ | **−Z** | +Y | +X |

> **Z-axis negation rule:** On XZ and YZ planes, one sketch axis maps to
> negative world Z. Use `geometry_utils.sketch_to_world()` when converting.

### 6. Verify after every milestone

Minimum verification checklist per stage:

| After... | Check |
|---|---|
| Sketch creation | Profile count matches expectation |
| Extrude (new body) | Body count = expected; bounding box sane |
| Extrude (cut) | Body count unchanged (no split); volume decreased |
| Fillet / Chamfer | Body count unchanged; edge count changed |
| Shell | Body count unchanged; volume decreased |
| Combine | Body count decreased by 1; volume ≈ sum |
| Export | File exists at expected path |

### 7. Stop on failure — do not improvise retries

When verification fails:
1. Report the failing stage and what was expected vs. actual
2. Preserve the partial valid state
3. Suggest the **narrowest corrective next step**
4. Do not silently rebuild known-good geometry

### 8. Verify the Centroid for Asymmetry

When building parts with tapers, offsets, or asymmetric feature patterns, a simple `body_count` check is insufficient. You must validate the **Centroid** (Center of Mass) returned by `get_body_info`.

- **Tapers:** If a bracket tapers toward the top (Y+), the centroid's Y-coordinate must be **lower** than the geometric center of the bounding box. If it is higher, your taper is likely inverted.
- **Asymmetric Holes:** If holes are concentrated on one side of a part, the centroid must shift away from that side.
- **Verification Strategy:** After a complex mutation, predict where the mass *should* move, then verify the shift in the `centroid` coordinates.

---

## CSG Recipes

These are reusable boolean logic patterns for common mechanical features.
Each recipe uses only the available primitives and operations.

### Flat Plate with Holes

```
1. Sketch rectangle on XY plane
2. Extrude → new body (plate thickness)
3. Verify: 1 body, bounding box matches L×W×H
4. For each hole:
   a. Create sketch on plate top face (or XY plane at offset)
   b. Draw circle at (cx, cy) with radius r
   c. Extrude cut (symmetric or through-all)
   d. Verify: still 1 body, volume decreased
5. Optional: fillet hole edges
6. Export
```

### L-Bracket (Sheet Metal Style)

```
1. Sketch thin L-profile cross-section on XY plane
   - Horizontal leg: width = material_thickness, length = leg_length
   - Vertical leg: width = leg_length, height = material_thickness
   - The cross-section is thin (e.g. 3mm), NOT the full bracket width
2. Extrude → new body to full bracket width (e.g. 50mm)
3. Verify: 1 body, bounding box = (leg_length × bracket_width × leg_length)
4. Apply fillet at inner bend (bend radius)
5. Verify: 1 body
6. Add mounting holes as circle-cut stages
7. Export
```

> **Common mistake:** Sketching the wide L-profile and extruding to material
> thickness. This produces a bracket with the wrong proportions — the vertical
> leg will be material_thickness wide instead of bracket_width wide.

### Flanged Bushing / Spacer

```
1. Sketch circle (outer diameter) on XY plane
2. Extrude → new body (bushing height + flange thickness)
3. Verify: 1 body
4. Sketch circle (bore diameter) on top face
5. Extrude cut through body (bore)
6. Verify: 1 body, volume decreased (now a tube)
7. Sketch circle (flange diameter) on XY plane
8. Extrude → new body (flange thickness only)
9. Combine flange body with tube body
10. Verify: 1 body, volume ≈ tube + flange ring
11. Optional: fillet flange-to-tube transition
12. Export
```

### Box with Lid (Enclosure)

```
Phase 1 — Box body:
1. Sketch rectangle on XY plane
2. Extrude → new body (total box height)
3. Shell from top face (wall thickness)
4. Verify: 1 body, volume < solid block volume

Phase 2 — Lid:
5. New sketch on XY plane
6. Draw rectangle (box outer dimensions + clearance)
7. Extrude → new body (lid wall height)
8. Shell from bottom face (wall thickness)
9. Verify: 2 bodies total
10. Optional: add lip/step feature for fit

Phase 3 — Fit verification:
11. Check lid inner dimensions > box outer dimensions by clearance
12. Export both bodies
```

### Revolved Part (Handle, Knob)

```
1. Create sketch on XY plane
2. Draw profile as half cross-section (right side of Y-axis)
   - Profile must not cross the Y-axis
   - Bottom of profile typically sits on X-axis
3. Revolve around Y-axis → new body
4. Verify: 1 body, bounding box is symmetric in X and Z
5. Optional: add socket cut, keyway, or grip features
6. Export
```

### Taper via Wedge Subtraction

```
1. Build the un-tapered body (full rectangular extrusion)
2. Create sketch on appropriate plane
3. Draw triangle defining the taper angle
4. Extrude triangle as cut (ensure cutter extends past body boundary)
5. Verify: 1 body, volume decreased, bounding box shows taper
```

### Taper via Intersection Limiter

```
1. Build the oversized body
2. Build a "limiter" body (large wedge or cone that defines the taper envelope)
3. The intersection of body ∩ limiter keeps only the drafted volume
Note: ParamAItric currently has combine (union) but not explicit intersect.
This pattern requires two subtractive cuts to simulate intersection.
```

### Circle Pattern (Manual Array)

```
For N features equally spaced on radius R:
  angle_step = 360 / N
  For i in 0..N-1:
    cx = R × cos(i × angle_step)
    cy = R × sin(i × angle_step)
    1. Create sketch
    2. Draw circle at (cx, cy)
    3. Extrude cut
    4. Verify: body count unchanged, volume decreased
```

> ParamAItric has no built-in circular pattern. Calculate positions explicitly.

---

## Snap-Fit Joints (CSG-Native)

Snap-fits are entirely buildable with rectangles, triangles, extrude, and cut.

### Cantilever Snap-Fit

**Male side (latch):**
```
1. Add base block
2. Add beam (thin rectangle extrude, merged at one end)
3. Add hook at free end (small rectangle extrude)
4. Optional: subtract root relief notch to tune stiffness
5. Fillet beam root to reduce stress concentration
```

**Female side (socket):**
```
1. Add housing block
2. Subtract entry pocket (rectangle cut)
3. Subtract undercut seat (secondary pocket for hook catch)
4. Subtract lead-in wedge (triangle cut for gradual deflection)
```

**Key parameters:** beam length, beam thickness (controls flex), hook depth
(controls retention force), clearance between male and female.

### Annular Snap-Fit (Cap/Plug Style)

**Male (plug):**
```
1. Add cylinder
2. Add bead ring (union slightly larger cylinder segment)
3. Chamfer bead edge for lead-in
```

**Female (socket):**
```
1. Add outer cylinder
2. Subtract inner bore
3. Subtract groove ring (annular channel for bead)
4. Chamfer entry for lead-in
```

---

## Bayonet / Twist-Lock (CSG-Friendly Alternative to Threads)

Prefer bayonet locks over threads when:
- Quick engage/disengage is acceptable
- Printer resolution makes fine threads unreliable
- Limited lock positions are tolerable

**Female (slot housing):**
```
1. Add outer cylinder
2. Subtract inner bore
3. For each lug position:
   a. Subtract radial entry slot (rectangle cut from bore outward)
   b. Subtract tangential twist slot (rectangle cut rotated around axis)
4. Optional: subtract ramp wedge at lock end for preload
```

**Male (lug plug):**
```
1. Add plug cylinder
2. Add lug blocks (rectangle extrude, union onto shaft)
3. Chamfer lug edges for smoother engagement
```

---

## Mating Surface Rules

### Global Clearance Parameter

All male/female pairs need a consistent clearance offset. Apply it symmetrically:

- **Holes:** increase radius by clearance value
- **Plugs / pins:** decrease radius by clearance value
- **Pockets:** increase dimensions by clearance value
- **Tabs / tongues:** decrease dimensions by clearance value

Typical values for FDM printing: 0.15 mm – 0.30 mm per side.

### Fit-Critical Verification

For any part with mating surfaces:
1. Verify male bounding box + 2 × clearance ≤ female pocket dimensions
2. Check that clearance is consistent across all mating features
3. If bolt patterns exist, verify hole center distances match between parts

---

## Common Mistakes and Fixes

| Mistake | Symptom | Fix |
|---|---|---|
| Wrong extrusion orientation | Bounding box dimensions swapped | Re-sketch as cross-section, extrude to full width |
| Coplanar cut surface | "Did not intersect" error or zero-volume result | Extend cutter by epsilon past boundary |
| Cut on wrong plane | Holes on wrong face | Check plane-to-world coordinate mapping table |
| Multiple bodies after cut | Body count increased | Cut distance too short; use symmetric or through-all |
| Fillet fails | Edge not found or radius too large | Reduce fillet radius; ensure edge exists post-boolean |
| Shell fails | Face not found | Apply shell before cuts that remove the target face |
| YZ plane confusion | Features offset or mirrored | Apply Z-negation rule for YZ/XZ sketches |

---

## Workflow Planning Checklist

Before starting any new part workflow:

- [ ] Identify the closest existing workflow family
- [ ] List the critical interface dimensions (what must fit)
- [ ] Decide sketch plane for each feature
- [ ] Write the stage sequence before issuing any commands
- [ ] Identify verification checks for each stage
- [ ] Determine clearance / slop values for mating surfaces
- [ ] Confirm all features can be built with available primitives

---

## When to Use Freeform Mode vs. Pre-Built Workflows

| Situation | Use |
|---|---|
| Part matches an existing `create_*` workflow | Pre-built workflow |
| Part is a parameterized variant of existing family | Pre-built workflow |
| Part requires novel geometry or untested combinations | Freeform session |
| Exploring a new part family for future workflow extraction | Freeform session |
| Part has > 3 novel features not in any existing workflow | Freeform session |

In freeform mode, the state machine enforces:
```
AWAITING_MUTATION ──[mutation tool]──> AWAITING_VERIFICATION
                                              │
                                  [commit_verification]
                                              │
AWAITING_MUTATION <────────────────────────────┘
```

`commit_verification` requires machine-checkable assertions:
- `expected_body_count` (server validates against actual)
- `expected_volume_range` [min, max] (optional, server validates)
- `notes` (forces the agent to articulate reasoning)

If assertions fail, the state remains locked. The agent must inspect, understand,
and either correct expectations or fix the geometry.

---

## Deferred Capabilities (Not Yet Available)

These features are recognized as valuable but are not yet implemented:

- Threads (helical extrude required — use bayonet locks instead)
- Angled sketch planes
- Linear / circular pattern operations
- Assembly joints and constraints
- Rollback / undo within freeform sessions
- STEP export
