from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper


logger = get_logger(__name__)


class VolatilityIndicatorEngine:
    """Volatility indicators with derived features."""

    def __init__(self, config: Dict, data_sources: List[str]):
        self._config = config
        self._data_sources = data_sources

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
                logger.warning("Volatility indicator %s failed: %s", name, exc)

        frames.append(self._compute_keltner(data))
        frames.append(self._compute_donchian(data))
        frames.append(self._compute_parkinson(data))
        frames.append(self._compute_garman_klass(data))

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
                    parts = [source_label, spec.category, indicator_name]
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
        window = 20
        multiplier = 2.0
        metadata[f"hlc_volatility_Keltner_Width_{window}_{multiplier}"] = {
            "layer": "layer1",
            "category": "volatility",
            "indicator": "Keltner_Width",
            "source": "hlc",
            "params": {"timeperiod": window, "multiplier": multiplier},
            "description": "Keltner channel width",
        }
        metadata[f"hlc_volatility_Donchian_Width_{window}"] = {
            "layer": "layer1",
            "category": "volatility",
            "indicator": "Donchian_Width",
            "source": "hlc",
            "params": {"timeperiod": window},
            "description": "Donchian channel width",
        }
        metadata[f"hlc_volatility_Parkinson_{window}"] = {
            "layer": "layer1",
            "category": "volatility",
            "indicator": "Parkinson",
            "source": "hlc",
            "params": {"timeperiod": window},
            "description": "Parkinson volatility estimator",
        }
        metadata[f"hlc_volatility_GarmanKlass_{window}"] = {
            "layer": "layer1",
            "category": "volatility",
            "indicator": "GarmanKlass",
            "source": "hlc",
            "params": {"timeperiod": window},
            "description": "Garman-Klass volatility estimator",
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
                f"hlc_volatility_Keltner_Width_{window}_{multiplier}": width,
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
            {f"hlc_volatility_Donchian_Width_{window}": width},
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
            {f"hlc_volatility_Parkinson_{window}": sigma},
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
            {f"hlc_volatility_GarmanKlass_{window}": sigma},
            index=data.index,
        )
