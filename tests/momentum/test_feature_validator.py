"""
Feature Validator Tests - 特徵驗證器測試

測試特徵驗證功能，確保符合機器學習要求

Author: AI Agent
Date: 2026-01-10
"""

import pytest
import pandas as pd
import numpy as np
import h5py

from momentum.FeatureEngineering.feature_extractor import (
    FeatureExtractor,
    StrategyParams
)
from momentum.FeatureEngineering.feature_validator import FeatureValidator


@pytest.fixture
def sample_features():
    """生成樣本特徵數據"""
    extractor = FeatureExtractor()
    
    # 載入真實數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:500]
    df = pd.DataFrame(data)
    
    # 提取特徵
    params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6}
    )
    
    features_df, feature_names = extractor.extract_features_from_strategy(
        df, params, include_basic_features=True
    )
    
    return features_df, feature_names


def test_feature_validation(sample_features):
    """測試完整驗證流程"""
    features_df, feature_names = sample_features
    validator = FeatureValidator(correlation_threshold=0.95)
    
    # 前向填補 NaN
    features_df[feature_names] = features_df[feature_names].fillna(method='ffill')
    features_df[feature_names] = features_df[feature_names].fillna(0)
    
    result = validator.validate(features_df, feature_names)
    
    # 檢查驗證結果
    assert result.has_nan == False, "不應有 NaN 值 (已填補)"
    assert result.has_inf == False, "不應有 Inf 值"
    assert result.max_correlation <= 1.0
    
    print(f"✅ 驗證完成 - 最大相關性: {result.max_correlation:.4f}")
    if result.high_correlation_pairs:
        print(f"   高相關性對數量: {len(result.high_correlation_pairs)}")
    if result.warnings:
        print(f"   警告: {result.warnings}")


def test_validate_correlation_threshold(sample_features):
    """測試高相關性檢測 (相關性 > 0.95)"""
    features_df, feature_names = sample_features
    validator = FeatureValidator(correlation_threshold=0.95)
    
    # 前向填補
    features_df[feature_names] = features_df[feature_names].fillna(method='ffill')
    features_df[feature_names] = features_df[feature_names].fillna(0)
    
    max_corr, high_corr_pairs = validator.validate_correlation(features_df, feature_names)
    
    assert max_corr <= 1.0
    assert max_corr >= 0.0
    
    # 檢查高相關性對
    for feat1, feat2, corr in high_corr_pairs:
        assert corr > 0.95, f"相關性應 > 0.95: {feat1} <-> {feat2} = {corr}"
    
    print(f"✅ 相關性檢測完成 - 最大相關性: {max_corr:.4f}, "
          f"高相關性對: {len(high_corr_pairs)}")


def test_validate_no_future_leak(sample_features):
    """測試無未來函數 (基於時間序列)"""
    features_df, feature_names = sample_features
    validator = FeatureValidator()
    
    # 檢查時間戳遞增
    result = validator.validate_no_future_leak(features_df, feature_names)
    
    assert result == True, "檢測到未來函數"
    
    print("✅ 無未來函數檢查通過")


def test_fill_nan_values():
    """測試 NaN 值填補"""
    validator = FeatureValidator()
    
    # 建立包含 NaN 的數據
    df = pd.DataFrame({
        'timestamp': [1, 2, 3, 4, 5],
        'feature1': [1.0, np.nan, 3.0, np.nan, 5.0],
        'feature2': [10.0, 20.0, np.nan, np.nan, 50.0]
    })
    
    feature_names = ['feature1', 'feature2']
    
    # 前向填補
    df_filled = validator.fill_nan_values(df, feature_names, method='forward')
    
    # 檢查 NaN 已填補
    assert df_filled['feature1'].isna().sum() == 0
    assert df_filled['feature2'].isna().sum() == 0
    
    # 檢查填補值正確
    assert df_filled['feature1'].iloc[1] == 1.0  # 前向填補
    assert df_filled['feature2'].iloc[2] == 20.0  # 前向填補
    
    print("✅ NaN 值填補測試通過")


def test_edge_case_constant_features():
    """Edge Case: 常數特徵處理 (標準差為 0)"""
    validator = FeatureValidator()
    
    # 建立包含常數特徵的數據
    df = pd.DataFrame({
        'timestamp': [1, 2, 3, 4, 5],
        'feature1': [1.0, 1.0, 1.0, 1.0, 1.0],  # 常數
        'feature2': [10.0, 20.0, 30.0, 40.0, 50.0],  # 正常
        'feature3': [5.0, 5.0, 5.0, 5.0, 5.0]  # 常數
    })
    
    feature_names = ['feature1', 'feature2', 'feature3']
    
    result = validator.validate(df, feature_names)
    
    # 檢查警告中是否提到常數特徵
    constant_warning = any('常數特徵' in w for w in result.warnings)
    assert constant_warning, "應該警告常數特徵"
    
    print("✅ 常數特徵處理測試通過")


def test_edge_case_all_nan():
    """Edge Case: 整列都是 NaN"""
    validator = FeatureValidator()
    
    df = pd.DataFrame({
        'timestamp': [1, 2, 3],
        'feature1': [np.nan, np.nan, np.nan],
        'feature2': [10.0, 20.0, 30.0]
    })
    
    feature_names = ['feature1', 'feature2']
    
    # 填補後檢查
    df_filled = validator.fill_nan_values(df, feature_names, method='forward')
    
    # 整列 NaN 應該被填 0
    assert df_filled['feature1'].iloc[0] == 0.0
    
    print("✅ 整列 NaN 處理測試通過")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
