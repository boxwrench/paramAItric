from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import tempfile
import uuid

import pytest

from fusion_addin.http_bridge import HTTPBridgeService


TEST_TEMP_ROOT = Path(__file__).resolve().parent.parent / "tmp_test_runtime"


@pytest.fixture(scope="session", autouse=True)
def _force_repo_local_tempdir() -> Iterator[None]:
    """Keep tempfile-based allowlist checks aligned with pytest's temp root."""
    TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    previous_env = {name: os.environ.get(name) for name in ("TMP", "TEMP", "TMPDIR")}
    previous_tempdir = tempfile.tempdir
    os.environ["TMP"] = str(TEST_TEMP_ROOT)
    os.environ["TEMP"] = str(TEST_TEMP_ROOT)
    os.environ["TMPDIR"] = str(TEST_TEMP_ROOT)
    tempfile.tempdir = str(TEST_TEMP_ROOT)
    try:
        yield
    finally:
        for name, value in previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        tempfile.tempdir = previous_tempdir


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    """Provide a writable repo-local temp directory without pytest tempdir plugin state."""
    TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_TEMP_ROOT / f"case-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def running_bridge(tmp_path) -> Iterator[tuple[HTTPBridgeService, str]]:
    service = HTTPBridgeService(port=0)
    service.start()
    host, port = service.address
    try:
        yield service, f"http://{host}:{port}"
    finally:
        service.stop()
