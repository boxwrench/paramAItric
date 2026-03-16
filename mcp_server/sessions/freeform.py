"""Freeform session management for ParamAItric.

Provides the guided AI modeling mode with mutation/verification cycles,
session lifecycle management, and rollback/replay capabilities.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from mcp_server.freeform import FreeformSession
from mcp_server.schemas import (
    CommitVerificationInput,
    EndFreeformSessionInput,
    ExportSessionLogInput,
    RollbackFreeformSessionInput,
    StartFreeformSessionInput,
    VerificationSnapshot,
)

if TYPE_CHECKING:
    from mcp_server.bridge_client import BridgeClient


class FreeformSessionManager:
    """Manages freeform CAD sessions with verification checkpoints.

    Freeform mode allows AI hosts to perform exploratory modeling with
    mandatory verification between mutations. This provides a middle ground
    between rigid predefined workflows and fully open-ended CAD automation.
    """

    def __init__(self) -> None:
        self.active_freeform_session: FreeformSession | None = None
        self._freeform_replay_mode = False

    def start_freeform_session(self, payload: dict) -> dict:
        """Start a new freeform session with a clean design."""
        if self.active_freeform_session:
            raise ValueError("A freeform session is already active. End it before starting a new one.")

        spec = StartFreeformSessionInput.from_payload(payload)
        session_id = str(uuid.uuid4())

        # Trigger a new design in Fusion
        new_design_res = self.new_design(spec.design_name)

        self.active_freeform_session = FreeformSession(
            session_id=session_id,
            design_name=spec.design_name,
            state="AWAITING_MUTATION",
            target_features=spec.target_features or []
        )
        return {
            "ok": True,
            "session_id": session_id,
            "design_name": spec.design_name,
            "message": "Freeform session started. The canvas is clean. You may now perform ONE mutation before verification is required.",
            "fusion_result": new_design_res,
        }

    def commit_verification(self, payload: dict) -> dict:
        """Commit verification after a mutation to unlock the next operation."""
        if not self.active_freeform_session:
            raise ValueError("No active freeform session.")
        if self.active_freeform_session.state != "AWAITING_VERIFICATION":
            raise ValueError("Session is not awaiting verification. You must perform a mutation first.")

        spec = CommitVerificationInput.from_payload(payload)
        if spec.resolved_features:
            unknown_features = [
                feature for feature in spec.resolved_features
                if feature not in self.active_freeform_session.target_feature_set
            ]
            if unknown_features:
                raise ValueError(
                    f"resolved_features contains undeclared manifest items: {unknown_features}"
                )

        # Automatically verify current state
        scene_res = self.get_scene_info()
        scene = scene_res["result"]
        snapshot = VerificationSnapshot.from_scene(scene)
        previous_snapshot = self.active_freeform_session.latest_committed_snapshot()
        verification_diff = self._build_freeform_verification_diff(previous_snapshot, snapshot.__dict__)
        verification_signals = self._build_freeform_verification_signals(
            spec=spec,
            snapshot=snapshot.__dict__,
            verification_diff=verification_diff,
        )

        # 1. Body count assertion
        if spec.expected_body_count != snapshot.body_count:
            return {
                "ok": False,
                "error": f"Verification failed: expected {spec.expected_body_count} bodies, but found {snapshot.body_count}.",
                "actual_body_count": snapshot.body_count,
                "verification_diff": verification_diff,
                "verification_signals": self._mark_signal_failed(
                    verification_signals,
                    "expected_body_count",
                    observed=snapshot.body_count,
                ),
                "hint": "Analyze the scene and correct your understanding, or undo/fix the geometry before trying to commit again."
            }

        # 2. Body count delta assertion
        if spec.expected_body_count_delta is not None:
            actual_body_count_delta = verification_diff["body_count_delta"]
            if actual_body_count_delta is None:
                return {
                    "ok": False,
                    "error": "Verification failed: expected_body_count_delta requires a prior committed snapshot.",
                    "verification_diff": verification_diff,
                    "verification_signals": self._mark_signal_failed(
                        verification_signals,
                        "expected_body_count_delta",
                        observed=None,
                    ),
                    "hint": "Use expected_body_count_delta only after at least one committed mutation."
                }
            if actual_body_count_delta != spec.expected_body_count_delta:
                return {
                    "ok": False,
                    "error": (
                        "Verification failed: expected body-count delta "
                        f"{spec.expected_body_count_delta}, but found {actual_body_count_delta}."
                    ),
                    "actual_body_count_delta": actual_body_count_delta,
                    "verification_diff": verification_diff,
                    "verification_signals": self._mark_signal_failed(
                        verification_signals,
                        "expected_body_count_delta",
                        observed=actual_body_count_delta,
                    ),
                    "hint": "Inspect whether the mutation created, merged, or split bodies unexpectedly."
                }

        # 3. Volume range assertion
        if spec.expected_volume_range is not None:
            total_volume = verification_diff["current_total_volume_cm3"]
            v_min, v_max = spec.expected_volume_range
            if not (v_min <= total_volume <= v_max):
                return {
                    "ok": False,
                    "error": f"Verification failed: total volume {total_volume:.3f} cm3 is outside expected range [{v_min}, {v_max}].",
                    "actual_total_volume": total_volume,
                    "verification_diff": verification_diff,
                    "verification_signals": self._mark_signal_failed(
                        verification_signals,
                        "expected_volume_range",
                        observed=total_volume,
                    ),
                    "hint": "Check your math or inspect if a cut was deeper/shallower than expected."
                }

        # 4. Volume delta sign assertion
        if spec.expected_volume_delta_sign is not None:
            actual_volume_delta_sign = verification_diff["volume_delta_sign"]
            if actual_volume_delta_sign is None:
                return {
                    "ok": False,
                    "error": "Verification failed: expected_volume_delta_sign requires a prior committed snapshot.",
                    "verification_diff": verification_diff,
                    "verification_signals": self._mark_signal_failed(
                        verification_signals,
                        "expected_volume_delta_sign",
                        observed=None,
                    ),
                    "hint": "Use expected_volume_delta_sign only after at least one committed mutation."
                }
            if actual_volume_delta_sign != spec.expected_volume_delta_sign:
                return {
                    "ok": False,
                    "error": (
                        "Verification failed: expected volume delta sign "
                        f"{spec.expected_volume_delta_sign}, but found {actual_volume_delta_sign}."
                    ),
                    "actual_volume_delta_sign": actual_volume_delta_sign,
                    "verification_diff": verification_diff,
                    "verification_signals": self._mark_signal_failed(
                        verification_signals,
                        "expected_volume_delta_sign",
                        observed=actual_volume_delta_sign,
                    ),
                    "hint": "Inspect whether the mutation added, removed, or failed to change material as intended."
                }

        # 5. Resolve features
        if spec.resolved_features:
            self.active_freeform_session.resolve_features(spec.resolved_features)

        verification_data = {
            "notes": spec.notes,
            "snapshot": snapshot.__dict__,
            "verification_diff": verification_diff,
            "verification_signals": verification_signals,
            "resolved_features": spec.resolved_features
        }
        self.active_freeform_session.commit(verification_data)

        return {
            "ok": True,
            "message": "Verification committed. The state is unlocked. You may perform your next mutation.",
            "snapshot": snapshot.__dict__,
            "verification_diff": verification_diff,
            "verification_signals": verification_signals,
        }

    def end_freeform_session(self, payload: dict) -> dict:
        """End the active freeform session with compliance audit."""
        if not self.active_freeform_session:
            raise ValueError("No active freeform session.")

        # Ensure they aren't abandoning an unverified mutation
        if self.active_freeform_session.state == "AWAITING_VERIFICATION":
            raise ValueError("Cannot end session while awaiting verification. Commit your last mutation first.")

        spec = EndFreeformSessionInput.from_payload(payload)

        # COMPLIANCE AUDIT
        target_set = set(self.active_freeform_session.target_features)
        resolved_set = self.active_freeform_session.resolved_features

        # Account for deferred features
        deferred_set = set()
        if spec.deferred_features:
            deferred_set = {d["feature"] for d in spec.deferred_features}

        missing = target_set - (resolved_set | deferred_set)

        if missing:
            return {
                "ok": False,
                "error": f"Compliance Audit Failed: Missing features: {list(missing)}",
                "hint": "You must resolve all target features or explicitly defer them before ending the session.",
                "resolved": list(resolved_set),
                "target": list(target_set)
            }

        session_data = {
            "session_id": self.active_freeform_session.session_id,
            "design_name": self.active_freeform_session.design_name,
            "mutations_logged": len(self.active_freeform_session.mutation_log),
            "manifest": {
                "resolved": list(resolved_set),
                "deferred": spec.deferred_features or []
            }
        }
        self.active_freeform_session = None
        return {
            "ok": True,
            "message": "Freeform session ended. Compliance audit passed.",
            "session": session_data,
        }

    def export_session_log(self, payload: dict) -> dict:
        """Export the full mutation and verification log for the session."""
        _ = payload  # Reserved for future filtering options
        if not self.active_freeform_session:
            raise ValueError("No active freeform session.")

        log = self.active_freeform_session.export_log()
        return {
            "ok": True,
            "session_log": log,
            "message": "Session log exported. You can use this log to reverse-engineer a reusable workflow macro."
        }

    def rollback_freeform_session(self, payload: dict) -> dict:
        """Rollback to a previous committed checkpoint in the session."""
        if not self.active_freeform_session:
            raise ValueError("No active freeform session.")

        session = self.active_freeform_session
        spec = RollbackFreeformSessionInput.from_payload(payload)
        current_step = len(session.mutation_log)
        target_step = current_step if spec.target_step is None else spec.target_step
        if target_step > current_step:
            raise ValueError(
                f"target_step {target_step} exceeds the last committed step {current_step}."
            )

        discarded_pending = session.pending_mutation is not None
        self._rebuild_freeform_session_to_step(target_step)

        assert self.active_freeform_session is not None
        return {
            "ok": True,
            "message": "Freeform session rolled back to a committed checkpoint.",
            "target_step": target_step,
            "discarded_pending_mutation": discarded_pending,
            "mutations_retained": len(self.active_freeform_session.mutation_log),
            "resolved_features": sorted(self.active_freeform_session.resolved_features),
            "state": self.active_freeform_session.state,
        }

    # -------------------------------------------------------------------------
    # Freeform verification helpers
    # -------------------------------------------------------------------------

    def _build_freeform_verification_diff(
        self,
        previous_snapshot: dict | None,
        current_snapshot: dict,
    ) -> dict:
        """Calculate the difference between two verification snapshots."""
        current_total_volume = self._snapshot_total_volume(current_snapshot)
        previous_total_volume = self._snapshot_total_volume(previous_snapshot)
        body_count = current_snapshot.get("body_count")
        previous_body_count = previous_snapshot.get("body_count") if previous_snapshot else None
        body_count_delta = None if previous_body_count is None or body_count is None else body_count - previous_body_count
        volume_delta = None if previous_total_volume is None else current_total_volume - previous_total_volume

        return {
            "previous_body_count": previous_body_count,
            "current_body_count": body_count,
            "body_count_delta": body_count_delta,
            "previous_total_volume_cm3": previous_total_volume,
            "current_total_volume_cm3": current_total_volume,
            "total_volume_delta_cm3": volume_delta,
            "volume_delta_sign": self._volume_delta_sign(volume_delta),
        }

    def _build_freeform_verification_signals(
        self,
        *,
        spec: CommitVerificationInput,
        snapshot: dict,
        verification_diff: dict,
    ) -> list[dict]:
        """Build the tiered verification signals for a commit operation."""
        current_body_count = snapshot.get("body_count")
        current_total_volume = verification_diff.get("current_total_volume_cm3")
        signals: list[dict] = [
            {
                "signal": "expected_body_count",
                "tier": "hard_gate",
                "provenance": "exact_kernel_fact",
                "accuracy": "exact",
                "status": "pass" if spec.expected_body_count == current_body_count else "fail",
                "expected": spec.expected_body_count,
                "observed": current_body_count,
                "context": "freeform_commit",
                "why": "Cheap structural assertion used to block runtime progression.",
            },
            {
                "signal": "current_total_volume_cm3",
                "tier": "audit_check",
                "provenance": "exact_but_context_sensitive",
                "accuracy": "default_physical_properties",
                "status": "observed",
                "observed": current_total_volume,
                "context": "freeform_commit",
                "why": "Useful physical-property observation, but stronger trust depends on explicit accuracy and tolerances.",
            },
            {
                "signal": "body_count_delta_observation",
                "tier": "diagnostic",
                "provenance": "exact_kernel_fact",
                "accuracy": "exact",
                "status": "observed",
                "observed": verification_diff.get("body_count_delta"),
                "context": "freeform_commit",
                "why": "Helpful drift clue, but not semantic proof by itself.",
            },
            {
                "signal": "volume_delta_sign_observation",
                "tier": "diagnostic",
                "provenance": "exact_but_context_sensitive",
                "accuracy": "derived_from_default_physical_properties",
                "status": "observed",
                "observed": verification_diff.get("volume_delta_sign"),
                "context": "freeform_commit",
                "why": "Useful change-direction clue, but should stay tolerance-aware.",
            },
        ]

        if spec.expected_body_count_delta is not None:
            observed_delta = verification_diff.get("body_count_delta")
            signals.append(
                {
                    "signal": "expected_body_count_delta",
                    "tier": "hard_gate",
                    "provenance": "exact_kernel_fact",
                    "accuracy": "exact",
                    "status": "pass" if observed_delta == spec.expected_body_count_delta else "fail",
                    "expected": spec.expected_body_count_delta,
                    "observed": observed_delta,
                    "context": "freeform_commit",
                    "why": "Explicit delta assertion for replay-safe structural change.",
                }
            )

        if spec.expected_volume_range is not None:
            v_min, v_max = spec.expected_volume_range
            in_range = current_total_volume is not None and v_min <= current_total_volume <= v_max
            signals.append(
                {
                    "signal": "expected_volume_range",
                    "tier": "hard_gate",
                    "provenance": "exact_but_context_sensitive",
                    "accuracy": "default_physical_properties",
                    "status": "pass" if in_range else "fail",
                    "expected": spec.expected_volume_range,
                    "observed": current_total_volume,
                    "context": "freeform_commit",
                    "why": "Manifest-declared volume envelope used as a gated constraint.",
                }
            )

        if spec.expected_volume_delta_sign is not None:
            observed_sign = verification_diff.get("volume_delta_sign")
            signals.append(
                {
                    "signal": "expected_volume_delta_sign",
                    "tier": "hard_gate",
                    "provenance": "exact_but_context_sensitive",
                    "accuracy": "derived_from_default_physical_properties",
                    "status": "pass" if observed_sign == spec.expected_volume_delta_sign else "fail",
                    "expected": spec.expected_volume_delta_sign,
                    "observed": observed_sign,
                    "context": "freeform_commit",
                    "why": "Cheap direction-of-change assertion for additive vs subtractive intent.",
                }
            )

        return signals

    def _mark_signal_failed(self, signals: list[dict], signal_name: str, *, observed) -> list[dict]:
        """Mark a specific verification signal as failed with observed value."""
        updated: list[dict] = []
        for signal in signals:
            item = dict(signal)
            if item.get("signal") == signal_name:
                item["status"] = "fail"
                item["observed"] = observed
            updated.append(item)
        return updated

    def _snapshot_total_volume(self, snapshot: dict | None) -> float | None:
        """Extract total volume from a verification snapshot."""
        if not snapshot:
            return None
        bodies_info = snapshot.get("bodies_info")
        if not isinstance(bodies_info, list):
            return None
        total = 0.0
        for body in bodies_info:
            volume = body.get("volume_cm3", 0.0)
            if isinstance(volume, (int, float)):
                total += float(volume)
        return total

    def _volume_delta_sign(self, volume_delta: float | None) -> str | None:
        """Determine the sign of volume change for verification reporting."""
        if volume_delta is None:
            return None
        if abs(volume_delta) <= 1e-6:
            return "unchanged"
        if volume_delta > 0:
            return "increase"
        return "decrease"

    # -------------------------------------------------------------------------
    # Session replay/rollback helpers
    # -------------------------------------------------------------------------

    def _rebuild_freeform_session_to_step(self, target_step: int) -> None:
        """Rebuild a freeform session by replaying mutations up to target_step."""
        session = self.active_freeform_session
        assert session is not None

        retained_records = list(session.mutation_log[:target_step])
        retained_profile_observations = dict(session.profile_observations)

        session.mutation_log = []
        session.pending_mutation = None
        session.resolved_features = set()
        session.state = "AWAITING_MUTATION"

        self._freeform_replay_mode = True
        try:
            self.new_design(session.design_name)
            token_map: dict[str, str] = {}
            for record in retained_records:
                replay_args = self._translate_replay_args(
                    tool=record.tool,
                    arguments=record.args,
                    token_map=token_map,
                    profile_observations=retained_profile_observations,
                )
                replay_result = self._send(record.tool, replay_args)
                self._collect_token_mappings(record.result, replay_result, token_map)
                session.mutation_log.append(record)
                verification = record.verification or {}
                resolved_features = verification.get("resolved_features") or []
                if resolved_features:
                    session.resolve_features(list(resolved_features))
        finally:
            self._freeform_replay_mode = False

    def _translate_replay_args(
        self,
        *,
        tool: str,
        arguments: dict,
        token_map: dict[str, str],
        profile_observations: dict[str, dict],
    ) -> dict:
        """Translate token references for session replay."""
        translated = self._translate_tokens(arguments, token_map)
        if tool in {"extrude_profile", "revolve_profile"}:
            old_profile_token = arguments.get("profile_token")
            if isinstance(old_profile_token, str) and old_profile_token not in token_map:
                translated["profile_token"] = self._rebind_profile_token(
                    old_profile_token=old_profile_token,
                    token_map=token_map,
                    profile_observations=profile_observations,
                )
        return translated

    def _translate_tokens(self, value: Any, token_map: dict[str, str]) -> Any:
        """Recursively translate token strings in a value structure."""
        if isinstance(value, dict):
            return {key: self._translate_tokens(item, token_map) for key, item in value.items()}
        if isinstance(value, list):
            return [self._translate_tokens(item, token_map) for item in value]
        if isinstance(value, str) and value in token_map:
            return token_map[value]
        return value

    def _rebind_profile_token(
        self,
        *,
        old_profile_token: str,
        token_map: dict[str, str],
        profile_observations: dict[str, dict],
    ) -> str:
        """Rebind a profile token during session replay by index or dimensions."""
        observation = profile_observations.get(old_profile_token)
        if observation is None:
            raise ValueError(
                f"Cannot replay mutation because profile token {old_profile_token!r} has no cached observation."
            )

        old_sketch_token = observation["sketch_token"]
        new_sketch_token = token_map.get(old_sketch_token)
        if new_sketch_token is None:
            raise ValueError(
                f"Cannot replay mutation because sketch token {old_sketch_token!r} was not remapped."
            )

        profiles = self.list_profiles(new_sketch_token)["result"]["profiles"]
        profile_index = observation["index"]
        if profile_index < len(profiles):
            rebound = profiles[profile_index]["token"]
            token_map[old_profile_token] = rebound
            return rebound

        expected_width = observation.get("width_cm")
        expected_height = observation.get("height_cm")
        for profile in profiles:
            if (
                profile.get("width_cm") == expected_width
                and profile.get("height_cm") == expected_height
            ):
                rebound = profile["token"]
                token_map[old_profile_token] = rebound
                return rebound

        raise ValueError(
            f"Cannot replay mutation because profile token {old_profile_token!r} could not be rebound."
        )

    def _collect_token_mappings(
        self,
        original_value: Any,
        replay_value: Any,
        token_map: dict[str, str]
    ) -> None:
        """Collect token mappings from replay results for subsequent translations."""
        if isinstance(original_value, dict) and isinstance(replay_value, dict):
            for key, original_item in original_value.items():
                if key not in replay_value:
                    continue
                replay_item = replay_value[key]
                if "token" in key and isinstance(original_item, str) and isinstance(replay_item, str):
                    token_map[original_item] = replay_item
                self._collect_token_mappings(original_item, replay_item, token_map)
            return
        if isinstance(original_value, list) and isinstance(replay_value, list):
            for original_item, replay_item in zip(original_value, replay_value):
                self._collect_token_mappings(original_item, replay_item, token_map)

