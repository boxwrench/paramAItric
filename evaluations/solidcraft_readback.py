"""Compatibility entry point for the shared independent SolidCraft reader."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "cad_backends/solidcraft/readback.py"), run_name="__main__")
else:
    from cad_backends.solidcraft.readback import read, read_mesh, verify
