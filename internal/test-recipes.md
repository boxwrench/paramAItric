# ParamAItric Test Recipes

This file is the recipe corpus for session-to-session validation work.
It is not the freeform architecture spec.
For system behavior and runtime rules, see `internal/freeform-architecture.md`.
Treat the recipes and any companion runners as working validation artifacts unless they are separately promoted into tests or canonical docs.

Concrete part specifications for progressive workflow development and system validation.
Each recipe is written as a user request with real dimensions, followed by the
verification coverage it exercises.

---

## Recipe 1 - Snap-Fit Enclosure with View Holes
**Status:** COMPLETED - lid now wraps over box (box + 2xwall + clearance), bead combined into lid

**User request:**
> Create a project enclosure box, 10cm wide x 8cm deep x 6cm tall, 0.3cm wall
> thickness. The lid should be 0.5cm thick with a snap bead ring on the underside -
> bead is 0.3cm wide x 0.15cm tall with 0.02cm clearance per side. Cut a 2cm diameter
> circular view hole through the front wall, centered 2.5cm from the bottom. Cut a
> 1.5cm diameter circular view hole through the right side wall, centered 2.0cm from
> the bottom. Export box and lid as separate STL files.

**Dimensions:**
- `box_width_cm`: 10.0, `box_depth_cm`: 8.0, `box_height_cm`: 6.0
- `wall_thickness_cm`: 0.3, `lid_height_cm`: 0.5
- `snap_bead_width_cm`: 0.3, `snap_bead_height_cm`: 0.15, `clearance_cm`: 0.02
- `front_hole_diameter_cm`: 2.0, `front_hole_center_z_cm`: 2.5
- `side_hole_diameter_cm`: 1.5, `side_hole_center_z_cm`: 2.0

**Verification coverage:**
| Check | Type |
|---|---|
| Body count after shell | `expected_body_count` |
| Volume decreased after shell | `expected_volume_range` |
| 2 bodies after lid created | `expected_body_count` |
| Front hole on correct face (XZ plane) | `get_body_info` cylindrical face count |
| Side hole on correct face (YZ plane) | `get_body_info` cylindrical face count |
| Bead OD + 2xclearance <= box inner dimensions | Dimensional assertion |
| Both STL files exported | File existence |

**New capabilities tested:** Shell, XZ-plane cut, YZ-plane cut, multi-body export

---

## Recipe 2 - Telescoping Nesting Containers
**Status:** COMPLETED - concentric placement fixed and visually verified

**User request:**
> Create three nesting rectangular containers. The outer container is 12cm x 10cm x
> 8cm with 0.3cm walls. The middle container fits inside with 0.2cm clearance all
> around (so 11.4cm x 9.4cm x 7.5cm outer, 0.3cm walls). The inner container fits
> inside the middle with 0.3cm clearance all around (so 10.8cm x 8.8cm x 7.0cm outer,
> 0.3cm walls). All open-top boxes. Export all three as separate STL files.

**Dimensions:**
- Outer: `width`: 12.0, `depth`: 10.0, `height`: 8.0, `wall`: 0.3
- Middle: `width`: 11.4, `depth`: 9.4, `height`: 7.5, `wall`: 0.3, `clearance`: 0.2
- Inner: `width`: 10.8, `depth`: 8.8, `height`: 7.0, `wall`: 0.3, `clearance`: 0.3

**Verification coverage:**
| Check | Type |
|---|---|
| Volume of each shell within expected range | `expected_volume_range` |
| Middle outer bbox < outer inner bbox | Dimensional containment |
| Inner outer bbox < middle inner bbox | Dimensional containment |
| Progressive wall thinning shows clearance math is correct | Dimensional assertion |
| 3 bodies / 3 exports | `expected_body_count` + file existence |

**New capabilities tested:** Multi-part coordinated dimensioning, progressive clearance system, containment verification

---

## Recipe 3 - Slotted Flex Panel (Living Hinge)
**Status:** COMPLETED - slot centering fixed and visually verified

**User request:**
> Create a flat rectangular panel 15cm wide x 10cm deep x 0.4cm thick. Cut a row of
> 5 evenly spaced rectangular slots through the panel thickness, each slot 8cm long
> x 0.2cm wide, leaving 1.0cm of solid material at each end. Slots are centered on
> the panel length axis, spaced 1.0cm apart (center to center). Leave 1.0cm solid
> borders at the top and bottom of the panel. Apply 0.05cm fillets to all slot
> edges. Export STL.

