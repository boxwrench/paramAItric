# CSG-only CAD: expert patterns and boolean “hacks” for threads, snaps, tapers, and curves

## Constraint model and why expert users lean on “workflows” as much as geometry

Your constraint set—rectangles, circles, triangles → straight extrusions; then boolean combine/cut/intersect; then chamfers, fillets, and shell—is essentially “classical” entity["organization","Constructive Solid Geometry","solid modeling technique"] (CSG): complex solids are built by combining simple solids with boolean operators. citeturn10search37turn1search27

Two practical implications show up repeatedly in expert practice in both entity["organization","Tinkercad","autodesk web cad"] and entity["organization","OpenSCAD","script-based cad"]:

1) **You rarely “draw the final shape.” You build it by constructing cutters and masks.**  
In entity["organization","OpenSCAD","script-based cad"] the core operators are explicit: `union` keeps the sum (logical OR), `difference` subtracts later children from the first (AND-NOT), and `intersection` keeps only the overlap (logical AND). citeturn1search27 In entity["organization","Tinkercad","autodesk web cad"], the same idea exists via grouping modes (e.g., “Union group,” “Intersect group”) and “Hole” shapes that subtract when grouped. citeturn4view1turn14search20turn3search23

2) **The “hack” is often the *sequence*, not the primitive.**  
Experts treat boolean sequences as reusable “recipes.” The same cutters can be re-used as parametric tools (thread cutters, latch cutters, draft cutters, dome cutters), and the success/failure is driven by ordering, overlap, and tolerances (slop/clearance), not the sketch sophistication. citeturn13view4turn2view3turn14search0turn14search3

Because your agent cannot loft/sweep or rely on splines, the most transferable expert trick is **controlled discretization**: approximate a continuous feature (helix, cone, sphere) as a *stack* or *array* of small extruded primitives, then soften with fillets/chamfers/shell where allowed. This is also exactly how many OpenSCAD threading implementations work internally: they build many facets/segments and carefully align them for robustness. citeturn8view4turn8view3turn8view1

## Cross-platform “CSG power tools” experts use to unlock complexity

### Copy/array as a modeling primitive (especially in Tinkercad)

A recurring expert move in entity["organization","Tinkercad","autodesk web cad"] is to treat “Duplicate & Repeat” as the backbone of patterns (threads, slits, knurls, ribs, ratchets). The official shortcut sheet calls out **Duplicate/Repeat (Ctrl+D)** and **Intersect group (Ctrl+I)** and **Union group (Ctrl+G)**, plus Workplane (W) and Align (L). citeturn4view1

Third-party but widely taught workflow descriptions emphasize the same: Duplicate & Repeat “remembers the previous action” so a repeated transform sequence produces a precise pattern without manual re-measuring. citeturn3search15turn3search27

**Why it matters for your agent:** any “continuous” feature (helix, taper, dome) can be approximated as (a) a column of slices or (b) a circular array of identical wedges—both of which are just “repeat transforms.”

### Epsilon overlaps to prevent silent boolean failures

CSG engines and CAD boolean kernels can produce ambiguous geometry when solids only *touch* along a face/edge/point without overlapping volume. citeturn14search4turn14search3 Expert OpenSCAD users routinely introduce a tiny `epsilon` offset so parts overlap (or separate) by a negligible amount, preventing coplanar/zero-volume artifacts. citeturn14search0turn14search3turn14search10

**CSG-only rule of thumb (portable to your agent):**  
- For a `union`, ensure intended “joins” have **positive overlap volume** (not just touching).  
- For a `difference`, ensure cutters extend **slightly past** the target boundary so no coplanar residual surfaces remain. citeturn14search3turn14search9

### Slop/clearance as a first-class modeling parameter

Advanced OpenSCAD libraries formalize printer compensation as a **global slop** parameter: the BOSL2 docs recommend adding a single `$slop` to mating surfaces; for holes, increase radius by `get_slop()` or diameter by `2*get_slop()`. citeturn13view4 They also warn slop varies with printer, material, slicer settings, and orientation, and provide a calibration procedure. citeturn13view4

