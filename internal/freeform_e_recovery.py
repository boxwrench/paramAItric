"""
Freeform E — Deliberate Failure and Recovery
=============================================
Tests: State machine lock behavior + AI recovery discipline

Recipe:
  Create a 5cm × 5cm × 5cm cube. Then bore a 2cm diameter hole through
  the center, top to bottom.

Scripted behavior:
  After the bore is cut, we deliberately commit verification with
  expected_body_count: 2 (INCORRECT — should be 1). The state machine
  must stay locked. We then call get_body_info, diagnose that only 1 body
  exists, correct the assertion to expected_body_count: 1, and successfully
  commit. Finally, verify the session ends cleanly.

Manifest:
  ["Cube body", "Center bore cut", "RECOVERY: corrected body count assertion"]

Failure mode targeted:
  AI either trivially succeeds (wrong assertion not tested) or gets
  permanently stuck (no recovery path). Pass condition: AI diagnoses and
  self-corrects within the locked state.
"""
from mcp_server.server import ParamAIToolServer


CUBE_SIZE_CM  = 5.0
BORE_RADIUS_CM = 1.0   # 2cm diameter bore


def main() -> None:
    server = ParamAIToolServer()
    print("=== STARTING FREEFORM E: DELIBERATE FAILURE AND RECOVERY ===")

    manifest = [
        "Cube body",
        "Center bore cut",
        "RECOVERY: corrected body count assertion",
    ]
    server.start_freeform_session({
        "design_name": "FM-E Failure and Recovery",
        "target_features": manifest,
    })

    # ── Phase 1: Create cube ─────────────────────────────────────────────────
    res_sk = server.create_sketch(plane="xy", name="Cube Base Sketch")
    sk_cube = res_sk["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Cube sketch created.", "expected_body_count": 0})

    server.draw_rectangle(width_cm=CUBE_SIZE_CM, height_cm=CUBE_SIZE_CM, sketch_token=sk_cube)
    cube_profs = server.list_profiles(sketch_token=sk_cube)
    cube_prof_token = cube_profs["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "Cube profile drawn, resolved.", "expected_body_count": 0})

    res_ext = server.extrude_profile(
        profile_token=cube_prof_token,
        distance_cm=CUBE_SIZE_CM,
        body_name="Cube",
    )
    body_token = res_ext["result"]["body"]["token"]
    server.commit_verification({
        "notes": "Cube extruded: 5×5×5cm solid.",
        "expected_body_count": 1,
        "resolved_features": ["Cube body"],
    })
    print("[+] FEATURE RESOLVED: Cube body")

    # ── Phase 2: Cut center bore ─────────────────────────────────────────────
    res_bore_sk = server.create_sketch(plane="xy", name="Bore Sketch")
    sk_bore = res_bore_sk["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Bore sketch created.", "expected_body_count": 1})

    server.draw_circle(
        center_x_cm=CUBE_SIZE_CM / 2.0,
        center_y_cm=CUBE_SIZE_CM / 2.0,
        radius_cm=BORE_RADIUS_CM,
        sketch_token=sk_bore,
    )
    bore_profs = server.list_profiles(sketch_token=sk_bore)
    bore_prof_token = bore_profs["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "Bore circle drawn.", "expected_body_count": 1})

    server.extrude_profile(
        profile_token=bore_prof_token,
        distance_cm=CUBE_SIZE_CM + 0.002,
        body_name="Bore Cut",
        operation="cut",
        target_body_token=body_token,
        symmetric=True,
    )
    print("[~] Bore cut executed. Now deliberately making WRONG assertion...")

    # ── Phase 3: DELIBERATE FAILURE — wrong body count ───────────────────────
    # The AI incorrectly believes the cut produced 2 bodies. This must be rejected.
    bad_commit = server.commit_verification({
        "notes": "I think the bore cut created 2 bodies (wrong!).",
        "expected_body_count": 2,  # INCORRECT — it's still 1 body
    })

    assert bad_commit["ok"] is False, "State machine should have rejected the wrong assertion!"
    print(f"[+] LOCK CONFIRMED: Server rejected wrong assertion → '{bad_commit.get('error')}'")
    print(f"    Session state: {server.active_freeform_session.state}")
    assert server.active_freeform_session.state == "AWAITING_VERIFICATION", \
        "Session must remain AWAITING_VERIFICATION after failed commit"
    print("[+] Session remains locked in AWAITING_VERIFICATION state.")

    # ── Phase 4: RECOVERY — diagnose via inspection, correct assertion ────────
    print("\n[~] Diagnosing via get_scene_info (inspection allowed while locked)...")
    scene = server.get_scene_info()["result"]
    actual_body_count = len(scene.get("bodies", []))
    print(f"    get_scene_info reports {actual_body_count} body/bodies.")

    # Also inspect body info to confirm it is 1 solid with a hole
    body_info_res = server.get_body_info({"body_token": body_token})
    body_info = body_info_res["result"]["body_info"]
    print(f"    Body volume: {body_info['volume_cm3']:.4f} cm³ (cube minus bore)")

    cube_volume = CUBE_SIZE_CM ** 3
    bore_volume = 3.14159 * BORE_RADIUS_CM ** 2 * CUBE_SIZE_CM
    expected_volume = cube_volume - bore_volume
    print(f"    Expected ~{expected_volume:.2f} cm³ → confirms single body with bore.")

    # Corrected commit
    print("\n[~] Correcting assertion to expected_body_count: 1...")
    good_commit = server.commit_verification({
        "notes": (
            "RECOVERY: Inspected scene — only 1 body. The bore is a through-hole, "
            "not a split. Correcting assertion."
        ),
        "expected_body_count": 1,  # CORRECT
        "resolved_features": ["Center bore cut", "RECOVERY: corrected body count assertion"],
    })

    assert good_commit["ok"] is True, f"Corrected commit should succeed, got: {good_commit}"
    print("[+] RECOVERY SUCCESSFUL: Corrected assertion accepted.")
    print(f"[+] FEATURE RESOLVED: Center bore cut")
    print(f"[+] FEATURE RESOLVED: RECOVERY: corrected body count assertion")

    # ── Compliance Audit ─────────────────────────────────────────────────────
    print("\n--- FINAL COMPLIANCE AUDIT ---")
    end_res = server.end_freeform_session({})
    if end_res["ok"]:
        print("[+] AUDIT PASSED: Clean recovery from wrong assertion. Session ended.")
        server.export_stl(
            body_token=body_token,
            output_path="manual_test_output/fm_e_recovery_cube.stl",
        )
        print("[+] Model Exported.")
    else:
        print(f"[-] AUDIT FAILED: {end_res.get('error')}")

    print("=== SESSION ENDED ===")


if __name__ == "__main__":
    main()
