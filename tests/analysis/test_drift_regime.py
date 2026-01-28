import numpy as np

from momentum.Analysis.drift_analyzer import DriftAnalyzer
from momentum.Analysis.regime_analyzer import RegimeAnalyzer


def test_calculate_psi_stable():
    analyzer = DriftAnalyzer()
    expected = np.linspace(0, 1, 500)
    actual = np.linspace(0, 1, 500)
    psi, _, _, _ = analyzer.calculate_psi(expected, actual, bins=10)
    assert psi < 0.1


def test_calculate_psi_shifted():
    analyzer = DriftAnalyzer()
    rng = np.random.default_rng(42)
    expected = rng.normal(loc=0.0, scale=1.0, size=2000)
    actual = rng.normal(loc=3.0, scale=1.0, size=2000)
    psi, _, _, _ = analyzer.calculate_psi(expected, actual, bins=10)
    assert psi >= 0.1


def test_regime_analysis_insufficient_samples():
    analyzer = RegimeAnalyzer(min_samples=5)
    y_true = np.array([1, 0, 1])
    y_pred = np.array([0.9, 0.1, 0.8])
    phases = ["FEAR", "FEAR", "FEAR"]

    report = analyzer.analyze_by_phase(y_true, y_pred, phases)
    phase_result = report.phase_metrics[0]

    assert phase_result.phase == "FEAR"
    assert phase_result.note == "樣本不足"
    assert phase_result.recommendation.startswith("不建議交易")