**Dimensions:**
- `panel_width_cm`: 15.0, `panel_depth_cm`: 10.0, `panel_thickness_cm`: 0.4
- Slot count: 5, `slot_length_cm`: 8.0, `slot_width_cm`: 0.2
- `slot_spacing_cm`: 1.0 (center to center), `end_margin_cm`: 1.0
- `edge_fillet_radius_cm`: 0.05

**Verification coverage:**
| Check | Type |
|---|---|
| Body count unchanged after each slot cut | `expected_body_count` |
| Volume decreases by slot volume after each cut | `expected_volume_range` |
| Centroid Y remains centered (symmetric slots) | Centroid assertion |
| Edge count increases after each fillet | Edge count delta |
| Cumulative volume = panel - 5 x slot volume | Final `expected_volume_range` |

**New capabilities tested:** Manual slot array (no pattern tool), cumulative volume tracking, fillet on thin-feature edges

---

## Recipe 4 - Ratchet Wheel
**Status:** COMPLETED - tooth geometry redesigned to cut outer silhouette (cutter extends beyond outer_radius)

**User request:**
> Create a ratchet wheel 6cm outer diameter, 0.8cm thick, with a 1.0cm center bore.
> Cut 10 asymmetric teeth around the outer edge: each tooth is a right triangle with
> a 0.5cm gentle slope face (engagement side) and a 0.1cm vertical drop face (locking
> side). Tooth height is 0.4cm. The outer cylinder remains as the root circle between
> teeth. Apply 0.05cm fillets to all tooth tips. Export STL.

**Dimensions:**
- `outer_diameter_cm`: 6.0, `thickness_cm`: 0.8, `bore_diameter_cm`: 1.0
- `tooth_count`: 10, `tooth_height_cm`: 0.4
- `slope_width_cm`: 0.5, `locking_width_cm`: 0.1
- `tip_fillet_cm`: 0.05

**Tooth coordinate generation** (manual, pre-calculated):
Each tooth = 36 degrees apart. For tooth i at angle theta = i x 36 degrees:
- Triangle vertices calculated from root circle (r=2.7cm) to tip circle (r=3.1cm)
- Engagement face at theta, locking face at theta + about 3 degrees

**Verification coverage:**
| Check | Type |
|---|---|
| Body count = 1 throughout | `expected_body_count` |
| Volume after each tooth cut within range | `expected_volume_range` |
| Centroid remains approximately at origin (symmetric cuts) | Centroid X/Y ~= 0 |
| Cylindrical face count = 2 (outer + bore) | Face type assertion |
| Final volume significantly less than solid cylinder | `expected_volume_range` |
| Edge count increases with each fillet | Edge count delta |

**New capabilities tested:** Manual wedge array, volume tracking across many sequential cuts, centroid stability check for symmetric operations

---

## Recipe 5 - Wire Clamp with Strain Relief
**Status:** COMPLETED - bore positioning fixed via XZ plane Z-negation, visually verified

**User request:**
> Create a wire clamp for 6mm diameter wire. The clamp body is 4cm long x 3cm wide
> x 2cm tall. Bore a 0.35cm radius channel through the length (center of body, Y-axis).
> Taper the entry on both ends: cut a cone-shaped lead-in 0.8cm deep, widening from
> 0.35cm to 0.6cm radius. Add 4 internal grip ribs: rectangular protrusions 0.05cm
> tall x 0.1cm wide x full bore circumference, spaced 0.8cm apart along the bore.
> Cut a longitudinal split slot 0.1cm wide through the top face to allow the clamp
> to flex open. Export STL.

**Dimensions:**
- `body_length_cm`: 4.0, `body_width_cm`: 3.0, `body_height_cm`: 2.0
- `bore_radius_cm`: 0.35, `lead_in_depth_cm`: 0.8, `lead_in_exit_radius_cm`: 0.6
- `rib_count`: 4, `rib_height_cm`: 0.05, `rib_width_cm`: 0.1, `rib_spacing_cm`: 0.8
- `split_slot_width_cm`: 0.1

