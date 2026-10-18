"""
Consensus meta features — Layer 6 Sub-engines A~D.

設計說明：
  本模組計算四種「共識型」元特徵，將 Layer 1 多個指標整合為單一訊號。
  所有指標均為 hardcode 之身分條件（IdentitySpec），透過 _find_column() 以欄名身分精確比對 Layer 1 DataFrame 欄位。
  若 scan_config.yaml 未啟用對應指標，該計算會優雅略過（回傳空 Series）。

選用指標根據（為何是這幾個）：
  - 均選自 scan_config.yaml 中 industry_standard 欄位標記的業界通用參數
  - 三大類別各自選語義最互補的代表：趨勢(EMA/ADX)、動量(RSI/CCI/STOCH)、波動率(ATR)
  - 設計目的是提供「教科書級別」的快速基準，而非窮舉所有指標組合

使用限制：
  Layer 6 元特徵本身仍需經過 IC Analysis 和 SHAP 評估其有效性，
  並非所有 sub-engine 對所有標的或時間框架都有預測力。
  高粒度時間框架（如 1h）的 time_features 較有意義；12h 以上建議關閉 HourOfDay。
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
from momentum.FeatureEngineering.preprocessing import stable_mask as _stable_mask

# FF-NAME Task 3.2：L1 輸入以身分精確比對（indicator 相等、第一參數成員相等、可選 source；依序取第一個相符者）
_EMA_FAST = (IdentitySpec("EMA", ("8",), "close"), IdentitySpec("EMA", ("8",)))
_EMA_SLOW = (IdentitySpec("EMA", ("21",), "close"), IdentitySpec("EMA", ("21",)))
_MACD_HIST = (IdentitySpec("MACD-Hist"),)
_ADX_14 = (IdentitySpec("ADX", ("14",)),)
_RSI = (IdentitySpec("RSI", ("14",)), IdentitySpec("RSI"))
_CCI = (IdentitySpec("CCI", ("14",)), IdentitySpec("CCI"))
_STOCH_SLOWK = (IdentitySpec("STOCH-slowk"),)
_ATR_14 = (IdentitySpec("ATR", ("14",)),)
_ATR_55 = (IdentitySpec("ATR", ("55",)),)

# FF-NAME Task 2.4：L6 meta 欄名＝`meta_meta_<indicator>`（未標記形；落盤 `meta_<tf>_meta_<indicator>`）
_TREND_CONSENSUS = format_feature_name(build_identity("meta", "meta", "trend-consensus"))
_MOMENTUM_DIVERGENCE = format_feature_name(build_identity("meta", "meta", "momentum-divergence"))
_VOLUME_PRICE_DIVERGENCE = format_feature_name(build_identity("meta", "meta", "volume-price-divergence"))
_VOLATILITY_REGIME = format_feature_name(build_identity("meta", "meta", "volatility-regime"))


def _prefix_masked(output: pd.Series, inputs: Iterable[pd.Series]) -> pd.Series:
    """FFSTAT Task 2.3 第④類：逐點／跨欄運算對 NaN 給有限值 ⇒ 各輸入首個有限值之最大者之前設 NaN（只遮開頭段）。"""
    values = _stable_mask.mask_pointwise_prefix(
        output.to_numpy(dtype=np.float64), [s.to_numpy(dtype=np.float64) for s in inputs]
    )
    return pd.Series(values, index=output.index, name=output.name)

logger = get_logger(__name__)


class ConsensusFeatureEngine:
    """Consensus-based meta features."""

    def compute_trend_consensus(self, layer1: pd.DataFrame) -> pd.Series:
        """mean(sign(EMA_8 > EMA_21), sign(MACD_Hist > 0), sign(ADX > 25))"""
        index = layer1.index
        if layer1.empty:
            return pd.Series(index=index, name=_TREND_CONSENSUS, dtype=float)

        ema_fast = self._find_column(layer1, _EMA_FAST)
        ema_slow = self._find_column(layer1, _EMA_SLOW)
        macd_hist = self._find_column(layer1, _MACD_HIST)
        adx = self._find_column(layer1, _ADX_14)

        signals: list[pd.Series] = []
        if ema_fast is not None and ema_slow is not None:
            signals.append(np.sign(ema_fast - ema_slow))
        if macd_hist is not None:
            signals.append(np.sign(macd_hist))
        if adx is not None:
            signals.append(pd.Series(np.where(adx > 25, 1.0, 0.0), index=index))

        if not signals:
            return pd.Series(index=index, name=_TREND_CONSENSUS, dtype=float)

        consensus = pd.concat(signals, axis=1).mean(axis=1, skipna=True)
        consensus.name = _TREND_CONSENSUS
        inputs = [s for s in (ema_fast, ema_slow, macd_hist, adx) if s is not None]
        return _prefix_masked(consensus, inputs)

    def compute_momentum_divergence(self, layer1: pd.DataFrame) -> pd.Series:
        """std(RSI_rank, CCI_rank, STOCH_rank)"""
        index = layer1.index
        if layer1.empty:
            return pd.Series(index=index, name=_MOMENTUM_DIVERGENCE, dtype=float)

        rsi = self._find_column(layer1, _RSI)
        cci = self._find_column(layer1, _CCI)
        stoch = self._find_column(layer1, _STOCH_SLOWK)

        series_list = [s for s in [rsi, cci, stoch] if s is not None]
        if len(series_list) < 2:
            return pd.Series(index=index, name=_MOMENTUM_DIVERGENCE, dtype=float)

        stacked = pd.concat(series_list, axis=1)
        ranked = stacked.rank(axis=1, pct=True)
        divergence = ranked.std(axis=1, ddof=0)
        divergence.name = _MOMENTUM_DIVERGENCE
        return _prefix_masked(divergence, series_list)

    def compute_volume_price_divergence(self, layer1: pd.DataFrame, raw: pd.DataFrame) -> pd.Series:
        """sign(Price_Change) != sign(Volume_Change)"""
        index = raw.index if not raw.empty else layer1.index
        if raw.empty or "close" not in raw.columns or "volume" not in raw.columns:
            return pd.Series(index=index, name=_VOLUME_PRICE_DIVERGENCE, dtype=float)

        price_change = raw["close"].pct_change()
        volume_change = raw["volume"].pct_change()
        sign_price = np.sign(price_change)
        sign_volume = np.sign(volume_change)
        divergence = (sign_price * sign_volume < 0).astype(float)
        divergence.name = _VOLUME_PRICE_DIVERGENCE
        return _prefix_masked(divergence, [price_change, volume_change])

    def compute_volatility_regime(self, layer1: pd.DataFrame) -> pd.Series:
        """ATR_14 / ATR_55"""
        index = layer1.index
        if layer1.empty:
            return pd.Series(index=index, name=_VOLATILITY_REGIME, dtype=float)

        atr_fast = self._find_column(layer1, _ATR_14)
        atr_slow = self._find_column(layer1, _ATR_55)
        if atr_fast is None or atr_slow is None:
            return pd.Series(index=index, name=_VOLATILITY_REGIME, dtype=float)

        regime = atr_fast / atr_slow.replace(0, np.nan)
        regime.name = _VOLATILITY_REGIME
        return regime

    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: Iterable[IdentitySpec]) -> Optional[pd.Series]:
        """依身分條件之優先序取第一個相符之 L1 欄（FF-NAME Task 3.2；不以子字串比對）。"""
        column = find_identity_column(df.columns, candidates)
        return None if column is None else df[column]