Even if your agent is platform-agnostic, adopting *one uniform slop variable* and applying it systematically to all “male/female” pairs is one of the most effective “anti-hack-hack” decisions because it converts ad-hoc tuning into repeatable rules. citeturn13view4turn2view3

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["OpenSCAD threads.scad polyhedron screw thread example","Tinkercad duplicate and repeat Ctrl+D tutorial screenshot","OpenSCAD BOSL2 rabbit_clip joiner snap fit socket","Steinmetz solid intersection of cylinders visualization"],"num_per_query":1}

## Threads, screw threads, and twist-lock mechanisms

This section covers two families: (a) helical threads (hardest under your constraints) and (b) twist-lock/bayonet mechanisms (often easier in pure CSG and widely used in consumer lids).

### Threads: what expert OpenSCAD libraries do and how to translate to primitive-only CSG

Two prominent OpenSCAD thread libraries illustrate the “expert-level” approach:

- Dan Kirshner’s ISO/UTS thread library (`threads.scad`) explicitly notes it uses **discrete polyhedra rather than `linear_extrude()`** for threads and exposes parameters like `internal` (clearances for internal threads), `groove` (subtract inverted V instead of adding), multi-start, and lead-in options. citeturn8view4turn2view2turn11search2  
- The `threads-scad` library describes generating an entire threaded screw as a single **polyhedron** for speed/robustness and tactile smoothness. citeturn8view1turn8view0  

Your agent can’t use arbitrary polyhedra, but the conceptual translation is straightforward:

- A polyhedron thread “turn” is ultimately many **triangular facets** arranged along a helix. citeturn8view3turn8view1  
- With your constraints, you can approximate those facets as **extruded triangular prisms** (“thread teeth segments”) placed in a staircase helix: rotate a wedge around the axis while stepping up in Z each segment.

#### Boolean recipe: external V-thread as a discrete helix of triangle prisms

**Goal:** screw/bolt-like external thread on a cylindrical core.

**Solids:**
- **A = core cylinder** (major diameter minus thread height margin).
- **Bᵢ = one thread “tooth segment”**: an extruded triangle prism oriented so its long direction is tangential/axial, and its cross-section approximates the thread profile.
- **C = optional crest-trim cylinder** (to cap the thread OD cleanly).
- **D = optional root-relief cylinder** (to avoid sharp valleys).

**Boolean logic (high-level):**
1. **Add A** (core).  
2. For each segment `i` along the helix: **Add Bᵢ** (union/combine).  
   - In OpenSCAD terms this is conceptually `union(){ core; for(i) transform(tooth); }`. citeturn1search27turn11search4  
   - In Tinkercad terms this is “Union group,” often built quickly via Duplicate/Repeat transforms. citeturn4view1turn3search15  
3. **Intersect with C** (optional) to clamp the outside diameter to a perfect cylinder (removes tiny tooth tips that exceed OD).  
4. **Subtract D** (optional) to create a slight undercut/root relief that improves printability and reduces binding.

**Key “expert hack” knobs:**
- **Step count along circumference**: more steps → smoother helix; fewer → faster render and more “square thread” feel. This mirrors why libraries tune segment count and even align facets with the base cylinder facets for robustness. citeturn12search2turn8view3turn8view4  
- **Thread profile choice**: square/buttress-style profiles tolerate discretization better than sharp V profiles; note Kirshner’s library explicitly supports square/rectangular threads, and “groove” mode (cut threads) vs protruding threads. citeturn8view4turn2view2  
- **Epsilon overlap**: ensure each tooth overlaps the core by a tiny amount to avoid “touch-only” unions that can produce non-manifold results. citeturn14search0turn14search3  

#### Boolean recipe: internal thread by subtracting a “thread tap” mask

