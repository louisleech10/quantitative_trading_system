from __future__ import annotations

from typing import Dict, List
import fnmatch
import re

import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.feature_config import FactoryConfig


logger = get_logger(__name__)


class LagProcessor:
    """Layer 4: lag feature expansion."""

    def __init__(self, config: FactoryConfig) -> None:
        self._lag_strategy = config.global_settings.lag_strategy
        self._sequence_length = config.global_settings.sequence_length
        self._max_lag_ratio = config.global_settings.max_lag_ratio
        self._custom_lags = config.global_settings.custom_lags
        self._apply_to = config.lag_features.apply_to
        self._exclude_patterns = config.lag_features.exclude_patterns
        self._enabled = config.lag_features.enabled

    def compute_all(self, features_df: pd.DataFrame) -> pd.DataFrame:
        if not self._enabled or features_df.empty:
            return pd.DataFrame(index=features_df.index)

        lag_steps = ParameterGenerator.generate_lag_sequence(
            self._sequence_length,
            self._max_lag_ratio,
            self._lag_strategy,
            self._custom_lags,
        )
        lag_steps = self._normalize_lags(lag_steps)

        columns = self._select_columns(features_df.columns)
        if not columns or not lag_steps:
            return pd.DataFrame(index=features_df.index)

        frames: List[pd.DataFrame] = []
        chunk_size = 200
        for start in range(0, len(columns), chunk_size):
            chunk = columns[start : start + chunk_size]
            chunk_df = features_df[chunk]
            lag_frames: List[pd.DataFrame] = []
            for lag in lag_steps:
                lagged = self._apply_lag(chunk_df, lag)
                lag_frames.append(lagged.add_suffix(f"_Lag_{lag}"))
            if lag_frames:
                frames.append(pd.concat(lag_frames, axis=1))

        if not frames:
            return pd.DataFrame(index=features_df.index)
        return pd.concat(frames, axis=1)

    def _apply_lag(self, data: pd.DataFrame, lag: int) -> pd.DataFrame:
        return data.shift(lag)

    def _select_columns(self, columns: List[str]) -> List[str]:
        selected = []
        for col in columns:
            if self._is_excluded(col):
                continue
            if self._apply_to == "all":
                selected.append(col)
                continue
            if self._apply_to == "layer1_and_raw":
                if self._is_layer1_or_raw(col):
                    selected.append(col)
                continue
            if isinstance(self._apply_to, list):
                if any(token in col for token in self._apply_to):
                    selected.append(col)
                continue
            try:
                if re.search(str(self._apply_to), col):
                    selected.append(col)
            except re.error:
                if str(self._apply_to) in col:
                    selected.append(col)
        return selected

    def _is_excluded(self, col: str) -> bool:
        for pattern in self._exclude_patterns:
            if fnmatch.fnmatch(col, pattern):
                return True
        return False

    def _is_layer1_or_raw(self, col: str) -> bool:
        operator_tokens = [
            "_Distance",
            "_Cross",
            "_Momentum",
            "_Ratio",
            "_BinarySignal",
            "_SignedStrength",
            "_TsArgmax",
            "_TsArgmin",
            "_TsRank",
            "_DecayLinear",
            "_TsCorr",
            "_Sign",
            "_Log1p",
            "_Abs",
            "_Clip",
            "_Slope_",
            "_Std_",
            "_Mean_",
            "_Rank_",
            "_ZScore_",
            "_Skew_",
            "_Kurt_",
            "_Min_",
            "_Max_",
            "_Range_",
            "_Lag_",
        ]
        if any(token in col for token in operator_tokens):
            return False
        if re.search(r"_W\d+$", col):
            return False
        return True

    def _normalize_lags(self, lags: List[int]) -> List[int]:
        normalized = sorted({int(lag) for lag in lags if lag >= 1})
        if self._lag_strategy == "adaptive":
            max_lag = max(1, int(self._sequence_length * self._max_lag_ratio))
            for lag in [1, 2, 3]:
                if lag <= max_lag:
                    normalized.append(lag)
            normalized = sorted(set(normalized))
        return normalized
