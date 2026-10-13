from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

from cad_backends.protocol import Measurements
from cad_backends.cadgen import CadgenPlateBackend
from cad_backends.fusion import FusionPlateBackend
from evaluations.utility_plate import compare_measurements
from mcp_server.bridge_client import BridgeClient
from mcp_server.errors import WorkflowFailure
from mcp_server.server import ParamAIToolServer
from mcp_server.utility_plate import CenteredPlate, build_plate, regenerate_plate, verify_plate


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "80"])
def test_invalid_input_is_rejected_before_backend(value):
    with pytest.raises(ValueError):
        CenteredPlate(width_mm=value)


def test_plate_matches_fixture_and_center_is_a_relationship(tmp_path):
    fixture = json.loads(Path("evaluations/cases/plate_centered_hole_success.json").read_text())
    p = CenteredPlate().legacy_payload(tmp_path / "plate.stl")
    for key, value in fixture["arguments"].items():
        if key != "output_path":
            assert p[key] == value
    edited = replace(CenteredPlate(), width_mm=100)
    assert edited.operations()[1].placement.x_cm == 5
    assert edited.operations()[1].target.dimensions_cm["radius"] == 0.5
    with pytest.raises(ValueError):
        CenteredPlate(hole_diameter_mm=60)


def test_fusion_mock_executes_neutral_contract_and_replay(running_bridge, tmp_path):
    _, url = running_bridge
    b = FusionPlateBackend(ParamAIToolServer(BridgeClient(url)), evidence="mock_contract")
    a = build_plate(b, CenteredPlate(), tmp_path, full_geometry=False, formats=("stl",))
    c = regenerate_plate(b, a, {"width_mm": 100}, tmp_path, full_geometry=False, formats=("stl",))
    assert a["measurements"]["width_mm"] == 80
    assert c["measurements"]["width_mm"] == 100
    assert c["previous_revision"] == a["directory"]
    assert a["evidence"] == "mock_contract"
    # No fabricated native-kernel/topology/bore evidence.
    assert "through_hole" not in a["measurements"]
    assert compare_measurements(a["measurements"], a["measurements"])["status"] == "incomplete"
    assert Path(a["artifacts"]["stl"]).exists()
    assert Path(a["directory"], "parameters.json").exists()


def test_unsupported_fusion_proof_fails_before_mutation(running_bridge, tmp_path):
    service, url = running_bridge
    b = FusionPlateBackend(ParamAIToolServer(BridgeClient(url)), evidence="mock_contract")
    with pytest.raises(WorkflowFailure) as error:
        build_plate(b, CenteredPlate(), tmp_path)
    assert error.value.as_dict()["classification"] == "unsupported_capability"
    assert list(tmp_path.iterdir()) == []


def test_failed_readback_blocks_next_mutation_and_export(running_bridge, tmp_path, monkeypatch):
    _, url = running_bridge
    b = FusionPlateBackend(ParamAIToolServer(BridgeClient(url)), evidence="mock_contract")
    calls = []
    monkeypatch.setattr(b, "apply", lambda *args: calls.append("mutation"))
    monkeypatch.setattr(b, "inspect", lambda *args: Measurements({"body_count": 2}, "fault", "synthetic"))
    monkeypatch.setattr(b, "export", lambda *args: calls.append("export"))
    with pytest.raises(WorkflowFailure) as error:
        build_plate(b, CenteredPlate(), tmp_path, full_geometry=False, formats=("stl",))
    assert calls == ["mutation"]
    assert error.value.classification == "verification_failed"
    assert "directory" in error.value.partial_result


def test_nonfinite_readback_never_passes():
    with pytest.raises(WorkflowFailure):
        verify_plate(CenteredPlate(), Measurements({"body_count": 1, "width_mm": float("nan")}, "fault", "unknown"), hole=True, full=True)


def test_worker_output_root_and_symlink_are_rejected(tmp_path):
    import sys
    b = CadgenPlateBackend(Path(sys.executable), tmp_path / "owned")
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError, match="output root"):
        b.start_part(outside, CenteredPlate().parameters())
    b.output_root.mkdir()
    link = b.output_root / "link"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        b.start_part(link, CenteredPlate().parameters())


def test_missing_geometry_is_not_equivalence():
    assert compare_measurements({}, {})["status"] == "incomplete"
    assert compare_measurements({"width_mm": 80}, {"width_mm": 100})["status"] == "mismatch"


def test_real_cadgen_geometry_and_parameter_replay(tmp_path):
    python = os.environ.get("PARAMAITRIC_CAD_PYTHON")
    if not python:
        pytest.skip("Real geometry gate: set PARAMAITRIC_CAD_PYTHON to the pinned dedicated worker environment")
    b = CadgenPlateBackend(Path(python), tmp_path)
    a = build_plate(b, CenteredPlate(), tmp_path)
    c = regenerate_plate(b, a, {"width_mm": 100}, tmp_path)
    for report, width in ((a, 80), (c, 100)):
        f = report["measurements"]
        assert f["width_mm"] == pytest.approx(width, abs=0.01)
        assert f["hole_center_x_mm"] == pytest.approx(width / 2, abs=0.01)
        assert f["hole_center_y_mm"] == pytest.approx(30, abs=0.01)
        assert f["hole_diameter_mm"] == pytest.approx(10, abs=0.01)
        assert f["valid"] and f["through_hole"] and f["body_count"] == 1
        for fmt in ("step", "stl", "recipe", "parameters", "runtime"):
            assert Path(report["artifacts"][fmt]).stat().st_size > 0
        assert json.loads(Path(report["directory"], "mesh-verification.json").read_text())["triangle_count"] > 0
    # Inspections actually parse saved geometry and reject corrupted output.
    from cad_backends.protocol import Part
    part = Part(Path(c["directory"]), revision=2)
    (part.directory / "stage-2.step").write_text("not a STEP file")
    with pytest.raises(WorkflowFailure):
        b.inspect(part)
