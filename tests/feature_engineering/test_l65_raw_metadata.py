from __future__ import annotations

from types import SimpleNamespace

from momentum.FeatureEngineering.feature_factory import FeatureFactory


def _step(enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(enabled=enabled)


def test_l7_raw_metadata_separates_config_enabled_from_raw_applied(monkeypatch) -> None:
    monkeypatch.setenv("FFACT_FRACDIFF_APPLY_TO_LAYERS", "L1,L2")
    factory = FeatureFactory.__new__(FeatureFactory)
    config = SimpleNamespace(
        preprocessing=SimpleNamespace(
            enabled=True,
            winsorization=_step(True),
            rank_transform=_step(True),
            adaptive_zscore=_step(True),
            gaussian_normalize=_step(True),
            fractional_differencing=_step(True),
            adf_differencing=_step(False),
        )
    )
    raw_config = {
        "winsorization": {"enabled": True},
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
        "fractional_differencing": {"enabled": True, "apply_to": "non_stationary"},
        "adf_differencing": {"enabled": False},
    }

    metadata = factory._build_l7_raw_preprocessing_metadata(config, raw_config, "ic_first_pre")

    assert metadata["preprocessing_config_enabled"]["steps"]["rank_transform"] is True
    assert metadata["preprocessing_config_enabled"]["ic_first_pipeline"] is True
    assert metadata["preprocessing_config_enabled"]["steps"]["adaptive_zscore"] is True
    assert metadata["preprocessing_config_enabled"]["steps"]["gaussian_normalize"] is True
    assert metadata["raw_artifact_applied"]["mode"] == "ic_first_pre"
    assert metadata["raw_artifact_applied"]["steps"]["rank_transform"] is False
    assert metadata["raw_artifact_applied"]["steps"]["adaptive_zscore"] is False
    assert metadata["raw_artifact_applied"]["steps"]["gaussian_normalize"] is False
    assert metadata["rank_enabled"] is False
    assert metadata["zscore_enabled"] is False
    assert metadata["gaussian_enabled"] is False
    assert metadata["fracdiff_enabled"] is True
    assert metadata["raw_artifact_applied"]["fracdiff_layers"] == ["L1", "L2"]
