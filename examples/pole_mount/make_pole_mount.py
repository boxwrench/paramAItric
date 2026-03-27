"""Create a pole mount: 4"×3" plate with 0.75" ID socket, 0.25" walls, 1.5" tall socket."""
from mcp_server.server import ParamAIToolServer
import json

# Initialize server
server = ParamAIToolServer()

# Convert inches to cm (Fusion uses cm internally)
INCH_TO_CM = 2.54

# User specs:
# - Plate: 4" × 3"
# - Socket ID: 0.75"
# - Wall thickness: 0.25"
# - Socket height: 1.5"

plate_width_in = 4.0
plate_depth_in = 3.0
wall_thickness_in = 0.25
socket_id_in = 0.75
socket_height_in = 1.5

# Calculate dimensions
socket_od_in = socket_id_in + (2 * wall_thickness_in)  # 1.25"
plate_thickness_in = 0.25  # Standard mounting plate thickness

# Payload for tube_mounting_plate workflow
payload = {
    "workflow_name": "tube_mounting_plate",
    "width_cm": plate_width_in * INCH_TO_CM,
    "height_cm": plate_depth_in * INCH_TO_CM,
    "plate_thickness_cm": plate_thickness_in * INCH_TO_CM,
    "hole_diameter_cm": 0.25 * INCH_TO_CM,  # #8 screw holes
    "edge_offset_y_cm": 0.375 * INCH_TO_CM,  # Mounting hole inset from edges
    "tube_outer_diameter_cm": socket_od_in * INCH_TO_CM,
    "tube_inner_diameter_cm": socket_id_in * INCH_TO_CM,
    "tube_height_cm": socket_height_in * INCH_TO_CM,
    "plane": "xy",
    "sketch_name": "BasePlate",
    "first_hole_sketch_name": "MountHole1",
    "second_hole_sketch_name": "MountHole2", 
    "tube_sketch_name": "TubeSocket",
    "bore_sketch_name": "BoreCut",
    "body_name": "PoleMount",
    "output_path": "C:\\Users\\wests\\AppData\\Local\\Temp\\pole_mount.stl"
}

print("Creating Pole Mount:")
print(f"  Plate: {plate_width_in}\" × {plate_depth_in}\" × {plate_thickness_in}\"")
print(f"  Socket: OD={socket_od_in}\", ID={socket_id_in}\", Height={socket_height_in}\"")
print(f"  Wall thickness: {wall_thickness_in}\"")
print()

try:
    result = server.create_tube_mounting_plate(payload)
    print("SUCCESS!")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
