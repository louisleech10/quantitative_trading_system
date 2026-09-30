from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic import l1_output_points as l1op
from momentum.FeatureEngineering.atomic import warmup_lookup
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
        freq_df, consensus_df = self._mask_derived(data, pattern_df, freq_df, consensus_df)

        return pd.concat([pattern_df, freq_df, consensus_df], axis=1)

    @staticmethod
    def _mask_derived(data: pd.DataFrame, pattern_df: pd.DataFrame, freq_df: pd.DataFrame,
                      consensus_df: pd.DataFrame) -> tuple:
        """FF-STAT Task 2.3（SPEC §C v39）：同引擎衍生輸出之 L1 輸出點——frequency（窗型）K＝上游 raw K＋window−1、
        Consensus（逐點聚合）K＝上游 raw K 之最大者；上游＝全部 raw CDL 欄（各欄 K 取表內 ``CDL_PATTERN`` 條目）。"""
        upstream = tuple(str(c) for c in pattern_df.columns)
        upstream_k = {c: warmup_lookup.get_pattern_default_bars() for c in upstream}
        origin = l1op.origin_of([data[c].to_numpy(dtype=float) for c in ("open", "high", "low", "close")])
        freq = {}
        for column in freq_df.columns:
            window = int(str(column).rsplit("_W", 1)[1])
            freq[column] = l1op.mask_output("pattern", warmup_lookup.PATTERN_ENTRY, str(column), freq_df[column].to_numpy(),
                                            {"window": window}, origin=origin, upstream=upstream, window=window,
                                            upstream_k=upstream_k)[0]
        consensus = {
            column: l1op.mask_output("pattern", warmup_lookup.PATTERN_ENTRY, str(column), consensus_df[column].to_numpy(),
                                     {}, origin=origin, upstream=upstream, upstream_k=upstream_k)[0]
            for column in consensus_df.columns
        }
        return (pd.DataFrame(freq, index=freq_df.index), pd.DataFrame(consensus, index=consensus_df.index))

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
