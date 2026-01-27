#!/usr/bin/env python3
"""
簡單測試運行腳本 - Task 4.1 測試

直接執行測試，不使用 pytest runner
"""

import sys
from pathlib import Path

# 設定 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import h5py

from momentum.FeatureEngineering.feature_extractor import (
    FeatureExtractor,
    StrategyParams
)


def test_feature_extraction():
    """測試特徵提取"""
    print("=" * 60)
    print("測試 1: EMA 三線策略特徵提取")
    print("=" * 60)
    
    # 載入真實數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:1000]
    df = pd.DataFrame(data)
    
    print(f"載入數據: {len(df)} 行")
    
    # 建立策略參數
    params = StrategyParams(
        strategy_type='ema_three_line',
        data_source='close',  # 指定數據源
        params={
            'ema_short': 5,
            'ema_mid': 20,
            'ema_long': 60,
            'volume_threshold': 0.6
        }
    )
    
    # 提取特徵
    extractor = FeatureExtractor()
    features_df, feature_names = extractor.extract_features_from_strategy(
        df, params, include_basic_features=True
    )
    
    print(f"\n✅ 特徵提取成功")
    print(f"   - 樣本數: {len(features_df)}")
    print(f"   - 特徵數: {len(feature_names)}")
    print(f"   - 前 30 個特徵: {feature_names[:30]}")
    
    # 檢查必要特徵
    expected_features = [
        'price_change_pct', 'volume_change_pct',
        'ema_5', 'ema_20', 'ema_60',
        'ema_distance_5_20', 'ema_trend_aligned',
        'entry_signal_score'
    ]
    
    missing = [f for f in expected_features if f not in feature_names]
    if missing:
        print(f"\n❌ 缺少特徵: {missing}")
        return False
    else:
        print(f"\n✅ 所有必要特徵都存在")
    
    return True


def test_no_nan_inf():
    """測試無 NaN/Inf"""
    print("\n" + "=" * 60)
    print("測試 2: 檢查 NaN/Inf 值")
    print("=" * 60)
    
    # 載入數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:500]
    df = pd.DataFrame(data)
    
    params = StrategyParams(
        strategy_type='ema_three_line',
        data_source='close',  # 指定數據源
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6}
    )
    
    extractor = FeatureExtractor()
    features_df, feature_names = extractor.extract_features_from_strategy(
        df, params, include_basic_features=True
    )
    
    # 前向填補
    features_df[feature_names] = features_df[feature_names].fillna(method='ffill')
    features_df[feature_names] = features_df[feature_names].fillna(0)
    
    # 檢查 NaN
    nan_count = features_df[feature_names].isna().sum().sum()
    if nan_count > 0:
        print(f"❌ 發現 {nan_count} 個 NaN 值")
        return False
    else:
        print(f"✅ 無 NaN 值")
    
    # 檢查 Inf
    inf_count = np.isinf(features_df[feature_names]).sum().sum()
    if inf_count > 0:
        print(f"❌ 發現 {inf_count} 個 Inf 值")
        return False
    else:
        print(f"✅ 無 Inf 值")
    
    return True


def main():
    print("\n" + "=" * 60)
    print("Task 4.1 Feature Engineering - 簡易測試")
    print("=" * 60)
    
    tests = [
        test_feature_extraction,
        test_no_nan_inf,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ 測試失敗: {test_func.__name__}")
            print(f"   錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"測試結果: {passed} 通過, {failed} 失敗")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
