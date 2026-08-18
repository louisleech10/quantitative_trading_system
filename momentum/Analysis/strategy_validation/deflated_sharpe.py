"""Task 3.2 — Deflated Sharpe Ratio（`票 GAP-1/C2`；全式寫死；跨 trial 變異數來源二態）。

SPEC ref：Task 3.2 ＋ A1-12（分母單一定義處＝Task 1.2 之 `sr_estimator_variance`；explicit 變異數之 reason）。

  SR0 = √V[{SR_n}] · ((1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e)))，γ=0.5772156649015329；N==1 ⇒ SR0=0
  DSR = Φ( (SR_obs - SR0) / √Var(SR_hat) )，Var(SR_hat)＝`SharpeResult.sr_estimator_variance`（Mertens，per-period）
  ⇒ N==1 時 DSR ≡ PSR（`sr_estimator_variance` 唯一定義處在 sharpe.py，本檔**禁**重算）。

輸入語意鎖死：`period_returns.status != "ok"`（含 `bar_count`／`default_730`）⇒ 傳遞 status／reason、`value=NaN`；
N 只能來自 `LedgerReadResult.n_for_dsr` 或明示 `n_trials`（互斥）；`variance_source` 只決定 SR0 之 V[{SR_n}]。
`n_semantics="adaptive_search"` ⇒ `n_independence="unverified"`（不做 effective-N 換算）。
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Optional

from scipy.stats import norm

from momentum.Analysis.strategy_validation.contract import load_strategy_validation_contract
from momentum.Analysis.strategy_validation.ledger import LedgerReadResult
from momentum.Analysis.strategy_validation.min_btl import InvalidValidationArgument, _validated_status
from momentum.Analysis.strategy_validation.returns_contract import PeriodReturns
from momentum.Analysis.strategy_validation.sharpe import compute_sharpe

_EULER_GAMMA = 0.5772156649015329
_REASON_CROSS_TRIAL_UNAVAILABLE = "cross_trial_variance_unavailable"
_REASON_SNAPSHOT_MISMATCH = "ledger_snapshot_mismatch"
_REASON_DEGENERATE = "degenerate_returns"
_N_INDEPENDENCE_UNVERIFIED = "unverified"
_N_INDEPENDENCE_ASSUMED = "assumed_independent"


@dataclass(frozen=True)
class DSRResult:
    """DSR 結果（退化／不可算時 `value`／`sr0`／`sr_obs_per_period` 為 NaN，status 非 ok）。"""

    value: float
    sr0: float
    sr_obs_per_period: float
    n_trials_used: Optional[int]
    variance_source: str
    n_independence: str
    status: str
    reason: str


def expected_max_sharpe_factor(n_trials: int) -> float:
    """`E[max SR]/√V[SR]` 之解析近似：`(1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))`；N==1 ⇒ 0.0（唯一定義處）。"""
    if n_trials == 1:
        return 0.0
    return (1.0 - _EULER_GAMMA) * float(norm.ppf(1.0 - 1.0 / n_trials)) + _EULER_GAMMA * float(
        norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    )


def _fail(
    *, status: str, reason: str, n: Optional[int], variance_source: str, n_independence: str,
    sr_obs: float = float("nan"),
) -> DSRResult:
    nan = float("nan")
    return DSRResult(
        value=nan,
        sr0=nan,
        sr_obs_per_period=sr_obs,
        n_trials_used=n,
        variance_source=variance_source,
        n_independence=n_independence,
        status=_validated_status(status),
        reason=reason,
    )


def deflated_sharpe(
    *,
    period_returns: PeriodReturns,
    ledger_result: Optional[LedgerReadResult] = None,
    n_trials: Optional[int] = None,
    variance_source: str,
    cross_trial_sr_variance: Optional[float] = None,
    n_semantics: str,
) -> DSRResult:
    """冠軍檢定。

    Raises:
        ValueError: `n_semantics`／`variance_source` 不在契約枚舉；`ledger_result` 與 `n_trials` 皆給或皆缺。
        InvalidValidationArgument: `n_trials` 非 `>=1` 之 int。
    """
    contract = load_strategy_validation_contract()
    if n_semantics not in contract["n_semantics_values"]:
        raise ValueError(f"n_semantics {n_semantics!r} 不在契約 n_semantics_values")
    if variance_source not in contract["variance_source_values"]:
        raise ValueError(f"variance_source {variance_source!r} 不在契約 variance_source_values")
    if (ledger_result is None) == (n_trials is None):
        raise ValueError("ledger_result 與 n_trials 必須恰給其一（互斥；禁 request n_trials 冒充帳本 N）")
    if n_trials is not None and (not isinstance(n_trials, int) or isinstance(n_trials, bool) or n_trials < 1):
        raise InvalidValidationArgument(f"n_trials 須為 >=1 之 int，得到 {n_trials!r}")

    n_independence = (
        _N_INDEPENDENCE_UNVERIFIED if n_semantics == "adaptive_search" else _N_INDEPENDENCE_ASSUMED
    )

    # N：ledger 在場恆取 n_for_dsr（呼叫方無從挑欄位）
    if ledger_result is not None:
        if ledger_result.status != "ok":
            return _fail(
                status=ledger_result.status, reason=ledger_result.reason, n=None,
                variance_source=variance_source, n_independence=n_independence,
            )
        n = int(ledger_result.n_for_dsr)
    else:
        n = int(n_trials)  # type: ignore[arg-type]

    if period_returns.status != "ok":
        return _fail(
            status=period_returns.status, reason=period_returns.reason, n=n,
            variance_source=variance_source, n_independence=n_independence,
        )

    # snapshot 綁定（集合成員測試，非 digest 比對）
    if ledger_result is not None:
        if (
            period_returns.source_artifact_hash not in ledger_result.artifact_hashes
            or len(ledger_result.valid_sharpe_values) > ledger_result.n_valid_metrics
        ):
            return _fail(
                status="unavailable", reason=_REASON_SNAPSHOT_MISMATCH, n=n,
                variance_source=variance_source, n_independence=n_independence,
            )

    sr = compute_sharpe(period_returns.values, periods_per_year=period_returns.periods_per_year)
    if sr.status != "ok" or not math.isfinite(sr.sr_estimator_variance) or sr.sr_estimator_variance <= 0:
        return _fail(
            status="not_computed", reason=_REASON_DEGENERATE, n=n,
            variance_source=variance_source, n_independence=n_independence,
        )
    sr_obs = float(sr.value_per_period)

    # SR0：N==1 ⇒ 0（不需跨 trial 變異數）；否則依 variance_source 取 V[{SR_n}]
    if n == 1:
        sr0 = 0.0
    else:
        if variance_source == "explicit":
            if cross_trial_sr_variance is None:
                return _fail(
                    status="unavailable", reason=_REASON_CROSS_TRIAL_UNAVAILABLE, n=n,
                    variance_source=variance_source, n_independence=n_independence, sr_obs=sr_obs,
                )
            v_cross = float(cross_trial_sr_variance)
        else:  # ledger_cross_trial
            values = () if ledger_result is None else tuple(ledger_result.valid_sharpe_values)
            if len(values) < 2:
                return _fail(
                    status="unavailable", reason=_REASON_CROSS_TRIAL_UNAVAILABLE, n=n,
                    variance_source=variance_source, n_independence=n_independence, sr_obs=sr_obs,
                )
            v_cross = float(statistics.variance(values))
        if not math.isfinite(v_cross) or v_cross <= 0.0:
            return _fail(
                status="not_computed", reason=_REASON_DEGENERATE, n=n,
                variance_source=variance_source, n_independence=n_independence, sr_obs=sr_obs,
            )
        sr0 = math.sqrt(v_cross) * expected_max_sharpe_factor(n)

    stat = (sr_obs - sr0) / math.sqrt(sr.sr_estimator_variance)  # A1-12：分母唯一定義處
    return DSRResult(
        value=float(norm.cdf(stat)),
        sr0=float(sr0),
        sr_obs_per_period=sr_obs,
        n_trials_used=n,
        variance_source=variance_source,
        n_independence=n_independence,
        status=_validated_status("ok"),
        reason="",
    )
