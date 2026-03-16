#!/usr/bin/env python3
"""Insert extracted workflows and helpers into plates.py boilerplate."""
from __future__ import annotations

from pathlib import Path


def indent_code(code: str, indent: str = "    ") -> str:
    """Add indentation to each non-empty line."""
    lines = code.split("\n")
    result = []
    for line in lines:
        if line.strip():
            result.append(indent + line)
        else:
            result.append(line)
    return "\n".join(result)


def read_file(path: Path) -> str:
    with open(path, "r") as f:
        return f.read()


def main():
    plates_path = Path("C:/Github/paramAItric/mcp_server/workflows/plates.py")
    with open(plates_path, "r") as f:
        content = f.read()

    # Build the private implementations section
    implementations = []

    # List of workflows to insert
    workflows = [
        "counterbored_plate",
        "recessed_mount",
        "slotted_mount",
        "cable_gland_plate",
        "rectangular_prism",
        "two_hole_plate",
        "four_hole_mounting_plate",
        "slotted_mounting_plate",
    ]

    for workflow in workflows:
        wf_path = Path(f"C:/tmp/wf_{workflow}.py")
        if wf_path.exists():
            code = read_file(wf_path)
            # Remove comment header if present
            lines = code.split("\n")
            if lines and lines[0].startswith("# _create_"):
                code = "\n".join(lines[1:]).strip()
            implementations.append(code)
            print(f"[OK] Added workflow: {workflow}")
        else:
            print(f"[MISSING] Workflow not found: {workflow}")

    # Join workflows with blank lines
    workflows_section = "\n\n".join(implementations)
    workflows_section = indent_code(workflows_section)

    # Build the helpers section
    helpers = [
        "_create_base_plate_body",
        "_run_circle_cut_stage",
        "_run_rectangle_cut_stage",
        "_verify_body_against_expected_dimensions",
        "_matching_profiles_by_dimensions",
        "_select_profile_by_dimensions",
    ]

    helper_implementations = []
    for helper in helpers:
        helper_path = Path(f"C:/tmp/helper_{helper}.py")
        if helper_path.exists():
            code = read_file(helper_path)
            # Remove comment header
            lines = code.split("\n")
            if lines and lines[0].startswith("# "):
                code = "\n".join(lines[1:]).strip()
            helper_implementations.append(code)
            print(f"[OK] Added helper: {helper}")
        else:
            print(f"[MISSING] Helper not found: {helper}")

    helpers_section = "\n\n".join(helper_implementations)
    helpers_section = indent_code(helpers_section)

    # Find insertion point - between "Private workflow implementations" and "Abstract methods"
    marker_start = "    # -------------------------------------------------------------------------\n    # Private workflow implementations\n    # -------------------------------------------------------------------------"
    marker_end = "\n\n    # -------------------------------------------------------------------------\n    # Abstract methods provided by other mixins"

    if marker_start in content and marker_end in content:
        # Build new content
        idx_start = content.find(marker_start) + len(marker_start)
        idx_end = content.find(marker_end)

        new_content = (
            content[:idx_start] +
            "\n\n" +
            workflows_section +
            "\n\n" +
            "    # -------------------------------------------------------------------------\n    # Shared helper methods\n    # -------------------------------------------------------------------------\n\n" +
            helpers_section +
            content[idx_end:]
        )

        with open(plates_path, "w") as f:
            f.write(new_content)

        print("\n[OK] Successfully updated plates.py")
    else:
        print("\n[ERROR] Could not find insertion markers")
        print(f"  start found: {marker_start in content}")
        print(f"  end found: {marker_end in content}")


if __name__ == "__main__":
    main()
