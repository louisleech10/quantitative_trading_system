"""Strategy backtest objective for Optuna."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union

import optuna
import pandas as pd

from momentum.core.logging import get_logger
from momentum.core.protocols import IBacktestEngine, IOptimizationObjective

logger = get_logger(__name__)


class StrategyBacktestObjective(IOptimizationObjective):
    """策略回測參數優化目標。"""

    SUPPORTED_TARGET_METRICS = [
        "expectancy",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "sqn",
    ]

    def __init__(
        self,
        backtest_engine: IBacktestEngine,
        prices: pd.DataFrame,
        predicted_proba: pd.Series,
        atr_values: pd.Series,
        target_metric: str = "expectancy",
        constraints: Optional[Dict[str, float]] = None,
        multi_objective: bool = False,
        timeframe: Optional[str] = None,
        risk_free_rate: float = 0.02,
    ):
        # GAP-1 Task 1.3：年化來源必須從 objective 一路傳到 engine，
        # 否則「策略路徑消除隱性 730」只是存在參數而未生效（SPEC 驗收②b）。
        self.timeframe = timeframe
        self.risk_free_rate = float(risk_free_rate)
        self.backtest_engine = backtest_engine
        self.prices = prices.copy()
        self.predicted_proba = pd.Series(predicted_proba).astype(float)
        self.atr_values = pd.Series(atr_values).astype(float)
        self.target_metric = str(target_metric).strip()
        self.constraints = constraints or {}
        self.multi_objective = multi_objective
        self._current_trial = None

        if self.target_metric not in self.SUPPORTED_TARGET_METRICS:
            raise ValueError(
                f"Unsupported target_metric: {self.target_metric}. "
                f"Options: {self.SUPPORTED_TARGET_METRICS}"
            )

        if len(self.prices) != len(self.predicted_proba):
            raise ValueError(
                f"prices length {len(self.prices)} != "
                f"predicted_proba length {len(self.predicted_proba)}"
            )
        if len(self.prices) != len(self.atr_values):
            raise ValueError(
                f"prices length {len(self.prices)} != "
                f"atr_values length {len(self.atr_values)}"
            )

        if self.predicted_proba.isna().any():
            logger.warning("predicted_proba contains NaN, filling with 0.5")
            self.predicted_proba = self.predicted_proba.fillna(0.5)

        if "timestamp" in self.prices.columns:
            ts = pd.to_datetime(self.prices["timestamp"], errors="coerce")
            if ts.notna().all() and not ts.is_monotonic_increasing:
                logger.warning("timestamp is not monotonic increasing")

    @property
    def name(self) -> str:
        return "strategy_backtest"

    @property
    def direction(self) -> str:
        return "maximize"

    @property
    def directions(self) -> Optional[list[str]]:
        if self.multi_objective:
            return ["maximize", "minimize"]
        return None

    def create_search_space(self, trial: Any) -> Dict[str, Any]:
        self._current_trial = trial
        return {
            "entry_threshold": trial.suggest_float("entry_threshold", 0.5, 0.95, step=0.05),
            "exit_threshold": trial.suggest_float("exit_threshold", 0.3, 0.6, step=0.05),
            "stop_loss_atr": trial.suggest_float("stop_loss_atr", 1.0, 5.0, step=0.5),
            "take_profit_ratio": trial.suggest_float("take_profit_ratio", 1.0, 5.0, step=0.5),
            "position_sizing_method": trial.suggest_categorical(
                "position_sizing_method", ["fixed", "kelly", "probability_scaled"]
            ),
            "kelly_fraction": trial.suggest_float("kelly_fraction", 0.25, 0.75, step=0.05),
            "max_position_size": trial.suggest_float("max_position_size", 0.1, 0.5, step=0.1),
            "cooldown_bars": trial.suggest_int("cooldown_bars", 0, 20, step=5),
            "trailing_stop_activation": trial.suggest_float(
                "trailing_stop_activation", 0.01, 0.10, step=0.01
            ),
        }

    # GAP-1 Task 1.3 / K1：legacy 相容路徑之年化基準（僅在**未宣告** timeframe 時適用）。
    _LEGACY_PERIODS_PER_YEAR = 730

    def _resolve_metrics_periods(self, annualization: Optional[Dict[str, Any]]) -> int:
        """決定 objective 端 metrics 之 `periods_per_year`（fail-loud，禁靜默 730）。

        - `self.timeframe` 已宣告 ⇒ engine **必須**回填 `annualization`（dict、`source=="resolved"`、
          `periods_per_year` 為正整數）；任一不符即 `ValueError`（K1 反例之回歸點）。
        - `self.timeframe is None`（legacy 路徑）⇒ 沿用既有 730，並在缺欄時 warn 一次。
        """
        if self.timeframe is not None:
            if not isinstance(annualization, dict):
                raise ValueError(
                    "objective 已宣告 timeframe，但 engine 未回填 BacktestResult.annualization "
                    f"(got {type(annualization).__name__}) — 拒絕靜默以 730 年化"
                )
            source = annualization.get("source")
            periods = annualization.get("periods_per_year")
            if source != "resolved":
                raise ValueError(
                    f"objective 已宣告 timeframe={self.timeframe!r}，但 annualization['source']={source!r}"
                    " != 'resolved' — 拒絕靜默以 730 年化"
                )
            if not isinstance(periods, int) or isinstance(periods, bool) or periods <= 0:
                raise ValueError(
                    f"annualization['periods_per_year'] 非正整數: {periods!r}"
                )
            return periods

        if not isinstance(annualization, dict) or "periods_per_year" not in annualization:
            logger.warning(
                "BacktestResult 無 annualization 欄；objective 以 legacy %d 年化"
                "（未宣告 timeframe 之相容路徑）",
                self._LEGACY_PERIODS_PER_YEAR,
            )
            return self._LEGACY_PERIODS_PER_YEAR
        periods = annualization.get("periods_per_year", self._LEGACY_PERIODS_PER_YEAR)
        return int(periods) if isinstance(periods, int) and periods > 0 else self._LEGACY_PERIODS_PER_YEAR

    def evaluate(self, params: Dict[str, Any]) -> Union[float, Tuple[float, float]]:
        # GAP-1 Task 1.3：只有在**本 objective 真的被指定 timeframe** 時才傳新參數。
        # 理由：`IBacktestEngine` 之其他實作（含既有測試替身）簽名尚未含 timeframe／risk_free_rate；
        # 無條件傳會使「沒用到 GAP-1 的既有路徑」爆 TypeError。
        # timeframe 有給而引擎不支援 ⇒ TypeError（fail-loud），**不**靜默退回隱性 730。
        extra_kwargs: Dict[str, Any] = {}
        if self.timeframe is not None:
            extra_kwargs["timeframe"] = self.timeframe
            extra_kwargs["risk_free_rate"] = self.risk_free_rate

        result = self.backtest_engine.run_backtest(
            prices=self.prices,
            predicted_proba=self.predicted_proba,
            atr_values=self.atr_values,
            strategy_params=params,
            **extra_kwargs,
        )

        from momentum.Strategy.performance_metrics import PerformanceMetrics  # noqa: PLC0415

        # GAP-1 Task 1.3：periods_per_year 取自 engine 之解析結果（單一來源），不再隱性 730。
        # 🔴 K1（B1 code review：CODEX-R10-P1-03／GROK-R10-P1-01 各以可執行反例推翻 A1-19 之宣稱）：
        #   若 engine 以 **kwargs 吞下 timeframe 卻不回填 annualization，舊寫法
        #   `annualization.get("periods_per_year", 730)` 會**靜默**用 730 年化——這正是 C2 要關的病。
        #   ⇒ 宣告了 timeframe 就**硬性要求**可驗證之 annualization，缺任一條件即 fail-loud。
        periods_per_year = self._resolve_metrics_periods(getattr(result, "annualization", None))
        metrics = PerformanceMetrics(
            result.equity_curve,
            result.trades,
            risk_free_rate=self.risk_free_rate,
            periods_per_year=periods_per_year,
        ).calculate_all()
        self._record_trial_metrics(metrics)
        self._apply_constraints(metrics)

        target_value = float(metrics.get(self.target_metric, 0.0))
        if self.multi_objective:
            max_drawdown_abs = abs(float(metrics.get("max_drawdown", 0.0)))
            return target_value, max_drawdown_abs
        return target_value

    def get_pruning_callback(self, trial: Any) -> Optional[Any]:
        return None

    def _apply_constraints(self, metrics: Dict[str, float]) -> None:
        max_drawdown_limit = float(self.constraints.get("max_drawdown", -0.30))
        min_win_rate = float(self.constraints.get("min_win_rate", 0.40))
        min_trades = float(self.constraints.get("min_trades", 10))

        max_drawdown = float(metrics.get("max_drawdown", 0.0))
        win_rate = float(metrics.get("win_rate", 0.0))
        total_trades = float(metrics.get("total_trades", 0.0))

        if max_drawdown < max_drawdown_limit:
            raise optuna.TrialPruned(
                f"max_drawdown {max_drawdown:.4f} < threshold {max_drawdown_limit:.4f}"
            )
        if win_rate < min_win_rate:
            raise optuna.TrialPruned(f"win_rate {win_rate:.4f} < threshold {min_win_rate:.4f}")
        if total_trades < min_trades:
            raise optuna.TrialPruned(
                f"total_trades {total_trades:.0f} < threshold {min_trades:.0f}"
            )

    def _record_trial_metrics(self, metrics: Dict[str, float]) -> None:
        if self._current_trial is None:
            return
        for key, value in metrics.items():
            try:
                self._current_trial.set_user_attr(key, float(value))
            except (TypeError, ValueError):
                self._current_trial.set_user_attr(key, value)
