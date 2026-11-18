"""Phase 3 效能驗收測試（T3.P1, T3.P2）。

TESTSEL S3：計時與行程 RSS 斷言屬效能基準（perf，結果隨機器負載而變）；輸出形狀屬正確性，留在非 perf 測試。
壓力場景之計算於模組 fixture 只做一次，正確性與計時兩條共用其結果（不重複計算）。
"""

from __future__ import annotations

import gc
import time
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator


def _make_perf_df(n_rows: int, n_cols: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    values = rng.normal(loc=0.0, scale=1.0, size=(n_rows, n_cols)).astype(np.float64)
    values[::97, 0] = np.nan
    values[::131, 1] = np.nan
    return pd.DataFrame(values, columns=[f"feat_{idx:04d}" for idx in range(n_cols)])


@pytest.fixture(scope="module")
def numba_rolling_stress_run() -> Dict[str, Any]:
    """壓力場景（2,500 列 × 96 欄、9 窗 × 10 聚合）跑一次：回傳輸入、輸出與牆鐘秒數。"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("FFACT_L3_STREAMING", "1")
        mp.setenv("FFACT_USE_NUMBA_ROLLING", "1")

        config = {
            "enabled": True,
            "windows": [5, 8, 13, 21, 34, 55, 89, 144, 233],
            "aggregators": ["slope", "std", "mean", "rank", "zscore", "skew", "kurt", "min", "max", "range"],
            "apply_to": "all",
        }

        warmup_df = _make_perf_df(n_rows=260, n_cols=8, seed=7)
        RollingAggregator(config).compute_all(warmup_df)

        test_df = _make_perf_df(n_rows=2_500, n_cols=96, seed=11)

        started = time.perf_counter()
        result = RollingAggregator(config).compute_all(test_df)
        elapsed = time.perf_counter() - started
    return {"test_df": test_df, "result": result, "elapsed": elapsed}


@pytest.mark.slow
def test_numba_rolling_stress_output_shape(numba_rolling_stress_run: Dict[str, Any]) -> None:
    """T3.P1 之正確性部分：壓力場景輸出列數等於輸入、欄數非零。"""
    result, test_df = numba_rolling_stress_run["result"], numba_rolling_stress_run["test_df"]
    assert result.shape[0] == test_df.shape[0]
    assert result.shape[1] > 0


@pytest.mark.perf
@pytest.mark.slow
def test_numba_rolling_speed_under_120s(numba_rolling_stress_run: Dict[str, Any]) -> None:
    """T3.P1: Numba rolling 在壓力場景下應於 120 秒內完成。"""
    elapsed = numba_rolling_stress_run["elapsed"]
    assert elapsed < 120.0


@pytest.mark.perf
@pytest.mark.slow
def test_numba_rolling_memory_under_500mb(monkeypatch):
    """T3.P2: Numba rolling 的 RSS 增量應低於 500 MB。"""
    try:
        import psutil
    except Exception:
        pytest.skip("psutil not available")

    monkeypatch.setenv("FFACT_L3_STREAMING", "1")
    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "1")

    config = {
        "enabled": True,
        "windows": [5, 13, 21, 34, 55],
        "aggregators": ["mean", "std", "rank", "slope", "range"],
        "apply_to": "all",
    }

    process = psutil.Process()
    test_df = _make_perf_df(n_rows=2_000, n_cols=96, seed=17)

    gc.collect()
    rss_before = process.memory_info().rss
    _ = RollingAggregator(config).compute_all(test_df)
    gc.collect()
    rss_after = process.memory_info().rss

    delta_mb = max(0.0, float(rss_after - rss_before) / (1024.0 * 1024.0))
    assert delta_mb < 500.0
