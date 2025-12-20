"""
三線排列策略實現

策略邏輯：短期EMA > 中期EMA > 長期EMA
當三條均線按順序排列時產生信號，適合趨勢明顯的市場。

Author: Claude (Phase 1 - Dynamic Parameters Refactoring)
Date: 2025-12-03
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from momentum.Indicators.indicator_engine import IndicatorEngine
from api.core.logging import get_logger

logger = get_logger("three_line_strategy")


def calculate_signals(
    kline_data: pd.DataFrame,
    indicators: Dict[str, pd.Series],
    params: Dict[str, Any]
) -> np.ndarray:
    """
    計算三線排列策略信號

    參數說明：
    - kline_data: K線數據（DataFrame，包含 open, high, low, close, volume 等列）
    - indicators: 預計算的指標字典（通常為空，因為這個函數會自己計算）
    - params: 參數字典
      - short_period: 短期週期
      - mid_period: 中期週期
      - long_period: 長期週期
      - indicator_type: 指標類型（ema/sma）
      - data_source: 數據源（close/open/high/low）

    返回：
    - np.ndarray: boolean 數組，True 表示信號有效

    策略邏輯：
    short_ema > mid_ema > long_ema
    """
    try:
        # 提取參數
        short_period = params['short_period']
        mid_period = params['mid_period']
        long_period = params['long_period']
        indicator_type = params.get('indicator_type', 'ema')
        data_source = params.get('data_source', 'close')

        # 創建指標引擎
        indicator_engine = IndicatorEngine()

        # 配置三條均線
        indicator_configs = [
            {
                "indicator": indicator_type,
                "data_source": data_source,
                "params": {"period": short_period},
                "output_name": "ema_short"
            },
            {
                "indicator": indicator_type,
                "data_source": data_source,
                "params": {"period": mid_period},
                "output_name": "ema_mid"
            },
            {
                "indicator": indicator_type,
                "data_source": data_source,
                "params": {"period": long_period},
                "output_name": "ema_long"
            }
        ]

        # 批量計算指標
        indicators_df = indicator_engine.calculate_indicators_from_dataframe(
            kline_data,
            indicator_configs
        )

        # 驗證結果
        required_cols = ["ema_short", "ema_mid", "ema_long"]
        missing_cols = [col for col in required_cols if col not in indicators_df.columns]
        if missing_cols:
            error_msg = f"Indicator calculation missing columns: {missing_cols}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 應用三線排列邏輯
        signals = (
            (indicators_df["ema_short"] > indicators_df["ema_mid"]) &
            (indicators_df["ema_mid"] > indicators_df["ema_long"])
        )

        return signals.values

    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        raise ValueError(f"Missing required parameter: {e}")
    except Exception as e:
        logger.error(
            f"Failed to calculate three-line signals: {e}",
            exc_info=True
        )
        raise


def validate_params(params: Dict[str, Any]) -> List[str]:
    """
    驗證三線排列策略的參數

    除了基礎驗證（由 StrategyRegistry 執行）外，
    這裡執行業務邏輯驗證。

    參數：
    - params: 參數字典

    返回：
    - List[str]: 錯誤訊息列表（空列表表示驗證通過）
    """
    errors = []

    try:
        short_period = params['short_period']
        mid_period = params['mid_period']
        long_period = params['long_period']

        # 業務邏輯驗證已移除
        # 基礎約束（short < mid < long）已由 YAML 配置的 constraints 保證
        # 不需要額外的差距限制，用戶有自由選擇參數的權利
        pass

    except KeyError as e:
        errors.append(f"缺少必要參數: {e}")

    return errors
