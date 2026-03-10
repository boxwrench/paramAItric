import pytest
from mcp_server.server import ParamAIToolServer
from mcp_server.bridge_client import BridgeClient

def test_freeform_session_lifecycle(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))
    
    # 1. Start session
    res = server.start_freeform_session({"design_name": "Test Bracket"})
    assert res["ok"] is True
    assert server.active_freeform_session is not None
    assert server.active_freeform_session.state == "AWAITING_MUTATION"
    
    # 2. Perform a mutation (create_sketch)
    # The mock bridge in ParamAItric naturally handles the state in DesignState
    res_sketch = server.create_sketch(
        plane="xy",
        name="Base Sketch"
    )
    assert res_sketch["result"]["sketch"]["token"] is not None
    sketch_token = res_sketch["result"]["sketch"]["token"]
    
    assert server.active_freeform_session.state == "AWAITING_VERIFICATION"
    assert len(server.active_freeform_session.mutation_log) == 0 # Not committed yet
    assert server.active_freeform_session.pending_mutation is not None
    assert server.active_freeform_session.pending_mutation.tool == "create_sketch"
    
    # 3. Try another mutation while locked -> should fail
    with pytest.raises(ValueError, match="FREEFORM LOCKED"):
        server.draw_rectangle(
            width_cm=5.0,
            height_cm=5.0,
            sketch_token=sketch_token
        )
        
    # 4. Perform inspection -> should be allowed
    scene = server.get_scene_info()["result"]
    assert len(scene["sketches"]) == 1
    
    # 5. Commit verification
    commit_res = server.commit_verification({
        "notes": "Verified one sketch exists.",
        "expected_body_count": 0
    })
    assert commit_res["ok"] is True
    assert server.active_freeform_session.state == "AWAITING_MUTATION"
    assert len(server.active_freeform_session.mutation_log) == 1
    
    # 6. End session
    end_res = server.end_freeform_session({})
    assert end_res["ok"] is True
    assert server.active_freeform_session is None

def test_freeform_find_face(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))
    
    server.start_freeform_session({"design_name": "Face Test"})
    
    # Create a box to get some faces
    # Mutation 1: create_sketch
    res_sk = server.create_sketch(plane="xy", name="S1")
    sketch_token = res_sk["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Sketch created.", "expected_body_count": 0})
    
    # Mutation 2: draw_rectangle
    server.draw_rectangle(width_cm=10.0, height_cm=10.0)
    server.commit_verification({"notes": "Rectangle drawn.", "expected_body_count": 0})
    
    # Fetch profile
    profiles = server.list_profiles(sketch_token=sketch_token)["result"]["profiles"]
    profile_token = profiles[0]["token"]
    
    # Mutation 3: extrude
    res = server.extrude_profile(profile_token=profile_token, distance_cm=5.0, body_name="Test Box")
    body_token = res["result"]["body"]["token"]
    server.commit_verification({"notes": "Box created.", "expected_body_count": 1})
    
    # Test find_face
    # top face should have highest Z
    top_face = server.find_face({"body_token": body_token, "selector": "top"})
    assert top_face["ok"] is True
    assert top_face["selector"] == "top"
    assert top_face["face_info"]["bounding_box"]["max_z"] == 5.0
    
    # bottom face should have min Z = 0
    bottom_face = server.find_face({"body_token": body_token, "selector": "bottom"})
    assert bottom_face["face_info"]["bounding_box"]["min_z"] == 0.0

def test_freeform_verification_failure(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))
    
    server.start_freeform_session({"design_name": "Test"})
    
    server.create_sketch(plane="xy", name="S1")
    
    # Fail verification by expecting 1 body when 0 exist
    commit_res = server.commit_verification({
        "notes": "I think there is a body.",
        "expected_body_count": 1
    })
    assert commit_res["ok"] is False
    assert "Verification failed" in commit_res["error"]
    assert server.active_freeform_session.state == "AWAITING_VERIFICATION"
