"""Valve specification extractor for CAD parameter generation.

This module helps extract CAD-relevant dimensions from valve manufacturer
documentation (PDFs, web pages, datasheets) and converts them to the
standard spec format for valve handle generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class ValveStemSpec:
    """Extracted valve stem specifications for CAD modeling."""

    shape: str  # square, hex, round_flat, double_d
    across_flats_cm: float | None = None  # For square/hex
    diameter_cm: float | None = None  # For round stems
    depth_cm: float = 2.0  # Default engagement depth
    tolerance_cm: float = 0.05  # Default print clearance

    # Set screw details
    set_screw_diameter_cm: float | None = None
    set_screw_thread: str | None = None

    def to_cad_params(self) -> dict:
        """Convert to parameters for create_valve_handle workflow."""
        if self.shape in ("square", "hex") and self.across_flats_cm:
            return {
                "stem_width_cm": self.across_flats_cm,
                "stem_depth_cm": self.depth_cm,
                "socket_type": self.shape,
                "clearance_cm": self.tolerance_cm,
                "set_screw_diameter_cm": self.set_screw_diameter_cm,
            }
        elif self.shape == "round_flat" and self.diameter_cm:
            return {
                "stem_width_cm": self.diameter_cm,
                "stem_depth_cm": self.depth_cm,
                "socket_type": "round_flat",
                "clearance_cm": self.tolerance_cm,
                "set_screw_diameter_cm": self.set_screw_diameter_cm,
            }
        raise ValueError(f"Invalid spec: shape={self.shape}, flats={self.across_flats_cm}, dia={self.diameter_cm}")


class DimensionExtractor:
    """Extract dimensions from text snippets (PDFs, web pages, etc.)."""

    # Common patterns for valve stem dimensions
    PATTERNS = {
        "square_stem": [
            re.compile(r"(\d+(?:\.\d+)?)\s*""\s*(?:square|sq\.?)\s*(?:stem|operating nut)", re.IGNORECASE),
            re.compile(r"square\s*(?:stem|nut)?\s*:?\s*(\d+(?:\.\d+)?)\s*""", re.IGNORECASE),
            re.compile(r"(\d+/\d+)\s*""\s*(?:square|sq\.?)\s*(?:stem|nut)", re.IGNORECASE),
        ],
        "hex_stem": [
            re.compile(r"(\d+(?:\.\d+)?)\s*""\s*hex\s*(?:stem|socket)", re.IGNORECASE),
            re.compile(r"across flats\s*:?\s*(\d+(?:\.\d+)?)\s*""", re.IGNORECASE),
        ],
        "stem_depth": [
            re.compile(r"stem\s*(?:engagement|depth)\s*:?\s*(\d+(?:\.\d+)?)\s*""", re.IGNORECASE),
            re.compile(r"(?:engagement|socket)\s*depth\s*:?\s*(\d+(?:\.\d+)?)\s*""", re.IGNORECASE),
        ],
        "set_screw": [
            re.compile(r"set\s*screw\s*:?\s*(M?\d+(?:\.\d+)?[-x]?\d*)", re.IGNORECASE),
            re.compile(r"(#?\d+-\d+)\s*(?:set|socket)\s*screw", re.IGNORECASE),
        ],
    }

    @classmethod
    def extract_from_text(cls, text: str) -> ValveStemSpec | None:
        """Extract valve stem spec from text content.

        Args:
            text: Text content from PDF, webpage, or datasheet.

        Returns:
            ValveStemSpec if dimensions found, None otherwise.
        """
        spec = ValveStemSpec(shape="square")  # Default assumption

        # Try to find square stem dimension
        for pattern in cls.PATTERNS["square_stem"]:
            match = pattern.search(text)
            if match:
                dim_str = match.group(1)
                spec.across_flats_cm = cls._parse_dimension(dim_str)
                break

        # Try to find hex stem (overrides square if found)
        for pattern in cls.PATTERNS["hex_stem"]:
            match = pattern.search(text)
            if match:
                dim_str = match.group(1)
                spec.shape = "hex"
                spec.across_flats_cm = cls._parse_dimension(dim_str)
                break

        # Try to find stem depth
        for pattern in cls.PATTERNS["stem_depth"]:
            match = pattern.search(text)
            if match:
                dim_str = match.group(1)
                spec.depth_cm = cls._parse_dimension(dim_str)
                break

        # Try to find set screw
        for pattern in cls.PATTERNS["set_screw"]:
            match = pattern.search(text)
            if match:
                thread_str = match.group(1)
                spec.set_screw_thread = thread_str
                spec.set_screw_diameter_cm = cls._estimate_screw_diameter(thread_str)
                break

        # Return None if no dimensions found
        if spec.across_flats_cm is None:
            return None

        return spec

    @staticmethod
    def _parse_dimension(dim_str: str) -> float:
        """Parse dimension string to centimeters.

        Handles: 0.5, 1/2, 12.7mm, 1/2", etc.
        """
        dim_str = dim_str.strip()

        # Check for fraction like "1/2"
        if "/" in dim_str and "mm" not in dim_str and '"' not in dim_str:
            try:
                num, denom = dim_str.split("/")
                return float(num) / float(denom) * 2.54  # inches to cm
            except (ValueError, ZeroDivisionError):
                pass

        # Check for explicit inches with quote
        if '"' in dim_str:
            try:
                num = dim_str.replace('"', '').replace("in", "").strip()
                if "/" in num:
                    n, d = num.split("/")
                    return float(n) / float(d) * 2.54
                return float(num) * 2.54
            except ValueError:
                pass

        # Check for mm
        if "mm" in dim_str.lower():
            try:
                num = dim_str.lower().replace("mm", "").strip()
                return float(num) / 10.0  # mm to cm
            except ValueError:
                pass

        # Plain number - assume inches for valve specs (industry standard)
        try:
            return float(dim_str) * 2.54
        except ValueError:
            return 0.0

    @staticmethod
    def _estimate_screw_diameter(thread_str: str) -> float:
        """Estimate set screw diameter from thread designation."""
        thread_str = thread_str.upper()

        # Metric: M4, M5, M6, M8
        if thread_str.startswith("M"):
            try:
                diameter_mm = float(thread_str[1:].split("-")[0].split("X")[0])
                return diameter_mm / 10.0  # mm to cm
            except ValueError:
                pass

        # Imperial: #8-32, 1/4-20, etc.
        if thread_str.startswith("#"):
            # Machine screw sizes approx
            size_map = {"#4": 0.28, "#6": 0.34, "#8": 0.42, "#10": 0.48}
            for size, dia_in in size_map.items():
                if size in thread_str:
                    return dia_in * 2.54

        # Fraction like 1/4-20
        if "/" in thread_str:
            try:
                frac = thread_str.split("-")[0].strip()
                num, denom = frac.split("/")
                return (float(num) / float(denom)) * 2.54
            except (ValueError, ZeroDivisionError):
                pass

        return 0.4  # Default to ~M4 size


