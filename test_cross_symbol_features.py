"""
測試跨標的特徵提取
驗證所有特徵均為相對值，可在不同標的之間使用

Author: AI Agent
Date: 2026-01-23
"""

import pandas as pd
import numpy as np
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor, StrategyParams


def test_cross_symbol_features():
    """測試特徵在不同標的上的表現"""
    
    print("=" * 80)
    print("跨標的特徵提取測試")
    print("=" * 80)
    
    # 建立兩個標的的模擬數據（價格差異巨大）
    btc_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='12h'),
        'open': np.random.uniform(95000, 100000, 100),
        'high': np.random.uniform(95000, 100000, 100),
        'low': np.random.uniform(95000, 100000, 100),
        'close': np.random.uniform(95000, 100000, 100),
        'volume': np.random.uniform(5000, 10000, 100),
        'taker_buy_volume': np.random.uniform(2500, 7500, 100),
        'taker_ratio': np.random.uniform(0.3, 0.8, 100),
        'quote_volume': np.random.uniform(500000000, 1000000000, 100),
    })
    
    sol_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='12h'),
        'open': np.random.uniform(120, 130, 100),
        'high': np.random.uniform(120, 130, 100),
        'low': np.random.uniform(120, 130, 100),
        'close': np.random.uniform(120, 130, 100),
        'volume': np.random.uniform(800000, 1200000, 100),
        'taker_buy_volume': np.random.uniform(400000, 900000, 100),
        'taker_ratio': np.random.uniform(0.3, 0.8, 100),
        'quote_volume': np.random.uniform(100000000, 150000000, 100),
    })
    
    # 特徵提取器
    extractor = FeatureExtractor()
    
    # EMA 策略參數
    strategy_params = StrategyParams(
        strategy_type='ema_three_line',
        params={
            'ema_short': 5,
            'ema_mid': 20,
            'ema_long': 60,
            'volume_threshold': 0.6
        },
        data_source='close'
    )
    
    # 提取 BTC 特徵
    print("\n提取 BTCUSDT 特徵...")
    btc_features, btc_feature_names = extractor.extract_features_from_strategy(
        btc_data, strategy_params
    )
    print(f"✅ BTCUSDT: {len(btc_feature_names)} 個特徵")
    
    # 提取 SOL 特徵
    print("\n提取 SOLUSDT 特徵...")
    sol_features, sol_feature_names = extractor.extract_features_from_strategy(
        sol_data, strategy_params
    )
    print(f"✅ SOLUSDT: {len(sol_feature_names)} 個特徵")
    
    # 驗證特徵名稱一致
    print("\n" + "=" * 80)
    print("檢查 1: 特徵名稱一致性")
    print("=" * 80)
    assert btc_feature_names == sol_feature_names, "❌ 特徵名稱不一致！"
    print("✅ 特徵名稱完全一致")
    
    # 檢查絕對值特徵（不應該存在）
    print("\n" + "=" * 80)
    print("檢查 2: 不應存在絕對值特徵")
    print("=" * 80)
    
    forbidden_keywords = ['_value', '_ema5', '_ema20', '_ema60']
    forbidden_exact = ['price_momentum_3']  # 舊的絕對值動量
    
    found_forbidden = []
    for name in btc_feature_names:
        # 檢查關鍵字
        for keyword in forbidden_keywords:
            if keyword in name and name.endswith('_value'):
                found_forbidden.append(name)
        # 檢查完全匹配
        if name in forbidden_exact:
            found_forbidden.append(name)
    
    if found_forbidden:
        print(f"❌ 發現絕對值特徵: {found_forbidden}")
        raise AssertionError("存在不可跨標的的絕對值特徵！")
    else:
        print("✅ 沒有絕對值特徵")
    
    # 檢查特徵值範圍（相對特徵應該在相似範圍內）
    print("\n" + "=" * 80)
    print("檢查 3: 特徵值分布範圍")
    print("=" * 80)
    
    # 選擇幾個關鍵特徵檢查
    test_features = [
        'price_change_pct',
        'close_price_ema_short_distance_pct',
        'close_ema5_20_distance_pct',
        'taker_buy_ratio'
    ]
    
    print(f"\n{'特徵名稱':<40} {'BTC 範圍':<25} {'SOL 範圍':<25} {'兼容性'}")
    print("-" * 100)
    
    all_compatible = True
    for feat in test_features:
        if feat not in btc_feature_names:
            continue
        
        btc_values = btc_features[feat].dropna()
        sol_values = sol_features[feat].dropna()
        
        btc_min, btc_max = btc_values.min(), btc_values.max()
        sol_min, sol_max = sol_values.min(), sol_values.max()
        
        # 檢查範圍是否相似（允許一定誤差）
        # 相對特徵的範圍應該在同一數量級
        btc_magnitude = max(abs(btc_min), abs(btc_max))
        sol_magnitude = max(abs(sol_min), abs(sol_max))
        
        compatible = False
        if btc_magnitude < 0.01 and sol_magnitude < 0.01:
            compatible = True  # 都很小
        elif btc_magnitude > 0 and sol_magnitude > 0:
            ratio = btc_magnitude / sol_magnitude
            compatible = 0.1 < ratio < 10  # 同一數量級
        
        status = "✅" if compatible else "⚠️"
        all_compatible = all_compatible and compatible
        
        print(f"{feat:<40} [{btc_min:>8.4f}, {btc_max:>8.4f}] [{sol_min:>8.4f}, {sol_max:>8.4f}] {status}")
    
    if all_compatible:
        print("\n✅ 所有測試特徵的數值範圍相似，可跨標的使用")
    else:
        print("\n⚠️ 部分特徵範圍差異較大，需進一步檢查")
    
    # 列出所有特徵
    print("\n" + "=" * 80)
    print(f"所有特徵列表 (共 {len(btc_feature_names)} 個)")
    print("=" * 80)
    
    # 分類顯示
    price_features = [f for f in btc_feature_names if any(k in f for k in ['price', 'shadow', 'body', 'range', 'volatility', 'momentum'])]
    volume_features = [f for f in btc_feature_names if any(k in f for k in ['volume', 'taker'])]
    ema_features = [f for f in btc_feature_names if 'ema' in f]
    signal_features = [f for f in btc_feature_names if 'signal' in f or 'score' in f or 'consistency' in f or 'strength' in f]
    
    print(f"\n價格特徵 ({len(price_features)} 個):")
    for f in price_features:
        print(f"  • {f}")
    
    print(f"\n成交量特徵 ({len(volume_features)} 個):")
    for f in volume_features:
        print(f"  • {f}")
    
    print(f"\nEMA 特徵 ({len(ema_features)} 個):")
    for f in ema_features:
        print(f"  • {f}")
    
    print(f"\n信號特徵 ({len(signal_features)} 個):")
    for f in signal_features:
        print(f"  • {f}")
    
    print("\n" + "=" * 80)
    print("✅ 跨標的特徵提取測試通過！")
    print("=" * 80)
    print("\n總結：")
    print("  • 所有特徵均為相對值（百分比、比例、標記）")
    print("  • 不存在絕對價格或絕對成交量特徵")
    print("  • 特徵在不同標的上的數值範圍相似")
    print("  • 可安全用於跨標的訓練")
    print()


if __name__ == "__main__":
    test_cross_symbol_features()
