"""
Feature Extractor Tests - 特徵提取器測試

使用真實 ETHUSDT 數據測試動態特徵生成

Author: AI Agent
Date: 2026-01-10
"""

import pytest
import pandas as pd
import numpy as np
import h5py
import json

from momentum.FeatureEngineering import FeatureExtractor, StrategyParams


@pytest.fixture
def sample_kline_data():
    """載入真實 ETHUSDT 1h 數據樣本 (前 1000 行)"""
    hdf5_path = "data_cache/kline_cache.h5"
    
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:1000]  # 只取前 1000 行測試
    
    df = pd.DataFrame(data)
    return df


@pytest.fixture
def ema_strategy_params():
    """EMA 三線策略參數"""
    return StrategyParams(
        strategy_type='ema_three_line',
        params={
            'ema_short': 5,
            'ema_mid': 20,
            'ema_long': 60,
            'volume_threshold': 0.6
        }
    )


def test_feature_extraction_ema_strategy(sample_kline_data, ema_strategy_params):
    """測試 EMA 三線策略特徵提取 (使用真實數據)"""
    extractor = FeatureExtractor()
    
    features_df, feature_names = extractor.extract_features_from_strategy(
        sample_kline_data,
        ema_strategy_params,
        include_basic_features=True
    )
    
    # 檢查基本結構
    assert len(features_df) == len(sample_kline_data)
    assert len(feature_names) >= 20  # 至少 20 個特徵
    assert 'timestamp' in features_df.columns
    
    # 檢查必要特徵存在（使用新的動態命名）
    expected_features = [
        'price_change_pct',
        'volume_change_pct',
        'close_ema5_value',  # 新命名格式
        'close_ema20_value',
        'close_ema60_value',
        'close_ema5-20_distance',
        'close_ema_trend_aligned',
        'close_ema_entry_signal_score'
    ]
    
    for feature in expected_features:
        assert feature in feature_names, f"缺少特徵: {feature}"
    
    print(f"✅ 特徵提取成功 - 提取了 {len(feature_names)} 個特徵")
    print(f"特徵列表: {feature_names}")


def test_feature_no_nan_inf(sample_kline_data, ema_strategy_params):
    """測試特徵無 NaN/Inf 值 (前向填補後)"""
    extractor = FeatureExtractor()
    
    features_df, feature_names = extractor.extract_features_from_strategy(
        sample_kline_data,
        ema_strategy_params,
        include_basic_features=True
    )
    
    # 前向填補 NaN
    features_df[feature_names] = features_df[feature_names].fillna(method='ffill')
    features_df[feature_names] = features_df[feature_names].fillna(0)  # 剩餘的填 0
    
    # 檢查 NaN
    nan_count = features_df[feature_names].isna().sum().sum()
    assert nan_count == 0, f"發現 {nan_count} 個 NaN 值"
    
    # 檢查 Inf
    inf_count = np.isinf(features_df[feature_names]).sum().sum()
    assert inf_count == 0, f"發現 {inf_count} 個 Inf 值"
    
    print("✅ 特徵無 NaN/Inf 值 (填補後)")


def test_dynamic_feature_generation():
    """測試動態特徵生成 (不同參數組合，使用新命名)"""
    extractor = FeatureExtractor()
    
    # 參數組合 1: ema_short=5, ema_mid=20, ema_long=60
    params1 = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    
    # 參數組合 2: ema_short=10, ema_mid=30, ema_long=90
    params2 = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 10, 'ema_mid': 30, 'ema_long': 90, 'volume_threshold': 0.7},
        data_source='close'
    )
    
    # 參數組合 3: 使用 volume 作為數據源
    params3 = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='volume'
    )
    
    # 載入數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:500]
    df = pd.DataFrame(data)
    
    # 提取特徵 1
    _, feature_names1 = extractor.extract_features_from_strategy(
        df.copy(), params1, include_basic_features=False
    )
    
    # 提取特徵 2
    _, feature_names2 = extractor.extract_features_from_strategy(
        df.copy(), params2, include_basic_features=False
    )
    
    # 提取特徵 3
    _, feature_names3 = extractor.extract_features_from_strategy(
        df.copy(), params3, include_basic_features=False
    )
    
    # 特徵名稱應該不同 (因為 EMA 參數不同)
    assert 'close_ema5_value' in feature_names1
    assert 'close_ema10_value' in feature_names2
    assert 'close_ema5-20_distance' in feature_names1
    assert 'close_ema10-30_distance' in feature_names2
    
    # 不同數據源應該生成不同特徵名稱
    assert 'volume_ema5_value' in feature_names3
    assert 'close_ema5_value' not in feature_names3
    
    print("✅ 動態特徵生成測試通過")
    print(f"   組合1特徵數: {len(feature_names1)}")
    print(f"   組合2特徵數: {len(feature_names2)}")
    print(f"   組合3特徵數: {len(feature_names3)}")


