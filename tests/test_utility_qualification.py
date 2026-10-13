import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from evaluations import utility_plate, utility_qualification as qualification


@pytest.mark.parametrize("target,match", [(None, None), ("Actual CPU", True), ("Strix target CPU", False)])
def test_headless_success_and_target_match_never_certify_interactive_hardware(tmp_path, monkeypatch, target, match):
    monkeypatch.setattr(qualification, "host_facts", lambda: {"cpu_model": "Actual CPU"})
    async def proof(*args):
        return {"status": "pass"}
    monkeypatch.setattr(qualification, "run", proof)
    monkeypatch.setattr(qualification, "viewer_handoff", lambda *args: {"status": "launched"})
    monkeypatch.setattr(qualification, "fusion_availability", lambda *args: {"status": "available_live", "modeling_evidence": "not_run"})
    report = asyncio.run(qualification.collect(Path(sys.executable), tmp_path, target_cpu=target, endpoint="http://127.0.0.1:8123"))
    assert report["geometry_status"] == "pass"
    assert report["target_cpu_match"] is match
    assert report["qualification_status"] == "incomplete"
    assert report["fusion_geometry_parity"] == "not_run"


def test_failed_geometry_is_not_viewer_or_hardware_evidence(tmp_path, monkeypatch):
    async def fail(*args):
        raise ValueError("actual build failed")
    monkeypatch.setattr(qualification, "run", fail)
    monkeypatch.setattr(qualification, "viewer_handoff", lambda *args: pytest.fail("must not launch without geometry"))
    monkeypatch.setattr(qualification, "fusion_availability", lambda *args: {"status": "unavailable"})
    report = asyncio.run(qualification.collect(Path(sys.executable), tmp_path, target_cpu=None, endpoint="http://127.0.0.1:8123"))
    assert report["geometry_status"] == "fail"
    assert report["qualification_status"] == "incomplete"
    assert report["failure"]["classification"] == "validation_error"


def test_viewer_launch_only_provides_handoff_and_never_marks_ui_checks_passed(monkeypatch):
    def launch(command, **kwargs):
        assert command[1:] == ["viewer", "--host", "127.0.0.1", "--json", "--detach"]
        assert kwargs["timeout"] == 30 and kwargs["env"]["DO_NOT_TRACK"] == "1"
        return SimpleNamespace(returncode=0, stdout='Viewer starting\n{"url": "http://127.0.0.1:3245/"}\n', stderr="")
    monkeypatch.setattr(qualification.subprocess, "run", launch)
    proof = {label: {"artifacts": {"step": f"/tmp/{label} plate.step"}} for label in ("initial", "edited")}
    report = qualification.viewer_handoff(Path(sys.executable), proof)
    assert report["status"] == "launched"
    assert set(report["interactive_checks"].values()) == {"not_run"}
    assert "%20" in report["models"]["initial"]


def test_mock_fusion_health_is_not_live_qualification(monkeypatch):
    monkeypatch.setattr(qualification.BridgeClient, "health", lambda *args: {"ok": True, "mode": "mock", "backend": "autodesk_fusion"})
    result = qualification.fusion_availability("http://127.0.0.1:8123")
    assert result["status"] == "not_live" and result["modeling_evidence"] == "not_run"


def test_fusion_reference_runner_rejects_mock_before_any_mutation(tmp_path, running_bridge, monkeypatch):
    service, url = running_bridge
    from cad_backends.fusion import FusionPlateBackend
    monkeypatch.setattr(FusionPlateBackend, "start_part", lambda *args: pytest.fail("mock must never enter live proof"))
    monkeypatch.setattr(sys, "argv", ["utility_plate", "--backend", "fusion", "--endpoint", url, "--output-root", str(tmp_path)])
    assert utility_plate.main() == 1
    report = json.loads((tmp_path / "smoke.json").read_text())
    assert report["status"] == "fail" and report["bridge_health"]["mode"] == "mock"
    assert report["failure"]["stage"] == "fusion_preflight"
    assert not list(tmp_path.glob("plate-*"))


def test_live_health_alone_never_claims_geometry_parity(monkeypatch):
    monkeypatch.setattr(qualification.BridgeClient, "health", lambda *args: {"ok": True, "mode": "live", "backend": "autodesk_fusion"})
    report = qualification.fusion_availability("http://127.0.0.1:8123")
    assert report["status"] == "available_live" and report["modeling_evidence"] == "not_run"
