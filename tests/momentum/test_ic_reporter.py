from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_reporter import ICReporter


def test_report_generation_and_persistence(tmp_path: Path):
    """報告輸出應包含必要欄位且可持久化。"""
    reporter = ICReporter({"ai_summary": True})

    analysis_results = {
        "filter_log": {"stage": {"input": 10, "output": 5}},
        "summary_table": [
            {"feature_name": "f1", "icir": 0.8, "ic_mean": 0.03}
        ],
        "ic_decay": {},
        "quantile_returns": {},
        "grouped_ic": {},
        "correlation_matrix": {"features": [], "matrix": []},
        "diversification_metrics": {},
        "rolling_ic_series": {},
        "turnover_analysis": {},
        "coverage_analysis": {},
        "cross_sectional_symbol_ic": {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "features": ["f1"],
            "matrix": {"f1": {"BTCUSDT": 0.1, "ETHUSDT": 0.08}},
        },
        "cross_symbol_validation": {
            "status": "completed",
            "consistency_score": 0.76,
        },
    }
    metadata = {"total_features_input": 10, "total_features_output": 5}

    report = reporter.generate_json_report(analysis_results, metadata)
    assert report["metadata"]["total_features_output"] == 5
    assert "summary_table" in report
    assert "cross_sectional_symbol_ic" in report
    assert "cross_symbol_validation" in report

    output_dir = tmp_path / "reports"
    saved = reporter.save_report(report, str(output_dir), "case_1")
    assert Path(saved["json"]).exists()
    assert Path(saved["markdown"]).exists()


def test_save_filtered_features(tmp_path: Path):
    """精選特徵應可輸出為 HDF5。"""
    reporter = ICReporter({})
    df = pd.DataFrame(
        np.random.randn(10, 3).astype(np.float32),
        columns=["a", "b", "c"],
        index=pd.Index(np.arange(10), name="timestamp"),
    )

    output_path = tmp_path / "filtered.h5"
    saved_path = reporter.save_filtered_features(df, ["a", "c"], str(output_path))

    assert Path(saved_path).exists()
    with h5py.File(saved_path, "r") as file:
        assert "filtered" in file
        group = file["filtered"]
        assert group["features"].shape == (10, 2)
        assert group["feature_names"][0].decode("utf-8") == "a"


def test_generate_ai_summary_empty_table():
    """空 summary_table 時輸出應包含 fallback。"""
    reporter = ICReporter({"ai_summary": True})
    report = reporter.generate_json_report({"summary_table": []}, metadata={})

    summary = reporter.generate_ai_summary(report)

    assert "No features passed" in summary


def test_save_filtered_features_errors(tmp_path: Path):
    """空 DataFrame 或空欄位應拋出錯誤。"""
    reporter = ICReporter({})
    df = pd.DataFrame()

    with pytest.raises(ValueError):
        reporter.save_filtered_features(df, ["a"], str(tmp_path / "x.h5"))

    df = pd.DataFrame({"a": [1.0, 2.0]})
    with pytest.raises(ValueError):
        reporter.save_filtered_features(df, [], str(tmp_path / "x.h5"))


def test_sample_rolling_series_non_dict():
    """非 dict 輸入應直接回傳。"""
    reporter = ICReporter({})

    assert reporter._sample_rolling_series([1, 2, 3]) == [1, 2, 3]


def test_generate_filter_log_skips_none():
    """None 結果應被略過。"""
    reporter = ICReporter({})

    log = reporter.generate_filter_log({"stage1": {"ok": True}, "stage2": None})
    assert "stage1" in log
    assert "stage2" not in log


def test_extract_timestamps_branches():
    """timestamp 分支應使用正確來源。"""
    reporter = ICReporter({})

    df_dt = pd.DataFrame({"a": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2, freq="D"))
    assert reporter._extract_timestamps(df_dt).shape[0] == 2

    df_index = pd.DataFrame({"a": [1.0, 2.0]}, index=pd.Index([10, 20], name="timestamp"))
    assert reporter._extract_timestamps(df_index).tolist() == [10, 20]

    df_col = pd.DataFrame({"timestamp": [100, 200], "a": [1.0, 2.0]})
    assert reporter._extract_timestamps(df_col).tolist() == [100, 200]

    df_default = pd.DataFrame({"a": [1.0, 2.0]})
    assert reporter._extract_timestamps(df_default).tolist() == [0, 1]


def test_sample_rolling_series_limits_and_windows():
    """max_points 與非 dict windows 分支。"""
    reporter = ICReporter({"max_series_points": 0})
    sample = reporter._sample_rolling_series({"f1": {"window_5": [1, 2, 3]}})
    assert sample["f1"]["window_5"] == [1, 2, 3]

    reporter = ICReporter({"max_series_points": 2})
    sample = reporter._sample_rolling_series({"f1": [1, 2, 3]})
    assert sample["f1"] == [1, 2, 3]

    series = list(range(10))
    sample = reporter._sample_rolling_series({"f1": {"window_5": series}})
    assert len(sample["f1"]["window_5"]) <= 2
