from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from momentum.Analysis.ic_engine import ICEngine, ICReadError
from momentum.core.contracts import LayerExecutionResult, LayerStatus
from momentum.FeatureEngineering.feature_config import PreprocessingConfig
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


def _make_factory() -> FeatureFactory:
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._current_symbol = "SYNTHETIC"
    factory._current_timeframe = "fixture"
    factory._current_config_hash = "ic-first-test"
    factory._current_raw_data = None
    factory._cgsa_registry = None
    factory.layer_results = {}
    return factory


def _make_config(*, ic_first_pipeline: bool = False) -> Any:
    preprocessing = PreprocessingConfig(
        enabled=True,
        mode="replace",
        ic_first_pipeline=ic_first_pipeline,
        winsorization={
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.10, 0.90],
            "apply_to": "all",
        },
        fractional_differencing={"enabled": False},
        adf_differencing={"enabled": False},
        rank_transform={"enabled": True, "window": 3, "apply_to": "all"},
        gaussian_normalize={"enabled": False, "apply_to": "all"},
        adaptive_zscore={"enabled": True, "windows": [3], "apply_to": "all"},
    )
    return SimpleNamespace(preprocessing=preprocessing)


def _expected_pre_ic(frame: pd.DataFrame, config: Any) -> pd.DataFrame:
    preprocessing_config: Dict[str, Any] = config.preprocessing.model_dump()
    preprocessing_config["rank_transform"]["enabled"] = False
    preprocessing_config["adaptive_zscore"]["enabled"] = False
    preprocessing_config["gaussian_normalize"]["enabled"] = False
    preprocessing_config["adf_differencing"]["enabled"] = False
    return FeaturePreprocessor(preprocessing_config).transform(frame)


def _assert_frame_allclose(left: pd.DataFrame, right: pd.DataFrame) -> None:
    assert list(left.columns) == list(right.columns)
    assert left.index.equals(right.index)
    assert left.isna().equals(right.isna())
    np.testing.assert_allclose(
        left.to_numpy(dtype=np.float32),
        right.to_numpy(dtype=np.float32),
        rtol=1e-5,
        atol=1e-8,
        equal_nan=True,
    )


def _selection_metadata() -> Dict[str, Any]:
    return {
        "label_horizon": "1_bar_forward_return",
        "selection_window": {"start_pos": 0, "end_pos": 6},
        "split_id": "train_fold_0",
    }


def _ok_layer(data: pd.DataFrame) -> LayerExecutionResult:
    return LayerExecutionResult(
        data=data,
        status=LayerStatus.ok,
        failed_engines=(),
        reason=None,
        configured_engines=1,
        present_engines=1,
        required_engines=0,
        dependency_error=False,
    )


def _healthy_layer_results(row_index: pd.DatetimeIndex) -> Dict[str, LayerExecutionResult]:
    frame = pd.DataFrame({"x": np.ones(len(row_index), dtype=np.float32)}, index=row_index)
    return {f"Layer {idx}": _ok_layer(frame) for idx in range(1, 7)}


def _ic_fixture(
    tmp_path,
    symbol: str = "SYNTHETIC",
    tf: str = "1h",
    config_hash: str = "cfg_ic",
) -> Dict[str, Any]:
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))
    row_index = pd.date_range("2026-01-01", periods=6, freq="h")
    groups = {
        "group_alpha": pd.DataFrame(
            {
                "alpha": np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=np.float32),
                "beta": np.array([1.0, 3.0, 2.0, 5.0, 4.0, 6.0], dtype=np.float32),
            },
            index=row_index,
        ),
        "group_gamma": pd.DataFrame(
            {
                "gamma": np.array([2.0, 1.0, 2.0, 1.0, 2.0, 1.0], dtype=np.float32),
            },
            index=row_index,
        ),
    }
    raw_dir = storage.write_raw(
        symbol,
        tf,
        config_hash,
        groups,
        row_index=row_index,
        layer_results=_healthy_layer_results(row_index),
    )
    label = pd.Series(
        np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=np.float32),
        name="forward_return",
    )
    return {
        "storage": storage,
        "reader": reader,
        "groups": groups,
        "raw_dir": raw_dir,
        "label": label,
        "symbol": symbol,
        "tf": tf,
        "config_hash": config_hash,
    }


