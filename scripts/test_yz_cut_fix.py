"""Test YZ plane cut fix - verifies CSG epsilon overlap principle."""
import sys
sys.path.insert(0, "C:\\Github\\paramAItric")

from mcp_server.fusion_360_mcp_server import Fusion360MCPBridge

def test_yz_cut_fix():
    """Test that YZ plane cuts now work after the two-sided extent fix."""
    bridge = Fusion360MCPBridge()
    
    def send(tool, params):
        return bridge.execute_tool(tool, params)
    
    print("=" * 60)
    print("Testing YZ Plane Cut Fix (Two-Sided Extent)")
    print("=" * 60)
    
    # Reset
    send("new_design", {"name": "YZ Cut Fix Test"})
    
    # Create box on XY plane
    print("\n1. Creating base box (XY plane sketch)...")
    sketch1 = send("create_sketch", {"plane": "xy", "name": "Base Box"})
    send("draw_rectangle", {"sketch_token": sketch1["token"], "width_cm": 10.0, "height_cm": 10.0})
    profiles1 = send("list_profiles", {"sketch_token": sketch1["token"]})
    profile1 = profiles1[0]
    body = send("extrude_profile", {
        "profile_token": profile1["token"],
        "distance_cm": 10.0,
        "body_name": "BaseBox"
    })
    print(f"   Created box: {body['name']}")
    
    # Create YZ plane sketch with circle for cut
    print("\n2. Creating YZ plane sketch with circle cut...")
    sketch2 = send("create_sketch", {"plane": "yz", "name": "YZ Cut Profile"})
    
    # Position circle at center of the box's YZ face
    send("draw_circle", {
        "sketch_token": sketch2["token"],
        "center_x_cm": 5.0,  # Y coordinate in YZ plane
        "center_y_cm": 5.0,  # Z coordinate in YZ plane
        "radius_cm": 2.0
    })
    profiles2 = send("list_profiles", {"sketch_token": sketch2["token"]})
    profile2 = profiles2[0]
    
    # Attempt YZ plane cut - this used to fail!
    print("\n3. Attempting YZ plane cut extrusion...")
    try:
        result = send("extrude_profile", {
            "profile_token": profile2["token"],
            "distance_cm": 15.0,  # Use larger distance with two-sided extent
            "body_name": "YZCut",
            "operation": "cut",
            "target_body_token": body["token"]
        })
        print(f"   ✓ SUCCESS! YZ plane cut worked!")
        print(f"   Result: {result}")
        
        # Verify body info
        body_info = send("get_body_info", {"body_token": body["token"]})
        print(f"\n4. Body after cut:")
        print(f"   Volume: {body_info.get('volume_cm3', 'N/A')} cm³")
        print(f"   Faces: {body_info.get('face_count', 'N/A')}")
        print(f"   Edges: {body_info.get('edge_count', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_yz_cut_fix()
    sys.exit(0 if success else 1)
