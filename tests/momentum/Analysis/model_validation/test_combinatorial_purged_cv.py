import numpy as np
import pytest

from momentum.Analysis.model_validation.combinatorial_purged_cv import (
    CPCVConfig,
    CombinatorialPurgedCV,
)


def test_P1_too_few_groups():
    with pytest.raises(ValueError):
        CPCVConfig(n_groups=2, n_test_groups=1)


def test_P2_test_groups_exceed():
    with pytest.raises(Exception):
        CPCVConfig(n_groups=6, n_test_groups=6)


def test_P3_path_sampling_coverage(synthetic_binary_data):
    X, _ = synthetic_binary_data
    cpcv = CombinatorialPurgedCV(config={"n_groups": 10, "n_test_groups": 3, "max_paths": 20})
    splits = list(cpcv.split(X))
    assert len(splits) == 20


def test_P4_small_group(synthetic_binary_data):
    X, _ = synthetic_binary_data
    cpcv = CombinatorialPurgedCV(config={"n_groups": 20, "n_test_groups": 2})
    splits = list(cpcv.split(X.iloc[:200]))
    assert len(splits) > 0


def test_P5_purge_exceeds_group(synthetic_binary_data):
    X, _ = synthetic_binary_data
    cpcv = CombinatorialPurgedCV(config={"n_groups": 20, "n_test_groups": 2, "purge_gap": 50})
    with pytest.raises(ValueError):
        list(cpcv.split(X.iloc[:200]))


def test_P6_single_path_failure(synthetic_binary_data):
    X, y = synthetic_binary_data

    def bad_factory():
        class BadModel:
            def fit(self, X, y):
                raise RuntimeError("failed")

        return BadModel()

    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2})
    result = cpcv.validate(bad_factory, X, y, X.columns.tolist())
    assert result["cpcv"]["status"] == "skipped"


def test_P7_all_paths_nan(synthetic_binary_data):
    X, y = synthetic_binary_data
    y_one = np.ones_like(y)
    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2})

    def model_factory():
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(max_iter=1000)

    result = cpcv.validate(model_factory, X, y_one, X.columns.tolist())
    assert result["cpcv"]["status"] == "skipped"


def test_P8_standard_6_2_cpcv(synthetic_binary_data):
    X, _ = synthetic_binary_data
    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2, "max_paths": 200})
    paths = cpcv.generate_backtest_paths(6, 2)
    assert len(paths) == 15
    splits = list(cpcv.split(X))
    assert len(splits) == 15


def test_P9_embargo_empties_train(synthetic_binary_data):
    X, _ = synthetic_binary_data
    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2, "embargo_pct": 0.1, "purge_gap": 5})
    splits = list(cpcv.split(X.iloc[:200]))
    assert len(splits) > 0
    for train_idx, _ in splits:
        assert len(train_idx) > 0


def test_validate_schema(synthetic_binary_data):
    X, y = synthetic_binary_data

    def model_factory():
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(max_iter=1000)

    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2})
    result = cpcv.validate(model_factory, X, y, X.columns.tolist())
    assert "cpcv" in result
    if result["cpcv"].get("status") != "skipped":
        assert result["cpcv"]["n_paths"] > 0
        assert "feature_stability" in result["cpcv"]


def test_split_indices_do_not_overlap(synthetic_binary_data):
    X, _ = synthetic_binary_data
    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2})
    for train_idx, test_idx in cpcv.split(X):
        assert len(np.intersect1d(train_idx, test_idx)) == 0


def test_validate_returns_summary_statistics(synthetic_binary_data):
    X, y = synthetic_binary_data

    def model_factory():
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(max_iter=1000)

    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2})
    result = cpcv.validate(model_factory, X, y, X.columns.tolist())
    if result["cpcv"].get("status") != "skipped":
        summary = result["cpcv"]["summary"]
        assert summary["min_auc"] <= summary["mean_auc"] <= summary["max_auc"]


def test_generate_backtest_paths_schema():
    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2})
    paths = cpcv.generate_backtest_paths(6, 2)
    assert all(isinstance(path, list) for path in paths)
    assert all(len(path) == 2 for path in paths)


def test_validate_path_results_lengths_consistent(synthetic_binary_data):
    X, y = synthetic_binary_data

    def model_factory():
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(max_iter=1000)

    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2})
    result = cpcv.validate(model_factory, X, y, X.columns.tolist())
    if result["cpcv"].get("status") != "skipped":
        assert len(result["cpcv"]["path_results"]) == result["cpcv"]["n_paths"]


def test_validate_path_aucs_within_valid_range(synthetic_binary_data):
    X, y = synthetic_binary_data

    def model_factory():
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(max_iter=1000)

    cpcv = CombinatorialPurgedCV(config={"n_groups": 6, "n_test_groups": 2})
    result = cpcv.validate(model_factory, X, y, X.columns.tolist())
    if result["cpcv"].get("status") != "skipped":
        assert all(0.0 <= auc <= 1.0 for auc in result["cpcv"]["path_aucs"])
