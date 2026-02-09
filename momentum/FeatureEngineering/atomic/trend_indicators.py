from __future__ import annotations

from typing import Dict, List

import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper


logger = get_logger(__name__)


class TrendIndicatorEngine:
    """Trend indicator engine."""

    def __init__(self, config: Dict, data_sources: List[str]):
        self._config = config
        self._data_sources = data_sources

    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        indicators = self._config.get("indicators", []) if self._config else []
        if not indicators:
            indicators = [spec.name for spec in TALibWrapper.list_indicators("trend")]

        frames = []
        for indicator in indicators:
            name = indicator["name"] if isinstance(indicator, dict) else indicator
            indicator_def = indicator if isinstance(indicator, dict) else {}
            params_list = self._resolve_params(name, indicator_def)
            sources = self._resolve_sources(indicator_def)
            try:
                frames.append(TALibWrapper.compute_batch(name, data, params_list, sources))
            except Exception as exc:
                logger.warning("Trend indicator %s failed: %s", name, exc)

        if not frames:
            return pd.DataFrame(index=data.index)

        return pd.concat(frames, axis=1)

    def get_feature_metadata(self) -> Dict[str, Dict]:
        indicators = self._config.get("indicators", []) if self._config else []
        if not indicators:
            indicators = [spec.name for spec in TALibWrapper.list_indicators("trend")]

        metadata: Dict[str, Dict] = {}
        for indicator in indicators:
            name = indicator["name"] if isinstance(indicator, dict) else indicator
            indicator_def = indicator if isinstance(indicator, dict) else {}
            params_list = self._resolve_params(name, indicator_def)
            sources = self._resolve_sources(indicator_def)
            metadata.update(self._build_metadata_entries(name, params_list, sources))

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

    def _resolve_sources(self, indicator_def: Dict) -> List[str]:
        sources = indicator_def.get("data_sources")
        if sources:
            return sources
        category_sources = self._config.get("data_sources") if self._config else None
        if category_sources:
            return category_sources
        return self._data_sources

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

        combos = indicator_def.get("combos") if indicator_def else None
        if combos:
            return ParameterGenerator.generate_combos(name, combos)

        periods = indicator_def.get("periods") if indicator_def else None
        if isinstance(periods, list):
            values = [int(period) for period in periods]
            if industry_standard:
                values = sorted({*values, *industry_standard})
            if name == "MAVP":
                return [{"periods": period} for period in values]
            return [{"timeperiod": period} for period in values]
        if isinstance(periods, str):
            values = ParameterGenerator.generate(
                periods,
                range_min=range_min,
                range_max=range_max,
                industry_standard=industry_standard,
            )
            if name == "MAVP":
                return [{"periods": int(period)} for period in values]
            return [{"timeperiod": int(period)} for period in values]

        spec = TALibWrapper.get_indicator_spec(name)
        return [spec.default_params] if spec.default_params else [{}]
