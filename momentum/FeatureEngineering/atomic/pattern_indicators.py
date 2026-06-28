from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic.compute_guard import guard_indicator_compute, resolve_fail_open
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper


logger = get_logger(__name__)


class PatternIndicatorEngine:
    """Pattern indicator engine with derived frequency/consensus features."""

    def __init__(self, config: Dict, data_sources: List[str]):
        self._config = config
        self._data_sources = data_sources
        self._fail_open = resolve_fail_open(
            config.get("fail_open_indicators") if config else None
        )

    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        required = {"open", "high", "low", "close"}
        if not required.issubset(data.columns):
            return pd.DataFrame(index=data.index)
        indicators = self._config.get("indicators", []) if self._config else []
        if not indicators:
            indicators = [spec.name for spec in TALibWrapper.list_indicators("pattern")]

        frames = []
        for indicator in indicators:
            name = indicator["name"] if isinstance(indicator, dict) else indicator
            try:
                frames.append(TALibWrapper.compute_batch(name, data, [{}], self._data_sources))
            except Exception as exc:
                guard_indicator_compute(name, exc, fail_open=self._fail_open)

        pattern_df = pd.concat(frames, axis=1) if frames else pd.DataFrame(index=data.index)
        if pattern_df.empty:
            return pattern_df

        freq_df = self.compute_pattern_frequency(pattern_df)
        consensus = self.compute_pattern_consensus(pattern_df)
        consensus_df = pd.DataFrame({"ohlc_pattern_Consensus": consensus}, index=data.index)

        return pd.concat([pattern_df, freq_df, consensus_df], axis=1)

    def compute_pattern_frequency(
        self,
        pattern_df: pd.DataFrame,
        windows: List[int] | None = None,
    ) -> pd.DataFrame:
        if windows is None:
            windows = [5, 13, 21]

        frames = []
        bullish = pattern_df.gt(0).astype(int)
        bearish = pattern_df.lt(0).astype(int)

        for window in windows:
            bullish_count = bullish.rolling(window).sum().sum(axis=1)
            bearish_count = bearish.rolling(window).sum().sum(axis=1)
            frames.append(
                pd.DataFrame(
                    {
                        f"ohlc_pattern_BullishCount_W{window}": bullish_count,
                        f"ohlc_pattern_BearishCount_W{window}": bearish_count,
                    },
                    index=pattern_df.index,
                )
            )

        return pd.concat(frames, axis=1) if frames else pd.DataFrame(index=pattern_df.index)

    def compute_pattern_consensus(self, pattern_df: pd.DataFrame) -> pd.Series:
        sign_values = np.sign(pattern_df.replace(0, np.nan))
        consensus = sign_values.mean(axis=1).fillna(0.0)
        return consensus

    def get_feature_metadata(self) -> Dict[str, Dict]:
        indicators = self._config.get("indicators", []) if self._config else []
        if not indicators:
            indicators = [spec.name for spec in TALibWrapper.list_indicators("pattern")]

        metadata: Dict[str, Dict] = {}
        for indicator in indicators:
            name = indicator["name"] if isinstance(indicator, dict) else indicator
            metadata.update(self._build_metadata_entries(name))

        metadata.update(self._build_derived_metadata())
        return metadata

    def _build_metadata_entries(self, name: str) -> Dict[str, Dict]:
        spec = TALibWrapper.get_indicator_spec(name)
        if spec.computed_in_adapter:
            return {}

        source_label = spec.input_type
        metadata: Dict[str, Dict] = {}
        for idx in range(len(spec.output_names)):
            name_suffix = spec.output_names[idx] if len(spec.output_names) > idx else str(idx)
            if len(spec.output_names) == 1:
                indicator_name = spec.name
            else:
                indicator_name = spec.name if name_suffix == spec.name else f"{spec.name}_{name_suffix}"
            col_name = "_".join([source_label, spec.category, indicator_name])
            metadata[col_name] = {
                "layer": "layer1",
                "category": spec.category,
                "indicator": indicator_name,
                "source": source_label,
                "params": {},
                "description": f"{indicator_name} pattern signal",
            }
        return metadata

    def _build_derived_metadata(self) -> Dict[str, Dict]:
        metadata: Dict[str, Dict] = {}
        for window in [5, 13, 21]:
            metadata[f"ohlc_pattern_BullishCount_W{window}"] = {
                "layer": "layer1",
                "category": "pattern",
                "indicator": "BullishCount",
                "source": "ohlc",
                "params": {"window": window},
                "description": "Rolling bullish pattern count",
            }
            metadata[f"ohlc_pattern_BearishCount_W{window}"] = {
                "layer": "layer1",
                "category": "pattern",
                "indicator": "BearishCount",
                "source": "ohlc",
                "params": {"window": window},
                "description": "Rolling bearish pattern count",
            }

        metadata["ohlc_pattern_Consensus"] = {
            "layer": "layer1",
            "category": "pattern",
            "indicator": "Consensus",
            "source": "ohlc",
            "params": {},
            "description": "Average pattern direction",
        }
        return metadata
