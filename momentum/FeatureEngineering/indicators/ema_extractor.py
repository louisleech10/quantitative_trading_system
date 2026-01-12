"""
EMA (Exponential Moving Average) Extractor

從 feature_extractor.py 重構出來的 EMA 指標提取器
支援完全動態的特徵命名和參數配置

Author: AI Agent
Date: 2026-01-11
"""

import pandas as pd
from typing import Dict, List, Tuple
from momentum.FeatureEngineering.strategy_registry import BaseStrategyExtractor
from momentum.FeatureEngineering.feature_config import FeatureNamingConfig
from api.core.logging import get_logger

logger = get_logger(__name__)


class EMAExtractor(BaseStrategyExtractor):
    """
    EMA 三線策略特徵提取器
    
    支援特徵：
    - 三條 EMA 線（short, mid, long）
    - EMA 距離特徵
    - EMA 趨勢對齊
    - EMA 交叉信號
    - Volume spike 和 taker ratio distance
    """
    
    def validate_params(self, params: Dict) -> None:
        """驗證 EMA 參數"""
        required = ['ema_short', 'ema_mid', 'ema_long', 'volume_threshold']
        missing = [p for p in required if p not in params]
        
        if missing:
            raise ValueError(f"EMA 策略缺少必要參數: {missing}")
        
        # 驗證參數順序
        short = params['ema_short']
        mid = params['ema_mid']
        long = params['ema_long']
        
        if not (short < mid < long):
            raise ValueError(
                f"EMA 參數必須滿足 short < mid < long, "
                f"收到: short={short}, mid={mid}, long={long}"
            )
        
        # 驗證 volume_threshold 範圍
        volume_threshold = params['volume_threshold']
        if not (0 < volume_threshold < 1):
            raise ValueError(
                f"volume_threshold 必須在 0-1 之間, 收到: {volume_threshold}"
            )
    
    def extract(
        self,
        df: pd.DataFrame,
        params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        提取 EMA 策略特徵
        
        Args:
            df: K線數據
            params: {'ema_short': 5, 'ema_mid': 20, 'ema_long': 60, 'volume_threshold': 0.6}
            data_source: 數據源
        
        Returns:
            (features_df, feature_names)
        """
        feature_names = []
        
        short = params['ema_short']
        mid = params['ema_mid']
        long = params['ema_long']
        volume_threshold = params['volume_threshold']
        
        # 驗證數據源存在
        if data_source not in df.columns:
            raise ValueError(
                f"數據源 '{data_source}' 不存在於 DataFrame 中。"
                f"可用欄位: {df.columns.tolist()}"
            )
        
        logger.info(f"使用數據源 '{data_source}' 計算 EMA 特徵")
        
        # 使用動態命名系統生成所有特徵名稱
        feature_name_mapping = FeatureNamingConfig.make_ema_feature_names(
            data_source, params
        )
        
        # 1. EMA short 值
        ema_short_col = feature_name_mapping['ema_short']
        df[ema_short_col] = df[data_source].ewm(span=short, adjust=False).mean()
        feature_names.append(ema_short_col)
        
        # 2. EMA mid 值
        ema_mid_col = feature_name_mapping['ema_mid']
        df[ema_mid_col] = df[data_source].ewm(span=mid, adjust=False).mean()
        feature_names.append(ema_mid_col)
        
        # 3. EMA long 值
        ema_long_col = feature_name_mapping['ema_long']
        df[ema_long_col] = df[data_source].ewm(span=long, adjust=False).mean()
        feature_names.append(ema_long_col)
        
        # 4. EMA(short) 與 EMA(mid) 距離
        ema_dist_short_mid_col = feature_name_mapping['ema_distance_short_mid']
        df[ema_dist_short_mid_col] = (
            (df[ema_short_col] - df[ema_mid_col]) / (df[ema_mid_col] + 1e-10)
        )
        feature_names.append(ema_dist_short_mid_col)
        
        # 5. EMA(mid) 與 EMA(long) 距離
        ema_dist_mid_long_col = feature_name_mapping['ema_distance_mid_long']
        df[ema_dist_mid_long_col] = (
            (df[ema_mid_col] - df[ema_long_col]) / (df[ema_long_col] + 1e-10)
        )
        feature_names.append(ema_dist_mid_long_col)
        
        # 6. EMA 趨勢對齊
        ema_trend_col = f"{data_source}_ema_trend_aligned"
        df[ema_trend_col] = (
            (df[ema_short_col] > df[ema_mid_col]) & 
            (df[ema_mid_col] > df[ema_long_col])
        ).astype(float)
        feature_names.append(ema_trend_col)
        
        # 7. EMA(short) 穿越 EMA(mid) 信號
        ema_cross_col = feature_name_mapping['ema_cross_signal']
        ema_short_above = (df[ema_short_col] > df[ema_mid_col]).astype(bool)
        ema_short_above_prev = ema_short_above.shift(1).fillna(False)
        df[ema_cross_col] = (
            ema_short_above & (~ema_short_above_prev)
        ).astype(float)
        feature_names.append(ema_cross_col)
        
        # 8. Volume Threshold 特徵 - 成交量激增
        volume_spike_col = feature_name_mapping['volume_spike']
        df[volume_spike_col] = (
            df['taker_ratio'] > volume_threshold
        ).astype(float)
        feature_names.append(volume_spike_col)
        
        # 9. 主動買入比例與閾值距離
        taker_dist_col = feature_name_mapping['taker_ratio_distance']
        df[taker_dist_col] = (
            df['taker_ratio'] - volume_threshold
        )
        feature_names.append(taker_dist_col)
        
        return df, feature_names


# 測試代碼
if __name__ == "__main__":
    print("=" * 60)
    print("EMA Extractor 測試")
    print("=" * 60)
    
    # 建立模擬數據
    import numpy as np
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='12h'),
        'close': np.random.uniform(40000, 50000, 100),
        'volume': np.random.uniform(1000, 10000, 100),
        'taker_ratio': np.random.uniform(0.3, 0.8, 100),
    })
    
    # 測試提取
    extractor = EMAExtractor()
    params = {
        'ema_short': 5,
        'ema_mid': 20,
        'ema_long': 60,
        'volume_threshold': 0.6
    }
    
    try:
        extractor.validate_params(params)
        print("✅ 參數驗證通過")
    except Exception as e:
        print(f"❌ 參數驗證失敗: {e}")
    
    try:
        features_df, feature_names = extractor.extract(df, params, 'close')
        print(f"✅ 成功提取 {len(feature_names)} 個特徵")
        print("特徵名稱:")
        for i, name in enumerate(feature_names, 1):
            print(f"  {i}. {name}")
    except Exception as e:
        print(f"❌ 特徵提取失敗: {e}")
    
    print("=" * 60)
