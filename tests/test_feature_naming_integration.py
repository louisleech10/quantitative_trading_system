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


def test_close_source_expected_feature_names():
    """純增：上列四支只印出比對結果或 return 布林（pytest 只警告、永不失敗）；本組逐一斷言。CLOSE 數據源之 EMA(5,20,60)
    特徵名含上列 test_close_data_source 所列之預期名。"""
    np.random.seed(21)
    _df, names = FeatureExtractor().extract_features_from_strategy(
        create_mock_kline_data(), StrategyParams(strategy_type='ema_three_line', data_source='close',
                                                 params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60,
                                                         'volume_threshold': 0.6}))
    expected = {'close_ema5_value', 'close_ema20_value', 'close_ema60_value', 'close_ema5-20_distance',
                'close_ema20-60_distance', 'close_ema_trend_aligned', 'close_ema5-20_cross_signal'}
    assert expected <= set(names), sorted(expected - set(names))


def test_volume_source_expected_feature_names():
    """純增：VOLUME 數據源之 EMA(6,15,28) 特徵名含上列 test_volume_data_source 所列之預期名。"""
    np.random.seed(22)
    _df, names = FeatureExtractor().extract_features_from_strategy(
        create_mock_kline_data(), StrategyParams(strategy_type='ema_three_line', data_source='volume',
                                                 params={'ema_short': 6, 'ema_mid': 15, 'ema_long': 28,
                                                         'volume_threshold': 0.7}))
    expected = {'volume_ema6_value', 'volume_ema15_value', 'volume_ema28_value', 'volume_ema6-15_distance',
                'volume_ema15-28_distance', 'volume_ema_trend_aligned'}
    assert expected <= set(names), sorted(expected - set(names))


def test_strategy_names_across_sources_share_only_source_independent_columns():
    """純增：不同數據源（close、volume）同參數之策略特徵（不含基礎特徵）間，只有與數據源無關之欄（只依 taker_ratio 與
    門檻：volume_spike_*、taker_ratio_distance_*）同名，且兩邊值逐列相等（同值重複、非衝突）——上列 test_no_collision
    宣稱「無衝突」但只印出。註：同數據源不同參數時另有多欄同名而值不同（例 close_ema_trend_aligned），屬生產端命名
    缺陷、另案處理（handoffs/run_receipts/testreg_probes/b3/task32_triage.md），本案不把該行為寫成預期。"""
    np.random.seed(23)
    df = create_mock_kline_data()

    def run(source, short, mid, long, thr):
        return FeatureExtractor().extract_features_from_strategy(
            df.copy(), StrategyParams(strategy_type='ema_three_line', data_source=source,
                                      params={'ema_short': short, 'ema_mid': mid, 'ema_long': long,
                                              'volume_threshold': thr}),
            include_basic_features=False)
    out_ca, close_a = run('close', 5, 20, 60, 0.6)
    out_va, volume_a = run('volume', 5, 20, 60, 0.6)
    assert close_a and volume_a
    shared = sorted(set(close_a) & set(volume_a))
    assert all(n.startswith(('volume_spike_', 'taker_ratio_distance_')) for n in shared), shared
    for n in shared:
        np.testing.assert_array_equal(out_ca[n].to_numpy(), out_va[n].to_numpy())


def test_close_source_expected_names_are_returned_columns():
    """純增（審碼 r2 CODEX-R2-P2-02）：上列 test_close_source_expected_feature_names 只驗名稱清單；本案同參數另驗回傳表
    確含同名欄（名稱清單與資料欄不得脫鉤）。"""
    np.random.seed(21)
    df, names = FeatureExtractor().extract_features_from_strategy(
        create_mock_kline_data(), StrategyParams(strategy_type='ema_three_line', data_source='close',
                                                 params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60,
                                                         'volume_threshold': 0.6}))
    expected = {'close_ema5_value', 'close_ema20_value', 'close_ema60_value', 'close_ema5-20_distance',
                'close_ema20-60_distance', 'close_ema_trend_aligned', 'close_ema5-20_cross_signal'}
    assert expected <= set(names), sorted(expected - set(names))
    assert expected <= set(df.columns), sorted(expected - set(df.columns))


def test_volume_source_expected_names_are_returned_columns():
    """純增（審碼 r2 CODEX-R2-P2-02）：VOLUME 數據源 EMA(6,15,28) 之預期名同時在名稱清單與回傳表之欄中。"""
    np.random.seed(22)
    df, names = FeatureExtractor().extract_features_from_strategy(
        create_mock_kline_data(), StrategyParams(strategy_type='ema_three_line', data_source='volume',
                                                 params={'ema_short': 6, 'ema_mid': 15, 'ema_long': 28,
                                                         'volume_threshold': 0.7}))
    expected = {'volume_ema6_value', 'volume_ema15_value', 'volume_ema28_value', 'volume_ema6-15_distance',
                'volume_ema15-28_distance', 'volume_ema_trend_aligned'}
    assert expected <= set(names), sorted(expected - set(names))
    assert expected <= set(df.columns), sorted(expected - set(df.columns))

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
