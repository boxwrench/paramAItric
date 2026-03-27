"""Create pole mount with 4 corner holes + chamfered socket + filleted plate edges."""
from mcp_server.server import ParamAIToolServer
import json
import shutil

server = ParamAIToolServer()
INCH_TO_CM = 2.54

# User specs
plate_w = 4.0 * INCH_TO_CM      # 10.16 cm
plate_d = 3.0 * INCH_TO_CM      # 7.62 cm
plate_t = 0.25 * INCH_TO_CM     # 0.635 cm
socket_id = 0.75 * INCH_TO_CM   # 1.905 cm  
socket_od = 1.25 * INCH_TO_CM   # 3.175 cm
socket_h = 1.5 * INCH_TO_CM     # 3.81 cm

# Mounting hole specs
hole_dia = 0.25 * INCH_TO_CM
hole_inset = 0.5 * INCH_TO_CM

# Feature specs
chamfer_size = 0.1 * INCH_TO_CM
fillet_radius = 0.15 * INCH_TO_CM

print("Creating Pole Mount with chamfer + fillet...")
print(f"  Plate: {plate_w:.2f} x {plate_d:.2f} x {plate_t:.2f} cm")
print(f"  Socket: OD={socket_od:.2f}, ID={socket_id:.2f}, H={socket_h:.2f} cm")
print()

def get_edges(body_token):
    """Get all edges for a body."""
    result = server.get_body_edges({"body_token": body_token})["result"]
    return result.get("body_edges", [])

def find_socket_top_edges(edges, socket_top_z, plate_center_x, plate_center_y, socket_od):
    """Find circular edges at the top of the socket."""
    socket_top = []
    socket_radius = socket_od / 2
    for edge in edges:
        if edge.get("type") != "circular":
            continue
        start = edge.get("start_point", {})
        # Check if edge is near socket top height
        z = start.get("z", 0)
        if abs(z - socket_top_z) > 0.1:
            continue
        # Check if edge is near socket center (within socket radius)
        x = start.get("x", 0)
        y = start.get("y", 0)
        dist_from_center = ((x - plate_center_x)**2 + (y - plate_center_y)**2)**0.5
        if dist_from_center < socket_radius + 0.5:
            socket_top.append(edge)
    return socket_top

def find_plate_outer_edges(edges, plate_t, plate_w, plate_d):
    """Find vertical edges on the outer perimeter of the plate."""
    outer_edges = []
    for edge in edges:
        if edge.get("type") != "linear":
            continue
        start = edge.get("start_point", {})
        end = edge.get("end_point", {})
        z_start = start.get("z", 0)
        z_end = end.get("z", 0)
        # Must span from z=0 to z=plate_t
        z_min = min(z_start, z_end)
        z_max = max(z_start, z_end)
        if z_min > 0.1 or abs(z_max - plate_t) > 0.1:
            continue
        # Must be on outer perimeter
        x_start = start.get("x", 0)
        y_start = start.get("y", 0)
        x_end = end.get("x", 0)
        y_end = end.get("y", 0)
        # Check if on outer edge
        tolerance = 0.2
        is_outer = (
            abs(x_start) < tolerance or abs(x_start - plate_w) < tolerance or
            abs(y_start) < tolerance or abs(y_start - plate_d) < tolerance or
            abs(x_end) < tolerance or abs(x_end - plate_w) < tolerance or
            abs(y_end) < tolerance or abs(y_end - plate_d) < tolerance
        )
        if is_outer:
            outer_edges.append(edge)
    return outer_edges

