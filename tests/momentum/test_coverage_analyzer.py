import numpy as np
import pandas as pd

from momentum.Analysis.coverage_analyzer import CoverageAnalyzer


def test_time_coverage_and_effective_start():
    """覆蓋率與有效起始點正確計算。"""
    series = pd.Series([np.nan, np.nan, 1.0, 2.0])
    analyzer = CoverageAnalyzer()

    coverage = analyzer.compute_time_coverage(series)
    effective_start = analyzer.compute_effective_start(series)

    assert np.isclose(coverage, 0.5)
    assert effective_start == 2


def test_empty_series_outputs_nan_and_negative_start():
    """空序列回傳 NaN 與 -1。"""
    analyzer = CoverageAnalyzer()
    series = pd.Series([], dtype=float)

    assert np.isnan(analyzer.compute_time_coverage(series))
    assert analyzer.compute_effective_start(series) == -1


def test_effective_start_all_nan():
    """全 NaN 回傳 -1。"""
    series = pd.Series([np.nan, np.nan])
    analyzer = CoverageAnalyzer()

    assert analyzer.compute_effective_start(series) == -1


def test_compute_all_and_flag_low_coverage():
    """批次計算與低覆蓋率標記。"""
    df = pd.DataFrame(
        {
            "feature_a": [1.0, 2.0, np.nan, np.nan],
            "feature_b": [1.0, 2.0, 3.0, 4.0],
        }
    )
    analyzer = CoverageAnalyzer()

    results = analyzer.compute_all(df)
    low = analyzer.flag_low_coverage(results, threshold=0.6)

    assert set(results.keys()) == {"feature_a", "feature_b"}
    assert results["feature_a"]["nan_count"] == 2
    assert low == ["feature_a"]


def test_flag_low_coverage_skips_nan():
    """NaN 覆蓋率不應被標記。"""
    analyzer = CoverageAnalyzer()

    coverage_results = {
        "feature_a": {"coverage": float("nan")},
        "feature_b": {"coverage": 0.4},
    }
    low = analyzer.flag_low_coverage(coverage_results, threshold=0.5)

    assert low == ["feature_b"]
