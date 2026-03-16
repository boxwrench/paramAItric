"""Base workflow infrastructure for ParamAItric.

Provides the core WorkflowMixin with _send, _bridge_step, and shared
workflow building blocks used across all workflow families.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from mcp_server.bridge_client import BridgeCancelledError, BridgeTimeoutError
from mcp_server.errors import WorkflowFailure
from mcp_server.schemas import CommandEnvelope, VerificationSnapshot

if TYPE_CHECKING:
    from mcp_server.bridge_client import BridgeClient
    from mcp_server.workflow_registry import WorkflowRegistry


class WorkflowMixin:
    """Base mixin providing core workflow infrastructure.

    This mixin provides:
    - Bridge communication (_send)
    - Error handling with structured failures (_bridge_step)
    - Common workflow patterns (_create_rectangular_prism, etc.)
    """

    def __init__(
        self,
        bridge_client: BridgeClient | None = None,
        workflow_registry: WorkflowRegistry | None = None,
    ) -> None:
        self.bridge_client = bridge_client
        self.workflow_registry = workflow_registry

    def _send(self, command: str, arguments: dict) -> dict:
        """Send a command to the Fusion bridge with error handling."""
        envelope = CommandEnvelope.build(command, arguments)
        try:
            result = self.bridge_client.send(envelope)
        except BridgeTimeoutError as exc:
            raise WorkflowFailure(
                f"Bridge command timed out: {exc}",
                stage=command,
                classification="timeout",
                partial_result={"command": command, "arguments": arguments},
                next_step="Check if Fusion is responsive and retry.",
            ) from exc
        except BridgeCancelledError as exc:
            raise WorkflowFailure(
                f"Bridge command was cancelled: {exc}",
                stage=command,
                classification="cancelled",
                partial_result={"command": command, "arguments": arguments},
                next_step="Retry the operation if cancellation was unintended.",
            ) from exc
        except RuntimeError as exc:
            raise WorkflowFailure(
                f"Bridge command failed: {exc}",
                stage=command,
                classification="bridge_error",
                partial_result={"command": command, "arguments": arguments},
                next_step="Check Fusion bridge logs and retry.",
            ) from exc

        if not result.get("ok"):
            raise WorkflowFailure(
                result.get("error", "Unknown bridge error"),
                stage=command,
                classification="bridge_error",
                partial_result={"result": result, "command": command, "arguments": arguments},
                next_step="Check error details and retry with corrected parameters.",
            )
        return result

    def _bridge_step(
        self,
        *,
        stage: str,
        stages: list[dict],
        action: Callable,
        partial_result: dict | None = None,
        next_step: str | None = None,
    ):
        """Execute a workflow step with standardized error handling.

        Args:
            stage: Name of the current workflow stage.
            stages: Accumulated stages list for partial results.
            action: Callable that performs the actual work.
            partial_result: Additional context to include in failure reports.
            next_step: Guidance message for recovery on failure.

        Returns:
            The result of the action callable.

        Raises:
            WorkflowFailure: Structured failure with context on any error.
        """
        try:
            return action()
        except WorkflowFailure as exc:
            # Re-raise bridge errors with the workflow stage name instead of command name
            if exc.classification in ("bridge_error", "timeout", "cancelled"):
                payload = {"stages": list(stages)}
                if partial_result:
                    payload.update(partial_result)
                raise WorkflowFailure(
                    str(exc),
                    stage=stage,
                    classification=exc.classification,
                    partial_result=payload,
                    next_step=next_step or exc.next_step,
                ) from exc.__cause__
            raise
        except BridgeTimeoutError as exc:
            payload = {"stages": list(stages)}
            if partial_result:
                payload.update(partial_result)
            raise WorkflowFailure(
                f"Workflow bridge call timed out during {stage}: {exc}",
                stage=stage,
                classification="timeout",
                partial_result=payload,
                next_step=next_step or "Retry after checking whether Fusion is busy or the configured bridge timeout is too aggressive.",
            ) from exc
        except BridgeCancelledError as exc:
            payload = {"stages": list(stages)}
            if partial_result:
                payload.update(partial_result)
            raise WorkflowFailure(
                f"Workflow bridge call was cancelled during {stage}: {exc}",
                stage=stage,
                classification="cancelled",
                partial_result=payload,
                next_step=next_step or "Retry if the cancellation was unintended.",
            ) from exc
        except Exception as exc:
            payload = {"stages": list(stages)}
            if partial_result:
                payload.update(partial_result)
            raise WorkflowFailure(
                f"Workflow failed at stage '{stage}': {exc}",
                stage=stage,
                classification="unexpected_error",
                partial_result=payload,
                next_step=next_step or "Review the error details and retry.",
            ) from exc

    def _verify_clean_state(self, stages: list[dict]) -> VerificationSnapshot:
        """Verify the design starts from a clean state.

        Args:
            stages: Accumulated stages list.

        Returns:
            The initial verification snapshot.

        Raises:
            WorkflowFailure: If the design is not in a clean state.
        """
        initial_scene = self._bridge_step(
            stage="verify_clean_state",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
        )
        initial_snapshot = VerificationSnapshot.from_scene(initial_scene)
        if initial_snapshot.body_count != 0 or initial_snapshot.export_count != 0:
            raise WorkflowFailure(
                "Workflow did not start from a clean design state.",
                stage="verify_clean_state",
                classification="state_drift",
                partial_result={"scene": initial_scene, "stages": stages},
                next_step="Inspect the design reset path before attempting another workflow.",
            )
        stages.append(
            {
                "stage": "verify_clean_state",
                "status": "completed",
                "snapshot": initial_snapshot.__dict__,
            }
        )
        return initial_snapshot

    def _verify_single_body(
        self,
        body: dict,
        expected_dimensions: dict,
        stages: list[dict],
        workflow_name: str,
    ) -> VerificationSnapshot:
        """Verify a single body exists with expected dimensions.

        Args:
            body: The body dict to verify.
            expected_dimensions: Dict of expected dimension values.
            stages: Accumulated stages list.
            workflow_name: Name for error messages.

        Returns:
            The verification snapshot.

        Raises:
            WorkflowFailure: If verification fails.
        """
        scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
        snapshot = VerificationSnapshot.from_scene(scene)
        if snapshot.body_count != 1:
            raise WorkflowFailure(
                f"{workflow_name} workflow verification failed: expected exactly one body.",
                stage="verify_body_count",
                classification="verification_failed",
                partial_result={"scene": scene, "stages": stages},
                next_step="Preserve the partial model and inspect body creation before retrying.",
            )

        actual_dimensions = {
            "width_cm": body["width_cm"],
            "height_cm": body["height_cm"],
            "thickness_cm": body["thickness_cm"],
        }
        if actual_dimensions != expected_dimensions:
            raise WorkflowFailure(
                f"{workflow_name} workflow verification failed: body dimensions do not match.",
                stage="verify_dimensions",
                classification="verification_failed",
                partial_result={"body": body, "expected": expected_dimensions, "stages": stages},
                next_step="Inspect the profile selection and extrusion distance before retrying.",
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": snapshot.__dict__,
                "dimensions": actual_dimensions,
            }
        )
        return snapshot

    def _close(self, actual: object, expected: float, tolerance: float = 1e-9) -> bool:
        """Check if an actual value is close to expected within tolerance."""
        try:
            number = float(actual)
        except (TypeError, ValueError):
            return False
        return abs(number - expected) <= tolerance

    def _select_profile_by_dimensions(
        self,
        profiles: list[dict],
        expected_width_cm: float,
        expected_height_cm: float,
        workflow_label: str,
        stages: list[dict],
    ) -> dict:
        """Select a profile by matching dimensions.

        Args:
            profiles: List of profile dicts with width_cm and height_cm.
            expected_width_cm: Expected width to match.
            expected_height_cm: Expected height to match.
            workflow_label: Label for error messages.
            stages: Accumulated stages list for partial results.

        Returns:
            The matching profile dict.

        Raises:
            WorkflowFailure: If no unique profile matches.
        """
        matches = [
            profile
            for profile in profiles
            if self._close(profile.get("width_cm"), expected_width_cm)
            and self._close(profile.get("height_cm"), expected_height_cm)
        ]
        if len(matches) != 1:
            raise WorkflowFailure(
                f"{workflow_label} workflow could not determine the intended profile.",
                stage="list_profiles",
                classification="verification_failed",
                partial_result={
                    "profiles": profiles,
                    "expected_width_cm": expected_width_cm,
                    "expected_height_cm": expected_height_cm,
                    "stages": stages,
                },
                next_step="Inspect the sketch profile set before extrusion.",
            )
        return matches[0]

    def _verify_body_against_expected_dimensions(
        self,
        *,
        stages: list[dict],
        body: dict,
        expected_dimensions: dict[str, float],
        failure_message: str,
        next_step: str,
        operation_label: str,
    ) -> VerificationSnapshot:
        """Verify body dimensions match expected values.

        Args:
            stages: Accumulated stages list.
            body: Body dict to verify.
            expected_dimensions: Dict of expected dimension values.
            failure_message: Message for failure exception.
            next_step: Guidance for recovery on failure.
            operation_label: Label for the operation in stage records.

        Returns:
            The verification snapshot.

        Raises:
            WorkflowFailure: If verification fails.
        """
        scene = self._bridge_step(
            stage="verify_geometry",
            stages=stages,
            action=lambda: self.get_scene_info()["result"],
            partial_result={"body": body},
        )
        snapshot = VerificationSnapshot.from_scene(scene)
        actual_dimensions = {
            "width_cm": body["width_cm"],
            "height_cm": body["height_cm"],
            "thickness_cm": body["thickness_cm"],
        }
        dimensions_match = all(
            self._close(actual_dimensions[field_name], expected_value)
            for field_name, expected_value in expected_dimensions.items()
        )
        if snapshot.body_count != 1 or not dimensions_match:
            raise WorkflowFailure(
                failure_message,
                stage="verify_geometry",
                classification="verification_failed",
                partial_result={"scene": scene, "body": body, "expected": expected_dimensions, "stages": stages},
                next_step=next_step,
            )
        stages.append(
            {
                "stage": "verify_geometry",
                "status": "completed",
                "snapshot": snapshot.__dict__,
                "dimensions": actual_dimensions,
                "operation": operation_label,
            }
        )
        return snapshot

    def _matching_profiles_by_dimensions(
        self,
        profiles: list[dict],
        *,
        expected_width_cm: float,
        expected_height_cm: float,
    ) -> list[dict]:
        """Find profiles matching expected dimensions.

        Args:
            profiles: List of profile dicts with width_cm and height_cm.
            expected_width_cm: Expected width to match.
            expected_height_cm: Expected height to match.

        Returns:
            List of matching profile dicts.
        """
        return [
            profile
            for profile in profiles
            if self._close(profile.get("width_cm"), expected_width_cm)
            and self._close(profile.get("height_cm"), expected_height_cm)
        ]

    # -------------------------------------------------------------------------
    # Abstract methods provided by other mixins
    # -------------------------------------------------------------------------

    def new_design(self, name: str = "ParamAItric Design") -> dict:
        """Create a new design - implemented by PrimitiveMixin."""
        raise NotImplementedError

    def get_scene_info(self) -> dict:
        """Get scene info - implemented by PrimitiveMixin."""
        raise NotImplementedError

    def create_sketch(self, plane: str, name: str, offset_cm: float | None = None) -> dict:
        """Create a sketch - implemented by PrimitiveMixin."""
        raise NotImplementedError

    def draw_rectangle(self, width_cm: float, height_cm: float, sketch_token: str | None = None) -> dict:
        """Draw a rectangle - implemented by PrimitiveMixin."""
        raise NotImplementedError

    def list_profiles(self, sketch_token: str) -> dict:
        """List profiles - implemented by PrimitiveMixin."""
        raise NotImplementedError

    def extrude_profile(self, profile_token: str, distance_cm: float, body_name: str, **kwargs) -> dict:
        """Extrude a profile - implemented by PrimitiveMixin."""
        raise NotImplementedError

    def export_stl(self, body_token: str, output_path: str) -> dict:
        """Export STL - implemented by PrimitiveMixin."""
        raise NotImplementedError
