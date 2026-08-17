"""Task 1.4 — canonical 報酬序列與 T 語意契約（三關唯一合法輸入口）。

SPEC ref：Task 1.4 ＋ A1-6（`t_semantics` 為必填參數）。
DSR 只接 `trade_level` 與 `nonzero_return_bars`；`bar_count` 一律 `not_applicable`
（結構性 0 會膨脹 `√(T-1)`），值仍回傳供診斷。
`annualization_source != "resolved"` 或缺 `annualization` 欄 ⇒ status 非 ok（**禁**假設 730）。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from momentum.Analysis.ic_config_schema import contract_enum
from momentum.core.frequency import available_years, resolve_periods_per_year

T_SEMANTICS_BAR_COUNT = "bar_count"
T_SEMANTICS_NONZERO = "nonzero_return_bars"
T_SEMANTICS_TRADE_LEVEL = "trade_level"
_T_SEMANTICS_VALUES = (T_SEMANTICS_BAR_COUNT, T_SEMANTICS_NONZERO, T_SEMANTICS_TRADE_LEVEL)

_REASON_ANNUALIZATION_UNRESOLVED = "annualization_unresolved"
_REASON_T_SEMANTICS_INFLATES = "t_semantics_inflates_significance"


def _validated_status(status: str) -> str:
    allowed = contract_enum("capability_status")
    if status not in allowed:
        raise ValueError(f"status {status!r} not in capability_status contract")
    return status


@dataclass(frozen=True)
class PeriodReturns:
    """三關唯一合法輸入序列＋其 T 語意與來源綁定。"""

    values: np.ndarray
    t_semantics: str
    n_obs: int
    periods_per_year: float
    annualization_source: str
    source_artifact_hash: str
    status: str
    reason: str


def _artifact_hash(backtest_result: Any) -> str:
    """對產生該序列之 `BacktestResult` 取 sha256（供 DSR 之 ledger snapshot membership 測試）。

    演算法寫死於本檔（唯一定義處）：equity 值之 raw bytes ＋ 逐筆交易之
    `(entry_time, exit_time, pnl_pct)` 三元組之 repr。
    """
    digest = hashlib.sha256()
    equity = getattr(backtest_result, "equity_curve", None)
    if equity is not None:
        arr = np.asarray(getattr(equity, "values", equity), dtype=float)
        digest.update(np.ascontiguousarray(arr).tobytes())
    trades = getattr(backtest_result, "trades", []) or []
    for trade in trades:
        triple = (
            getattr(trade, "entry_time", None),
            getattr(trade, "exit_time", None),
            getattr(trade, "pnl_pct", None),
        )
        digest.update(repr(triple).encode("utf-8"))
    return digest.hexdigest()


def _bar_returns(backtest_result: Any) -> np.ndarray:
    equity = getattr(backtest_result, "equity_curve", None)
    if equity is None:
        return np.asarray([], dtype=float)
    series = equity if isinstance(equity, pd.Series) else pd.Series(np.asarray(equity, dtype=float))
    return series.astype(float).pct_change().dropna().to_numpy(dtype=float)


def _unavailable(
    values: np.ndarray,
    t_semantics: str,
    periods_per_year: float,
    annualization_source: str,
    artifact_hash: str,
    reason: str,
    status: str = "not_computed",
) -> PeriodReturns:
    return PeriodReturns(
        values=values,
        t_semantics=t_semantics,
        n_obs=int(values.size),
        periods_per_year=periods_per_year,
        annualization_source=annualization_source,
        source_artifact_hash=artifact_hash,
        status=_validated_status(status),
        reason=reason,
    )


def extract_period_returns(
    backtest_result: Any,
    *,
    timeframe: str,
    t_semantics: str,
) -> PeriodReturns:
    """由 `BacktestResult` 提取三關之 canonical 報酬序列。

    Args:
        backtest_result: `momentum.Strategy.vectorized_backtest.BacktestResult`（需含 Task 1.3 之
            `annualization` 欄；缺該欄 ⇒ `annualization_unresolved`，**不**假設 730）。
        timeframe: 由呼叫方提供（本函式不自行推導）。
        t_semantics: 必填，值集合＝`bar_count`／`nonzero_return_bars`／`trade_level`。

    Returns:
        `PeriodReturns`。

    Raises:
        ValueError: `t_semantics` 不在值集合內。
        UnknownTimeframeError: `timeframe` 未知（自 Task 1.1 向上拋）。
    """
    if t_semantics not in _T_SEMANTICS_VALUES:
        raise ValueError(
            f"t_semantics must be one of {_T_SEMANTICS_VALUES}, got {t_semantics!r}"
        )

    artifact_hash = _artifact_hash(backtest_result)
    annualization = getattr(backtest_result, "annualization", None)
    ppy_timeframe = resolve_periods_per_year(timeframe)  # 未知 timeframe ⇒ raise（fail-closed）

    if not isinstance(annualization, dict) or "source" not in annualization:
        return _unavailable(
            np.asarray([], dtype=float),
            t_semantics,
            float(ppy_timeframe),
            "",
            artifact_hash,
            _REASON_ANNUALIZATION_UNRESOLVED,
        )

    source = str(annualization.get("source", ""))
    bar_returns = _bar_returns(backtest_result)

    if t_semantics == T_SEMANTICS_TRADE_LEVEL:
        trades = getattr(backtest_result, "trades", []) or []
        values = np.asarray(
            [float(getattr(t, "pnl_pct", float("nan"))) for t in trades], dtype=float
        )
        years = available_years(n_bars=int(bar_returns.size) + 1, timeframe=timeframe)
        periods_per_year = float(values.size / years) if years > 0 else 0.0
    else:
        values = bar_returns if t_semantics == T_SEMANTICS_BAR_COUNT else bar_returns[bar_returns != 0.0]
        periods_per_year = float(ppy_timeframe)

    if source != "resolved":
        return _unavailable(
            values,
            t_semantics,
            periods_per_year,
            source,
            artifact_hash,
            _REASON_ANNUALIZATION_UNRESOLVED,
        )

    if t_semantics == T_SEMANTICS_BAR_COUNT:
        # 值仍回傳供診斷，但三關不得消費（結構性 0 膨脹 √(T-1)）。
        return _unavailable(
            values,
            t_semantics,
            periods_per_year,
            source,
            artifact_hash,
            _REASON_T_SEMANTICS_INFLATES,
            status="not_applicable",
        )

    return PeriodReturns(
        values=values,
        t_semantics=t_semantics,
        n_obs=int(values.size),
        periods_per_year=periods_per_year,
        annualization_source=source,
        source_artifact_hash=artifact_hash,
        status=_validated_status("ok"),
        reason="",
    )
