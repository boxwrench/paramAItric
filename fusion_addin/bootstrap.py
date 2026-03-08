from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fusion_addin.ops import live_ops, mock_ops
from mcp_server.workflows import WorkflowRegistry, build_default_registry

if TYPE_CHECKING:
    from fusion_addin.ops.registry import OperationRegistry


@dataclass(frozen=True)
class BootstrapResult:
    mode: str
    workflow_registry: WorkflowRegistry

    def build_registry(self) -> "OperationRegistry":
        raise NotImplementedError


@dataclass(frozen=True)
class MockBootstrapResult(BootstrapResult):
    def build_registry(self) -> "OperationRegistry":
        return mock_ops.build_registry(self.workflow_registry)


@dataclass(frozen=True)
class LiveBootstrapResult(BootstrapResult):
    execution_context: live_ops.FusionExecutionContext

    def build_registry(self) -> "OperationRegistry":
        return live_ops.build_registry(
            workflow_registry=self.workflow_registry,
            execution_context=self.execution_context,
        )


def bootstrap_addin(workflow_registry: WorkflowRegistry | None = None) -> BootstrapResult:
    registry = workflow_registry or build_default_registry()
    execution_context = _build_live_execution_context()
    if execution_context is None:
        return MockBootstrapResult(mode="mock", workflow_registry=registry)
    return LiveBootstrapResult(mode="live", workflow_registry=registry, execution_context=execution_context)


def _build_live_execution_context() -> live_ops.FusionExecutionContext | None:
    try:
        import adsk.core  # type: ignore[import-not-found]
        import adsk.fusion  # type: ignore[import-not-found]
    except ImportError:
        return None

    app = adsk.core.Application.get()
    if app is None:
        return None

    product = app.activeProduct
    if product is None:
        return None

    design = adsk.fusion.Design.cast(product)
    if design is None:
        return None

    adapter = live_ops.FusionApiAdapter(app=app, ui=app.userInterface, design=design)
    return live_ops.FusionExecutionContext(adapter=adapter)
