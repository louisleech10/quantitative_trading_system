import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.rolling_oos_validator import RollingOOSValidator


def _make_data(n=420):
    rng = np.random.default_rng(123)
    idx = pd.date_range("2024-01-01", periods=n, freq="12h")
    feature = pd.Series(rng.normal(size=n), index=idx)
    labels = pd.Series(feature.values * 0.03 + rng.normal(scale=0.02, size=n), index=idx)
    return feature, labels


def test_validate_success():
    feature, labels = _make_data()
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15, "min_splits": 5})

    result = analyzer.validate(feature, labels)

    assert isinstance(result, dict)
    assert "oos_stability" in result
    assert result["assessment"] in {"robust", "moderate", "overfitting"}


def test_data_too_short_for_oos():
    feature, labels = _make_data(100)
    analyzer = RollingOOSValidator({"train_window": 80, "test_window": 40, "step": 10})

    result = analyzer.validate(feature, labels)

    assert isinstance(result, SkippedResult)


def test_auto_reduce_step_generate_splits():
    analyzer = RollingOOSValidator({"train_window": 100, "test_window": 20, "step": 50, "min_splits": 5})
    splits = analyzer._generate_splits(260)
    assert len(splits) >= 1


def test_validate_batch():
    feature, labels = _make_data()
    features_df = pd.DataFrame({"f1": feature, "f2": feature * 0.8 + 0.1})
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15, "min_splits": 5})

    result = analyzer.validate_batch(features_df, labels, top_n=2)

    assert "features" in result
    assert "summary" in result
    assert len(result["features"]) == 2


def test_no_valid_splits_skip(monkeypatch):
    feature, labels = _make_data(300)
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 40, "step": 20})

    monkeypatch.setattr(analyzer, "_generate_splits", lambda n: [])
    result = analyzer.validate(feature, labels)
    assert isinstance(result, SkippedResult)
    assert result.reason == "no valid splits generated"


def test_all_splits_invalid_skip(monkeypatch):
    feature, labels = _make_data(360)
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15})

    monkeypatch.setattr(analyzer, "_compute_ic", lambda x, y, method: np.nan)
    result = analyzer.validate(feature, labels)
    assert isinstance(result, SkippedResult)
    assert result.reason == "all splits invalid"


def test_validate_with_pearson_path():
    feature, labels = _make_data(420)
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15, "min_splits": 5})
    result = analyzer.validate(feature, labels, method="pearson")
    assert isinstance(result, dict)
    assert "oos_stability" in result


def test_compute_ic_short_and_constant():
    short = RollingOOSValidator._compute_ic(pd.Series([1, 2]), pd.Series([1, 2]), "spearman")
    assert np.isnan(short)

    constant = RollingOOSValidator._compute_ic(pd.Series([1] * 10), pd.Series(np.arange(10)), "spearman")
    assert constant == 0.0


def test_classify_assessment_boundaries():
    analyzer = RollingOOSValidator({
        "assessment_thresholds": {
            "robust_hit_rate": 0.7,
            "robust_max_degradation": 0.3,
            "moderate_hit_rate": 0.5,
            "moderate_max_degradation": 0.5,
        }
    })
    assert analyzer._classify_assessment(0.8, 0.2) == "robust"
    assert analyzer._classify_assessment(0.55, 0.4) == "moderate"
    assert analyzer._classify_assessment(0.4, 0.9) == "overfitting"


def test_validate_batch_with_skipped_feature_summary_counts():
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15, "min_splits": 5})
    f1, labels = _make_data(420)
    f2, _ = _make_data(80)
    features_df = pd.DataFrame({"f1": f1.reindex(labels.index), "f2": f2.reindex(labels.index)})

    result = analyzer.validate_batch(features_df, labels, top_n=2)
    assert result["summary"]["total_validated"] >= 1
    assert result["features"]["f2"].get("skipped", False) is True
