"""Consensus meta features."""

from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class ConsensusFeatureEngine:
    """Consensus-based meta features."""

    def compute_trend_consensus(self, layer1: pd.DataFrame) -> pd.Series:
        """mean(sign(EMA_8 > EMA_21), sign(MACD_Hist > 0), sign(ADX > 25))"""
        index = layer1.index
        if layer1.empty:
            return pd.Series(index=index, name="meta_Trend_Consensus", dtype=float)

        ema_fast = self._find_column(layer1, ["close_trend_EMA_8", "EMA_8"])
        ema_slow = self._find_column(layer1, ["close_trend_EMA_21", "EMA_21"])
        macd_hist = self._find_column(layer1, ["MACD_Hist"])
        adx = self._find_column(layer1, ["ADX_14"])

        signals: list[pd.Series] = []
        if ema_fast is not None and ema_slow is not None:
            signals.append(np.sign(ema_fast - ema_slow))
        if macd_hist is not None:
            signals.append(np.sign(macd_hist))
        if adx is not None:
            signals.append(pd.Series(np.where(adx > 25, 1.0, 0.0), index=index))

        if not signals:
            return pd.Series(index=index, name="meta_Trend_Consensus", dtype=float)

        consensus = pd.concat(signals, axis=1).mean(axis=1, skipna=True)
        consensus.name = "meta_Trend_Consensus"
        return consensus

    def compute_momentum_divergence(self, layer1: pd.DataFrame) -> pd.Series:
        """std(RSI_rank, CCI_rank, STOCH_rank)"""
        index = layer1.index
        if layer1.empty:
            return pd.Series(index=index, name="meta_Momentum_Divergence", dtype=float)

        rsi = self._find_column(layer1, ["RSI_14", "RSI"])
        cci = self._find_column(layer1, ["CCI_14", "CCI"])
        stoch = self._find_column(layer1, ["STOCH_slowk", "STOCH"])

        series_list = [s for s in [rsi, cci, stoch] if s is not None]
        if len(series_list) < 2:
            return pd.Series(index=index, name="meta_Momentum_Divergence", dtype=float)

        stacked = pd.concat(series_list, axis=1)
        ranked = stacked.rank(axis=1, pct=True)
        divergence = ranked.std(axis=1, ddof=0)
        divergence.name = "meta_Momentum_Divergence"
        return divergence

    def compute_volume_price_divergence(self, layer1: pd.DataFrame, raw: pd.DataFrame) -> pd.Series:
        """sign(Price_Change) != sign(Volume_Change)"""
        index = raw.index if not raw.empty else layer1.index
        if raw.empty or "close" not in raw.columns or "volume" not in raw.columns:
            return pd.Series(index=index, name="meta_VolumePrice_Divergence", dtype=float)

        price_change = raw["close"].pct_change()
        volume_change = raw["volume"].pct_change()
        sign_price = np.sign(price_change)
        sign_volume = np.sign(volume_change)
        divergence = (sign_price * sign_volume < 0).astype(float)
        divergence.name = "meta_VolumePrice_Divergence"
        return divergence

    def compute_volatility_regime(self, layer1: pd.DataFrame) -> pd.Series:
        """ATR_14 / ATR_55"""
        index = layer1.index
        if layer1.empty:
            return pd.Series(index=index, name="meta_Volatility_Regime", dtype=float)

        atr_fast = self._find_column(layer1, ["ATR_14"])
        atr_slow = self._find_column(layer1, ["ATR_55"])
        if atr_fast is None or atr_slow is None:
            return pd.Series(index=index, name="meta_Volatility_Regime", dtype=float)

        regime = atr_fast / atr_slow.replace(0, np.nan)
        regime.name = "meta_Volatility_Regime"
        return regime

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
