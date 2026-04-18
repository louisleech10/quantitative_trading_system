"""
測試動態特徵命名系統與 feature_extractor.py 的整合

驗證：
1. 不同數據源生成不同特徵名稱
2. 特徵名稱格式正確
3. 混合配置不會衝突
"""

import pandas as pd
import numpy as np
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams

def create_mock_kline_data(n=200):
    """建立模擬 K 線數據"""
    return pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n, freq='12h'),
        'open': np.random.uniform(40000, 50000, n),
        'high': np.random.uniform(50000, 60000, n),
        'low': np.random.uniform(30000, 40000, n),
        'close': np.random.uniform(40000, 50000, n),
        'volume': np.random.uniform(1000, 10000, n),
        'taker_buy_volume': np.random.uniform(500, 8000, n),
        'taker_ratio': np.random.uniform(0.3, 0.8, n),
        'quote_volume': np.random.uniform(50000000, 500000000, n)
    })

def test_close_data_source():
    """測試 1: CLOSE 數據源特徵命名"""
    print("\n========== 測試 1: CLOSE 數據源特徵命名 ==========")
    
    df = create_mock_kline_data()
    extractor = FeatureExtractor()
    
    strategy_params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    
    features_df, feature_names = extractor.extract_features_from_strategy(df, strategy_params)
    
    print(f"✅ 生成 {len(feature_names)} 個特徵")
    print(f"前 10 個特徵名稱:")
    for i, name in enumerate(feature_names[:10], 1):
        print(f"   {i}. {name}")
    
    # 驗證關鍵特徵名稱
    expected_features = [
        'close_ema5_value',
        'close_ema20_value',
        'close_ema60_value',
        'close_ema5-20_distance',
        'close_ema20-60_distance',
        'close_ema_trend_aligned',
        'close_ema5-20_cross_signal'
    ]
    
    for expected in expected_features:
        if expected in feature_names:
            print(f"   ✅ 找到特徵: {expected}")
        else:
            print(f"   ❌ 缺少特徵: {expected}")
    
    return features_df, feature_names

def test_volume_data_source():
    """測試 2: VOLUME 數據源特徵命名"""
    print("\n========== 測試 2: VOLUME 數據源特徵命名 ==========")
    
    df = create_mock_kline_data()
    extractor = FeatureExtractor()
    
    strategy_params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 6, 'ema_mid': 15, 'ema_long': 28, 'volume_threshold': 0.7},
        data_source='volume'
    )
    
    features_df, feature_names = extractor.extract_features_from_strategy(df, strategy_params)
    
    print(f"✅ 生成 {len(feature_names)} 個特徵")
    print(f"前 10 個特徵名稱:")
    for i, name in enumerate(feature_names[:10], 1):
        print(f"   {i}. {name}")
    
    # 驗證關鍵特徵名稱
    expected_features = [
        'volume_ema6_value',
        'volume_ema15_value',
        'volume_ema28_value',
        'volume_ema6-15_distance',
        'volume_ema15-28_distance',
        'volume_ema_trend_aligned'
    ]
    
    for expected in expected_features:
        if expected in feature_names:
            print(f"   ✅ 找到特徵: {expected}")
        else:
            print(f"   ❌ 缺少特徵: {expected}")
    
    return features_df, feature_names

def test_no_collision():
    """測試 3: 混合配置不會衝突（僅檢查策略特徵）"""
    print("\n========== 測試 3: 混合配置無衝突驗證 ==========")
    
    df = create_mock_kline_data()
    extractor = FeatureExtractor()
    
    # 配置 1: close_ema
    params1 = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    
    # 配置 2: volume_ema
    params2 = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='volume'
    )
    
    # 不包含基礎特徵，只生成策略特徵
    features_df1, names1 = extractor.extract_features_from_strategy(df.copy(), params1, include_basic_features=False)
    features_df2, names2 = extractor.extract_features_from_strategy(df.copy(), params2, include_basic_features=False)
    
    # 檢查是否有重複特徵名稱
    collision = set(names1) & set(names2)
    
    if collision:
        print(f"❌ 發現衝突特徵: {collision}")
    else:
        print(f"✅ 無特徵名稱衝突（策略特徵）")
    
    print(f"\n配置 1 (close_ema) 特徵數量: {len(names1)}")
    print(f"配置 2 (volume_ema) 特徵數量: {len(names2)}")
    print(f"總特徵數量: {len(set(names1) | set(names2))}")
    
    # 顯示各自的所有特徵
    print(f"\n配置 1 特徵列表:")
    for name in names1:
        print(f"   - {name}")
    
    print(f"\n配置 2 特徵列表:")
    for name in names2:
        print(f"   - {name}")
    
    return len(collision) == 0

def test_different_params_same_indicator():
    """測試 4: 相同指標不同參數（僅檢查策略特徵）"""
    print("\n========== 測試 4: 相同指標不同參數 ==========")
    
    df = create_mock_kline_data()
    extractor = FeatureExtractor()
    
    # 配置 1: EMA(5, 20, 60)
    params1 = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    
    # 配置 2: EMA(10, 30, 90)
    params2 = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 10, 'ema_mid': 30, 'ema_long': 90, 'volume_threshold': 0.7},
        data_source='close'
    )
    
    # 不包含基礎特徵，只生成策略特徵
    features_df1, names1 = extractor.extract_features_from_strategy(df.copy(), params1, include_basic_features=False)
    features_df2, names2 = extractor.extract_features_from_strategy(df.copy(), params2, include_basic_features=False)
    
    # 檢查是否有重複特徵名稱
    collision = set(names1) & set(names2)
    
    if collision:
        print(f"❌ 發現衝突特徵: {collision}")
    else:
        print(f"✅ 無特徵名稱衝突（策略特徵）")
    
    print(f"\n配置 1 (5,20,60) 所有特徵:")
    for name in names1:
        print(f"   - {name}")
    
    print(f"\n配置 2 (10,30,90) 所有特徵:")
    for name in names2:
        print(f"   - {name}")
    
    return len(collision) == 0

if __name__ == "__main__":
    print("=" * 70)
    print("動態特徵命名系統整合測試")
    print("=" * 70)
    
    # 執行測試
    test_close_data_source()
    test_volume_data_source()
    no_collision = test_no_collision()
    different_params = test_different_params_same_indicator()
    
    print("\n" + "=" * 70)
    if no_collision and different_params:
        print("✅ 所有測試通過 - 動態命名系統工作正常")
    else:
        print("❌ 部分測試失敗 - 需要檢查實作")
    print("=" * 70)