def extract_from_pdf(pdf_path: str | Path) -> ValveStemSpec | None:
    """Extract valve stem spec from PDF file.

    Note: This is a placeholder - actual PDF text extraction would
    require PyPDF2, pdfplumber, or similar library.
    """
    # TODO: Implement actual PDF text extraction if needed
    # For now, direct user to paste relevant text section
    raise NotImplementedError(
        "PDF extraction requires additional dependencies. "
        "Please paste the relevant specification text directly."
    )


def main():
    """CLI for testing extraction from pasted text."""
    import sys

    print("Valve Spec Extractor")
    print("=" * 50)
    print("Paste specification text (Ctrl+D or Ctrl+Z when done):")

    text = sys.stdin.read()

    spec = DimensionExtractor.extract_from_text(text)

    if spec:
        print("\n--- Extracted Specifications ---")
        print(f"Shape: {spec.shape}")
        print(f"Across Flats: {spec.across_flats_cm:.2f} cm")
        print(f"Stem Depth: {spec.depth_cm:.2f} cm")
        print(f"Set Screw: {spec.set_screw_thread or 'None'}")
        print(f"\n--- CAD Parameters ---")
        for key, value in spec.to_cad_params().items():
            print(f"  {key}: {value}")
    else:
        print("\nNo valve stem dimensions found in text.")
        print("Look for patterns like:")
        print('  - "1/2" square stem"')
        print('  - "12.7mm across flats"')
        print('  - "3/8 hex operating nut"')


if __name__ == "__main__":
    main()
