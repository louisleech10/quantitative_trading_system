"""Module 5: Rolling out-of-sample validator."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.core.logging import get_logger


logger = get_logger(__name__)


class RollingOOSValidator:
    def __init__(self, config: dict):
        cfg = config or {}
        thresholds = cfg.get("assessment_thresholds", {})
        self._config = cfg
        self._train_window = int(cfg.get("train_window", 252))
        self._test_window = int(cfg.get("test_window", 63))
        self._step = int(cfg.get("step", 21))
        self._min_splits = int(cfg.get("min_splits", 5))
        self._robust_hit_rate = float(thresholds.get("robust_hit_rate", 0.7))
        self._robust_max_degradation = float(thresholds.get("robust_max_degradation", 0.3))
        self._moderate_hit_rate = float(thresholds.get("moderate_hit_rate", 0.5))
        self._moderate_max_degradation = float(thresholds.get("moderate_max_degradation", 0.5))

    def validate(
        self,
        feature: pd.Series,
        labels: pd.Series,
        method: str = "spearman",
    ) -> dict | SkippedResult:
        data = pd.concat([feature.rename("feature"), labels.rename("label")], axis=1).dropna()
        minimum_required = self._train_window + self._test_window
        if len(data) < minimum_required:
            return SkippedResult(
                module_name="rolling_oos",
                reason=f"insufficient samples: {len(data)} < {minimum_required}",
                error_type="INSUFFICIENT_DATA",
            )

        splits = self._generate_splits(len(data))
        if len(splits) == 0:
            return SkippedResult(
                module_name="rolling_oos",
                reason="no valid splits generated",
                error_type="INSUFFICIENT_DATA",
            )

        sampled = []
        is_values = []
        oos_values = []

        x = data["feature"].reset_index(drop=True)
        y = data["label"].reset_index(drop=True)

        for split_id, (train_idx, test_idx) in enumerate(splits):
            train_x = x.iloc[list(train_idx)]
            train_y = y.iloc[list(train_idx)]
            test_x = x.iloc[list(test_idx)]
            test_y = y.iloc[list(test_idx)]

            is_ic = self._compute_ic(train_x, train_y, method)
            oos_ic = self._compute_ic(test_x, test_y, method)
            if not np.isfinite(is_ic) or not np.isfinite(oos_ic):
                continue

            is_values.append(is_ic)
            oos_values.append(oos_ic)
            sampled.append({"split_id": split_id, "is_ic": float(is_ic), "oos_ic": float(oos_ic)})

        if len(oos_values) == 0:
            return SkippedResult(
                module_name="rolling_oos",
                reason="all splits invalid",
                error_type="INSUFFICIENT_DATA",
            )

        is_arr = np.array(is_values, dtype=float)
        oos_arr = np.array(oos_values, dtype=float)
        mean_is = float(np.mean(is_arr))
        mean_oos = float(np.mean(oos_arr))
        degradation_ratio = (
            float((mean_is - mean_oos) / abs(mean_is)) if mean_is != 0 else 0.0
        )

        oos_stability = {
            "mean_oos_ic": mean_oos,
            "std_oos_ic": float(np.std(oos_arr, ddof=0)),
            "oos_hit_rate": float(np.mean(oos_arr > 0)),
            "mean_is_oos_gap": float(np.mean(is_arr - oos_arr)),
            "oos_icir": float(mean_oos / np.std(oos_arr, ddof=0)) if np.std(oos_arr, ddof=0) > 0 else np.nan,
            "degradation_ratio": degradation_ratio,
        }

        assessment = self._classify_assessment(
            oos_stability["oos_hit_rate"],
            degradation_ratio,
        )

        return {
            "oos_stability": oos_stability,
            "assessment": assessment,
            "splits_sampled": sampled,
        }

    def validate_batch(
        self,
        features_df: pd.DataFrame,
        labels: pd.Series,
        top_n: int = 30,
        method: str = "spearman",
    ) -> dict[str, dict]:
        results: dict[str, dict] = {}
        selected = list(features_df.columns)[: max(1, int(top_n))]

        robust_count = 0
        moderate_count = 0
        overfit_count = 0
        success_count = 0

        for name in selected:
            result = self.validate(features_df[name], labels, method=method)
            if isinstance(result, SkippedResult):
                results[name] = {
                    "skipped": True,
                    "reason": result.reason,
                    "error_type": result.error_type,
                }
                continue

            results[name] = result
            success_count += 1
            if result["assessment"] == "robust":
                robust_count += 1
            elif result["assessment"] == "moderate":
                moderate_count += 1
            else:
                overfit_count += 1

        logger.info("Rolling OOS completed: %s features", len(selected))
        return {
            "config": {
                "train_window": self._train_window,
                "test_window": self._test_window,
                "step": self._step,
                "n_splits": len(self._generate_splits(len(labels.dropna()))),
            },
            "features": results,
            "summary": {
                "total_validated": success_count,
                "robust_count": robust_count,
                "moderate_count": moderate_count,
                "overfitting_count": overfit_count,
            },
        }

    def _generate_splits(self, n_samples: int) -> list[tuple[range, range]]:
        splits: list[tuple[range, range]] = []
        step = self._step

        if n_samples < self._train_window + self._test_window:
            return splits

        for _ in range(6):
            splits.clear()
            start = 0
            while True:
                train_start = start
                train_end = train_start + self._train_window
                test_end = train_end + self._test_window
                if test_end > n_samples:
                    break
                splits.append((range(train_start, train_end), range(train_end, test_end)))
                start += step

            if len(splits) >= self._min_splits or step <= 1:
                break
            step = max(1, step // 2)

        return splits

    @staticmethod
    def _compute_ic(x: pd.Series, y: pd.Series, method: str) -> float:
        if len(x) < 5 or len(y) < 5:
            return np.nan
        if x.nunique(dropna=True) <= 1 or y.nunique(dropna=True) <= 1:
            return 0.0
        if method != "spearman":
            corr = np.corrcoef(x.values.astype(float), y.values.astype(float))[0, 1]
            return float(corr) if np.isfinite(corr) else np.nan
        corr = spearmanr(x.values.astype(float), y.values.astype(float)).correlation
        return float(corr) if np.isfinite(corr) else np.nan

    def _classify_assessment(self, hit_rate: float, degradation_ratio: float) -> str:
        if hit_rate >= self._robust_hit_rate and degradation_ratio < self._robust_max_degradation:
            return "robust"
        if hit_rate >= self._moderate_hit_rate and degradation_ratio < self._moderate_max_degradation:
            return "moderate"
        return "overfitting"
