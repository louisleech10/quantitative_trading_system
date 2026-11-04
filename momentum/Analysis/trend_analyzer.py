"""Module 3: Trend analyzer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.stats import linregress

from momentum.Analysis import trend_inference as ti
from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.core.logging import get_logger


logger = get_logger(__name__)

#: ICPERF Task 0.4 ㉕：趨勢之四維（設定 `dimensions` 之值；輸出鍵＝`<dim>_trend`），依此序計算
TREND_DIMENSIONS: tuple[str, ...] = ("ic", "centrality", "factor_return", "ls_spread")
#: ㉕ 未出之維之原因（`dimension_status` 封閉值集）
DIMENSION_SOURCE_MODULE_OFF = "source_module_off"
DIMENSION_SOURCE_SKIPPED = "source_skipped"
DIMENSION_INSUFFICIENT_DATA = "insufficient_data"
DIMENSION_STATUS_VALUES: frozenset[str] = frozenset(
    {DIMENSION_SOURCE_MODULE_OFF, DIMENSION_SOURCE_SKIPPED, DIMENSION_INSUFFICIENT_DATA}
)


@dataclass(frozen=True)
class TrendDimensionInput:
    """ICPERF Task 0.4 ㉕：趨勢某一維之來源（同請求之來源模組已算）。

    - `series`：特徵名 → 逐時點序列（位置即時間軸；NaN 為缺值、保留位置）；特徵不在其中 ⇒ 該特徵此維 `source_skipped`
    - `overlap_window`：序列每值涵蓋之觀測數（HAC 頻寬下限＝其 −1）；None ⇒ 無重疊、只用自動頻寬
    - `status`：來源整體不可用之原因（`source_module_off`／`source_skipped`）；非 None 時忽略 `series`
    """

    series: Mapping[str, pd.Series] = field(default_factory=dict)
    overlap_window: Optional[int] = None
    status: Optional[str] = None
    #: ICPERF Task 0.4 ㊺ B(1)：各值之來源支撐〔起, 迄〕原列位置（與 `series` 逐位置對齊、同維各特徵共用）；
    #: None ⇒ 由 `overlap_window` 推〔位置, 位置＋overlap_window−1〕（未給 ⇒ 每值只涵蓋自身）
    support: Optional[tuple[np.ndarray, np.ndarray]] = None
    #: 序列第 j 值位於原列 j·position_scale（如因子報酬每 h 根取一之格點）；support 為 None 時用以推原列位置支撐
    position_scale: int = 1
    #: 非有限值＝非持倉點、不入設計（ls_spread，SPEC ㊺ B(7)）⇒ 不重疊選取只在有限值上進行
    select_finite_only: bool = False


class TrendAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._min_samples = int(cfg.get("min_samples", 20))
        self._significance = float(cfg.get("significance_level", 0.05))
        self._r2_threshold = float(cfg.get("r_squared_threshold", 0.1))

    def analyze_trend(
        self,
        time_series: pd.Series,
        series_name: str = "",
        *,
        overlap_window: Optional[int] = None,
        support: Optional[tuple[np.ndarray, np.ndarray]] = None,
        select_finite_only: bool = False,
    ) -> dict:
        """線性趨勢：描述用 OLS（縮尾、全部有效點）＋推論用不重疊子序列之 Bartlett fixed-b 精確 p（ICPERF ㊺ B）。

        `select_finite_only`（ls_spread 維，SPEC ㊺ B(7)）：非有限值＝非持倉點、不入設計 ⇒ 貪婪選取只在有限值上進行
        （非持倉點不佔支撐；r106 CODEX-P1-03）；其餘維為 False（同維共用位置軸、先選再剔非有限）。

        - 描述（⑱ CT-1、CT-2，不變）：x＝原始位置（去 NaN 不重編），1%／99% 縮尾後 OLS 之 `slope`／`r_squared`／
          `tail_estimate`（末一有效位置之擬合值）。
        - 推論（SPEC v5.78 ㊺ B(2)–(5)）：`support`＝各值來源支撐〔起, 迄〕原列位置（與 `time_series` 逐位置對齊）；
          未給 ⇒〔位置, 位置＋overlap_window−1〕（未給 overlap_window ⇒ 每值只涵蓋自身）。自第一個值起貪婪選取
          支撐不交疊之值，於選取點之有限值（x＝支撐迄點、y＝未縮尾原值）以 `trend_inference.infer_trend` 檢定。
        - 分類：`ok` 且 p ≤ α 且描述 r² ≥ 門檻 ⇒ 依推論斜率符號 up／down，否則 flat；`constant_series` ⇒ flat；
          其餘狀態 ⇒ `indeterminate`；有效點 < `min_samples`（使用者設定）⇒ `below_min_samples`、`indeterminate`。
        """
        raw = pd.Series(time_series, dtype=float).to_numpy(dtype=float)
        n_all = raw.size
        if support is None:
            span = max(1, int(overlap_window)) if overlap_window else 1
            pos_all = np.arange(n_all, dtype=np.int64)
            sup_start, sup_end = pos_all, pos_all + span - 1
        else:
            sup_start = np.asarray(support[0], dtype=np.int64)
            sup_end = np.asarray(support[1], dtype=np.int64)
            if sup_start.size != n_all or sup_end.size != n_all:
                raise ValueError("support must align with time_series")
        # 描述用沿用現行：只去 NaN（±inf 保留 ⇒ 描述斜率非有限 ⇒ indeterminate）；推論另於選取點以有限值判定
        valid = ~np.isnan(raw)
        positions = np.flatnonzero(valid).astype(float)
        series = pd.Series(raw[valid])

        def _result(desc: dict, inference: Optional[ti.TrendInference], status: str, trend: str,
                    sel: Optional[np.ndarray]) -> dict:
            gaps = int(np.sum(~np.isfinite(raw[sel]))) if sel is not None and sel.size else 0
            # SPEC ㊺ B 資料不足警示：只於推論 ok 時判定（同 A 只於 EWC ok 時判定）
            warning = (ti.trend_data_warning(sup_end[sel].astype(float), raw[sel], self._significance)
                       if status == ti.STATUS_OK and sel is not None
                       else {"data_warning": None, "data_warning_detail": None})
            out = {
                **desc,
                "p_value": inference.p_value if inference is not None else None,
                "trend": trend,
                "interpretation": self._interpret_trend(trend),
                "inference_slope": inference.slope if inference is not None else None,
                "inference_se": inference.se if inference is not None else None,
                "inference_method": ti.INFERENCE_METHOD,
                "inference_status": status,
                "p_abs_error": inference.p_abs_error if inference is not None else None,
                "subsample_points": inference.points if inference is not None else 0,
                "subsample_start_pos": int(sup_start[sel[0]]) if sel is not None and sel.size else None,
                "omitted_tail_rows": int(n_all - 1 - sel[-1]) if sel is not None and sel.size else n_all,
                "interior_gap_count": gaps,
                **warning,
            }
            return out

        empty_desc = {"slope": None, "r_squared": None, "tail_estimate": None}
        if len(series) < self._min_samples:
            return _result(empty_desc, None, ti.STATUS_BELOW_MIN_SAMPLES, "indeterminate", None)

        if select_finite_only:
            fin_idx = np.flatnonzero(np.isfinite(raw))
            sel = fin_idx[ti.select_nonoverlapping(sup_start[fin_idx], sup_end[fin_idx])]
        else:
            sel = ti.select_nonoverlapping(sup_start, sup_end)
        if series.nunique(dropna=True) <= 1:
            value = float(series.iloc[0])
            desc = {"slope": 0.0, "r_squared": 0.0, "tail_estimate": value}
            inf = ti.infer_trend(sup_end[sel].astype(float), raw[sel], self._significance)
            # 描述全同不代表推論可判定：選取點不足／退化 ⇒ indeterminate（SPEC ㊺ B(4)；r106 CODEX-P1-01）
            trend = "flat" if inf.status in (ti.STATUS_CONSTANT_SERIES, ti.STATUS_OK) else "indeterminate"
            return _result(desc, inf, inf.status, trend, sel)

        winsorized = self._winsorize(series)
        with np.errstate(invalid="ignore", divide="ignore"):
            reg = linregress(positions, winsorized.to_numpy(dtype=float))
        slope = float(reg.slope)
        r_squared = float(reg.rvalue ** 2) if np.isfinite(reg.rvalue) else 0.0
        desc = {
            "slope": slope,
            "r_squared": r_squared,
            "tail_estimate": float(reg.intercept + reg.slope * positions[-1]),
        }

        inf = ti.infer_trend(sup_end[sel].astype(float), raw[sel], self._significance)
        if not np.isfinite(slope):
            # 描述用斜率非有限（如含 ±inf）：沿用現行 ⇒ indeterminate
            trend = "indeterminate"
        elif inf.status == ti.STATUS_OK:
            if inf.significant and np.isfinite(r_squared) and r_squared >= self._r2_threshold:
                trend = "up" if inf.slope > 0 else "down" if inf.slope < 0 else "flat"
            else:
                trend = "flat"
        elif inf.status == ti.STATUS_CONSTANT_SERIES:
            trend = "flat"
        else:
            trend = "indeterminate"
        return _result(desc, inf, inf.status, trend, sel)

    def analyze_multi_dimension(
        self,
        feature_name: str,
        rolling_ic: Optional[pd.Series] = None,
        rolling_centrality: Optional[pd.Series] = None,
        factor_return_cumulative: Optional[pd.Series] = None,
        ls_spread_series: Optional[pd.Series] = None,
        ic_decay_half_life: Optional[float] = None,
        *,
        overlap_window: Optional[int] = None,
        centrality_overlap_window: Optional[int] = None,
        factor_return_overlap_window: Optional[int] = None,
        ls_spread_overlap_window: Optional[int] = None,
    ) -> dict:
        """`overlap_window` 套 IC 維（滾動 IC 之窗長／步長）；ICPERF Task 0.4 ㉕：其餘各維之 HAC 頻寬下限各由
        `<dim>_overlap_window` 給（該序列每值涵蓋之觀測數；None ⇒ 無重疊、只用自動頻寬）。"""
        dimensions: dict[str, dict] = {}

        ic_result = (
            self._ensure_trend_dict(self.analyze_trend(rolling_ic, "rolling_ic", overlap_window=overlap_window))
            if rolling_ic is not None
            else None
        )
        centrality_result = (
            self._ensure_trend_dict(self.analyze_trend(rolling_centrality, "rolling_centrality",
                                                       overlap_window=centrality_overlap_window))
            if rolling_centrality is not None
            else None
        )
        factor_return_result = (
            self._ensure_trend_dict(self.analyze_trend(factor_return_cumulative, "factor_return",
                                                       overlap_window=factor_return_overlap_window))
            if factor_return_cumulative is not None
            else None
        )
        ls_spread_result = (
            # ㊺ B(7)：非持倉點不入設計（同 batch_analyze 之 ls_spread；r107 CODEX-P1-01）
            self._ensure_trend_dict(self.analyze_trend(ls_spread_series, "ls_spread",
                                                       overlap_window=ls_spread_overlap_window,
                                                       select_finite_only=True))
            if ls_spread_series is not None
            else None
        )

        if ic_result:
            dimensions["ic_trend"] = ic_result
        if centrality_result:
            dimensions["centrality_trend"] = centrality_result
        if factor_return_result:
            dimensions["factor_return_trend"] = factor_return_result
        if ls_spread_result:
            dimensions["ls_spread_trend"] = ls_spread_result

        combined_signal = self._combine_signal(ic_result, centrality_result, ic_decay_half_life)

        return {
            feature_name: {
                **dimensions,
                "combined_signal": combined_signal,
            }
        }

    def batch_analyze(
        self,
        rolling_ic_matrix: pd.DataFrame,
        rolling_centrality_matrix: Optional[pd.DataFrame] = None,
        top_n: int = 30,
        *,
        overlap_window: Optional[int] = None,
        dimensions: Optional[Sequence[str]] = None,
        dimension_inputs: Optional[Mapping[str, TrendDimensionInput]] = None,
        ic_support: Optional[tuple[np.ndarray, np.ndarray]] = None,
    ) -> dict[str, dict]:
        """逐特徵多維趨勢（特徵集合＝滾動 IC 矩陣前 top_n 欄）。

        - `overlap_window`：滾動 IC 每值涵蓋之觀測數（窗長 w、步長 s ⇒ ceil(w／s)），供 IC 趨勢之 HAC 落後期數。
        - ICPERF Task 0.4 ㉕ `dimensions`：依序計算之維（`TREND_DIMENSIONS` 之子集；其他值忽略）；None ⇒ ic，另給
          `rolling_centrality_matrix` 時加 centrality（舊呼叫相容；該矩陣之重疊窗未知 ⇒ 自動頻寬）。
        - `dimension_inputs`：ic 以外各維之來源（`TrendDimensionInput`）；缺 ⇒ `source_module_off`。
        - 每特徵輸出 `<dim>_trend`（可算者）、`combined_signal`（現行規則表，用實際可得之 ic／centrality 維）與
          `dimension_status`（未出之維 → 封閉值集原因：來源狀態、該特徵不在來源序列 ⇒ `source_skipped`、
          有效觀測 < min_samples ⇒ `insufficient_data`）。
        """
        results: dict[str, dict] = {}
        selected = list(rolling_ic_matrix.columns)[: max(1, int(top_n))]
        inputs: dict[str, TrendDimensionInput] = dict(dimension_inputs or {})
        if dimensions is None:
            dims = ["ic"] + (["centrality"] if rolling_centrality_matrix is not None else [])
        else:
            dims = [str(d) for d in dimensions]
        if rolling_centrality_matrix is not None and "centrality" not in inputs:
            inputs["centrality"] = TrendDimensionInput(
                series={str(c): rolling_centrality_matrix[c] for c in rolling_centrality_matrix.columns}
            )
        active = [d for d in TREND_DIMENSIONS if d in dims]

        for feature_name in selected:
            entry: dict[str, dict] = {}
            status: dict[str, str] = {}
            for dim in active:
                if dim == "ic":
                    series: Optional[pd.Series] = rolling_ic_matrix[feature_name]
                    lag_window = overlap_window
                    dim_support = ic_support
                    finite_only = False
                else:
                    source = inputs.get(dim)
                    if source is None:
                        status[dim] = DIMENSION_SOURCE_MODULE_OFF
                        continue
                    if source.status is not None:
                        status[dim] = source.status
                        continue
                    series = source.series.get(str(feature_name))
                    if series is None:
                        status[dim] = DIMENSION_SOURCE_SKIPPED
                        continue
                    lag_window = source.overlap_window
                    dim_support = source.support
                    if dim_support is None and source.position_scale > 1:
                        # 每值位於原列 j·scale（序列為每 scale 根取一之格點）⇒ 支撐〔j·scale, j·scale＋span−1〕
                        pos = np.arange(len(series), dtype=np.int64) * int(source.position_scale)
                        span = max(1, int(lag_window or 1))
                        dim_support = (pos, pos + span - 1)
                    finite_only = bool(source.select_finite_only)
                result = self.analyze_trend(series, dim, overlap_window=lag_window, support=dim_support,
                                            select_finite_only=finite_only)
                if result.get("inference_status") == ti.STATUS_BELOW_MIN_SAMPLES:
                    # 有效觀測 < min_samples：該維不入輸出、記 `dimension_status`；combined_signal 視為缺維 ⇒「資訊不足」
                    status[dim] = DIMENSION_INSUFFICIENT_DATA
                    continue
                entry[f"{dim}_trend"] = result
            results[feature_name] = {
                **entry,
                "combined_signal": self._combine_signal(
                    entry.get("ic_trend"), entry.get("centrality_trend"), None
                ),
                "dimension_status": status,
            }

        logger.info("Trend analysis completed: %s features", len(selected))
        return results

    @staticmethod
    def _winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
        low = float(series.quantile(lower))
        high = float(series.quantile(upper))
        return series.clip(lower=low, upper=high)

    @staticmethod
    def _interpret_trend(trend: str) -> str:
        if trend == "down":
            return "呈現顯著下降趨勢，可能衰減"
        if trend == "up":
            return "呈現顯著上升趨勢"
        if trend == "flat":
            return "趨勢不顯著或近乎持平"
        return "趨勢不確定"

    @staticmethod
    def _ensure_trend_dict(result: dict | SkippedResult) -> dict | None:
        if isinstance(result, SkippedResult):
            return None
        if result.get("inference_status") == ti.STATUS_BELOW_MIN_SAMPLES:
            return None
        return result

    def _combine_signal(
        self,
        ic_result: Optional[dict],
        centrality_result: Optional[dict],
        ic_decay_half_life: Optional[float],
    ) -> dict:
        """綜合訊號（ICPERF ㊺ B(6)）：ic、centrality 兩維皆可判定 ⇒ 現行規則表；任一缺或 `indeterminate` ⇒
        「資訊不足」，reason 列不可判定之維與原因並保留可判定維之觀察，不得輸出「正常／訊號穩定」。"""
        names = {"ic": "IC", "centrality": "中心性"}
        words = {"up": "上升", "down": "下降", "flat": "持平"}
        known: list[str] = []
        unknown: list[str] = []
        for key, res in (("ic", ic_result), ("centrality", centrality_result)):
            trend = res.get("trend") if res else None
            if trend in words:
                known.append(f"{names[key]} {words[trend]}")
            else:
                why = (res or {}).get("inference_status") or ("source_unavailable" if res is None else "indeterminate")
                unknown.append(f"{names[key]}不可判定：{why}")
        if unknown:
            return {
                "recommendation": "資訊不足",
                "reason": "；".join(known + unknown),
                "action": "補足資料後重跑",
            }

        ic_trend = ic_result.get("trend")
        centrality_trend = centrality_result.get("trend")

        recommendation = "正常"
        reason = "訊號穩定"
        action = "維持觀察"

        if ic_trend == "down" and centrality_trend == "up":
            recommendation = "危險"
            reason = "IC 下降 + Centrality 上升"
            action = "建議降低配置"
        elif (ic_trend == "down" and centrality_trend == "flat") or (
            ic_trend == "flat" and centrality_trend == "up"
        ):
            recommendation = "警告"
            reason = "存在衰減或擁擠訊號"
            action = "建議提高監控頻率"
        elif ic_trend == "up" and centrality_trend == "down":
            recommendation = "正常"
            reason = "IC 改善且擁擠度降低"
            action = "可維持配置"

        if ic_decay_half_life is not None and np.isfinite(ic_decay_half_life) and ic_decay_half_life < 5:
            if recommendation == "正常":
                recommendation = "警告"
                reason += " + half_life 偏短"
            elif recommendation == "警告":
                recommendation = "危險"
                reason += " + half_life 偏短"

        return {
            "recommendation": recommendation,
            "reason": reason,
            "action": action,
        }
