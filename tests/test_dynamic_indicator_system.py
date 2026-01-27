"""
測試完全動態的指標系統

驗證：
1. EMA 指標動態提取
2. RSI 指標動態提取
3. MACD 指標動態提取
4. 混合多種指標無衝突
5. 任何人都可以添加新指標

Author: AI Agent
Date: 2026-01-11
"""

import pandas as pd
import numpy as np
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams
from momentum.FeatureEngineering.strategy_registry import StrategyRegistry
from momentum.FeatureEngineering.indicators import EMAExtractor, RSIExtractor, MACDExtractor

def create_mock_data(n=200):
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

def test_ema_dynamic_extraction():
    """測試 1: EMA 動態提取"""
    print("\n" + "=" * 70)
    print("測試 1: EMA 動態提取（使用註冊系統）")
    print("=" * 70)
    
    df = create_mock_data()
    extractor = FeatureExtractor()
    
    # EMA 策略（系統已自動註冊）
    params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    
    features_df, feature_names = extractor.extract_features_from_strategy(
        df, params, include_basic_features=False
    )
    
    print(f"✅ 成功提取 {len(feature_names)} 個 EMA 特徵")
    print("特徵名稱前 5 個:")
    for i, name in enumerate(feature_names[:5], 1):
        print(f"   {i}. {name}")
    
    return len(feature_names) > 0

def test_rsi_dynamic_extraction():
    """測試 2: RSI 動態提取"""
    print("\n" + "=" * 70)
    print("測試 2: RSI 動態提取（手動註冊）")
    print("=" * 70)
    
    # 註冊 RSI 策略
    registry = StrategyRegistry()
    registry.register_strategy(
        name='rsi',
        description='Relative Strength Index',
        required_params=['period'],
        optional_params={'overbought': 70, 'oversold': 30},
        extractor=RSIExtractor()
    )
    print("✅ 註冊 RSI 策略")
    
    df = create_mock_data()
    extractor = FeatureExtractor()
    
    params = StrategyParams(
        strategy_type='rsi',
        params={'period': 14, 'overbought': 70, 'oversold': 30},
        data_source='close'
    )
    
    features_df, feature_names = extractor.extract_features_from_strategy(
        df, params, include_basic_features=False
    )
    
    print(f"✅ 成功提取 {len(feature_names)} 個 RSI 特徵")
    print("特徵名稱:")
    for i, name in enumerate(feature_names, 1):
        print(f"   {i}. {name}")
    
    return len(feature_names) > 0

def test_macd_dynamic_extraction():
    """測試 3: MACD 動態提取"""
    print("\n" + "=" * 70)
    print("測試 3: MACD 動態提取（手動註冊）")
    print("=" * 70)
    
    # 註冊 MACD 策略
    registry = StrategyRegistry()
    registry.register_strategy(
        name='macd',
        description='Moving Average Convergence Divergence',
        required_params=['fast', 'slow', 'signal'],
        extractor=MACDExtractor()
    )
    print("✅ 註冊 MACD 策略")
    
    df = create_mock_data()
    extractor = FeatureExtractor()
    
    params = StrategyParams(
        strategy_type='macd',
        params={'fast': 12, 'slow': 26, 'signal': 9},
        data_source='close'
    )
    
    features_df, feature_names = extractor.extract_features_from_strategy(
        df, params, include_basic_features=False
    )
    
    print(f"✅ 成功提取 {len(feature_names)} 個 MACD 特徵")
    print("特徵名稱:")
    for i, name in enumerate(feature_names, 1):
        print(f"   {i}. {name}")
    
    return len(feature_names) > 0

