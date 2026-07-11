"""Default availability policy for high-level workflows.

Experimental workflow implementations may remain in the source tree, but a
workflow listed here is excluded from both the default Fusion catalog and the
default MCP tool surface until its implementation is ready.
"""
from __future__ import annotations


EXPERIMENTAL_WORKFLOWS: frozenset[str] = frozenset(
    {
        "flush_lid_enclosure_pair",
        "slotted_flex_panel",
        "snap_fit_enclosure",
        "telescoping_containers",
    }
)


def is_available_by_default(workflow_name: str) -> bool:
    """Return whether a workflow belongs on default public surfaces."""
    return workflow_name not in EXPERIMENTAL_WORKFLOWS
