import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import FeatureFilterSchema, load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.core.exceptions import InvalidInputError


def _orchestrator() -> ICFilterOrchestrator:
    return ICFilterOrchestrator(load_ic_config())


def _write_features_h5(path: Path, features_df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as file:
        group = file.create_group("BTCUSDT/12h")
        group.create_dataset("features", data=features_df.to_numpy(dtype=np.float32))
        group.create_dataset("timestamps", data=features_df.index.to_numpy(dtype=np.int64))
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
        group.create_dataset("labels", data=labels_df.to_numpy(dtype=np.float32))
        group.create_dataset("timestamps", data=labels_df.index.to_numpy(dtype=np.int64))
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset(
            "label_names",
            data=np.array(labels_df.columns.tolist(), dtype=object),
            dtype=str_dtype,
        )


def _write_meta_json(path: Path, features: list[str]) -> None:
    metadata = {
        name: {
            "name": name,
            "category": "trend",
            "layer": 1,
            "data_source": "close",
        }
        for name in features
    }
    metadata["symbol"] = "BTCUSDT"
    metadata["timeframe"] = "12h"
    path.write_text(json.dumps(metadata, ensure_ascii=True), encoding="utf-8")


def _sha_columns(columns: list[str]) -> str:
    return hashlib.sha256("\n".join(columns).encode()).hexdigest()


def test_load_ic_config_keeps_feature_filter_override() -> None:
    config = load_ic_config(api_override={"feature_filter": {"max_features": 30}})

    assert config.feature_filter is not None
    assert config.feature_filter.max_features == 30


def test_feature_filter_none_keeps_all_features() -> None:
    features = pd.DataFrame({f"f_{idx}": [float(idx)] for idx in range(5)})

    filtered, _metadata, info = _orchestrator()._apply_feature_filter(
        features,
        metadata={},
        feature_filter=None,
    )

    assert list(filtered.columns) == list(features.columns)
    assert info["feature_count_original"] == 5
    assert info["feature_count_filtered"] == 5
    assert info["feature_filter_applied"] is False
    assert info["truncation_mode"] == "none"


def test_feature_filter_max_features_uses_sorted_stable_subset() -> None:
    columns = ["zeta", "alpha", "kappa", "beta", "theta"]
    features = pd.DataFrame({column: [1.0, 2.0, 3.0] for column in columns})

    first, _metadata, first_info = _orchestrator()._apply_feature_filter(
        features,
        metadata={},
        feature_filter=FeatureFilterSchema(max_features=2),
    )
    second, _metadata, second_info = _orchestrator()._apply_feature_filter(
        features[columns[::-1]],
        metadata={},
        feature_filter=FeatureFilterSchema(max_features=2),
    )

    assert list(first.columns) == ["alpha", "beta"]
    assert list(second.columns) == ["alpha", "beta"]
    assert first_info == second_info
    assert first_info["feature_count_filtered"] == 2
    assert first_info["truncation_mode"] == "preview"
    assert first_info["truncation_order"] == "sorted_column_name"


def test_feature_filter_metadata_dimensions_do_not_preview_truncate() -> None:
    features = pd.DataFrame(
        {
            "trend_a": [1.0, 2.0],
            "trend_b": [2.0, 3.0],
            "volume_a": [3.0, 4.0],
        }
    )
    metadata = {
        "trend_a": {"category": "trend", "data_source": "close", "family": "ema"},
        "trend_b": {"category": "trend", "data_source": "close", "family": "sma"},
        "volume_a": {"category": "volume", "data_source": "volume", "family": "vpin"},
        "symbol": "BTCUSDT",
    }

    filtered, filtered_metadata, info = _orchestrator()._apply_feature_filter(
        features,
        metadata=metadata,
        feature_filter=FeatureFilterSchema(include_categories=["trend"]),
    )

    assert list(filtered.columns) == ["trend_a", "trend_b"]
    assert "volume_a" not in filtered_metadata
    assert filtered_metadata["symbol"] == "BTCUSDT"
    assert info["feature_filter_applied"] is True
    assert info["truncation_mode"] == "none"


def test_feature_filter_empty_result_fails_closed() -> None:
    features = pd.DataFrame({"alpha": [1.0, 2.0]})

    with pytest.raises(InvalidInputError, match="feature_filter selected zero features"):
        _orchestrator()._apply_feature_filter(
            features,
            metadata={},
            feature_filter=FeatureFilterSchema(include_pattern="does_not_match"),
        )


def test_analyze_applies_feature_filter_metadata_and_summary_limit(tmp_path: Path) -> None:
    n_samples = 120
    n_features = 8
    rng = np.random.default_rng(123)
    timestamps = np.arange(n_samples, dtype=np.int64) * 12 * 60 * 60
    features = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)).astype(np.float32),
        columns=[f"feature_{idx}" for idx in range(n_features)],
        index=pd.Index(timestamps, name="timestamp"),
    )
    label_values = rng.normal(size=n_samples).astype(np.float32)
    label_values[-1] = np.nan
    labels = pd.DataFrame({"return_1": label_values}, index=features.index)
    features_path = tmp_path / "features.h5"
    labels_path = tmp_path / "labels.h5"
    meta_path = tmp_path / "meta.json"
    _write_features_h5(features_path, features)
    _write_labels_h5(labels_path, labels)
    _write_meta_json(meta_path, list(features.columns))

    report = _orchestrator().analyze(
        features_path=str(features_path),
        labels_path=str(labels_path),
        meta_path=str(meta_path),
        config_override={"feature_filter": {"max_features": 3}},
    )

    assert report["metadata"]["feature_count_original"] == n_features
    assert report["metadata"]["feature_count_filtered"] == 3
    assert report["metadata"]["truncation_mode"] == "preview"
    assert len(report["summary_table"]) <= 3


@pytest.mark.slow
def test_feature_filter_45000_columns_stable_sorted_subset() -> None:
    n_features = 45_000
    columns = [f"feature_{idx:05d}" for idx in range(n_features)]
    features = pd.DataFrame(
        np.ones((1, n_features), dtype=np.float32),
        columns=columns,
    )
    reversed_features = features.loc[:, columns[::-1]]

    first, _metadata, first_info = _orchestrator()._apply_feature_filter(
        features,
        metadata={},
        feature_filter=FeatureFilterSchema(max_features=30),
    )
    second, _metadata, second_info = _orchestrator()._apply_feature_filter(
        reversed_features,
        metadata={},
        feature_filter=FeatureFilterSchema(max_features=30),
    )

    assert first_info["feature_count_original"] == n_features
    assert first_info["feature_count_filtered"] == 30
    assert second_info["feature_count_filtered"] == 30
    assert _sha_columns(list(first.columns)) == _sha_columns(list(second.columns))
