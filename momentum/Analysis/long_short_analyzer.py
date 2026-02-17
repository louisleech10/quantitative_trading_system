"""Module 8: Long/short analyzer."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.core.logging import get_logger


logger = get_logger(__name__)


class LongShortAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._num_quantiles = int(cfg.get("num_quantiles", 5))
        self._long_quantiles = list(cfg.get("long_quantiles", [4, 5]))
        self._short_quantiles = list(cfg.get("short_quantiles", [1, 2]))
        self._min_samples = int(cfg.get("min_samples", 30))

    def analyze(
        self,
        feature: pd.Series,
        future_returns: pd.Series,
        num_quantiles: int = 5,
    ) -> dict | SkippedResult:
        data = pd.concat(
            [feature.rename("feature"), future_returns.rename("future_returns")],
            axis=1,
        ).dropna()
        if len(data) < self._min_samples:
            return SkippedResult(
                module_name="long_short_analysis",
                reason=f"insufficient samples: {len(data)} < {self._min_samples}",
                error_type="INSUFFICIENT_DATA",
            )

        use_quantiles = max(2, int(num_quantiles or self._num_quantiles))
        bins, used_quantiles = self._assign_quantiles_with_fallback(data["feature"], use_quantiles)
        if bins is None:
            return SkippedResult(
                module_name="long_short_analysis",
                reason="cannot form quantiles",
                error_type="NUMERICAL_ERROR",
            )

        long_q = [q for q in self._long_quantiles if 1 <= q <= used_quantiles]
        short_q = [q for q in self._short_quantiles if 1 <= q <= used_quantiles]
        if not long_q:
            long_q = [used_quantiles]
        if not short_q:
            short_q = [1]

        long_mask = bins.isin([q - 1 for q in long_q])
        short_mask = bins.isin([q - 1 for q in short_q])

        long_returns = data.loc[long_mask, "future_returns"].astype(float)
        short_raw_returns = data.loc[short_mask, "future_returns"].astype(float)
        short_returns = -short_raw_returns

        long_analysis = self._compute_side_metrics(
            data.loc[long_mask, "feature"],
            long_returns,
            side="long",
        )
        short_analysis = self._compute_side_metrics(
            data.loc[short_mask, "feature"],
            short_returns,
            side="short",
        )

        asymmetry = self._classify_asymmetry(
            long_analysis.get("mean_return", 0.0),
            short_analysis.get("mean_return", 0.0),
        )
        recommendation = self._recommendation(
            long_ic=float(long_analysis.get("ic", np.nan)),
            short_ic=float(short_analysis.get("ic", np.nan)),
        )

        return {
            "long_analysis": long_analysis,
            "short_analysis": short_analysis,
            "asymmetry": asymmetry,
            "recommendation": recommendation,
            "num_quantiles_used": used_quantiles,
        }

    def batch_analyze(
        self,
        features_df: pd.DataFrame,
        future_returns: pd.Series,
        top_n: int = 30,
    ) -> dict[str, dict]:
        results: dict[str, dict] = {}
        selected = list(features_df.columns)[: max(1, int(top_n))]

        for name in selected:
            result = self.analyze(features_df[name], future_returns, self._num_quantiles)
            if isinstance(result, SkippedResult):
                results[name] = {
                    "skipped": True,
                    "reason": result.reason,
                    "error_type": result.error_type,
                }
            else:
                results[name] = result

        logger.info("Long/short analysis completed: %s features", len(selected))
        return results

    @staticmethod
    def _compute_side_metrics(feature: pd.Series, side_returns: pd.Series, side: str) -> dict:
        x = pd.Series(feature, dtype=float)
        y = pd.Series(side_returns, dtype=float)
        if len(y.dropna()) == 0:
            return {
                "mean_return": np.nan,
                "ic": np.nan,
                "hit_rate": np.nan,
                "sharpe": np.nan,
                "side": side,
                "samples": 0,
            }

        aligned = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
        if len(aligned) < 2 or aligned["x"].nunique(dropna=True) <= 1 or aligned["y"].nunique(dropna=True) <= 1:
            ic = np.nan
        else:
            corr = spearmanr(aligned["x"].values, aligned["y"].values).correlation
            ic = float(corr) if np.isfinite(corr) else np.nan

        std = float(y.std(ddof=1)) if len(y.dropna()) > 1 else np.nan
        sharpe = float(y.mean() / std) if np.isfinite(std) and std > 0 else np.nan

        return {
            "mean_return": float(y.mean()),
            "ic": ic,
            "hit_rate": float((y > 0).mean()),
            "sharpe": sharpe,
            "side": side,
            "samples": int(len(y.dropna())),
        }

    @staticmethod
    def _classify_asymmetry(long_return: float, short_return: float) -> dict:
        long_abs = abs(float(long_return)) if np.isfinite(long_return) else 0.0
        short_abs = abs(float(short_return)) if np.isfinite(short_return) else 0.0
        total = long_abs + short_abs
        if total == 0.0:
            return {
                "type": "symmetric",
                "long_contribution": 0.5,
                "short_contribution": 0.5,
                "ratio": 1.0,
            }

        ratio = float(long_abs / short_abs) if short_abs > 0 else np.inf
        if ratio > 1.5:
            asym_type = "long_dominant"
        elif ratio < (1 / 1.5):
            asym_type = "short_dominant"
        else:
            asym_type = "symmetric"

        return {
            "type": asym_type,
            "long_contribution": float(long_abs / total),
            "short_contribution": float(short_abs / total),
            "ratio": ratio,
        }

    @staticmethod
    def _recommendation(long_ic: float, short_ic: float) -> str:
        long_good = bool(np.isfinite(long_ic) and long_ic > 0)
        short_good = bool(np.isfinite(short_ic) and short_ic > 0)
        if long_good and short_good:
            return "雙向交易"
        if long_good and not short_good:
            return "只做多"
        if short_good and not long_good:
            return "只做空"
        return "不建議"

    @staticmethod
    def _assign_quantiles_with_fallback(feature: pd.Series, requested: int) -> tuple[pd.Series | None, int]:
        candidates = [requested]
        if requested > 4:
            candidates.append(4)
        if requested > 3:
            candidates.append(3)
        candidates.append(2)

        for q in candidates:
            try:
                bins = pd.qcut(feature, q=q, labels=False, duplicates="drop")
            except ValueError:
                continue
            if bins is None or bins.dropna().empty:
                continue
            actual = int(bins.dropna().nunique())
            if actual >= 2:
                return bins, actual
        return None, 0
