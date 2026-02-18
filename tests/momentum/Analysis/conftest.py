import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from momentum.factories import (
    create_probability_calibrator,
    create_walk_forward_validator,
    create_sample_weight_calculator,
    create_adversarial_validator,
    create_combinatorial_purged_cv,
    create_learning_curve_analyzer,
)


@pytest.fixture
def synthetic_binary_data():
    np.random.seed(42)
    n = 2000
    n_features = 20
    X = pd.DataFrame(
        np.random.randn(n, n_features),
        columns=[f"feature_{i}" for i in range(n_features)],
    )
    logits = X["feature_0"] * 1.5 - X["feature_1"] * 0.7 + np.random.randn(n) * 0.4
    probs = 1 / (1 + np.exp(-logits))
    y = (probs > np.quantile(probs, 0.6)).astype(int)
    return X, y


@pytest.fixture
def synthetic_predictions():
    np.random.seed(42)
    n = 2000
    y_true = np.random.binomial(1, 0.35, n)
    y_pred = np.clip(y_true * 0.75 + np.random.normal(0, 0.25, n), 0.01, 0.99)
    return y_pred, y_true


@pytest.fixture
def synthetic_timestamps():
    np.random.seed(42)
    n = 2000
    start = pd.Timestamp("2022-01-01")
    return np.array([start + pd.Timedelta(hours=12 * i) for i in range(n)])


@pytest.fixture
def probability_calibrator():
    return create_probability_calibrator()


@pytest.fixture
def walk_forward_validator():
    return create_walk_forward_validator()


@pytest.fixture
def sample_weight_calculator():
    return create_sample_weight_calculator()


@pytest.fixture
def adversarial_validator():
    return create_adversarial_validator()


@pytest.fixture
def combinatorial_purged_cv():
    return create_combinatorial_purged_cv()


@pytest.fixture
def learning_curve_analyzer():
    return create_learning_curve_analyzer()


@pytest.fixture
def model_factory():
    def _factory():
        return LogisticRegression(max_iter=1000)

    return _factory
