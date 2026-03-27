"""Debug edge analysis for chamfer/fillet."""
from mcp_server.server import ParamAIToolServer
import json

server = ParamAIToolServer()
INCH_TO_CM = 2.54

# Create a simple test body first
print("Creating test body...")
server.new_design("Edge Debug")
sketch = server.create_sketch(plane="xy", name="Test")["result"]["sketch"]
server.draw_rectangle(width_cm=5*INCH_TO_CM, height_cm=5*INCH_TO_CM, sketch_token=sketch["token"])
profiles = server.list_profiles(sketch["token"])["result"]["profiles"]
body = server.extrude_profile(
    profile_token=profiles[0]["token"],
    distance_cm=2*INCH_TO_CM,
    body_name="TestBody"
)["result"]["body"]

print(f"Body token: {body['token']}")
print(f"Body dimensions: {body['width_cm']:.2f} x {body['height_cm']:.2f} x {body['thickness_cm']:.2f}")
print()

# Get edges
print("Getting edges...")
edges_result = server.get_body_edges({"body_token": body["token"]})["result"]
edges = edges_result.get("body_edges", [])
print(f"Total edges: {len(edges)}")
print()

# Print all edge info
print("All edges:")
for i, edge in enumerate(edges):
    print(f"  {i}: token={edge['token'][:30]}... type={edge['type']}, length={edge['length_cm']:.3f}")
    print(f"      start=({edge['start_point']['x']:.2f}, {edge['start_point']['y']:.2f}, {edge['start_point']['z']:.2f})")
    print(f"      end=({edge['end_point']['x']:.2f}, {edge['end_point']['y']:.2f}, {edge['end_point']['z']:.2f})")
print()

# Try to apply fillet to all edges
print("Trying to fillet all edges...")
edge_tokens = [e["token"] for e in edges]
try:
    result = server.apply_fillet_to_edges(
        body_token=body["token"],
        edge_tokens=edge_tokens[:4],  # Just first 4
        radius_cm=0.5,
    )["result"]
    print(f"Result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