def _run_ic_selection(
    fixture: Dict[str, Any],
    *,
    threshold: float = 0.95,
    allow_partial_ic: bool = False,
):
    engine = ICEngine({"methods": ["spearman"]})
    return engine.compute_ic_from_l7_raw(
        fixture["symbol"],
        fixture["tf"],
        fixture["config_hash"],
        fixture["label"],
        feature_reader=fixture["reader"],
        ic_threshold=threshold,
        allow_partial_ic=allow_partial_ic,
        method="spearman",
        **_selection_metadata(),
    )


def _load_selected_payload(result) -> Dict[str, Any]:
    return json.loads(Path(result.selected_path).read_text(encoding="utf-8"))


def test_routing(monkeypatch) -> None:
    monkeypatch.setenv("FFACT_IC_FIRST_PIPELINE", "1")
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    factory = _make_factory()
    config = _make_config()
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, 3.0, 100.0, 5.0],
            "beta": [10.0, 9.0, 8.0, 7.0, 6.0],
            "gamma": [5.0, 5.0, 5.0, 5.0, 5.0],
        }
    )

    pre_ic = factory._layer6_5_preprocessing(frame, config)
    expected_pre_ic = _expected_pre_ic(frame, config)
    _assert_frame_allclose(pre_ic, expected_pre_ic)

    legacy = factory._layer6_5_legacy(frame, config)
    assert not np.allclose(
        pre_ic.to_numpy(dtype=np.float32),
        legacy.to_numpy(dtype=np.float32),
        equal_nan=True,
    )

    selected_features: List[str] = ["alpha", "gamma"]
    post_ic = factory._layer6_5_preprocessing(
        frame,
        config,
        selected_features=selected_features,
    )

    assert list(post_ic.columns) == selected_features
    assert post_ic.index.equals(frame.index)
    assert "beta" not in post_ic.columns


def test_config_flag_routes_to_pre_ic_without_env(monkeypatch) -> None:
    monkeypatch.delenv("FFACT_IC_FIRST_PIPELINE", raising=False)
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    factory = _make_factory()
    config = _make_config(ic_first_pipeline=True)
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, 3.0, 100.0, 5.0],
            "beta": [10.0, 9.0, 8.0, 7.0, 6.0],
            "gamma": [5.0, 5.0, 5.0, 5.0, 5.0],
        }
    )

    pre_ic = factory._layer6_5_preprocessing(frame, config)
    expected_pre_ic = _expected_pre_ic(frame, config)
    _assert_frame_allclose(pre_ic, expected_pre_ic)

    legacy = factory._layer6_5_legacy(frame, config)
    assert not np.allclose(
        pre_ic.to_numpy(dtype=np.float32),
        legacy.to_numpy(dtype=np.float32),
        equal_nan=True,
    )


def test_ic_first_legacy_fallback(monkeypatch) -> None:
    monkeypatch.setenv("FFACT_IC_FIRST_PIPELINE", "0")
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    factory = _make_factory()
    config = _make_config()
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, 3.0, 100.0, 5.0],
            "beta": [10.0, 9.0, 8.0, 7.0, 6.0],
            "gamma": [5.0, 5.0, 5.0, 5.0, 5.0],
        }
    )

    result = factory._layer6_5_preprocessing(
        frame,
        config,
        selected_features=["alpha"],
    )
    expected = factory._layer6_5_legacy(frame, config)

    assert list(result.columns) == list(frame.columns)
    _assert_frame_allclose(result, expected)


