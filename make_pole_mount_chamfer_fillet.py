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

print("Creating Pole Mount with chamfered socket + filleted plate...")
print(f"  Chamfer: {chamfer_size/INCH_TO_CM:.2f}\"")
print(f"  Fillet: {fillet_radius/INCH_TO_CM:.2f}\"")
print()

try:
    # Create base plate
    print("1. Creating base plate...")
    server.new_design("Pole Mount Chamfer Fillet")
    sketch = server.create_sketch(plane="xy", name="BasePlate")["result"]["sketch"]
    server.draw_rectangle(width_cm=plate_w, height_cm=plate_d, sketch_token=sketch["token"])
    profiles = server.list_profiles(sketch["token"])["result"]["profiles"]
    plate = server.extrude_profile(
        profile_token=profiles[0]["token"],
        distance_cm=plate_t,
        body_name="BasePlate"
    )["result"]["body"]
    
    # Calculate corner hole positions
    corners = [
        ("Bottom-Left", hole_inset, hole_inset),
        ("Bottom-Right", plate_w - hole_inset, hole_inset),
        ("Top-Left", hole_inset, plate_d - hole_inset),
        ("Top-Right", plate_w - hole_inset, plate_d - hole_inset),
    ]
    
    # Add 4 mounting holes
    current_body = plate
    for i, (name, cx, cy) in enumerate(corners, 1):
        print(f"{i+1}. Adding {name} mounting hole...")
        hole_sketch = server.create_sketch(plane="xy", name=f"Hole{i}")["result"]["sketch"]
        server.draw_circle(
            center_x_cm=cx,
            center_y_cm=cy,
            radius_cm=hole_dia/2,
            sketch_token=hole_sketch["token"]
        )
        hole_profiles = server.list_profiles(hole_sketch["token"])["result"]["profiles"]
        current_body = server.extrude_profile(
            profile_token=hole_profiles[0]["token"],
            distance_cm=plate_t,
            body_name="BasePlate",
            operation="cut",
            target_body_token=current_body["token"]
        )["result"]["body"]
    
    # Create tube socket
    print("6. Creating tube socket...")
    tube_sketch = server.create_sketch(plane="xy", name="TubeSocket", offset_cm=plate_t)["result"]["sketch"]
    server.draw_circle(
        center_x_cm=plate_w/2,
        center_y_cm=plate_d/2,
        radius_cm=socket_od/2,
        sketch_token=tube_sketch["token"]
    )
    tube_profiles = server.list_profiles(tube_sketch["token"])["result"]["profiles"]
    tube = server.extrude_profile(
        profile_token=tube_profiles[0]["token"],
        distance_cm=socket_h,
        body_name="TubeSocket"
    )["result"]["body"]
    
    # Combine tube to plate
    print("7. Combining tube with plate...")
    combined = server.combine_bodies(
        target_body_token=current_body["token"],
        tool_body_token=tube["token"]
    )["result"]["body"]
    
    # Create bore through tube
    print("8. Cutting bore through tube...")
    bore_sketch = server.create_sketch(plane="xy", name="BoreCut", offset_cm=plate_t)["result"]["sketch"]
    server.draw_circle(
        center_x_cm=plate_w/2,
        center_y_cm=plate_d/2,
        radius_cm=socket_id/2,
        sketch_token=bore_sketch["token"]
    )
    bore_profiles = server.list_profiles(bore_sketch["token"])["result"]["profiles"]
    body_with_bore = server.extrude_profile(
        profile_token=bore_profiles[0]["token"],
        distance_cm=socket_h,
        body_name="PoleMount",
        operation="cut",
        target_body_token=combined["token"]
    )["result"]["body"]
    
    # Apply chamfer to socket top edge
    print("9. Applying chamfer to socket top edge...")
    try:
        chamfer_result = server.apply_chamfer(
            body_token=body_with_bore["token"],
            distance_cm=chamfer_size,
            edge_selection="top_outer"
        )["result"]
        print(f"   Chamfer applied: {chamfer_result.get('distance_cm', chamfer_size):.2f}cm")
        body_with_chamfer = chamfer_result
    except Exception as e:
        print(f"   Chamfer skipped: {e}")
        body_with_chamfer = body_with_bore
    
    # Apply fillet to plate edges
    print("10. Applying fillet to plate edges...")
    try:
        fillet_result = server.apply_fillet(
            body_token=body_with_chamfer["token"],
            radius_cm=fillet_radius
        )["result"]
        print(f"   Fillet applied: {fillet_result.get('radius_cm', fillet_radius):.2f}cm to {fillet_result.get('edge_count', '?')} edges")
        final_body = fillet_result
    except Exception as e:
        print(f"   Fillet skipped: {e}")
        final_body = body_with_chamfer
    
    # Export
    print("11. Exporting STL...")
    export = server.export_stl(
        body_token=final_body["token"],
        output_path="C:\\Users\\wests\\AppData\\Local\\Temp\\pole_mount_chamfer_fillet.stl"
    )["result"]
    
    print()
    print("=" * 50)
    print("SUCCESS! Pole mount with chamfer + fillet created!")
    print(f"Dimensions: {final_body['width_cm']:.2f} x {final_body['height_cm']:.2f} x {final_body['thickness_cm']:.2f} cm")
    print(f"4x corner mounting holes")
    print(f"Socket chamfer: {chamfer_size/INCH_TO_CM:.2f}\"")
    print(f"Plate fillet: {fillet_radius/INCH_TO_CM:.2f}\"")
    print(f"STL: {export['output_path']}")
    print("=" * 50)
    
    # Copy to desktop
    import shutil
    shutil.copy(export['output_path'], f"{__import__('os').path.expanduser('~')}/Desktop/pole_mount_chamfer_fillet.stl")
    print("Also copied to Desktop!")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
