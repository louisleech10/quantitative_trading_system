"""
Interaction meta features — Layer 6 Sub-engine E.

設計說明：
  計算 Layer 1 指標兩兩乘積，捕捉「趨勢方向 × 動量強度」等非線性交互效應。
  目前僅使用三組組合（EMA×RSI、ATR×方向、成交量×價格）。

未來擴充方向（TODO）：
  - 納入更多 L1 指標的乘積（如 ADX×RSI、BBANDS_width×Volume_MA_Ratio）
  - 支援由 config 動態定義交互對（meta_features.interaction_pairs）
  - 考慮三元交互（Trend × Momentum × Volume），但需注意特徵爆炸問題
"""

from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class InteractionFeatureEngine:
    """Interaction features with physical meaning."""

    def compute_all(self, layer1: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
        """Trend x momentum, volatility x direction, volume x price change."""
        index = raw.index if not raw.empty else layer1.index
        frames: list[pd.Series] = []

        ema_fast = self._find_column(layer1, ["close_trend_EMA_8", "EMA_8"])
        ema_slow = self._find_column(layer1, ["close_trend_EMA_21", "EMA_21"])
        rsi = self._find_column(layer1, ["RSI_14", "RSI"])

        if ema_fast is not None and ema_slow is not None and rsi is not None:
            trend_strength = (ema_fast - ema_slow) / ema_slow.replace(0, np.nan)
            momentum_strength = (rsi - 50.0) / 50.0
            interaction = trend_strength * momentum_strength
            interaction.name = "meta_Trend_Momentum"
            frames.append(interaction)

        atr = self._find_column(layer1, ["ATR_14", "ATR"])
        if atr is not None and "close" in raw.columns:
            direction = np.sign(raw["close"].pct_change())
            volatility_direction = atr * direction
            volatility_direction.name = "meta_Volatility_Direction"
            frames.append(volatility_direction)

        if "close" in raw.columns and "volume" in raw.columns:
            price_change = raw["close"].pct_change()
            volume_change = raw["volume"].pct_change()
            interaction = price_change * volume_change
            interaction.name = "meta_Volume_PriceChange"
            frames.append(interaction)

        if not frames:
            return pd.DataFrame(index=index)

        return pd.concat(frames, axis=1)

    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[pd.Series]:
        for candidate in candidates:
            if candidate in df.columns:
                return df[candidate]
        for candidate in candidates:
            matches = [col for col in df.columns if candidate in col]
            if matches:
                return df[matches[0]]
        return None
