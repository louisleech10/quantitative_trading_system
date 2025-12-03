"""
短長交叉策略實現

策略邏輯：短期EMA上穿長期EMA（金叉）
比三線排列更靈敏，但可能產生更多假信號。

Author: Claude (Phase 1 - Dynamic Parameters Refactoring)
Date: 2025-12-03
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from momentum.Indicators.indicator_engine import IndicatorEngine
from api.core.logging import get_logger

logger = get_logger("short_long_cross_strategy")


def calculate_signals(
    kline_data: pd.DataFrame,
    indicators: Dict[str, pd.Series],
    params: Dict[str, Any]
) -> np.ndarray:
    """
    計算短長交叉策略信號

    參數說明：
    - short_period: 短期週期
    - long_period: 長期週期
    - indicator_type: 指標類型（ema/sma）
    - data_source: 數據源（close/open/high/low）

    返回：
    - np.ndarray: boolean 數組，True 表示 short > long

    策略邏輯：
    short_ema > long_ema (持續條件)
    或者可以改為: short_ema crosses above long_ema (交叉時刻)
    """
    try:
        # 提取參數
        short_period = params['short_period']
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
                "params": {"period": short_period},
                "output_name": "ema_short"
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
        required_cols = ["ema_short", "ema_long"]
        missing_cols = [col for col in required_cols if col not in indicators_df.columns]
        if missing_cols:
            error_msg = f"Indicator calculation missing columns: {missing_cols}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 應用短長交叉邏輯（持續條件：short > long）
        signals = indicators_df["ema_short"] > indicators_df["ema_long"]

        return signals.values

    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        raise ValueError(f"Missing required parameter: {e}")
    except Exception as e:
        logger.error(
            f"Failed to calculate short-long cross signals: {e}",
            exc_info=True
        )
        raise


def validate_params(params: Dict[str, Any]) -> List[str]:
    """
    驗證短長交叉策略的參數

    返回：
    - List[str]: 錯誤訊息列表
    """
    errors = []

    try:
        short_period = params['short_period']
        long_period = params['long_period']

        # 業務邏輯驗證：週期差距建議
        if long_period - short_period < 10:
            errors.append(
                f"長期週期({long_period})與短期週期({short_period})差距過小，"
                f"建議至少相差 10 個週期"
            )

    except KeyError as e:
        errors.append(f"缺少必要參數: {e}")

    return errors
