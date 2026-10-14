import numpy as np
import pytest

from momentum.Analysis.model_validation.walk_forward_validator import (
    WalkForwardReport,
)
from momentum.factories import create_walk_forward_validator as _create_wfv_additive
from sklearn.metrics import roc_auc_score as _roc_auc_additive


def test_W1_data_too_short(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    result = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X.iloc[:100],
        y=y[:100],
        feature_names=X.columns.tolist(),
        train_size=80,
        test_size=30,
    )
    assert result.error_type == "INSUFFICIENT_DATA"


def test_W2_small_train_window(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=45,
        test_size=80,
    )
    assert isinstance(report, WalkForwardReport)


def test_W3_minimal_periods(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X.iloc[:750],
        y=y[:750],
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert report.n_periods <= 2


def test_W4_single_class_test_period(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    y_mod = y.copy()
    y_mod[505:605] = 1
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y_mod,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
        step_size=100,
    )
    assert any(period.test_auc is None for period in report.period_results)


def test_W5_step_larger_than_test(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
        step_size=150,
    )
    assert report.n_periods >= 1


def test_W6_purge_exceeds_test(synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator

    validator = WalkForwardValidator(config={"purge_gap": 50})
    with pytest.raises(ValueError):
        validator.validate_rolling(model_factory=model_factory, X=X, y=y, feature_names=X.columns.tolist(), train_size=500, test_size=50)


def test_W7_training_failure_single_period(walk_forward_validator, synthetic_binary_data):
    X, y = synthetic_binary_data

    def bad_factory():
        class BadModel:
            def fit(self, X, y):
                raise RuntimeError("boom")

        return BadModel()

    report = walk_forward_validator.validate_rolling(
        model_factory=bad_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert isinstance(report, WalkForwardReport)
    assert report.n_periods == 0


def test_W8_both_modes(synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator

    validator = WalkForwardValidator(config={"mode": "both", "train_size": 500, "test_size": 100})
    result = validator.validate(model_factory=model_factory, X=X, y=y, feature_names=X.columns.tolist())
    assert "rolling" in result and "expanding" in result


def test_W9_all_periods_below_random(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    y_inverse = 1 - y
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y_inverse,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert report.assessment in {"unstable", "moderate", "robust"}


def test_W10_expanding_memory_warning(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_expanding(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        initial_train_size=500,
        test_size=100,
        step_size=200,
    )
    assert isinstance(report, WalkForwardReport)


def test_rolling_basic_metrics(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert report.n_periods >= 3
    assert report.mean_oos_auc >= 0.0
    assert report.assessment in {"robust", "moderate", "unstable"}


def test_validate_default_returns_rolling_key(synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator

    validator = WalkForwardValidator(config={"mode": "rolling", "train_size": 500, "test_size": 100})
    result = validator.validate(model_factory=model_factory, X=X, y=y, feature_names=X.columns.tolist())
    assert "rolling" in result
    assert isinstance(result["rolling"], WalkForwardReport)


def test_validate_expanding_returns_expanding_key(synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator

    validator = WalkForwardValidator(config={"mode": "expanding", "train_size": 500, "test_size": 100})
    result = validator.validate(model_factory=model_factory, X=X, y=y, feature_names=X.columns.tolist())
    assert "expanding" in result
    assert isinstance(result["expanding"], WalkForwardReport)


def test_rolling_report_contains_period_ranges(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
        step_size=100,
    )
    assert isinstance(report, WalkForwardReport)
    assert report.period_results
    first = report.period_results[0]
    assert first.train_end_idx > first.train_start_idx
    assert first.test_end_idx > first.test_start_idx


def test_rolling_feature_stability_has_reasonable_ratio(walk_forward_validator, synthetic_binary_data, model_factory):
    X, y = synthetic_binary_data
    report = walk_forward_validator.validate_rolling(
        model_factory=model_factory,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        train_size=500,
        test_size=100,
    )
    assert isinstance(report, WalkForwardReport)
    assert report.feature_stability
    assert all(0.0 <= value <= 1.0 for value in report.feature_stability.values())


def test_W9_reversed_scorer_is_unstable_with_all_periods_degraded(synthetic_binary_data):
    """W9 實質版：固定反向打分之替身模型 ⇒ 每個 OOS 窗 AUC 皆 < 0.5（以 sklearn 獨立重算比對），
    assessment 必為 unstable、degradation_periods＝全部 period；窗數以 purge／步長手算。"""
    X, y = synthetic_binary_data
    y_arr = np.asarray(y)
    purge, train_n, test_n, step = 7, 500, 100, 100

    def _reverse_scores(frame):
        z = -(frame["feature_0"].to_numpy() * 1.5 - frame["feature_1"].to_numpy() * 0.7)
        return 1.0 / (1.0 + np.exp(-z))

    class _ReversedScorer:
        def fit(self, X_fit, y_fit):
            return self

        def predict_proba(self, X_pred):
            p1 = _reverse_scores(X_pred)
            return np.column_stack([1.0 - p1, p1])

    validator = _create_wfv_additive(config={
        "mode": "rolling", "purge_gap": purge, "train_size": train_n, "test_size": test_n,
    })  # step_size 未給 ⇒ 步長＝test_size＝step
    report = validator.validate(
        model_factory=_ReversedScorer, X=X, y=y_arr, feature_names=X.columns.tolist(),
    )["rolling"]
    expected_n = (len(X) - train_n - purge - test_n) // step + 1
    oracle_auc = []
    for k in range(expected_n):
        lo = k * step + train_n + purge
        oracle_auc.append(_roc_auc_additive(y_arr[lo:lo + test_n], _reverse_scores(X.iloc[lo:lo + test_n])))
    got_auc = [p.test_auc for p in report.period_results]
    assert report.n_periods == expected_n and all(a < 0.5 for a in oracle_auc) and np.allclose(got_auc, oracle_auc, atol=1e-12), \
        f"OOS AUC 與獨立重算不符：got={got_auc} oracle={oracle_auc}"
    assert report.assessment == "unstable" and report.degradation_periods == list(range(expected_n)) \
        and report.oos_hit_rate == 0.0, (report.assessment, report.degradation_periods, report.oos_hit_rate)


def test_walk_forward_purge_gap_separates_train_and_test_in_both_modes(synthetic_binary_data, model_factory):
    """洩漏從嚴：每個 period 之 test_start − train_end 恰等於設定之 purge_gap（rolling 與 expanding），
    且窗起訖與窗數以手算 oracle 逐一比對（expanding 之訓練窗恆自 0 起、train_end < test_start）。"""
    X, y = synthetic_binary_data
    purge = 7
    validator = _create_wfv_additive(config={"mode": "both", "purge_gap": purge, "train_size": 500, "test_size": 100})
    n = len(X)

    both = validator.validate(model_factory=model_factory, X=X, y=y, feature_names=X.columns.tolist())
    rolling = both.get("rolling")
    expanding = both.get("expanding")
    exp_rolling = [(s, s + 500, s + 500 + purge, s + 600 + purge) for s in range(0, n, 100) if s + 600 + purge <= n]
    got_rolling = [(p.train_start_idx, p.train_end_idx, p.test_start_idx, p.test_end_idx) for p in rolling.period_results]
    assert got_rolling == exp_rolling and all(p.test_start_idx - p.train_end_idx == purge for p in rolling.period_results), \
        f"rolling 窗與 purge 間隔不符：{got_rolling[:3]} vs {exp_rolling[:3]}"

    exp_expanding = [(0, e, e + purge, e + purge + 100) for e in range(500, n, 100) if e + purge + 100 <= n]
    got_expanding = [(p.train_start_idx, p.train_end_idx, p.test_start_idx, p.test_end_idx) for p in expanding.period_results]
    assert got_expanding == exp_expanding and all(p.train_end_idx < p.test_start_idx for p in expanding.period_results), \
        f"expanding 窗與 purge 間隔不符：{got_expanding[:3]} vs {exp_expanding[:3]}"
