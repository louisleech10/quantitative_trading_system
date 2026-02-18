"""Sample weight calculator module."""

from __future__ import annotations

from typing import List, Dict, Optional, Any, Tuple

import numpy as np
import pandas as pd

from pydantic import BaseModel, Field

from momentum.core.logging import get_logger


class SampleWeightConfig(BaseModel):
    enabled: bool = True
    strategies: List[str] = Field(default_factory=lambda: ["time_decay", "class_balance"])
    combination: str = Field(default="multiply", pattern="^(multiply|additive)$")
    time_decay_half_life: int = Field(default=180, ge=10, le=3650)
    time_decay_type: str = Field(default="exponential", pattern="^(exponential|linear)$")
    class_balance_method: str = Field(default="balanced", pattern="^(balanced|sqrt|custom)$")
    min_weight: float = Field(default=0.01, ge=0.0, lt=1.0)


class SampleWeightCalculator:
    """樣本加權計算器。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = SampleWeightConfig(**(config or {}))
        self.logger = get_logger(__name__)

    def compute_time_decay(
        self,
        timestamps: np.ndarray,
        half_life: Optional[int] = None,
        decay_type: str = "exponential",
    ) -> np.ndarray:
        effective_half_life = int(self.config.time_decay_half_life if half_life is None else half_life)
        if effective_half_life <= 0:
            raise ValueError("half_life 必須 > 0")

        ts_series = pd.Series(timestamps)
        if ts_series.isna().any():
            self.logger.warning("SampleWeightCalculator: timestamps 含 NaN，將移除 NaN 後計算")
            ts_series = ts_series.dropna().reset_index(drop=True)

        if ts_series.empty:
            return np.ones(0)

        parsed = pd.to_datetime(ts_series, errors="coerce")
        if parsed.isna().any():
            self.logger.warning("SampleWeightCalculator: timestamps 解析失敗，fallback 等權重")
            return np.ones(len(ts_series))

        if not parsed.is_monotonic_increasing:
            self.logger.warning("SampleWeightCalculator: timestamps 非遞增，將排序後計算")
            parsed = parsed.sort_values(ignore_index=True)

        age_days = (parsed.max() - parsed).dt.total_seconds().to_numpy() / (24 * 3600)
        if decay_type == "linear":
            max_age = np.max(age_days) if np.max(age_days) > 0 else 1.0
            weights = 1.0 - (age_days / max_age)
        else:
            lam = np.log(2) / effective_half_life
            weights = np.exp(-lam * age_days)

        weights = np.maximum(weights, self.config.min_weight)
        return self._normalize(weights)

    def compute_class_balance(
        self,
        y: np.ndarray,
        method: str = "balanced",
        custom_ratio: Optional[float] = None,
    ) -> np.ndarray:
        y_arr = np.asarray(y).astype(int)
        if y_arr.size == 0:
            return np.ones(0)

        classes, counts = np.unique(y_arr, return_counts=True)
        if classes.size < 2:
            self.logger.warning("SampleWeightCalculator: y 單一類別，回傳等權重")
            return np.ones_like(y_arr, dtype=float)

        n_samples = len(y_arr)
        if method == "sqrt":
            class_weight = {cls: np.sqrt(n_samples / cnt) for cls, cnt in zip(classes, counts)}
        elif method == "custom" and custom_ratio is not None:
            minority = classes[np.argmin(counts)]
            class_weight = {cls: 1.0 for cls in classes}
            class_weight[minority] = float(custom_ratio)
        else:
            class_weight = {cls: n_samples / (len(classes) * cnt) for cls, cnt in zip(classes, counts)}

        weights = np.asarray([class_weight[v] for v in y_arr], dtype=float)
        return self._normalize(weights)

    def compute_return_based(
        self,
        returns: np.ndarray,
        method: str = "abs_return",
    ) -> np.ndarray:
        ret = np.asarray(returns, dtype=float)
        if ret.size == 0:
            return np.ones(0)

        if np.allclose(ret, 0.0):
            self.logger.warning("SampleWeightCalculator: returns 全為 0，回傳等權重")
            return np.ones_like(ret, dtype=float)

        if method == "squared_return":
            weights = np.square(ret)
        elif method == "positive_focus":
            weights = np.where(ret > 0, np.abs(ret), np.abs(ret) * 0.5)
        else:
            weights = np.abs(ret)

        weights = np.maximum(weights, self.config.min_weight)
        return self._normalize(weights)

    def compute_uniqueness(
        self,
        label_spans: List[Tuple[int, int]],
        n_samples: int,
    ) -> np.ndarray:
        if n_samples <= 0:
            return np.ones(0)

        if not label_spans:
            self.logger.warning("SampleWeightCalculator: label_spans 為空，回傳等權重")
            return np.ones(n_samples)

        overlap = np.zeros(n_samples, dtype=float)
        for start, end in label_spans:
            s = max(0, int(start))
            e = min(n_samples, int(end))
            if s >= e:
                continue
            overlap[s:e] += 1.0

        overlap_ratio = float(np.mean(overlap > 1.0)) if n_samples > 0 else 0.0
        if overlap_ratio > 0.99:
            self.logger.warning("SampleWeightCalculator: label_spans 重疊過高，建議切換 time_decay")

        overlap[overlap == 0] = 1.0
        uniqueness = 1.0 / overlap
        return self._normalize(uniqueness)

    def compute_combined_weights(
        self,
        timestamps=None,
        y=None,
        returns=None,
        label_spans=None,
        strategies: List[str] = ["time_decay", "class_balance"],
        combination: str = "multiply",
        **kwargs,
    ) -> np.ndarray:
        if self.config.min_weight > 1.0:
            raise ValueError("min_weight 不能 > 1.0")

        base_n = 0
        for item in [timestamps, y, returns]:
            if item is not None:
                base_n = len(item)
                break

        if base_n == 0 and label_spans:
            base_n = int(max(end for _, end in label_spans))

        if base_n < 10 and base_n > 0:
            self.logger.warning("SampleWeightCalculator: 樣本數 < 10，權重可能不穩定")

        if not strategies:
            return np.ones(base_n if base_n > 0 else 0)

        strategy_weights: List[np.ndarray] = []
        for strategy in strategies:
            if strategy == "time_decay" and timestamps is not None:
                strategy_weights.append(self.compute_time_decay(timestamps=timestamps, half_life=kwargs.get("half_life"), decay_type=kwargs.get("decay_type", self.config.time_decay_type)))
            elif strategy == "class_balance" and y is not None:
                strategy_weights.append(self.compute_class_balance(y=y, method=kwargs.get("class_balance_method", self.config.class_balance_method), custom_ratio=kwargs.get("custom_ratio")))
            elif strategy == "return_based" and returns is not None:
                strategy_weights.append(self.compute_return_based(returns=returns, method=kwargs.get("return_method", "abs_return")))
            elif strategy == "uniqueness":
                if label_spans:
                    uniq_weights = self.compute_uniqueness(label_spans=label_spans, n_samples=base_n)
                    overlap_ratio = float(np.mean(uniq_weights < 0.2)) if uniq_weights.size > 0 else 0.0
                    if overlap_ratio > 0.99 and timestamps is not None:
                        self.logger.warning("SampleWeightCalculator: uniqueness 極端重疊，fallback time_decay")
                        strategy_weights.append(self.compute_time_decay(timestamps=timestamps))
                    else:
                        strategy_weights.append(uniq_weights)
                elif timestamps is not None:
                    self.logger.warning("SampleWeightCalculator: uniqueness 缺少 label_spans，fallback time_decay")
                    strategy_weights.append(self.compute_time_decay(timestamps=timestamps))

        if not strategy_weights:
            return np.ones(base_n if base_n > 0 else 0)

        min_len = min(len(weights) for weights in strategy_weights)
        aligned = [weights[:min_len] for weights in strategy_weights]

        if combination == "additive":
            coeffs = kwargs.get("coefficients")
            if coeffs is None:
                self.logger.warning("SampleWeightCalculator: additive 無係數，採等權平均")
                coeffs = np.ones(len(aligned), dtype=float)
            coeffs = np.asarray(coeffs, dtype=float)
            coeffs = coeffs / np.sum(coeffs)
            stacked = np.vstack(aligned)
            combined = np.sum(stacked * coeffs[:, None], axis=0)
        else:
            combined = np.ones(min_len, dtype=float)
            for weights in aligned:
                combined *= weights

        combined = np.maximum(combined, self.config.min_weight)
        return self._normalize(combined)

    def get_weight_summary(self, weights: np.ndarray) -> Dict[str, float]:
        w = np.asarray(weights, dtype=float)
        if w.size == 0:
            return {
                "n_samples": 0,
                "effective_n": 0.0,
                "efficiency_ratio": 0.0,
                "weight_mean": 0.0,
                "weight_std": 0.0,
                "weight_min": 0.0,
                "weight_max": 0.0,
            }

        sum_w = float(np.sum(w))
        sum_w2 = float(np.sum(np.square(w)))
        effective_n = (sum_w ** 2) / max(sum_w2, 1e-12)
        n_samples = int(len(w))

        return {
            "n_samples": n_samples,
            "effective_n": float(effective_n),
            "efficiency_ratio": float(effective_n / n_samples),
            "weight_mean": float(np.mean(w)),
            "weight_std": float(np.std(w)),
            "weight_min": float(np.min(w)),
            "weight_max": float(np.max(w)),
        }

    @staticmethod
    def _normalize(weights: np.ndarray) -> np.ndarray:
        if weights.size == 0:
            return weights
        mean_w = float(np.mean(weights))
        if mean_w <= 0:
            return np.ones_like(weights, dtype=float)
        return weights / mean_w
