from __future__ import annotations

from fusion_addin.bootstrap import MockBootstrapResult, bootstrap_addin


def test_bootstrap_falls_back_to_mock_without_fusion() -> None:
    result = bootstrap_addin()

    assert isinstance(result, MockBootstrapResult)
    assert result.mode == "mock"
