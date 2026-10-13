"""
測試 volume_threshold = 0 的修復

驗證：
1. volume_threshold = 0 應該能通過驗證
2. volume_threshold = 0.5 應該能通過驗證
3. volume_threshold = 1.0 應該能通過驗證
4. volume_threshold = -0.1 應該失敗
5. volume_threshold = 1.1 應該失敗
"""

from momentum.FeatureEngineering.indicators.ema_extractor import EMAExtractor
import pandas as pd
import numpy as np
from api.core.logging import get_logger
import pytest

logger = get_logger(__name__)

def test_volume_threshold_validation():
    """測試 volume_threshold 參數驗證"""
    extractor = EMAExtractor()
    
    test_cases = [
        (0, True, "volume_threshold = 0 (不考慮成交量)"),
        (0.5, True, "volume_threshold = 0.5 (正常值)"),
        (1.0, True, "volume_threshold = 1.0 (最大值)"),
        (0.6, True, "volume_threshold = 0.6 (預設值)"),
        (-0.1, False, "volume_threshold = -0.1 (負數)"),
        (1.1, False, "volume_threshold = 1.1 (超過範圍)"),
    ]
    
    print("=" * 70)
    print("測試 volume_threshold 參數驗證")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for value, should_pass, description in test_cases:
        params = {
            'ema_short': 5,
            'ema_mid': 20,
            'ema_long': 60,
            'volume_threshold': value
        }
        
        try:
            extractor.validate_params(params)
            if should_pass:
                print(f"✅ PASS: {description}")
                passed += 1
            else:
                print(f"❌ FAIL: {description} - 應該失敗但通過了")
                failed += 1
        except ValueError as e:
            if not should_pass:
                print(f"✅ PASS: {description} - 正確拋出錯誤: {e}")
                passed += 1
            else:
                print(f"❌ FAIL: {description} - 不應該失敗: {e}")
                failed += 1
    
    print("\n" + "=" * 70)
    print(f"測試結果: {passed} 通過, {failed} 失敗")
    print("=" * 70)
    
    return failed == 0


def test_volume_threshold_zero_feature_extraction():
    """測試 volume_threshold = 0 時的特徵提取"""
    print("\n" + "=" * 70)
    print("測試 volume_threshold = 0 時的特徵提取")
    print("=" * 70)
    
    # 建立模擬數據
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='12h').astype(int) // 10**6,
        'open_time': pd.date_range('2024-01-01', periods=100, freq='12h').astype(int) // 10**6,
        'close': np.random.uniform(40000, 50000, 100),
        'open': np.random.uniform(40000, 50000, 100),
        'high': np.random.uniform(45000, 55000, 100),
        'low': np.random.uniform(35000, 45000, 100),
        'volume': np.random.uniform(1000, 10000, 100),
        'taker_ratio': np.random.uniform(0.3, 0.8, 100),
    })
    
    extractor = EMAExtractor()
    params = {
        'ema_short': 5,
        'ema_mid': 20,
        'ema_long': 60,
        'volume_threshold': 0  # 測試 0 值
    }
    
    try:
        features_df, feature_names = extractor.extract(df, params, 'close')
        print(f"✅ 成功提取 {len(feature_names)} 個特徵")
        print(f"\n特徵名稱:")
        for i, name in enumerate(feature_names, 1):
            print(f"  {i}. {name}")
        
        # 檢查 volume_spike 特徵（當 threshold=0 時，所有正值都算 spike）
        volume_spike_col = [col for col in features_df.columns if 'volume_spike' in col][0]
        spike_count = features_df[volume_spike_col].sum()
        total_positive_taker = (df['taker_ratio'] > 0).sum()
        
        print(f"\n驗證 volume_spike 邏輯:")
        print(f"  - volume_spike 計數: {spike_count}")
        print(f"  - 正 taker_ratio 計數: {total_positive_taker}")
        print(f"  - 符合預期: {spike_count == total_positive_taker}")
        
        # 檢查 taker_ratio_distance 特徵
        taker_dist_col = [col for col in features_df.columns if 'taker_ratio_distance' in col][0]
        print(f"\ntaker_ratio_distance 範例值:")
        print(f"  前 5 筆: {features_df[taker_dist_col].head().tolist()}")
        
        return True
    except Exception as e:
        print(f"❌ 特徵提取失敗: {e}")
        import traceback
        traceback.print_exc()
        return False



@pytest.mark.parametrize("value,ok", [(0, True), (0.5, True), (1.0, True), (0.6, True), (-0.1, False), (1.1, False)])
def test_volume_threshold_validation_strict(value, ok):
    """純增：上列 test_volume_threshold_validation 只累計結果並 return 布林（pytest 只警告、永不失敗）；本案逐值斷言——
    0–1（含端點）通過、範圍外拋 ValueError。"""
    params = {"ema_short": 5, "ema_mid": 20, "ema_long": 60, "volume_threshold": value}
    if ok:
        assert EMAExtractor().validate_params(params) is None
    else:
        with pytest.raises(ValueError, match="volume_threshold"):
            EMAExtractor().validate_params(params)


def test_volume_threshold_zero_spike_and_distance():
    """純增：threshold＝0 時 volume_spike＝(taker_ratio > 0)、taker_ratio_distance＝taker_ratio（上列
    test_volume_threshold_zero_feature_extraction 只印出並吞例外回 False）。taker_ratio 含非正值使 spike 非全 1。"""
    rng = np.random.default_rng(7)
    n = 100
    t = pd.date_range("2024-01-01", periods=n, freq="12h").astype("int64") // 10**6
    taker = rng.uniform(-0.2, 0.8, n)
    df = pd.DataFrame({"timestamp": t, "open_time": t, "close": rng.uniform(40000, 50000, n),
                       "open": rng.uniform(40000, 50000, n), "high": rng.uniform(45000, 55000, n),
                       "low": rng.uniform(35000, 45000, n), "volume": rng.uniform(1000, 10000, n),
                       "taker_ratio": taker})
    features_df, _names = EMAExtractor().extract(
        df, {"ema_short": 5, "ema_mid": 20, "ema_long": 60, "volume_threshold": 0}, "close")
    spike = [c for c in features_df.columns if "volume_spike" in c]
    dist = [c for c in features_df.columns if "taker_ratio_distance" in c]
    assert len(spike) == 1 and len(dist) == 1
    np.testing.assert_array_equal(features_df[spike[0]].to_numpy(), (taker > 0).astype(float))
    np.testing.assert_allclose(features_df[dist[0]].to_numpy(), taker)

if __name__ == "__main__":
    test1_passed = test_volume_threshold_validation()
    test2_passed = test_volume_threshold_zero_feature_extraction()
    
    print("\n" + "=" * 70)
    if test1_passed and test2_passed:
        print("🎉 所有測試通過！volume_threshold = 0 的修復驗證成功")
    else:
        print("⚠️  部分測試失敗，請檢查")
    print("=" * 70)