**Verification coverage:**
| Check | Type |
|---|---|
| Body count = 1 throughout | `expected_body_count` |
| Volume after bore < solid block | `expected_volume_range` |
| Volume after each taper cut | `expected_volume_range` |
| Volume after each rib protrusion | `expected_volume_range` (increases) |
| Cylindrical face count >= 3 (outer bore + ribs) | Face type assertion |
| Volume after split slot | `expected_volume_range` |
| Centroid X centered, Y slightly low (bore removes top mass) | Centroid assertion |

**New capabilities tested:** Internal feature protrusions (ribs), tapered bore entry, split slot, centroid as bore-axis verification

---

## Verification Coverage Matrix

Ensures every verification type is exercised across the recipe suite:

| Verification Type | Recipe 1 | Recipe 2 | Recipe 3 | Recipe 4 | Recipe 5 |
|---|---|---|---|---|---|
| `expected_body_count` | yes | yes | yes | yes | yes |
| `expected_volume_range` | yes | yes | yes | yes | yes |
| Centroid assertion | yes | no | yes | yes | yes |
| Bounding box dimensional | yes | yes | no | no | no |
| Containment (bbox A inside bbox B) | no | yes | no | no | no |
| Cylindrical face count | yes | no | no | yes | yes |
| Edge count delta (fillet/chamfer) | no | no | yes | yes | no |
| File existence (export) | yes | yes | yes | yes | yes |
| Multi-body coordination | yes | yes | no | no | no |

---

## Freeform Test Recipes

Freeform recipes test AI behavior inside the state machine, not just geometry correctness.
Each recipe targets a specific failure mode identified from live benchmarks.

---

### Freeform A - Custom Panel Mount Bracket
**Tests:** Archetype selection discipline

**User request:**
> I need a bracket to mount a 14cm x 9cm panel to a vertical surface. The bracket
> needs two holes on the vertical leg (0.4cm diameter, 2cm from each edge, centered
> height-wise) and two holes on the horizontal leg (same size, 1.5cm from each edge).
> Material thickness 0.35cm. Overall bracket width 5cm.

**Manifest:** `["L-profile body", "2 vertical leg holes", "2 horizontal leg holes", "inner bend fillet"]`

**Failure mode targeted:** AI selects Two-Plate instead of L-Profile. The fillet at the
inner bend is impossible on a Two-Plate result - edge count verification catches it.

**Verification coverage:** `expected_body_count`, cylindrical face count per leg, edge count after fillet, centroid shift after symmetric holes (should stay centered)

---

### Freeform B - Asymmetric Cable Guide
**Tests:** Hole normal discipline + multi-plane verification

**User request:**
> Design a cable guide box, 6cm x 4cm footprint, 2cm tall, 0.3cm walls, open top.
> Through the left wall cut a 1cm diameter hole centered 1cm from the bottom. Through
> the right wall cut a 0.8cm hole centered 1.5cm from the bottom. Through the front
> wall cut a 1.2cm wide x 0.8cm tall rectangular slot centered horizontally, 0.5cm
> from the bottom.

**Manifest:** `["Open box shell", "Left wall hole (YZ plane)", "Right wall hole (YZ plane)", "Front wall slot (XZ plane)", "Cylindrical face count verified"]`

**Failure mode targeted:** Cutting holes on the wrong plane - a YZ-plane hole that
should go through the left wall instead punches through the top or bottom.

**Verification coverage:** `expected_body_count` = 1 throughout, `expected_volume_range` decreases after each cut, cylindrical face count = 2 (left + right holes), centroid X shifts slightly due to different hole sizes

---

### Freeform C - Stepped Boss Plate
**Status:** LIVE-VALIDATED smoke recipe via [`scripts/freeform_recipe_c_smoke.py`](../scripts/freeform_recipe_c_smoke.py)

**Tests:** Non-monotonic volume tracking (volume goes up then down)

**User request:**
> Create a 10cm x 8cm x 0.4cm flat mounting plate. Add four corner mounting holes,
> 0.3cm radius, centered 1cm from each edge. In the center of the plate add a raised
> boss cylinder: 3cm outer diameter, 1cm tall. Bore the center of the boss: 1.5cm
> diameter, through the full plate thickness. Chamfer the top edge of the boss 0.1cm.

**Manifest:** `["Base plate", "4 corner holes (volume down)", "Central boss cylinder (volume UP)", "Boss bore (volume down)", "Top chamfer"]`

**Failure mode targeted:** AI provides `expected_volume_range` that only decreases.
The boss addition *increases* volume - if the AI doesn't account for this direction
change, the volume assertion fails.

