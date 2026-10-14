import numpy as np
import pandas as pd

from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
from momentum.Analysis.bootstrap_estimator import BootstrapEstimator
from momentum.Analysis.expectancy_calculator import ExpectancyCalculator
from momentum.Analysis.cross_symbol_validator import CrossSymbolValidator


def _build_dataset(n_samples: int = 400, n_features: int = 8, seed: int = 42):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)),
        columns=[f"feature_{i}" for i in range(n_features)]
    )
    logits = X["feature_0"] * 1.5 + X["feature_1"] * -1.2 + rng.normal(scale=0.5, size=n_samples)
    y = (logits > 0).astype(int)
    return X, y


def _train_analyzer():
    X, y = _build_dataset()
    analyzer = XGBoostAnalyzer(params={"n_estimators": 80, "max_depth": 4, "learning_rate": 0.08})
    analyzer.train_model(X, y)
    return analyzer, X, y


def test_precision_at_k():
    analyzer, X, y = _train_analyzer()
    result = analyzer.calculate_precision_at_k(X, y, k_values=[1, 5, 10])
    assert 1 in result.precision_at_k
    assert 5 in result.threshold_at_k
    assert result.sample_count_at_k[10] > 0
    assert 0.0 <= result.threshold_at_k[1] <= 1.0


def test_bootstrap_confidence_interval_auc():
    analyzer, X, y = _train_analyzer()
    y_pred = analyzer.model.predict_proba(X)[:, 1]
    estimator = BootstrapEstimator()
    ci = estimator.bootstrap_confidence_interval(
        y_true=y,
        y_pred_proba=y_pred,
        metric="auc",
        n_bootstrap=200,
        confidence=0.9
    )
    assert 0.0 <= ci.point_estimate <= 1.0
    assert ci.ci_lower <= ci.ci_upper


def test_expectancy_calculator():
    analyzer, X, y = _train_analyzer()
    y_pred = analyzer.model.predict_proba(X)[:, 1]
    price_changes = (y * 0.02) + (1 - y) * -0.01
    calculator = ExpectancyCalculator()
    result = calculator.estimate_expectancy(
        price_changes=price_changes,
        predicted_proba=y_pred,
        threshold=0.6
    )
    assert result.total_trades >= 0
    assert result.expectancy <= 0.05


def test_permutation_importance():
    analyzer, X, y = _train_analyzer()
    result = analyzer.calculate_permutation_importance(X, y, n_repeats=3)
    assert len(result.items) == X.shape[1]
    assert all(item.std >= 0 for item in result.items)


def test_fold_importance_stability():
    analyzer, X, y = _train_analyzer()
    stability = analyzer.calculate_fold_importance_stability(X, y, cv_folds=3)
    total_features = len(analyzer.feature_names)
    assert len(stability.feature_cv) == total_features
    assert len(stability.stable_features) + len(stability.unstable_features) == total_features


def test_cross_symbol_validator():
    X_source, y_source = _build_dataset(n_samples=300, seed=1)
    X_target, y_target = _build_dataset(n_samples=200, seed=2)

    validator = CrossSymbolValidator(params={"n_estimators": 60, "max_depth": 4})
    result = validator.validate_cross_symbol(
        X_train_source=X_source.values,
        y_train_source=y_source,
        X_test_target=X_target.values,
        y_test_target=y_target,
        source_symbol="BTCUSDT",
        target_symbol="ETHUSDT"
    )

    assert result.verdict in {"good", "moderate", "poor", "unknown"}


def test_expectancy_calculator_hand_calc_exact():
    """TESTREG 4.2 純增：固定小輸入手算 win_rate／avg_win／avg_loss／expectancy 精確比對。

    手算：proba≥0.6 之交易＝[0.03, -0.01, 0.01, -0.02, 0.0]（0.6 邊界含入、0.05 因 proba 0.2 排除）
    ⇒ total 5；勝（>0）＝0.03、0.01 ⇒ win_rate 0.4、avg_win 0.02；敗（≤0）＝-0.01、-0.02、0.0 ⇒ avg_loss -0.01；
    expectancy＝0.4×0.02＋0.6×(-0.01)＝0.002。模型路徑另以恆等式 expectancy＝交易報酬平均（獨立 oracle）比對。
    """
    calculator = ExpectancyCalculator()
    fixed = calculator.estimate_expectancy(
        price_changes=np.array([0.03, -0.01, 0.01, -0.02, 0.05, 0.0]),
        predicted_proba=np.array([0.9, 0.7, 0.6, 0.65, 0.2, 0.8]),
        threshold=0.6,
    )
    analyzer, X, y = _train_analyzer()
    y_pred = analyzer.model.predict_proba(X)[:, 1]
    price_changes = (y * 0.02) + (1 - y) * -0.01
    model_res = calculator.estimate_expectancy(price_changes=price_changes, predicted_proba=y_pred, threshold=0.6)
    traded = np.asarray(price_changes, dtype=float)[np.asarray(y_pred) >= 0.6]
    assert fixed.total_trades == 5 and np.allclose([fixed.win_rate, fixed.avg_win, fixed.avg_loss, fixed.expectancy], [0.4, 0.02, -0.01, 0.002], rtol=0, atol=1e-12) and model_res.total_trades == traded.size and np.isclose(model_res.expectancy, float(traded.mean()), rtol=0, atol=1e-12)
