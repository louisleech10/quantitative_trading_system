import json
import logging
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import (
    ICFilterOrchestrator,
    _build_holdout_split_plan,
    _derive_stage_masks,
    _resolve_effective_label_horizon,
    _resolve_expected_freq,
    _resolve_label_horizon_from_column,
    _resolve_metadata_symbol_allowlist,
)
from momentum.core.exceptions import InvalidInputError
from momentum.core.contracts import TimestampDiscontinuityError


KLINE_CACHE_PATH = Path("data_cache/feature_klines/kline_cache.h5")


def _real_btc_1h_features(limit: int = 300) -> pd.DataFrame:
    with h5py.File(KLINE_CACHE_PATH, "r") as file:
        data = file["BTCUSDT/1h/data"][:limit]
    return pd.DataFrame(
        {
            "open": data["open"].astype("float64"),
            "high": data["high"].astype("float64"),
            "low": data["low"].astype("float64"),
            "close": data["close"].astype("float64"),
            "volume": data["volume"].astype("float64"),
        },
        index=pd.Index(data["timestamp"].astype("int64"), name="timestamp"),
    )


def _labels_from_close(features_df: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    labels = features_df["close"].pct_change(periods=horizon).shift(-horizon)
    return pd.DataFrame({f"return_{horizon}": labels.astype("float64")}, index=features_df.index)


def _metadata(feature_names: list[str]) -> dict:
    meta = {
        name: {"name": name, "category": "price", "layer": 1}
        for name in feature_names
    }
    meta["symbol"] = "BTCUSDT"
    meta["timeframe"] = "1h"
    return meta


def _write_ic_inputs(
    tmp_path: Path,
    features_df: pd.DataFrame,
    labels_df: pd.DataFrame,
) -> tuple[Path, Path, Path]:
    features_path = tmp_path / "features.h5"
    labels_path = tmp_path / "labels.h5"
    meta_path = tmp_path / "meta.json"
    str_dtype = h5py.string_dtype(encoding="utf-8")
    with h5py.File(features_path, "w") as file:
        group = file.create_group("BTCUSDT/1h")
        group.create_dataset("features", data=features_df.to_numpy(dtype=np.float32))
        group.create_dataset("timestamps", data=features_df.index.to_numpy(dtype=np.int64))
        group.create_dataset(
            "feature_names",
            data=np.array(features_df.columns.tolist(), dtype=object),
            dtype=str_dtype,
        )
    with h5py.File(labels_path, "w") as file:
        group = file.create_group("BTCUSDT/1h")
        group.create_dataset("labels", data=labels_df.to_numpy(dtype=np.float32))
        group.create_dataset("timestamps", data=labels_df.index.to_numpy(dtype=np.int64))
        group.create_dataset(
            "label_names",
            data=np.array(labels_df.columns.tolist(), dtype=object),
            dtype=str_dtype,
        )
    meta_path.write_text(json.dumps(_metadata(list(features_df.columns))), encoding="utf-8")
    return features_path, labels_path, meta_path


def test_resolve_expected_freq() -> None:
    assert _resolve_expected_freq({"timeframe": "4h"}) == pd.Timedelta("4h")

    with pytest.raises(ValueError):
        _resolve_expected_freq({"timeframe": "1H"})


def test_metadata_symbol_required() -> None:
    with pytest.raises(ValueError):
        _resolve_metadata_symbol_allowlist({"timeframe": "1h"})


def test_metadata_symbol_outside_allowlist_blocked() -> None:
    with pytest.raises(ValueError):
        _resolve_metadata_symbol_allowlist(
            {"symbol": "ETH", "timeframe": "1h"},
            allowed_symbols={"BTC"},
        )


def test_icconfig_new_fields_default_off() -> None:
    config = ICConfig()

    # 三方數據簽核 PASS 後預設開啟（2026-06-26 使用者定；flag 只當逃生口）
    assert config.ic_train_test_split is True
    assert config.oos_test_size == 0.2
    assert config.embargo == 0
    assert config.min_test_rows >= max(config.ic_calculation.rolling_windows)


def test_analyze_builds_holdout() -> None:
    features_df = _real_btc_1h_features()
    config = ICConfig(ic_train_test_split=True, min_test_rows=20)
    expected_freq = _resolve_expected_freq({"timeframe": "1h"})

    result = _build_holdout_split_plan(
        features_df,
        config,
        "BTCUSDT",
        expected_freq,
        purge_gap=5,
    )

    assert isinstance(result, tuple)
    train_plan, test_plan = result
    assert train_plan.index_kind == "positional"
    assert test_plan.index_kind == "positional"
    assert set(train_plan.row_index).isdisjoint(set(test_plan.row_index))
    assert int(test_plan.row_index[0]) > int(train_plan.row_index[-1])
    assert train_plan.time_bounds[0] < train_plan.time_bounds[1] < test_plan.time_bounds[0]


def test_holdout_purge_covers_horizon() -> None:
    features_df = _real_btc_1h_features()
    config = ICConfig(ic_train_test_split=True, min_test_rows=20)
    horizon = _resolve_effective_label_horizon(config, _labels_from_close(features_df))
    expected_freq = _resolve_expected_freq({"timeframe": "1h"})

    train_plan, test_plan = _build_holdout_split_plan(
        features_df,
        config,
        "BTCUSDT",
        expected_freq,
        purge_gap=horizon,
    )

    split_point = int(np.floor((1.0 - config.oos_test_size) * len(features_df)))
    assert int(test_plan.row_index[0]) - split_point == horizon
    assert train_plan.purge_gap == horizon
    with pytest.raises(ValueError):
        _build_holdout_split_plan(
            features_df,
            config,
            "BTCUSDT",
            expected_freq,
            purge_gap=horizon - 1,
        )


def test_purge_uses_effective_not_default() -> None:
    features_df = _real_btc_1h_features()
    config = ICConfig(
        ic_train_test_split=True,
        min_test_rows=20,
        labels={"horizons": [13]},
    )
    expected_freq = _resolve_expected_freq({"timeframe": "1h"})

    train_plan, test_plan = _build_holdout_split_plan(
        features_df,
        config,
        "BTCUSDT",
        expected_freq,
        purge_gap=13,
    )

    assert _resolve_effective_label_horizon(config, _labels_from_close(features_df, 13)) == 13
    assert train_plan.purge_gap == 13
    assert test_plan.purge_gap == 13


def test_analyze_split_gap_blocked() -> None:
    features_df = _real_btc_1h_features().drop(index=_real_btc_1h_features().index[100])
    config = ICConfig(ic_train_test_split=True, min_test_rows=20)

    with pytest.raises(TimestampDiscontinuityError):
        _build_holdout_split_plan(
            features_df,
            config,
            "BTCUSDT",
            _resolve_expected_freq({"timeframe": "1h"}),
            purge_gap=5,
        )


def test_split_valid_passes() -> None:
    features_df = _real_btc_1h_features()
    config = ICConfig(ic_train_test_split=True, min_test_rows=20)

    train_plan, test_plan = _build_holdout_split_plan(
        features_df,
        config,
        "BTCUSDT",
        _resolve_expected_freq({"timeframe": "1h"}),
        purge_gap=5,
    )

    assert len(train_plan.row_index) > 0
    assert len(test_plan.row_index) > 0


def test_mask_survives_event_filter() -> None:
    features_df = _real_btc_1h_features()
    config = ICConfig(ic_train_test_split=True, min_test_rows=20)
    train_plan, test_plan = _build_holdout_split_plan(
        features_df,
        config,
        "BTCUSDT",
        _resolve_expected_freq({"timeframe": "1h"}),
        purge_gap=5,
    )
    filtered_index = features_df.drop(index=features_df.index[[10, 20, 30, 250]]).index

    train_mask, test_mask = _derive_stage_masks(train_plan, test_plan, filtered_index)

    assert not bool(np.any(train_mask & test_mask))
    assert train_mask.sum() < len(train_plan.row_index)
    assert test_mask.sum() < len(test_plan.row_index)


def test_pipeline_order_split_before_preprocessing(tmp_path: Path) -> None:
    features_df = _real_btc_1h_features()
    labels_df = _labels_from_close(features_df)
    features_path, labels_path, meta_path = _write_ic_inputs(tmp_path, features_df, labels_df)
    orchestrator = ICFilterOrchestrator(ICConfig(min_test_rows=20))
    calls: list[str] = []

    def stage1(features: pd.DataFrame, metadata: dict, fit_mask=None):
        calls.append("stage1")
        assert fit_mask is not None
        assert int(fit_mask.sum()) == int(metadata["ic_train_test_split"]["train_rows"])
        return features, {"fit_mask_rows": int(fit_mask.sum())}

    orchestrator._stage1_preprocessing = stage1
    orchestrator._stage4_ic_calculation = lambda *args, **kwargs: {
        "label_series": labels_df.iloc[:, 0],
        "icir": {},
        "rolling_ic": {},
        "ic_decay": {},
        "grouped_ic": {},
    }
    orchestrator._stage5_statistical_validation = lambda *args, **kwargs: {
        "summary_table": [],
        "passed_features": [],
        "threshold_log": {},
        "monotonicity": {},
        "coverage": {},
        "turnover": {},
    }
    orchestrator._stage6_redundancy = lambda *args, **kwargs: {
        "filtered_df": pd.DataFrame(index=features_df.index),
        "correlation_matrix": pd.DataFrame(),
        "diversification_metrics": {},
        "redundancy_log": {},
    }
    orchestrator._stage7_report = lambda *args, **kwargs: {
        "metadata": args[1],
        "summary_table": [],
    }

    report = orchestrator.analyze(
        str(features_path),
        str(labels_path),
        str(meta_path),
        config_override={"ic_train_test_split": True, "min_test_rows": 20},
    )

    assert calls == ["stage1"]
    assert report["metadata"]["ic_train_test_split"]["index_kind"] == "positional"


def test_effective_horizon_resolution() -> None:
    config = ICConfig(global_settings={"default_horizon": 5}, labels={"horizons": [13]})

    assert _resolve_effective_label_horizon(config, None) == 13


def test_horizon_resolver_uses_return_column_before_default_m7(caplog: pytest.LogCaptureFixture) -> None:
    """M7 receipt: reverting column parsing to default_horizon makes purge_gap assertions fail."""
    features_df = _real_btc_1h_features()
    labels_df = _labels_from_close(features_df, 5)
    config = ICConfig(
        ic_train_test_split=True,
        min_test_rows=20,
        global_settings={"default_horizon": 1},
    )
    expected_freq = _resolve_expected_freq({"timeframe": "1h"})

    assert _resolve_label_horizon_from_column("return_5", config) == 5
    with caplog.at_level(logging.INFO):
        assert _resolve_effective_label_horizon(config, labels_df) == 5
    matching_records = [
        record
        for record in caplog.records
        if getattr(record, "horizon_source", None) == "column_parse"
    ]
    assert matching_records
    assert getattr(matching_records[-1], "selected_label_column") == "return_5"
    assert getattr(matching_records[-1], "effective_horizon") == 5

    train_plan, test_plan = _build_holdout_split_plan(
        features_df,
        config,
        "BTCUSDT",
        expected_freq,
        purge_gap=5,
        labels_df=labels_df,
    )

    split_point = int(np.floor((1.0 - config.oos_test_size) * len(features_df)))
    assert int(test_plan.row_index[0]) - split_point == 5
    assert train_plan.purge_gap == 5
    assert test_plan.purge_gap == 5
    with pytest.raises(ValueError, match="purge_gap"):
        _build_holdout_split_plan(
            features_df,
            config,
            "BTCUSDT",
            expected_freq,
            purge_gap=1,
            labels_df=labels_df,
        )


def test_horizon_resolver_rejects_unconvertible_unit_column() -> None:
    config = ICConfig()

    with pytest.raises(InvalidInputError, match="unsupported unit"):
        _resolve_label_horizon_from_column("label_return_1d", config)
