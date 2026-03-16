#!/usr/bin/env python3
"""Extract specific workflow from original server.py using AST.

Usage:
    python extract_workflow_fixed.py --workflow counterbored_plate
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def find_method_bounds_ast(source_lines: list[str], method_name: str) -> tuple[int, int] | None:
    """Find the start and end line numbers of a method using AST."""
    source = "\n".join(source_lines)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            # AST uses 1-indexed line numbers
            return (node.lineno - 1, node.end_lineno)  # 0-indexed start, 1-indexed end
    return None


def extract_method(source_lines: list[str], method_name: str) -> str | None:
    """Extract a method's source code with proper handling."""
    bounds = find_method_bounds_ast(source_lines, method_name)
    if bounds is None:
        return None

    start, end = bounds
    # Extract the lines (end is 1-indexed, so we go up to end)
    method_lines = source_lines[start:end]

    # Dedent by removing class-level indentation (4 spaces)
    result_lines = []
    for line in method_lines:
        if line.startswith("    "):
            result_lines.append(line[4:])  # Remove 4-space class indent
        elif line.strip() == "":
            result_lines.append(line)
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


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

    # Try both naming conventions
    workflow_method = f"_create_{args.workflow}_workflow"

    workflow_source = extract_method(source_lines, workflow_method)
    if workflow_source is None:
        print(f"Error: Could not find {workflow_method}")
        return 1

    # Print with header
    print(f"# {workflow_method}")
    print()
    print(workflow_source)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
