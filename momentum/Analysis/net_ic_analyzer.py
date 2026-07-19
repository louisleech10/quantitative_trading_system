"""Module 10: Net IC analyzer (B-strict: 成本拖累,禁混量綱減)."""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)

_TURNOVER_SEMANTICS = "membership_change_both_legs_per_bar"
_COST_SEMANTICS = "per_rebalance_not_annualized"
_UNAVAILABLE_REASON = "canonical_factor_return_series_not_built (1c-FR)"
_ZERO_TURNOVER_REASON = "zero_mean_turnover"
_INSUFFICIENT_ALIGNED_REASON = "insufficient_aligned_series"
_SERIES_SHAPE_REASON = "factor_return_series_missing_or_invalid"


def _unavailable(reason: str = _UNAVAILABLE_REASON) -> dict[str, Any]:
    """§U conditional metric unavailable 形狀。"""
    return {"status": "unavailable", "value": None, "reason": reason}


def _ok(value: float | bool) -> dict[str, Any]:
    """§U conditional metric ok 形狀(reason=null)。"""
    return {"status": "ok", "value": value, "reason": None}


def _finite_or_null(value: Any) -> float | None:
    """非有限 number → null(JSON strict 邊界)。"""
    if value is None:
        return None
    try:
        fv = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(fv):
        return None
    return fv


def position_to_turnover_series(position: pd.Series) -> pd.Series:
    """D6: turnover_t = |position_t − position_{t−1}|;首 bar=0(fillna,非 NaN-drop)。

    雙邊尺度 ∈ {0,1,2};與 top-only membership turnover 不同。
    """
    return position.astype(float).diff().abs().fillna(0.0)


def _extract_gross_position(
    series_obj: Any,
) -> tuple[pd.Series, pd.Series] | None:
    """從 FactorTimingReturnSeries / duck-typed 物件取 gross=ls_return、position。

    裸 pd.Series 或缺欄 → None(禁 scalar 廣播/忽略舊 factor_returns 注入)。
    """
    if series_obj is None:
        return None
    ls = getattr(series_obj, "ls_return", None)
    pos = getattr(series_obj, "position", None)
    if ls is None and isinstance(series_obj, dict):
        ls = series_obj.get("ls_return")
        pos = series_obj.get("position")
    if not isinstance(ls, pd.Series) or not isinstance(pos, pd.Series):
        return None
    if ls.empty or pos.empty:
        return None
    return ls, pos


def compute_breakeven_and_net(
    gross: pd.Series,
    turnover: pd.Series,
    cost_bps: float | None,
) -> dict[str, Any]:
    """對齊 dropna 後算 net_mean / breakeven_cost_bps / profitable。

    breakeven = mean(gross)/mean(turnover)*10000;mean(turnover)==0 → unavailable。
    net_t = gross_t − (cost_bps/10000)*turnover_t;cost_bps=None 視為 0。
    """
    aligned = pd.concat(
        [gross.rename("gross"), turnover.rename("turnover")],
        axis=1,
    ).dropna()
    if aligned.empty:
        return {
            "evaluable": False,
            "reason": _INSUFFICIENT_ALIGNED_REASON,
            "gross_mean": None,
            "turnover_mean": None,
            "net_mean": None,
            "breakeven_cost_bps": None,
            "profitable_after_cost": None,
        }

    gross_mean = float(aligned["gross"].astype(float).mean())
    to_mean = float(aligned["turnover"].astype(float).mean())
    use_cost = float(cost_bps) if cost_bps is not None else 0.0
    cost_term = (use_cost / 10000.0) * aligned["turnover"].astype(float)
    net_series = aligned["gross"].astype(float) - cost_term
    net_mean = float(net_series.mean())

    if not math.isfinite(to_mean) or to_mean == 0.0:
        return {
            "evaluable": True,
            "reason": _ZERO_TURNOVER_REASON,
            "gross_mean": gross_mean if math.isfinite(gross_mean) else None,
            "turnover_mean": to_mean if math.isfinite(to_mean) else 0.0,
            "net_mean": net_mean if math.isfinite(net_mean) else None,
            "breakeven_cost_bps": None,
            "profitable_after_cost": (
                bool(net_mean > 0.0) if math.isfinite(net_mean) else None
            ),
        }

    if not math.isfinite(gross_mean) or not math.isfinite(net_mean):
        return {
            "evaluable": False,
            "reason": _INSUFFICIENT_ALIGNED_REASON,
            "gross_mean": None,
            "turnover_mean": to_mean,
            "net_mean": None,
            "breakeven_cost_bps": None,
            "profitable_after_cost": None,
        }

    breakeven = (gross_mean / to_mean) * 10000.0
    return {
        "evaluable": True,
        "reason": None,
        "gross_mean": gross_mean,
        "turnover_mean": to_mean,
        "net_mean": net_mean,
        "breakeven_cost_bps": float(breakeven),
        "profitable_after_cost": bool(net_mean > 0.0),
    }

