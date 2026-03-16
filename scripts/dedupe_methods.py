#!/usr/bin/env python3
"""Remove duplicate method definitions from Python file, keeping first occurrence."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def dedupe_methods(content: str) -> str:
    """Remove duplicate method definitions."""
    lines = content.split("\n")
    seen_methods = set()
    result = []
    skipping = False
    indent_level = None

    for i, line in enumerate(lines):
        # Check for method definition at class level (4 spaces + def)
        match = re.match(r"^(    def |def )(\w+)\(", line)
        if match:
            prefix, method_name = match.groups()
            if method_name in seen_methods:
                skipping = True
                indent_level = len(prefix)
                continue  # Skip this line
            else:
                seen_methods.add(method_name)
                skipping = False
                indent_level = None

        if skipping:
            # Check if we've exited the method (line with same or lower indent)
            if line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                # Hit class/function end or new top-level definition
                skipping = False
                indent_level = None
                result.append(line)
            elif line.startswith("    ") and len(line) - len(line.lstrip()) <= indent_level:
                # Hit next method at same or lower indentation
                skipping = False
                indent_level = None
                result.append(line)
            # Otherwise skip this line (it's part of the duplicate method)
        else:
            result.append(line)

    return "\n".join(result)


def main() -> int:
    plates_path = Path("C:/Github/paramAItric/mcp_server/workflows/plates.py")
    if not plates_path.exists():
        print(f"Error: {plates_path} not found")
        return 1

    content = plates_path.read_text(encoding="utf-8")
    fixed = dedupe_methods(content)

    # Also fix indentation - ensure class methods have proper 4-space indent
    lines = fixed.split("\n")
    fixed_lines = []
    in_class = False

    for line in lines:
        # Detect class definition
        if line.startswith("class "):
            in_class = True
            fixed_lines.append(line)
        # Detect end of class (top-level definition or empty line followed by top-level)
        elif in_class and line and not line.startswith(" ") and not line.startswith("\t") and not line.startswith("#"):
            in_class = False
            fixed_lines.append(line)
        # Fix method definitions that are at wrong indentation
        elif in_class and re.match(r"^def [^_]|^def __", line):
            # This is a public method that should be indented
            fixed_lines.append("    " + line)
        elif in_class and re.match(r"^def _", line):
            # Private method
            fixed_lines.append("    " + line)
        else:
            fixed_lines.append(line)

    final_content = "\n".join(fixed_lines)
    plates_path.write_text(final_content, encoding="utf-8")

    print(f"Fixed {plates_path}")
    print(f"Original lines: {len(content.split(chr(10)))}")
    print(f"Final lines: {len(final_content.split(chr(10)))}")

    # Verify no duplicates remain
    methods = re.findall(r"^    def (\w+)\(", final_content, re.MULTILINE)
    duplicates = [m for m in set(methods) if methods.count(m) > 1]
    if duplicates:
        print(f"Warning: Still have duplicates: {duplicates}")
    else:
        print("No duplicates found!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
