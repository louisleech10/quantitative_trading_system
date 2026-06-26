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
        fit_mask: Optional[np.ndarray] = None,
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
                fit_mask=fit_mask,
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
            fit_mask=fit_mask,
        )
        if removed_low_coverage:
            log["removed_features"]["low_coverage"] = removed_low_coverage

        df, removed_constants = self.remove_constant_features(df, fit_mask=fit_mask)
        if removed_constants:
            log["removed_features"]["constant"] = removed_constants

        standardize_cfg = self._config.get("standardize", {})
        method = standardize_cfg.get("method", "none")
        df = self.standardize(df, method=method, fit_mask=fit_mask)

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
        fit_mask: Optional[np.ndarray] = None,
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
            fit_series = self._select_fit_series(series, fit_mask)
            if self._is_type_feature(fit_series):
                skipped.append(column)
                continue

            clipped[column] = self._clip_series(
                series,
                method,
                lower,
                upper,
                fit_mask=fit_mask,
            )
            winsorized.append(column)

        return clipped, {"winsorized": winsorized, "skipped": skipped}

    def handle_missing(
        self,
        df: pd.DataFrame,
        max_fill_forward: int,
        min_coverage: float,
        fit_mask: Optional[np.ndarray] = None,
    ) -> tuple[pd.DataFrame, list[str]]:
        filled = df.ffill(limit=max_fill_forward)
        fit_df = self._select_fit_frame(filled, fit_mask)
        coverage = fit_df.notna().mean()
        removed = coverage[coverage < min_coverage].index.tolist()
        if removed:
            filled = filled.drop(columns=removed)
        return filled, removed

    def remove_constant_features(
        self,
        df: pd.DataFrame,
        fit_mask: Optional[np.ndarray] = None,
    ) -> tuple[pd.DataFrame, list[str]]:
        fit_df = self._select_fit_frame(df, fit_mask)
        nunique = fit_df.nunique(dropna=True)
        removed = nunique[nunique <= 1].index.tolist()
        if removed:
            df = df.drop(columns=removed)
        return df, removed

    def standardize(
        self,
        df: pd.DataFrame,
        method: str = "none",
        fit_mask: Optional[np.ndarray] = None,
    ) -> pd.DataFrame:
        method = method.lower()
        if method == "none":
            return df
        if method == "cross_sectional_zscore":
            mean = df.mean(axis=1)
            std = df.std(axis=1).replace(0, np.nan)
            return df.sub(mean, axis=0).div(std, axis=0).fillna(0.0)
        if method == "time_series_zscore":
            fit_df = self._select_fit_frame(df, fit_mask)
            mean = fit_df.mean(axis=0)
            std = fit_df.std(axis=0).replace(0, np.nan)
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
        fit_mask: Optional[np.ndarray] = None,
    ) -> pd.Series:
        fit_series = self._select_fit_series(series, fit_mask)
        if fit_series.dropna().empty:
            return series
        if method == "percentile":
            lower_q = lower / 100.0
            upper_q = upper / 100.0
            lo = fit_series.quantile(lower_q)
            hi = fit_series.quantile(upper_q)
            return series.clip(lo, hi)

        if method == "mad":
            median = np.nanmedian(fit_series)
            mad = np.nanmedian(np.abs(fit_series - median))
            if mad == 0 or np.isnan(mad):
                return series
            bound = 3.5 * mad
            return series.clip(median - bound, median + bound)

        if method == "zscore":
            mean = fit_series.mean()
            std = fit_series.std()
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

    @staticmethod
    def _coerce_fit_mask(length: int, fit_mask: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if fit_mask is None:
            return None
        mask = np.asarray(fit_mask, dtype=bool)
        if mask.shape[0] != length:
            raise ValueError("fit_mask length must match data length")
        if not bool(mask.any()):
            raise ValueError("fit_mask must select at least one row")
        return mask

    @classmethod
    def _select_fit_frame(
        cls,
        df: pd.DataFrame,
        fit_mask: Optional[np.ndarray],
    ) -> pd.DataFrame:
        mask = cls._coerce_fit_mask(len(df), fit_mask)
        return df if mask is None else df.loc[mask]

    @classmethod
    def _select_fit_series(
        cls,
        series: pd.Series,
        fit_mask: Optional[np.ndarray],
    ) -> pd.Series:
        mask = cls._coerce_fit_mask(len(series), fit_mask)
        return series if mask is None else series.loc[mask]
