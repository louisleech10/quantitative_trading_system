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
