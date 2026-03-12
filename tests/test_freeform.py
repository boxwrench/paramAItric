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
    assert commit_res["verification_diff"]["current_body_count"] == 0
    assert commit_res["verification_diff"]["body_count_delta"] is None
    assert "verification_signals" in commit_res
    body_count_signal = next(signal for signal in commit_res["verification_signals"] if signal["signal"] == "expected_body_count")
    assert body_count_signal["tier"] == "hard_gate"
    assert body_count_signal["provenance"] == "exact_kernel_fact"
    assert body_count_signal["accuracy"] == "exact"
    assert body_count_signal["status"] == "pass"
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
    assert "verification_diff" in commit_res
    assert "verification_signals" in commit_res
    body_count_signal = next(signal for signal in commit_res["verification_signals"] if signal["signal"] == "expected_body_count")
    assert body_count_signal["status"] == "fail"

def test_freeform_rejects_duplicate_manifest_features(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    with pytest.raises(ValueError, match="Duplicate target_features entry"):
        server.start_freeform_session({
            "design_name": "Dupes",
            "target_features": ["body", "body"],
        })

def test_freeform_rejects_undeclared_resolved_feature(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    server.start_freeform_session({
        "design_name": "Manifest Test",
        "target_features": ["base sketch"],
    })
    server.create_sketch(plane="xy", name="S1")

    with pytest.raises(ValueError, match="undeclared manifest items"):
        server.commit_verification({
            "notes": "Trying to resolve something undeclared.",
            "expected_body_count": 0,
            "resolved_features": ["wrong feature"],
        })

def test_freeform_commit_requires_expected_body_count(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    server.start_freeform_session({"design_name": "Expected Count Test"})
    server.create_sketch(plane="xy", name="S1")

    with pytest.raises(ValueError, match="expected_body_count is required"):
        server.commit_verification({
            "notes": "No body count provided.",
        })

def test_freeform_commit_supports_delta_assertions(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    server.start_freeform_session({"design_name": "Delta Test"})
    sketch = server.create_sketch(plane="xy", name="Base")
    sketch_token = sketch["result"]["sketch"]["token"]
    server.commit_verification({
        "notes": "Sketch created.",
        "expected_body_count": 0,
    })

    server.draw_rectangle(width_cm=5.0, height_cm=5.0, sketch_token=sketch_token)
    server.commit_verification({
        "notes": "Rectangle drawn.",
        "expected_body_count": 0,
        "expected_body_count_delta": 0,
        "expected_volume_delta_sign": "unchanged",
    })

def test_freeform_commit_reports_verification_signal_tiers(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    server.start_freeform_session({"design_name": "Signal Smoke"})
    sketch = server.create_sketch(plane="xy", name="Base")
    sketch_token = sketch["result"]["sketch"]["token"]
    server.commit_verification({
        "notes": "Sketch created.",
        "expected_body_count": 0,
    })

    server.draw_rectangle(width_cm=5.0, height_cm=5.0, sketch_token=sketch_token)
    commit_res = server.commit_verification({
        "notes": "Rectangle drawn.",
        "expected_body_count": 0,
        "expected_body_count_delta": 0,
        "expected_volume_delta_sign": "unchanged",
    })

    assert commit_res["ok"] is True
    signals = {signal["signal"]: signal for signal in commit_res["verification_signals"]}
    assert signals["expected_body_count"]["tier"] == "hard_gate"
    assert signals["expected_body_count"]["status"] == "pass"
    assert signals["expected_body_count_delta"]["tier"] == "hard_gate"
    assert signals["expected_body_count_delta"]["status"] == "pass"
    assert signals["expected_volume_delta_sign"]["tier"] == "hard_gate"
    assert signals["expected_volume_delta_sign"]["status"] == "pass"
    assert signals["current_total_volume_cm3"]["tier"] == "audit_check"
    assert signals["current_total_volume_cm3"]["accuracy"] == "default_physical_properties"
    assert signals["current_total_volume_cm3"]["status"] == "observed"
    assert signals["body_count_delta_observation"]["tier"] == "diagnostic"
    assert signals["volume_delta_sign_observation"]["tier"] == "diagnostic"

def test_freeform_rollback_discards_pending_mutation(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    server.start_freeform_session({"design_name": "Rollback Pending"})
    sketch = server.create_sketch(plane="xy", name="Base")
    sketch_token = sketch["result"]["sketch"]["token"]
    server.commit_verification({
        "notes": "Sketch created.",
        "expected_body_count": 0,
    })

    server.draw_rectangle(width_cm=5.0, height_cm=5.0, sketch_token=sketch_token)
    rollback_res = server.rollback_freeform_session({})

    assert rollback_res["ok"] is True
    assert rollback_res["discarded_pending_mutation"] is True
    assert server.active_freeform_session is not None
    assert server.active_freeform_session.state == "AWAITING_MUTATION"
    assert len(server.active_freeform_session.mutation_log) == 1

def test_freeform_rollback_replays_committed_extrude(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    server.start_freeform_session({"design_name": "Rollback Replay"})
    sketch = server.create_sketch(plane="xy", name="Base")
    sketch_token = sketch["result"]["sketch"]["token"]
    server.commit_verification({
        "notes": "Sketch created.",
        "expected_body_count": 0,
    })

    server.draw_rectangle(width_cm=5.0, height_cm=5.0, sketch_token=sketch_token)
    server.commit_verification({
        "notes": "Rectangle drawn.",
        "expected_body_count": 0,
    })

    profiles = server.list_profiles(sketch_token=sketch_token)["result"]["profiles"]
    profile_token = profiles[0]["token"]
    body = server.extrude_profile(profile_token=profile_token, distance_cm=2.0, body_name="Block")
    body_token = body["result"]["body"]["token"]
    server.commit_verification({
        "notes": "Block created.",
        "expected_body_count": 1,
    })

    server.apply_fillet(body_token=body_token, radius_cm=0.1)
    rollback_res = server.rollback_freeform_session({})

    assert rollback_res["ok"] is True
    assert rollback_res["target_step"] == 3
    assert rollback_res["discarded_pending_mutation"] is True
    scene = server.get_scene_info()["result"]
    assert len(scene["bodies"]) == 1
    assert server.active_freeform_session is not None
    assert server.active_freeform_session.state == "AWAITING_MUTATION"

def test_freeform_rollback_to_explicit_step_rewinds_resolved_features(running_bridge):
    _, base_url = running_bridge
    server = ParamAIToolServer(bridge_client=BridgeClient(base_url))

    server.start_freeform_session({
        "design_name": "Rollback Step",
        "target_features": ["sketch", "rectangle"],
    })
    sketch = server.create_sketch(plane="xy", name="Base")
    sketch_token = sketch["result"]["sketch"]["token"]
    server.commit_verification({
        "notes": "Sketch created.",
        "expected_body_count": 0,
        "resolved_features": ["sketch"],
    })

    server.draw_rectangle(width_cm=5.0, height_cm=5.0, sketch_token=sketch_token)
    server.commit_verification({
        "notes": "Rectangle drawn.",
        "expected_body_count": 0,
        "resolved_features": ["rectangle"],
    })

    rollback_res = server.rollback_freeform_session({"target_step": 1})

    assert rollback_res["ok"] is True
    assert rollback_res["target_step"] == 1
    assert rollback_res["resolved_features"] == ["sketch"]
    assert server.active_freeform_session is not None
    assert server.active_freeform_session.resolved_features == {"sketch"}
