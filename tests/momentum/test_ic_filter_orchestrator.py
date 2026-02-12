import json
from typing import Optional
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig, load_ic_config
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.core.exceptions import InsufficientDataError, InvalidInputError


def _write_features_h5(
    path: Path, features_df: pd.DataFrame, metadata_json: Optional[dict] = None
) -> None:
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
        if metadata_json:
            group.attrs["metadata_json"] = json.dumps(metadata_json, ensure_ascii=True)


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


def _write_meta_json(path: Path, features: list[str]) -> None:
    meta = {
        name: {
            "name": name,
            "category": "trend",
            "layer": 1,
            "data_source": "close",
        }
        for name in features
    }
    meta["symbol"] = "BTCUSDT"
    meta["timeframe"] = "12h"
    meta["case_id"] = "BTCUSDT_12h"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=True), encoding="utf-8")


def test_ic_filter_orchestrator_analyze(tmp_path: Path):
    """驗證 analyze 端到端輸出與報告結構。"""
    np.random.seed(42)
    n_samples = 120
    n_features = 8
    features = pd.DataFrame(
        np.random.randn(n_samples, n_features).astype(np.float32),
        columns=[f"feature_{i}" for i in range(n_features)],
        index=pd.Index(np.arange(n_samples), name="timestamp"),
    )
    labels = pd.DataFrame(
        {"label": np.random.randn(n_samples).astype(np.float32)},
        index=features.index,
    )

    features_path = tmp_path / "features.h5"
    labels_path = tmp_path / "labels.h5"
    meta_path = tmp_path / "meta.json"
    _write_features_h5(features_path, features)
    _write_labels_h5(labels_path, labels)
    _write_meta_json(meta_path, list(features.columns))

    config = load_ic_config()
    orchestrator = ICFilterOrchestrator(config)

    report = orchestrator.analyze(
        features_path=str(features_path),
        labels_path=str(labels_path),
        meta_path=str(meta_path),
    )

    assert "summary_table" in report
    assert "filter_log" in report
    assert report["metadata"]["total_features_input"] == n_features
    assert report["metadata"]["total_features_output"] >= 0

    refilter_report = orchestrator.refilter({"icir_min": -1.0})
    assert refilter_report["metadata"]["total_features_input"] == n_features


def test_event_filter_fallback(tmp_path: Path):
    """事件數不足時應回退 Global Mode。"""
    np.random.seed(7)
    n_samples = 120
    features = pd.DataFrame(
        np.random.randn(n_samples, 5).astype(np.float32),
        columns=[f"feature_{i}" for i in range(5)],
        index=pd.Index(np.arange(n_samples), name="timestamp"),
    )
    labels = pd.DataFrame(
        {"label": np.random.randn(n_samples).astype(np.float32)},
        index=features.index,
    )

    features_path = tmp_path / "features.h5"
    labels_path = tmp_path / "labels.h5"
    meta_path = tmp_path / "meta.json"
    _write_features_h5(features_path, features)
    _write_labels_h5(labels_path, labels)
    _write_meta_json(meta_path, list(features.columns))

    config_override = {
        "event_filter": {
            "enabled": True,
            "query": "feature_0 > 1000",
            "min_events": 30,
            "sample_size_tiers": {"low_confidence": 30},
        }
    }

    config = load_ic_config()
    orchestrator = ICFilterOrchestrator(load_ic_config())
    report = orchestrator.analyze(
        features_path=str(features_path),
        labels_path=str(labels_path),
        meta_path=str(meta_path),
        config_override=config_override,
    )

    event_info = report["metadata"].get("event_filter", {})
    assert event_info.get("tier") == "insufficient"


def test_refilter_without_cache_raises():
    """未先 analyze 時 refilter 應拋錯。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    with pytest.raises(ValueError):
        orchestrator.refilter({"icir_min": 0.0})


def test_get_top_features_empty_report():
    """空報告時回空結果。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    assert orchestrator.get_top_features() == []
    assert orchestrator.get_filtered_features().empty