def test_edge_case_empty_data():
    """Edge Case: 空數據處理"""
    extractor = FeatureExtractor()
    empty_df = pd.DataFrame()
    
    params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6}
    )
    
    with pytest.raises(ValueError, match="數據為空"):
        extractor.extract_features_from_strategy(empty_df, params)
    
    print("✅ 空數據處理測試通過")


def test_edge_case_missing_columns():
    """Edge Case: 缺失欄位處理"""
    extractor = FeatureExtractor()
    
    # 建立缺少 taker_buy_volume 欄位的數據
    incomplete_df = pd.DataFrame({
        'timestamp': [1672171200, 1672174800],
        'open': [1211.1, 1212.0],
        'high': [1212.0, 1213.0],
        'low': [1210.0, 1211.0],
        'close': [1211.5, 1212.5],
        'volume': [1000.0, 1100.0],
        # 缺少 taker_buy_volume, taker_ratio, quote_volume
    })
    
    params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6}
    )
    
    with pytest.raises(ValueError, match="缺少必要欄位"):
        extractor.extract_features_from_strategy(incomplete_df, params)
    
    print("✅ 缺失欄位處理測試通過")


def test_edge_case_invalid_strategy_params():
    """Edge Case: 無效策略參數處理"""
    extractor = FeatureExtractor()
    
    # 載入數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:100]
    df = pd.DataFrame(data)
    
    # 無效的策略類型
    invalid_params = StrategyParams(
        strategy_type='invalid_strategy',
        params={'ema_short': 5}
    )
    
    with pytest.raises(ValueError, match="不支持的策略類型|找不到策略"):
        extractor.extract_features_from_strategy(df, invalid_params)
    
    # 缺少必要參數
    incomplete_params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5}  # 缺少 ema_mid, ema_long, volume_threshold
    )
    
    with pytest.raises((ValueError, KeyError)):
        extractor.extract_features_from_strategy(df, incomplete_params)
    
    print("✅ 無效策略參數處理測試通過")


def test_multi_indicator_strategy():
    """測試多指標混合策略（EMA + RSI + MACD）"""
    from momentum.FeatureEngineering.strategy_registry import StrategyRegistry
    from momentum.FeatureEngineering.indicators import RSIExtractor, MACDExtractor
    
    # 註冊 RSI 和 MACD
    registry = StrategyRegistry()
    registry.register_strategy(
        name='rsi',
        description='Relative Strength Index',
        required_params=['period'],
        optional_params={'overbought': 70, 'oversold': 30},
        extractor=RSIExtractor()
    )
    registry.register_strategy(
        name='macd',
        description='Moving Average Convergence Divergence',
        required_params=['fast', 'slow', 'signal'],
        extractor=MACDExtractor()
    )
    
    # 載入數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:500]
    df = pd.DataFrame(data)
    
    extractor = FeatureExtractor()
    
    # 提取 EMA 特徵
    params_ema = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    df_ema, names_ema = extractor.extract_features_from_strategy(
        df.copy(), params_ema, include_basic_features=False
    )
    
    # 提取 RSI 特徵
    params_rsi = StrategyParams(
        strategy_type='rsi',
        params={'period': 14, 'overbought': 70, 'oversold': 30},
        data_source='close'
    )
    df_rsi, names_rsi = extractor.extract_features_from_strategy(
        df.copy(), params_rsi, include_basic_features=False
    )
    
    # 提取 MACD 特徵
    params_macd = StrategyParams(
        strategy_type='macd',
        params={'fast': 12, 'slow': 26, 'signal': 9},
        data_source='close'
    )
    df_macd, names_macd = extractor.extract_features_from_strategy(
        df.copy(), params_macd, include_basic_features=False
    )
    
    # 合併所有特徵
    all_feature_names = names_ema + names_rsi + names_macd
    unique_feature_names = set(all_feature_names)
    
    # 驗證無衝突
    assert len(all_feature_names) == len(unique_feature_names), "發現特徵名稱衝突！"
    
    # 驗證特徵存在
    assert any('ema' in name for name in names_ema)
    assert any('rsi' in name for name in names_rsi)
    assert any('macd' in name for name in names_macd)
    
    print("✅ 多指標混合策略測試通過")
    print(f"   EMA 特徵數: {len(names_ema)}")
    print(f"   RSI 特徵數: {len(names_rsi)}")
    print(f"   MACD 特徵數: {len(names_macd)}")
    print(f"   總特徵數: {len(all_feature_names)}")
    print(f"   唯一特徵數: {len(unique_feature_names)}")


if __name__ == "__main__":
    # 可單獨執行測試
    pytest.main([__file__, "-v", "--tb=short"])
