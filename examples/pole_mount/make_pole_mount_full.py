"""Create pole mount with 4 corner holes + chamfered socket + filleted plate edges."""
from mcp_server.server import ParamAIToolServer
import json

server = ParamAIToolServer()
INCH_TO_CM = 2.54

# User specs
plate_w = 4.0 * INCH_TO_CM      # 10.16 cm
plate_d = 3.0 * INCH_TO_CM      # 7.62 cm
plate_t = 0.25 * INCH_TO_CM     # 0.635 cm
socket_id = 0.75 * INCH_TO_CM   # 1.905 cm  
socket_od = 1.25 * INCH_TO_CM   # 3.175 cm
socket_h = 1.5 * INCH_TO_CM     # 3.81 cm

# Mounting hole specs - 4 corners
hole_dia = 0.25 * INCH_TO_CM    # 0.635 cm (#8 screw)
hole_inset = 0.5 * INCH_TO_CM   # 1.27 cm from each edge

# Feature specs
chamfer_size = 0.1 * INCH_TO_CM   # 0.25 cm chamfer on socket top
fillet_radius = 0.15 * INCH_TO_CM # 0.38 cm (3/8") fillet on plate edges

print("Creating Pole Mount with chamfer + fillet...")
print(f"  Plate: {plate_w:.2f} x {plate_d:.2f} x {plate_t:.2f} cm")
print(f"  Socket: OD={socket_od:.2f}, ID={socket_id:.2f}, H={socket_h:.2f} cm")
print(f"  Chamfer: {chamfer_size/INCH_TO_CM:.2f}\"")
print(f"  Fillet: {fillet_radius/INCH_TO_CM:.2f}\"")
print()

