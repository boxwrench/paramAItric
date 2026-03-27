"""Create pole mount with mounting holes."""
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

# Mounting hole specs
hole_dia = 0.25 * INCH_TO_CM    # 0.635 cm (#8 screw)
hole_offset = 0.5 * INCH_TO_CM  # 1.27 cm from edge

print("Creating Pole Mount with mounting holes...")
print()

try:
    # Create base plate
    print("1. Creating base plate...")
    server.new_design("Pole Mount with Holes")
    sketch = server.create_sketch(plane="xy", name="BasePlate")["result"]["sketch"]
    server.draw_rectangle(width_cm=plate_w, height_cm=plate_d, sketch_token=sketch["token"])
    profiles = server.list_profiles(sketch["token"])["result"]["profiles"]
    plate = server.extrude_profile(
        profile_token=profiles[0]["token"],
        distance_cm=plate_t,
        body_name="BasePlate"
    )["result"]["body"]
    
    # Add first mounting hole (top)
    print("2. Adding mounting hole 1...")
    hole1_sketch = server.create_sketch(plane="xy", name="Hole1")["result"]["sketch"]
    server.draw_circle(
        center_x_cm=plate_w/2,
        center_y_cm=hole_offset,
        radius_cm=hole_dia/2,
        sketch_token=hole1_sketch["token"]
    )
    hole1_profiles = server.list_profiles(hole1_sketch["token"])["result"]["profiles"]
    plate_with_hole1 = server.extrude_profile(
        profile_token=hole1_profiles[0]["token"],
        distance_cm=plate_t,
        body_name="BasePlate",
        operation="cut",
        target_body_token=plate["token"]
    )["result"]["body"]
    
    # Add second mounting hole (bottom)
    print("3. Adding mounting hole 2...")
    hole2_sketch = server.create_sketch(plane="xy", name="Hole2")["result"]["sketch"]
    server.draw_circle(
        center_x_cm=plate_w/2,
        center_y_cm=plate_d - hole_offset,
        radius_cm=hole_dia/2,
        sketch_token=hole2_sketch["token"]
    )
    hole2_profiles = server.list_profiles(hole2_sketch["token"])["result"]["profiles"]
    plate_with_holes = server.extrude_profile(
        profile_token=hole2_profiles[0]["token"],
        distance_cm=plate_t,
        body_name="BasePlate",
        operation="cut",
        target_body_token=plate_with_hole1["token"]
    )["result"]["body"]
    
    # Create tube socket
    print("4. Creating tube socket...")
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
    print("5. Combining tube with plate...")
    combined = server.combine_bodies(
        target_body_token=plate_with_holes["token"],
        tool_body_token=tube["token"]
    )["result"]["body"]
    
    # Create bore through tube
    print("6. Cutting bore through tube...")
    bore_sketch = server.create_sketch(plane="xy", name="BoreCut", offset_cm=plate_t)["result"]["sketch"]
    server.draw_circle(
        center_x_cm=plate_w/2,
        center_y_cm=plate_d/2,
        radius_cm=socket_id/2,
        sketch_token=bore_sketch["token"]
    )
    bore_profiles = server.list_profiles(bore_sketch["token"])["result"]["profiles"]
    final = server.extrude_profile(
        profile_token=bore_profiles[0]["token"],
        distance_cm=socket_h,
        body_name="PoleMount",
        operation="cut",
        target_body_token=combined["token"]
    )["result"]["body"]
    
    # Export
    print("7. Exporting STL...")
    export = server.export_stl(
        body_token=final["token"],
        output_path="C:\\Users\\wests\\AppData\\Local\\Temp\\pole_mount_with_holes.stl"
    )["result"]
    
    print()
    print("=" * 50)
    print("SUCCESS! Pole mount with holes created!")
    print(f"Dimensions: {final['width_cm']:.2f} x {final['height_cm']:.2f} x {final['thickness_cm']:.2f} cm")
    print(f"STL: {export['output_path']}")
    print("=" * 50)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
