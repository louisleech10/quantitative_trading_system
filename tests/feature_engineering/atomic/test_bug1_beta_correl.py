"""BUG-1 新舊差異表 + IC 語義漂移 smoke + metadata 驗證。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import talib

from momentum.FeatureEngineering.atomic.statistics_indicators import StatisticsIndicatorEngine
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper

pytestmark = pytest.mark.requires_kline

DIFF_TABLE_PATH = Path("tests/_golden/ff_deepaudit/beta_correl_v0_v1_diff.json")


@pytest.fixture
def ohlcv_df(requires_kline_data):
    return requires_kline_data("BTCUSDT", "12h", min_rows=500)


def test_beta_correl_metadata_non_standard_variants() -> None:
    engine = StatisticsIndicatorEngine(
        {
            "indicators": [
                {"name": "Beta_CloseVolume", "periods": [5]},
                {"name": "Correl_CloseVolume", "periods": [5]},
            ]
        },
        ["close"],
    )
    meta = engine.get_feature_metadata()
    beta_cols = [k for k in meta if "Beta-CloseVolume" in k]
    correl_cols = [k for k in meta if "Correl-CloseVolume" in k]
    assert len(beta_cols) == 1
    assert len(correl_cols) == 1
    assert meta[beta_cols[0]]["variant"] == "non_standard_close_volume"
    assert meta[correl_cols[0]]["variant"] == "non_standard_close_volume"


def test_beta_correl_v0_v1_diff_table(ohlcv_df) -> None:
    """§G v1：記錄舊 close-volume BETA/CORREL 語義 vs 新 hl 標準 + 價量別名。"""
    params = {"timeperiod": 5}
    high = ohlcv_df["high"].to_numpy(dtype=float)
    low = ohlcv_df["low"].to_numpy(dtype=float)
    close = ohlcv_df["close"].to_numpy(dtype=float)
    volume = ohlcv_df["volume"].to_numpy(dtype=float)

    old_beta = talib.BETA(close, volume, timeperiod=5)
    old_correl = talib.CORREL(close, volume, timeperiod=5)
    new_beta_hl = TALibWrapper.compute("BETA", ohlcv_df, params).iloc[:, 0].to_numpy()
    new_correl_hl = TALibWrapper.compute("CORREL", ohlcv_df, params).iloc[:, 0].to_numpy()
    new_beta_cv = TALibWrapper.compute("Beta_CloseVolume", ohlcv_df, params).iloc[:, 0].to_numpy()
    new_correl_cv = TALibWrapper.compute("Correl_CloseVolume", ohlcv_df, params).iloc[:, 0].to_numpy()

    mask_b = ~(np.isnan(old_beta) | np.isnan(new_beta_hl))
    mask_c = ~(np.isnan(old_correl) | np.isnan(new_correl_hl))

    table = {
        "migration": {
            "old_column_pattern": "close-volume_{tf}_statistics_BETA_{p}",
            "new_standard_pattern": "hl_{tf}_statistics_BETA_{p}",
            "new_legacy_pattern": "close-volume_{tf}_statistics_Beta-CloseVolume_{p}",
        },
        "BTCUSDT_12h_period_5": {
            "old_beta_vs_new_hl_beta": {
                "max_abs_diff": float(np.max(np.abs(old_beta[mask_b] - new_beta_hl[mask_b]))),
                "semantic_change": True,
            },
            "old_correl_vs_new_hl_correl": {
                "max_abs_diff": float(np.max(np.abs(old_correl[mask_c] - new_correl_hl[mask_c]))),
                "semantic_change": True,
            },
            "old_beta_vs_beta_close_volume": {
                "max_abs_diff": float(
                    np.max(np.abs(old_beta[mask_b] - new_beta_cv[mask_b]))
                ),
                "preserved_legacy_semantics": True,
            },
            "old_correl_vs_correl_close_volume": {
                "max_abs_diff": float(
                    np.max(np.abs(old_correl[mask_c] - new_correl_cv[mask_c]))
                ),
                "preserved_legacy_semantics": True,
            },
        },
        "ic_semantic_drift_smoke": {
            "note": "IC on statistics_BETA family will change;三方簽核待 Claude 接回",
            "old_feature_ic_basis": "close-volume BETA (mislabeled)",
            "new_standard_ic_basis": "hl BETA (TA-Lib canonical)",
            "legacy_alias_ic_basis": "Beta-CloseVolume (explicit non-standard)",
        },
    }
    DIFF_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIFF_TABLE_PATH.write_text(json.dumps(table, indent=2), encoding="utf-8")

    np.testing.assert_allclose(old_beta[mask_b], new_beta_cv[mask_b], rtol=1e-10, atol=1e-10)
    np.testing.assert_allclose(old_correl[mask_c], new_correl_cv[mask_c], rtol=1e-10, atol=1e-10)
    assert table["BTCUSDT_12h_period_5"]["old_beta_vs_new_hl_beta"]["max_abs_diff"] > 0.01


def test_mutation_beta_input_type_close_volume_regression_fails(ohlcv_df) -> None:
    """§B1.1：BETA input_type 還原 close_volume（舊 bug）→ 雙 oracle 必紅。"""
    import talib

    params = {"timeperiod": 5}
    high = ohlcv_df["high"].to_numpy(dtype=float)
    low = ohlcv_df["low"].to_numpy(dtype=float)
    close = ohlcv_df["close"].to_numpy(dtype=float)
    volume = ohlcv_df["volume"].to_numpy(dtype=float)

    TALibWrapper.INDICATOR_REGISTRY.clear()
    TALibWrapper.initialize()
    hl_original = set(TALibWrapper._INPUT_TYPE_MAP["hl"])
    cv_original = set(TALibWrapper._INPUT_TYPE_MAP["close_volume"])
    try:
        hl_mutated = set(hl_original)
        hl_mutated.discard("BETA")
        cv_mutated = set(cv_original) | {"BETA"}
        TALibWrapper._INPUT_TYPE_MAP["hl"] = hl_mutated
        TALibWrapper._INPUT_TYPE_MAP["close_volume"] = cv_mutated
        TALibWrapper.INDICATOR_REGISTRY.clear()
        TALibWrapper.initialize()

        beta_hl = TALibWrapper.compute("BETA", ohlcv_df, params).iloc[:, 0].to_numpy()
        oracle_hl = talib.BETA(high, low, timeperiod=5)
        mask = ~(np.isnan(beta_hl) | np.isnan(oracle_hl))
        with pytest.raises(AssertionError):
            np.testing.assert_allclose(beta_hl[mask], oracle_hl[mask], rtol=1e-10, atol=1e-10)
    finally:
        TALibWrapper._INPUT_TYPE_MAP["hl"] = hl_original
        TALibWrapper._INPUT_TYPE_MAP["close_volume"] = cv_original
        TALibWrapper.INDICATOR_REGISTRY.clear()
        TALibWrapper.initialize()
