#!/usr/bin/env python3
"""Fix plates.py by removing duplicate methods."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def remove_duplicate_methods(content: str) -> str:
    """Remove duplicate method definitions, keeping only the first occurrence."""
    lines = content.split("\n")
    seen_methods = set()
    result = []
    skip_until_next_method = False
    current_method = None

    for line in lines:
        # Check if this is a method definition
        match = re.match(r"^(    def|def) (\w+)\(", line)
        if match:
            method_name = match.group(2)
            if method_name in seen_methods:
                skip_until_next_method = True
                current_method = method_name
            else:
                seen_methods.add(method_name)
                skip_until_next_method = False
                current_method = None
            result.append(line)
        elif skip_until_next_method:
            # Check if we've reached the next method at class level
            if re.match(r"^(    def|def) \w+\(", line):
                skip_until_next_method = False
                result.append(line)
            # Otherwise skip this line
        else:
            result.append(line)

    return "\n".join(result)


def main() -> int:
    plates_path = Path("C:/Github/paramAItric/mcp_server/workflows/plates.py")
    if not plates_path.exists():
        print(f"Error: {plates_path} not found")
        return 1

    content = plates_path.read_text(encoding="utf-8")
    fixed = remove_duplicate_methods(content)
    plates_path.write_text(fixed, encoding="utf-8")

    print(f"Fixed {plates_path}")
    print(f"Original size: {len(content)} chars")
    print(f"Fixed size: {len(fixed)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
