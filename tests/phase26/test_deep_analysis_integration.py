import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import DeepAnalysisReport
from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator


def _build_orchestrator() -> ICFilterOrchestrator:
    config = ICConfig()
    orchestrator = ICFilterOrchestrator(config)

    n_samples = 180
    index = pd.date_range("2024-01-01", periods=n_samples, freq="12h")
    rng = np.random.default_rng(42)

    features_df = pd.DataFrame(
        {
            "feat_1": rng.normal(size=n_samples),
            "feat_2": rng.normal(size=n_samples),
            "feat_3": rng.normal(size=n_samples),
            "feat_4": rng.normal(size=n_samples),
        },
        index=index,
        dtype=float,
    )
    labels = pd.Series(
        0.03 * features_df["feat_1"] + rng.normal(scale=0.02, size=n_samples),
        index=index,
        name="future_return",
        dtype=float,
    )

    rolling_ic = {
        name: {"30": (0.02 * features_df[name].rolling(20).mean().fillna(0.0)).tolist()}
        for name in features_df.columns
    }

    orchestrator._ic_cache = {
        "features_df": features_df,
        "label_series": labels,
        "metadata": {},
        "icir": {name: {"icir": 0.1} for name in features_df.columns},
        "rolling_ic": rolling_ic,
        "ic_decay": {},
        "grouped_ic": {},
        "event_info": {},
        "stage0_log": {},
        "preproc_log": {},
    }
    orchestrator._monotonicity_cache = {name: {} for name in features_df.columns}
    orchestrator._filtered_features_df = features_df[["feat_1", "feat_2", "feat_3"]]
    orchestrator._report = {
        "summary_table": [
            {"feature_name": "feat_1", "ic_mean": 0.05},
            {"feature_name": "feat_2", "ic_mean": 0.03},
            {"feature_name": "feat_3", "ic_mean": 0.02},
        ],
        "turnover_analysis": {
            "feat_1": {"quantile_turnover": 0.2},
            "feat_2": {"quantile_turnover": 0.3},
            "feat_3": {"quantile_turnover": 0.4},
        },
    }
    return orchestrator


def test_run_deep_analysis_generates_report_and_progress():
    orchestrator = _build_orchestrator()
    progress_events = []

    report = orchestrator.run_deep_analysis(progress_callback=progress_events.append)

    assert isinstance(report, DeepAnalysisReport)
    assert report.total_modules == 10
    assert report.completed_count >= 1
    assert "factor_returns" in report.results
    assert len(progress_events) > 0
    assert all("module_name" in event for event in progress_events)


def test_module_failure_is_isolated(monkeypatch):
    orchestrator = _build_orchestrator()

    def _fail(*args, **kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr(orchestrator, "_run_trend_analysis", _fail)

    report = orchestrator.run_deep_analysis(force_modules=["trend_analysis", "factor_returns"])

    assert report.module_summary["factor_returns"] == "completed"
    assert report.module_summary["trend_analysis"] == "skipped"
    assert any(err.module_name == "trend_analysis" for err in report.deep_analysis_errors)


def test_cache_hit_and_force_modules_recompute(monkeypatch):
    orchestrator = _build_orchestrator()
    call_count = {"factor_return": 0}
    original = orchestrator._run_factor_return

    def _wrapped(*args, **kwargs):
        call_count["factor_return"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(orchestrator, "_run_factor_return", _wrapped)

    orchestrator.run_deep_analysis(force_modules=["factor_returns"])
    orchestrator.run_deep_analysis()
    orchestrator.run_deep_analysis(force_modules=["factor_returns"])

    assert call_count["factor_return"] == 2


def test_refilter_clears_deep_analysis_cache(monkeypatch):
    orchestrator = _build_orchestrator()
    orchestrator._deep_analysis_cache["dummy"] = DeepAnalysisReport()

    monkeypatch.setattr(
        orchestrator,
        "_stage5_statistical_validation",
        lambda *args, **kwargs: {
            "summary_table": [],
            "passed_features": [],
            "threshold_log": {},
            "monotonicity": {},
            "coverage": {},
            "turnover": {},
        },
    )
    monkeypatch.setattr(
        orchestrator,
        "_stage6_redundancy",
        lambda *args, **kwargs: {
            "filtered_df": pd.DataFrame(index=orchestrator._ic_cache["features_df"].index),
            "redundancy_log": {},
            "correlation_matrix": pd.DataFrame(),
            "diversification_metrics": {},
        },
    )
    monkeypatch.setattr(orchestrator, "_stage7_report", lambda *args, **kwargs: {})

    orchestrator.refilter({})

    assert len(orchestrator._deep_analysis_cache) == 0
