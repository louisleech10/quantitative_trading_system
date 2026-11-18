"""searchsorted 對齊效能驗收（T1.P1, T1.P2）。

TESTSEL S3：計時與行程 RSS 斷言屬效能基準（perf，結果隨機器負載而變）；輸出形狀屬正確性，留在非 perf 測試。
T1.P1 之對齊計算於模組 fixture 只做一次，正確性與計時兩條共用其結果（不重複計算）。
"""

import gc
import time
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


@pytest.fixture(scope="module")
def searchsorted_align_run() -> Dict[str, Any]:
    """12,888 列 × 1,000 欄 1h→12h 對齊跑一次：回傳主軸、欄數、輸出與牆鐘秒數。"""
    rows = 12_888
    cols = 1_000
    source_index = pd.date_range("2026-01-01", periods=rows, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=max(1, rows // 12), freq="12h")

    rng = np.random.RandomState(7)
    source_values = pd.DataFrame(
        rng.standard_normal((rows, cols)).astype(np.float32),
        index=source_index,
        columns=[f"c_{i}" for i in range(cols)],
    )

    start = time.perf_counter()
    aligned = TimeframeAligner._searchsorted_align(
        source_values=source_values,
        source_index=source_index,
        primary_index=primary_index,
        source_tf="1h",
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )
    elapsed = time.perf_counter() - start
    return {"aligned": aligned, "primary_index": primary_index, "cols": cols, "elapsed": elapsed}


@pytest.mark.slow
def test_searchsorted_align_output_shape(searchsorted_align_run: Dict[str, Any]) -> None:
    """T1.P1 之正確性部分：對齊輸出形狀＝(主軸長度, 欄數)。"""
    aligned, primary_index = searchsorted_align_run["aligned"], searchsorted_align_run["primary_index"]
    cols = searchsorted_align_run["cols"]
    assert aligned.shape == (len(primary_index), cols)


@pytest.mark.perf
@pytest.mark.slow
def test_searchsorted_align_speed(searchsorted_align_run: Dict[str, Any]) -> None:
    """T1.P1: searchsorted 對齊速度需在 30 秒內。"""
    elapsed = searchsorted_align_run["elapsed"]
    assert elapsed < 30.0


@pytest.mark.perf
@pytest.mark.slow
def test_searchsorted_align_memory():
    """T1.P2: searchsorted 對齊 RSS 增量應小於 500 MB。"""
    try:
        import psutil
    except Exception:
        pytest.skip("psutil not available")

    process = psutil.Process()
    rows = 8_000
    cols = 800
    source_index = pd.date_range("2026-01-01", periods=rows, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=max(1, rows // 12), freq="12h")

    rng = np.random.RandomState(11)
    source_values = pd.DataFrame(
        rng.standard_normal((rows, cols)).astype(np.float32),
        index=source_index,
        columns=[f"m_{i}" for i in range(cols)],
    )

    gc.collect()
    rss_before = process.memory_info().rss
    _ = TimeframeAligner._searchsorted_align(
        source_values=source_values,
        source_index=source_index,
        primary_index=primary_index,
        source_tf="1h",
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )
    gc.collect()
    rss_after = process.memory_info().rss

    delta_mb = max(0.0, (rss_after - rss_before) / (1024 * 1024))
    assert delta_mb < 500.0
