"""
MACD (Moving Average Convergence Divergence) Extractor

完全動態的 MACD 指標提取器範例

Author: AI Agent
Date: 2026-01-11
"""

import pandas as pd
from typing import Dict, List, Tuple
from momentum.FeatureEngineering.strategy_registry import BaseStrategyExtractor
from momentum.FeatureEngineering.feature_config import FeatureNamingConfig
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class MACDExtractor(BaseStrategyExtractor):
    """
    MACD 指標特徵提取器
    
    支援特徵：
    - MACD 線（快線 - 慢線）
    - 信號線（MACD 線的移動平均）
    - 柱狀圖（MACD 線 - 信號線）
    - 交叉信號（MACD 穿越信號線）
    """
    
    def validate_params(self, params: Dict) -> None:
        """驗證 MACD 參數"""
        required = ['fast', 'slow', 'signal']
        missing = [p for p in required if p not in params]
        
        if missing:
            raise ValueError(f"MACD 策略缺少必要參數: {missing}")
        
        fast = params['fast']
        slow = params['slow']
        signal = params['signal']
        
        if not (fast < slow):
            raise ValueError(
                f"MACD 參數必須滿足 fast < slow, "
                f"收到: fast={fast}, slow={slow}"
            )
        
        if signal < 1:
            raise ValueError(f"signal 必須 >= 1, 收到: {signal}")
    
    def extract(
        self,
        df: pd.DataFrame,
        params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        提取 MACD 策略特徵
        
        Args:
            df: K線數據
            params: {'fast': 12, 'slow': 26, 'signal': 9}
            data_source: 數據源
        
        Returns:
            (features_df, feature_names)
        """
        feature_names = []
        
        fast = params['fast']
        slow = params['slow']
        signal = params['signal']
        
        # 驗證數據源
        if data_source not in df.columns:
            raise ValueError(
                f"數據源 '{data_source}' 不存在於 DataFrame 中。"
                f"可用欄位: {df.columns.tolist()}"
            )
        
        logger.info(f"使用數據源 '{data_source}' 計算 MACD 特徵")
        
        # 獲取動態命名
        feature_name_mapping = FeatureNamingConfig.make_macd_feature_names(
            data_source, params
        )
        
        # 1. 計算 MACD 線
        ema_fast = df[data_source].ewm(span=fast, adjust=False).mean()
        ema_slow = df[data_source].ewm(span=slow, adjust=False).mean()
        
        macd_line_col = feature_name_mapping['macd_line']
        df[macd_line_col] = ema_fast - ema_slow
        feature_names.append(macd_line_col)
        
        # 2. 計算信號線
        macd_signal_col = feature_name_mapping['macd_signal']
        df[macd_signal_col] = df[macd_line_col].ewm(span=signal, adjust=False).mean()
        feature_names.append(macd_signal_col)
        
        # 3. 計算柱狀圖
        histogram_col = feature_name_mapping['macd_histogram']
        df[histogram_col] = df[macd_line_col] - df[macd_signal_col]
        feature_names.append(histogram_col)
        
        # 4. 交叉信號（MACD 穿越信號線）
        cross_col = feature_name_mapping['macd_cross']
        macd_above = (df[macd_line_col] > df[macd_signal_col]).astype(bool)
        macd_above_prev = macd_above.shift(1).fillna(False)
        df[cross_col] = (macd_above & (~macd_above_prev)).astype(float)
        feature_names.append(cross_col)
        
        return df, feature_names


# 註冊到系統（範例）
if __name__ == "__main__":
    from momentum.FeatureEngineering.strategy_registry import StrategyRegistry
    import numpy as np
    
    print("=" * 60)
    print("MACD Extractor 測試")
    print("=" * 60)
    
    # 註冊
    registry = StrategyRegistry()
    registry.register_strategy(
        name='macd',
        description='Moving Average Convergence Divergence',
        required_params=['fast', 'slow', 'signal'],
        extractor=MACDExtractor()
    )
    
    print(f"✅ 註冊 MACD 策略")
    print(f"可用策略: {registry.list_strategies()}")
    
    # 建立模擬數據
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='12h'),
        'close': np.random.uniform(40000, 50000, 100),
    })
    
    # 測試提取
    params = {'fast': 12, 'slow': 26, 'signal': 9}
    
    try:
        features_df, feature_names = registry.extract_features(
            strategy_name='macd',
            df=df,
            params=params,
            data_source='close'
        )
        print(f"✅ 成功提取 {len(feature_names)} 個特徵")
        print("特徵名稱:")
        for i, name in enumerate(feature_names, 1):
            print(f"  {i}. {name}")
    except Exception as e:
        print(f"❌ 特徵提取失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)