def test_mixed_indicators():
    """測試 4: 混合多種指標"""
    print("\n" + "=" * 70)
    print("測試 4: 混合多種指標（驗證無衝突）")
    print("=" * 70)
    
    # 註冊所有策略
    registry = StrategyRegistry()
    registry.register_strategy(
        name='rsi',
        description='RSI',
        required_params=['period'],
        extractor=RSIExtractor()
    )
    registry.register_strategy(
        name='macd',
        description='MACD',
        required_params=['fast', 'slow', 'signal'],
        extractor=MACDExtractor()
    )
    
    df = create_mock_data()
    extractor = FeatureExtractor()
    
    # 提取 EMA 特徵
    params_ema = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    df1, names_ema = extractor.extract_features_from_strategy(
        df.copy(), params_ema, include_basic_features=False
    )
    
    # 提取 RSI 特徵
    params_rsi = StrategyParams(
        strategy_type='rsi',
        params={'period': 14, 'overbought': 70, 'oversold': 30},
        data_source='close'
    )
    df2, names_rsi = extractor.extract_features_from_strategy(
        df.copy(), params_rsi, include_basic_features=False
    )
    
    # 提取 MACD 特徵
    params_macd = StrategyParams(
        strategy_type='macd',
        params={'fast': 12, 'slow': 26, 'signal': 9},
        data_source='close'
    )
    df3, names_macd = extractor.extract_features_from_strategy(
        df.copy(), params_macd, include_basic_features=False
    )
    
    # 檢查衝突
    all_names = names_ema + names_rsi + names_macd
    unique_names = set(all_names)
    
    has_collision = len(all_names) != len(unique_names)
    
    print(f"EMA 特徵數: {len(names_ema)}")
    print(f"RSI 特徵數: {len(names_rsi)}")
    print(f"MACD 特徵數: {len(names_macd)}")
    print(f"總特徵數: {len(all_names)}")
    print(f"唯一特徵數: {len(unique_names)}")
    
    if has_collision:
        collisions = [name for name in all_names if all_names.count(name) > 1]
        print(f"❌ 發現衝突: {set(collisions)}")
    else:
        print("✅ 無特徵名稱衝突")
    
    # 顯示各類特徵範例
    print("\nEMA 特徵範例:")
    for name in names_ema[:3]:
        print(f"   - {name}")
    
    print("\nRSI 特徵範例:")
    for name in names_rsi[:3]:
        print(f"   - {name}")
    
    print("\nMACD 特徵範例:")
    for name in names_macd[:3]:
        print(f"   - {name}")
    
    return not has_collision

def test_registry_listing():
    """測試 5: 查看所有已註冊策略"""
    print("\n" + "=" * 70)
    print("測試 5: 查看所有已註冊策略")
    print("=" * 70)
    
    # 註冊所有策略
    registry = StrategyRegistry()
    registry.register_strategy(
        name='rsi',
        description='Relative Strength Index',
        required_params=['period'],
        extractor=RSIExtractor()
    )
    registry.register_strategy(
        name='macd',
        description='Moving Average Convergence Divergence',
        required_params=['fast', 'slow', 'signal'],
        extractor=MACDExtractor()
    )
    
    strategies = registry.list_strategies()
    print(f"✅ 系統中已註冊 {len(strategies)} 個策略:")
    for i, name in enumerate(strategies, 1):
        strategy = registry.get_strategy(name)
        print(f"   {i}. {name} - {strategy.description}")
        print(f"      必要參數: {strategy.required_params}")
    
    return len(strategies) >= 3

if __name__ == "__main__":
    print("=" * 70)
    print("完全動態指標系統測試")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("EMA 動態提取", test_ema_dynamic_extraction()))
    except Exception as e:
        print(f"❌ EMA 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results.append(("EMA 動態提取", False))
    
    try:
        results.append(("RSI 動態提取", test_rsi_dynamic_extraction()))
    except Exception as e:
        print(f"❌ RSI 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results.append(("RSI 動態提取", False))
    
    try:
        results.append(("MACD 動態提取", test_macd_dynamic_extraction()))
    except Exception as e:
        print(f"❌ MACD 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results.append(("MACD 動態提取", False))
    
    try:
        results.append(("混合多種指標", test_mixed_indicators()))
    except Exception as e:
        print(f"❌ 混合指標測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results.append(("混合多種指標", False))
    
    try:
        results.append(("策略列表查詢", test_registry_listing()))
    except Exception as e:
        print(f"❌ 策略列表測試失敗: {e}")
        results.append(("策略列表查詢", False))
    
    # 總結
    print("\n" + "=" * 70)
    print("測試總結")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n總計: {passed_count}/{total_count} 測試通過")
    
    if passed_count == total_count:
        print("\n🎉 所有測試通過！完全動態系統運作正常！")
    else:
        print(f"\n⚠️  {total_count - passed_count} 個測試失敗，需要檢查。")
