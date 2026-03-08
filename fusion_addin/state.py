from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from tempfile import gettempdir


@dataclass
class SketchState:
    token: str
    name: str
    plane: str
    profile_bounds: list[dict[str, float]] = field(default_factory=list)
    circles: list[dict[str, float]] = field(default_factory=list)


@dataclass
class BodyState:
    token: str
    name: str
    width_cm: float
    height_cm: float
    thickness_cm: float


@dataclass
class DesignState:
    design_name: str = "ParamAItric Design"
    sketches: dict[str, SketchState] = field(default_factory=dict)
    bodies: dict[str, BodyState] = field(default_factory=dict)
    exports: list[str] = field(default_factory=list)
    active_sketch_token: str | None = None
    next_id: int = 1

    def issue_token(self, prefix: str) -> str:
        token = f"{prefix}-{self.next_id}"
        self.next_id += 1
        return token

    def export(self, output_path: str) -> str:
        destination = Path(output_path).expanduser().resolve(strict=False)
        if not destination.suffix:
            raise ValueError("output_path must include a file extension.")
        if "manual_test_output" not in destination.parts:
            try:
                destination.relative_to(Path(gettempdir()).resolve(strict=False))
            except ValueError as exc:
                raise ValueError("output_path must stay inside an allowlisted export directory.") from exc
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("mock stl export\n", encoding="ascii")
        self.exports.append(str(destination))
        return str(destination)
