#!/usr/bin/env python3
"""Insert extracted workflow methods into mixin files.

Usage:
    python scripts/insert_workflows.py --mixin plates --workflow counterbored_plate
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Insert workflow into mixin")
    parser.add_argument("--mixin", required=True, choices=["plates", "cylinders", "brackets", "enclosures"])
    parser.add_argument("--workflow", required=True, help="Workflow name (e.g., counterbored_plate)")
    parser.add_argument("--source", type=Path, default=Path("C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py"))
    args = parser.parse_args()

    mixin_file = Path(f"C:/Github/paramAItric/mcp_server/workflows/{args.mixin}.py")
    if not mixin_file.exists():
        print(f"Error: Mixin file not found: {mixin_file}")
        return 1

    # Read current mixin content
    mixin_content = mixin_file.read_text(encoding="utf-8")
    lines = mixin_content.split("\n")

    # Find the abstract methods section
    abstract_line = None
    for i, line in enumerate(lines):
        if "Abstract methods provided by other mixins" in line:
            abstract_line = i
            break

    if abstract_line is None:
        print("Error: Could not find abstract methods section")
        return 1

    # Run extraction script
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/extract_workflow.py", "--workflow", args.workflow],
        capture_output=True,
        text=True,
        cwd="C:/Github/paramAItric",
    )

    if result.returncode != 0:
        print(f"Error extracting workflow: {result.stderr}")
        return 1

    extracted = result.stdout

    # Parse extracted content and skip duplicates
    extracted_lines = extracted.split("\n")
    new_methods = []
    skip_methods = set()

    # Find which methods already exist in the mixin
    for line in lines[:abstract_line]:
        if line.strip().startswith("def _"):
            method_name = line.split("(")[0].replace("def ", "").strip()
            skip_methods.add(method_name)

    # Filter out duplicate methods from extracted content
    current_method = None
    for line in extracted_lines:
        if line.startswith("def "):
            current_method = line.split("(")[0].replace("def ", "").strip()
            if current_method in skip_methods:
                current_method = None  # Skip this entire method
        if current_method is not None:
            new_methods.append(line)

    # Insert before abstract methods section
    new_lines = lines[:abstract_line] + [""] + new_methods + [""] + lines[abstract_line:]

    # Write back
    mixin_file.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"Inserted {args.workflow} into {mixin_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
