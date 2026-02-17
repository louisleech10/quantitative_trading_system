"""Module 10: Net IC analyzer."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class NetICAnalyzer:
    def __init__(self, config: dict):
        cfg = config or {}
        self._config = cfg
        self._default_cost_bps = float(cfg.get("default_cost_bps", 5.0))
        self._cost_scenarios = list(cfg.get("cost_scenarios", [1, 3, 5, 10, 20]))
        self._participation_rate = float(cfg.get("participation_rate", 0.01))

    def compute_net_ic(
        self,
        gross_ic: float,
        turnover: float,
        cost_bps: Optional[float] = None,
    ) -> dict:
        use_cost = float(self._default_cost_bps if cost_bps is None else cost_bps)
        gross_ic_value = float(gross_ic)
        turnover_value = max(0.0, float(turnover))
        net_ic = gross_ic_value - (use_cost / 10000.0) * turnover_value * 2.0
        return {
            "gross_ic": gross_ic_value,
            "net_ic": float(net_ic),
            "turnover": turnover_value,
            "cost_bps": use_cost,
            "profitable_after_cost": bool(net_ic > 0),
            "breakeven_cost_bps": float((gross_ic_value * 10000.0) / (turnover_value * 2.0)) if turnover_value > 0 else np.inf,
        }

    def compute_net_factor_return(
        self,
        gross_return_series: pd.Series,
        turnover_series: pd.Series,
        cost_bps: Optional[float] = None,
    ) -> dict:
        use_cost = float(self._default_cost_bps if cost_bps is None else cost_bps)
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

        cost_term = (use_cost / 10000.0) * aligned["turnover"].astype(float) * 2.0
        net_series = aligned["gross"].astype(float) - cost_term
        return {
            "net_return_series": net_series.astype(float).tolist(),
            "gross_mean": float(aligned["gross"].mean()),
            "net_mean": float(net_series.mean()),
            "cost_drag": float((aligned["gross"].mean() - net_series.mean())),
        }

    def cost_sensitivity_analysis(
        self,
        gross_ic: float,
        turnover: float,
        scenarios: Optional[list[float]] = None,
    ) -> dict:
        cost_scenarios = scenarios or self._cost_scenarios
        rows = []
        for scenario_cost in cost_scenarios:
            result = self.compute_net_ic(gross_ic, turnover, cost_bps=float(scenario_cost))
            rows.append({
                "cost_bps": float(scenario_cost),
                "net_ic": float(result["net_ic"]),
            })
        return {
            "scenarios": rows,
        }

    def estimate_factor_capacity(
        self,
        turnover: float,
        avg_daily_volume_usd: Optional[float] = None,
        participation_rate: float = 0.01,
    ) -> dict:
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

    def batch_analyze(
        self,
        ic_summary: dict[str, dict],
        turnover_data: dict[str, float],
        factor_returns: Optional[dict[str, pd.Series]] = None,
    ) -> dict:
        if not turnover_data:
            return {
                "skipped": True,
                "reason": "turnover_not_available",
                "features": {},
                "summary": {
                    "total_analyzed": 0,
                    "profitable_count": 0,
                    "avg_ic_loss_pct": np.nan,
                    "rank_correlation_gross_vs_net": np.nan,
                },
            }

        feature_results: dict[str, dict] = {}
        gross_values: list[float] = []
        net_values: list[float] = []

        for feature_name, metric in ic_summary.items():
            turnover = turnover_data.get(feature_name)
            if turnover is None:
                feature_results[feature_name] = {
                    "skipped": True,
                    "reason": "turnover_missing",
                }
                continue

            gross_ic = metric.get("gross_ic", metric.get("ic_mean", metric.get("mean_ic", np.nan)))
            if not np.isfinite(float(gross_ic)):
                feature_results[feature_name] = {
                    "skipped": True,
                    "reason": "gross_ic_missing",
                }
                continue

            net_result = self.compute_net_ic(float(gross_ic), float(turnover))
            net_result["cost_sensitivity"] = self.cost_sensitivity_analysis(
                gross_ic=float(gross_ic),
                turnover=float(turnover),
            )["scenarios"]

            volume = metric.get("avg_daily_volume_usd")
            net_result["capacity"] = self.estimate_factor_capacity(
                turnover=float(turnover),
                avg_daily_volume_usd=float(volume) if volume is not None else None,
                participation_rate=self._participation_rate,
            )

            if factor_returns and feature_name in factor_returns:
                gross_series = factor_returns[feature_name]
                turnover_series = pd.Series(float(turnover), index=gross_series.index)
                net_result["net_factor_return"] = self.compute_net_factor_return(
                    gross_series,
                    turnover_series,
                )

            feature_results[feature_name] = net_result
            gross_values.append(float(net_result["gross_ic"]))
            net_values.append(float(net_result["net_ic"]))

        profitable_count = sum(
            1
            for value in feature_results.values()
            if isinstance(value, dict) and not value.get("skipped") and value.get("profitable_after_cost")
        )
        total_analyzed = sum(1 for value in feature_results.values() if not value.get("skipped"))

        ic_loss_pct = []
        for value in feature_results.values():
            if value.get("skipped"):
                continue
            gross_ic = float(value["gross_ic"])
            net_ic = float(value["net_ic"])
            if gross_ic != 0:
                ic_loss_pct.append((gross_ic - net_ic) / abs(gross_ic) * 100.0)

        rank_corr = np.nan
        if len(gross_values) >= 2 and len(net_values) >= 2:
            corr = spearmanr(np.array(gross_values), np.array(net_values)).correlation
            rank_corr = float(corr) if np.isfinite(corr) else np.nan

        return {
            "features": feature_results,
            "summary": {
                "total_analyzed": int(total_analyzed),
                "profitable_count": int(profitable_count),
                "avg_ic_loss_pct": float(np.mean(ic_loss_pct)) if ic_loss_pct else np.nan,
                "rank_correlation_gross_vs_net": rank_corr,
            },
        }
