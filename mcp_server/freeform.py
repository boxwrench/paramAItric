import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Literal, Any

# Standard constructive solid geometry overlap to avoid non-manifold coplanar surfaces.
BOOLEAN_EPSILON_CM = 0.001

MUTATION_TOOLS = {
    "create_sketch", "draw_rectangle", "draw_circle", "draw_triangle",
    "draw_slot", "draw_l_bracket_profile", "draw_revolve_profile",
    "extrude_profile", "apply_fillet", "apply_chamfer", "apply_shell",
    "cut_body_with_profile", "combine_bodies", "convert_bodies_to_components"
}

INSPECTION_TOOLS = {
    "list_design_bodies", "get_body_info", "get_body_faces",
    "get_body_edges", "list_profiles", "get_scene_info", "health",
    "get_workflow_catalog", "list_component_states", "get_component_state",
    "find_face"
}

SESSION_TOOLS = {
    "start_freeform_session", "commit_verification", "end_freeform_session", "export_session_log", "new_design"
}

@dataclass
class MutationRecord:
    step: int
    tool: str
    args: dict[str, Any]
    result: dict[str, Any]
    verification: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class FreeformSession:
    session_id: str
    design_name: str
    state: Literal["AWAITING_MUTATION", "AWAITING_VERIFICATION"]
    target_features: list[str] = field(default_factory=list)
    resolved_features: set[str] = field(default_factory=set)
    mutation_log: list[MutationRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    pending_mutation: MutationRecord | None = None

    def record_mutation(self, tool: str, args: dict, result: dict) -> None:
        self.pending_mutation = MutationRecord(
            step=len(self.mutation_log) + 1,
            tool=tool,
            args=args,
            result=result
        )
        self.state = "AWAITING_VERIFICATION"

    def resolve_features(self, features: list[str]) -> None:
        for f in features:
            self.resolved_features.add(f)

    def commit(self, verification: dict) -> None:
        if not self.pending_mutation:
            raise RuntimeError("No pending mutation to commit.")
        self.pending_mutation.verification = verification
        self.mutation_log.append(self.pending_mutation)
        self.pending_mutation = None
        self.state = "AWAITING_MUTATION"

    def export_log(self) -> dict:
        return {
            "session_id": self.session_id,
            "design_name": self.design_name,
            "created_at": self.created_at.isoformat(),
            "manifest": {
                "target_features": self.target_features,
                "resolved_features": list(self.resolved_features),
                "completion_pct": (len(self.resolved_features) / len(self.target_features) * 100) if self.target_features else 100
            },
            "mutations": [
                {
                    "step": m.step,
                    "tool": m.tool,
                    "args": m.args,
                    "result": m.result,
                    "verification": m.verification,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in self.mutation_log
            ],
        }
