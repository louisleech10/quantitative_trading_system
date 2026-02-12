"""PSI Calculator Tests - PSI 計算器測試"""

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.model_validation.psi_calculator import PSICalculator


def test_compute_psi_and_classify():
    """PSI 計算與分類"""
    rng = np.random.default_rng(42)
    baseline = pd.Series(rng.normal(0, 1, 1000))
    comparison = pd.Series(rng.normal(0.5, 1.2, 1000))

    calculator = PSICalculator()
    psi_value = calculator.compute_psi(baseline, comparison)

    assert psi_value >= 0.0
    stability = calculator.classify_psi(psi_value)
    assert stability in {"stable", "slight_shift", "significant_shift", "unknown"}


def test_compute_all_features():
    """批次 PSI 計算"""
    rng = np.random.default_rng(7)
    X_train = pd.DataFrame({
        "f1": rng.normal(0, 1, 500),
        "f2": rng.normal(0, 1, 500),
    })
    X_test = pd.DataFrame({
        "f1": rng.normal(0.4, 1, 500),
        "f2": rng.normal(0, 1.3, 500),
    })

    calculator = PSICalculator()
    results = calculator.compute_all_features_psi(X_train, X_test)

    assert "f1" in results
    assert "f2" in results
    assert "psi" in results["f1"]
    assert "stability" in results["f1"]


def test_compute_psi_edge_cases(monkeypatch):
    """PSI 邊界與錯誤分支"""
    calculator = PSICalculator()

    baseline = pd.Series([], dtype=float)
    comparison = pd.Series([1.0, 2.0])
    assert np.isnan(calculator.compute_psi(baseline, comparison))

    baseline = pd.Series([1.0, 1.0, 1.0, 1.0])
    comparison = pd.Series([1.0, 1.0, 1.0, 1.0])
    assert calculator.compute_psi(baseline, comparison) == 0.0

    def fake_quantile(*args, **kwargs):
        raise ValueError("bad quantile")

    monkeypatch.setattr(pd.Series, "quantile", fake_quantile)
    baseline = pd.Series([1.0, 2.0, 3.0])
    comparison = pd.Series([1.0, 2.0, 3.0])
    assert np.isnan(calculator.compute_psi(baseline, comparison))


def test_classify_psi_unknown():
    """PSI 未知分類"""
    assert PSICalculator.classify_psi(np.nan) == "unknown"
    assert PSICalculator.classify_psi(0.05) == "stable"
    assert PSICalculator.classify_psi(0.2) == "slight_shift"
    assert PSICalculator.classify_psi(0.3) == "significant_shift"
