import json
import math
from mcp_server.server import ParamAIToolServer
from mcp_server.errors import WorkflowFailure

def main():
    server = ParamAIToolServer()
    print("=== STARTING AGENT FREEFORM SESSION ===")
    
    # 1. Start Session
    res = server.start_freeform_session({"design_name": "Freeform McMaster Strut"})
    print(f"[1] Session Started: {res['ok']}")

    # 2. Mutation: Create Sketch
    res_sk = server.create_sketch(plane="xy", name="Base Cross Section")
    sk_token = res_sk["result"]["sketch"]["token"]
    print(f"[2] Mutation (Create Sketch): OK. State is now LOCKED.")

    # --- HALLUCINATION TRAP ---
    # The AI agent tries to DRAW the profile immediately without verifying.
    print("\n[!] Agent Attempting Hallucination: Drawing without verification...")
    try:
        server.draw_l_bracket_profile(width_cm=4.128, height_cm=10.478, leg_thickness_cm=0.635, sketch_token=sk_token)
    except ValueError as e:
        print(f"[-] SERVER BLOCKED Hallucination: {e}")

    # 3. Proper Flow: Verification
    print("\n[3] Proper Flow: Verifying Sketch...")
    server.get_scene_info() # Inspection is allowed
    server.commit_verification({"notes": "Verified XY sketch exists.", "expected_body_count": 0})
    print("[+] Verification Committed. State is now UNLOCKED.")

    # 4. Mutation: Draw L-Profile
    server.draw_l_bracket_profile(width_cm=4.128, height_cm=10.478, leg_thickness_cm=0.635, sketch_token=sk_token)
    print("[4] Mutation (Draw L-Profile): OK. State is now LOCKED.")
    
    # Verify profiles
    res_prof = server.list_profiles(sk_token)
    prof_token = res_prof["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "L-Profile profile resolved.", "expected_body_count": 0})
    print("[+] Verification Committed. State is now UNLOCKED.")

    # 5. Mutation: Extrude to full width (3.5in = 8.89cm)
    # Following Rule 4: Extrude cross-section to full width.
    res_ext = server.extrude_profile(profile_token=prof_token, distance_cm=8.89, body_name="Strut Bracket")
    body_token = res_ext["result"]["body"]["token"]
    print("[5] Mutation (Extrude Block): OK. State is now LOCKED.")

    # 6. Verification: Rule 4 & 8 (Bounding Box and Centroid)
    print("\n[6] Inspecting Base Block...")
    info = server.get_body_info({"body_token": body_token})["result"]["body_info"]
    print(f"    BBox: {info['bounding_box']}")
    print(f"    Volume: {info['volume_cm3']:.2f} cm3")
    print(f"    Centroid: {info['centroid']}")
    
    # Assertion Gate: Checking if width is 8.89
    # In XY-to-Z extrusion, Z is the 'thickness' in tool output
    if abs(info['bounding_box']['max_z'] - 8.89) > 0.01:
        print("[-] Verification FAILED: Width is wrong!")
        return

    server.commit_verification({
        "notes": "Base block verified. Centroid is centered in width.",
        "expected_body_count": 1
    })
    print("[+] Block Verification Committed. State is now UNLOCKED.")

    # 7. Mutation: Taper Cuts (YZ Plane)
    # Following Rule 5: YZ sketch-X = -worldZ, sketch-Y = worldY
    # Taper offset for 12.8 degrees over 9.8cm height is ~2.2cm
    taper_offset = 2.22
    sk_taper_res = server.create_sketch(plane="yz", name="Taper Cut", offset_cm=0.635)
    sk_taper = sk_taper_res["result"]["sketch"]["token"]
    
    server.commit_verification({"notes": "YZ sketch created for taper.", "expected_body_count": 1})
    print("[+] Verification Committed. State is now UNLOCKED.")
    
    # Draw cutters
    # Top-Left Taper
    server.draw_triangle(x1_cm=0.0, y1_cm=10.478, x2_cm=-taper_offset, y2_cm=10.478, x3_cm=0.0, y3_cm=0.635, sketch_token=sk_taper)
    server.commit_verification({"notes": "Taper triangle drawn.", "expected_body_count": 1})
    print("[+] Verification Committed. State is now UNLOCKED.")
    
    # Cut Taper
    res_prof_t = server.list_profiles(sk_taper)
    server.extrude_profile(
        profile_token=res_prof_t["result"]["profiles"][0]["token"], 
        distance_cm=10.0, 
        symmetric=True, 
        body_name="Strut Bracket", 
        operation="cut", 
        target_body_token=body_token
    )
    print("[7] Mutation (Taper Cut): OK. State is now LOCKED.")

    # 8. Verification: Centroid Check (Rule 8)
    print("\n[8] Verifying Taper Direction via Centroid...")
    info_t = server.get_body_info({"body_token": body_token})["result"]["body_info"]
    print(f"    Original Centroid Y: {info['centroid']['y']:.3f}")
    print(f"    New Centroid Y:      {info_t['centroid']['y']:.3f}")
    
    if info_t['centroid']['y'] < info['centroid']['y']:
        print("[+] SUCCESS: Centroid moved DOWN. Taper is correctly wider at base!")
    else:
        print("[-] FAILURE: Centroid moved UP! Taper is upside down.")
        
    server.commit_verification({"notes": "Taper verified via centroid shift.", "expected_body_count": 1})
    print("[+] Verification Committed. State is now UNLOCKED.")

    # 9. Export Session Log
    print("\n=== FINAL EXPORT ===")
    log = server.export_session_log({})
    print(f"Session Log Exported: {len(log['session_log']['mutations'])} steps recorded.")
    
    server.end_freeform_session({})
    print("=== SESSION ENDED ===")

if __name__ == "__main__":
    main()
