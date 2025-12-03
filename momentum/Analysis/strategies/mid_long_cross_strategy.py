"""
中長交叉策略實現

策略邏輯：中期EMA上穿長期EMA（金叉）
比短長交叉更穩定，但反應較慢，適合較長週期的趨勢追蹤。

Author: Claude (Phase 1 - Dynamic Parameters Refactoring)
Date: 2025-12-03
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from momentum.Indicators.indicator_engine import IndicatorEngine
from api.core.logging import get_logger

logger = get_logger("mid_long_cross_strategy")


def calculate_signals(
    kline_data: pd.DataFrame,
    indicators: Dict[str, pd.Series],
    params: Dict[str, Any]
) -> np.ndarray:
    """
    計算中長交叉策略信號

    參數說明：
    - mid_period: 中期週期
    - long_period: 長期週期
    - indicator_type: 指標類型（ema/sma）
    - data_source: 數據源（close/open/high/low）

    返回：
    - np.ndarray: boolean 數組，True 表示 mid > long
    """
    try:
        # 提取參數
        mid_period = params['mid_period']
        long_period = params['long_period']
        indicator_type = params.get('indicator_type', 'ema')
        data_source = params.get('data_source', 'close')

        # 創建指標引擎
        indicator_engine = IndicatorEngine()

        # 配置兩條均線
        indicator_configs = [
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
        required_cols = ["ema_mid", "ema_long"]
        missing_cols = [col for col in required_cols if col not in indicators_df.columns]
        if missing_cols:
            error_msg = f"Indicator calculation missing columns: {missing_cols}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 應用中長交叉邏輯（持續條件：mid > long）
        signals = indicators_df["ema_mid"] > indicators_df["ema_long"]

        return signals.values

    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        raise ValueError(f"Missing required parameter: {e}")
    except Exception as e:
        logger.error(
            f"Failed to calculate mid-long cross signals: {e}",
            exc_info=True
        )
        raise


def validate_params(params: Dict[str, Any]) -> List[str]:
    """
    驗證中長交叉策略的參數

    返回：
    - List[str]: 錯誤訊息列表
    """
    errors = []

    try:
        mid_period = params['mid_period']
        long_period = params['long_period']

        # 業務邏輯驗證：週期差距建議
        if long_period - mid_period < 15:
            errors.append(
                f"長期週期({long_period})與中期週期({mid_period})差距過小，"
                f"建議至少相差 15 個週期"
            )

    except KeyError as e:
        errors.append(f"缺少必要參數: {e}")

    return errors
