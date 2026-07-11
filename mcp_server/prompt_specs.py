"""Prompt registry for high-level ParamAItric MCP entrypoints.

Prompts are host-facing convenience entrypoints layered on top of the audited
tool surface. They do not execute CAD operations directly; instead they provide
portable task framing that Claude Code and other MCP-capable hosts can expose
as reusable commands.
"""
from __future__ import annotations

from typing import NamedTuple


class PromptSpec(NamedTuple):
    description: str


PROMPTS: dict[str, PromptSpec] = {
    "cad_status": PromptSpec(
        description=(
            "Check whether the configured ParamAItric CAD backend is reachable and report "
            "its identity, ParamAItric version, operating mode, capabilities, and workflow count."
        ),
    ),
    "cad_list_workflows": PromptSpec(
        description=(
            "List the validated ParamAItric workflow catalog before choosing a CAD workflow."
        ),
    ),
    "cad_request": PromptSpec(
        description=(
            "Guided replacement-part intake for users new to CAD and 3D printing: understand "
            "the part from a description or reference photo, help them confirm measurements, "
            "convert units, pick the best validated workflow, build it, and hand off the "
            "exported STL with plain-language next steps."
        ),
    ),
}