Internal threads are best treated as a **cutter** (tap) that you subtract, which matches how OpenSCAD libraries document internal threads: internal threads are produced as a geometry intended to be “cut out” using `difference()`. citeturn8view4turn11search2

**Solids:**
- **A = nut/body block** (often a cylinder or polygonal prism).
- **B = pilot hole cylinder** (minor diameter + clearance).
- **C = thread “tap” cutter**: same discrete-helix tooth set as external, but expanded by clearance.

**Boolean logic:**
1. **Add A** (nut body).  
2. **Subtract B** (straight hole).  
3. **Subtract C** (helical thread cutter).  
4. (Optional) **Chamfer** entry to make starting the thread easier (libraries implement lead-in/chamfer options for this reason). citeturn8view4turn2view2  

**Tolerance hack:**  
Thread libraries treat tolerance as a first-class input: BOSL2’s screw system supports explicit thread tolerances (e.g., ISO “6g” screws, “6H” nuts), and also supports “none”/0 tolerance for nominal geometry. citeturn13view3turn12search3 If your agent is not using those libraries, you still want the same concept:
- Inflate internal cutters and/or shrink external threads by a global slop amount, applied consistently as described by BOSL2’s `$slop` guidance. citeturn13view4turn2view3  

### Twist-lock / bayonet mechanisms: CSG-friendly and often preferable under constraints

A twist-lock (often called a bayonet lock) typically uses **lugs/pins on one part** and **L-shaped slots with a stop/ramp on the other**, which is naturally representable as “rectangles extruded and subtracted” on a cylindrical body.

OpenSCAD users publish dedicated bayonet lock connector libraries (multiple versions) intended to generate the mating pin and slot parts. citeturn10search0turn10search3turn10search1

#### Boolean recipe: bayonet lock with lead-in + stop

**Female part (slot):**
- **A = outer cylinder** (housing).
- **B = inner cylinder hole** (bore).
- **C = radial entry slot cutters**: rectangular prisms that cut from the bore outward.
- **D = tangential “twist” slot cutters**: rectangular prisms rotated around the axis to form the sideways leg of the L.
- **E = ramp/bevel cutter**: an extruded triangle prism (wedge) that creates a rising ramp or chamfer at the end of travel.
- **F = stop block cutter**: a small prism that limits rotation.

**Boolean logic (female):**
1. **Add A**.  
2. **Subtract B** (make it a tube).  
3. For each lug position: **Subtract C** (entry) then **Subtract D** (twist leg).  
4. **Subtract E** to create a cam/ramp (optional but common for better “snap” and preload).  
5. **Subtract F** (or do nothing and rely on geometry) to define a hard stop.

**Male part (lug):**
- **A = plug cylinder** (shaft).  
- **B = lugs**: rectangular prisms (or cylinders) placed on the shaft OD.
- **C = lead-in chamfer**: wedge cut or chamfer operation.

**Boolean logic (male):**
1. **Add A**.  
2. **Add B** (union lugs).  
3. Apply **chamfer C** on lug edges and/or entry faces for smoother engagement.

**Expert hack:** prefer bayonet locks when: (a) you need large pitches / quick engage, (b) the printer resolution makes fine threads unreliable, (c) you can accept a limited number of lock positions. This matches why bayonet connectors are popular in printed couplings and connector libraries. citeturn10search0turn10search1  

## Snap-fit joints, latches, and living hinges with only blocks, wedges, and cutters

Snap-fits are inherently CSG-friendly because they are defined by **an undercut and a compliant feature**, both representable as simple extrusions and subtractive pockets.

A solid reference framing:
- A snap-fit uses a flexible protrusion (bead/hook) and a matching recess; an “integral undercut” retains the parts after engagement. citeturn13view2  
- The two most common types for 3D printed parts are **cantilever** and **annular** snap-fits. citeturn13view2  

### Cantilever snap-fit: classic latch beam

#### Boolean recipe: cantilever hook + mating pocket

