# Potential Reference Parts

This document outlines categories and specific ideas for real-world utility parts to use as benchmarks for ParamAItric. 

These ideas adhere to our current constraints:
- **No Threading:** Avoid internal/external helical threads (use heat-set insert hole diameters instead).
- **FDM Printable:** Focus on robust geometries that don't require microscopic tolerances.
- **Constructive Solid Geometry (CSG) Friendly:** Parts that can be built using primitives (extrusions, cuts, revolves, shells, chamfers/fillets).

## 1. Strut Channel & Beam Attachments
*   **Strut Channel Spring Nut (Blank):** The parallelogram/rhombus shaped base that twists into a strut channel, modeled with a pilot hole for a heat-set insert rather than a thread. Tests angled sketching and clearance tolerances.
*   **Beam Clamp (C-Clamp Style):** A thick, structural "C" shape with a set-screw hole and a mounting hole. Tests thick-wall extrusions and off-axis hole placement.
*   **Strut Pipe Clamp / Saddle:** A two-piece clamp that drops into a strut to hold a pipe. Tests multi-body symmetry and semi-circular cuts.

## 2. Unthreaded Pipe Fittings & Hose Adapters
*   **Straight Hose Splicer (Barb to Barb):** Tests the `revolve` primitive. Forces the AI to generate a stepped, saw-tooth profile and revolve it 360 degrees around a central axis.
*   **Reducing Hose Splicer:** Similar to the straight splicer, but tests asymmetric revolve profiles.
*   **Flange Adapter (Smooth Bore):** A pipe flange with a bolt circle pattern, but with a smooth slip-fit bore instead of NPT threads. Tests circular array logic (or manual math for bolt circles) and combining cylinders.

## 3. Enclosures & Covers
*   **NEMA-Style Flanged Junction Box:** A rectangular project box that features external mounting "ears" (flanges). Tests shelling, and joining secondary bodies to the exterior of a shelled volume.
*   **Friction-Fit Lid with Stepped Lip:** A lid designed to snap into the junction box. Tests inter-part fit tolerances (e.g., leaving a 0.2mm gap between the lid lip and the box rim).
*   **Terminal Block Splash Shield:** A thin, open-backed cover designed to slip over a DIN rail or terminal block. Tests thin-wall extrusions and snap-fit flex points.

## 4. Hardware & Utility
*   **Shaft Collar (Clamp-On):** A cylinder with an axial bore, sliced down one side with a cross-bolt hole to clamp it tight. Tests complex boolean cuts (slicing a cylinder) and intersecting holes.
*   **Pillow Block Bearing Housing:** The mounting block for a standard ball bearing. Tests thick-base extrusions, a large precise bore, and heavy fillets for stress distribution.
*   **Knurled / Ribbed Control Knob:** A potentiometer knob. Tests whether the AI can use repeated boolean cuts (CSG) around the perimeter of a cylinder to create a grip texture.