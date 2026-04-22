from __future__ import annotations

import gc
import time

import numpy as np
import pandas as pd
import psutil
import pytest

from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator


WINDOWS = [5, 8, 13, 21, 34, 55, 89, 144, 233]
ALL_AGGS = ["slope", "std", "mean", "rank", "zscore", "skew", "kurt", "min", "max", "range"]


@pytest.fixture
def perf_frame() -> pd.DataFrame:
    """建立 Phase 3 效能驗收用的穩定輸入資料。"""
    rng = np.random.default_rng(20260422)
    data = rng.normal(loc=0.0, scale=1.0, size=(12000, 128)).astype(np.float64)
    data[::53, 5] = np.nan
    data[::79, 11] = np.nan
    return pd.DataFrame(data, columns=[f"perf_{idx:03d}" for idx in range(data.shape[1])])


def _build_config() -> dict:
    return {
        "enabled": True,
        "windows": WINDOWS,
        "aggregators": ALL_AGGS,
        "apply_to": "all",
    }


def _measure_runtime(
    perf_frame: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
    multi_window_enabled: bool,
    rounds: int = 1,
) -> float:
    monkeypatch.setenv("FFACT_L3_STREAMING", "1")
    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "1")
    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "1" if multi_window_enabled else "0")

    config = _build_config()
    aggregator = RollingAggregator(config)
    _ = aggregator.compute_all(perf_frame)

    timings = []
    for _ in range(rounds):
        start_time = time.perf_counter()
        _ = RollingAggregator(config).compute_all(perf_frame)
        timings.append(time.perf_counter() - start_time)
    return min(timings)


def test_multi_window_speedup(perf_frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch):
    """T3.P1: multi-window 路徑應比 fallback 路徑快至少 1.3 倍。"""
    fallback_time = _measure_runtime(perf_frame, monkeypatch, multi_window_enabled=False)
    multi_window_time = _measure_runtime(perf_frame, monkeypatch, multi_window_enabled=True)

    speedup = fallback_time / multi_window_time
    assert speedup >= 1.3, (
        f"Expected multi-window speedup >= 1.3x, got {speedup:.2f}x "
        f"(fallback={fallback_time:.3f}s, multi={multi_window_time:.3f}s)"
    )


def test_multi_window_rss_stable(perf_frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch):
    """T3.P2: multi-window 路徑的 RSS 增量應低於 500 MB。"""
    monkeypatch.setenv("FFACT_L3_STREAMING", "1")
    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "1")
    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "1")

    process = psutil.Process()
    gc.collect()
    rss_before = process.memory_info().rss

    _ = RollingAggregator(_build_config()).compute_all(perf_frame)

    gc.collect()
    rss_after = process.memory_info().rss
    rss_delta = rss_after - rss_before

    assert rss_delta < 500 * 1024 * 1024, f"Expected RSS delta < 500 MB, got {rss_delta / 1024 / 1024:.2f} MB"