"""Module 4: Parameter sensitivity analyzer.

ICPERF Task 0.4 ⑧⑬⑳（docs/ICPERF_SPEC.md）：
- `ic_mean`＝全段點 IC，依請求之 `method`（spearman／pearson／kendall）於特徵與標籤之逐對有限值上計（標籤依特徵索引對齊，
  不壓縮時間軸）；列數 < 5 或任一欄常數 ⇒ NaN。
- `icir`＝滾動 IC 之均值／標準差（同 `ICEngine.compute_icir`：nanmean／nanstd ddof=0，std ≤ 0 ⇒ NaN）。滾動 IC 逐特徵
  獨立、時間軸＝標籤有限之列（同 Task 0.4 ④）；窗內特徵有非有限值或窗內常數 ⇒ 該窗 NaN。窗長取設定 `icir_window`
  （呼叫端可於設定 dict 傳入 IC 頁之 ICIR 窗；未傳 ⇒ 63）。
- `best_param` 以 |ic_mean| 判強度（同強度取首個），並記方向 `best_param_direction`（上游 `direction` 優先；未傳 ⇒
  sign(該變體 ic_mean)）。
- `auto_detect_families`＝False ⇒ 只依 metadata 之 indicator 分組，不以名稱樣式自動偵測。
"""

from __future__ import annotations

import re
from typing import Mapping, Optional

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from scipy.stats import kendalltau, spearmanr

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.pit_stats import rolling_window_rank_corr
from momentum.core.logging import get_logger


logger = get_logger(__name__)

_METHODS = ("spearman", "pearson", "kendall")
#: 點 IC 之最少有限配對列數（沿用現行）
_MIN_ROWS = 5


class ParameterSensitivityAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._min_family_size = int(cfg.get("min_family_size", 3))
        self._ic_std_threshold_low = float(cfg.get("ic_std_threshold_low", 0.02))
        self._ic_std_threshold_high = float(cfg.get("ic_std_threshold_high", 0.05))
        self._auto_detect_families = bool(cfg.get("auto_detect_families", True))
        self._icir_window = int(cfg.get("icir_window", 63))

    def detect_feature_families(
        self,
        feature_names: list[str],
        metadata: Optional[dict] = None,
    ) -> dict[str, list[str]]:
        if metadata:
            grouped: dict[str, list[str]] = {}
            for name in feature_names:
                meta = metadata.get(name, {}) if isinstance(metadata, dict) else {}
                indicator = str(meta.get("indicator", ""))
                source = str(meta.get("data_source", ""))
                if indicator:
                    key = f"{source}_{indicator}" if source else indicator
                    grouped.setdefault(key, []).append(name)
            if grouped:
                return grouped

        if not self._auto_detect_families:
            return {}

        families: dict[str, list[str]] = {}
        pattern = re.compile(r"^(.+?)_(\d+)$")
        for name in feature_names:
            match = pattern.match(name)
            if match:
                families.setdefault(match.group(1), []).append(name)
            else:
                families.setdefault(name, []).append(name)
        return families

    def analyze_from_variants(
        self,
        features_df: pd.DataFrame,
        labels: pd.Series,
        feature_family: str,
        variant_params: dict[str, list],
        *,
        method: str = "spearman",
        direction: Optional[Mapping[str, int]] = None,
    ) -> dict | SkippedResult:
        method = self._check_method(method)
        variants = variant_params.get("variants", [])
        if len(variants) < self._min_family_size:
            return SkippedResult(
                module_name="parameter_sensitivity",
                reason=f"family {feature_family} too small",
                error_type="INSUFFICIENT_DATA",
            )

        present = [v for v in variants if v in features_df.columns]
        if len(present) < self._min_family_size:
            return SkippedResult(
                module_name="parameter_sensitivity",
                reason=f"family {feature_family} has insufficient valid variants",
                error_type="INSUFFICIENT_DATA",
            )

        icirs = self._compute_rolling_icir(features_df[present], labels, method, self._icir_window)
        rows = []
        for variant in present:
            rows.append(
                {
                    "variant": variant,
                    "param_value": self._extract_param_value(variant),
                    "ic_mean": self._compute_ic(features_df[variant], labels, method),
                    "icir": icirs[variant],
                }
            )

        df = pd.DataFrame(rows)
        if df["ic_mean"].dropna().empty:
            return SkippedResult(
                module_name="parameter_sensitivity",
                reason=f"family {feature_family} all nan ic",
                error_type="INSUFFICIENT_DATA",
            )

        best_idx = int(df["ic_mean"].abs().fillna(-np.inf).idxmax())
        ic_std = float(df["ic_mean"].std(ddof=0)) if len(df) > 1 else 0.0
        icir_std = float(df["icir"].std(ddof=0)) if len(df) > 1 else 0.0
        best_variant = df.loc[best_idx, "variant"]

        return {
            "variants": variants,
            "param_axis": "period",
            "sensitivity_table": df.to_dict(orient="records"),
            "stability_metrics": {
                "ic_std_across_params": ic_std,
                "icir_std_across_params": icir_std,
                "overfitting_risk": self.classify_overfitting_risk(ic_std, icir_std),
                "best_param": df.loc[best_idx, "param_value"],
                "best_param_direction": self._resolve_direction(
                    direction, best_variant, float(df.loc[best_idx, "ic_mean"])
                ),
            },
        }

    def classify_overfitting_risk(
        self,
        ic_std_across_params: float,
        icir_std_across_params: float,
    ) -> str:
        if (
            ic_std_across_params < self._ic_std_threshold_low
            and icir_std_across_params < 0.15
        ):
            return "low"
        if (
            ic_std_across_params < self._ic_std_threshold_high
            and icir_std_across_params < 0.3
        ):
            return "medium"
        return "high"

    def batch_analyze(
        self,
        features_df: pd.DataFrame,
        labels: pd.Series,
        metadata: Optional[dict] = None,
        min_family_size: int = 3,
        *,
        method: str = "spearman",
        direction: Optional[Mapping[str, int]] = None,
    ) -> dict:
        method = self._check_method(method)
        families = self.detect_feature_families(list(features_df.columns), metadata)
        threshold = max(int(min_family_size), self._min_family_size)

        result_families: dict[str, dict] = {}
        high_risk: list[str] = []
        robust: list[str] = []

        for family_name, variants in families.items():
            if len(variants) < threshold:
                continue
            family_result = self.analyze_from_variants(
                features_df,
                labels,
                feature_family=family_name,
                variant_params={"variants": variants},
                method=method,
                direction=direction,
            )
            if isinstance(family_result, SkippedResult):
                continue
            result_families[family_name] = family_result
            risk = family_result["stability_metrics"]["overfitting_risk"]
            if risk == "high":
                high_risk.append(family_name)
            if risk == "low":
                robust.append(family_name)

        summary = {
            "total_families": len(result_families),
            "high_risk_count": len(high_risk),
            "robust_count": len(robust),
        }

        logger.info(
            "Parameter sensitivity completed: %s families", len(result_families)
        )

        return {
            "families": result_families,
            "summary": summary,
            "high_risk_families": high_risk,
            "robust_families": robust,
        }

    @staticmethod
    def _check_method(method: str) -> str:
        if method not in _METHODS:
            raise ValueError(f"parameter_sensitivity method must be one of {_METHODS}, got {method!r}")
        return method

    @staticmethod
    def _resolve_direction(direction: Optional[Mapping[str, int]], variant: str, ic: float) -> int:
        if direction is not None and variant in direction:
            d = int(direction[variant])
            if d not in (-1, 0, 1):
                raise ValueError(f"direction must be -1, 0 or +1, got {direction[variant]!r}")
            return d
        if not np.isfinite(ic) or ic == 0:
            return 0
        return 1 if ic > 0 else -1

    @staticmethod
    def _aligned_arrays(feature: pd.Series, labels: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        """時間軸＝特徵索引；標籤依索引對齊（缺 ⇒ NaN），不剔除列。"""
        return feature.to_numpy(dtype=float), labels.reindex(feature.index).to_numpy(dtype=float)

    @staticmethod
    def _corr(x: np.ndarray, y: np.ndarray, method: str) -> float:
        if method == "kendall":
            value = kendalltau(x, y).statistic
        elif method == "pearson":
            value = np.corrcoef(x, y)[0, 1]
        else:
            value = spearmanr(x, y).correlation
        return float(value) if np.isfinite(value) else np.nan

    @staticmethod
    def _compute_ic(feature: pd.Series, labels: pd.Series, method: str = "spearman") -> float:
        x, y = ParameterSensitivityAnalyzer._aligned_arrays(feature, labels)
        mask = np.isfinite(x) & np.isfinite(y)
        x, y = x[mask], y[mask]
        if x.size < _MIN_ROWS:
            return np.nan
        if np.unique(x).size <= 1 or np.unique(y).size <= 1:
            return np.nan
        return ParameterSensitivityAnalyzer._corr(x, y, method)

    @staticmethod
    def _compute_rolling_icir(
        features: pd.DataFrame,
        labels: pd.Series,
        method: str,
        window: int,
    ) -> dict[str, float]:
        """逐特徵滾動 IC（時間軸＝標籤有限之列、步長 1）之 ICIR＝nanmean／nanstd(ddof=0)；無窗或 std ≤ 0 ⇒ NaN。"""
        y_all = labels.reindex(features.index).to_numpy(dtype=float)
        keep = np.isfinite(y_all)
        y = y_all[keep]
        x = features.to_numpy(dtype=float)[keep]
        out: dict[str, float] = {}
        if window <= 1 or y.size < window:
            return {name: np.nan for name in features.columns}
        if method == "spearman":
            series = rolling_window_rank_corr(x, y, window=int(window), stride=1)
        else:
            series = ParameterSensitivityAnalyzer._rolling_corr(x, y, int(window), method)
        for idx, name in enumerate(features.columns):
            values = series[:, idx]
            if not np.isfinite(values).any():
                out[name] = np.nan
                continue
            ic_mean = float(np.nanmean(values))
            ic_std = float(np.nanstd(values))
            out[name] = float(ic_mean / ic_std) if ic_std > 0 else np.nan
        return out

    @staticmethod
    def _rolling_corr(x: np.ndarray, y: np.ndarray, window: int, method: str) -> np.ndarray:
        """非 spearman 之逐窗相關（窗內特徵非有限或常數 ⇒ NaN；y 已全為有限值）。"""
        xw = sliding_window_view(x, window, axis=0)  # (n_out, n_features, window)
        yw = sliding_window_view(y, window)  # (n_out, window)
        n_out, n_features = xw.shape[0], xw.shape[1]
        out = np.full((n_out, n_features), np.nan)
        for oi in range(n_out):
            yv = yw[oi]
            if np.all(yv == yv[0]):
                continue
            for fi in range(n_features):
                xv = xw[oi, fi]
                if not np.isfinite(xv).all() or np.all(xv == xv[0]):
                    continue
                out[oi, fi] = ParameterSensitivityAnalyzer._corr(xv, yv, method)
        return out

    @staticmethod
    def _extract_param_value(variant_name: str) -> str | int:
        match = re.search(r"_(\d+)$", variant_name)
        if match:
            return int(match.group(1))
        return variant_name
