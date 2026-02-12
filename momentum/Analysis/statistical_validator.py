"""Statistical validation utilities for IC analysis."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class StatisticalValidator:
    """Stage 5 (部分): IC 統計驗證。"""

    def __init__(self, config: dict):
        self._config = config or {}
        self._default_p_value_max = float(self._config.get("p_value_max", 0.05))

    def compute_ic_statistics(self, rolling_ic_dict: dict) -> dict[str, dict]:
        """計算每個特徵的 IC 統計量。"""

        stats_results: dict[str, dict] = {}
        for feature, windows in (rolling_ic_dict or {}).items():
            values = self._collect_values(windows)
            ic_stats = self._compute_stats(values)
            stats_results[feature] = ic_stats
        return stats_results

    def apply_significance_filter(
        self,
        ic_stats: dict,
        p_value_max: float = 0.05,
        sample_tier: str = "sufficient",
    ) -> dict[str, dict]:
        """根據 p-value 過濾。"""

        if p_value_max is None:
            p_value_max = self._default_p_value_max

        threshold = float(p_value_max)
        if sample_tier == "low_confidence":
            threshold = max(threshold, 0.10)

        filtered: dict[str, dict] = {}
        for feature, stats_item in (ic_stats or {}).items():
            p_value = stats_item.get("p_value", np.nan)
            if np.isnan(p_value):
                continue
            if p_value <= threshold:
                filtered[feature] = stats_item
        return filtered

    def adjust_multiple_comparisons(
        self, p_values: dict, method: str = "fdr_bh"
    ) -> dict[str, float]:
        """多重比較校正 (Bonferroni / FDR)。"""

        if not p_values:
            return {}

        method = (method or "").lower()
        if method == "bonferroni":
            return self._bonferroni(p_values)
        if method in {"fdr_bh", "fdr"}:
            return self._fdr_bh(p_values)

        logger.warning("Unknown adjustment method=%s, return raw p-values", method)
        return {key: float(value) for key, value in p_values.items()}

    def _collect_values(self, windows: object) -> np.ndarray:
        if windows is None:
            return np.array([], dtype=float)
        if isinstance(windows, dict):
            values: list[float] = []
            for _, series in sorted(windows.items()):
                values.extend(self._to_list(series))
            return np.array(values, dtype=float)
        return np.array(self._to_list(windows), dtype=float)

    @staticmethod
    def _to_list(values: object) -> list[float]:
        if values is None:
            return []
        if isinstance(values, np.ndarray):
            return values.astype(float).tolist()
        if isinstance(values, (list, tuple, pd.Series)):
            return pd.Series(values).astype(float).tolist()
        return [float(values)]

    def _compute_stats(self, values: np.ndarray) -> dict:
        values = values[np.isfinite(values)]
        n_obs = int(values.size)
        if n_obs < 2:
            return {
                "t_stat": np.nan,
                "p_value": np.nan,
                "ci_lower": np.nan,
                "ci_upper": np.nan,
                "n_observations": n_obs,
            }

        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1))
        if std == 0:
            return {
                "t_stat": np.nan,
                "p_value": np.nan,
                "ci_lower": np.nan,
                "ci_upper": np.nan,
                "n_observations": n_obs,
            }

        t_stat = float(mean / (std / np.sqrt(n_obs)))
        ttest = stats.ttest_1samp(values, 0.0, nan_policy="omit")
        p_value = float(ttest.pvalue)
        ci_lower, ci_upper = self._confidence_interval(mean, std, n_obs)
        return {
            "t_stat": t_stat,
            "p_value": p_value,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "n_observations": n_obs,
        }

    @staticmethod
    def _confidence_interval(
        mean: float, std: float, n_obs: int, alpha: float = 0.05
    ) -> tuple[float, float]:
        if n_obs < 2 or std == 0:
            return np.nan, np.nan
        t_crit = stats.t.ppf(1 - alpha / 2, df=n_obs - 1)
        margin = t_crit * std / np.sqrt(n_obs)
        return float(mean - margin), float(mean + margin)

    @staticmethod
    def _bonferroni(p_values: dict) -> dict[str, float]:
        total = len(p_values)
        adjusted: dict[str, float] = {}
        for key, value in p_values.items():
            adj = min(float(value) * total, 1.0)
            adjusted[key] = adj
        return adjusted

    @staticmethod
    def _fdr_bh(p_values: dict) -> dict[str, float]:
        items = [(key, float(value)) for key, value in p_values.items()]
        items.sort(key=lambda item: item[1])
        n = len(items)
        adjusted_values = [0.0] * n
        for idx, (_, p_value) in enumerate(items, start=1):
            adjusted_values[idx - 1] = min(p_value * n / idx, 1.0)

        for idx in range(n - 2, -1, -1):
            adjusted_values[idx] = min(
                adjusted_values[idx], adjusted_values[idx + 1]
            )

        adjusted: dict[str, float] = {}
        for (key, _), adj in zip(items, adjusted_values):
            adjusted[key] = float(adj)
        return adjusted