**Male part (cantilever latch):**
- **A = base plate/block**.
- **B = cantilever beam** (rectangle extrude).
- **C = hook/bead** at beam tip (small rectangle extrude).
- **D = relief notch** near beam root (subtract rectangle) to localize bending.
- **E = fillet at root** (fillet operation) to reduce stress concentration (explicitly recommended for cantilevers). citeturn13view2  

**Boolean logic (male):**
1. **Add A**.  
2. **Add B** (beam) merged into A at one end.  
3. **Add C** (hook) at free end.  
4. **Subtract D** (optional) to tune stiffness/deflection.  
5. Apply **fillet E** at the beam root and optionally at the hook to reduce sharp corners. citeturn13view2  

**Female part (socket/pocket):**
- **A = housing wall/block**.
- **B = entry pocket** (subtract rectangular viewport).
- **C = undercut seat** (subtract a secondary pocket so the hook catches).
- **D = lead-in ramp** (subtract a wedge) so insertion deflects the beam gradually.

**Boolean logic (female):**
1. **Add A**.  
2. **Subtract B** (pocket volume).  
3. **Subtract C** (undercut seat).  
4. **Subtract D** (lead-in wedge).  

**Expert printability knobs highlighted in industrial guidance:**
- Avoid sharp internal corners; fillet the base of the cantilever, and taper the latch geometry for better strain distribution. citeturn13view2  

### Annular snap-fit: bottle-cap style ring + bead

Annular snaps are especially relevant under your limited primitives because they’re basically “a ring and a ridge.”

#### Boolean recipe: bead-on-cylinder + groove-in-socket

**Male (cap or plug):**
- **A = cylinder (plug)**.
- **B = bead/ridge**: a thin ring made by unioning a slightly larger cylinder segment.
- **C = lead-in chamfer** at bead.

**Boolean logic (male):**
1. **Add A**.  
2. **Add B** (union ring ridge).  
3. Chamfer **C** (optional).

**Female (socket):**
- **A = outer cylinder**.
- **B = inner bore** (subtract).
- **C = groove** (subtract a ring-shaped channel: subtract a slightly larger inner cylinder for a short height, leaving a groove step).
- **D = lead-in chamfer/wedge**.

**Boolean logic (female):**
1. **Add A**.  
2. **Subtract B**.  
3. **Subtract C** (annular groove).  
4. **Subtract/Chamfer D**.

This matches the definition: annular snap-fits use hoop strain and are common in bottle caps and similar closures. citeturn13view2  

### “Library” patterns that reveal mature geometry decisions

The BOSL2 joiners documentation effectively encodes a parametric snap-fit DSL, and it’s valuable because it exposes what experts tune: **compression, clearance, lock geometry, and printable orientation**, plus a printer-specific `$slop`. citeturn2view3turn13view4

Even if your agent cannot use splines, the design intent is portable:

- “Socket masks” are negative cutters; a secure clip is created by **making the socket bigger by clearance** and the clip “ears” bigger by compression, then optionally adding a lock flange. citeturn2view3  
- BOSL2’s hinge system includes snap-locking hinged parts and explicitly uses `$slop` to enlarge pin holes, and can generate print-in-place hinge geometry. citeturn12search28turn7view0turn13view4  

### Living hinges: two CSG-friendly approaches under your constraint set

Living hinges are “thin flexible webs” connecting rigid sections; for 3D printing, they’re often used for prototyping and proof-of-concept due to layer anisotropy and limited flex-cycle life. citeturn7view1

There are two geometry patterns that work well with rectangles-only cutters:

#### Pattern A: “Thin web” living hinge (classic injection-mold style, approximated)

**Boolean recipe:**
- **A = solid part (two rigid plates)**.
- **B = hinge thinning cutter**: subtract a shallow rectangular pocket across the hinge line, leaving a thin web.
- **C = stress-relief fillets**: fillet the transitions into the thin web.

