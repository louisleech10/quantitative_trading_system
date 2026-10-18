from __future__ import annotations

import dataclasses
import os
from typing import Dict, List, Mapping, Optional
import fnmatch
import re

import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.feature_config import FactoryConfig
from momentum.FeatureEngineering.feature_naming import (
    FeatureIdentity,
    FeatureNameParseError,
    format_feature_name,
    parse_feature_name,
    raw_value_identity,
)


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
        self._column_chunk_size = self._resolve_positive_env("FFACT_LAYER4_CHUNK_SIZE", 200)
        self._lag_batch_size = self._resolve_positive_env("FFACT_LAYER4_LAG_BATCH_SIZE", 8)
        # P1.4: V7→V8 regression fix. The legacy chunked path triggers
        # ~ (cols/chunk) × (lags/batch) intermediate ``pd.concat`` calls — at
        # 12K cols × 8 lags this costs >20s of overhead alone. When the
        # estimated output stays under this cap we fall back to a flat
        # one-shift-per-lag plan that performs only ``len(lags)`` concats.
        self._fast_path_max_cols = self._resolve_positive_env(
            "FFACT_LAYER4_FAST_PATH_MAX_COLS", 200_000
        )

    def compute_all(
        self,
        features_df: pd.DataFrame,
        column_layers: Optional[Mapping[str, str]] = None,
    ) -> pd.DataFrame:
        """`column_layers`：欄 → 來源層（`"raw"`＝K 線資料鍵、`"L1"`＝L1 群組欄…；FF-NAME Task 3.2），
        `apply_to="layer1_and_raw"` 時必填（以層別選欄，不讀欄名）。"""
        if not self._enabled or features_df.empty:
            return pd.DataFrame(index=features_df.index)

        lag_steps = ParameterGenerator.generate_lag_sequence(
            self._sequence_length,
            self._max_lag_ratio,
            self._lag_strategy,
            self._custom_lags,
        )
        lag_steps = self._normalize_lags(lag_steps)

        columns = self._select_columns(features_df.columns, column_layers)
        if not columns or not lag_steps:
            return pd.DataFrame(index=features_df.index)

        selected_df = features_df[columns]
        estimated_output_cols = len(columns) * len(lag_steps)

        if estimated_output_cols <= self._fast_path_max_cols:
            # Fast path (P1.4): one shift per lag, single outer concat.
            # ``copy=False`` keeps memory flat; output columns are immutable.
            frames: List[pd.DataFrame] = [
                self._with_lag_names(selected_df.shift(lag), lag) for lag in lag_steps
            ]
            return pd.concat(frames, axis=1, copy=False)

        # Legacy chunked path retained for very wide inputs (>fast_path_max_cols).
        frames = []
        chunk_size = self._column_chunk_size
        for start in range(0, len(columns), chunk_size):
            chunk = columns[start : start + chunk_size]
            chunk_df = features_df[chunk]
            chunk_frames: List[pd.DataFrame] = []
            for lag_start in range(0, len(lag_steps), self._lag_batch_size):
                lag_subset = lag_steps[lag_start : lag_start + self._lag_batch_size]
                lag_frames: List[pd.DataFrame] = []
                for lag in lag_subset:
                    lagged = self._apply_lag(chunk_df, lag)
                    lag_frames.append(self._with_lag_names(lagged, lag))
                if lag_frames:
                    chunk_frames.append(pd.concat(lag_frames, axis=1, copy=False))

            if chunk_frames:
                frames.append(pd.concat(chunk_frames, axis=1, copy=False))

        if not frames:
            return pd.DataFrame(index=features_df.index)
        return pd.concat(frames, axis=1, copy=False)

    def _apply_lag(self, data: pd.DataFrame, lag: int) -> pd.DataFrame:
        return data.shift(lag)

    def _select_columns(self, columns: List[str], column_layers: Optional[Mapping[str, str]] = None) -> List[str]:
        if self._apply_to == "layer1_and_raw" and column_layers is None:
            raise ValueError(
                "lag_features.apply_to='layer1_and_raw' 須由呼叫端提供欄之來源層（column_layers）；"
                "不以欄名推斷層別（FF-NAME Task 3.2）"
            )
        selected = []
        for col in columns:
            if self._is_excluded(col):
                continue
            if self._apply_to == "all":
                selected.append(col)
                continue
            if self._apply_to == "layer1_and_raw":
                if self._is_layer1_or_raw(str(col), column_layers):
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

    @staticmethod
    def _identity_or_none(col: str) -> Optional[FeatureIdentity]:
        """生成期間之未標記形欄名 → 身分；不合特徵文法（raw kline 資料鍵，如 `taker_ratio`、`avg-price`）⇒ None。"""
        try:
            return parse_feature_name(str(col), tagged=False)
        except FeatureNameParseError:
            return None

    _LAYER1_OR_RAW = frozenset({"L1", "raw"})

    def _is_layer1_or_raw(self, col: str, column_layers: Mapping[str, str]) -> bool:
        """`layer1_and_raw` 之選欄（FF-NAME Task 3.2、§G ⑥）：讀呼叫端提供之來源層（L1 群組欄或 raw 資料鍵），
        不讀欄名子字串或身分推層；取代改前之欄名黑名單（該黑名單誤排除 `VolumeMA_Ratio`、`BullishCount_W5`）。"""
        return column_layers.get(col) in self._LAYER1_OR_RAW

    def _lag_name(self, col: str, lag: int) -> str:
        """L4 欄名（FF-NAME Task 2.4）：特徵欄＝身分＋op `Lag-<k>`；raw 資料鍵＝`<canonical raw>_raw_value_Lag-<k>`。"""
        op = f"Lag-{int(lag)}"
        identity = self._identity_or_none(col)
        if identity is None:
            raw = raw_value_identity(str(col))
            return format_feature_name(dataclasses.replace(raw, ops=(op,)))
        return format_feature_name(dataclasses.replace(identity, ops=tuple(identity.ops) + (op,)))

    def _with_lag_names(self, frame: pd.DataFrame, lag: int) -> pd.DataFrame:
        """整表欄名加 L4 lag op（取代改前之 `add_suffix("_Lag_<k>")`；不改值）。"""
        return frame.set_axis([self._lag_name(str(c), lag) for c in frame.columns], axis=1)

    def _normalize_lags(self, lags: List[int]) -> List[int]:
        normalized = sorted({int(lag) for lag in lags if lag >= 1})
        if self._lag_strategy == "adaptive":
            max_lag = max(1, int(self._sequence_length * self._max_lag_ratio))
            for lag in [1, 2, 3]:
                if lag <= max_lag:
                    normalized.append(lag)
            normalized = sorted(set(normalized))
        return normalized

    @staticmethod
    def _resolve_positive_env(env_name: str, default_value: int) -> int:
        raw = os.getenv(env_name, str(default_value)).strip()
        try:
            parsed = int(raw)
        except ValueError:
            parsed = default_value
        return max(1, parsed)
