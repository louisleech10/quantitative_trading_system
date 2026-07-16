from pathlib import Path
from typing import Optional

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.data_preprocessor import DataPreprocessor
from momentum.Analysis.ic_filter_orchestrator import (
    ICFilterOrchestrator,
    _build_holdout_split_plan,
    _derive_stage_masks,
    _resolve_expected_freq,
)
from api.models.ic_models import ICAnalyzeRequest
from api.services.ic_analysis_service import ICAnalysisService
from momentum.core.contracts import TimestampDiscontinuityError
from momentum.core.contracts import AlignmentViolationError
from tests.momentum.Analysis.test_ic_1a_cut1_split import _write_ic_inputs


KLINE_CACHE_PATH = Path("data_cache/feature_klines/kline_cache.h5")


def _nan_aware_equal(left: object, right: object) -> bool:
    """結構等價；float NaN 視為相等（dict/list 遞迴）。"""
    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            return False
        return all(_nan_aware_equal(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        if len(left) != len(right):
            return False
        return all(_nan_aware_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, float) and isinstance(right, float):
        if np.isnan(left) and np.isnan(right):
            return True
        return left == right
    return left == right


def _real_btc_frame(limit: int = 180) -> pd.DataFrame:
    with h5py.File(KLINE_CACHE_PATH, "r") as file:
        data = file["BTCUSDT/1h/data"][:limit]
    index = pd.Index(data["timestamp"].astype("int64"), name="timestamp")
    close = pd.Series(data["close"].astype("float64"), index=index, name="close")
    returns = close.pct_change().fillna(0.0)
    return pd.DataFrame(
        {
            "trend": returns.rolling(3, min_periods=1).mean(),
            "momentum": returns.rolling(6, min_periods=1).mean(),
        },
        index=index,
    ).fillna(0.0)


def _label(features: pd.DataFrame) -> pd.Series:
    return (
        features["trend"].shift(-1).fillna(0.0)
        + features["momentum"].shift(-2).fillna(0.0)
    ).rename("label")


def _return_label(features: pd.DataFrame, horizon: int = 5) -> pd.Series:
    values = _label(features).astype("float64").copy()
    if horizon > 0:
        values.iloc[-horizon:] = np.nan
    return values.rename(f"return_{horizon}")


def _split_context(features: pd.DataFrame, config: Optional[ICConfig] = None) -> dict:
    active_config = config or _config()
    split_result = _build_holdout_split_plan(
        features,
        active_config,
        "BTCUSDT",
        _resolve_expected_freq({"timeframe": "1h"}),
        purge_gap=int(active_config.global_settings.default_horizon),
    )
    assert isinstance(split_result, tuple)
    train_plan, test_plan = split_result
    train_mask, test_mask = _derive_stage_masks(train_plan, test_plan, features.index)
    return {
        "train_mask": train_mask,
        "test_mask": test_mask,
        "train_plan": train_plan,
        "test_plan": test_plan,
        "effective_horizon": int(active_config.global_settings.default_horizon),
    }


def _config(**overrides) -> ICConfig:
    data = {
        "ic_train_test_split": True,
        "min_test_rows": 20,
        "global": {"default_method": "spearman", "default_horizon": 5},
        "ic_calculation": {
            "rolling_windows": [5],
            "rolling_stride": 1,
            "icir": {"window": 5},
            "grouped_analysis": {
                "by_year": False,
                "by_quarter": False,
                "by_regime": False,
                "by_category": False,
                "by_data_source": False,
                "by_layer": False,
            },
        },
        "thresholds": {
            "ic_mean_min": -1.0,
            "icir_min": -999.0,
            "p_value_max": 1.0,
            "ic_hit_rate_min": 0.0,
            "monotonicity_score_min": 0.0,
            "coverage_min": 0.0,
        },
        "report": {
            "include_decay_analysis": False,
            "include_regime_analysis": False,
        },
    }
    data.update(overrides)
    return ICConfig.model_validate(data)


def test_oos_ic_rolling_warmup() -> None:
    features = _real_btc_frame()
    label = _label(features)
    orchestrator = ICFilterOrchestrator(_config())
    context = _split_context(features, orchestrator._config)

    results = orchestrator._stage4_ic_calculation(
        features,
        label,
        {"symbol": "BTCUSDT", "timeframe": "1h"},
        orchestrator._config,
        None,
        split_context=context,
    )

    test_rows = int(context["test_mask"].sum())
    assert results["scope"] == "test"
    assert len(results["rolling_ic"]["trend"]["window_5"]) == test_rows
    assert results["icir"]["trend"]["ic_mean"] != orchestrator._ic_engine.compute_icir(
        orchestrator._ic_engine.compute_rolling_ic(
            features.loc[context["test_mask"]],
            label.loc[context["test_mask"]],
            [5],
            1,
            "spearman",
        )
    )["trend"]["ic_mean"]


def test_min_test_rows_skipped() -> None:
    features = _real_btc_frame(limit=80)
    label = _label(features)
    config = _config(
        min_test_rows=1,
        ic_calculation={
            "rolling_windows": [30],
            "rolling_stride": 1,
            "icir": {"window": 30},
        }
    )
    orchestrator = ICFilterOrchestrator(config)
    context = _split_context(features, config)

    results = orchestrator._stage4_ic_calculation(
        features,
        label,
        {"symbol": "BTCUSDT", "timeframe": "1h"},
        config,
        None,
        split_context=context,
    )

    assert results["status"] == "skipped"
    assert results["error_type"] == "INSUFFICIENT_DATA"


def test_summary_and_threshold_same_scope() -> None:
    features = _real_btc_frame()
    label = _label(features)
    orchestrator = ICFilterOrchestrator(_config())
    context = _split_context(features, orchestrator._config)
    ic_results = {
        "rolling_ic": {"trend": {"window_5": [0.2, 0.3]}, "momentum": {"window_5": [0.1, 0.2]}},
        "icir": {
            "trend": {"ic_mean": 0.2, "ic_std": 0.1, "icir": 2.0, "ic_hit_rate": 1.0},
            "momentum": {"ic_mean": 0.1, "ic_std": 0.1, "icir": 1.0, "ic_hit_rate": 1.0},
        },
        "ic_decay": {},
    }

    stage5 = orchestrator._stage5_statistical_validation(
        features,
        label,
        ic_results,
        orchestrator._config,
        {},
        split_context=context,
        metadata={"symbol": "BTCUSDT"},
    )

    assert stage5["scope"] == "test"
    assert set(stage5["passed_features"]) == {"trend", "momentum"}
    for row in stage5["summary_table"]:
        assert row["ic_mean"] == ic_results["icir"][row["feature_name"]]["ic_mean"]


def test_stage5_metrics_all_oos() -> None:
    features = _real_btc_frame()
    label = _label(features)
    dirty = features.copy()
    orchestrator = ICFilterOrchestrator(_config())
    context = _split_context(features, orchestrator._config)
    dirty.loc[context["train_mask"], "trend"] = np.nan
    ic_results = {
        "rolling_ic": {"trend": {"window_5": [0.2, 0.3]}, "momentum": {"window_5": [0.1, 0.2]}},
        "icir": {
            "trend": {"ic_mean": 0.2, "ic_std": 0.1, "icir": 2.0, "ic_hit_rate": 1.0},
            "momentum": {"ic_mean": 0.1, "ic_std": 0.1, "icir": 1.0, "ic_hit_rate": 1.0},
        },
        "ic_decay": {},
    }

    clean_stage5 = orchestrator._stage5_statistical_validation(
        features,
        label,
        ic_results,
        orchestrator._config,
        {},
        split_context=context,
        metadata={"symbol": "BTCUSDT"},
    )
    dirty_stage5 = orchestrator._stage5_statistical_validation(
        dirty,
        label,
        ic_results,
        orchestrator._config,
        {},
        split_context=context,
        metadata={"symbol": "BTCUSDT"},
    )

    assert dirty_stage5["coverage"] == clean_stage5["coverage"]
    # B3 turnover/mono scalar 可為 NaN；dict/list == 對 NaN 不成立 → nan-aware 等價
    assert _nan_aware_equal(dirty_stage5["turnover"], clean_stage5["turnover"])
    assert _nan_aware_equal(
        dirty_stage5["summary_table"], clean_stage5["summary_table"]
    )


def test_decay_redundancy_scope_test() -> None:
    features = _real_btc_frame()
    orchestrator = ICFilterOrchestrator(_config())
    context = _split_context(features, orchestrator._config)

    results = orchestrator._stage6_redundancy(
        features,
        ["trend"],
        {"trend": {"icir": 1.0}},
        {},
        split_context=context,
    )

    assert results["scope"] == "test"
    assert results["redundancy_log"]["scope"] == "test"
    assert results["filtered_df"].index.equals(features.index[context["test_mask"]])


def test_purge_label_mutation_does_not_change_test_rolling_ic() -> None:
    features = _real_btc_frame()
    label = _label(features)
    orchestrator = ICFilterOrchestrator(_config())
    context = _split_context(features, orchestrator._config)
    purge_mask = ~(context["train_mask"] | context["test_mask"])
    assert bool(purge_mask.any())

    clean = orchestrator._stage4_ic_calculation(
        features,
        label,
        {"symbol": "BTCUSDT", "timeframe": "1h"},
        orchestrator._config,
        None,
        split_context=context,
    )
    dirty_label = label.copy()
    dirty_label.loc[features.index[purge_mask]] = dirty_label.loc[features.index[purge_mask]] * -999.0
    dirty = orchestrator._stage4_ic_calculation(
        features,
        dirty_label,
        {"symbol": "BTCUSDT", "timeframe": "1h"},
        orchestrator._config,
        None,
        split_context=context,
    )

    assert dirty["rolling_ic"] == clean["rolling_ic"]
    assert dirty["icir"] == clean["icir"]


def test_winsorize_type_branch_uses_train_slice_only() -> None:
    features = _real_btc_frame()
    config = _config()
    context = _split_context(features, config)
    type_like = pd.DataFrame({"type_signal": 0.0}, index=features.index)
    train_values = np.resize(
        np.array([-100.0, 0.0, 100.0], dtype=float),
        int(context["train_mask"].sum()),
    )
    type_like.loc[context["train_mask"], "type_signal"] = train_values
    changed_test = type_like.copy()
    changed_test.loc[context["test_mask"], "type_signal"] = 1_000.0
    preprocessor = DataPreprocessor(
        {
            "winsorization": {
                "enabled": True,
                "method": "percentile",
                "lower_percentile": 1.0,
                "upper_percentile": 99.0,
            },
            "missing_values": {"max_fill_forward": 1, "min_coverage": 0.0},
            "standardize": {"method": "none"},
        }
    )

    clean_df, clean_log = preprocessor.preprocess(
        type_like, fit_mask=context["train_mask"], fit_mode="train_mask"
    )
    dirty_df, dirty_log = preprocessor.preprocess(
        changed_test, fit_mask=context["train_mask"], fit_mode="train_mask"
    )

    assert clean_log["skipped_winsorization"] == ["type_signal"]
    assert dirty_log["skipped_winsorization"] == clean_log["skipped_winsorization"]
    pd.testing.assert_series_equal(
        dirty_df.loc[context["train_mask"], "type_signal"],
        clean_df.loc[context["train_mask"], "type_signal"],
    )


def test_holdout_embargo_delays_test_start() -> None:
    features = _real_btc_frame()
    config = _config(embargo=3)

    train_plan, test_plan = _build_holdout_split_plan(
        features,
        config,
        "BTCUSDT",
        _resolve_expected_freq({"timeframe": "1h"}),
        purge_gap=int(config.global_settings.default_horizon),
    )

    split_point = int(np.floor((1.0 - config.oos_test_size) * len(features)))
    expected_start = split_point + int(config.global_settings.default_horizon) + config.embargo
    assert int(test_plan.row_index[0]) == expected_start
    assert int(test_plan.row_index[0]) - int(train_plan.row_index[-1]) - 1 == (
        int(config.global_settings.default_horizon) + config.embargo
    )


def test_flag_toggles_path(tmp_path: Path) -> None:
    features = _real_btc_frame()
    labels = pd.DataFrame({"return_5": _return_label(features)}, index=features.index)
    features_path, labels_path, meta_path = _write_ic_inputs(tmp_path, features, labels)

    # 預設已 ON（簽核後），off 分支須顯式關閉
    off_orchestrator = ICFilterOrchestrator(
        ICConfig(ic_train_test_split=False, min_test_rows=20)
    )
    off_orchestrator._stage4_ic_calculation = lambda *args, **kwargs: {
        "label_series": labels.iloc[:, 0],
        "icir": {},
        "rolling_ic": {},
        "ic_decay": {},
        "grouped_ic": {},
    }
    off_orchestrator._stage5_statistical_validation = lambda *args, **kwargs: {
        "summary_table": [],
        "passed_features": [],
        "threshold_log": {},
        "monotonicity": {},
        "coverage": {},
        "turnover": {},
    }
    off_orchestrator._stage6_redundancy = lambda *args, **kwargs: {
        "filtered_df": pd.DataFrame(index=features.index),
        "correlation_matrix": pd.DataFrame(),
        "diversification_metrics": {},
        "redundancy_log": {},
    }
    off_orchestrator._stage7_report = lambda *args, **kwargs: {"metadata": args[1]}
    off_report = off_orchestrator.analyze(str(features_path), str(labels_path), str(meta_path))

    on_orchestrator = ICFilterOrchestrator(ICConfig(min_test_rows=20))
    on_orchestrator._stage4_ic_calculation = off_orchestrator._stage4_ic_calculation
    on_orchestrator._stage5_statistical_validation = off_orchestrator._stage5_statistical_validation
    on_orchestrator._stage6_redundancy = off_orchestrator._stage6_redundancy
    on_orchestrator._stage7_report = lambda *args, **kwargs: {"metadata": args[1]}
    on_report = on_orchestrator.analyze(
        str(features_path),
        str(labels_path),
        str(meta_path),
        config_override={"ic_train_test_split": True, "min_test_rows": 20},
    )

    assert "ic_train_test_split" not in off_report["metadata"]
    assert on_report["metadata"]["ic_train_test_split"]["applied"] is True


@pytest.mark.ic_persist_redirect
@pytest.mark.usefixtures("ic_persist_redirect")
def test_fallback_insufficient_data_marks_applied_false(tmp_path: Path) -> None:
    features = _real_btc_frame(limit=120)
    labels = pd.DataFrame({"return_5": _return_label(features)}, index=features.index)
    features_path, labels_path, meta_path = _write_ic_inputs(tmp_path, features, labels)

    report = ICFilterOrchestrator(ICConfig()).analyze(
        str(features_path),
        str(labels_path),
        str(meta_path),
    )

    split_meta = report["metadata"]["ic_train_test_split"]
    assert report["summary_table"]
    assert split_meta["requested"] is True
    assert split_meta["applied"] is False
    assert split_meta["scope"] == "full_sample_legacy"
    assert split_meta["oos_guarantees"] is False
    assert split_meta["reason"] == "insufficient_data"
    assert set(split_meta["details"]) == {"train_rows", "test_rows", "min_test_rows"}
    assert "train_time_bounds" not in split_meta
    assert "test_time_bounds" not in split_meta
    assert report["metadata"].get("scope") != "test"


def test_irregular_timestamps_still_fail_closed(tmp_path: Path) -> None:
    n_rows = 760
    index = pd.Index(np.arange(n_rows, dtype=np.int64), name="timestamp")
    features = pd.DataFrame(
        {
            "trend": np.linspace(0.0, 1.0, n_rows),
            "momentum": np.linspace(1.0, 0.0, n_rows),
        },
        index=index,
    )
    labels = pd.DataFrame({"return_5": _return_label(features)}, index=features.index)
    features_path, labels_path, meta_path = _write_ic_inputs(tmp_path, features, labels)

    with pytest.raises((TimestampDiscontinuityError, AlignmentViolationError)):
        ICFilterOrchestrator(ICConfig()).analyze(
            str(features_path),
            str(labels_path),
            str(meta_path),
        )


@pytest.mark.ic_persist_redirect
@pytest.mark.usefixtures("ic_persist_redirect")
def test_oos_applied_true_when_sufficient(tmp_path: Path) -> None:
    features = _real_btc_frame(limit=760)
    labels = pd.DataFrame({"return_5": _return_label(features)}, index=features.index)
    features_path, labels_path, meta_path = _write_ic_inputs(tmp_path, features, labels)

    report = ICFilterOrchestrator(ICConfig()).analyze(
        str(features_path),
        str(labels_path),
        str(meta_path),
    )

    split_meta = report["metadata"]["ic_train_test_split"]
    assert split_meta["requested"] is True
    assert split_meta["applied"] is True
    assert split_meta["scope"] == "train_test_holdout"
    assert split_meta["oos_guarantees"] is True
    assert report["metadata"]["scope"] == "test"


def test_flag_via_config_override() -> None:
    request = ICAnalyzeRequest(
        features_path="features.h5",
        config_override={"ic_train_test_split": True},
    )

    override = ICAnalysisService()._build_config_override(request)

    assert override["ic_train_test_split"] is True
