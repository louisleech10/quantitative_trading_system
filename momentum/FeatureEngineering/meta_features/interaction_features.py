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
from momentum.FeatureEngineering.feature_naming import (
    IdentitySpec,
    build_identity,
    find_identity_column,
    format_feature_name,
)

logger = get_logger(__name__)

# FF-NAME Task 3.2：L1 輸入以身分精確比對（同 consensus_features）
_EMA_FAST = (IdentitySpec("EMA", ("8",), "close"), IdentitySpec("EMA", ("8",)))
_EMA_SLOW = (IdentitySpec("EMA", ("21",), "close"), IdentitySpec("EMA", ("21",)))
_RSI = (IdentitySpec("RSI", ("14",)), IdentitySpec("RSI"))
_ATR = (IdentitySpec("ATR", ("14",)), IdentitySpec("ATR"))

# FF-NAME Task 2.4：L6 meta 欄名＝`meta_meta_<indicator>`（未標記形；落盤 `meta_<tf>_meta_<indicator>`）
_TREND_MOMENTUM = format_feature_name(build_identity("meta", "meta", "trend-momentum"))
_VOLATILITY_DIRECTION = format_feature_name(build_identity("meta", "meta", "volatility-direction"))
_VOLUME_PRICE_CHANGE = format_feature_name(build_identity("meta", "meta", "volume-price-change"))


class InteractionFeatureEngine:
    """Interaction features with physical meaning."""

    def compute_all(self, layer1: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
        """Trend x momentum, volatility x direction, volume x price change."""
        index = raw.index if not raw.empty else layer1.index
        frames: list[pd.Series] = []

        ema_fast = self._find_column(layer1, _EMA_FAST)
        ema_slow = self._find_column(layer1, _EMA_SLOW)
        rsi = self._find_column(layer1, _RSI)

        if ema_fast is not None and ema_slow is not None and rsi is not None:
            trend_strength = (ema_fast - ema_slow) / ema_slow.replace(0, np.nan)
            momentum_strength = (rsi - 50.0) / 50.0
            interaction = trend_strength * momentum_strength
            interaction.name = _TREND_MOMENTUM
            frames.append(interaction)

        atr = self._find_column(layer1, _ATR)
        if atr is not None and "close" in raw.columns:
            direction = np.sign(raw["close"].pct_change())
            volatility_direction = atr * direction
            volatility_direction.name = _VOLATILITY_DIRECTION
            frames.append(volatility_direction)

        if "close" in raw.columns and "volume" in raw.columns:
            price_change = raw["close"].pct_change()
            volume_change = raw["volume"].pct_change()
            interaction = price_change * volume_change
            interaction.name = _VOLUME_PRICE_CHANGE
            frames.append(interaction)

        if not frames:
            return pd.DataFrame(index=index)

        return pd.concat(frames, axis=1)

    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: Iterable[IdentitySpec]) -> Optional[pd.Series]:
        """依身分條件之優先序取第一個相符之 L1 欄（FF-NAME Task 3.2；不以子字串比對）。"""
        column = find_identity_column(df.columns, candidates)
        return None if column is None else df[column]
