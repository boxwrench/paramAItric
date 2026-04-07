# Pole Mount Demo - ParamAItric

This document describes the pole mount bracket created as a demonstration of ParamAItric's step-by-step workflow approach. Created on 2026-03-27.

## Demo Narrative Notes

This demo is designed to feel like a live first-time session. When running it:

- **Do not reference this document or prior attempts.** Treat each request as if it's the first time the part is being made.
- **The demo runs in two natural requests:** first the user asks for the basic pole mount (no holes), then as a follow-up they ask to add corner mounting holes. This simulates a realistic iterative design conversation.
- Do not pre-empt the second request by asking about holes upfront — let the user drive it.

## Part Specification

### Overall Dimensions
| Dimension | Value | Notes |
|-----------|-------|-------|
| Plate Width | 4.0 inches | 10.16 cm |
| Plate Depth | 3.0 inches | 7.62 cm |
| Plate Thickness | 0.25 inches | 0.635 cm |
| Socket Height | 1.5 inches | 3.81 cm |
| Total Height | 1.75 inches | 4.445 cm |

### Pole Socket (Cylindrical)
| Dimension | Value | Notes |
|-----------|-------|-------|
| Interior Diameter (ID) | 0.75 inches | 1.905 cm (bore) |
| Exterior Diameter (OD) | 1.25 inches | 3.175 cm |
| Wall Thickness | 0.25 inches | 0.635 cm |
| Height | 1.5 inches | 3.81 cm |

### Mounting Holes (4x corners)
| Specification | Value | Notes |
|---------------|-------|-------|
| Hole Diameter | 0.164 inches | 0.416 cm (#8 screw clearance) |
| Inset from Corners | 0.5 inches | 1.27 cm |
| Hole Depth | Through plate | 0.25 inches / 0.635 cm |

#### Hole Positions (from origin 0,0)
- **Bottom-Left:** x=1.27 cm, y=1.27 cm
- **Bottom-Right:** x=8.89 cm, y=1.27 cm
- **Top-Left:** x=1.27 cm, y=6.35 cm
- **Top-Right:** x=8.89 cm, y=6.35 cm

---

## Assembly Instructions

### Step 1: Create New Design
```
Command: new_design("Pole Mount")
```
Start with a fresh design file.

### Step 2: Create Base Plate
```
Commands:
  • create_sketch(plane="xy", name="Plate Sketch")
  • draw_rectangle(width_cm=10.16, height_cm=7.62)
  • list_profiles() → get profile token
  • extrude_profile(profile_token=..., distance_cm=0.635, body_name="Pole Mount")
```
Creates the flat mounting plate (4" × 3" × 0.25").

### Step 3: Create Pole Socket
```
Commands:
  • create_sketch(plane="xy", name="Socket Sketch", offset_cm=0.635)
  • draw_circle(center_x_cm=5.08, center_y_cm=3.81, radius_cm=1.5875)
  • list_profiles() → get profile token
  • extrude_profile(profile_token=..., distance_cm=3.81, body_name="Socket")
```
Creates a solid cylinder on top of the plate (1.5" tall, 1.25" OD).

### Step 4: Combine Bodies
```
Command: combine_bodies(target_body_token=plate_token, tool_body_token=socket_token)
```
Merges the plate and socket into a single body.

### Step 5: Cut Socket Bore (Make it Hollow)
```
Commands:
  • create_sketch(plane="xy", name="Socket Bore", offset_cm=4.445)
  • draw_circle(center_x_cm=5.08, center_y_cm=3.81, radius_cm=0.9525)
  • list_profiles() → get profile token
  • extrude_profile(profile_token=..., distance_cm=3.81, operation="cut", target_body_token=combined_token)
```
Cuts the 0.75" ID bore through the socket to create the hollow pole opening.

### Step 6: Add Four Corner Mounting Holes
Repeat for each corner position:
```
Commands:
  • create_sketch(plane="xy", name="Hole [N]")
  • draw_circle(center_x_cm=[x], center_y_cm=[y], radius_cm=0.208)
  • list_profiles() → get profile token
  • extrude_profile(profile_token=..., distance_cm=0.635, operation="cut", target_body_token=current_body)
```

**Hole 1 (Bottom-Left):** center_x_cm=1.27, center_y_cm=1.27
**Hole 2 (Bottom-Right):** center_x_cm=8.89, center_y_cm=1.27
**Hole 3 (Top-Left):** center_x_cm=1.27, center_y_cm=6.35
**Hole 4 (Top-Right):** center_x_cm=8.89, center_y_cm=6.35

### Step 7: Export STL
```
Command: export_stl(body_token=final_body_token, output_path="pole_mount.stl")
```
Exports the finished part for 3D printing or CAD review.

---

## Workflow Approach Comparison

### Method A: Step-by-Step (Recommended for Custom Parts)
- Build plate → socket → combine → cut bore → add holes
- Full control over geometry at each stage
- No rigid verification constraints
- Easier to debug individual steps
- **Used for this demo** ✓

### Method B: Workflow Template (Better for Standardized Parts)
- Use `create_tube_mounting_plate()` workflow
- Requires exact parameter validation
- Faster once configured correctly
- Uses tolerance-based verification (0.01 cm) for robustness
- Good for production/repeated designs

---

## Key Insights

1. **Floating-Point Tolerance:** When verifying dimensions created by CAD software, always use tolerance-based comparison (not exact equality) to account for floating-point precision.

2. **Order Matters:** While both approaches work, cutting holes before combining bodies simplifies geometry during intermediate steps.

3. **Offset Sketches:** Socket bore sketch must be offset by plate thickness (0.635 cm) to position correctly at the plate-socket interface.

4. **Bore Depth:** The bore cutting distance should match the socket height (3.81 cm) to fully hollow out the socket.

---

## Files Generated

- **Output STL:** `scripts/manual_test_output/pole_mount_complete.stl`
- **Demo Date:** 2026-03-27
- **Fusion 360 Bridge:** Live mode verified

---

## Next Steps (Future Enhancements)

- [ ] Add fillet to socket edge (0.1" radius)
- [ ] Add chamfer to mounting hole edges (0.05" × 45°)
- [ ] Create workflow template for reusable pole mount variants
- [ ] Test with different socket diameters and plate sizes
