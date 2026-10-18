from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic import l1_output_points as l1op
from momentum.FeatureEngineering.atomic.compute_guard import guard_indicator_compute, resolve_fail_open
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.feature_naming import FeatureIdentity, build_identity, format_feature_name


logger = get_logger(__name__)


# FF-NAME Task 2.2：自製 volatility 欄之身分常數（compute、輸出點、metadata 三處共用；來源標籤沿用 `hlc`）
def _keltner_identity(window: int, multiplier: float) -> FeatureIdentity:
    return build_identity("hlc", "volatility", "Keltner-Width", (window, multiplier))


def _donchian_identity(window: int) -> FeatureIdentity:
    return build_identity("hlc", "volatility", "Donchian-Width", (window,))


def _parkinson_identity(window: int) -> FeatureIdentity:
    return build_identity("hlc", "volatility", "Parkinson", (window,))


def _garman_klass_identity(window: int) -> FeatureIdentity:
    return build_identity("hlc", "volatility", "GarmanKlass", (window,))


class VolatilityIndicatorEngine:
    """Volatility indicators with derived features."""

    def __init__(self, config: Dict, data_sources: List[str]):
        self._config = config
        self._data_sources = data_sources
        self._fail_open = resolve_fail_open(
            config.get("fail_open_indicators") if config else None
        )

    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        indicators = self._config.get("indicators", []) if self._config else []
        if not indicators:
            indicators = [spec.name for spec in TALibWrapper.list_indicators("volatility")]

        TALibWrapper.initialize()
        talib_names = set(TALibWrapper.INDICATOR_REGISTRY.keys())

        frames = []
        for indicator in indicators:
            name = indicator["name"] if isinstance(indicator, dict) else indicator
            if name not in talib_names:
                continue
            indicator_def = indicator if isinstance(indicator, dict) else {}
            params_list = self._resolve_params(name, indicator_def)
            try:
                frames.append(TALibWrapper.compute_batch(name, data, params_list, self._data_sources))
            except Exception as exc:
                guard_indicator_compute(name, exc, fail_open=self._fail_open)

        # FF-STAT Task 2.3：自訂欄之 L1 輸出點（倍數表條目、產生該欄之參數、全部輸入欄）
        frames.append(l1op.mask_frame(self._compute_keltner(data), "volatility", "KELTNER", {"timeperiod": 20}, data,
                                      ("high", "low", "close")))
        frames.append(l1op.mask_frame(self._compute_donchian(data), "volatility", "DONCHIAN", {"timeperiod": 20}, data,
                                      ("high", "low")))
        frames.append(l1op.mask_frame(self._compute_parkinson(data), "volatility", "PARKINSON_VOL", {"timeperiod": 20},
                                      data, ("high", "low")))
        frames.append(l1op.mask_frame(self._compute_garman_klass(data), "volatility", "GARMANKLASS_VOL",
                                      {"timeperiod": 20}, data, ("open", "high", "low", "close")))

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)

    def get_feature_metadata(self) -> Dict[str, Dict]:
        indicators = self._config.get("indicators", []) if self._config else []
        if not indicators:
            indicators = [spec.name for spec in TALibWrapper.list_indicators("volatility")]

        TALibWrapper.initialize()
        talib_names = set(TALibWrapper.INDICATOR_REGISTRY.keys())

        metadata: Dict[str, Dict] = {}
        for indicator in indicators:
            name = indicator["name"] if isinstance(indicator, dict) else indicator
            if name not in talib_names:
                continue
            indicator_def = indicator if isinstance(indicator, dict) else {}
            params_list = self._resolve_params(name, indicator_def)
            metadata.update(self._build_metadata_entries(name, params_list, self._data_sources))

        metadata.update(self._build_derived_metadata())
        return metadata

    def _build_metadata_entries(
        self,
        name: str,
        params_list: List[Dict],
        sources: List[str],
    ) -> Dict[str, Dict]:
        """FF-NAME Task 2.1：委派 `TALibWrapper.build_metadata_entries`（共用身分建構）。"""
        return TALibWrapper.build_metadata_entries(name, params_list, sources)

    def _build_derived_metadata(self) -> Dict[str, Dict]:
        """自製欄之 metadata：鍵與 compute／輸出點同一身分常數（FF-NAME Task 2.2）；來源標籤 `hlc` 非 raw 鍵。"""
        window = 20
        multiplier = 2.0
        entries = (
            (_keltner_identity(window, multiplier), {"timeperiod": window, "multiplier": multiplier},
             "Keltner channel width"),
            (_donchian_identity(window), {"timeperiod": window}, "Donchian channel width"),
            (_parkinson_identity(window), {"timeperiod": window}, "Parkinson volatility estimator"),
            (_garman_klass_identity(window), {"timeperiod": window}, "Garman-Klass volatility estimator"),
        )
        return {
            format_feature_name(identity): {
                "layer": "layer1",
                "category": identity.category,
                "indicator": identity.indicator,
                "source": identity.source,
                "raw_lookup_key": None,
                "params": params,
                "description": description,
            }
            for identity, params, description in entries
        }

    def _resolve_params(self, name: str, indicator_def: Dict) -> List[Dict]:
        period_range = indicator_def.get("period_range") if indicator_def else None
        range_min = 5
        range_max = 233
        if isinstance(period_range, list) and period_range:
            range_min = int(period_range[0])
            range_max = int(period_range[-1])
        industry_standard = indicator_def.get("industry_standard") if indicator_def else None

        params = indicator_def.get("params") if indicator_def else None
        if isinstance(params, dict) and params:
            return [params]

        periods = indicator_def.get("periods") if indicator_def else None
        if isinstance(periods, list):
            values = [int(period) for period in periods]
            if industry_standard:
                values = sorted({*values, *industry_standard})
            return [{"timeperiod": period} for period in values]
        if isinstance(periods, str):
            values = ParameterGenerator.generate(
                periods,
                range_min=range_min,
                range_max=range_max,
                industry_standard=industry_standard,
            )
            return [{"timeperiod": int(period)} for period in values]

        spec = TALibWrapper.get_indicator_spec(name)
        return [spec.default_params] if spec.default_params else [{}]

    def _compute_keltner(self, data: pd.DataFrame, window: int = 20, multiplier: float = 2.0) -> pd.DataFrame:
        required = {"high", "low", "close"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        ema = TALibWrapper.compute("EMA", data, {"timeperiod": window}, "close")
        atr = TALibWrapper.compute("ATR", data, {"timeperiod": window}, "close")
        ema_col = ema.columns[0]
        atr_col = atr.columns[0]
        middle = ema[ema_col]
        upper = middle + multiplier * atr[atr_col]
        lower = middle - multiplier * atr[atr_col]
        width = (upper - lower) / middle.replace(0, np.nan)

        return pd.DataFrame(
            {
                format_feature_name(_keltner_identity(window, multiplier)): width,
            },
            index=data.index,
        )

    def _compute_donchian(self, data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        required = {"high", "low"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        high = data["high"].rolling(window).max()
        low = data["low"].rolling(window).min()
        mid = (high + low) / 2.0
        width = (high - low) / mid.replace(0, np.nan)
        return pd.DataFrame(
            {format_feature_name(_donchian_identity(window)): width},
            index=data.index,
        )

    def _compute_parkinson(self, data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        required = {"high", "low"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        log_hl = np.log(data["high"] / data["low"].replace(0, np.nan))
        factor = 1.0 / (4.0 * np.log(2.0))
        variance = (log_hl ** 2).rolling(window).mean() * factor
        sigma = np.sqrt(variance)
        return pd.DataFrame(
            {format_feature_name(_parkinson_identity(window)): sigma},
            index=data.index,
        )

    def _compute_garman_klass(self, data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        required = {"high", "low", "open", "close"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        log_hl = np.log(data["high"] / data["low"].replace(0, np.nan))
        log_co = np.log(data["close"] / data["open"].replace(0, np.nan))
        variance = 0.5 * (log_hl ** 2) - (2.0 * np.log(2.0) - 1.0) * (log_co ** 2)
        sigma = np.sqrt(variance.rolling(window).mean())
        return pd.DataFrame(
            {format_feature_name(_garman_klass_identity(window)): sigma},
            index=data.index,
        )
