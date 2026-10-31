"""Module 9: Feature quality diagnostics."""

from __future__ import annotations

import warnings
from typing import Optional

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox, breaks_cusumolsresid
from statsmodels.tsa.stattools import adfuller

from momentum.core.logging import get_logger


logger = get_logger(__name__)

#: CUSUM 漂移判定之顯著水準（Ploberger–Krämer OLS-CUSUM；ICPERF Task 0.4 ㉒ QN-3）
_CUSUM_SIGNIFICANCE = 0.05
#: PSI 近期窗之預設觀測數（同 `ic_config_schema.FeatureQualityDiagnosticsConfig.drift_window`；ICPERF Task 0.4 ㉖）
_DEFAULT_DRIFT_WINDOW = 60
#: PSI 參照段（近期窗之前）之最少有限觀測數（同 `_psi` 每側下限）
_PSI_MIN_REFERENCE = 5
#: PSI 觀測不足之原因碼（有限觀測 < drift_window＋_PSI_MIN_REFERENCE）
PSI_INSUFFICIENT_REASON = "insufficient_observations_for_drift_window"


class FeatureQualityDiagnostics:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._adf_significance = float(cfg.get("adf_significance", 0.05))
        self._ljungbox_lags = int(cfg.get("ljungbox_lags", 10))
        self._ljungbox_significance = float(cfg.get("ljungbox_significance", 0.05))
        self._coverage_threshold = float(cfg.get("coverage_threshold", 0.8))
        self._drift_threshold = float(cfg.get("drift_threshold", 0.25))
        self._redundancy_threshold = float(cfg.get("redundancy_threshold", 0.85))
        self._adf_min_samples = int(cfg.get("adf_min_samples", 20))
        self._drift_window = int(cfg.get("drift_window", _DEFAULT_DRIFT_WINDOW))

    def run_batch_adf_test(self, features_df: pd.DataFrame) -> dict[str, dict]:
        """逐欄 ADF。未實際檢定（全缺／樣本不足／常數／ADF 例外）或 p 非有限 ⇒ is_stationary=None（未知，
        不得當非平穩；ICPERF Task 0.4 ㉒ QN-2）。不設牆鐘逾時（QN-5，使用者 2026-10-27「全專案禁時間上限停運算」；
        卡死一律交共用監看）。"""
        results: dict[str, dict] = {}
        for feature_name in features_df.columns:
            series = pd.Series(features_df[feature_name], dtype=float)
            clean = series.dropna()

            if clean.empty:
                results[feature_name] = {
                    "skipped": True,
                    "reason": "all_nan",
                    "adf_statistic": np.nan,
                    "p_value": np.nan,
                    "is_stationary": None,
                }
                continue
            if len(clean) < self._adf_min_samples:
                results[feature_name] = {
                    "skipped": True,
                    "reason": "insufficient_samples",
                    "adf_statistic": np.nan,
                    "p_value": np.nan,
                    "is_stationary": None,
                }
                continue
            if clean.nunique(dropna=True) <= 1:
                results[feature_name] = {
                    "skipped": True,
                    "reason": "constant_feature",
                    "adf_statistic": np.nan,
                    "p_value": np.nan,
                    "is_stationary": None,
                }
                continue

            winsorized = self._winsorize(clean)
            try:
                adf_stat, p_value, *_ = adfuller(winsorized.values.astype(float))
                p_value = float(p_value)
                results[feature_name] = {
                    "adf_statistic": float(adf_stat),
                    "p_value": p_value,
                    "is_stationary": bool(p_value < self._adf_significance) if np.isfinite(p_value) else None,
                    "skipped": False,
                }
            except Exception as exc:
                logger.warning("ADF failed for %s: %s", feature_name, exc)
                results[feature_name] = {
                    "skipped": True,
                    "reason": "adf_error",
                    "error": str(exc),
                    "adf_statistic": np.nan,
                    "p_value": np.nan,
                    "is_stationary": None,
                }

        return results

    def run_batch_autocorrelation_test(self, features_df: pd.DataFrame) -> dict[str, dict]:
        results: dict[str, dict] = {}
        for feature_name in features_df.columns:
            series = pd.Series(features_df[feature_name], dtype=float).dropna()
            if len(series) < max(10, self._ljungbox_lags + 5):
                results[feature_name] = {
                    "skipped": True,
                    "reason": "insufficient_samples",
                    "ljungbox_stat": np.nan,
                    "p_value": np.nan,
                    "significant_autocorrelation": False,
                    "effective_sample_ratio": np.nan,
                }
                continue

            try:
                lb = acorr_ljungbox(series.values.astype(float), lags=[self._ljungbox_lags], return_df=True)
                stat = float(lb["lb_stat"].iloc[0])
                p_value = float(lb["lb_pvalue"].iloc[0])
                effective_sample_ratio = self._effective_sample_ratio(series)
                results[feature_name] = {
                    "ljungbox_stat": stat,
                    "p_value": p_value,
                    "significant_autocorrelation": bool(p_value < self._ljungbox_significance),
                    "effective_sample_ratio": float(effective_sample_ratio),
                    "skipped": False,
                }
            except Exception as exc:
                logger.warning("Ljung-Box failed for %s: %s", feature_name, exc)
                results[feature_name] = {
                    "skipped": True,
                    "reason": "ljungbox_error",
                    "error": str(exc),
                    "ljungbox_stat": np.nan,
                    "p_value": np.nan,
                    "significant_autocorrelation": False,
                    "effective_sample_ratio": np.nan,
                }
        return results

    def detect_concept_drift(
        self,
        rolling_ic_series: pd.Series,
        feature_name: str,
    ) -> dict:
        series = pd.Series(rolling_ic_series, dtype=float).dropna()
        if len(series) < 20:
            return {
                "feature_name": feature_name,
                "skipped": True,
                "reason": "insufficient_rolling_ic",
                "cusum_breakpoint": None,
                "psi_score": np.nan,
                "drifted": False,
            }

        centered = series - float(series.mean())
        cumulative = centered.cumsum()
        breakpoint_idx = cumulative.abs().idxmax() if not cumulative.empty else None
        # ICPERF Task 0.4 ㉒ QN-3：Ploberger–Krämer OLS-CUSUM（統計量 max|S_k|／(σ√n)，Brownian bridge 臨界值）；
        # 舊法 max|S_k| > 5σ 未除 √n ⇒ 長序列恆判漂移。σ 非有限或為 0 ⇒ p 非有限 ⇒ 不判漂移。
        with warnings.catch_warnings(), np.errstate(divide="ignore", invalid="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            _sup_b, cusum_p, _crit = breaks_cusumolsresid(centered.to_numpy(dtype=float), ddof=0)
        drift_by_cusum = bool(np.isfinite(cusum_p) and cusum_p < _CUSUM_SIGNIFICANCE)

        # ICPERF Task 0.4 ㉖ QN-6：PSI 近期窗＝最近 drift_window 個有限觀測，參照＝其之前全部有限觀測（舊法前後兩半，
        # 設定 drift_window 未被讀）；參照段 < _PSI_MIN_REFERENCE ⇒ PSI NaN 並記原因。CUSUM 不變。
        n_reference = len(series) - self._drift_window
        if n_reference < _PSI_MIN_REFERENCE or self._drift_window < _PSI_MIN_REFERENCE:
            psi_score = np.nan
            psi_reason: Optional[str] = PSI_INSUFFICIENT_REASON
        else:
            psi_score = self._psi(series.iloc[:n_reference], series.iloc[n_reference:])
            psi_reason = None
        drifted = bool(drift_by_cusum or (np.isfinite(psi_score) and psi_score > self._drift_threshold))

        return {
            "feature_name": feature_name,
            "cusum_breakpoint": str(breakpoint_idx) if breakpoint_idx is not None else None,
            "psi_score": float(psi_score) if np.isfinite(psi_score) else np.nan,
            "psi_reason": psi_reason,
            "drifted": drifted,
            "skipped": False,
        }

    def compute_coverage_stats(self, features_df: pd.DataFrame) -> dict[str, dict]:
        total = len(features_df)
        results: dict[str, dict] = {}
        for feature_name in features_df.columns:
            # ICPERF Task 0.4 ㊴：有效值＝有限值（NaN、±inf 皆非有效；同 coverage_analyzer 與 IC 有限值遮罩）
            non_nan = int(np.isfinite(pd.to_numeric(features_df[feature_name], errors="coerce")
                                      .to_numpy(dtype=np.float64)).sum())
            nan_count = int(total - non_nan)
            coverage = float(non_nan / total) if total > 0 else 0.0
            results[feature_name] = {
                "coverage": coverage,
                "nan_count": nan_count,
                "total": int(total),
            }
        return results

    def redundancy_pre_scan(
        self,
        features_df: pd.DataFrame,
        method: str = "spearman",
    ) -> dict:
        if features_df.shape[1] < 2:
            return {
                "high_correlation_pairs": [],
                "threshold": self._redundancy_threshold,
                "method": method,
                "skipped": True,
            }

        corr = features_df.corr(method=method).abs()
        pairs: list[list[object]] = []
        columns = list(corr.columns)
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                value = float(corr.iloc[i, j])
                if np.isfinite(value) and value >= self._redundancy_threshold:
                    pairs.append([columns[i], columns[j], value])

        return {
            "high_correlation_pairs": pairs,
            "threshold": self._redundancy_threshold,
            "method": method,
            "skipped": False,
        }

    def run_full_diagnostics(
        self,
        features_df: pd.DataFrame,
        rolling_ic_dict: Optional[dict[str, pd.Series]] = None,
    ) -> dict:
        adf_results = self.run_batch_adf_test(features_df)
        autocorrelation_results = self.run_batch_autocorrelation_test(features_df)
        coverage_stats = self.compute_coverage_stats(features_df)
        redundancy_scan = self.redundancy_pre_scan(features_df, method="spearman")

        drift_results: dict[str, dict] = {}
        if rolling_ic_dict:
            for feature_name in features_df.columns:
                if feature_name in rolling_ic_dict:
                    drift_results[feature_name] = self.detect_concept_drift(
                        rolling_ic_dict[feature_name],
                        feature_name,
                    )
                else:
                    drift_results[feature_name] = {
                        "feature_name": feature_name,
                        "skipped": True,
                        "reason": "rolling_ic_missing",
                        "cusum_breakpoint": None,
                        "psi_score": np.nan,
                        "drifted": False,
                    }
        else:
            for feature_name in features_df.columns:
                drift_results[feature_name] = {
                    "feature_name": feature_name,
                    "skipped": True,
                    "reason": "rolling_ic_unavailable",
                    "cusum_breakpoint": None,
                    "psi_score": np.nan,
                    "drifted": False,
                }

        quality_flags = {
            "non_stationary": [],
            "high_autocorrelation": [],
            "low_coverage": [],
            "drifted": [],
        }
        for feature_name in features_df.columns:
            # QN-2：只有實際檢定且判非平穩（is_stationary is False）者入旗標；None＝未檢定、不入
            adf_flag = adf_results[feature_name].get("is_stationary") is False
            acf_flag = bool(autocorrelation_results[feature_name].get("significant_autocorrelation", False))
            coverage = float(coverage_stats[feature_name].get("coverage", 0.0))
            drifted = bool(drift_results[feature_name].get("drifted", False))

            if adf_flag:
                quality_flags["non_stationary"].append(feature_name)
            if acf_flag:
                quality_flags["high_autocorrelation"].append(feature_name)
            if coverage < self._coverage_threshold:
                quality_flags["low_coverage"].append(feature_name)
            if drifted:
                quality_flags["drifted"].append(feature_name)

        stationary_count = sum(1 for r in adf_results.values() if r.get("is_stationary") is True)
        total_features = int(len(features_df.columns))
        mean_coverage = float(np.mean([v["coverage"] for v in coverage_stats.values()])) if total_features > 0 else 0.0

        low_quality_set = (
            set(quality_flags["non_stationary"])
            | set(quality_flags["high_autocorrelation"])
            | set(quality_flags["low_coverage"])
            | set(quality_flags["drifted"])
        )

        return {
            "adf_results": adf_results,
            "autocorrelation_results": autocorrelation_results,
            "drift_results": drift_results,
            "coverage_stats": coverage_stats,
            "redundancy_scan": redundancy_scan,
            "quality_flags": quality_flags,
            "summary": {
                "total_features": total_features,
                "stationary_rate": float(stationary_count / total_features) if total_features > 0 else 0.0,
                "mean_coverage": mean_coverage,
                "low_quality_count": int(len(low_quality_set)),
            },
        }

    @staticmethod
    def _winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
        low = float(series.quantile(lower))
        high = float(series.quantile(upper))
        return series.clip(lower=low, upper=high)

    @staticmethod
    def _effective_sample_ratio(series: pd.Series) -> float:
        values = series.values.astype(float)
        if len(values) < 3:
            return 1.0
        with np.errstate(divide="ignore", invalid="ignore"):
            acf1 = np.corrcoef(values[:-1], values[1:])[0, 1]
        if not np.isfinite(acf1):
            # ICPERF Task 0.4 ㉒ QN-4：lag-1 自相關無定義（常數序列）⇒ 有效樣本比無定義，不得寫 1.0
            return float("nan")
        if (1.0 + acf1) <= 0.0:
            # ρ₁ → −1 之極限 (1−ρ)/(1+ρ) → +∞，截上限後＝1（舊碼於此回 0.0，與 ρ₁ 略大於 −1 時之 1.0 不連續）
            return 1.0
        ratio = (1.0 - acf1) / (1.0 + acf1)
        return float(max(0.0, min(1.0, ratio)))

    @staticmethod
    def _psi(front: pd.Series, back: pd.Series, bins: int = 10) -> float:
        if len(front.dropna()) < 5 or len(back.dropna()) < 5:
            return np.nan
        values = pd.concat([front.rename("front"), back.rename("back")], axis=1)
        all_values = values.stack().astype(float)
        edges = np.quantile(all_values, np.linspace(0, 1, bins + 1))
        edges = np.unique(edges)
        if len(edges) < 3:
            return 0.0

        f_counts, _ = np.histogram(front.values.astype(float), bins=edges)
        b_counts, _ = np.histogram(back.values.astype(float), bins=edges)
        f_ratio = np.clip(f_counts / max(1, np.sum(f_counts)), 1e-8, 1.0)
        b_ratio = np.clip(b_counts / max(1, np.sum(b_counts)), 1e-8, 1.0)
        psi = np.sum((f_ratio - b_ratio) * np.log(f_ratio / b_ratio))
        return float(psi)
