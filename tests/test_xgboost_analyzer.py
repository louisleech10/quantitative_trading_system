"""
測試 XGBoost 分析器

測試 XGBoost 模型訓練、特徵重要性計算、交叉驗證

Author: AI Agent
Date: 2026-01-10
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
from api.core.logging import get_logger

logger = get_logger(__name__)


def _train_sample_model():
    """測試 XGBoost 模型訓練"""
    logger.info("=" * 60)
    logger.info("測試 1: XGBoost 模型訓練")
    logger.info("=" * 60)
    
    # 建立測試數據
    np.random.seed(42)
    n_samples = 500
    n_features = 10
    
    # 生成特徵
    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f"feature_{i}" for i in range(n_features)]
    )
    
    # 生成標籤（基於某些特徵的組合）
    y = ((X['feature_0'] > 0) & (X['feature_1'] > 0)).astype(int).values
    
    logger.info(f"數據集大小: {n_samples} 樣本, {n_features} 特徵")
    logger.info(f"正樣本比例: {y.mean():.2%}")
    
    # 訓練模型
    analyzer = XGBoostAnalyzer()
    performance = analyzer.train_model(X, y)
    
    logger.info(f"訓練集 AUC: {performance.in_sample_train_auc:.4f}")
    logger.info(f"交叉驗證 AUC: {performance.cv_auc_mean:.4f} ± {performance.cv_auc_std:.4f}")
    logger.info(f"Precision: {performance.precision:.4f}")
    logger.info(f"Recall: {performance.recall:.4f}")
    logger.info(f"F1 Score: {performance.f1_score:.4f}")
    logger.info(f"Overfitting Score: {performance.overfitting_score:.4f}")
    
    # 驗證
    assert performance.in_sample_train_auc > 0.5, "訓練 AUC 應該 > 0.5"
    assert performance.cv_auc_mean > 0.5, "交叉驗證 AUC 應該 > 0.5"
    assert 0 <= performance.overfitting_score <= 1, "Overfitting score 應該在 [0, 1] 範圍"
    
    logger.info("✅ 測試通過: XGBoost 模型訓練成功")
    return analyzer, X.columns.tolist()


def test_xgboost_training():
    """測試 XGBoost 模型訓練"""
    _train_sample_model()


def test_feature_importance():
    """測試特徵重要性計算"""
    logger.info("=" * 60)
    logger.info("測試 2: 特徵重要性計算")
    logger.info("=" * 60)

    analyzer, feature_names = _train_sample_model()
    importance = analyzer.calculate_feature_importance(feature_names)
    
    logger.info(f"前 5 個重要特徵:")
    for fi in importance[:5]:
        logger.info(
            f"  {fi.rank}. {fi.feature}: {fi.importance:.4f} (method: {fi.method})"
        )
    
    # 驗證
    assert len(importance) == len(feature_names), "重要性數量應等於特徵數量"
    assert importance[0].rank == 1, "第一個特徵的 rank 應為 1"
    assert all(fi.importance >= 0 for fi in importance), "重要性應 >= 0"
    
    logger.info("✅ 測試通過: 特徵重要性計算成功")


def run_all_tests():
    """執行所有測試"""
    logger.info("開始執行 XGBoost 分析器測試...")
    
    try:
        # 測試 1: 模型訓練
        analyzer, feature_names = _train_sample_model()
        
        # 測試 2: 特徵重要性
        test_feature_importance()
        
        logger.info("=" * 60)
        logger.info("✅ 所有測試通過!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 測試失敗: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