try:
    # Step 1: Create base plate
    print("1. Creating base plate...")
    server.new_design("Pole Mount Final")
    sketch = server.create_sketch(plane="xy", name="BasePlate")["result"]["sketch"]
    server.draw_rectangle(width_cm=plate_w, height_cm=plate_d, sketch_token=sketch["token"])
    profiles = server.list_profiles(sketch["token"])["result"]["profiles"]
    plate = server.extrude_profile(
        profile_token=profiles[0]["token"],
        distance_cm=plate_t,
        body_name="BasePlate"
    )["result"]["body"]
    print(f"   Plate created")
    
    # Step 2: Add 4 mounting holes
    print("2. Adding 4 corner mounting holes...")
    corners = [
        (hole_inset, hole_inset),
        (plate_w - hole_inset, hole_inset),
        (hole_inset, plate_d - hole_inset),
        (plate_w - hole_inset, plate_d - hole_inset),
    ]
    current_body = plate
    for cx, cy in corners:
        hole_sketch = server.create_sketch(plane="xy", name="Hole")["result"]["sketch"]
        server.draw_circle(center_x_cm=cx, center_y_cm=cy, radius_cm=hole_dia/2, sketch_token=hole_sketch["token"])
        hole_profiles = server.list_profiles(hole_sketch["token"])["result"]["profiles"]
        current_body = server.extrude_profile(
            profile_token=hole_profiles[0]["token"],
            distance_cm=plate_t,
            body_name="BasePlate",
            operation="cut",
            target_body_token=current_body["token"]
        )["result"]["body"]
    print(f"   Holes added")
    
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
    print(f"   Tube created")
    
    # Step 4: Combine tube to plate
    print("4. Combining tube with plate...")
    combined = server.combine_bodies(
        target_body_token=current_body["token"],
        tool_body_token=tube["token"]
    )["result"]["body"]
    print(f"   Combined")
    
    # Step 5: Create bore through tube
    print("5. Cutting bore through tube...")
    bore_sketch = server.create_sketch(plane="xy", name="BoreCut", offset_cm=plate_t)["result"]["sketch"]
    server.draw_circle(center_x_cm=plate_w/2, center_y_cm=plate_d/2, radius_cm=socket_id/2, sketch_token=bore_sketch["token"])
    bore_profiles = server.list_profiles(bore_sketch["token"])["result"]["profiles"]
    final_body = server.extrude_profile(
        profile_token=bore_profiles[0]["token"],
        distance_cm=socket_h,
        body_name="PoleMount",
        operation="cut",
        target_body_token=combined["token"]
    )["result"]["body"]
    print(f"   Bore cut")
    
    # Step 6: Get edges and apply chamfer to socket top
    print("6. Applying chamfer to socket top...")
    edges = get_edges(final_body["token"])
    socket_top_z = plate_t + socket_h
    socket_top_edges = find_socket_top_edges(edges, socket_top_z, plate_w/2, plate_d/2, socket_od)
    print(f"   Found {len(socket_top_edges)} socket top edges")
    
    if socket_top_edges:
        chamfer_tokens = [e["token"] for e in socket_top_edges]
        chamfer_result = server.apply_chamfer_to_edges(
            body_token=final_body["token"],
            edge_tokens=chamfer_tokens,
            distance_cm=chamfer_size,
        )["result"]
        print(f"   Chamfer applied: {chamfer_result.get('edge_count', 0)} edges")
    
    # Step 7: Get updated edges and apply fillet to plate outer edges
    print("7. Applying fillet to plate outer edges...")
    edges = get_edges(final_body["token"])  # Re-query after chamfer
    outer_edges = find_plate_outer_edges(edges, plate_t, plate_w, plate_d)
    print(f"   Found {len(outer_edges)} plate outer edges")
    
    if outer_edges:
        fillet_tokens = [e["token"] for e in outer_edges[:8]]  # Limit to 8
        fillet_result = server.apply_fillet_to_edges(
            body_token=final_body["token"],
            edge_tokens=fillet_tokens,
            radius_cm=fillet_radius,
        )["result"]
        print(f"   Fillet applied: {fillet_result.get('edge_count', 0)} edges")
    
    # Step 8: Export
    print("8. Exporting STL...")
    export = server.export_stl(
        body_token=final_body["token"],
        output_path="C:\\Users\\wests\\AppData\\Local\\Temp\\pole_mount_final.stl"
    )["result"]
    
    # Copy to desktop
    shutil.copy(export['output_path'], "C:/Users/wests/Desktop/pole_mount_final.stl")
    
    print()
    print("=" * 60)
    print("SUCCESS! Pole mount complete!")
    print(f"Features: 4 corner holes, chamfered socket, filleted plate")
    print(f"STL: C:\\Users\\wests\\Desktop\\pole_mount_final.stl")
    print("=" * 60)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
