#!/usr/bin/env python3
"""Extract helper methods from original server.py using AST.

Usage:
    python extract_helpers.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def extract_method(source_lines: list[str], method_name: str) -> str | None:
    """Extract a method's source code."""
    source = "\n".join(source_lines)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            start = node.lineno - 1  # 0-indexed
            end = node.end_lineno     # 1-indexed (exclusive)
            method_lines = source_lines[start:end]

            # Dedent by removing class-level indentation (4 spaces)
            result_lines = []
            for line in method_lines:
                if line.startswith("    "):
                    result_lines.append(line[4:])
                elif line.strip() == "":
                    result_lines.append(line)
                else:
                    result_lines.append(line)
            return "\n".join(result_lines)
    return None


def main() -> int:
    source_path = Path("C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py")
    if not source_path.exists():
        print(f"Error: Source not found: {source_path}")
        return 1

    source_code = source_path.read_text(encoding="utf-8")
    source_lines = source_code.split("\n")

    # List of helpers to extract
    helpers = [
        "_create_base_plate_body",
        "_run_circle_cut_stage",
        "_run_rectangle_cut_stage",
        "_verify_body_against_expected_dimensions",
        "_matching_profiles_by_dimensions",
        "_select_profile_by_dimensions",
    ]

    for helper in helpers:
        helper_source = extract_method(source_lines, helper)
        if helper_source:
            output_path = Path(f"C:/tmp/helper_{helper}.py")
            with open(output_path, "w") as f:
                f.write(f"# {helper}\n\n")
                f.write(helper_source)
            print(f"[OK] Extracted {helper} ({len(helper_source.split(chr(10)))} lines)")
        else:
            print(f"[MISSING] Could not find {helper}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
