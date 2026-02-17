"""Module 4: Parameter sensitivity analyzer."""

from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.core.logging import get_logger


logger = get_logger(__name__)


class ParameterSensitivityAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._min_family_size = int(cfg.get("min_family_size", 3))
        self._ic_std_threshold_low = float(cfg.get("ic_std_threshold_low", 0.02))
        self._ic_std_threshold_high = float(cfg.get("ic_std_threshold_high", 0.05))
        self._auto_detect_families = bool(cfg.get("auto_detect_families", True))

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
    ) -> dict | SkippedResult:
        variants = variant_params.get("variants", [])
        if len(variants) < self._min_family_size:
            return SkippedResult(
                module_name="parameter_sensitivity",
                reason=f"family {feature_family} too small",
                error_type="INSUFFICIENT_DATA",
            )

        rows = []
        for variant in variants:
            if variant not in features_df.columns:
                continue
            ic = self._compute_ic(features_df[variant], labels)
            icir = self._compute_icir_proxy(features_df[variant], labels)
            rows.append(
                {
                    "variant": variant,
                    "param_value": self._extract_param_value(variant),
                    "ic_mean": ic,
                    "icir": icir,
                }
            )

        if len(rows) < self._min_family_size:
            return SkippedResult(
                module_name="parameter_sensitivity",
                reason=f"family {feature_family} has insufficient valid variants",
                error_type="INSUFFICIENT_DATA",
            )

        df = pd.DataFrame(rows)
        if df["ic_mean"].dropna().empty:
            return SkippedResult(
                module_name="parameter_sensitivity",
                reason=f"family {feature_family} all nan ic",
                error_type="INSUFFICIENT_DATA",
            )

        best_idx = int(df["ic_mean"].fillna(-np.inf).idxmax())
        ic_std = float(df["ic_mean"].std(ddof=0)) if len(df) > 1 else 0.0
        icir_std = float(df["icir"].std(ddof=0)) if len(df) > 1 else 0.0

        return {
            "variants": variants,
            "param_axis": "period",
            "sensitivity_table": df.to_dict(orient="records"),
            "stability_metrics": {
                "ic_std_across_params": ic_std,
                "icir_std_across_params": icir_std,
                "overfitting_risk": self.classify_overfitting_risk(ic_std, icir_std),
                "best_param": df.loc[best_idx, "param_value"],
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
    ) -> dict:
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
    def _compute_ic(feature: pd.Series, labels: pd.Series) -> float:
        data = pd.concat([feature.rename("x"), labels.rename("y")], axis=1).dropna()
        if len(data) < 5:
            return np.nan
        if data["x"].nunique(dropna=True) <= 1 or data["y"].nunique(dropna=True) <= 1:
            return np.nan
        value = spearmanr(data["x"].values, data["y"].values).correlation
        return float(value) if np.isfinite(value) else np.nan

    @staticmethod
    def _compute_icir_proxy(feature: pd.Series, labels: pd.Series) -> float:
        data = pd.concat([feature.rename("x"), labels.rename("y")], axis=1).dropna()
        if len(data) < 5:
            return np.nan
        product = data["x"].astype(float) * data["y"].astype(float)
        std = float(product.std(ddof=1)) if len(product) > 1 else np.nan
        if not np.isfinite(std) or std == 0:
            return np.nan
        return float(product.mean() / std)

    @staticmethod
    def _extract_param_value(variant_name: str) -> str | int:
        match = re.search(r"_(\d+)$", variant_name)
        if match:
            return int(match.group(1))
        return variant_name