def test_transform_selected_only_processes_ic_features(monkeypatch) -> None:
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    config = _make_config()
    preprocessor = FeaturePreprocessor(config.preprocessing.model_dump())
    groups = {
        "group_alpha": pd.DataFrame(
            {
                "alpha": np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
                "beta": np.array([4.0, 3.0, 2.0, 1.0], dtype=np.float32),
            }
        ),
        "group_gamma": pd.DataFrame(
            {"gamma": np.array([2.0, 2.0, 2.0, 2.0], dtype=np.float32)}
        ),
    }

    result = preprocessor.transform_selected(
        ["alpha", "gamma"],
        groups,
        config.preprocessing,
    )

    assert set(result) == {"group_alpha", "group_gamma"}
    assert list(result["group_alpha"].columns) == ["alpha"]
    assert list(result["group_gamma"].columns) == ["gamma"]
    assert "beta" not in result["group_alpha"].columns


def test_ic_empty_selection(tmp_path) -> None:
    config = _make_config()
    preprocessor = FeaturePreprocessor(config.preprocessing.model_dump())
    processed_groups = preprocessor.transform_selected(
        [],
        {
            "group_alpha": pd.DataFrame(
                {"alpha": np.array([1.0, 2.0, 3.0], dtype=np.float32)}
            )
        },
        config.preprocessing,
    )
    assert processed_groups == {}

    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))
    storage.write_processed("SYNTHETIC", "1h", "cfg_empty_selection", processed_groups)
    manifest = reader.load_manifest_v2(
        "SYNTHETIC",
        "1h",
        "cfg_empty_selection",
        artifact_kind="processed",
    )
    assert manifest["artifacts"]["processed"]["quality_status"] == "empty_selection"
    assert manifest["artifacts"]["processed"]["total_features"] == 0


def test_l7_schema_version_metadata(tmp_path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))
    symbol = "SYNTHETIC"
    tf = "1h"
    config_hash = "cfg_schema"
    raw_groups = {
        "group_alpha": pd.DataFrame(
            {
                "alpha": np.array([1.0, 2.0, np.nan], dtype=np.float32),
                "beta": np.array([4.0, 5.0, 6.0], dtype=np.float32),
            }
        ),
        "group_gamma": pd.DataFrame(
            {"gamma": np.array([7.0, 8.0, 9.0], dtype=np.float32)}
        ),
    }
    processed_groups = {
        "selected": pd.DataFrame(
            {"alpha_rank": np.array([0.5, 1.0, np.nan], dtype=np.float32)}
        )
    }

    raw_dir = storage.write_raw(symbol, tf, config_hash, raw_groups)
    processed_dir = storage.write_processed(symbol, tf, config_hash, processed_groups)

    assert raw_dir == tmp_path / "features" / symbol / tf / config_hash / "raw"
    assert processed_dir == tmp_path / "features" / symbol / tf / config_hash / "processed"

    manifest = reader.load_manifest_v2(symbol, tf, config_hash, artifact_kind="raw")
    assert manifest["complete"] is True
    assert manifest["artifacts"]["raw"]["schema_version"] == "raw_v2"
    assert manifest["artifacts"]["raw"]["total_features"] == 3
    assert manifest["artifacts"]["processed"]["schema_version"] == "processed_v2"
    assert manifest["artifacts"]["processed"]["total_features"] == 1

    raw_schema = pq.read_schema(str(raw_dir / "group_alpha.parquet"))
    processed_schema = pq.read_schema(str(processed_dir / "selected.parquet"))
    assert raw_schema.metadata[b"schema_version"] == b"raw_v2"
    assert processed_schema.metadata[b"schema_version"] == b"processed_v2"

    streamed_raw = dict(reader.stream_groups_v2(symbol, tf, config_hash, artifact_kind="raw"))
    assert set(streamed_raw) == {"group_alpha", "group_gamma"}
    loaded_processed = reader.load_columns_v2(
        symbol,
        tf,
        config_hash,
        ["alpha_rank"],
        artifact_kind="processed",
    )
    np.testing.assert_allclose(
        loaded_processed["alpha_rank"].to_numpy(dtype=np.float32),
        processed_groups["selected"]["alpha_rank"].to_numpy(dtype=np.float32),
        equal_nan=True,
    )


