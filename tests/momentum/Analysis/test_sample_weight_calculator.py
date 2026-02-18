import numpy as np
import pandas as pd
import pytest


def test_S1_invalid_half_life(sample_weight_calculator, synthetic_timestamps):
    with pytest.raises(ValueError):
        sample_weight_calculator.compute_time_decay(synthetic_timestamps, half_life=0)


def test_S2_unsorted_timestamps(sample_weight_calculator, synthetic_timestamps):
    ts = synthetic_timestamps.copy()[::-1]
    weights = sample_weight_calculator.compute_time_decay(ts)
    assert len(weights) == len(ts)


def test_S3_zero_returns(sample_weight_calculator):
    returns = np.zeros(100)
    weights = sample_weight_calculator.compute_return_based(returns)
    assert np.allclose(weights, 1.0)


def test_S4_single_class_weight(sample_weight_calculator):
    y = np.ones(100, dtype=int)
    weights = sample_weight_calculator.compute_class_balance(y)
    assert np.allclose(weights, 1.0)


def test_S5_invalid_min_weight():
    from momentum.Analysis.sample_weight_calculator import SampleWeightCalculator

    calc = SampleWeightCalculator(config={"min_weight": 0.5})
    calc.config.min_weight = 1.1
    with pytest.raises(ValueError):
        calc.compute_combined_weights(y=np.array([0, 1, 0]))


def test_S6_tiny_sample(sample_weight_calculator, synthetic_timestamps):
    weights = sample_weight_calculator.compute_combined_weights(
        timestamps=synthetic_timestamps[:8],
        y=np.array([0, 1, 0, 1, 0, 1, 0, 1]),
        strategies=["time_decay", "class_balance"],
    )
    assert len(weights) == 8


def test_S7_no_strategies(sample_weight_calculator):
    weights = sample_weight_calculator.compute_combined_weights(y=np.array([0, 1, 0, 1]), strategies=[])
    assert np.allclose(weights, 1.0)


def test_S8_extreme_label_overlap(sample_weight_calculator, synthetic_timestamps):
    n = 100
    spans = [(0, n)] * 100
    weights = sample_weight_calculator.compute_combined_weights(
        timestamps=synthetic_timestamps[:n],
        label_spans=spans,
        strategies=["uniqueness"],
    )
    assert len(weights) == n


def test_S9_additive_default_coeffs(sample_weight_calculator, synthetic_timestamps):
    y = np.random.binomial(1, 0.3, len(synthetic_timestamps))
    weights = sample_weight_calculator.compute_combined_weights(
        timestamps=synthetic_timestamps,
        y=y,
        strategies=["time_decay", "class_balance"],
        combination="additive",
    )
    assert np.isclose(np.mean(weights), 1.0, atol=1e-6)


def test_S10_nan_timestamps(sample_weight_calculator, synthetic_timestamps):
    ts = synthetic_timestamps.astype("datetime64[ns]").astype(object)
    ts[5] = np.nan
    weights = sample_weight_calculator.compute_time_decay(ts)
    assert len(weights) == len(ts) - 1


def test_time_decay_recent_higher(sample_weight_calculator, synthetic_timestamps):
    weights = sample_weight_calculator.compute_time_decay(synthetic_timestamps)
    assert weights[-1] > weights[0]


def test_class_balance_minority_higher(sample_weight_calculator):
    y = np.array([0] * 90 + [1] * 10)
    weights = sample_weight_calculator.compute_class_balance(y)
    assert np.mean(weights[y == 1]) > np.mean(weights[y == 0])


def test_weight_summary_effective_n(sample_weight_calculator):
    weights = np.array([0.5, 1.0, 1.5, 2.0])
    summary = sample_weight_calculator.get_weight_summary(weights)
    assert 0 < summary["effective_n"] <= summary["n_samples"]
    assert 0 < summary["efficiency_ratio"] <= 1


def test_return_based_weights_mean_is_one(sample_weight_calculator):
    returns = np.linspace(-0.05, 0.07, 200)
    weights = sample_weight_calculator.compute_return_based(returns, method="squared_return")
    assert np.isclose(np.mean(weights), 1.0, atol=1e-6)
    assert np.all(weights > 0)


def test_combined_multiply_weights_mean_is_one(sample_weight_calculator, synthetic_timestamps):
    y = np.array([0, 1] * 1000)
    returns = np.linspace(-0.02, 0.03, 2000)
    weights = sample_weight_calculator.compute_combined_weights(
        timestamps=synthetic_timestamps,
        y=y,
        returns=returns,
        strategies=["time_decay", "class_balance", "return_based"],
        combination="multiply",
    )
    assert len(weights) == 2000
    assert np.isclose(np.mean(weights), 1.0, atol=1e-6)


def test_uniqueness_weights_mean_is_one(sample_weight_calculator):
    spans = [(i, min(i + 5, 200)) for i in range(0, 200, 2)]
    weights = sample_weight_calculator.compute_uniqueness(label_spans=spans, n_samples=200)
    assert len(weights) == 200
    assert np.isclose(np.mean(weights), 1.0, atol=1e-6)