**Logic:**
1. **Add A**.  
2. **Subtract B** to locally thin the wall to hinge thickness.  
3. Apply **C** fillets at hinge boundaries.

Why experts also split a hinge into multiple small hinges: making several narrow hinge strips reduces force and extends functional life. citeturn7view2

#### Pattern B: “Kerf / slit hinge” (especially printable with rigid plastics)

This is the most CSG-native pattern: make a thick plate, then cut **many repeated slots** that allow bending.

**Boolean recipe:**
- **A = hinge strip block** (full thickness).
- **Bᵢ = slot cutters**: repeated thin rectangular prisms removed in a pattern.
- **C = round-ended slot tips**: replace sharp slot ends with round/filleted ends to reduce crack initiation (can be approximated by subtracting small cylinders at slot ends, then connecting with a rectangle).

**Logic:**
1. **Add A**.  
2. For each slot `i`: **Subtract Bᵢ** (arrayed via Duplicate/Repeat in Tinkercad or loops in OpenSCAD). citeturn4view1turn11search4  
3. If possible, **Subtract C** at slot ends (round relief) to reduce stress concentration; design guidance commonly warns sharp corners concentrate stress in flexible features. citeturn13view2turn7view1  

## Complex tapers, drafts, and bevels without lofts or sweeps

Even though pure CSG can’t smoothly morph profiles, experts routinely create tapers via **(a) wedge cuts, (b) intersections with simple limiting solids, or (c) stair-stepped stacking**.

### Technique family: wedge cutters for non-square edges

The core idea is that a chamfer is “subtract a wedge.” If you can extrude a triangle, you can make a wedge of any slope.

#### Boolean recipe: bevel one arbitrary edge of a block

**Solids:**
- **A = base block** (your main body).
- **B = wedge cutter**: triangle extruded → triangular prism; positioned so its sloped face defines bevel angle.

**Logic:**
1. **Add A**.  
2. **Subtract B** (bevel).  
3. Apply a small fillet at the bevel boundary if needed for print robustness.

**Extending to non-square edges:**  
- If the edge is angled in plan view, rotate the wedge cutter to match the edge direction, then subtract.

**Expert hack:** do *not* let the wedge cutter terminate exactly on the face boundary; extend it past and use epsilon overlap to avoid coplanar leftovers. citeturn14search3turn14search0  

### Technique family: “draft via stacked slices” (cone/frustum approximation)

If the target is a tapered wall (e.g., draft angle), you can approximate a cone/frustum by stacking many thin extruded circles (disks) whose radius changes in steps.

#### Boolean recipe: tapered outer wall via slice stacking

**Solids:**
- **A₀..Aₙ = cylinder slices**: each slice is a thin cylinder; radii go from bottom radius to top radius.
- **B = union of all slices**.
- **C = (optional) smoothing via fillets** at slice transitions.
- **D = inner bore** for a tapered tube (subtract).

**Logic:**
1. **Add all Aᵢ** (union to create a stepped frustum).  
2. (Optional) Apply **fillets C** if your kernel supports multi-edge fillets.  
3. **Subtract D** if you need a hollow part.

This is computationally heavier but stays within your constraints.

### Technique family: “draft by intersection with a limiter”

If you can define a “limiting volume” that contains only the desired taper region, intersection becomes a powerful trimming tool.

In OpenSCAD, intersection is explicitly “keep only shared volume.” citeturn1search27 In Tinkercad, Intersect group exists as a first-class grouping mode. citeturn4view1turn14search20

#### Boolean recipe: intersection-based trimming

**Solids:**
- **A = near-final part**.
- **B = limiter solid** (often a big wedge-shaped prism that defines a sloped boundary).

**Logic:**
1. **Add A**.  
2. **Intersect with B** to “slice off” everything outside the limiter.

This is useful when subtractive cutters would require many pieces; intersection can do it in one operation if you can build the limiter from wedges/blocks.

## Spheres, domes, and complex curves from cylinders, intersections, and “stacked rounding”

