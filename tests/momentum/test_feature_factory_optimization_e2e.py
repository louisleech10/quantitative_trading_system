from __future__ import annotations

from copy import deepcopy

import pandas as pd

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine


def _base_pipeline_override() -> dict:
    return {
        "atomic_indicators": {
            "trend": {"enabled": False},
            "momentum": {"enabled": False},
            "volatility": {"enabled": False},
            "volume": {"enabled": False},
            "cycle": {"enabled": False},
            "pattern": {"enabled": False},
            "statistics": {"enabled": False},
            "microstructure": {"enabled": False},
            "entropy": {"enabled": False},
            "tail_risk": {"enabled": False},
        },
        "operators": {
            "distance": {"enabled": False},
            "cross": {"enabled": False},
            "momentum": {"enabled": False},
            "ratio": {"enabled": False},
            "binary_signal": {"enabled": False},
            "worldquant": {"enabled": False},
        },
        "rolling_aggregation": {"enabled": False},
        "lag_features": {"enabled": False},
        "cross_sectional": {"enabled": False},
        "meta_features": {"enabled": False},
        "preprocessing": {"enabled": False},
    }


def _generate(config_override: dict):
    factory = create_feature_factory()
    return factory.generate_features(
        symbol="BTCUSDT",
        timeframe="12h",
        config_override=config_override,
        force_regenerate=True,
    )


def test_pipeline_with_microstructure() -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["microstructure"]["enabled"] = True

    result = _generate(config)
    ms_columns = [col for col in result.features_df.columns if col.startswith("ms_")]

    assert len(ms_columns) > 0


def test_pipeline_with_entropy() -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["entropy"]["enabled"] = True

    result = _generate(config)
    ent_columns = [col for col in result.features_df.columns if col.startswith("ent_")]

    assert len(ent_columns) > 0


def test_pipeline_with_tail_risk() -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["tail_risk"]["enabled"] = True

    result = _generate(config)
    tr_columns = [col for col in result.features_df.columns if col.startswith("tr_")]

    assert len(tr_columns) > 0


def test_pipeline_with_preprocessing() -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["microstructure"]["enabled"] = True
    config["preprocessing"] = {
        "enabled": True,
        "mode": "append",
        "winsorization": {"enabled": True, "apply_to": "all"},
        "adf_differencing": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "rank_transform": {"enabled": True, "window": 55, "apply_to": "all"},
        "gaussian_normalize": {"enabled": False},
        "adaptive_zscore": {"enabled": True, "windows": [55], "apply_to": "all", "epsilon": 1e-8},
    }

    result = _generate(config)
    columns = result.features_df.columns

    assert any(col.endswith("_rank") for col in columns)
    assert any("_zscore_" in col for col in columns)


def test_pipeline_all_new_features() -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["microstructure"]["enabled"] = True
    config["atomic_indicators"]["entropy"]["enabled"] = True
    config["atomic_indicators"]["tail_risk"]["enabled"] = True
    config["preprocessing"] = {
        "enabled": True,
        "mode": "append",
        "winsorization": {"enabled": True, "apply_to": "all"},
        "adf_differencing": {"enabled": False},
        "fractional_differencing": {"enabled": False},
        "rank_transform": {"enabled": True, "window": 55, "apply_to": "all"},
        "gaussian_normalize": {"enabled": False},
        "adaptive_zscore": {"enabled": True, "windows": [55], "apply_to": "all", "epsilon": 1e-8},
    }

    result = _generate(config)

    assert result.feature_count > 0
    assert any(col.startswith("ms_") for col in result.features_df.columns)
    assert any(col.startswith("ent_") for col in result.features_df.columns)
    assert any(col.startswith("tr_") for col in result.features_df.columns)
    assert result.hdf5_path is not None
    assert "validation" in result.metadata


def test_pipeline_backward_compatible() -> None:
    config_a = _base_pipeline_override()
    config_b = deepcopy(_base_pipeline_override())

    result_a = _generate(config_a)
    result_b = _generate(config_b)

    assert result_a.features_df.shape == result_b.features_df.shape
    assert list(result_a.features_df.columns) == list(result_b.features_df.columns)
    pd.testing.assert_frame_equal(result_a.features_df, result_b.features_df)


def test_pipeline_partial_engine_failure(monkeypatch) -> None:
    config = _base_pipeline_override()
    config["atomic_indicators"]["microstructure"]["enabled"] = True
    config["atomic_indicators"]["tail_risk"]["enabled"] = True

    def _raise(*_args, **_kwargs):
        raise RuntimeError("forced microstructure failure")

    monkeypatch.setattr(MicrostructureIndicatorEngine, "compute_all", _raise)

    result = _generate(config)

    assert any(col.startswith("tr_") for col in result.features_df.columns)
    assert not any(col.startswith("ms_") for col in result.features_df.columns)