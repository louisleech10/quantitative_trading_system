"""Module 5: Rolling out-of-sample validator.

ICPERF Task 0.4 ⑬⑳（docs/ICPERF_SPEC.md）：
- 切分依**原始時間位置**（`features_df` 之索引；標籤依索引對齊），有限值遮罩只在逐切分算 IC 時套用，不壓縮時間軸。
- 訓練段末與測試段首隔 purge ≥ `horizon`（標籤＝h 根前瞻報酬時，訓練段只用 [start, train_end − h)，其標籤不讀測試段價格）。
  `horizon` 為必填關鍵字（缺 ⇒ TypeError）。
- `method` ∈ spearman／pearson／kendall（kendall＝`scipy.stats.kendalltau`）；常數窗 IC 未定義 ⇒ NaN、該切分不入統計。
- 命中率／退化率以方向 d 對齊：d 取呼叫端傳入之上游 `direction`；未傳（或該特徵缺）⇒ sign(全段點 IC)；d＝0 ⇒ 兩者 NaN。
- 回顯實際步長（步長減半後）與逐特徵有效切分數。
"""

from __future__ import annotations

from typing import Mapping, Optional

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.core.logging import get_logger


logger = get_logger(__name__)

_METHODS = ("spearman", "pearson", "kendall")
#: 逐切分 IC 之最少有限配對列數（沿用現行）
_MIN_ROWS = 5


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
        *,
        horizon: int,
        direction: Optional[int] = None,
    ) -> dict | SkippedResult:
        """單特徵滾動 OOS。時間軸＝`feature` 之索引（標籤依索引對齊）；`direction` None ⇒ sign(全段點 IC)。"""
        method = self._check_method(method)
        purge = self._check_horizon(horizon)
        x_all, y_all = self._align(feature, labels)
        finite = np.isfinite(x_all) & np.isfinite(y_all)
        n_finite = int(finite.sum())
        minimum_required = self._train_window + self._test_window
        if n_finite < minimum_required:
            return SkippedResult(
                module_name="rolling_oos",
                reason=f"insufficient samples: {n_finite} < {minimum_required}",
                error_type="INSUFFICIENT_DATA",
            )

        splits = self._generate_splits(len(x_all))
        if len(splits) == 0:
            return SkippedResult(
                module_name="rolling_oos",
                reason="no valid splits generated",
                error_type="INSUFFICIENT_DATA",
            )

        d = self._resolve_direction(direction, x_all, y_all, finite, method)

        sampled = []
        is_values = []
        oos_values = []
        for split_id, (train_idx, test_idx) in enumerate(splits):
            train_start, train_end = train_idx.start, train_idx.stop - purge
            if train_end <= train_start:
                continue
            is_ic = self._masked_ic(x_all[train_start:train_end], y_all[train_start:train_end], method)
            oos_ic = self._masked_ic(x_all[test_idx.start:test_idx.stop], y_all[test_idx.start:test_idx.stop], method)
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
        std_oos = float(np.std(oos_arr, ddof=0))
        if d == 0:
            hit_rate = np.nan
            degradation_ratio = np.nan
        else:
            hit_rate = float(np.mean(d * oos_arr > 0))
            degradation_ratio = (
                float((d * mean_is - d * mean_oos) / abs(mean_is)) if mean_is != 0 else 0.0
            )

        oos_stability = {
            "mean_oos_ic": mean_oos,
            "std_oos_ic": std_oos,
            "oos_hit_rate": hit_rate,
            "mean_is_oos_gap": float(np.mean(is_arr - oos_arr)),
            "oos_icir": float(mean_oos / std_oos) if std_oos > 0 else np.nan,
            "degradation_ratio": degradation_ratio,
        }

        assessment = self._classify_assessment(hit_rate, degradation_ratio)

        return {
            "oos_stability": oos_stability,
            "assessment": assessment,
            "direction": int(d),
            "n_valid_splits": len(sampled),
            "splits_sampled": sampled,
        }

    def validate_batch(
        self,
        features_df: pd.DataFrame,
        labels: pd.Series,
        *,
        horizon: int,
        method: str = "spearman",
        direction: Optional[Mapping[str, int]] = None,
        top_n: int = 30,
    ) -> dict[str, dict]:
        method = self._check_method(method)
        self._check_horizon(horizon)
        results: dict[str, dict] = {}
        selected = list(features_df.columns)[: max(1, int(top_n))]
        direction_map = dict(direction) if direction is not None else {}

        robust_count = 0
        moderate_count = 0
        overfit_count = 0
        success_count = 0

        for name in selected:
            result = self.validate(
                features_df[name],
                labels,
                method=method,
                horizon=horizon,
                direction=direction_map.get(name),
            )
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

        splits, actual_step = self._generate_splits_with_step(len(features_df.index))
        logger.info("Rolling OOS completed: %s features", len(selected))
        return {
            "config": {
                "train_window": self._train_window,
                "test_window": self._test_window,
                "step": actual_step,
                "n_splits": len(splits),
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
        return self._generate_splits_with_step(n_samples)[0]

    def _generate_splits_with_step(self, n_samples: int) -> tuple[list[tuple[range, range]], int]:
        """固定窗切分（原始時間位置）；切分數 < min_splits 則步長減半（至多 6 輪）。回 (切分, 實際步長)。"""
        splits: list[tuple[range, range]] = []
        step = self._step

        if n_samples < self._train_window + self._test_window:
            return splits, step

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

        return splits, step

    @staticmethod
    def _check_method(method: str) -> str:
        if method not in _METHODS:
            raise ValueError(f"rolling_oos method must be one of {_METHODS}, got {method!r}")
        return method

    @staticmethod
    def _check_horizon(horizon: int) -> int:
        if isinstance(horizon, bool) or not isinstance(horizon, (int, np.integer)) or int(horizon) < 0:
            raise ValueError(f"horizon must be a non-negative int, got {horizon!r}")
        return int(horizon)

    @staticmethod
    def _align(feature: pd.Series, labels: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        """時間軸＝特徵索引；標籤依索引對齊（缺 ⇒ NaN），不剔除任何列。"""
        y = labels.reindex(feature.index)
        return feature.to_numpy(dtype=float), y.to_numpy(dtype=float)

    def _resolve_direction(
        self,
        direction: Optional[int],
        x: np.ndarray,
        y: np.ndarray,
        finite: np.ndarray,
        method: str,
    ) -> int:
        if direction is not None:
            d = int(direction)
            if d not in (-1, 0, 1):
                raise ValueError(f"direction must be -1, 0 or +1, got {direction!r}")
            return d
        ic = self._compute_ic(pd.Series(x[finite]), pd.Series(y[finite]), method)
        if not np.isfinite(ic) or ic == 0:
            return 0
        return 1 if ic > 0 else -1

    def _masked_ic(self, x: np.ndarray, y: np.ndarray, method: str) -> float:
        mask = np.isfinite(x) & np.isfinite(y)
        return self._compute_ic(pd.Series(x[mask]), pd.Series(y[mask]), method)

    @staticmethod
    def _compute_ic(x: pd.Series, y: pd.Series, method: str) -> float:
        """兩序列（已為有限配對）之 IC：列數 < 5 或任一欄常數（相關未定義）⇒ NaN。"""
        if len(x) < _MIN_ROWS or len(y) < _MIN_ROWS:
            return np.nan
        if x.nunique(dropna=True) <= 1 or y.nunique(dropna=True) <= 1:
            return np.nan
        xv = x.to_numpy(dtype=float)
        yv = y.to_numpy(dtype=float)
        if method == "kendall":
            corr = kendalltau(xv, yv).statistic
        elif method == "pearson":
            corr = np.corrcoef(xv, yv)[0, 1]
        else:
            corr = spearmanr(xv, yv).correlation
        return float(corr) if np.isfinite(corr) else np.nan

    def _classify_assessment(self, hit_rate: float, degradation_ratio: float) -> str:
        if hit_rate >= self._robust_hit_rate and degradation_ratio < self._robust_max_degradation:
            return "robust"
        if hit_rate >= self._moderate_hit_rate and degradation_ratio < self._moderate_max_degradation:
            return "moderate"
        return "overfitting"