You asked specifically about “stacking fillets” and “boolean intersections of cylinders.” That is exactly the right mental model: in strict CSG, smooth curves often appear as the **envelope of many small planar pieces** or as **analytic intersections** of primitives.

### Technique: create rounded “vault” surfaces via cylinder intersections (Steinmetz solids)

The intersection of two perpendicular cylinders is known as a **Steinmetz solid** (bicylinder). citeturn1search38turn1search7 This matters because it gives you a **naturally curved surface** without a sphere primitive.

#### Boolean recipe: domed/vaulted top from two cylinders

**Solids:**
- **A = cylinder 1** (vertical along Z).
- **B = cylinder 2** (horizontal along X or Y), with radius chosen to give desired curvature.
- **C = base trim** (a block to cut the bottom flat).

**Logic:**
1. **Intersect A and B** → produces a rounded vault-like solid. citeturn1search27turn1search38  
2. **Subtract/intersect with C** to keep only the dome portion you want (e.g., top half).

**Practical variant:**  
Intersect **three** cylinders at right angles (tricylinder) to get even more “sphere-like” rounding (still not a perfect sphere, but often very usable as a “mechanical dome”). citeturn1search38turn1search27

### Technique: “sphere by slices” (lathe approximation without revolve)

A true sphere can be approximated by stacking thin cylinders (disks) whose radii follow the circle equation. Under your constraints, this is the most direct “no sweep, no loft, no spline” path to a sphere-like shape.

#### Boolean recipe: sphere approximation via unioned disks + optional smoothing

**Solids:**
- **Aᵢ = disk slices**: cylinder of thickness `dz`, radius `r(z)`.
- **B = union(Aᵢ)**.
- **C = smoothing operations**: fillets where supported.

**Logic:**
1. **Add Aᵢ** for i=0..n (union).  
2. If you have fillets: apply them to reduce the stepped surface.

**Why experts like this:** it reuses the same “discretize into steps” trick used for threads and tapers—just in a different axis.

### Technique: “stacked fillets / shell-first” workflows

When fillets and shell are available, experts often invert the order of operations:

1) Create a **blocky shape** that is guaranteed manifold and boolean-friendly.  
2) Apply **fillets/chamfers** as a finishing step, because boolean ops can invalidate edge references and create fragile geometry if fillets are applied too early (this is a common reason advanced OpenSCAD libraries focus on generating robust base solids and then trimming/finishing). citeturn8view1turn8view3  
3) Use **shell** to create thin-walled domes or capsules: create the outer hull from booleans, then shell inward.

This approach also helps with printability—thin wall thickness becomes a controlled parameter rather than an emergent result.

### Practical correctness hacks for curves and booleans

- **Avoid coplanar cut planes** by extending cutters slightly beyond the target and/or applying epsilon offsets; this is repeatedly recommended by experienced OpenSCAD users because it prevents preview/render artifacts and non-manifold edges. citeturn14search3turn14search0turn14search10  
- **Adopt a global slop parameter** for all mating curved surfaces (dome lip to socket, spherical seat to ball, etc.), and calibrate it per printer/material if your workflow can. citeturn13view4turn13view3  

## Consolidated step-by-step boolean logic templates you can directly encode in an agent

This final section summarizes each requested mechanical feature as a reusable “boolean program.” The goal is to give you canonical action graphs (Add/Subtract/Intersect) that an LLM agent can follow deterministically, with clear places to insert `$slop` and `epsilon`.

### Threads and screw threads

**External thread (discrete helix):**
1. Add **core cylinder** A.  
2. Add **tooth segment array** Bᵢ (triangular prisms), arranged by repeated rotate+translate (helix staircase).  
3. (Optional) Intersect with **OD limiter** C to clamp max diameter.  
4. (Optional) Subtract **root relief** D (slightly larger inner cylinder) to avoid sharp valleys.  
5. Apply **chamfer/fillet** on starts/ends.

