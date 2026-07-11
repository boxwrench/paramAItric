from mcp_server.mcp_entrypoint import cad_request
from mcp_server.prompt_specs import PROMPTS


def test_cad_request_guides_safe_photo_measurement_intake() -> None:
    prompt = cad_request("Replace a broken clip")

    assert "beside a ruler" in prompt
    assert "grid paper" in prompt
    assert "rough estimates" in prompt
    assert "confirm it with a ruler or calipers" in prompt
    assert "only one measurement at a time" in prompt
    assert "live electrical parts" in prompt
    assert "server-side" not in prompt


def test_cad_request_description_mentions_reference_photos_and_confirmation() -> None:
    description = PROMPTS["cad_request"].description

    assert "reference photo" in description
    assert "confirm measurements" in description
