"""
測試校準指標、PR AUC 與預測輸出

Author: AI Agent
Date: 2026-01-28
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, precision_recall_curve, auc

from momentum.Analysis.calibration_analyzer import CalibrationAnalyzer
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer


def test_calibration_metrics_match_sklearn():
    """校準指標與 sklearn 計算一致"""
    y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 0, 1])
    y_pred_proba = np.array([0.05, 0.92, 0.12, 0.78, 0.64, 0.23, 0.88, 0.31, 0.19, 0.73])

    analyzer = CalibrationAnalyzer(min_samples=1)

    brier = analyzer.calculate_brier_score(y_true, y_pred_proba)
    expected_brier = brier_score_loss(y_true, y_pred_proba)
    assert abs(brier - expected_brier) < 1e-10

    # 手動 ECE
    n_bins = 5
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(y_pred_proba, bins, right=True) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)
    ece_manual = 0.0
    total = len(y_true)
    for idx in range(n_bins):
        mask = bin_indices == idx
        count = int(np.sum(mask))
        if count == 0:
            continue
        actual_rate = float(np.mean(y_true[mask]))
        pred_mean = float(np.mean(y_pred_proba[mask]))
        ece_manual += (count / total) * abs(actual_rate - pred_mean)

    ece = analyzer.calculate_ece(y_true, y_pred_proba, n_bins=n_bins)
    assert abs(ece - ece_manual) < 1e-10


def test_pr_auc_and_predictions_output():
    """PR AUC 與預測輸出正確"""
    np.random.seed(42)
    n_samples = 300
    n_features = 8

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f"feature_{i}" for i in range(n_features)]
    )
    y = ((X["feature_0"] > 0) & (X["feature_1"] > 0)).astype(int).values
    case_ids = [f"case_{i}" for i in range(n_samples)]

    analyzer = XGBoostAnalyzer()
    analyzer.train_model(X, y, cv_folds=3)

    predictions_output = analyzer.get_predictions(X, y, case_ids)
    proba_values = [p.predicted_proba for p in predictions_output.predictions]

    assert len(predictions_output.predictions) == n_samples
    assert all(0.0 <= p <= 1.0 for p in proba_values)

    summary = predictions_output.proba_summary
    assert abs(summary.mean - float(np.mean(proba_values))) < 1e-8
    assert sum(summary.bins.values()) == n_samples

    pr_metrics = analyzer.calculate_pr_metrics(X, y)
    precision, recall, _ = precision_recall_curve(y, np.array(proba_values))
    expected_pr_auc = auc(recall, precision)

    assert abs(pr_metrics.pr_auc - expected_pr_auc) < 1e-8
    assert abs(pr_metrics.positive_rate - float(np.mean(y))) < 1e-10
