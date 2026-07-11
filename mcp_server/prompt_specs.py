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
            "Check whether the ParamAItric Fusion bridge is reachable and report "
            "its current operating mode."
        ),
    ),
    "cad_list_workflows": PromptSpec(
        description=(
            "List the validated ParamAItric workflow catalog before choosing a CAD workflow."
        ),
    ),
    "cad_request": PromptSpec(
        description=(
            "Interpret a user CAD request using the ParamAItric MCP tools. Start with health, "
            "map the request to the best validated workflow, then create or inspect as needed."
        ),
    ),
}