def test_get_top_features_empty_summary_table():
    """summary_table 為空時回空結果。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    orchestrator._report = {"summary_table": []}

    assert orchestrator.get_top_features() == []


def test_validate_input_errors():
    """輸入驗證錯誤分支。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    with pytest.raises(InvalidInputError):
        orchestrator._validate_input(pd.DataFrame(), None, {})

    small_df = pd.DataFrame({"f1": np.ones(10, dtype=np.float32)})
    with pytest.raises(InsufficientDataError):
        orchestrator._validate_input(small_df, None, {})

    bad_df = pd.DataFrame({"f1": ["a"] * 100})
    with pytest.raises(InvalidInputError):
        orchestrator._validate_input(bad_df, None, {})

    labels_df = pd.DataFrame({"label": ["x"] * 100})
    with pytest.raises(InvalidInputError):
        orchestrator._validate_input(pd.DataFrame({"f1": [1.0] * 100}, dtype=float), labels_df, {})

    meta = {"f1": {"name": "f1", "category": "trend"}}
    with pytest.raises(InvalidInputError):
        orchestrator._validate_input(pd.DataFrame({"f1": [1.0] * 100}, dtype=np.float32), None, meta)


def test_select_label_series_branches():
    """標籤選擇分支。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    config = load_ic_config()

    with pytest.raises(InvalidInputError):
        orchestrator._select_label_series(pd.DataFrame(), config)

    labels_df = pd.DataFrame({"label": [1.0, 2.0]})
    assert orchestrator._select_label_series(labels_df, config).name == "label"

    labels_df = pd.DataFrame({"return_5": [1.0, 2.0], "return_3": [0.5, 1.0]})
    assert orchestrator._select_label_series(labels_df, config).name == "return_5"


def test_build_correlation_payload_empty():
    """空相關矩陣回傳空 payload。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    payload = orchestrator._build_correlation_payload(pd.DataFrame())
    assert payload == {"features": [], "matrix": []}


def test_collect_ic_decay_warnings_and_metadata():
    """IC Decay 警示與報告 Metadata 合併。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    ic_decay = {
        "f1": {"fit_warning": True, "fit_warning_reason": "low_r2"},
        "f2": {"fit_warning": True, "fit_warning_reason": "low_variance"},
    }

    warnings = orchestrator._collect_ic_decay_warnings(ic_decay)
    assert warnings

    features_df = pd.DataFrame({"f1": [1.0, 2.0]}, dtype=np.float32)
    meta = {"warnings": ["existing"]}
    report_meta = orchestrator._build_report_metadata(features_df, None, meta, {}, ic_decay)
    assert "existing" in report_meta["warnings"]


def test_stage5_statistical_validation_adjusted_p_threshold():
    """adjusted_p_threshold 應覆蓋 p_value_max。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    config = load_ic_config()
    features_df = pd.DataFrame({"f1": [0.1, 0.2, 0.15, 0.25, 0.3]}, dtype=np.float32)
    label_series = pd.Series([0.1, 0.2, 0.1, 0.2, 0.1], index=features_df.index)
    ic_results = {
        "rolling_ic": {"f1": {"window_2": [0.1, 0.2, 0.15]}},
        "icir": {"f1": {"icir": 0.1, "ic_mean": 0.1, "ic_hit_rate": 1.0}},
        "ic_decay": {},
    }
    event_info = {"tier": "sufficient", "adjusted_p_threshold": 0.2}

    result = orchestrator._stage5_statistical_validation(
        features_df, label_series, ic_results, config, event_info
    )

    assert "summary_table" in result


def test_apply_config_override_rejects_non_dict():
    """config_override 非 dict 時拋錯。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    with pytest.raises(InvalidInputError):
        orchestrator._apply_config_override("bad")


def test_passes_threshold_inverse_and_nan():
    """Threshold 檢查邏輯。"""
    assert ICFilterOrchestrator._passes_threshold(None, 1.0) is False
    assert ICFilterOrchestrator._passes_threshold(0.5, 1.0) is False
    assert ICFilterOrchestrator._passes_threshold(0.5, 1.0, inverse=True) is True


def test_load_hdf5_and_meta_errors(tmp_path: Path):
    """HDF5 與 meta 讀取錯誤分支。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    with pytest.raises(FileNotFoundError):
        orchestrator._load_features_hdf5(str(tmp_path / "missing.h5"))

    with pytest.raises(FileNotFoundError):
        orchestrator._load_labels_hdf5(str(tmp_path / "missing.h5"))

    with pytest.raises(FileNotFoundError):
        orchestrator._load_meta_json(str(tmp_path / "missing.json"))

    assert orchestrator._load_labels_hdf5("") is None


def test_report_progress_callback_errors():
    """progress_callback 例外應被吞掉。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    def _boom(_payload):
        raise RuntimeError("boom")

    orchestrator._progress_callback = _boom
    orchestrator._report_progress(1, "test", 0.1, "msg")


def test_get_top_features_sorted_and_report_access():
    """Top N 排序與報告存取。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    orchestrator._report = {
        "summary_table": [
            {"feature_name": "f1", "icir": 0.1},
            {"feature_name": "f2", "icir": 0.9},
        ]
    }

    top = orchestrator.get_top_features(n=1, sort_by="icir")
    assert top[0]["feature_name"] == "f2"
    assert orchestrator.get_report() == orchestrator._report