def _validate_cost_params(cost_enabled: bool, cost_bps: float | None) -> None:
    """三層統一 validator 偽碼:非 None 一律驗域;enabled 另驗非 None。"""
    if cost_bps is not None:
        try:
            bps = float(cost_bps)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"cost_bps must be finite and in (0, 1000], got {cost_bps!r}"
            ) from exc
        if not math.isfinite(bps) or not (0.0 < bps <= 1000.0):
            raise ValueError(
                f"cost_bps must be finite and in (0, 1000], got {cost_bps!r}"
            )
    if cost_enabled and cost_bps is None:
        raise ValueError("cost_enabled=True requires cost_bps to be set (0 is illegal)")


class NetICAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._cost_enabled = bool(cfg.get("cost_enabled", False))
        raw_bps = cfg.get("cost_bps", None)
        self._cost_bps: float | None
        if raw_bps is None:
            self._cost_bps = None
        else:
            self._cost_bps = float(raw_bps)
        _validate_cost_params(self._cost_enabled, self._cost_bps)
        self._participation_rate = float(cfg.get("participation_rate", 0.01))

    @staticmethod
    def compute_cost_drag(cost_bps: float, turnover: float) -> float:
        """成本拖累(報酬空間)= (cost_bps/10000)×turnover;無 ×2。

        呼叫前提:turnover 已過 profile 檢查(有限且 ≥0)。
        """
        return float((float(cost_bps) / 10000.0) * float(turnover))

    def compute_net_factor_return(
        self,
        gross_return_series: pd.Series,
        turnover_series: pd.Series,
        cost_bps: Optional[float] = None,
    ) -> dict:
        """Deprecated(1c):canonical 因子報酬序列未建立前勿用於 batch_analyze。

        保留函式本體供日後 1c-FR;本票 batch_analyze 不再呼叫。
        """
        use_cost = float(
            self._cost_bps if cost_bps is None else cost_bps
        ) if (cost_bps is not None or self._cost_bps is not None) else 0.0
        aligned = pd.concat(
            [gross_return_series.rename("gross"), turnover_series.rename("turnover")],
            axis=1,
        ).dropna()
        if aligned.empty:
            return {
                "net_return_series": [],
                "gross_mean": np.nan,
                "net_mean": np.nan,
                "cost_drag": np.nan,
            }

        cost_term = (use_cost / 10000.0) * aligned["turnover"].astype(float)
        net_series = aligned["gross"].astype(float) - cost_term
        return {
            "net_return_series": net_series.astype(float).tolist(),
            "gross_mean": float(aligned["gross"].mean()),
            "net_mean": float(net_series.mean()),
            "cost_drag": float((aligned["gross"].mean() - net_series.mean())),
        }

    def cost_sensitivity_analysis(
        self,
        cost_bps: float,
        turnover: float,
    ) -> list[dict[str, float]]:
        """成本階梯掃描:{c/2,c,2c,5c} clamp [0.1,1000] 四捨五入 0.1 去重。

        每項僅 {cost_bps, cost_drag_return};無 net_ic 鍵。
        """
        c = float(cost_bps)
        t = float(turnover)
        raw = [c / 2.0, c, 2.0 * c, 5.0 * c]
        ladder = sorted(
            {round(min(1000.0, max(0.1, x)), 1) for x in raw}
        )
        return [
            {
                "cost_bps": float(scenario),
                "cost_drag_return": self.compute_cost_drag(scenario, t),
            }
            for scenario in ladder
        ]

    def estimate_factor_capacity(
        self,
        turnover: float,
        avg_daily_volume_usd: Optional[float] = None,
        participation_rate: float = 0.01,
    ) -> dict:
        """容量估計(計算本體不變;calibration 由 batch 組 dict 時注入)。"""
        turnover_value = max(0.0, float(turnover))
        if avg_daily_volume_usd is None or avg_daily_volume_usd <= 0:
            return {
                "estimated_capacity_usd": np.nan,
                "capacity_tier": "unknown",
            }

        effective_rate = float(participation_rate or self._participation_rate)
        if turnover_value <= 0:
            capacity = float(avg_daily_volume_usd * effective_rate)
        else:
            capacity = float((avg_daily_volume_usd * effective_rate) / turnover_value)

        if turnover_value > 1.0:
            tier = "low"
        elif turnover_value > 0.5:
            tier = "medium"
        else:
            tier = "high"

        return {
            "estimated_capacity_usd": capacity,
            "capacity_tier": tier,
        }

    def _capacity_payload(
        self,
        turnover: float,
        avg_daily_volume_usd: Optional[float],
    ) -> dict[str, Any]:
        raw = self.estimate_factor_capacity(
            turnover=float(turnover),
            avg_daily_volume_usd=avg_daily_volume_usd,
            participation_rate=self._participation_rate,
        )
        return {
            "estimated_capacity_usd": _finite_or_null(raw.get("estimated_capacity_usd")),
            "capacity_tier": str(raw.get("capacity_tier", "unknown")),
            "calibration": "uncalibrated",
        }

    def _series_conditional_metrics(
        self,
        series_obj: Any,
        *,
        cost_bps: float | None,
        include_cost_keys: bool,
    ) -> tuple[dict[str, Any], bool, bool]:
        """由 PIT series 回填 net/breakeven/profitable。

        Returns:
            metrics: 要 merge 進 feature dict 的 conditional keys
            is_evaluable: 對齊後可評估(含 zero-turnover 但 net 可算)
            is_profitable: profitable_after_cost value is True
        """
        extracted = _extract_gross_position(series_obj)
        if extracted is None:
            metrics: dict[str, Any] = {
                "net_factor_return": _unavailable(_SERIES_SHAPE_REASON if series_obj is not None else _UNAVAILABLE_REASON),
            }
            if include_cost_keys:
                metrics["breakeven_cost_bps"] = _unavailable(
                    _SERIES_SHAPE_REASON if series_obj is not None else _UNAVAILABLE_REASON
                )
                metrics["profitable_after_cost"] = _unavailable(
                    _SERIES_SHAPE_REASON if series_obj is not None else _UNAVAILABLE_REASON
                )
            return metrics, False, False

        gross, position = extracted
        turnover_s = position_to_turnover_series(position)
        stats = compute_breakeven_and_net(gross, turnover_s, cost_bps=cost_bps)

        if not stats["evaluable"] or stats["net_mean"] is None:
            reason = str(stats.get("reason") or _INSUFFICIENT_ALIGNED_REASON)
            metrics = {"net_factor_return": _unavailable(reason)}
            if include_cost_keys:
                metrics["breakeven_cost_bps"] = _unavailable(reason)
                metrics["profitable_after_cost"] = _unavailable(reason)
            return metrics, False, False

        net_mean = float(stats["net_mean"])
        metrics = {"net_factor_return": _ok(net_mean)}
        is_profitable = bool(net_mean > 0.0)

        if include_cost_keys:
            be = stats.get("breakeven_cost_bps")
            if be is None or not math.isfinite(float(be)):
                metrics["breakeven_cost_bps"] = _unavailable(
                    str(stats.get("reason") or _ZERO_TURNOVER_REASON)
                )
            else:
                metrics["breakeven_cost_bps"] = _ok(float(be))
            metrics["profitable_after_cost"] = _ok(is_profitable)

        return metrics, True, is_profitable

    def batch_analyze(
        self,
        ic_summary: dict[str, dict],
        turnover_data: dict[str, float],
        factor_return_series: Optional[dict[str, Any]] = None,
    ) -> dict:
        """依 cost_enabled 輸出 §U 三 profile;series owner 回填 net/breakeven/profitable。

        Args:
            ic_summary: feature → {gross_ic|ic_mean, ...}
            turnover_data: feature → scalar quantile turnover(容量/cost_drag 用)
            factor_return_series: feature → FactorTimingReturnSeries(ls_return+position);
                缺/無效 → conditional metrics unavailable(禁 scalar 廣播)。
        """
        series_map = factor_return_series or {}

        if not turnover_data:
            return {
                "skipped": True,
                "reason": "turnover_not_available",
                "features": {},
                "summary": {
                    "total_analyzed": 0,
                    "evaluable_count": 0,
                    "profitable_count": 0,
                },
            }

        feature_results: dict[str, dict] = {}
        cost_drags: list[float] = []
        evaluable_count = 0
        profitable_count = 0

        for feature_name, metric in ic_summary.items():
            if feature_name not in turnover_data:
                feature_results[feature_name] = {
                    "skipped": True,
                    "reason": "turnover_missing",
                }
                continue

            turnover_raw = turnover_data[feature_name]
            try:
                turnover_f = float(turnover_raw)
            except (TypeError, ValueError):
                feature_results[feature_name] = {
                    "skipped": True,
                    "reason": "non_finite_turnover",
                }
                continue

            if not math.isfinite(turnover_f):
                feature_results[feature_name] = {
                    "skipped": True,
                    "reason": "non_finite_turnover",
                }
                continue

            if turnover_f < 0.0:
                # 禁 max(0,·) 靜默 clamp
                feature_results[feature_name] = {
                    "skipped": True,
                    "reason": "negative_turnover",
                }
                continue

            gross_ic = metric.get(
                "gross_ic", metric.get("ic_mean", metric.get("mean_ic", np.nan))
            )
            try:
                gross_f = float(gross_ic)
            except (TypeError, ValueError):
                feature_results[feature_name] = {
                    "skipped": True,
                    "reason": "gross_ic_missing",
                }
                continue

            if not math.isfinite(gross_f):
                feature_results[feature_name] = {
                    "skipped": True,
                    "reason": "gross_ic_missing",
                }
                continue

            volume = metric.get("avg_daily_volume_usd")
            capacity = self._capacity_payload(
                turnover=turnover_f,
                avg_daily_volume_usd=float(volume) if volume is not None else None,
            )

            series_obj = series_map.get(feature_name)

            if not self._cost_enabled:
                # SCHEMA_GROSS_ONLY(無 breakeven/profitable 鍵)
                cond, is_eval, _is_prof = self._series_conditional_metrics(
                    series_obj,
                    cost_bps=None,
                    include_cost_keys=False,
                )
                if is_eval:
                    evaluable_count += 1
                feature_results[feature_name] = {
                    "gross_ic": gross_f,
                    "turnover": turnover_f,
                    "turnover_semantics": _TURNOVER_SEMANTICS,
                    "capacity": capacity,
                    **cond,
                }
                continue

            # SCHEMA_COST_ENABLED
            assert self._cost_bps is not None  # validated in __init__
            cost_bps = float(self._cost_bps)
            drag = self.compute_cost_drag(cost_bps, turnover_f)
            cost_drags.append(drag)
            cond, is_eval, is_prof = self._series_conditional_metrics(
                series_obj,
                cost_bps=cost_bps,
                include_cost_keys=True,
            )
            if is_eval:
                evaluable_count += 1
                if is_prof:
                    profitable_count += 1
            feature_results[feature_name] = {
                "gross_ic": gross_f,
                "turnover": turnover_f,
                "turnover_semantics": _TURNOVER_SEMANTICS,
                "capacity": capacity,
                "cost_bps": cost_bps,
                "cost_semantics": _COST_SEMANTICS,
                "cost_drag_return": drag,
                "cost_sensitivity": self.cost_sensitivity_analysis(cost_bps, turnover_f),
                **cond,
            }

        total_analyzed = sum(
            1 for value in feature_results.values() if not value.get("skipped")
        )
        summary: dict[str, Any] = {
            "total_analyzed": int(total_analyzed),
            "evaluable_count": int(evaluable_count),
            "profitable_count": int(profitable_count),
        }
        if self._cost_enabled:
            summary["avg_cost_drag_return"] = (
                float(np.mean(cost_drags)) if cost_drags else None
            )

        return {
            "features": feature_results,
            "summary": summary,
        }
