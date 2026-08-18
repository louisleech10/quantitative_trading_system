"""Task 1.2 — typed Sharpe（退化情形回 NaN＋status，非 0.0）。

SPEC ref：Task 1.2。單位鎖定（[A-單位]）：`skew`／`kurtosis`／`sr_estimator_variance`
一律以 **per-period** 報酬計算；`value_annualized` 僅供展示，禁代入 DSR 檢定統計量。
status 值直接取 IC 契約枚舉（`ic_report_contract.json#capability_status`），不複列。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats as _scipy_stats

from momentum.Analysis.ic_config_schema import contract_enum

_STATUS_OK = "ok"
_STATUS_NOT_COMPUTED = "not_computed"
_REASON_DEGENERATE = "degenerate_returns"


def _validated_status(status: str) -> str:
    """status 必須屬 IC 契約之 capability_status（唯一來源；本檔不複列六值）。"""
    allowed = contract_enum("capability_status")
    if status not in allowed:
        raise ValueError(f"status {status!r} not in capability_status contract")
    return status


@dataclass(frozen=True)
class SharpeResult:
    """三關共用之 typed Sharpe 結果（退化時數值欄皆 NaN，status 非 ok）。"""

    value_per_period: float
    value_annualized: float
    status: str
    reason: str
    n_obs: int
    periods_per_year: int
    skew: float
    kurtosis: float
    sr_estimator_variance: float


def _degenerate(periods_per_year: int, n_obs: int) -> SharpeResult:
    nan = float("nan")
    return SharpeResult(
        value_per_period=nan,
        value_annualized=nan,
        status=_validated_status(_STATUS_NOT_COMPUTED),
        reason=_REASON_DEGENERATE,
        n_obs=n_obs,
        periods_per_year=periods_per_year,
        skew=nan,
        kurtosis=nan,
        sr_estimator_variance=nan,
    )


def compute_sharpe(
    returns,
    *,
    periods_per_year: int,
    risk_free_rate: float = 0.0,
) -> SharpeResult:
    """自算觀測 Sharpe；退化一律 NaN＋status 非 ok（**不**提供回 0.0 之相容模式）。

    Args:
        returns: 1D per-period 報酬序列（ndarray／Series／list 皆可）。
        periods_per_year: 必填關鍵字；由 Task 1.1 之 `resolve_periods_per_year` 取得。
        risk_free_rate: 年化無風險利率（預設 0.0；內部以 `rf/periods_per_year` 換算為 per-period）。

    Returns:
        `SharpeResult`。退化條件：`n_obs < 2`／含 NaN·inf／`std(ddof=1) == 0`。

    Raises:
        ValueError: `periods_per_year <= 0`。
    """
    if periods_per_year <= 0:
        raise ValueError(f"periods_per_year must be > 0, got {periods_per_year}")

    values = np.asarray(returns, dtype=float).ravel()
    n_obs = int(values.size)

    if n_obs < 2 or not np.all(np.isfinite(values)):
        return _degenerate(periods_per_year, n_obs)

    std = float(values.std(ddof=1))
    # 常數序列 ⇒ 退化：`std == 0.0` 之精確比對對「非二進位可精確表示之常數」（如 80×0.01）會因求和捨入得 std≈1e-18 而漏判
    # ⇒ 併判 `np.ptp(values) == 0.0`（輸入元素**位元全等**；G1-R11／consult r20 三家一致：不引入相對容差，
    #   「近常數微擾」之巨大 SR 為數學上正確；`ptp==0` 只辨識編碼值相等，不保證跨異源浮點表達式之數學相等）。
    if std == 0.0 or not np.isfinite(std) or float(np.ptp(values)) == 0.0:
        return _degenerate(periods_per_year, n_obs)

    sr_pp = (float(values.mean()) - risk_free_rate / periods_per_year) / std
    skew = float(_scipy_stats.skew(values))
    kurtosis = float(_scipy_stats.kurtosis(values, fisher=False))
    # Mertens 估計量變異數（§G；per-period，供 DSR 檢定統計量之分母；此為唯一定義處）
    sr_var = (1.0 - skew * sr_pp + (kurtosis - 1.0) / 4.0 * sr_pp**2) / (n_obs - 1)

    return SharpeResult(
        value_per_period=sr_pp,
        value_annualized=sr_pp * float(np.sqrt(periods_per_year)),
        status=_validated_status(_STATUS_OK),
        reason="",
        n_obs=n_obs,
        periods_per_year=periods_per_year,
        skew=skew,
        kurtosis=kurtosis,
        sr_estimator_variance=sr_var,
    )