def test_get_filtered_features_returns_copy():
    """精選特徵回傳 copy。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    df = pd.DataFrame({"a": [1.0, 2.0]}, dtype=np.float32)
    orchestrator._filtered_features_df = df

    returned = orchestrator.get_filtered_features()
    assert returned.equals(df)
    assert returned is not df


def test_stage0_ingestion_uses_meta_and_reindexes_labels(tmp_path: Path):
    """metadata_json 與 labels reindex 分支。"""
    features = pd.DataFrame(
        {
            "f1": np.random.randn(120).astype(np.float32),
            "nan_col": [np.nan] * 110 + [1.0] * 10,
        },
        index=pd.Index(np.arange(120), name="timestamp"),
    )
    labels = pd.DataFrame(
        {"label": np.random.randn(120).astype(np.float32)},
        index=pd.Index(np.arange(1000, 1120), name="timestamp"),
    )

    meta = {
        "f1": {"name": "f1", "category": "trend", "layer": 1, "data_source": "close"},
        "nan_col": {"name": "nan_col", "category": "trend", "layer": 1, "data_source": "close"},
    }

    features_path = tmp_path / "features.h5"
    labels_path = tmp_path / "labels.h5"
    _write_features_h5(features_path, features, metadata_json=meta)
    _write_labels_h5(labels_path, labels)

    orchestrator = ICFilterOrchestrator(load_ic_config())
    features_df, labels_df, metadata, stage0_log = orchestrator._stage0_ingestion(
        str(features_path), str(labels_path), None
    )

    assert "nan_col" in stage0_log["removed_nan_features"]
    assert "nan_col" not in features_df.columns
    assert "nan_col" not in metadata
    assert labels_df.index.equals(features_df.index)


def test_validate_input_missing_metadata_feature():
    """缺少特徵 metadata 應拋錯。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    features_df = pd.DataFrame({"f1": [1.0] * 100}, dtype=np.float32)
    metadata = {"f2": {"name": "f2", "category": "trend", "layer": 1}}

    with pytest.raises(InvalidInputError):
        orchestrator._validate_input(features_df, None, metadata)


def test_stage2_label_generation_with_kline_reader(tmp_path: Path):
    """缺 labels 時改用 kline_reader 產生。"""
    class _DummyReader:
        def read_klines(self, _symbol, _timeframe):
            return pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=pd.RangeIndex(3))

    config = load_ic_config()
    config_data = config.model_dump()
    config_data["global_settings"]["default_horizon"] = 999
    config = ICConfig.model_validate(config_data)
    orchestrator = ICFilterOrchestrator(load_ic_config())
    metadata = {"symbol": "BTCUSDT", "timeframe": "12h"}

    label_series, labels_df = orchestrator._stage2_label_generation(
        None, metadata, config, _DummyReader()
    )

    assert label_series is not None
    assert labels_df.shape[1] == 1


