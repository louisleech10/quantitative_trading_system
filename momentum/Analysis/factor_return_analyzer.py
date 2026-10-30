"""Module 1: Factor return analysis — 單標的因子擇時多空(PIT expanding)。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.core.logging import get_logger


logger = get_logger(__name__)

# index 對齊政策字串(序列化/artifact 契約)
INDEX_POLICY_FRAME_DROPNA = "frame_dropna_intersection"


@dataclass(frozen=True)
class FactorTimingReturnSeries:
    """Internal artifact: 單標的因子擇時多空序列(供 net_ic / orchestrator)。"""

    feature: str
    ls_return: pd.Series
    position: pd.Series
    index_policy: str


class FactorReturnAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._num_quantiles = int(cfg.get("num_quantiles", 5))
        self._risk_free_rate = float(cfg.get("risk_free_rate", 0.0))
        # 全序列最低列數 gate(production 預設 30;test-config 可降)
        self._min_samples = int(cfg.get("min_samples", 30))
        # 分位冷啟動: t < warmup_periods → position=0
        self._warmup_periods = int(cfg.get("warmup_periods", 20))
        # 最近一次 compute_batch/compute_factor_returns 的 series map
        self._series_map: dict[str, FactorTimingReturnSeries] = {}

    def get_series_map(self) -> dict[str, FactorTimingReturnSeries]:
        """回傳最近一次批次/單次計算的 series artifact(唯讀副本)。"""
        return dict(self._series_map)

    def compute_factor_returns(
        self,
        feature: pd.Series,
        future_returns: pd.Series,
        num_quantiles: Optional[int] = None,
        *,
        feature_name: Optional[str] = None,
        store_series: bool = True,
        horizon: int = 1,
    ) -> dict | SkippedResult:
        """計算單因子 PIT expanding 擇時多空序列與摘要指標。

        公式鎖(SPEC §C;ICPERF Task 0.4 ⑭–⑰):
          - returns_w = future_return(raw identity, 無 winsorize);``horizon``＝其前瞻根數 h
          - position_t = PIT expanding qcut 邊分位 membership(+1 top / -1 bottom / 0 else);
            分箱歷史＝特徵自身全時序 0..t 之有限值(RB-3,不受標籤可得性影響);頂分位＝當根實際箱數 k_t−1
          - ls_return_full = position * returns_w(只在特徵與標籤皆有限之列)
          - 風險指標與 ls_cumulative 以自首個有效根起每隔 h 根(原始時間位置)之不重疊序列計;
            年化期數＝有效根密度(每年根數,時間戳導出)／h

        ``horizon`` 預設 1 僅為單特徵直接呼叫之相容預設;批次入口 ``compute_batch`` 必填。
        """
        h = int(horizon)
        if h < 1:
            raise ValueError(f"horizon must be >= 1, got {horizon!r}")
        name = feature_name
        if name is None:
            name = str(feature.name) if feature.name is not None else "feature"

        def _skip(reason: str, error_type: str) -> SkippedResult:
            # SkippedResult 路徑不得留下同名 stale series(F0-codex-3)
            if name in self._series_map:
                del self._series_map[name]
            return SkippedResult(
                module_name="factor_return",
                reason=reason,
                error_type=error_type,
            )

        # 特徵全時序(分箱歷史來源);標籤對齊至特徵時間軸(特徵軸外之標籤列無特徵、不可能入 frame)
        feat_all = pd.Series(feature, dtype=float)
        y_all = pd.Series(future_returns, dtype=float).reindex(feat_all.index)
        feat_arr = feat_all.to_numpy(dtype=float)
        y_arr = y_all.to_numpy(dtype=float)

        # NaN/inf gate: 非有限值明確剔除(鐵律,不得 silent 進 ls/risk)
        both_present = ~np.isnan(feat_arr) & ~np.isnan(y_arr)
        valid = np.isfinite(feat_arr) & np.isfinite(y_arr)
        if bool(both_present.any()) and not bool(valid.any()):
            return _skip(
                "non-finite feature/future_returns (all inf/nan after dropna)",
                "INVALID_DATA",
            )
        valid_pos = np.flatnonzero(valid)
        frame_index = feat_all.index[valid]

        if len(frame_index) < self._min_samples:
            return _skip(
                f"insufficient samples: {len(frame_index)} < {self._min_samples}",
                "INSUFFICIENT_DATA",
            )

        if np.unique(feat_arr[valid_pos]).size <= 1:
            return _skip("constant feature", "INSUFFICIENT_DATA")

        # 全期 nanstd 僅作 skip 守衛(不入報酬值;SPEC §C 保留)
        y_vals = y_arr[valid_pos]
        if float(np.nanstd(y_vals)) == 0.0:
            return _skip("zero variance future_returns", "INSUFFICIENT_DATA")

        returns_w = pd.Series(y_vals, index=frame_index, dtype=float)  # raw identity(v0.6 winsorize 移除)
        quantiles = int(num_quantiles or self._num_quantiles)
        position = self._pit_expanding_position(
            feat_all,
            num_quantiles=quantiles,
            warmup_periods=self._warmup_periods,
            eval_positions=valid_pos,
        )
        position.index = frame_index

        # post-warmup 全程無 ±1 → 整段 skip
        if int((position != 0).sum()) == 0:
            return _skip(
                "no active edge quantiles after warmup",
                "INSUFFICIENT_DATA",
            )

        ls_return_full = (position * returns_w).astype(float)
        # 雙重保險: artifact 不得含非有限
        if not np.isfinite(ls_return_full.to_numpy(dtype=float)).all():
            return _skip("non-finite ls_return produced", "INVALID_DATA")

        # h 根前瞻報酬每根取樣而相鄰重疊 ⇒ 自首個有效根起每隔 h 根(原始時間位置)取一,得不重疊序列
        non_overlap = ((valid_pos - valid_pos[0]) % h) == 0
        ls_return_nov = ls_return_full.iloc[np.flatnonzero(non_overlap)]

        ls_cumulative = (1.0 + ls_return_nov).cumprod() - 1.0
        # ICPERF Task 0.4 ㉕：同一不重疊序列之逐時點輸出（趨勢 factor_return 維）——置於原時間軸自首個有效根起每 h 根之
        # 格點（格點序號＝(位置−首位置)／h），無有效根之格點為 NaN（中段缺根不壓縮時間軸）；不重疊 ⇒ 無重疊窗
        grid = (valid_pos[non_overlap] - valid_pos[0]) // h
        ls_return_series = np.full(int(grid[-1]) + 1, np.nan)
        ls_return_series[grid] = ls_return_nov.to_numpy(dtype=float)
        active_bar_count = int((position != 0).sum())
        turnover_series = position.astype(float).diff().abs().fillna(0.0)
        turnover = float(turnover_series.mean())

        bars_per_year = self._infer_periods_per_year(frame_index)
        risk_metrics = self.compute_risk_metrics(
            ls_return_nov,
            risk_free_rate=self._risk_free_rate,
            periods_per_year=bars_per_year / h,
        )

        # 描述性 ex-post 全樣本分位摘要(非可交易訊號;標 descriptive_full_sample)
        quantile_summary = self._descriptive_quantile_summary(
            pd.Series(feat_arr[valid_pos], index=frame_index, dtype=float),
            returns_w,
            quantiles,
        )

        if store_series:
            self._series_map[name] = FactorTimingReturnSeries(
                feature=name,
                ls_return=ls_return_full.copy(),
                position=position.astype(int).copy(),
                index_policy=INDEX_POLICY_FRAME_DROPNA,
            )

        return {
            "long_short_mean_return": float(ls_return_full.mean()),
            "ls_cumulative_sampled": self._sample_series(ls_cumulative, max_points=100),
            "ls_return_series": ls_return_series.tolist(),
            "risk_metrics": risk_metrics,
            "active_bar_count": active_bar_count,
            "turnover": turnover,
            "quantile_summary": quantile_summary,
            "num_quantiles_used": quantiles,
            "newey_west_adjusted": False,
        }

    def compute_risk_metrics(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.0,
        periods_per_year: Optional[float] = None,
    ) -> dict:
        """風險指標(輸入須為不重疊之逐期報酬;``periods_per_year``＝每年期數)。

        ICPERF Task 0.4 ⑯⑰:年化報酬＝CAGR＝∏(1+r)^(P/N)−1;Sortino 下行偏差＝√mean(min(r,0)²)(全觀測);
        標準差以 numpy ddof=1、以相對容差判 0(避免浮點殘差 ~1e-18 冒充非零)。
        ``periods_per_year`` 為 None ⇒ 365(直接呼叫之相容預設);非有限或 ≤ 0 ⇒ 年化類指標 NaN。
        """
        # 非有限輸入全轉 nan 後剔除(F0-codex-2);禁止 inf 出口
        raw = pd.Series(returns, dtype=float).to_numpy(dtype=float)
        clean = raw[np.isfinite(raw)]
        if clean.size == 0:
            return {
                "sharpe_ratio": np.nan,
                "sortino_ratio": np.nan,
                "calmar_ratio": np.nan,
                "max_drawdown": np.nan,
                "win_rate": np.nan,
                "annualized_return": np.nan,
                "annualized_volatility": np.nan,
            }

        periods = 365.0 if periods_per_year is None else float(periods_per_year)
        periods_ok = bool(np.isfinite(periods) and periods > 0)
        n_obs = int(clean.size)
        mean_return = float(np.mean(clean))
        # 相對容差:|r| 尺度之 1e-12 以下之離散度視為 0
        zero_tol = 1e-12 * float(np.max(np.abs(clean)))
        std_return = float(np.std(clean, ddof=1)) if n_obs > 1 else np.nan
        std_ok = bool(np.isfinite(std_return) and std_return > zero_tol)

        # CAGR;權益曾 ≤ 0(某期 r ≤ −1)⇒ 歸零記 −1、轉負無定義記 NaN;合理界 abs>1e6 視為 garbage(F0-composer-2)
        growth = float(np.prod(1.0 + clean))
        annualized_return = np.nan
        if periods_ok and np.isfinite(growth):
            if bool(np.any(clean == -1.0)):
                annualized_return = -1.0
            elif bool(np.all(clean > -1.0)):
                try:
                    annualized_return = float(growth ** (periods / n_obs) - 1.0)
                except OverflowError:
                    annualized_return = np.nan
                if (not np.isfinite(annualized_return)) or abs(annualized_return) > 1e6:
                    annualized_return = np.nan

        # 離散度判為 0(常數報酬)⇒ 波動恰 0(數學值);Sharpe／Sortino 分母 0 ⇒ NaN
        if std_ok and periods_ok:
            annualized_volatility = float(std_return * np.sqrt(periods))
        elif np.isfinite(std_return) and periods_ok:
            annualized_volatility = 0.0
        else:
            annualized_volatility = np.nan
        if not np.isfinite(annualized_volatility):
            annualized_volatility = np.nan

        rf_period = risk_free_rate / periods if periods_ok else np.nan
        sharpe = (
            float((mean_return - rf_period) / std_return * np.sqrt(periods))
            if std_ok and periods_ok
            else np.nan
        )
        if not np.isfinite(sharpe):
            sharpe = np.nan

        downside_dev = float(np.sqrt(np.mean(np.minimum(clean, 0.0) ** 2)))
        sortino = (
            float((mean_return - rf_period) / downside_dev * np.sqrt(periods))
            if periods_ok and downside_dev > zero_tol
            else np.nan
        )
        if not np.isfinite(sortino):
            sortino = np.nan

        equity = np.cumprod(1.0 + clean)
        rolling_peak = np.maximum.accumulate(equity)
        # 避免 0/0 或 inf equity 污染 drawdown
        with np.errstate(divide="ignore", invalid="ignore"):
            drawdown = equity / rolling_peak - 1.0
        finite_dd = drawdown[np.isfinite(drawdown)]
        max_drawdown = float(np.min(finite_dd)) if finite_dd.size else np.nan
        if not np.isfinite(max_drawdown):
            max_drawdown = np.nan
        calmar = (
            float(annualized_return / abs(max_drawdown))
            if np.isfinite(annualized_return)
            and np.isfinite(max_drawdown)
            and max_drawdown < 0
            else np.nan
        )
        if not np.isfinite(calmar):
            calmar = np.nan

        win_rate = float((clean > 0).mean())
        if not np.isfinite(win_rate):
            win_rate = np.nan

        return {
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility,
        }

    def compute_batch(
        self,
        features_df: pd.DataFrame,
        future_returns: pd.Series,
        *,
        horizon: int,
        top_n: int,
    ) -> dict[str, Any]:
        """批次計算並回傳 §U ok union;series 經 get_series_map() 取用。

        ``horizon``＝標籤前瞻根數(必填關鍵字,ICPERF Task 0.4 ⑯;呼叫端傳 effective_horizon)。
        """
        h = int(horizon)
        if h < 1:
            raise ValueError(f"horizon must be >= 1, got {horizon!r}")
        self._series_map = {}
        features_payload: dict[str, dict[str, Any]] = {}
        selected_columns = list(features_df.columns)[: max(1, int(top_n))]

        for name in selected_columns:
            result = self.compute_factor_returns(
                features_df[name],
                future_returns,
                feature_name=str(name),
                store_series=True,
                horizon=h,
            )
            if isinstance(result, SkippedResult):
                # SkippedResult 不入 features;series_map 亦不寫
                if str(name) in self._series_map:
                    del self._series_map[str(name)]
                continue
            features_payload[str(name)] = result

        logger.info(
            "Factor return analysis completed: %s features (%s ok)",
            len(selected_columns),
            len(features_payload),
        )

        # §U ok union(F0.2 external schema)
        return {
            "status": "ok",
            "value": {
                "schema_version": "fr_full_v1",
                "semantics": "single_asset_factor_timing_ls",
                "quantile_fit": "pit_expanding",
                "return_transform": "identity",
                "turnover_semantics": "abs_delta_position_p1",
                "warmup_periods": int(self._warmup_periods),
                "features": features_payload,
            },
            "reason": None,
        }

    @staticmethod
    def _pit_expanding_position(
        feature: pd.Series,
        *,
        num_quantiles: int,
        warmup_periods: int,
        eval_positions: Optional[np.ndarray] = None,
    ) -> pd.Series:
        """§C 手刻 PIT expanding 分位 membership(ICPERF Task 0.4 ⑭⑮)。

        第 t 根(t ∈ ``eval_positions``,特徵時間軸之位置;None ⇒ 全部有限根):
          - 分箱歷史＝``feature`` 於 0..t 之有限值(特徵自身全時序,RB-3;不受標籤可得性影響)
          - 有限歷史序位 < ``warmup_periods`` ⇒ 0
          - q_eff＝min(q, 歷史相異值數),< 2 ⇒ 0;``pd.qcut(歷史, q_eff, duplicates="drop")``
            之當根標籤 ℓ 與實際箱數 k_t;k_t < 2 ⇒ 0;ℓ＝k_t−1 ⇒ +1;ℓ＝0 ⇒ −1
        回傳 position(index＝``feature.index[eval_positions]``)。不複用 pit_stats(q_eff 語意不同)。
        """
        vals = pd.Series(feature, dtype=float).to_numpy(dtype=float)
        fin = np.isfinite(vals)
        if eval_positions is None:
            eval_positions = np.flatnonzero(fin)
        eval_positions = np.asarray(eval_positions, dtype=np.int64)
        out = np.zeros(eval_positions.size, dtype=int)
        if eval_positions.size == 0:
            return pd.Series(out, index=feature.index[eval_positions], dtype=int)
        q = int(num_quantiles)
        finite_rank = np.cumsum(fin) - 1  # 當根於有限歷史中之序位
        seen: set = set()
        hist: list[float] = []
        cursor = 0
        for j, t in enumerate(eval_positions):
            # 增量擴張有限歷史至 t(含)
            while cursor <= t:
                if fin[cursor]:
                    v = float(vals[cursor])
                    hist.append(v)
                    seen.add(v)
                cursor += 1
            if not fin[t] or finite_rank[t] < warmup_periods:
                continue
            q_eff = min(q, len(seen))
            if q_eff < 2:
                continue
            try:
                labels, edges = pd.qcut(
                    np.asarray(hist, dtype=float), q_eff, labels=False, duplicates="drop", retbins=True
                )
            except ValueError:
                continue
            label_t = np.asarray(labels, dtype=float)[-1]
            k_t = len(edges) - 1
            if not np.isfinite(label_t) or k_t < 2:
                continue
            label_i = int(label_t)
            if label_i == k_t - 1:
                out[j] = 1
            elif label_i == 0:
                out[j] = -1
        return pd.Series(out, index=feature.index[eval_positions], dtype=int)

    @staticmethod
    def _descriptive_quantile_summary(
        feature: pd.Series,
        returns: pd.Series,
        num_quantiles: int,
    ) -> dict[str, Any]:
        """全樣本描述性分位平均報酬(非可交易訊號)。"""
        summary: dict[str, Any] = {"descriptive_full_sample": True}
        q_eff = min(int(num_quantiles), int(feature.nunique()))
        if q_eff < 2:
            return summary
        try:
            bins = pd.qcut(feature, q=q_eff, labels=False, duplicates="drop")
        except ValueError:
            return summary
        if bins is None or bins.dropna().empty:
            return summary
        for quantile_value in sorted(bins.dropna().unique()):
            label = f"Q{int(quantile_value) + 1}"
            series = returns[bins == quantile_value]
            summary[label] = float(series.mean()) if not series.empty else np.nan
        return summary

    @staticmethod
    def _sample_series(series: pd.Series, max_points: int) -> list[float]:
        values = pd.Series(series, dtype=float).dropna().values
        if len(values) <= max_points:
            return values.astype(float).tolist()
        idx = np.linspace(0, len(values) - 1, max_points).astype(int)
        return values[idx].astype(float).tolist()

    @staticmethod
    def _infer_periods_per_year(index: pd.Index) -> float:
        """觀測根密度＝每年根數＝(有效根數−1)／時間跨度(年,365 日)(ICPERF Task 0.4 ⑯ FR-9)。

        由時間戳導出,不寫死 24h(非 24/7 市場如工作日日線得實際每年根數);非 DatetimeIndex、
        < 2 列或跨度 ≤ 0 ⇒ NaN(無時間戳無從導出,年化類指標隨之 NaN)。
        """
        if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
            return float("nan")
        span_seconds = float(index[-1].value - index[0].value) / 1e9
        if not np.isfinite(span_seconds) or span_seconds <= 0:
            return float("nan")
        return float((len(index) - 1) * 365.0 * 86400.0 / span_seconds)
