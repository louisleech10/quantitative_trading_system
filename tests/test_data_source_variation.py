#!/usr/bin/env python3
"""
測試不同 data_source 的 EMA 特徵工程
驗證：Optuna 的 data_source 參數確實會影響 EMA 計算

TESTREG Task 4.4 改寫：原版零 assert（extract_features_from_strategy 回傳 tuple 未解包、`.iloc` 拋錯被吞，
差異與範圍檢查只寫 log）且讀非 canonical 之 data_cache/kline_cache.h5。改為讀真實 feature_klines
（requires_kline_data，缺檔 fail 非 skip），逐 data_source 以獨立遞迴 EMA（alpha=2/(span+1)、首值起算）
對生產輸出之 `{data_source}_ema{N}_value` 全列比對，並斷言不同 data_source 產生不同 EMA。

Author: Louis
Date: 2026-01-10
"""

from typing import Callable

import numpy as np
import pytest
import pandas as pd

from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams

_SPANS = (5, 20, 60)
_DATA_SOURCES = ("close", "volume", "taker_ratio")


def _reference_ema(values: np.ndarray, span: int) -> np.ndarray:
    """獨立 oracle：遞迴 EMA（adjust=False 語意），第 0 列＝首值。"""
    alpha = 2.0 / (span + 1.0)
    out = np.empty(len(values), dtype=np.float64)
    out[0] = values[0]
    for i in range(1, len(values)):
        out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]
    return out


@pytest.mark.requires_kline
def test_data_source_variation(requires_kline_data: Callable[..., pd.DataFrame]) -> None:
    """測試不同 data_source 對 EMA 特徵的影響"""
    df = requires_kline_data("ETHUSDT", "1h", min_rows=100).tail(100).reset_index(drop=True)
    base_params = {"ema_short": 5, "ema_mid": 20, "ema_long": 60, "volume_threshold": 0.6}
    extractor = FeatureExtractor()

    last_values: dict[str, np.ndarray] = {}
    for data_source in _DATA_SOURCES:
        strategy_params = StrategyParams(
            strategy_type="ema_three_line",
            data_source=data_source,
            params=base_params,
        )
        features_df, feature_names = extractor.extract_features_from_strategy(df.copy(), strategy_params)

        source_values = df[data_source].to_numpy(dtype=np.float64)
        assert np.isfinite(source_values).all()
        row = []
        for span in _SPANS:
            col = f"{data_source}_ema{span}_value"
            assert col in feature_names
            np.testing.assert_allclose(
                features_df[col].to_numpy(dtype=np.float64),
                _reference_ema(source_values, span),
                rtol=1e-9,
                atol=0.0,
            )
            row.append(float(features_df[col].iloc[-1]))
        last_values[data_source] = np.asarray(row)

    # 不同 data_source 之 EMA 必不同（data_source 參數確實生效）
    for i, first in enumerate(_DATA_SOURCES):
        for second in _DATA_SOURCES[i + 1:]:
            assert not np.allclose(last_values[first], last_values[second])
    # taker_ratio 為比率 ⇒ 其 EMA 必落在 [0, 1]（凸組合不出界）
    assert ((last_values["taker_ratio"] >= 0.0) & (last_values["taker_ratio"] <= 1.0)).all()