**Internal thread:**
1. Add **nut/body** A.  
2. Subtract **pilot hole** B.  
3. Subtract **thread cutter** C (same helix pattern as external, expanded by clearance/slop).  
4. Add **entry chamfer** (subtract wedge or apply chamfer).

(Internal threads are explicitly modeled as geometry intended to be cut out via `difference()` in OpenSCAD thread libraries, matching this pipeline.) citeturn8view4turn11search2

### Twist-lock / bayonet lock

**Female socket with L-slots:**
1. Add **outer cylinder** A.  
2. Subtract **inner bore** B.  
3. For each lug: subtract **radial entry slot** C, subtract **tangential slot** D.  
4. Subtract **ramp wedge** E near the lock end (optional).  
5. Subtract **stop pocket** F (optional).

**Male plug with lugs:**
1. Add **plug cylinder** A.  
2. Add **lug blocks** B (union).  
3. Chamfer/fillet lug edges.

(Reusable idea: bayonet lock connector libraries exist specifically to generate these mating pin+slot parts.) citeturn10search0turn10search3turn10search1

### Snap-fit joints and latches

**Cantilever snap:**
1. Add **base** A.  
2. Add **beam** B.  
3. Add **hook** C.  
4. Subtract **root relief notch** D (optional).  
5. Fillet **beam root** E (recommended to reduce stress concentration). citeturn13view2  

**Mating socket:**
1. Add **housing** A.  
2. Subtract **entry pocket** B.  
3. Subtract **undercut seat** C.  
4. Subtract **lead-in wedge** D.

**Annular snap (cap):**
1. Add **plug cylinder** A.  
2. Add **bead ring** B.  
3. Add chamfer at bead edge.

**Annular socket:**
1. Add **outer cylinder** A.  
2. Subtract **inner bore** B.  
3. Subtract **groove ring** C.  
4. Add chamfer/lead-in.

(These correspond to the common snap-fit types and the “hook + undercut” retention principle.) citeturn13view2

### Living hinges

**Thin-web hinge:**
1. Add **two rigid plates** A.  
2. Subtract a shallow **thinning pocket** B along hinge line (leave thin web).  
3. Fillet transitions.

**Slit/kerf hinge:**
1. Add **hinge strip block** A.  
2. Subtract repeated **slots** Bᵢ (array).  
3. Subtract/add end-rounding features at slot ends where possible.

(Design guidance emphasizes living hinges are thin webs, and printed living hinges are often best for prototyping due to anisotropy; hinge geometry and material matter.) citeturn7view1turn7view2

### Complex tapers, drafts, bevels

**Bevel via wedge cut:**
1. Add **base solid** A.  
2. Subtract **wedge cutter** B (triangle extrude).  
3. Fillet/chamfer edges as needed.

**Taper via slice stacking:**
1. Add **stack of thin cylinders** Aᵢ with monotonic radii.  
2. Union them → B.  
3. Apply fillets (optional).  
4. Subtract inner bore for tubes.

**Draft via intersection limiter:**
1. Add **oversized body** A.  
2. Intersect with **limiter wedge** B to keep only drafted volume (AND).

### Domes and complex curves

**Vault/dome via cylinder intersection (Steinmetz-style):**
1. Intersect **cylinder A** and **perpendicular cylinder B** to create curved boundary. citeturn1search27turn1search38  
2. Subtract/Intersect with **trim block** C to isolate cap/dome portion.

**Sphere-ish via disk stacking:**
1. Add **disk slices** Aᵢ (thin cylinders) whose radii follow your target profile.  
2. Union all slices.  
3. Fillet edges (optional).

**Robustness guardrail (for all features):**
- Use epsilon overlaps so unions/differences don’t leave ambiguous “touching” surfaces—a well-known OpenSCAD workaround. citeturn14search0turn14search3turn14search10  
- Apply a single global slop parameter to mating geometry and calibrate it, as BOSL2 recommends. citeturn13view4turn13view3