def test_stage2_label_generation_missing_reader_raises():
    """無 labels 與 reader 時應拋錯。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    with pytest.raises(InvalidInputError):
        orchestrator._stage2_label_generation(None, {}, load_ic_config(), None)


def test_stage2_label_generation_missing_close_raises():
    """raw_data 缺 close 欄位時應拋錯。"""
    class _DummyReader:
        def read_klines(self, _symbol, _timeframe):
            return pd.DataFrame({"open": [1.0, 2.0, 3.0]}, index=pd.RangeIndex(3))

    orchestrator = ICFilterOrchestrator(load_ic_config())
    metadata = {"symbol": "BTCUSDT", "timeframe": "12h"}

    with pytest.raises(InvalidInputError):
        orchestrator._stage2_label_generation(None, metadata, load_ic_config(), _DummyReader())


def test_stage3_event_filter_uses_raw_data():
    """事件過濾應使用 kline_reader 的 raw_data。"""
    class _DummyReader:
        def read_klines(self, _symbol, _timeframe):
            values = np.arange(50, dtype=float)
            return pd.DataFrame({"close": values}, index=pd.Index(values.astype(int)))

    config = load_ic_config()
    config_data = config.model_dump()
    config_data["event_filter"].update(
        {
            "enabled": True,
            "query": "close > 10",
            "min_events": 1,
        }
    )
    config = ICConfig.model_validate(config_data)
    orchestrator = ICFilterOrchestrator(load_ic_config())
    features_df = pd.DataFrame({"f1": np.arange(50, dtype=float)}, index=pd.Index(range(50)))
    label = pd.Series(np.arange(50, dtype=float) / 10.0, index=features_df.index)

    filtered_features, filtered_label, info = orchestrator._stage3_event_filter(
        features_df, label, {"symbol": "BTCUSDT", "timeframe": "12h"}, config, _DummyReader()
    )

    assert info["mode"] == "query"
    assert filtered_features.index.tolist() == list(range(11, 50))
    assert filtered_label.index.tolist() == list(range(11, 50))


def test_stage4_ic_calculation_with_kline_reader():
    """IC 計算含 decay/regime 分支。"""
    from types import SimpleNamespace

    class _DummyReader:
        def read_klines(self, _symbol, _timeframe):
            return pd.DataFrame(
                {"close": np.linspace(1.0, 2.0, 120)},
                index=pd.date_range("2024-01-01", periods=120, freq="D"),
            )

    config = SimpleNamespace(
        global_settings=SimpleNamespace(default_method="spearman"),
        ic_calculation=SimpleNamespace(
            rolling_windows=[5],
            rolling_stride=1,
            ic_decay_horizons=[1, 2],
            grouped_analysis={
                "by_year": False,
                "by_quarter": False,
                "by_regime": False,
                "by_category": False,
                "by_data_source": False,
                "by_layer": False,
                "method": "spearman",
            },
        ),
        report=SimpleNamespace(include_decay_analysis=True, include_regime_analysis=True),
        labels=SimpleNamespace(return_type="simple"),
    )
    orchestrator = ICFilterOrchestrator(load_ic_config())
    features_df = pd.DataFrame(
        np.random.randn(120, 2).astype(np.float32),
        columns=["f1", "f2"],
    )
    label = pd.Series(np.random.randn(120).astype(np.float32))

    results = orchestrator._stage4_ic_calculation(
        features_df,
        label,
        {"symbol": "BTCUSDT", "timeframe": "12h"},
        config,
        _DummyReader(),
    )

    assert "ic_decay" in results
    assert "grouped_ic" in results


def test_select_label_series_single_and_fallback():
    """單欄位與 fallback 分支。"""
    config = load_ic_config()
    config_data = config.model_dump()
    config_data["global_settings"]["default_horizon"] = 999
    config = ICConfig.model_validate(config_data)
    orchestrator = ICFilterOrchestrator(config)

    labels_df = pd.DataFrame({"only": [1.0, 2.0]})
    assert orchestrator._select_label_series(labels_df, config).name == "only"

    labels_df = pd.DataFrame({"return_1": [1.0, 2.0], "return_2": [1.5, 2.5]})
    assert orchestrator._select_label_series(labels_df, config).name == "return_1"


def test_apply_thresholds_missing_and_long_short():
    """缺 feature_name 與 long_short_spread 分支。"""
    config = load_ic_config()
    config_data = config.model_dump()
    config_data["thresholds"].update(
        {
            "ic_mean_min": 0.0,
            "icir_min": 0.0,
            "ic_hit_rate_min": 0.5,
            "monotonicity_score_min": 0.0,
            "coverage_min": 0.5,
        }
    )
    config_data["thresholds"]["long_short_spread"].update({"enabled": True, "min_spread": 0.1})
    config = ICConfig.model_validate(config_data)
    orchestrator = ICFilterOrchestrator(config)

    summary_table = [
        {"ic_mean": 0.1},
        {
            "feature_name": "f1",
            "ic_mean": 0.1,
            "icir": 0.1,
            "p_value": 0.01,
            "ic_hit_rate": 0.4,
            "monotonicity_score": 0.1,
            "coverage": 0.6,
            "long_short_spread": 0.2,
        },
        {
            "feature_name": "f2",
            "ic_mean": 0.1,
            "icir": 0.1,
            "p_value": 0.01,
            "ic_hit_rate": 0.6,
            "monotonicity_score": 0.1,
            "coverage": 0.4,
            "long_short_spread": 0.2,
        },
        {
            "feature_name": "f3",
            "ic_mean": 0.1,
            "icir": 0.1,
            "p_value": 0.01,
            "ic_hit_rate": 0.6,
            "monotonicity_score": 0.1,
            "coverage": 0.6,
            "long_short_spread": 0.05,
        },
    ]

    _, log = orchestrator._apply_thresholds(summary_table, config.thresholds, 0.05)
    assert "f1" in log["removed_features"]["ic_hit_rate"]
    assert "f2" in log["removed_features"]["coverage"]
    assert "f3" in log["removed_features"]["long_short_spread"]


def test_collect_ic_decay_warnings_empty_and_non_dict():
    """空或非 dict 結果應回空。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    assert orchestrator._collect_ic_decay_warnings({"f1": 123}) == []
    assert orchestrator._collect_ic_decay_warnings({"f1": {"fit_warning": False}}) == []


