"""Download or verify the release-pinned SolidCraft experiment, without system installation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root: Path, *, verify_only=False, include_web=False):
    lock = json.loads((ROOT / "resources/solidcraft.lock.json").read_text())
    items = lock["files"] + ([lock["optional_web"]] if include_web else [])
    for item in items:
        path = root / item["path"]
        if not path.is_file() and not verify_only:
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_suffix(path.suffix + ".partial")
            try:
                request = urllib.request.Request(item["url"], headers={"User-Agent": "ParamAItric-evaluation"})
                with urllib.request.urlopen(request, timeout=90) as response, partial.open("wb") as out:
                    while chunk := response.read(1024 * 1024):
                        out.write(chunk)
                        if out.tell() > 64 * 1024**2:
                            raise ValueError("Resource exceeds the 64 MiB download bound")
                if sha256(partial) != item["sha256"]:
                    raise ValueError(f"Checksum mismatch: {item['path']}")
                partial.replace(path)
            finally:
                partial.unlink(missing_ok=True)
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise ValueError(f"Missing or modified resource: {item['path']}")
    cli = root / lock["cli_path"]
    if not cli.exists() and not verify_only:
        with tarfile.open(root / lock["archive"]) as archive:
            archive.extractall(root / lock["extract_to"], filter="data")
    if not cli.is_file() or sha256(cli) != lock["cli_sha256"]:
        raise ValueError("Extracted CLI missing or modified")
    if include_web:
        web = root / lock["optional_web"]["extract_to"]
        with zipfile.ZipFile(root / lock["optional_web"]["path"]) as archive:
            for name in archive.namelist():
                if not (web / name).resolve().is_relative_to(web.resolve()):
                    raise ValueError("Web archive contains an escaping path")
            if not verify_only:
                archive.extractall(web)
            for info in archive.infolist():
                if not info.is_dir() and (not (web / info.filename).is_file() or sha256(web / info.filename) != hashlib.sha256(archive.read(info)).hexdigest()):
                    raise ValueError("Extracted web asset missing or modified")
    return {"release": lock["release"], "source_commit": lock["source_commit"], "verified_downloads": len(items),
            "solidcraft_cli": str(cli.absolute()), "cli_sha256": lock["cli_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".external-resources/solidcraft")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--include-web", action="store_true", help="Also acquire/verify the optional official browser UI bundle")
    args = parser.parse_args()
    print(json.dumps(prepare(args.root, verify_only=args.verify_only, include_web=args.include_web)))


if __name__ == "__main__":
    main()
