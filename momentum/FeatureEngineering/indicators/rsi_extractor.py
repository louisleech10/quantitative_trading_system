"""
RSI (Relative Strength Index) Extractor

完全動態的 RSI 指標提取器範例

Author: AI Agent
Date: 2026-01-11
"""

import pandas as pd
from typing import Dict, List, Tuple
from momentum.FeatureEngineering.strategy_registry import BaseStrategyExtractor
from momentum.FeatureEngineering.feature_config import FeatureNamingConfig
from api.core.logging import get_logger

logger = get_logger(__name__)


class RSIExtractor(BaseStrategyExtractor):
    """
    RSI 指標特徵提取器
    
    支援特徵：
    - RSI 值
    - 超買信號（RSI > overbought）
    - 超賣信號（RSI < oversold）
    - RSI 動量（5期變化）
    """
    
    def validate_params(self, params: Dict) -> None:
        """驗證 RSI 參數"""
        if 'period' not in params:
            raise ValueError("RSI 策略需要 'period' 參數")
        
        period = params['period']
        if not (2 <= period <= 100):
            raise ValueError(f"RSI period 必須在 2-100 之間, 收到: {period}")
        
        # 可選參數驗證
        if 'overbought' in params:
            overbought = params['overbought']
            if not (50 <= overbought <= 100):
                raise ValueError(f"overbought 必須在 50-100 之間, 收到: {overbought}")
        
        if 'oversold' in params:
            oversold = params['oversold']
            if not (0 <= oversold <= 50):
                raise ValueError(f"oversold 必須在 0-50 之間, 收到: {oversold}")
    
    def extract(
        self,
        df: pd.DataFrame,
        params: Dict,
        data_source: str = 'close'
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        提取 RSI 策略特徵
        
        Args:
            df: K線數據
            params: {'period': 14, 'overbought': 70, 'oversold': 30}
            data_source: 數據源
        
        Returns:
            (features_df, feature_names)
        """
        feature_names = []
        
        period = params['period']
        overbought = params.get('overbought', 70)
        oversold = params.get('oversold', 30)
        
        # 驗證數據源
        if data_source not in df.columns:
            raise ValueError(
                f"數據源 '{data_source}' 不存在於 DataFrame 中。"
                f"可用欄位: {df.columns.tolist()}"
            )
        
        logger.info(f"使用數據源 '{data_source}' 計算 RSI 特徵")
        
        # 獲取動態命名
        feature_name_mapping = FeatureNamingConfig.make_rsi_feature_names(
            data_source, params
        )
        
        # 1. 計算 RSI 值
        delta = df[data_source].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        rsi_col = feature_name_mapping['rsi_value']
        df[rsi_col] = rsi
        feature_names.append(rsi_col)
        
        # 2. 超買信號
        overbought_col = feature_name_mapping['rsi_overbought']
        df[overbought_col] = (rsi > overbought).astype(float)
        feature_names.append(overbought_col)
        
        # 3. 超賣信號
        oversold_col = feature_name_mapping['rsi_oversold']
        df[oversold_col] = (rsi < oversold).astype(float)
        feature_names.append(oversold_col)
        
        # 4. RSI 動量（5期變化）
        momentum_col = feature_name_mapping['rsi_momentum']
        df[momentum_col] = rsi - rsi.shift(5)
        feature_names.append(momentum_col)
        
        return df, feature_names


# 註冊到系統（範例）
if __name__ == "__main__":
    from momentum.FeatureEngineering.strategy_registry import StrategyRegistry
    import numpy as np
    
    print("=" * 60)
    print("RSI Extractor 測試")
    print("=" * 60)
    
    # 註冊
    registry = StrategyRegistry()
    registry.register_strategy(
        name='rsi',
        description='Relative Strength Index',
        required_params=['period'],
        optional_params={'overbought': 70, 'oversold': 30},
        extractor=RSIExtractor()
    )
    
    print(f"✅ 註冊 RSI 策略")
    print(f"可用策略: {registry.list_strategies()}")
    
    # 建立模擬數據
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='12h'),
        'close': np.random.uniform(40000, 50000, 100),
    })
    
    # 測試提取
    params = {'period': 14, 'overbought': 70, 'oversold': 30}
    
    try:
        features_df, feature_names = registry.extract_features(
            strategy_name='rsi',
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