def test_filter_feature_metadata_empty():
    """空 metadata 應回空 dict。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    assert orchestrator._filter_feature_metadata({}) == {}


def test_resolve_case_id_and_filtered_path_default():
    """case_id 與 filtered path 預設值。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    assert orchestrator._resolve_case_id({}) == "ic_gatekeeper"
    assert orchestrator._resolve_filtered_path({}).endswith("filtered_features.h5")


def test_load_features_hdf5_edge_cases(tmp_path: Path):
    """features HDF5 例外與預設分支。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    empty_path = tmp_path / "empty.h5"
    with h5py.File(empty_path, "w"):
        pass
    with pytest.raises(InvalidInputError):
        orchestrator._load_features_hdf5(str(empty_path))

    missing_features_path = tmp_path / "missing_features.h5"
    with h5py.File(missing_features_path, "w") as file:
        file.create_group("group")
    with pytest.raises(InvalidInputError):
        orchestrator._load_features_hdf5(str(missing_features_path))

    no_timestamp_path = tmp_path / "no_timestamp.h5"
    with h5py.File(no_timestamp_path, "w") as file:
        group = file.create_group("group")
        group.create_dataset("features", data=np.random.randn(3, 2))
    features_df, metadata = orchestrator._load_features_hdf5(str(no_timestamp_path))
    assert isinstance(features_df.index, pd.RangeIndex)
    assert features_df.columns.tolist() == ["feature_0", "feature_1"]
    assert metadata == {}

    bad_meta_path = tmp_path / "bad_meta.h5"
    with h5py.File(bad_meta_path, "w") as file:
        group = file.create_group("group")
        group.create_dataset("features", data=np.random.randn(3, 1))
        group.attrs["metadata_json"] = "{bad json"
    _, metadata = orchestrator._load_features_hdf5(str(bad_meta_path))
    assert metadata == {}


def test_load_labels_hdf5_edge_cases(tmp_path: Path):
    """labels HDF5 例外與預設分支。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    empty_path = tmp_path / "labels_empty.h5"
    with h5py.File(empty_path, "w"):
        pass
    with pytest.raises(InvalidInputError):
        orchestrator._load_labels_hdf5(str(empty_path))

    missing_labels_path = tmp_path / "labels_missing.h5"
    with h5py.File(missing_labels_path, "w") as file:
        file.create_group("group")
    with pytest.raises(InvalidInputError):
        orchestrator._load_labels_hdf5(str(missing_labels_path))

    simple_labels_path = tmp_path / "labels_simple.h5"
    with h5py.File(simple_labels_path, "w") as file:
        group = file.create_group("group")
        group.create_dataset("labels", data=np.array([1.0, 2.0, 3.0]))
    labels_df = orchestrator._load_labels_hdf5(str(simple_labels_path))
    assert labels_df.shape == (3, 1)
    assert labels_df.columns.tolist() == ["label"]


def test_load_meta_json_empty_path():
    """meta_path 為空時回空 dict。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    assert orchestrator._load_meta_json("") == {}


def test_select_first_group_and_read_names(tmp_path: Path):
    """select_first_group 與 read_names 分支。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())

    empty_path = tmp_path / "no_keys.h5"
    with h5py.File(empty_path, "w") as file:
        assert orchestrator._select_first_group(file) is None

    group_path = tmp_path / "group_only.h5"
    with h5py.File(group_path, "w") as file:
        file.create_group("group")
        assert orchestrator._select_first_group(file) is not None

    dataset_path = tmp_path / "dataset_only.h5"
    with h5py.File(dataset_path, "w") as file:
        file.create_dataset("data", data=[1, 2, 3])
        assert orchestrator._select_first_group(file) is None

    names_path = tmp_path / "names.h5"
    with h5py.File(names_path, "w") as file:
        group = file.create_group("group")
        group.attrs["names"] = np.array([1, 2], dtype=np.int64)
        names = orchestrator._read_names(group, "names")
        assert names == ["1", "2"]
