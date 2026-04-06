import numpy as np
import pandas as pd
import h5py

from momentum.Analysis.coverage_analyzer import CoverageAnalyzer


def _write_feature_h5(path, data: np.ndarray, feature_names: list[str]) -> None:
    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=data)
        group.create_dataset(
            "feature_names",
            data=np.array(feature_names, dtype=object),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )


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


def test_compute_symbol_coverage_matrix(tmp_path):
    """features x symbols NaN 率矩陣計算正確。"""
    analyzer = CoverageAnalyzer()
    base = tmp_path / "features"
    base.mkdir()

    _write_feature_h5(
        base / "BTCUSDT_12h_factory.h5",
        np.array(
            [
                [1.0, np.nan],
                [np.nan, np.nan],
                [3.0, 1.0],
            ],
            dtype=float,
        ),
        ["feature_a", "feature_b"],
    )
    _write_feature_h5(
        base / "ETHUSDT_12h_factory.h5",
        np.array(
            [
                [1.0, 4.0],
                [2.0, 5.0],
                [3.0, 6.0],
            ],
            dtype=float,
        ),
        ["feature_a", "feature_b"],
    )

    result = analyzer.compute_symbol_coverage_matrix(
        symbols=["btcusdt", "ethusdt"],
        timeframe="12h",
        feature_names=["feature_a", "feature_b"],
        feature_base_path=str(base),
    )

    assert result["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert result["features"] == ["feature_a", "feature_b"]
    assert np.isclose(result["matrix"]["feature_a"]["BTCUSDT"], 1.0 / 3.0)
    assert np.isclose(result["matrix"]["feature_a"]["ETHUSDT"], 0.0)
    assert np.isclose(result["matrix"]["feature_b"]["BTCUSDT"], 2.0 / 3.0)
    assert np.isclose(result["matrix"]["feature_b"]["ETHUSDT"], 0.0)
    assert result["valid_counts"]["feature_b"]["BTCUSDT"] == 1
    assert result["row_counts"]["BTCUSDT"] == 3
    assert result["summary"]["worst_symbol"] == "BTCUSDT"
    assert result["summary"]["worst_feature"] == "feature_b"


def test_compute_symbol_coverage_matrix_missing_symbol_file(tmp_path):
    """缺失 Symbol 檔案時，應回傳 100% NaN。"""
    analyzer = CoverageAnalyzer()
    base = tmp_path / "features"
    base.mkdir()

    _write_feature_h5(
        base / "BTCUSDT_12h_factory.h5",
        np.array([[1.0], [2.0], [3.0]], dtype=float),
        ["feature_a"],
    )

    result = analyzer.compute_symbol_coverage_matrix(
        symbols=["BTCUSDT", "SOLUSDT"],
        timeframe="12h",
        feature_names=["feature_a"],
        feature_base_path=str(base),
    )

    assert np.isclose(result["matrix"]["feature_a"]["BTCUSDT"], 0.0)
    assert np.isclose(result["matrix"]["feature_a"]["SOLUSDT"], 1.0)
    assert result["valid_counts"]["feature_a"]["SOLUSDT"] == 0
    assert result["row_counts"]["SOLUSDT"] == 0
