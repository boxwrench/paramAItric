#!/usr/bin/env python3
"""Verify migration integrity after moving workflows to mixins.

Usage:
    python scripts/verify_migration.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def get_methods_from_file(path: Path) -> set[str]:
    """Extract all method names from a Python file."""
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {path}: {e}")
        return set()

    methods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            methods.add(node.name)
    return methods


def check_all_workflows_accounted_for() -> bool:
    """Ensure every create_* method from original server.py exists in mixins."""
    print("\n=== Checking all workflows accounted for ===")

    original = Path("C:/Users/wests/.gemini/tmp/paramaitric_freeform/mcp_server/server.py")
    if not original.exists():
        print(f"WARNING: Original server.py not found at {original}")
        return False

    original_methods = get_methods_from_file(original)
    original_workflows = {m for m in original_methods if m.startswith("create_") and not m.startswith("_")}

    # Check current server.py
    current = Path("C:/Github/paramAItric/mcp_server/server.py")
    current_methods = get_methods_from_file(current)

    mixin_files = [
        Path("C:/Github/paramAItric/mcp_server/workflows/plates.py"),
        Path("C:/Github/paramAItric/mcp_server/workflows/cylinders.py"),
        Path("C:/Github/paramAItric/mcp_server/workflows/brackets.py"),
        Path("C:/Github/paramAItric/mcp_server/workflows/enclosures.py"),
        Path("C:/Github/paramAItric/mcp_server/workflows/specialty.py"),
    ]

    mixin_methods = set()
    for mixin_file in mixin_files:
        if mixin_file.exists():
            mixin_methods.update(get_methods_from_file(mixin_file))

    all_available = current_methods.union(mixin_methods)

    missing = original_workflows - all_available
    if missing:
        print(f"FAIL: {len(missing)} workflows from original not found:")
        for w in sorted(missing):
            print(f"  - {w}")
        return False

    print(f"PASS: All {len(original_workflows)} workflows accounted for")
    return True


def check_no_duplicate_methods() -> bool:
    """Ensure no method defined in multiple mixins."""
    print("\n=== Checking for duplicate methods ===")

    mixin_files = {
        "plates": Path("C:/Github/paramAItric/mcp_server/workflows/plates.py"),
        "cylinders": Path("C:/Github/paramAItric/mcp_server/workflows/cylinders.py"),
        "brackets": Path("C:/Github/paramAItric/mcp_server/workflows/brackets.py"),
        "enclosures": Path("C:/Github/paramAItric/mcp_server/workflows/enclosures.py"),
        "specialty": Path("C:/Github/paramAItric/mcp_server/workflows/specialty.py"),
    }

    all_methods: dict[str, list[str]] = {}
    for name, path in mixin_files.items():
        if not path.exists():
            continue
        methods = get_methods_from_file(path)
        for method in methods:
            if method not in all_methods:
                all_methods[method] = []
            all_methods[method].append(name)

    duplicates = {m: files for m, files in all_methods.items() if len(files) > 1}

    # Filter out legitimate duplicates (abstract method declarations)
    ignore_list = {"_bridge_step", "new_design", "get_scene_info", "create_sketch",
                   "draw_rectangle", "draw_circle", "list_profiles", "extrude_profile",
                   "export_stl", "draw_slot", "find_face", "draw_rectangle_at",
                   "apply_fillet", "apply_chamfer", "apply_shell", "combine_bodies",
                   "draw_l_bracket_profile", "revolve_profile"}

    real_duplicates = {m: files for m, files in duplicates.items() if m not in ignore_list}

    if real_duplicates:
        print(f"FAIL: {len(real_duplicates)} methods defined in multiple mixins:")
        for method, files in sorted(real_duplicates.items()):
            print(f"  - {method}: {', '.join(files)}")
        return False

    print("PASS: No duplicate method definitions")
    return True


def check_imports_complete() -> bool:
    """Ensure all mixin imports resolve."""
    print("\n=== Checking imports ===")

    try:
        from mcp_server.workflows.plates import PlateWorkflowsMixin
        from mcp_server.workflows.cylinders import CylinderWorkflowsMixin
        from mcp_server.workflows.brackets import BracketWorkflowsMixin
        from mcp_server.workflows.enclosures import EnclosureWorkflowsMixin
        from mcp_server.workflows.specialty import SpecialtyWorkflowsMixin
        print("PASS: All mixin imports resolve")
        return True
    except ImportError as e:
        print(f"FAIL: Import error: {e}")
        return False


def check_syntax_valid() -> bool:
    """Ensure all mixin files have valid syntax."""
    print("\n=== Checking syntax ===")

    mixin_files = [
        Path("C:/Github/paramAItric/mcp_server/workflows/plates.py"),
        Path("C:/Github/paramAItric/mcp_server/workflows/cylinders.py"),
        Path("C:/Github/paramAItric/mcp_server/workflows/brackets.py"),
        Path("C:/Github/paramAItric/mcp_server/workflows/enclosures.py"),
        Path("C:/Github/paramAItric/mcp_server/workflows/specialty.py"),
    ]

    all_valid = True
    for path in mixin_files:
        if not path.exists():
            print(f"SKIP: {path.name} does not exist")
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
            print(f"  [OK] {path.name}")
        except SyntaxError as e:
            print(f"  [ERROR] {path.name}: {e}")
            all_valid = False

    if all_valid:
        print("PASS: All files have valid syntax")
    return all_valid


def main() -> int:
    print("=" * 60)
    print("MIGRATION VERIFICATION")
    print("=" * 60)

    checks = [
        ("Syntax", check_syntax_valid),
        ("Imports", check_imports_complete),
        ("Duplicates", check_no_duplicate_methods),
        ("Workflows", check_all_workflows_accounted_for),
    ]

    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"ERROR in {name} check: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
        if not result:
            all_passed = False

    if all_passed:
        print("\n[OK] All checks passed!")
        return 0
    else:
        print("\n[ERROR] Some checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
