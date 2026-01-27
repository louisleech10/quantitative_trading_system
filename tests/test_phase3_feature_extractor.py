"""
Phase 3 測試 - 驗證動態特徵命名系統

測試更新後的 feature_extractor.py 功能
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pandas as pd
import h5py
from momentum.FeatureEngineering import FeatureExtractor, StrategyParams
from momentum.FeatureEngineering.strategy_registry import StrategyRegistry
from momentum.FeatureEngineering.indicators import RSIExtractor, MACDExtractor


def test_1_basic_ema_extraction():
    """測試 1: 基本 EMA 特徵提取（新命名）"""
    print("\n" + "="*60)
    print("測試 1: 基本 EMA 特徵提取（新命名）")
    print("="*60)
    
    # 載入數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:500]
    df = pd.DataFrame(data)
    
    # 建立提取器
    extractor = FeatureExtractor()
    
    # EMA 策略參數
    params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    
    # 提取特徵
    features_df, feature_names = extractor.extract_features_from_strategy(
        df, params, include_basic_features=True
    )
    
    # 驗證新命名格式
    expected_features = [
        'close_ema5_value',
        'close_ema20_value',
        'close_ema60_value',
        'close_ema5_20_distance',
        'close_ema20_60_distance',
        'close_ema_trend_aligned',
        'close_ema_entry_signal_score'
    ]
    
    found = []
    missing = []
    
    for feature in expected_features:
        if feature in feature_names:
            found.append(feature)
        else:
            missing.append(feature)
    
    print(f"✅ 找到 {len(found)}/{len(expected_features)} 個預期特徵")
    print(f"   找到的特徵: {found[:5]}...")
    
    if missing:
        print(f"⚠️  缺少的特徵: {missing}")
        print(f"   實際特徵: {feature_names[:10]}...")
    
    assert len(missing) == 0, f"缺少特徵: {missing}"
    print("✅ 測試 1 通過")


def test_2_different_parameters():
    """測試 2: 不同參數生成不同特徵名稱"""
    print("\n" + "="*60)
    print("測試 2: 不同參數生成不同特徵名稱")
    print("="*60)
    
    # 載入數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:500]
    df = pd.DataFrame(data)
    
    extractor = FeatureExtractor()
    
    # 參數組 1: EMA(5,20,60)
    params1 = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    
    # 參數組 2: EMA(10,30,90)
    params2 = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 10, 'ema_mid': 30, 'ema_long': 90, 'volume_threshold': 0.7},
        data_source='close'
    )
    
    # 提取特徵
    _, names1 = extractor.extract_features_from_strategy(df.copy(), params1, include_basic_features=False)
    _, names2 = extractor.extract_features_from_strategy(df.copy(), params2, include_basic_features=False)
    
    # 驗證
    assert 'close_ema5_value' in names1, "參數組1應包含 close_ema5_value"
    assert 'close_ema10_value' in names2, "參數組2應包含 close_ema10_value"
    assert 'close_ema5_20_distance' in names1
    assert 'close_ema10_30_distance' in names2
    
    print(f"✅ 參數組1特徵數: {len(names1)}")
    print(f"✅ 參數組2特徵數: {len(names2)}")
    print(f"   參數組1範例: {names1[:3]}")
    print(f"   參數組2範例: {names2[:3]}")
    print("✅ 測試 2 通過")


def test_3_different_data_sources():
    """測試 3: 不同數據源生成不同特徵名稱"""
    print("\n" + "="*60)
    print("測試 3: 不同數據源生成不同特徵名稱")
    print("="*60)
    
    # 載入數據
    hdf5_path = "data_cache/kline_cache.h5"
    with h5py.File(hdf5_path, 'r') as f:
        data = f['ETHUSDT/1h/data'][:500]
    df = pd.DataFrame(data)
    
    extractor = FeatureExtractor()
    
    # 使用 close 數據源
    params_close = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    
    # 使用 volume 數據源
    params_volume = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='volume'
    )
    
    # 提取特徵
    _, names_close = extractor.extract_features_from_strategy(df.copy(), params_close, include_basic_features=False)
    _, names_volume = extractor.extract_features_from_strategy(df.copy(), params_volume, include_basic_features=False)
    
    # 驗證
    assert 'close_ema5_value' in names_close
    assert 'volume_ema5_value' in names_volume
    assert 'close_ema5_value' not in names_volume, "volume特徵不應包含close前綴"
    
    print(f"✅ Close 特徵數: {len(names_close)}")
    print(f"✅ Volume 特徵數: {len(names_volume)}")
    print(f"   Close範例: {names_close[:3]}")
    print(f"   Volume範例: {names_volume[:3]}")
    print("✅ 測試 3 通過")


def test_4_multi_indicator_integration():
    """測試 4: 多指標整合（EMA + RSI + MACD）"""
    print("\n" + "="*60)
    print("測試 4: 多指標整合（EMA + RSI + MACD）")
    print("="*60)
    
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
    
    # EMA 特徵
    params_ema = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6},
        data_source='close'
    )
    _, names_ema = extractor.extract_features_from_strategy(df.copy(), params_ema, include_basic_features=False)
    
    # RSI 特徵
    params_rsi = StrategyParams(
        strategy_type='rsi',
        params={'period': 14, 'overbought': 70, 'oversold': 30},
        data_source='close'
    )
    _, names_rsi = extractor.extract_features_from_strategy(df.copy(), params_rsi, include_basic_features=False)
    
    # MACD 特徵
    params_macd = StrategyParams(
        strategy_type='macd',
        params={'fast': 12, 'slow': 26, 'signal': 9},
        data_source='close'
    )
    _, names_macd = extractor.extract_features_from_strategy(df.copy(), params_macd, include_basic_features=False)
    
    # 合併並檢查衝突
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
    
    assert not has_collision, "多指標整合存在特徵名稱衝突"
    print("✅ 測試 4 通過")


def run_all_tests():
    """執行所有測試"""
    print("\n" + "="*60)
    print("Phase 3 測試 - 動態特徵命名系統驗證")
    print("="*60)
    
    tests = [
        ("基本 EMA 特徵提取", test_1_basic_ema_extraction),
        ("不同參數生成不同名稱", test_2_different_parameters),
        ("不同數據源生成不同名稱", test_3_different_data_sources),
        ("多指標整合", test_4_multi_indicator_integration)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ 測試失敗: {name}")
            print(f"   錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)
    print(f"✅ 通過: {passed}/{len(tests)}")
    print(f"❌ 失敗: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有測試通過！Phase 3 完成！")
        return True
    else:
        print("\n⚠️  部分測試失敗，需要修復")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
