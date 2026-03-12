from __future__ import annotations

import importlib.util
from pathlib import Path


_FUSION_SMOKE_PATH = Path(__file__).with_name("fusion_smoke_test.py")
_FUSION_SMOKE_SPEC = importlib.util.spec_from_file_location("paramaitric_fusion_smoke_test_wrapper", _FUSION_SMOKE_PATH)
assert _FUSION_SMOKE_SPEC is not None
assert _FUSION_SMOKE_SPEC.loader is not None
fusion_smoke_test = importlib.util.module_from_spec(_FUSION_SMOKE_SPEC)
_FUSION_SMOKE_SPEC.loader.exec_module(fusion_smoke_test)


def main() -> int:
    # The drawing-backed 1590EE envelope is explicit; lid cross-section values remain
    # normalized working assumptions until a tighter closure-section spec lands.
    return fusion_smoke_test.main(
        [
            "--workflow",
            "flush_lid_enclosure_pair",
            "--width-cm",
            "20.02",
            "--depth-cm",
            "12.02",
            "--box-height-cm",
            "8.45",
            "--wall-thickness-cm",
            "0.4285",
            "--floor-thickness-cm",
            "0.45",
            "--lid-thickness-cm",
            "0.25",
            "--lip-depth-cm",
            "0.35",
            "--lip-clearance-cm",
            "0.05",
            "--verification-gap-cm",
            "1.5",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
