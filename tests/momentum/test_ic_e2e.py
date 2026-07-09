import json
import os
import time
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_ic_analyzer


_RUN_E2E_PERF = os.getenv("RUN_IC_E2E_PERF") == "1"


def _lenient_thresholds() -> dict:
    return {
        "ic_mean_min": -1.0,
        "icir_min": -1.0,
        "p_value_max": 1.0,
        "ic_hit_rate_min": 0.0,
        "monotonicity_score_min": 0.0,
        "coverage_min": 0.0,
        "long_short_spread": {"enabled": False},
    }


def _write_features_h5(path: Path, features_df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as file:
        group = file.create_group("BTCUSDT/12h")
        group.create_dataset(
            "features",
            data=features_df.to_numpy(dtype=np.float32),
            compression="gzip",
        )
        group.create_dataset(
            "timestamps",
            data=features_df.index.to_numpy(dtype=np.int64),
            compression="gzip",
        )
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset(
            "feature_names",
            data=np.array(features_df.columns.tolist(), dtype=object),
            dtype=str_dtype,
        )


def _write_labels_h5(path: Path, labels_df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as file:
        group = file.create_group("BTCUSDT/12h")
        group.create_dataset(
            "labels",
            data=labels_df.to_numpy(dtype=np.float32),
            compression="gzip",
        )
        group.create_dataset(
            "timestamps",
            data=labels_df.index.to_numpy(dtype=np.int64),
            compression="gzip",
        )
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset(
            "label_names",
            data=np.array(labels_df.columns.tolist(), dtype=object),
            dtype=str_dtype,
        )


def _write_meta_json(path: Path, feature_names: list[str]) -> None:
    payload = {
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "case_id": "ic_e2e_test",
    }
    for name in feature_names:
        payload[name] = {
            "name": name,
            "category": "trend",
            "layer": 1,
            "data_source": "close",
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")


def _make_sample_dataset(n_samples: int, n_features: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(42)
    timestamps = np.arange(n_samples, dtype=np.int64) * 12 * 60 * 60
    features = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)).astype(np.float32),
        columns=[f"feature_{i}" for i in range(n_features)],
        index=pd.Index(timestamps, name="timestamp"),
    )
    label_values = rng.normal(size=n_samples).astype(np.float32)
    label_values[-1] = np.nan
    labels = pd.DataFrame({"return_1": label_values}, index=features.index)
    return features, labels


class TestICGatekeeperE2E:
    def test_full_pipeline_global_mode(self, tmp_path: Path) -> None:
        """Global Mode: 完整八階段流水線 → 輸出精選特徵。"""
        features, labels = _make_sample_dataset(n_samples=120, n_features=8)

        features_path = tmp_path / "features.h5"
        labels_path = tmp_path / "labels.h5"
        meta_path = tmp_path / "meta.json"
        _write_features_h5(features_path, features)
        _write_labels_h5(labels_path, labels)
        _write_meta_json(meta_path, list(features.columns))

        config_override = {
            "thresholds": _lenient_thresholds(),
            "redundancy": {"correlation_threshold": 0.99},
        }

        analyzer = create_ic_analyzer(config_override)
        result = analyzer.analyze(
            features_path=str(features_path),
            labels_path=str(labels_path),
            meta_path=str(meta_path),
        )

        assert result["metadata"]["total_features_output"] >= 0
        assert result["metadata"]["total_features_input"] == 8
        assert result["metadata"]["total_features_output"] <= 8
        assert len(result["summary_table"]) > 0

    def test_refilter_uses_cache(self, tmp_path: Path) -> None:
        """refilter 不重算 IC。"""
        features, labels = _make_sample_dataset(n_samples=120, n_features=6)

        features_path = tmp_path / "features.h5"
        labels_path = tmp_path / "labels.h5"
        meta_path = tmp_path / "meta.json"
        _write_features_h5(features_path, features)
        _write_labels_h5(labels_path, labels)
        _write_meta_json(meta_path, list(features.columns))

        analyzer = create_ic_analyzer(
            {
                "thresholds": _lenient_thresholds()
            }
        )
        analyzer.analyze(
            features_path=str(features_path),
            labels_path=str(labels_path),
            meta_path=str(meta_path),
        )

        start = time.perf_counter()
        report = analyzer.refilter({"icir_min": -1.0})
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0
        assert "summary_table" in report

    def test_event_mode_with_query(self, tmp_path: Path) -> None:
        """Event Mode: Query String 過濾。"""
        features, labels = _make_sample_dataset(n_samples=150, n_features=6)

        features_path = tmp_path / "features.h5"
        labels_path = tmp_path / "labels.h5"
        meta_path = tmp_path / "meta.json"
        _write_features_h5(features_path, features)
        _write_labels_h5(labels_path, labels)
        _write_meta_json(meta_path, list(features.columns))

        analyzer = create_ic_analyzer(
            {
                "event_filter": {
                    "enabled": True,
                    "query": "feature_0 > 0",
                    "min_events": 30,
                },
                "thresholds": _lenient_thresholds(),
            }
        )

        report = analyzer.analyze(
            features_path=str(features_path),
            labels_path=str(labels_path),
            meta_path=str(meta_path),
        )

        event_info = report.get("metadata", {}).get("event_filter", {})
        assert event_info.get("mode") == "query"
        assert event_info.get("tier") in {"sufficient", "marginal", "low_confidence"}

    def test_report_json_structure(self, tmp_path: Path) -> None:
        """報告 JSON 結構完整性。"""
        features, labels = _make_sample_dataset(n_samples=120, n_features=5)

        features_path = tmp_path / "features.h5"
        labels_path = tmp_path / "labels.h5"
        meta_path = tmp_path / "meta.json"
        _write_features_h5(features_path, features)
        _write_labels_h5(labels_path, labels)
        _write_meta_json(meta_path, list(features.columns))

        analyzer = create_ic_analyzer(
            {
                "thresholds": _lenient_thresholds()
            }
        )
        report = analyzer.analyze(
            features_path=str(features_path),
            labels_path=str(labels_path),
            meta_path=str(meta_path),
        )

        for key in (
            "metadata",
            "filter_log",
            "summary_table",
            "ic_decay",
            "quantile_returns",
            "grouped_ic",
            "correlation_matrix",
            "diversification_metrics",
            "rolling_ic_series",
            "turnover_analysis",
            "coverage_analysis",
        ):
            assert key in report

    @pytest.mark.skipif(not _RUN_E2E_PERF, reason="Set RUN_IC_E2E_PERF=1 to run")
    def test_performance_800_features(self, tmp_path: Path) -> None:
        """效能: 800 特徵 × 10K 樣本 < 30 秒。"""
        features, labels = _make_sample_dataset(n_samples=10000, n_features=800)

        features_path = tmp_path / "features.h5"
        labels_path = tmp_path / "labels.h5"
        meta_path = tmp_path / "meta.json"
        _write_features_h5(features_path, features)
        _write_labels_h5(labels_path, labels)
        _write_meta_json(meta_path, list(features.columns))

        analyzer = create_ic_analyzer(
            {
                "thresholds": _lenient_thresholds(),
                "redundancy": {"correlation_threshold": 0.99},
            }
        )

        start = time.perf_counter()
        analyzer.analyze(
            features_path=str(features_path),
            labels_path=str(labels_path),
            meta_path=str(meta_path),
        )
        elapsed = time.perf_counter() - start

        assert elapsed < 30.0
