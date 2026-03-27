"""Debug version to see what's happening with the tube mounting plate."""
from mcp_server.server import ParamAIToolServer
from mcp_server.schemas import CreateTubeMountingPlateInput
import json

# Initialize server
server = ParamAIToolServer()

# Convert inches to cm (Fusion uses cm internally)
INCH_TO_CM = 2.54

# User specs
plate_width_in = 4.0
plate_depth_in = 3.0
wall_thickness_in = 0.25
socket_id_in = 0.75
socket_height_in = 1.5
socket_od_in = socket_id_in + (2 * wall_thickness_in)
plate_thickness_in = 0.25

# Build payload
payload = {
    "workflow_name": "tube_mounting_plate",
    "width_cm": plate_width_in * INCH_TO_CM,
    "height_cm": plate_depth_in * INCH_TO_CM,
    "plate_thickness_cm": plate_thickness_in * INCH_TO_CM,
    "hole_diameter_cm": 0.25 * INCH_TO_CM,
    "edge_offset_y_cm": 0.5 * INCH_TO_CM,  # Adjusted for better placement
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

print("Expected dimensions:")
print(f"  Plate: {payload['width_cm']:.3f}cm × {payload['height_cm']:.3f}cm × {payload['plate_thickness_cm']:.3f}cm")
print(f"  Tube OD: {payload['tube_outer_diameter_cm']:.3f}cm, ID: {payload['tube_inner_diameter_cm']:.3f}cm")
print(f"  Tube height: {payload['tube_height_cm']:.3f}cm")
print()

# First create a simple spacer to test the connection
print("Testing connection with simple spacer...")
try:
    spacer_result = server.create_spacer({
        "width_cm": 5.0,
        "height_cm": 5.0, 
        "thickness_cm": 1.0,
        "plane": "xy",
        "sketch_name": "Test",
        "body_name": "TestSpacer",
        "output_path": "C:\\Users\\wests\\AppData\\Local\\Temp\\test_spacer.stl"
    })
    print("Spacer created successfully!")
    print(f"Body dimensions: {spacer_result.get('body', {}).get('width_cm')} x {spacer_result.get('body', {}).get('height_cm')} x {spacer_result.get('body', {}).get('thickness_cm')}")
except Exception as e:
    print(f"Spacer failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("Now trying tube mounting plate...")
try:
    result = server.create_tube_mounting_plate(payload)
    print("SUCCESS!")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
