"""Small internal contract for the Utility plate proof, not a general CAD IR."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

from mcp_server.operations import Operation
from mcp_server.errors import WorkflowFailure


class Editability(str, Enum):
    RECIPE = "parameterized_recipe"
    HISTORY = "native_feature_history"
    STATIC = "static_geometry"


@dataclass(frozen=True)
class Capabilities:
    name: str
    evidence: str
    operations: frozenset[str]
    measurements: frozenset[str]
    exports: frozenset[str]
    editability: Editability

    def require(self, *, operations=(), measurements=(), exports=()) -> None:
        missing = {
            "operations": sorted(set(operations) - self.operations),
            "measurements": sorted(set(measurements) - self.measurements),
            "exports": sorted(set(exports) - self.exports),
        }
        if any(missing.values()):
            raise WorkflowFailure(
                f"{self.name} does not support the requested capabilities: {missing}",
                stage="capabilities", classification="unsupported_capability",
                partial_result=missing, next_step="Use the supported plate scope or qualify the missing capability.",
            )


@dataclass
class Part:
    directory: Path
    revision: int = 0
    artifacts: dict[str, Path] = field(default_factory=dict)
    # Adapter-private state: never interpreted by the product workflow.
    state: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Measurements:
    facts: dict
    provenance: str
    accuracy: str


class PlateBackend(Protocol):
    capabilities: Capabilities

    def start_part(self, directory: Path, parameters: dict) -> Part: ...
    def apply(self, part: Part, operation: Operation) -> None: ...
    def inspect(self, part: Part) -> Measurements: ...
    def export(self, part: Part, formats: tuple[str, ...]) -> dict[str, Path]: ...
