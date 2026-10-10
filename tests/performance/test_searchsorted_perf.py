import gc
import time

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner


@pytest.mark.slow
def test_searchsorted_align_speed():
    """T1.P1: searchsorted 對齊速度需在 30 秒內。"""
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

    assert aligned.shape == (len(primary_index), cols)
    assert elapsed < 30.0


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