**Verification coverage:** `expected_body_count`, `expected_body_count_delta`, `expected_volume_delta_sign`, audit-only volume observation, edge count after chamfer, centroid Z rises when boss is added then drops when bored

**Adopted live scope:** Base plate, four hole cuts, boss add/combine, and boss bore are live-validated. The top chamfer remains deferred until `apply_chamfer` is validated on this geometry path.

---

### Freeform D - Enclosure Lid with Retention Clips
**Tests:** Multi-body combine discipline + compliance audit gate

**User request:**
> Design a snap-on lid for a 10cm x 8cm box. The lid is 0.5cm thick, 10.4cm x 8.4cm
> outer (0.2cm overlap per side). On each long side add two cantilever retention clips:
> each clip is 1.5cm long x 0.3cm thick x 0.4cm tall, attached flush to the lid edge,
> with a 0.1cm hook protrusion at the free end. 4 clips total, evenly spaced on each
> long side.

**Manifest:** `["Lid plate body", "Clip 1 body + combined", "Clip 2 body + combined", "Clip 3 body + combined", "Clip 4 body + combined", "Final body count = 1"]`

**Failure mode targeted:** AI creates 5 separate bodies (lid + 4 clips) and declares
success without combining. `expected_body_count: 1` at end-of-session compliance
audit catches this - session cannot close until all clips are combined.

**Verification coverage:** `expected_body_count` after each combine decrements by 1, final volume = lid plate + 4 clip volumes, compliance audit gate at `end_freeform_session`

---

### Freeform E - Deliberate Failure and Recovery
**Status:** LIVE-VALIDATED recovery smoke concept; current adopted runner is simpler than the full cube-bore recipe

**Tests:** State machine lock behavior + AI recovery discipline

**User request:**
> Create a 5cm x 5cm x 5cm cube. Then bore a 2cm diameter hole through the center,
> top to bottom.

**Scripted behavior:** After the bore is cut, instruct the AI to commit verification
with an intentionally wrong hard-gate assertion. The state machine must stay locked.
The AI must then call `get_body_info`, diagnose the post-cut state, correct the bad
assertion, and successfully commit.

**Manifest:** `["Cube body", "Center bore cut", "RECOVERY: corrected body count assertion"]`

**Failure mode targeted:** AI either succeeds trivially (wrong assertion not tested)
or gets permanently stuck (no recovery). Pass condition is the AI diagnosing and
self-correcting within the locked state.

**Verification coverage:** Locked state persists on wrong assertion, failed `verification_signals` surface the bad assertion, inspection is required before recovery, corrected hard-gate assertion succeeds, session ends clean

**Current adopted runner:** [`scripts/freeform_failure_recovery_smoke.py`](../scripts/freeform_failure_recovery_smoke.py) currently uses a deterministic single-body plate extrusion rather than the full cube-plus-bore request above. That narrower shape is intentional: it isolates the recovery contract without depending on a less-settled subtractive path.

---

## Freeform Coverage Matrix

| Verification Type | FM-A Bracket | FM-B Cable Guide | FM-C Boss Plate | FM-D Lid Clips | FM-E Recovery |
|---|---|---|---|---|---|
| `expected_body_count` | yes | yes | yes | yes | yes |
| `expected_volume_range` | no | yes | yes (non-monotonic) | yes | yes |
| Centroid assertion | yes | yes | yes | no | no |
| Cylindrical face count | yes | yes | no | no | no |
| Edge count delta | yes | no | yes | no | no |
| Compliance audit gate | yes | yes | yes | yes | yes |
| Failure recovery | no | no | no | no | yes |
| Archetype check | yes | no | no | no | no |
| Hole normal discipline | no | yes | no | no | no |
| Multi-body combine | no | no | no | yes | no |

---

## Deferred Recipes (Blocked on Missing Capabilities)

| Recipe | Blocker |
|---|---|
| Print-in-Place Hinge | No boolean intersect; cannot simulate clearance separation |
| Ball Joint Socket | Steinmetz solid requires intersect boolean |
| Gothic Arch Cutter | Angled sketch planes not available |
| Heat-Set Insert Knurl | 50+ wedge cuts impractical; no circular pattern tool |
| Ratchet Pawl (spring arm) | Thin flexure geometry + spring simulation out of scope |