def test_feature_run_dir_and_manifest_atomicity(tmp_path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))
    symbol = "SYNTHETIC"
    tf = "12h"
    config_hash = "cfg_atomic"
    initial_groups = {
        "group_alpha": pd.DataFrame({"alpha": np.array([1.0, 2.0], dtype=np.float32)})
    }
    replacement_groups = {
        "group_alpha": pd.DataFrame({"alpha": np.array([10.0, 20.0], dtype=np.float32)})
    }

    assert storage.feature_run_dir(symbol, tf, config_hash) == tmp_path / "features" / symbol / tf / config_hash

    storage.write_raw(symbol, tf, config_hash, initial_groups)
    storage.write_raw(symbol, tf, config_hash, replacement_groups)

    run_dir = tmp_path / "features" / symbol / tf / config_hash
    assert not list(run_dir.glob(".tmp-*"))
    assert not list(run_dir.glob(".previous-*"))

    manifest_path = run_dir / "feature_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["complete"] is True
    assert manifest["artifacts"]["raw"]["complete"] is True

    loaded = reader.load_columns_v2(symbol, tf, config_hash, ["alpha"], artifact_kind="raw")
    np.testing.assert_allclose(
        loaded["alpha"].to_numpy(dtype=np.float32),
        replacement_groups["group_alpha"]["alpha"].to_numpy(dtype=np.float32),
    )

    with pytest.raises(ValueError, match="write_raw requires non-empty"):
        storage.write_raw(symbol, tf, "cfg_empty_raw", {})

    processed_dir = storage.write_processed(symbol, tf, "cfg_empty_processed", {})
    assert processed_dir.exists()
    processed_manifest = reader.load_manifest_v2(
        symbol,
        tf,
        "cfg_empty_processed",
        artifact_kind="processed",
    )
    assert processed_manifest["artifacts"]["processed"]["quality_status"] == "empty_selection"
    assert processed_manifest["artifacts"]["processed"]["total_features"] == 0
    assert list(reader.stream_groups_v2(symbol, tf, "cfg_empty_processed", artifact_kind="processed")) == []

    temp_only_dir = tmp_path / "features" / "TEMP" / "1h" / "cfg_tmp" / ".tmp-raw-orphan" / "raw"
    temp_only_dir.mkdir(parents=True)
    table = pa.Table.from_pandas(pd.DataFrame({"orphan": [1.0]}), preserve_index=False)
    pq.write_table(table, str(temp_only_dir / "group.parquet"))
    with pytest.raises(FileNotFoundError):
        reader.load_manifest_v2("TEMP", "1h", "cfg_tmp", artifact_kind="raw")


