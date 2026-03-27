# Pole Mount Examples

This folder contains scripts demonstrating ParamAItric usage for creating a custom pole mount plate.

## Use Case

Mount a 0.75" diameter pole to a flat surface using a plate with integrated tube socket.

## Specifications

- **Base plate:** 4" × 3" × 0.25"
- **Socket:** 1.25" OD, 0.75" ID, 1.5" tall
- **Wall thickness:** 0.25"
- **Mounting:** 4 corner holes for #8 screws
- **Features:** Chamfered socket top, filleted plate edges

## Scripts

| Script | Description |
|--------|-------------|
| `make_pole_mount_manual.py` | Basic pole mount (plate + socket + bore) |
| `make_pole_mount_4_holes.py` | Adds 4 corner mounting holes |
| `make_pole_mount_final.py` | Full version with chamfer + fillet using edge-specific API |
| `make_pole_mount_full.py` | Earlier attempt with detailed edge analysis |
| `debug_edges.py` | Tool for analyzing body edges |
| `test_bridge.py` | Simple connectivity test |

## Key Techniques Demonstrated

### 1. Manual Workflow Construction

Instead of using a predefined workflow, build the part step-by-step:

```python
# Create base sketch
sketch = server.create_sketch(plane="xy", name="BasePlate")
server.draw_rectangle(width_cm=10.16, height_cm=7.62)
profiles = server.list_profiles(sketch_token)
plate = server.extrude_profile(profile_token, distance_cm=0.635)
```

### 2. Boolean Operations

Combine separate bodies into one:

```python
combined = server.combine_bodies(
    target_body_token=plate["token"],
    tool_body_token=tube["token"]
)
```

### 3. Cut Operations

Cut holes and bores:

```python
bore = server.extrude_profile(
    profile_token=bore_profile,
    distance_cm=socket_height,
    operation="cut",
    target_body_token=body["token"]
)
```

### 4. Edge-Specific Features

Select specific edges for chamfer/fillet:

```python
# Get all edges
edges = server.get_body_edges({"body_token": body_token})["result"]["body_edges"]

# Filter by geometry (e.g., socket top circular edges)
socket_top_edges = [e for e in edges if is_at_socket_top(e)]

# Apply chamfer to selected edges
server.apply_chamfer_to_edges(
    body_token=body_token,
    edge_tokens=[e["token"] for e in socket_top_edges],
    distance_cm=0.254
)
```

## Running the Scripts

```bash
cd C:\GitHub\paramAItric
.venv\Scripts\python examples\pole_mount\make_pole_mount_final.py
```

## Output

STL files are saved to:
- Temp: `C:\Users\<user>\AppData\Local\Temp\pole_mount_*.stl`
- Desktop: `C:\Users\<user>\Desktop\pole_mount_*.stl`

Check Fusion 360 to see the live 3D model.

## Edge Selection Strategy

For the socket chamfer:
- Find circular edges at `z = plate_thickness + socket_height`
- These are the top rim of the socket

For the plate fillet:
- Find linear edges spanning `z = 0` to `z = plate_thickness`
- Filter to those on the outer perimeter (x=0, x=width, y=0, y=depth)

## Lessons Learned

1. **Workflows vs Manual:** Predefined workflows have strict validation. Manual construction allows more flexibility for custom geometry.

2. **Edge Tokens:** Edge tokens persist after geometry changes, but re-query after each operation to get updated topology.

3. **API Extension:** Added `apply_fillet_to_edges` and `apply_chamfer_to_edges` commands to enable edge-specific operations not covered by the predefined selectors.
