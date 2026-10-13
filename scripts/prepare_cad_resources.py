"""Download pinned reference documents and optional CAD wheels, without vendoring.

Run from any directory. Downloads live in the ignored .external-resources cache;
the repository keeps only the upstream/dependency locks and this preparation tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheels", action="store_true", help="Download all pinned wheels for the current Python/platform (requires pip)")
    parser.add_argument("--verify-only", action="store_true", help="Validate the local download manifest without network access")
    args = parser.parse_args()
    cache = ROOT / ".external-resources"
    manifest_path = cache / "manifest.json"
    if args.verify_only:
        manifest = json.loads(manifest_path.read_text())
        for key, path in (("upstreams_lock_sha256", ROOT / "resources/upstreams.lock.json"),
                          ("worker_lock_sha256", ROOT / "cad_backends/cadgen/requirements.lock.txt")):
            if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[key]:
                raise ValueError("resource lock changed; prepare resources again")
        for item in manifest["files"]:
            path = (cache / item["path"]).resolve()
            if not path.is_relative_to(cache.resolve()):
                raise ValueError("invalid manifest path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError(f"changed resource: {item['path']}")
        print(f"Verified {len(manifest['files'])} resources")
        return 0
    lock_path = ROOT / "resources/upstreams.lock.json"
    sources = json.loads(lock_path.read_text())
    files = []
    for source in sources["sources"]:
        repo, commit = source["repository"], source["commit"]
        for filename in source["files"]:
            url = f"https://raw.githubusercontent.com/{repo}/{commit}/{filename}"
            relative = Path("references") / repo.replace("/", "--") / filename
            destination = cache / relative
            request = urllib.request.Request(url, headers={"User-Agent": "ParamAItric-resource-preparation"})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError(f"reference exceeds size limit: {filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            files.append({"path": str(relative), "url": url, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    if args.wheels:
        subprocess.run([sys.executable, "-m", "pip", "--disable-pip-version-check", "download",
                        "--only-binary=:all:", "--dest", str(cache / "wheels"),
                        "-r", str(ROOT / "cad_backends/cadgen/requirements.lock.txt")], check=True)
    for path in sorted((cache / "wheels").glob("*.whl")):
        files.append({"path": str(path.relative_to(cache)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    manifest = {"upstreams_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
                "worker_lock_sha256": hashlib.sha256((ROOT / "cad_backends/cadgen/requirements.lock.txt").read_bytes()).hexdigest(),
                "python": sys.version, "files": files}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {len(files)} resources in {cache}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
