"""
Freeform D — Enclosure Lid with Retention Clips
================================================
Tests: Multi-body combine discipline + compliance audit gate

Recipe:
  Design a snap-on lid for a 10cm × 8cm box. The lid is 0.5cm thick,
  10.4cm × 8.4cm outer (0.2cm overlap per side). On each long side add two
  cantilever retention clips: each clip is 1.5cm long × 0.3cm thick × 0.4cm tall,
  attached flush to the lid edge, with a 0.1cm hook protrusion at the free end.
  4 clips total, evenly spaced on each long side.

Manifest:
  ["Lid plate body", "Clip 1 body + combined", "Clip 2 body + combined",
   "Clip 3 body + combined", "Clip 4 body + combined", "Final body count = 1"]

Failure mode targeted:
  AI creates 5 separate bodies and declares success without combining.
  expected_body_count: 1 at end-of-session compliance audit catches this.

Clip geometry (simplified):
  Each clip is an L-shaped protrusion: a vertical wall + small hook.
  We model each clip as a thin rectangular box (1.5cm × 0.3cm × 0.4cm)
  combined into the lid body. The 0.1cm hook is added as a second small
  extrude on top.

  Clip placement (long sides = along X axis, 10.4cm wide):
    Side A (front, Y=0):   Clip 1 at X=2.0, Clip 2 at X=7.0
    Side B (back, Y=8.4):  Clip 3 at X=2.0, Clip 4 at X=7.0
  Clips hang down from the lid edge (extruded in -Z direction).
"""
from mcp_server.server import ParamAIToolServer


LID_WIDTH_CM   = 10.4
LID_DEPTH_CM   =  8.4
LID_HEIGHT_CM  =  0.5

CLIP_LENGTH_CM = 1.5   # along X
CLIP_THICK_CM  = 0.3   # along Y (into edge)
CLIP_TALL_CM   = 0.4   # hangs below lid

HOOK_LENGTH_CM = CLIP_LENGTH_CM  # same footprint, tiny extrude inward
HOOK_THICK_CM  = 0.1             # 0.1cm hook
HOOK_TALL_CM   = 0.1

# Four clip origins (bottom-left of clip rectangle, in XY).
# Side A: clips hang from Y=0 edge, so clip body extends from Y=-CLIP_THICK to Y=0
# Side B: clips hang from Y=LID_DEPTH edge, clip body from Y=LID_DEPTH to Y=LID_DEPTH+CLIP_THICK
CLIP_POSITIONS = [
    # (origin_x, origin_y, width_cm, depth_cm, side_label)
    (2.0,                       -CLIP_THICK_CM, CLIP_LENGTH_CM, CLIP_THICK_CM, "A1"),  # front left
    (LID_WIDTH_CM - 2.0 - CLIP_LENGTH_CM, -CLIP_THICK_CM, CLIP_LENGTH_CM, CLIP_THICK_CM, "A2"),  # front right
    (2.0,                       LID_DEPTH_CM,  CLIP_LENGTH_CM, CLIP_THICK_CM, "B1"),  # back left
    (LID_WIDTH_CM - 2.0 - CLIP_LENGTH_CM, LID_DEPTH_CM,  CLIP_LENGTH_CM, CLIP_THICK_CM, "B2"),  # back right
]