def test_old_parquet_no_metadata(tmp_path) -> None:
    base_dir = tmp_path / "features"
    symbol = "LEGACY"
    config_hash = "cfg_legacy"
    legacy_dir = base_dir / symbol / config_hash
    legacy_dir.mkdir(parents=True)
    frame = pd.DataFrame({"legacy_alpha": np.array([1.0, 2.0, 3.0], dtype=np.float32)})
    legacy_path = legacy_dir / "legacy_group.parquet"
    frame.to_parquet(legacy_path, index=False)
    manifest = {
        "version": "7.0",
        "symbol": symbol,
        "config_hash": config_hash,
        "total_features": 1,
        "total_rows": 3,
        "groups": {
            "legacy_group": {
                "file": "legacy_group.parquet",
                "columns": ["legacy_alpha"],
                "column_count": 1,
                "dtype": "float32",
            }
        },
    }
    (legacy_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    schema_metadata = pq.read_schema(str(legacy_path)).metadata or {}
    assert b"schema_version" not in schema_metadata

    reader = FeatureReader(str(base_dir))
    loaded_manifest = reader.load_manifest_v2(symbol, "1h", config_hash, artifact_kind="raw")
    assert loaded_manifest["legacy_format"] is True
    loaded = reader.load_columns_v2(symbol, "1h", config_hash, ["legacy_alpha"], artifact_kind="raw")
    np.testing.assert_allclose(
        loaded["legacy_alpha"].to_numpy(dtype=np.float32),
        frame["legacy_alpha"].to_numpy(dtype=np.float32),
    )


def test_ic_selection_stability(tmp_path) -> None:
    fixture = _ic_fixture(tmp_path)
    engine = ICEngine({"methods": ["spearman"]})
    legacy_frame = pd.concat(fixture["groups"].values(), axis=1)
    legacy_scores = engine.compute_ic(legacy_frame, fixture["label"], method="spearman")

    result = _run_ic_selection(fixture, threshold=0.95)
    payload = _load_selected_payload(result)

    assert result.quality_status == "complete"
    assert result.skipped_groups == []
    assert payload["quality_status"] == "complete"
    assert payload["frozen_gate_eligible"] is True
    assert result.selected == ["alpha"]

    max_abs_diff = max(
        abs(float(result.ic_scores[name]) - float(legacy_scores[name]))
        for name in legacy_scores
    )
    assert max_abs_diff <= 0.01
    assert set(result.selected) == {
        name for name, value in legacy_scores.items() if np.isfinite(value) and abs(value) >= 0.95
    }


def test_ic_group_read_failure_fail_closed(tmp_path) -> None:
    fixture = _ic_fixture(tmp_path)
    broken_path = fixture["raw_dir"] / "group_gamma.parquet"
    broken_path.unlink()

    with pytest.raises(ICReadError, match="Failed to read L7 raw group"):
        _run_ic_selection(fixture)

    selected_path = Path(fixture["reader"].feature_run_dir(
        fixture["symbol"],
        fixture["tf"],
        fixture["config_hash"],
    )) / f"ic_selected_features_{fixture['symbol']}_{fixture['tf']}.json"
    assert not selected_path.exists()


def test_ic_group_read_failure_partial_mode(tmp_path) -> None:
    fixture = _ic_fixture(tmp_path)
    broken_path = fixture["raw_dir"] / "group_gamma.parquet"
    broken_path.unlink()

    result = _run_ic_selection(fixture, allow_partial_ic=True)
    payload = _load_selected_payload(result)

    assert result.quality_status == "partial"
    assert payload["quality_status"] == "partial"
    assert payload["frozen_gate_eligible"] is False
    assert payload["skipped_groups"] == [str(broken_path)]
    assert result.selected == ["alpha"]


def test_ic_cross_symbol_isolation(tmp_path) -> None:
    first = _ic_fixture(tmp_path, symbol="SYN_A", tf="1h", config_hash="cfg_shared")
    second = _ic_fixture(tmp_path, symbol="SYN_B", tf="1h", config_hash="cfg_shared")

    first_result = _run_ic_selection(first)
    second_result = _run_ic_selection(second)
    first_payload = _load_selected_payload(first_result)
    second_payload = _load_selected_payload(second_result)

    assert first_result.selected_path != second_result.selected_path
    assert first_payload["symbol"] == "SYN_A"
    assert second_payload["symbol"] == "SYN_B"
    assert Path(first_result.selected_path).name == "ic_selected_features_SYN_A_1h.json"
    assert Path(second_result.selected_path).name == "ic_selected_features_SYN_B_1h.json"


def test_ic_selection_no_oos_leakage(tmp_path) -> None:
    fixture = _ic_fixture(tmp_path)
    result = _run_ic_selection(fixture)
    payload = _load_selected_payload(result)

    assert payload["ic_params"]["label_horizon"] == "1_bar_forward_return"
    assert payload["ic_params"]["selection_window"] == {"start_pos": 0, "end_pos": 6}
    assert payload["ic_params"]["split_id"] == "train_fold_0"
    assert payload["data_fingerprint"]["label_horizon"] == "1_bar_forward_return"
    assert payload["data_fingerprint"]["selection_window"] == {"start_pos": 0, "end_pos": 6}
    assert payload["data_fingerprint"]["split_id"] == "train_fold_0"

    engine = ICEngine({"methods": ["spearman"]})
    with pytest.raises(ValueError, match="label_horizon"):
        engine.compute_ic_from_l7_raw(
            fixture["symbol"],
            fixture["tf"],
            fixture["config_hash"],
            fixture["label"],
            feature_reader=fixture["reader"],
            ic_threshold=0.95,
            selection_window={"start_pos": 0, "end_pos": 6},
            split_id="train_fold_0",
        )


def test_ic_analysis_service_l7_raw_integration(tmp_path) -> None:
    from api.services.ic_analysis_service import ICAnalysisService

    fixture = _ic_fixture(tmp_path, symbol="API_SYN", tf="12h", config_hash="cfg_service")
    service = ICAnalysisService()
    result = service.compute_ic_from_l7_raw(
        symbol=fixture["symbol"],
        timeframe=fixture["tf"],
        config_hash=fixture["config_hash"],
        label=fixture["label"],
        feature_base_path=str(tmp_path / "features"),
        ic_threshold=0.95,
        method="spearman",
        **_selection_metadata(),
    )

    assert result["selected"] == ["alpha"]
    assert result["quality_status"] == "complete"
    assert Path(result["selected_path"]).name == "ic_selected_features_API_SYN_12h.json"


def test_memory_budget_after_raw_persist(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    factory = _make_factory()
    config = _make_config()
    config.ic_gate_required_available_gb = 0.0
    config.tier_peak_budget_gb = 999.0
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))
    row_index = pd.date_range("2026-01-01", periods=6, freq="h")
    raw_data = pd.DataFrame(
        {"close": np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0], dtype=np.float32)},
        index=row_index,
    )
    factory.layer_results = _healthy_layer_results(row_index)
    layers = [
        pd.DataFrame(
            {
                "alpha": np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=np.float32),
                "beta": np.array([1.0, 3.0, 2.0, 5.0, 4.0, 6.0], dtype=np.float32),
            }
        )
    ]
    label = pd.Series(
        np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=np.float32),
        name="forward_return",
    )

    result = factory.run_ic_first_pipeline(
        "SYNTHETIC",
        "1h",
        config,
        raw_data=raw_data,
        layers=layers,
        config_hash="cfg_pipeline",
        label=label,
        ic_engine=ICEngine({"methods": ["spearman"]}),
        feature_reader=reader,
        storage=storage,
        ic_threshold=0.95,
        label_horizon="1_bar_forward_return",
        selection_window={"start_pos": 0, "end_pos": 6},
        split_id="train_fold_0",
    )

    assert result.metadata["raw_feature_count"] == 2
    assert result.metadata["selected_features"] == ["alpha"]
    assert result.metadata["processed_feature_count"] == 1
    assert result.metadata["memory_budget"]["available_after_gb"] >= 0.0
    assert result.metadata["run_ic_gate_peak_rss_gb"] <= 999.0

    run_dir = storage.feature_run_dir("SYNTHETIC", "1h", "cfg_pipeline")
    assert (run_dir / "raw").exists()
    assert (run_dir / "processed").exists()
    processed = reader.load_columns_v2(
        "SYNTHETIC",
        "1h",
        "cfg_pipeline",
        ["alpha"],
        artifact_kind="processed",
    )
    assert list(processed.columns) == ["alpha"]