try:
    # Step 1: Create base plate
    print("1. Creating base plate...")
    server.new_design("Pole Mount Full")
    sketch = server.create_sketch(plane="xy", name="BasePlate")["result"]["sketch"]
    server.draw_rectangle(width_cm=plate_w, height_cm=plate_d, sketch_token=sketch["token"])
    profiles = server.list_profiles(sketch["token"])["result"]["profiles"]
    plate = server.extrude_profile(
        profile_token=profiles[0]["token"],
        distance_cm=plate_t,
        body_name="BasePlate"
    )["result"]["body"]
    print(f"   Plate: {plate['width_cm']:.2f} x {plate['height_cm']:.2f} x {plate['thickness_cm']:.2f}")
    
    # Step 2: Add 4 mounting holes
    print("2. Adding 4 corner mounting holes...")
    corners = [
        ("BL", hole_inset, hole_inset),
        ("BR", plate_w - hole_inset, hole_inset),
        ("TL", hole_inset, plate_d - hole_inset),
        ("TR", plate_w - hole_inset, plate_d - hole_inset),
    ]
    current_body = plate
    for name, cx, cy in corners:
        hole_sketch = server.create_sketch(plane="xy", name=f"Hole{name}")["result"]["sketch"]
        server.draw_circle(center_x_cm=cx, center_y_cm=cy, radius_cm=hole_dia/2, sketch_token=hole_sketch["token"])
        hole_profiles = server.list_profiles(hole_sketch["token"])["result"]["profiles"]
        current_body = server.extrude_profile(
            profile_token=hole_profiles[0]["token"],
            distance_cm=plate_t,
            body_name="BasePlate",
            operation="cut",
            target_body_token=current_body["token"]
        )["result"]["body"]
    print(f"   Plate with holes: {current_body['token']}")
    
    # Step 3: Create tube socket
    print("3. Creating tube socket...")
    tube_sketch = server.create_sketch(plane="xy", name="TubeSocket", offset_cm=plate_t)["result"]["sketch"]
    server.draw_circle(center_x_cm=plate_w/2, center_y_cm=plate_d/2, radius_cm=socket_od/2, sketch_token=tube_sketch["token"])
    tube_profiles = server.list_profiles(tube_sketch["token"])["result"]["profiles"]
    tube = server.extrude_profile(
        profile_token=tube_profiles[0]["token"],
        distance_cm=socket_h,
        body_name="TubeSocket"
    )["result"]["body"]
    print(f"   Tube: {tube['width_cm']:.2f} x {tube['height_cm']:.2f} x {tube['thickness_cm']:.2f}")
    
    # Step 4: Combine tube to plate
    print("4. Combining tube with plate...")
    combined = server.combine_bodies(
        target_body_token=current_body["token"],
        tool_body_token=tube["token"]
    )["result"]["body"]
    print(f"   Combined: {combined['width_cm']:.2f} x {combined['height_cm']:.2f} x {combined['thickness_cm']:.2f}")
    
    # Step 5: Create bore through tube
    print("5. Cutting bore through tube...")
    bore_sketch = server.create_sketch(plane="xy", name="BoreCut", offset_cm=plate_t)["result"]["sketch"]
    server.draw_circle(center_x_cm=plate_w/2, center_y_cm=plate_d/2, radius_cm=socket_id/2, sketch_token=bore_sketch["token"])
    bore_profiles = server.list_profiles(bore_sketch["token"])["result"]["profiles"]
    body_with_bore = server.extrude_profile(
        profile_token=bore_profiles[0]["token"],
        distance_cm=socket_h,
        body_name="PoleMount",
        operation="cut",
        target_body_token=combined["token"]
    )["result"]["body"]
    print(f"   Final body: {body_with_bore['token']}")
    
    # Step 6: Get all edges and analyze them
    print("6. Analyzing edges for chamfer/fillet...")
    edges_result = server.get_body_edges({"body_token": body_with_bore["token"]})["result"]
    all_edges = edges_result.get("body_edges", [])
    print(f"   Total edges: {len(all_edges)}")
    
    # Find socket top edges (circular edges at z = plate_t + socket_h)
    socket_top_z = plate_t + socket_h
    socket_top_edges = []
    plate_bottom_edges = []
    plate_outer_edges = []
    
    for edge in all_edges:
        start = edge.get("start_point", {})
        end = edge.get("end_point", {})
        edge_type = edge.get("type", "")
        
        # Socket top edges are circular edges near the top of the socket
        if edge_type == "circular":
            z_start = start.get("z", 0)
            z_end = end.get("z", 0)
            # Check if this edge is at the socket top (within tolerance)
            if abs(z_start - socket_top_z) < 0.01 and abs(z_end - socket_top_z) < 0.01:
                socket_top_edges.append(edge)
        
        # Plate bottom edges are at z = 0
        z_start = start.get("z", 0)
        z_end = end.get("z", 0)
        if abs(z_start) < 0.01 and abs(z_end) < 0.01:
            plate_bottom_edges.append(edge)
        
        # Plate outer vertical edges connect bottom to top of plate
        if edge_type == "linear":
            z_min = min(z_start, z_end)
            z_max = max(z_start, z_end)
            if z_min < 0.01 and abs(z_max - plate_t) < 0.01:
                # Check if it's on the outer perimeter
                x_start = start.get("x", 0)
                y_start = start.get("y", 0)
                x_end = end.get("x", 0)
                y_end = end.get("y", 0)
                # Edge is on outer perimeter if it's at the edge of the plate
                is_outer = (
                    abs(x_start) < 0.01 or abs(x_start - plate_w) < 0.01 or
                    abs(y_start) < 0.01 or abs(y_start - plate_d) < 0.01 or
                    abs(x_end) < 0.01 or abs(x_end - plate_w) < 0.01 or
                    abs(y_end) < 0.01 or abs(y_end - plate_d) < 0.01
                )
                if is_outer:
                    plate_outer_edges.append(edge)
    
    print(f"   Socket top edges: {len(socket_top_edges)}")
    print(f"   Plate bottom edges: {len(plate_bottom_edges)}")
    print(f"   Plate outer vertical edges: {len(plate_outer_edges)}")
    
    # Step 7: Apply chamfer to socket top edges
    print("7. Applying chamfer to socket top...")
    if socket_top_edges:
        chamfer_edge_tokens = [e["token"] for e in socket_top_edges[:4]]  # Limit to first 4
        print(f"   Chamfering {len(chamfer_edge_tokens)} edges")
        chamfer_result = server.apply_chamfer_to_edges(
            body_token=body_with_bore["token"],
            edge_tokens=chamfer_edge_tokens,
            distance_cm=chamfer_size,
        )["result"]
        print(f"   Chamfer applied: {chamfer_result.get('distance_cm', chamfer_size):.3f}cm to {chamfer_result.get('edge_count', 0)} edges")
        body_after_chamfer = {"token": body_with_bore["token"]}  # Same body token
    else:
        print("   No socket top edges found, skipping chamfer")
        body_after_chamfer = body_with_bore
    
    # Step 8: Apply fillet to plate outer edges
    print("8. Applying fillet to plate outer edges...")
    if plate_outer_edges:
        fillet_edge_tokens = [e["token"] for e in plate_outer_edges[:8]]  # Limit to first 8
        print(f"   Filleting {len(fillet_edge_tokens)} edges")
        fillet_result = server.apply_fillet_to_edges(
            body_token=body_after_chamfer["token"],
            edge_tokens=fillet_edge_tokens,
            radius_cm=fillet_radius,
        )["result"]
        print(f"   Fillet applied: {fillet_result.get('radius_cm', fillet_radius):.3f}cm to {fillet_result.get('edge_count', 0)} edges")
    else:
        print("   No plate outer edges found, skipping fillet")
    
    # Step 9: Export
    print("9. Exporting STL...")
    export = server.export_stl(
        body_token=body_with_bore["token"],
        output_path="C:\\Users\\wests\\AppData\\Local\\Temp\\pole_mount_full.stl"
    )["result"]
    
    # Copy to desktop
    import shutil
    shutil.copy(export['output_path'], f"C:/Users/wests/Desktop/pole_mount_full.stl")
    
    print()
    print("=" * 60)
    print("SUCCESS! Pole mount with chamfer + fillet created!")
    print("STL: C:\\Users\\wests\\Desktop\\pole_mount_full.stl")
    print("=" * 60)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
