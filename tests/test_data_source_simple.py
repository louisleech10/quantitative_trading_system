#!/usr/bin/env python3
"""
最簡單的 data_source 測試 - 直接測試 extract_ema_features
"""

import pandas as pd
import numpy as np
from momentum.FeatureEngineering.feature_extractor import FeatureExtractor
from momentum.FeatureEngineering.feature_config import FeatureNamingConfig

# 建立簡單的測試數據
np.random.seed(42)
df = pd.DataFrame({
    'close': [3000, 3050, 3100, 3080, 3120] * 20,  # 100 rows
    'volume': [5000, 6000, 5500, 5800, 6200] * 20,
    'taker_ratio': [0.5, 0.55, 0.52, 0.53, 0.54] * 20
})

ema_params = {
    'ema_short': 5,
    'ema_mid': 20,
    'ema_long': 60,
    'volume_threshold': 0.6
}

extractor = FeatureExtractor()

print("="*60)
print("測試不同 data_source 的 EMA 計算")
print("="*60)

# 測試 1: close
print("\n1. data_source='close'")
result_df, feature_names = extractor.extract_ema_features(df.copy(), ema_params, data_source='close')
close_mapping = FeatureNamingConfig.make_ema_feature_names('close', ema_params)
print(f"   EMA_5 最後值: {result_df[close_mapping['ema_short']].iloc[-1]:.4f}")
print(f"   EMA_20 最後值: {result_df[close_mapping['ema_mid']].iloc[-1]:.4f}")

close_ema5 = result_df[close_mapping['ema_short']].iloc[-1]

# 測試 2: volume
print("\n2. data_source='volume'")
result_df, feature_names = extractor.extract_ema_features(df.copy(), ema_params, data_source='volume')
volume_mapping = FeatureNamingConfig.make_ema_feature_names('volume', ema_params)
print(f"   EMA_5 最後值: {result_df[volume_mapping['ema_short']].iloc[-1]:.4f}")
print(f"   EMA_20 最後值: {result_df[volume_mapping['ema_mid']].iloc[-1]:.4f}")

volume_ema5 = result_df[volume_mapping['ema_short']].iloc[-1]

# 測試 3: taker_ratio
print("\n3. data_source='taker_ratio'")
result_df, feature_names = extractor.extract_ema_features(df.copy(), ema_params, data_source='taker_ratio')
tr_mapping = FeatureNamingConfig.make_ema_feature_names('taker_ratio', ema_params)
print(f"   EMA_5 最後值: {result_df[tr_mapping['ema_short']].iloc[-1]:.4f}")
print(f"   EMA_20 最後值: {result_df[tr_mapping['ema_mid']].iloc[-1]:.4f}")

taker_ema5 = result_df[tr_mapping['ema_short']].iloc[-1]

# 驗證結果
print("\n" + "="*60)
print("驗證結果")
print("="*60)

# 不同 data_source 應該產生不同的 EMA 值
if close_ema5 != volume_ema5 and close_ema5 != taker_ema5:
    print("✅ 成功：不同 data_source 產生不同的 EMA 值")
    print(f"   close EMA_5: {close_ema5:.4f}")
    print(f"   volume EMA_5: {volume_ema5:.4f}")
    print(f"   taker_ratio EMA_5: {taker_ema5:.4f}")
    print("\n✅✅✅ data_source 參數修復成功！✅✅✅")
else:
    print("❌ 失敗：data_source 沒有生效")
    exit(1)
