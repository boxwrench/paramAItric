"""Create pole mount manually step by step for better debugging."""
from mcp_server.server import ParamAIToolServer
import json

server = ParamAIToolServer()
INCH_TO_CM = 2.54

# User specs in inches
plate_w = 4.0 * INCH_TO_CM      # 10.16 cm
plate_d = 3.0 * INCH_TO_CM      # 7.62 cm
plate_t = 0.25 * INCH_TO_CM     # 0.635 cm
socket_id = 0.75 * INCH_TO_CM   # 1.905 cm  
socket_od = 1.25 * INCH_TO_CM   # 3.175 cm (0.75 + 2*0.25)
socket_h = 1.5 * INCH_TO_CM     # 3.81 cm

print("Creating Pole Mount manually...")
print(f"Plate: {plate_w:.2f}cm × {plate_d:.2f}cm × {plate_t:.2f}cm")
print(f"Socket: OD={socket_od:.2f}cm, ID={socket_id:.2f}cm, H={socket_h:.2f}cm")
print()

try:
    # Step 1: New design
    print("1. Creating new design...")
    server.new_design("Pole Mount")
    
    # Step 2: Create base plate sketch
    print("2. Creating base plate sketch...")
    sketch = server.create_sketch(plane="xy", name="BasePlate")["result"]["sketch"]
    sketch_token = sketch["token"]
    
    # Step 3: Draw rectangle for plate
    print("3. Drawing plate rectangle...")
    server.draw_rectangle(width_cm=plate_w, height_cm=plate_d, sketch_token=sketch_token)
    
    # Step 4: Get profiles and extrude plate
    print("4. Extruding base plate...")
    profiles = server.list_profiles(sketch_token)["result"]["profiles"]
    plate_body = server.extrude_profile(
        profile_token=profiles[0]["token"],
        distance_cm=plate_t,
        body_name="BasePlate"
    )["result"]["body"]
    print(f"   Plate created: {plate_body['width_cm']:.2f} x {plate_body['height_cm']:.2f} x {plate_body['thickness_cm']:.2f}")
    
    # Step 5: Create sketch for tube socket on top of plate
    print("5. Creating tube socket sketch...")
    tube_sketch = server.create_sketch(plane="xy", name="TubeSocket", offset_cm=plate_t)["result"]["sketch"]
    tube_sketch_token = tube_sketch["token"]
    
    # Step 6: Draw circle for tube OD (centered on plate)
    print("6. Drawing tube outer circle...")
    tube_center_x = plate_w / 2
    tube_center_y = plate_d / 2
    server.draw_circle(
        center_x_cm=tube_center_x,
        center_y_cm=tube_center_y,
        radius_cm=socket_od / 2,
        sketch_token=tube_sketch_token
    )
    
    # Step 7: Extrude tube
    print("7. Extruding tube socket...")
    tube_profiles = server.list_profiles(tube_sketch_token)["result"]["profiles"]
    tube_body = server.extrude_profile(
        profile_token=tube_profiles[0]["token"],
        distance_cm=socket_h,
        body_name="TubeSocket"
    )["result"]["body"]
    print(f"   Tube created: {tube_body['width_cm']:.2f} x {tube_body['height_cm']:.2f} x {tube_body['thickness_cm']:.2f}")
    
    # Step 8: Combine tube to plate
    print("8. Combining tube with plate...")
    combined = server.combine_bodies(
        target_body_token=plate_body["token"],
        tool_body_token=tube_body["token"]
    )["result"]["body"]
    print(f"   Combined body: {combined['width_cm']:.2f} x {combined['height_cm']:.2f} x {combined['thickness_cm']:.2f}")
    
    # Step 9: Create bore cut sketch on top of tube
    print("9. Creating bore cut sketch...")
    bore_sketch = server.create_sketch(plane="xy", name="BoreCut", offset_cm=plate_t)["result"]["sketch"]
    bore_sketch_token = bore_sketch["token"]
    
    # Step 10: Draw circle for bore ID
    print("10. Drawing bore circle...")
    server.draw_circle(
        center_x_cm=tube_center_x,
        center_y_cm=tube_center_y,
        radius_cm=socket_id / 2,
        sketch_token=bore_sketch_token
    )
    
    # Step 11: Cut the bore through tube
    print("11. Cutting bore through tube...")
    bore_profiles = server.list_profiles(bore_sketch_token)["result"]["profiles"]
    final_body = server.extrude_profile(
        profile_token=bore_profiles[0]["token"],
        distance_cm=socket_h,  # Cut through full tube height
        body_name="PoleMount",
        operation="cut",
        target_body_token=combined["token"]
    )["result"]["body"]
    print(f"    Final body: {final_body['width_cm']:.2f} x {final_body['height_cm']:.2f} x {final_body['thickness_cm']:.2f}")
    
    # Step 12: Export STL
    print("12. Exporting STL...")
    export = server.export_stl(
        body_token=final_body["token"],
        output_path="C:\\Users\\wests\\AppData\\Local\\Temp\\pole_mount.stl"
    )["result"]
    
    print()
    print("=" * 50)
    print("SUCCESS! Pole mount created!")
    print(f"STL exported to: {export['output_path']}")
    print("=" * 50)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
