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


# 浮點 Pearson 相關係數之上界：|r| 數學上 ≤ 1，但 IEEE-754 累積誤差可使實算值超出 1 數個 ulp
# （本機真實 ETHUSDT 1h 實得 1.0000000000000004，為兩欄線性相依）。原斷言 `<= 1.0` 為精確比較，
# 對浮點運算本身錯誤；改以 1e-12 之數值容差表達同一數學上界（TESTREG b5）。
_CORR_UPPER = 1.0 + 1e-12


def _oracle_corr_pairs(features_df, feature_names, threshold):
    """獨立 oracle：以 numpy.corrcoef（非 pandas.corr）重算去 NaN 列後之 |r| 上三角。"""
    clean = features_df[feature_names].dropna().to_numpy(dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.abs(np.corrcoef(clean, rowvar=False))
    iu = np.triu_indices(len(feature_names), k=1)
    upper = corr[iu]
    max_corr = float(np.nanmax(upper))
    pairs = {
        (feature_names[i], feature_names[j]): float(corr[i, j])
        for i, j in zip(*iu)
        if np.isfinite(corr[i, j]) and corr[i, j] > threshold
    }
    return max_corr, pairs


def test_feature_validation(sample_features):
    """測試完整驗證流程：NaN／Inf 偵測、填補後通過、最大相關性與獨立重算一致。"""
    features_df, feature_names = sample_features
    validator = FeatureValidator(correlation_threshold=0.95)

    # 未填補之真實特徵含暖機 NaN ⇒ 驗證器必須偵測到（否則下方「填補後無 NaN」無鑑別力）
    assert features_df[feature_names].isna().to_numpy().any(), "前提不成立：真實特徵無暖機 NaN"
    raw_result = validator.validate(features_df, feature_names)
    assert raw_result.has_nan, "未填補之 NaN 未被偵測"
    assert not raw_result.is_valid()
    assert any("NaN" in w for w in raw_result.warnings)

    # 前向填補 NaN
    features_df[feature_names] = features_df[feature_names].ffill()
    features_df[feature_names] = features_df[feature_names].fillna(0)

    result = validator.validate(features_df, feature_names)

    # 檢查驗證結果
    assert not result.has_nan, "不應有 NaN 值 (已填補)"
    assert not result.has_inf, "不應有 Inf 值"
    assert result.is_valid()
    oracle_max, oracle_pairs = _oracle_corr_pairs(features_df, feature_names, 0.95)
    assert 0.0 <= result.max_correlation <= _CORR_UPPER
    assert result.max_correlation == pytest.approx(oracle_max, abs=1e-9)
    assert len(result.high_correlation_pairs) == len(oracle_pairs)

    # Inf 偵測：注入單一 inf ⇒ has_inf 轉 True、驗證不通過
    with_inf = features_df.copy()
    with_inf.loc[with_inf.index[10], feature_names[0]] = np.inf
    inf_result = validator.validate(with_inf, feature_names)
    assert inf_result.has_inf and not inf_result.is_valid()


def test_validate_correlation_threshold(sample_features):
    """測試高相關性檢測 (相關性 > 0.95)：回傳之高相關對＝獨立重算之高相關對（不多不少）。"""
    features_df, feature_names = sample_features
    validator = FeatureValidator(correlation_threshold=0.95)

    # 前向填補
    features_df[feature_names] = features_df[feature_names].ffill()
    features_df[feature_names] = features_df[feature_names].fillna(0)

    max_corr, high_corr_pairs = validator.validate_correlation(features_df, feature_names)

    assert 0.0 <= max_corr <= _CORR_UPPER

    # 檢查高相關性對
    for feat1, feat2, corr in high_corr_pairs:
        assert corr > 0.95, f"相關性應 > 0.95: {feat1} <-> {feat2} = {corr}"

    oracle_max, oracle_pairs = _oracle_corr_pairs(features_df, feature_names, 0.95)
    assert oracle_pairs, "前提不成立：真實特徵無任何高相關對，完整性斷言無鑑別力"
    assert max_corr == pytest.approx(oracle_max, abs=1e-9)
    got = {(a, b): c for a, b, c in high_corr_pairs}
    # 排除落在門檻 ±1e-9 之邊界對（兩種實作之浮點差可合法翻轉）
    boundary = {k for k, v in oracle_pairs.items() if abs(v - 0.95) <= 1e-9}
    assert set(got) - boundary == set(oracle_pairs) - boundary, (
        f"高相關對不符：多 {sorted(set(got) - set(oracle_pairs))}、漏 {sorted(set(oracle_pairs) - set(got))}"
    )
    for key, corr in got.items():
        assert corr == pytest.approx(oracle_pairs[key], abs=1e-9)


def test_validate_no_future_leak(sample_features):
    """測試無未來函數 (基於時間序列)。

    TESTREG b5 改寫：`FeatureValidator.validate_no_future_leak` 實作只檢查時間戳遞增
    （feature_validator.py 約 :345-360），單靠它不能證明「無未來函數」。本條改以真 MR 直接驗
    特徵產出：截斷 t 之後之 K 線重算，t 以前之特徵值逐位元組不變（含 NaN 位置）；
    並保留驗證器之時間戳單調契約（正例通過、亂序必拒）。
    """
    features_df, feature_names = sample_features
    validator = FeatureValidator()

    # ① 真 MR：截斷未來 K 線不得改變過去之特徵值
    with h5py.File("data_cache/kline_cache.h5", 'r') as f:
        data = f['ETHUSDT/1h/data'][:500]
    kline = pd.DataFrame(data)
    params = StrategyParams(
        strategy_type='ema_three_line',
        params={'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6}
    )
    extractor = FeatureExtractor()
    for cut in (300, 450):
        truncated, truncated_names = extractor.extract_features_from_strategy(
            kline.iloc[:cut].copy(), params, include_basic_features=True
        )
        assert truncated_names == feature_names
        past_full = features_df[feature_names].iloc[:cut].reset_index(drop=True)
        past_trunc = truncated[feature_names].reset_index(drop=True)
        leaked = [
            c for c in feature_names
            if not np.array_equal(
                past_full[c].to_numpy(dtype=np.float64),
                past_trunc[c].to_numpy(dtype=np.float64),
                equal_nan=True,
            )
        ]
        assert not leaked, f"截斷於 {cut} 後，過去特徵值改變（看到未來資料）：{leaked}"

    # ② 驗證器之時間戳單調契約：正例通過、亂序必拒
    result = validator.validate_no_future_leak(features_df, feature_names)
    assert result == True, "檢測到未來函數"
    shuffled = features_df.iloc[::-1].reset_index(drop=True)
    assert validator.validate_no_future_leak(shuffled, feature_names) == False


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
