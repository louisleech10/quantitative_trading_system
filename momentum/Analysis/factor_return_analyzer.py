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
    ) -> dict | SkippedResult:
        """計算單因子 PIT expanding 擇時多空序列與摘要指標。

        公式鎖(SPEC §C):
          - returns_w = future_return(raw identity, 無 winsorize)
          - position_t = PIT expanding qcut 邊分位 membership(+1 top / -1 bottom / 0 else)
          - ls_return_full = position * returns_w
        """
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

        frame = pd.concat(
            [feature.rename("feature"), future_returns.rename("y")],
            axis=1,
        ).dropna()

        # NaN/inf gate: 非有限值明確剔除(鐵律,不得 silent 進 ls/risk)
        if not frame.empty:
            feat_f = frame["feature"].astype(float)
            y_f = frame["y"].astype(float)
            finite_mask = np.isfinite(feat_f.to_numpy(dtype=float)) & np.isfinite(
                y_f.to_numpy(dtype=float)
            )
            if not bool(finite_mask.all()):
                # 若整段皆非有限 → INVALID_DATA;部分 → drop 該列
                if not bool(finite_mask.any()):
                    return _skip(
                        "non-finite feature/future_returns (all inf/nan after dropna)",
                        "INVALID_DATA",
                    )
                frame = frame.loc[finite_mask].copy()

        if len(frame) < self._min_samples:
            return _skip(
                f"insufficient samples: {len(frame)} < {self._min_samples}",
                "INSUFFICIENT_DATA",
            )

        if frame["feature"].nunique(dropna=True) <= 1:
            return _skip("constant feature", "INSUFFICIENT_DATA")

        # 全期 nanstd 僅作 skip 守衛(不入報酬值;SPEC §C 保留)
        y_vals = frame["y"].values.astype(float)
        if not np.isfinite(y_vals).all() or float(np.nanstd(y_vals)) == 0.0:
            if not np.isfinite(y_vals).all():
                return _skip(
                    "non-finite future_returns after finite filter",
                    "INVALID_DATA",
                )
            return _skip("zero variance future_returns", "INSUFFICIENT_DATA")

        returns_w = frame["y"].astype(float)  # raw identity(v0.6 winsorize 移除)
        quantiles = int(num_quantiles or self._num_quantiles)
        position = self._pit_expanding_position(
            frame["feature"].astype(float),
            num_quantiles=quantiles,
            warmup_periods=self._warmup_periods,
        )

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

        ls_cumulative = (1.0 + ls_return_full).cumprod() - 1.0
        active_bar_count = int((position != 0).sum())
        turnover_series = position.astype(float).diff().abs().fillna(0.0)
        turnover = float(turnover_series.mean())

        risk_metrics = self.compute_risk_metrics(
            ls_return_full,
            risk_free_rate=self._risk_free_rate,
            periods_per_year=self._infer_periods_per_year(frame.index),
        )

        # 描述性 ex-post 全樣本分位摘要(非可交易訊號;標 descriptive_full_sample)
        quantile_summary = self._descriptive_quantile_summary(
            frame["feature"].astype(float),
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
        periods_per_year: Optional[int] = None,
    ) -> dict:
        # 非有限輸入全轉 nan 後剔除(F0-codex-2);禁止 inf 出口
        raw = pd.Series(returns, dtype=float)
        clean = raw[np.isfinite(raw.to_numpy(dtype=float))]
        if clean.empty:
            return {
                "sharpe_ratio": np.nan,
                "sortino_ratio": np.nan,
                "calmar_ratio": np.nan,
                "max_drawdown": np.nan,
                "win_rate": np.nan,
                "annualized_return": np.nan,
                "annualized_volatility": np.nan,
            }

        periods = int(periods_per_year or 365)
        mean_return = float(clean.mean())
        std_return = float(clean.std(ddof=1))
        if not np.isfinite(mean_return):
            mean_return = np.nan
        if not np.isfinite(std_return):
            std_return = np.nan

        # crypto 高頻 + 大 mean 時 (1+r)^periods 可能 overflow / 不合理大數 → nan
        # 合理界 abs>1e6 視為 garbage(F0-composer-2)
        try:
            annualized_return = float((1.0 + mean_return) ** periods - 1.0)
            if (not np.isfinite(annualized_return)) or abs(annualized_return) > 1e6:
                annualized_return = np.nan
        except (OverflowError, FloatingPointError, ValueError):
            annualized_return = np.nan

        if np.isfinite(std_return) and std_return > 0:
            annualized_volatility = float(std_return * np.sqrt(periods))
            if not np.isfinite(annualized_volatility):
                annualized_volatility = np.nan
        else:
            annualized_volatility = np.nan

        rf_period = risk_free_rate / periods
        sharpe = (
            float((mean_return - rf_period) / std_return * np.sqrt(periods))
            if np.isfinite(std_return) and std_return > 0 and np.isfinite(mean_return)
            else np.nan
        )
        if not np.isfinite(sharpe):
            sharpe = np.nan

        downside = clean[clean < 0.0]
        downside_std = float(downside.std(ddof=1)) if len(downside) >= 2 else np.nan
        sortino = (
            float((mean_return - rf_period) / downside_std * np.sqrt(periods))
            if np.isfinite(downside_std)
            and downside_std > 0
            and np.isfinite(mean_return)
            else np.nan
        )
        if not np.isfinite(sortino):
            sortino = np.nan

        equity = (1.0 + clean).cumprod()
        rolling_peak = equity.cummax()
        # 避免 0/0 或 inf equity 污染 drawdown
        with np.errstate(divide="ignore", invalid="ignore"):
            drawdown = equity / rolling_peak - 1.0
        max_drawdown = float(drawdown.min()) if not drawdown.empty else np.nan
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
        top_n: int = 30,
    ) -> dict[str, Any]:
        """批次計算並回傳 §U ok union;series 經 get_series_map() 取用。"""
        self._series_map = {}
        features_payload: dict[str, dict[str, Any]] = {}
        selected_columns = list(features_df.columns)[: max(1, int(top_n))]

        for name in selected_columns:
            result = self.compute_factor_returns(
                features_df[name],
                future_returns,
                feature_name=str(name),
                store_series=True,
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
    ) -> pd.Series:
        """§C 手刻 PIT expanding 分位 membership。

        不複用 pit_stats.pit_expanding_qcut_label(語意差會改凍結 golden)。
        """
        position = pd.Series(0, index=feature.index, dtype=int)
        n = len(feature)
        for t in range(n):
            if t < warmup_periods:
                continue
            window = feature.iloc[: t + 1]
            q_eff = min(int(num_quantiles), int(window.nunique()))
            if q_eff < 2:
                continue
            try:
                labels = pd.qcut(window, q_eff, labels=False, duplicates="drop")
            except ValueError:
                continue
            if labels is None or labels.dropna().empty:
                continue
            label_t = labels.iloc[-1]
            if pd.isna(label_t):
                continue
            label_i = int(label_t)
            if label_i == q_eff - 1:
                position.iloc[t] = 1
            elif label_i == 0:
                position.iloc[t] = -1
        return position

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
    def _infer_periods_per_year(index: pd.Index) -> int:
        if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
            return 365
        median_delta_hours = (
            pd.Series(index).diff().dropna().dt.total_seconds().median() / 3600.0
        )
        if not np.isfinite(median_delta_hours) or median_delta_hours <= 0:
            return 365
        return int(round((24.0 * 365.0) / median_delta_hours))
