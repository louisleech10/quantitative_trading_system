"""Module 8: Long/short analyzer（LA-1 P1-2：PIT 分箱 + 固定 q）。"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.pit_stats import MIN_SAMPLES, pit_expanding_qcut_label
from momentum.core.logging import get_logger


logger = get_logger(__name__)

# recommendation enum 鎖（SPEC B2.1 / R3-M1）
RECOMMENDATION_ENUM = frozenset({"雙向交易", "只做多", "只做空", "不建議"})

# bin 分配 min_samples 寫死 §MS=100；禁 config override（F-B2-002）
_BIN_MIN_SAMPLES: int = MIN_SAMPLES


def _finite_mask(series: pd.Series) -> pd.Series:
    """對齊 finite gate（禁 notna：±inf 不進 metrics）。"""
    arr = np.asarray(series, dtype=float)
    return pd.Series(np.isfinite(arr), index=series.index, dtype=bool)


class LongShortAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._num_quantiles = int(cfg.get("num_quantiles", 5))
        self._long_quantiles = list(cfg.get("long_quantiles", [4, 5]))
        self._short_quantiles = list(cfg.get("short_quantiles", [1, 2]))
        # 模組進入門檻（樣本對數）；與 bin 分配 min_samples=100 兩層分離
        self._min_samples = int(cfg.get("min_samples", 30))

    def compute_pit_bins(
        self,
        feature: pd.Series,
        future_returns: Optional[pd.Series] = None,
        num_quantiles: Optional[int] = None,
    ) -> pd.Series:
        """產線 PIT 分箱（RB-3：feature 原時序；僅 feature 自身 NaN 排除）。

        ``future_returns`` 僅接受為 API 對稱／mutation 探測；**不得**參與分箱
        （禁 concat(feature, future_returns).dropna() 後再分箱）。
        """
        use_q = max(2, int(num_quantiles if num_quantiles is not None else self._num_quantiles))
        feat = pd.Series(feature, dtype=float)
        # 刻意不讀 future_returns；保留參數供測試探測 RB-3 回歸
        _ = future_returns
        return pit_expanding_qcut_label(
            feat,
            q=use_q,
            min_samples=_BIN_MIN_SAMPLES,
            require_full_q=True,
        )

    def compute_side_masks(
        self,
        feature: pd.Series,
        future_returns: Optional[pd.Series] = None,
        num_quantiles: Optional[int] = None,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """產線 (bins, long_mask, short_mask)；mask 對 NaN bin 自動為 False。"""
        use_q = max(2, int(num_quantiles if num_quantiles is not None else self._num_quantiles))
        bins = self.compute_pit_bins(feature, future_returns, use_q)
        long_q = [q for q in self._long_quantiles if 1 <= q <= use_q]
        short_q = [q for q in self._short_quantiles if 1 <= q <= use_q]
        if not long_q:
            long_q = [use_q]
        if not short_q:
            short_q = [1]
        long_mask = bins.isin([q - 1 for q in long_q]).fillna(False)
        short_mask = bins.isin([q - 1 for q in short_q]).fillna(False)
        return bins, long_mask, short_mask

    def analyze(
        self,
        feature: pd.Series,
        future_returns: pd.Series,
        num_quantiles: int = 5,
    ) -> dict | SkippedResult:
        feat = pd.Series(feature, dtype=float)
        ret = pd.Series(future_returns, dtype=float).reindex(feat.index)

        feat_fin = _finite_mask(feat)
        ret_fin = _finite_mask(ret)

        # 模組進入門檻：feature∩returns 有效（finite）對數
        n_pair = int((feat_fin & ret_fin).sum())
        if n_pair < self._min_samples:
            return SkippedResult(
                module_name="long_short_analysis",
                reason=f"insufficient samples: {n_pair} < {self._min_samples}",
                error_type="INSUFFICIENT_DATA",
            )

        use_quantiles = max(2, int(num_quantiles or self._num_quantiles))
        # RB-3：先在 feature 原時序 PIT 分箱（禁 feat.where(ret.*) 污染），再對齊 finite returns 只算 metrics
        bins, long_mask, short_mask = self.compute_side_masks(
            feat, ret, use_quantiles
        )

        n_labeled = int(bins.notna().sum())
        if n_labeled == 0:
            # 僅「結構上完全無法成 q」（finite feature < bin min_samples）→ skip
            # reduced-bin / require_full_q 全期 NaN label 但 n 足夠 → 走空側 + 不建議
            n_feat_finite = int(feat_fin.sum())
            if n_feat_finite < _BIN_MIN_SAMPLES:
                return SkippedResult(
                    module_name="long_short_analysis",
                    reason="cannot form quantiles",
                    error_type="NUMERICAL_ERROR",
                )

        # 分箱後 reindex 對齊 finite future_returns 只算 metrics（±inf 排除）
        long_sel = long_mask.fillna(False) & ret_fin
        short_sel = short_mask.fillna(False) & ret_fin

        long_returns = ret.loc[long_sel].astype(float)
        short_raw_returns = ret.loc[short_sel].astype(float)
        short_returns = -short_raw_returns

        long_analysis = self._compute_side_metrics(
            feat.loc[long_sel],
            long_returns,
            side="long",
        )
        short_analysis = self._compute_side_metrics(
            feat.loc[short_sel],
            short_returns,
            side="short",
        )

        asymmetry = self._classify_asymmetry(
            long_analysis.get("mean_return", 0.0),
            short_analysis.get("mean_return", 0.0),
        )

        long_ic = float(long_analysis.get("ic", np.nan))
        short_ic = float(short_analysis.get("ic", np.nan))
        # 空側 / IC 全 NaN → 不建議（_recommendation 本體不動；外層契約）
        long_empty = int(long_analysis.get("samples", 0) or 0) == 0
        short_empty = int(short_analysis.get("samples", 0) or 0) == 0
        if long_empty or short_empty:
            recommendation = "不建議"
        elif (not np.isfinite(long_ic)) and (not np.isfinite(short_ic)):
            recommendation = "不建議"
        else:
            recommendation = self._recommendation(long_ic=long_ic, short_ic=short_ic)

        assert recommendation in RECOMMENDATION_ENUM

        return {
            "long_analysis": long_analysis,
            "short_analysis": short_analysis,
            "asymmetry": asymmetry,
            "recommendation": recommendation,
            # schema 鎖：固定 q == requested（禁暗示全域實際 bin 數）
            "num_quantiles_used": use_quantiles,
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
        # finite-only（與 analyze 對齊；dropna 不擋 ±inf）
        fin = np.isfinite(x.to_numpy(dtype=float, copy=False)) & np.isfinite(
            y.to_numpy(dtype=float, copy=False)
        )
        if not np.any(fin):
            return {
                "mean_return": np.nan,
                "ic": np.nan,
                "hit_rate": np.nan,
                "sharpe": np.nan,
                "side": side,
                "samples": 0,
            }

        x_f = x.to_numpy(dtype=float, copy=False)[fin]
        y_f = y.to_numpy(dtype=float, copy=False)[fin]
        n = int(len(y_f))
        if n < 2 or len(np.unique(x_f)) <= 1 or len(np.unique(y_f)) <= 1:
            ic = np.nan
        else:
            corr = spearmanr(x_f, y_f).correlation
            ic = float(corr) if np.isfinite(corr) else np.nan

        std = float(np.std(y_f, ddof=1)) if n > 1 else np.nan
        mean_y = float(np.mean(y_f))
        sharpe = float(mean_y / std) if np.isfinite(std) and std > 0 else np.nan

        return {
            "mean_return": mean_y,
            "ic": ic,
            "hit_rate": float(np.mean(y_f > 0)),
            "sharpe": sharpe,
            "side": side,
            "samples": n,
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
