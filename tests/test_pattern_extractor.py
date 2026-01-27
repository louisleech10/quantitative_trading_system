"""
測試模式提取器

測試從 XGBoost 模型提取決策規則

Author: AI Agent
Date: 2026-01-10
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
from momentum.Analysis.pattern_extractor import PatternExtractor
from api.core.logging import get_logger

logger = get_logger(__name__)


def test_pattern_extraction():
    """測試模式提取"""
    logger.info("=" * 60)
    logger.info("測試: 決策規則提取")
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
    analyzer.train_model(X, y)
    
    # 提取規則
    extractor = PatternExtractor()
    rules = extractor.extract_decision_rules(
        model=analyzer.model,
        X=X,
        y=y,
        feature_names=X.columns.tolist(),
        top_n=10,
        min_support=10
    )
    
    logger.info(f"提取到 {len(rules)} 條規則")
    
    # 顯示前 3 條規則
    for i, rule in enumerate(rules[:3], 1):
        logger.info(f"\n規則 {i}:")
        logger.info(f"  條件: {rule.condition}")
        logger.info(f"  支持度: {rule.support}")
        logger.info(f"  信心度: {rule.confidence:.4f}")
        logger.info(f"  提升: {rule.lift:.4f}")
    
    # 驗證
    assert len(rules) > 0, "應該提取到至少 1 條規則"
    assert all(rule.support >= 10 for rule in rules), "所有規則的支持度應 >= 10"
    assert all(0 <= rule.confidence <= 1 for rule in rules), "信心度應在 [0, 1] 範圍"
    assert all(rule.lift >= 0 for rule in rules), "提升應 >= 0"
    
    logger.info("\n✅ 測試通過: 模式提取成功")


def run_all_tests():
    """執行所有測試"""
    logger.info("開始執行模式提取器測試...")
    
    try:
        test_pattern_extraction()
        
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
