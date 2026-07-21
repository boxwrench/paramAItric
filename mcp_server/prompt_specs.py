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


# Maps a full-profile tool identifier referenced in prompt prose to the
# guided-profile facade tool (see mcp_entrypoint.GUIDED_TOOLS) that provides
# the closest capability. Under the "guided" tool_profile only the five
# cad_* facade tools are registered, so prompt text written against the full
# tool surface must be rewritten before it reaches a guided host -- otherwise
# it names tools that do not exist under that profile.
GUIDED_TOOL_NAMES: dict[str, str] = {
    "health": "cad_health",
    "workflow_catalog": "cad_recommend_workflow",
    "recommend_workflow": "cad_recommend_workflow",
    "get_workflow_requirements": "cad_get_requirements",
    "build_workflow": "cad_build",
    "create_*": "cad_build",
    "list_design_bodies": "cad_inspect",
    "get_body_info": "cad_inspect",
    "get_body_faces": "cad_inspect",
    "get_body_edges": "cad_inspect",
    "find_face": "cad_inspect",
}


def tool_name_for_profile(full_profile_name: str, tool_profile: str) -> str:
    """Translate a full-profile tool identifier for the active tool_profile.

    ``full_profile_name`` is the tool identifier a prompt would name under the
    "full" tool_profile (e.g. "health", "recommend_workflow", "create_spacer").
    Under "guided", only cad_health / cad_recommend_workflow /
    cad_get_requirements / cad_build / cad_inspect exist, so any create_*
    workflow name collapses to "cad_build" and read-only inspection
    operations collapse to "cad_inspect". Under "full" the name passes
    through unchanged.
    """
    if tool_profile != "guided":
        return full_profile_name
    if full_profile_name.startswith("create_"):
        return GUIDED_TOOL_NAMES["create_*"]
    return GUIDED_TOOL_NAMES.get(full_profile_name, full_profile_name)


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
