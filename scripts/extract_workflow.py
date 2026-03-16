#!/usr/bin/env python3
"""Extract specific workflow and its helpers from original server.py.

Usage:
    python scripts/extract_workflow.py --workflow counterbored_plate
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def find_method_bounds(source_lines: list[str], method_name: str) -> tuple[int, int] | None:
    """Find the start and end line numbers of a method."""
    # Find method start
    start_line = None
    for i, line in enumerate(source_lines):
        if re.match(rf"    def {method_name}\(", line):
            start_line = i
            break

    if start_line is None:
        return None

    # Find method end (next method at same or lower indentation, or end of class)
    end_line = len(source_lines)
    for i in range(start_line + 1, len(source_lines)):
        line = source_lines[i]
        # Check for next method at same indentation level (4 spaces + def)
        if re.match(r"    def [^_]|    def __", line):
            end_line = i
            break
        # Check for end of class
        if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
            end_line = i
            break

    return start_line, end_line


def extract_method(source_lines: list[str], method_name: str) -> str | None:
    """Extract a method's source code."""
    bounds = find_method_bounds(source_lines, method_name)
    if bounds is None:
        return None

    start, end = bounds
    # Dedent by 4 spaces (class level indentation)
    lines = source_lines[start:end]
    result_lines = []
    for line in lines:
        if line.startswith("    "):
            result_lines.append(line[4:])  # Remove class-level indent
        elif line.strip() == "":
            result_lines.append(line)
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


def find_called_helpers(method_source: str, all_helpers: set[str]) -> set[str]:
    """Find which helpers are called by a method."""
    called = set()
    for helper in all_helpers:
        if f"self.{helper}(" in method_source:
            called.add(helper)
    return called


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract workflow from original server.py")
    parser.add_argument("--workflow", required=True, help="Workflow name (e.g., counterbored_plate)")
    parser.add_argument("--source", type=Path, default=Path("C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py"))
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Error: Source not found: {args.source}")
        return 1

    source_code = args.source.read_text(encoding="utf-8")
    source_lines = source_code.split("\n")

    # Known helpers in the original server.py
    helpers = {
        "_create_base_plate_body",
        "_run_circle_cut_stage",
        "_run_rectangle_cut_stage",
        "_create_revolved_body",
        "_verify_revolve_body",
        "_verify_shell_result",
        "_select_revolve_profile_by_dimensions",
    }

    workflow_method = f"_create_{args.workflow}_workflow"

    # Extract the main workflow
    workflow_source = extract_method(source_lines, workflow_method)
    if workflow_source is None:
        print(f"Error: Could not find {workflow_method}")
        return 1

    # Find helpers it calls
    called_helpers = find_called_helpers(workflow_source, helpers)

    # Recursively find helpers called by helpers
    all_helpers_needed = set(called_helpers)
    for helper in list(called_helpers):
        helper_source = extract_method(source_lines, helper)
        if helper_source:
            nested_helpers = find_called_helpers(helper_source, helpers)
            all_helpers_needed.update(nested_helpers)

    # Print helpers first (order matters)
    print("# Helper methods:")
    print()
    for helper in sorted(all_helpers_needed):
        helper_source = extract_method(source_lines, helper)
        if helper_source:
            print(helper_source)
            print()

    # Print main workflow
    print(f"# Main workflow method:")
    print()
    print(workflow_source)

    return 0


if __name__ == "__main__":
    sys.exit(main())
