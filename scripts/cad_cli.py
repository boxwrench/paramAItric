#!/usr/bin/env python3
"""
/cad - ParamAItric CLI Wrapper
==============================

Natural language CAD command interface for ParamAItric.
Maps simple commands to Fusion 360 workflows via HTTP bridge.

Usage:
    python scripts/cad_cli.py create tube mounting plate 4x3 inches with 1.5 inch socket
    python scripts/cad_cli.py run workflow bracket
    python scripts/cad_cli.py list workflows

Or create a shell alias for cleaner usage:
    alias /cad='python C:/Github/paramAItric/scripts/cad_cli.py'
    /cad create tube mounting plate...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_BRIDGE_URL = os.environ.get("PARAMAITRIC_BRIDGE_URL", "http://127.0.0.1:8123")


WORKFLOW_CATALOG = {
    "spacer": {
        "patterns": ["spacer", "rectangular plate", "flat plate"],
        "description": "Simple rectangular extrusion",
        "default_params": {"width": 10.0, "height": 5.0, "thickness": 0.5},
    },
    "tube_mounting_plate": {
        "patterns": ["tube mounting", "mounting plate with socket", "tube socket"],
        "description": "Mounting plate with cylindrical tube socket",
        "default_params": {
            "base_width": 10.0,
            "base_height": 8.0,
            "base_thickness": 0.6,
            "socket_diameter": 4.0,
            "socket_height": 3.0,
            "hole_diameter": 0.6,
        },
    },
    "bracket": {
        "patterns": ["bracket", "l-bracket", "l bracket", "corner bracket"],
        "description": "L-shaped structural bracket",
        "default_params": {"leg1": 5.0, "leg2": 5.0, "thickness": 0.5, "width": 3.0},
    },
    "filleted_bracket": {
        "patterns": ["filleted bracket", "rounded bracket", "bracket with fillet"],
        "description": "L-bracket with rounded interior corners",
        "default_params": {"leg1": 5.0, "leg2": 5.0, "thickness": 0.5, "width": 3.0, "fillet_radius": 0.3},
    },
    "cylinder": {
        "patterns": ["cylinder", "rod", "pin"],
        "description": "Simple cylindrical solid",
        "default_params": {"diameter": 3.0, "height": 5.0},
    },
    "tube": {
        "patterns": ["tube", "pipe", "hollow cylinder", "sleeve"],
        "description": "Hollow cylindrical tube",
        "default_params": {"outer_diameter": 4.0, "inner_diameter": 3.0, "height": 5.0},
    },
    "plate_with_hole": {
        "patterns": ["plate with hole", "mounting plate", "drilled plate"],
        "description": "Flat plate with through-holes",
        "default_params": {"width": 8.0, "height": 6.0, "thickness": 0.5, "hole_diameter": 0.6, "hole_count": 2},
    },
    "simple_enclosure": {
        "patterns": ["enclosure", "box", "case", "project box"],
        "description": "Hollow shelled enclosure",
        "default_params": {"width": 10.0, "height": 8.0, "depth": 4.0, "wall_thickness": 0.3},
    },
    "project_box_with_standoffs": {
        "patterns": ["project box with standoffs", "pcb enclosure", "box with mounts"],
        "description": "Shelled enclosure with PCB mounting standoffs",
        "default_params": {"width": 12.0, "height": 8.0, "depth": 4.0, "wall_thickness": 0.3, "standoff_diameter": 0.8, "standoff_height": 1.0},
    },
    "box_with_lid": {
        "patterns": ["box with lid", "container with lid", "box and lid"],
        "description": "Matched box and lid as separate bodies",
        "default_params": {"width": 10.0, "height": 8.0, "depth": 4.0, "wall_thickness": 0.3, "lid_height": 1.0},
    },
}


class CADCommander:
    """CLI interface to ParamAItric Fusion bridge."""

    def __init__(self, base_url: str = DEFAULT_BRIDGE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.output_dir = Path("manual_test_output")
        self.output_dir.mkdir(exist_ok=True)

    def _send_command(self, command: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send command to Fusion bridge."""
        payload = json.dumps({"command": command, "arguments": arguments}).encode()
        req = request.Request(
            f"{self.base_url}/command",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode())
        except error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(f"Command failed: {e.code} - {body}") from e
        except error.URLError as e:
            raise RuntimeError(
                f"Cannot connect to Fusion bridge at {self.base_url}\n"
                "Make sure Fusion 360 is running with the ParamAItric add-in started."
            ) from e

    def parse_natural_language(self, command_str: str) -> tuple[str, dict[str, Any]]:
        """Parse natural language command into workflow and parameters."""
        command_lower = command_str.lower()
        dimensions = self._extract_dimensions(command_lower)
        workflow_name = self._match_workflow(command_lower)

        if not workflow_name:
            raise ValueError(
                f"Could not determine workflow from: '{command_str}'\n"
                "Try: /cad create [workflow] or /cad list workflows"
            )

        params = {**WORKFLOW_CATALOG[workflow_name]["default_params"], **dimensions}

        if "inch" in command_lower or '"' in command_str:
            params["units"] = "inches"
        else:
            params["units"] = "cm"

        return workflow_name, params

    def _extract_dimensions(self, text: str) -> dict[str, float]:
        """Extract dimension values from text."""
        dims: dict[str, float] = {}
        dim_pattern = r'(\d+(?:\.\d+)?)\s*(?:x|by)\s*(\d+(?:\.\d+)?)'
        matches = list(re.finditer(dim_pattern, text.lower()))
        if matches:
            dims["width"] = float(matches[0].group(1))
            dims["height"] = float(matches[0].group(2))

        dia_pattern = r'(\d+(?:\.\d+)?)\s*(?:inch|in|"|\s*")(?:\s*diameter|\s*socket|\s*hole|\s*pipe)?'
        dia_match = re.search(dia_pattern, text.lower())
        if dia_match:
            dims["socket_diameter"] = float(dia_match.group(1))
            dims["diameter"] = float(dia_match.group(1))

        thick_pattern = r'(?:thick(?:ness)?|height)\s*(?:of\s*)?(\d+(?:\.\d+)?)'
        thick_match = re.search(thick_pattern, text.lower())
        if thick_match:
            dims["thickness"] = float(thick_match.group(1))
            dims["base_thickness"] = float(thick_match.group(1))

        return dims

    def _match_workflow(self, text: str) -> str | None:
        """Match text to workflow name."""
        for workflow_name, config in WORKFLOW_CATALOG.items():
            for pattern in config["patterns"]:
                if pattern in text:
                    return workflow_name
        return None

    def execute(self, command_str: str, dry_run: bool = False) -> dict[str, Any]:
        """Execute parsed command."""
        workflow_name, params = self.parse_natural_language(command_str)

        print(f"Workflow: {workflow_name}")
        print(f"Description: {WORKFLOW_CATALOG[workflow_name]['description']}")
        print(f"Parameters: {json.dumps(params, indent=2)}")

        if dry_run:
            return {"dry_run": True, "workflow": workflow_name, "params": params}

        print("\nSending to Fusion...")
        result = self._send_command(
            "run_workflow",
            {
                "workflow_name": workflow_name,
                "parameters": params,
            },
        )

        if result.get("ok"):
            print("[ok] Workflow completed successfully")
            exports = result.get("result", {}).get("exports", [])
            if exports:
                print("\nExported files:")
                for export in exports:
                    print(f"  - {export.get('path', 'unknown')}")
        else:
            print(f"[error] Workflow failed: {result.get('error', 'Unknown error')}")

        return result

    def list_workflows(self) -> None:
        """List available workflows."""
        print("\nAvailable CAD Workflows:")
        print("-" * 60)
        for name, config in WORKFLOW_CATALOG.items():
            print(f"\n{name}")
            print(f"  {config['description']}")
            print(f"  Triggers: {', '.join(config['patterns'][:3])}")
        print()

    def check_status(self) -> bool:
        """Check if Fusion bridge is running."""
        try:
            req = request.Request(f"{self.base_url}/health", method="GET")
            with request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                print(f"[ok] Fusion bridge connected: {data}")
                return True
        except Exception as e:
            print(f"[error] Cannot connect to Fusion bridge: {e}")
            print("\nMake sure:")
            print("  1. Fusion 360 is running")
            print("  2. ParamAItric add-in is started (Utilities -> Scripts and Add-Ins)")
            return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ParamAItric /cad CLI - Natural language CAD commands",
        usage="%(prog)s [command] [options]",
    )
    parser.add_argument(
        "command",
        nargs="*",
        help="Natural language command (e.g., 'create tube mounting plate 4x3 inches')",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_BRIDGE_URL,
        help=f"Fusion bridge URL (default: {DEFAULT_BRIDGE_URL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse command but don't execute",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available workflows",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check Fusion bridge connection status",
    )

    args = parser.parse_args()
    commander = CADCommander(base_url=args.url)

    if args.status:
        return 0 if commander.check_status() else 1

    if args.list:
        commander.list_workflows()
        return 0

    if not args.command:
        parser.print_help()
        return 1

    command_str = " ".join(args.command)

    try:
        result = commander.execute(command_str, dry_run=args.dry_run)
        return 0 if result.get("ok") or args.dry_run else 1
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