def main() -> None:
    server = ParamAIToolServer()
    print("=== STARTING FREEFORM D: ENCLOSURE LID WITH RETENTION CLIPS ===")

    manifest = [
        "Lid plate body",
        "Clip 1 body + combined",
        "Clip 2 body + combined",
        "Clip 3 body + combined",
        "Clip 4 body + combined",
        "Final body count = 1",
    ]
    server.start_freeform_session({
        "design_name": "FM-D Enclosure Lid with Clips",
        "target_features": manifest,
    })

    # ── Phase 1: Lid plate ───────────────────────────────────────────────────
    res_sk = server.create_sketch(plane="xy", name="Lid Base Sketch")
    sk_lid = res_sk["result"]["sketch"]["token"]
    server.commit_verification({"notes": "Lid sketch created.", "expected_body_count": 0})

    server.draw_rectangle(width_cm=LID_WIDTH_CM, height_cm=LID_DEPTH_CM, sketch_token=sk_lid)
    lid_profs = server.list_profiles(sketch_token=sk_lid)
    lid_prof_token = lid_profs["result"]["profiles"][0]["token"]
    server.commit_verification({"notes": "Lid rectangle drawn, profile resolved.", "expected_body_count": 0})

    res_ext = server.extrude_profile(
        profile_token=lid_prof_token,
        distance_cm=LID_HEIGHT_CM,
        body_name="Lid Plate",
    )
    body_token = res_ext["result"]["body"]["token"]
    server.commit_verification({
        "notes": f"Lid plate extruded: {LID_WIDTH_CM}×{LID_DEPTH_CM}×{LID_HEIGHT_CM}cm.",
        "expected_body_count": 1,
        "resolved_features": ["Lid plate body"],
    })
    print("[+] FEATURE RESOLVED: Lid plate body")

    # ── Phase 2: 4 Retention Clips ──────────────────────────────────────────
    # Each clip is built as a new_body then immediately combined into the lid.
    # After each combine, body_count must be 1.
    clip_feature_labels = [
        "Clip 1 body + combined",
        "Clip 2 body + combined",
        "Clip 3 body + combined",
        "Clip 4 body + combined",
    ]

    for clip_idx, (ox, oy, w, d, label) in enumerate(CLIP_POSITIONS):
        clip_num = clip_idx + 1
        feature_label = clip_feature_labels[clip_idx]

        # Mutation 1: Create clip sketch
        res_clip_sk = server.create_sketch(
            plane="xy",
            name=f"Clip {clip_num} Sketch",
        )
        sk_clip = res_clip_sk["result"]["sketch"]["token"]
        server.commit_verification({
            "notes": f"Clip {clip_num} sketch created.",
            "expected_body_count": 1,
        })

        # Mutation 2: Draw clip rectangle (list_profiles is inspection — no commit needed between)
        server.draw_rectangle_at(
            origin_x_cm=ox,
            origin_y_cm=oy,
            width_cm=w,
            height_cm=abs(d),
            sketch_token=sk_clip,
        )
        # list_profiles is an inspection call (allowed while locked after draw)
        clip_profs = server.list_profiles(sketch_token=sk_clip)
        clip_prof_token = clip_profs["result"]["profiles"][0]["token"]
        server.commit_verification({
            "notes": f"Clip {clip_num} rectangle drawn, profile resolved.",
            "expected_body_count": 1,
        })

        # Mutation 3: Extrude clip as a new_body
        res_clip_ext = server.extrude_profile(
            profile_token=clip_prof_token,
            distance_cm=CLIP_TALL_CM,
            body_name=f"Clip {clip_num}",
            operation="new_body",
        )
        clip_body_token = res_clip_ext["result"]["body"]["token"]
        server.commit_verification({
            "notes": f"Clip {clip_num} body extruded. 2 bodies now exist.",
            "expected_body_count": 2,
        })

        # Mutation 4: Immediately combine clip into lid — discipline test
        server.combine_bodies(
            target_body_token=body_token,
            tool_body_token=clip_body_token,
        )
        # On the final clip, also resolve the 'Final body count = 1' feature
        resolved = [feature_label]
        if clip_num == len(CLIP_POSITIONS):
            resolved.append("Final body count = 1")
        server.commit_verification({
            "notes": f"Clip {clip_num} combined into lid. Back to 1 body.",
            "expected_body_count": 1,
            "resolved_features": resolved,
        })
        print(f"[+] FEATURE RESOLVED: {feature_label}")
        if clip_num == len(CLIP_POSITIONS):
            print("[+] FEATURE RESOLVED: Final body count = 1")

    # ── Phase 3: Final body count check (inspection only — already resolved above) ──

    # ── Compliance Audit ────────────────────────────────────────────────────
    print("\n--- FINAL COMPLIANCE AUDIT ---")
    end_res = server.end_freeform_session({})
    if end_res["ok"]:
        print("[+] AUDIT PASSED: All clips combined, body count = 1.")
        server.export_stl(
            body_token=body_token,
            output_path="manual_test_output/fm_d_lid_clips.stl",
        )
        print("[+] Model Exported.")
    else:
        print(f"[-] AUDIT FAILED: {end_res.get('error')}")

    print("=== SESSION ENDED ===")


if __name__ == "__main__":
    main()
