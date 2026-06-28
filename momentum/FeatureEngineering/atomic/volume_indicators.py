from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
import talib

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic.compute_guard import guard_indicator_compute, resolve_fail_open
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper


logger = get_logger(__name__)


class VolumeIndicatorEngine:
    """Volume indicators with derived features."""

    def __init__(self, config: Dict, data_sources: List[str]):
        self._config = config
        self._data_sources = data_sources
        self._fail_open = resolve_fail_open(
            config.get("fail_open_indicators") if config else None
        )

    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        indicators = self._config.get("indicators", []) if self._config else []
        if not indicators:
            indicators = [spec.name for spec in TALibWrapper.list_indicators("volume")]

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

        frames.append(self._compute_vwap(data))
        frames.append(self._compute_volume_ma_ratio(data))
        frames.append(self._compute_force_index(data))
        frames.append(self._compute_klinger(data))
        frames.append(self._compute_eom(data))

        frames = [frame for frame in frames if frame is not None and not frame.empty]
        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)

    def get_feature_metadata(self) -> Dict[str, Dict]:
        indicators = self._config.get("indicators", []) if self._config else []
        if not indicators:
            indicators = [spec.name for spec in TALibWrapper.list_indicators("volume")]

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
        spec = TALibWrapper.get_indicator_spec(name)
        if spec.computed_in_adapter:
            return {}

        source_labels = sources if spec.input_type == "single" else [spec.input_type]
        metadata: Dict[str, Dict] = {}
        for params in params_list or [{}]:
            param_str = TALibWrapper._format_params(name, params)
            for source_label in source_labels:
                for idx in range(len(spec.output_names)):
                    name_suffix = spec.output_names[idx] if len(spec.output_names) > idx else str(idx)
                    if len(spec.output_names) == 1:
                        indicator_name = spec.name
                    else:
                        indicator_name = (
                            spec.name if name_suffix == spec.name else f"{spec.name}_{name_suffix}"
                        )
                    normalized_source = TALibWrapper.normalize_source_label(source_label)
                    normalized_indicator = TALibWrapper.normalize_indicator_name(indicator_name)
                    parts = [normalized_source, spec.category, normalized_indicator]
                    if param_str:
                        parts.append(param_str)
                    col_name = "_".join(parts)
                    metadata[col_name] = {
                        "layer": "layer1",
                        "category": spec.category,
                        "indicator": indicator_name,
                        "source": source_label,
                        "params": params,
                        "description": f"{indicator_name} computed from {source_label}",
                    }
        return metadata

    def _build_derived_metadata(self) -> Dict[str, Dict]:
        metadata: Dict[str, Dict] = {}
        vwap_window = 20
        metadata[f"hlcv_volume_VWAP_{vwap_window}"] = {
            "layer": "layer1",
            "category": "volume",
            "indicator": "VWAP",
            "source": "hlcv",
            "params": {"timeperiod": vwap_window},
            "description": "Volume weighted average price",
        }

        ma_window = 20
        metadata[f"volume_volume_VolumeMA_Ratio_{ma_window}"] = {
            "layer": "layer1",
            "category": "volume",
            "indicator": "VolumeMA_Ratio",
            "source": "volume",
            "params": {"timeperiod": ma_window},
            "description": "Volume to moving average ratio",
        }

        metadata["hlcv_volume_ForceIndex"] = {
            "layer": "layer1",
            "category": "volume",
            "indicator": "ForceIndex",
            "source": "hlcv",
            "params": {"timeperiod": 13},
            "description": "Elder Force Index canonical (EMA13 of close change × volume)",
        }

        fast = 34
        slow = 55
        metadata[f"hlcv_volume_Klinger_{fast}_{slow}"] = {
            "layer": "layer1",
            "category": "volume",
            "indicator": "Klinger",
            "source": "hlcv",
            "params": {"fast": fast, "slow": slow},
            "description": "Klinger Volume Oscillator canonical (trend-aware VF, EMA34−EMA55)",
        }

        eom_window = 14
        metadata[f"hlcv_volume_EOM_{eom_window}"] = {
            "layer": "layer1",
            "category": "volume",
            "indicator": "EOM",
            "source": "hlcv",
            "params": {"timeperiod": eom_window},
            "variant": "simplified",
            "description": "Simplified ease of movement (no 1e8 scale factor)",
        }
        return metadata

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

    def _compute_vwap(self, data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        required = {"high", "low", "close", "volume"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        price = (data["high"] + data["low"] + data["close"]) / 3.0
        volume = data["volume"].replace(0, np.nan)
        vwap = (price * volume).rolling(window).sum() / volume.rolling(window).sum()
        return pd.DataFrame(
            {f"hlcv_volume_VWAP_{window}": vwap},
            index=data.index,
        )

    def _compute_volume_ma_ratio(self, data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        if "volume" not in data.columns:
            return pd.DataFrame(index=data.index)
        volume_ma = data["volume"].rolling(window).mean()
        ratio = data["volume"] / volume_ma.replace(0, np.nan)
        return pd.DataFrame(
            {f"volume_volume_VolumeMA_Ratio_{window}": ratio},
            index=data.index,
        )

    def _compute_force_index(self, data: pd.DataFrame, ema_period: int = 13) -> pd.DataFrame:
        required = {"close", "volume"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)
        raw = close.diff() * volume
        smoothed = talib.EMA(raw.values, timeperiod=ema_period)
        return pd.DataFrame(
            {"hlcv_volume_ForceIndex": pd.Series(smoothed, index=data.index)},
            index=data.index,
        )

    @staticmethod
    def _klinger_cumulative_measurement(dm: np.ndarray, trend: np.ndarray) -> np.ndarray:
        """Klinger cumulative measurement：trend 不變時累加 dm，反轉時重置。"""
        n = len(dm)
        cm = np.empty(n, dtype=float)
        cm[0] = dm[0]
        for idx in range(1, n):
            if trend[idx] == trend[idx - 1]:
                cm[idx] = cm[idx - 1] + dm[idx]
            else:
                cm[idx] = dm[idx - 1] + dm[idx]
        return cm

    def _compute_klinger(self, data: pd.DataFrame, fast: int = 34, slow: int = 55) -> pd.DataFrame:
        required = {"high", "low", "close", "volume"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)
        hlc = (high + low + close).values
        trend = np.where(hlc > np.roll(hlc, 1), 1.0, -1.0)
        trend[0] = 1.0
        dm = (high - low).values
        cm = self._klinger_cumulative_measurement(dm, trend)
        cm = np.where(cm == 0, np.nan, cm)
        vf = volume.values * np.abs(2.0 * (dm / cm - 1.0)) * trend * 100.0
        vf = np.nan_to_num(vf, nan=0.0, posinf=0.0, neginf=0.0)
        ema_fast = talib.EMA(vf.astype(float), timeperiod=fast)
        ema_slow = talib.EMA(vf.astype(float), timeperiod=slow)
        kvo = ema_fast - ema_slow
        return pd.DataFrame(
            {f"hlcv_volume_Klinger_{fast}_{slow}": pd.Series(kvo, index=data.index)},
            index=data.index,
        )

    def _compute_eom(self, data: pd.DataFrame, window: int = 14) -> pd.DataFrame:
        required = {"high", "low", "volume"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        mid = (data["high"] + data["low"]) / 2.0
        mid_move = mid.diff()
        box_ratio = (data["high"] - data["low"]) / data["volume"].replace(0, np.nan)
        eom = (mid_move * box_ratio).rolling(window).mean()
        return pd.DataFrame(
            {f"hlcv_volume_EOM_{window}": eom},
            index=data.index,
        )
