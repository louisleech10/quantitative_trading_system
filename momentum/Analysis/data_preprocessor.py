"""Data preprocessing utilities for IC analysis."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class DataPreprocessor:
    """Stage 1: 數據預處理 — Winsorization, 缺失值處理, 標準化."""

    def __init__(self, config: dict):
        self._config = config or {}

    def preprocess(
        self,
        features_df: pd.DataFrame,
        metadata: Optional[dict] = None,
    ) -> tuple[pd.DataFrame, dict]:
        if features_df is None or features_df.empty:
            raise ValueError("features_df is empty")

        log: dict = {
            "removed_features": {},
            "winsorized_features": [],
            "skipped_winsorization": [],
        }

        df = features_df.copy()

        winsor_cfg = self._config.get("winsorization", {})
        if winsor_cfg.get("enabled", True):
            method = winsor_cfg.get("method", "percentile")
            lower = winsor_cfg.get("lower_percentile", 1.0)
            upper = winsor_cfg.get("upper_percentile", 99.0)
            df, winsor_log = self.winsorize(
                df,
                method=method,
                lower=lower,
                upper=upper,
                metadata=metadata,
            )
            log["winsorized_features"] = winsor_log["winsorized"]
            log["skipped_winsorization"] = winsor_log["skipped"]

        missing_cfg = self._config.get("missing_values", {})
        max_fill_forward = int(missing_cfg.get("max_fill_forward", 3))
        min_coverage = float(missing_cfg.get("min_coverage", 0.3))
        df, removed_low_coverage = self.handle_missing(
            df,
            max_fill_forward=max_fill_forward,
            min_coverage=min_coverage,
        )
        if removed_low_coverage:
            log["removed_features"]["low_coverage"] = removed_low_coverage

        df, removed_constants = self.remove_constant_features(df)
        if removed_constants:
            log["removed_features"]["constant"] = removed_constants

        standardize_cfg = self._config.get("standardize", {})
        method = standardize_cfg.get("method", "none")
        df = self.standardize(df, method=method)

        logger.info(
            "Data preprocessing complete: columns=%s",
            df.shape[1],
        )
        return df, log

    def winsorize(
        self,
        df: pd.DataFrame,
        method: str,
        lower: float,
        upper: float,
        metadata: Optional[dict] = None,
    ) -> tuple[pd.DataFrame, dict]:
        del metadata

        method = method.lower()
        if method == "none":
            return df, {"winsorized": [], "skipped": list(df.columns)}

        winsorized = []
        skipped = []
        clipped = df.copy()

        for column in clipped.columns:
            series = clipped[column]
            if self._is_type_feature(series):
                skipped.append(column)
                continue

            clipped[column] = self._clip_series(series, method, lower, upper)
            winsorized.append(column)

        return clipped, {"winsorized": winsorized, "skipped": skipped}

    def handle_missing(
        self,
        df: pd.DataFrame,
        max_fill_forward: int,
        min_coverage: float,
    ) -> tuple[pd.DataFrame, list[str]]:
        filled = df.ffill(limit=max_fill_forward)
        coverage = filled.notna().mean()
        removed = coverage[coverage < min_coverage].index.tolist()
        if removed:
            filled = filled.drop(columns=removed)
        return filled, removed

    def remove_constant_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        nunique = df.nunique(dropna=True)
        removed = nunique[nunique <= 1].index.tolist()
        if removed:
            df = df.drop(columns=removed)
        return df, removed

    def standardize(self, df: pd.DataFrame, method: str = "none") -> pd.DataFrame:
        method = method.lower()
        if method == "none":
            return df
        if method == "cross_sectional_zscore":
            mean = df.mean(axis=1)
            std = df.std(axis=1).replace(0, np.nan)
            return df.sub(mean, axis=0).div(std, axis=0).fillna(0.0)
        if method == "time_series_zscore":
            mean = df.mean(axis=0)
            std = df.std(axis=0).replace(0, np.nan)
            return df.sub(mean, axis=1).div(std, axis=1).fillna(0.0)
        if method == "rank_transform":
            return df.rank(axis=1, pct=True)

        raise ValueError(f"Unknown standardize method: {method}")

    def _clip_series(
        self,
        series: pd.Series,
        method: str,
        lower: float,
        upper: float,
    ) -> pd.Series:
        if method == "percentile":
            lower_q = lower / 100.0
            upper_q = upper / 100.0
            lo = series.quantile(lower_q)
            hi = series.quantile(upper_q)
            return series.clip(lo, hi)

        if method == "mad":
            median = np.nanmedian(series)
            mad = np.nanmedian(np.abs(series - median))
            if mad == 0 or np.isnan(mad):
                return series
            bound = 3.5 * mad
            return series.clip(median - bound, median + bound)

        if method == "zscore":
            mean = series.mean()
            std = series.std()
            if std == 0 or np.isnan(std):
                return series
            bound = 3.0 * std
            return series.clip(mean - bound, mean + bound)

        raise ValueError(f"Unknown winsorization method: {method}")

    @staticmethod
    def _is_type_feature(series: pd.Series) -> bool:
        values = set(series.dropna().unique())
        if not values:
            return False
        return values.issubset({-100, 0, 100})
