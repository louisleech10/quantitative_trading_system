"""Task 3.1 — MinBTL 上界、試驗預算與資格三態（`票 GAP-1/C5`）。

SPEC ref：Task 3.1 ＋ A1-5（簽名／overflow）／A1-9（保守性 oracle）／A1-16（`InvalidValidationArgument`）。

公式（全式寫死，**不**提供調常數之參數）：
  `min_btl_years_upper_bound(N, SR*) = 2·ln(N) / SR*²`（N==1 ⇒ 0.0）
  `max_trials_budget(T, SR*)         = floor(exp(T·SR*²/2))`（`x = T·SR*²/2 > 700` ⇒ raise，禁 cap）
語意：上界＝「想宣稱 SR* 至少要幾年」，**不是**精確最短長度；`t_years` 固定為年，不以頻率折抵。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from momentum.Analysis.ic_config_schema import contract_enum
from momentum.Analysis.strategy_validation.contract import load_strategy_validation_contract
from momentum.Analysis.strategy_validation.ledger import LedgerReadResult

_EXP_ARG_LIMIT = 700.0  # A1-5：`math.exp(710)` 即 OverflowError；超過視為無物理意義輸入 ⇒ raise（禁 cap）
_N_SOURCE_LEDGER = "ledger"
_N_SOURCE_LEDGER_UNAVAILABLE = "ledger_unavailable"


class InvalidValidationArgument(ValueError):
    """呼叫方傳入非法參數（`n_trials<1`／`target_sharpe<=0`／`t_years<=0`／`exp` 引數 >700）。

    為 `ValueError` 子類 ⇒ 既有 `except ValueError` 語意不變；reporter（A1-16）**不**捕獲本例外，
    使呼叫方 bug 以 5xx 可觀測，而非被吞成 `reporter_failed`。
    """


def _validated_status(status: str) -> str:
    """status 必須屬 IC 契約之 capability_status（唯一來源；本檔不複列六值）。"""
    allowed = contract_enum("capability_status")
    if status not in allowed:
        raise ValueError(f"status {status!r} not in capability_status contract")
    return status


def _validated_n_source(n_source: str) -> str:
    """`n_source` 必須屬策略契約 `n_source_values`（A1-22；禁自創字面；loader 枚舉對映亦於 report 側再驗）。"""
    allowed = load_strategy_validation_contract()["n_source_values"]
    if n_source not in allowed:
        raise ValueError(f"n_source {n_source!r} not in contract n_source_values {allowed}")
    return n_source


@dataclass(frozen=True)
class EligibilityResult:
    """資格三態（`eligible ∈ {True, False, None}`）；欄位＝契約 `eligibility_keys` 之子集＋`status`／`reason`。

    `display_downgrade`／`warning_text_key` 由 Task 3.3 `build_validation_section` 決定，不在本型別。
    **禁**新增契約 `eligibility_keys` 以外之欄（A1-5 第 3 點；`budget_capped` 已刪）。
    """

    eligible: Optional[bool]
    required_years_upper_bound: Optional[float]
    available_years: Optional[float]
    trials_budget: Optional[int]
    trials_used: Optional[int]
    target_sharpe: Optional[float]
    n_source: str
    status: str
    reason: str


def _check_positive(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise InvalidValidationArgument(f"{name} 須為有限正數，得到 {value!r}")


def min_btl_years_upper_bound(*, n_trials: int, target_sharpe: float) -> float:
    """MinBTL 上界（年）：`2·ln(n_trials)/target_sharpe²`；`n_trials==1 ⇒ 0.0`。

    Raises:
        InvalidValidationArgument: `n_trials < 1`（或非 int）／`target_sharpe <= 0`。
    """
    if not isinstance(n_trials, int) or isinstance(n_trials, bool) or n_trials < 1:
        raise InvalidValidationArgument(f"n_trials 須為 >=1 之 int，得到 {n_trials!r}")
    _check_positive("target_sharpe", target_sharpe)
    if n_trials == 1:
        return 0.0
    return 2.0 * math.log(n_trials) / (float(target_sharpe) ** 2)


def max_trials_budget(*, t_years: float, target_sharpe: float) -> int:
    """給定資料長度 T（年）最多准試幾個候選：`floor(exp(T·SR²/2))`（**floor**，非 round）。

    Raises:
        InvalidValidationArgument: `t_years <= 0`／`target_sharpe <= 0`／`x = T·SR²/2 > 700`（A1-5：禁 cap）。
    """
    _check_positive("t_years", t_years)
    _check_positive("target_sharpe", target_sharpe)
    x = float(t_years) * float(target_sharpe) ** 2 / 2.0
    if x > _EXP_ARG_LIMIT:
        raise InvalidValidationArgument(
            f"t_years*target_sharpe**2/2 = {x!r} > {_EXP_ARG_LIMIT}（exp 溢位；該輸入無物理意義，禁 cap）"
        )
    return int(math.floor(math.exp(x)))


def assess_eligibility(
    *, t_years: float, ledger_result: LedgerReadResult, target_sharpe: float
) -> EligibilityResult:
    """資格三態：N 只能來自 Task 2.2 之 `LedgerReadResult`（禁 request `n_trials` 冒充）。

    - `ledger_result.status != "ok"` ⇒ `eligible=None`、status／reason **傳遞**、`trials_used=None`、
      `required_years_upper_bound=None`（N 不可知）、`n_source="ledger_unavailable"`；
    - 否則 `trials_used = n_for_dsr`、`required = min_btl_years_upper_bound(n_for_dsr, SR*)`、
      `eligible = required <= t_years`、`n_source="ledger"`。
    `trials_budget = max_trials_budget(t_years, SR*)`、`available_years = t_years` 兩態皆算。

    Raises:
        InvalidValidationArgument: `t_years <= 0`／`target_sharpe <= 0`／預算 `exp` 溢位（呼叫方 bug，**不**正規化）。
    """
    _check_positive("t_years", t_years)
    _check_positive("target_sharpe", target_sharpe)
    budget = max_trials_budget(t_years=t_years, target_sharpe=target_sharpe)

    if ledger_result.status != "ok":
        return EligibilityResult(
            eligible=None,
            required_years_upper_bound=None,
            available_years=float(t_years),
            trials_budget=budget,
            trials_used=None,
            target_sharpe=float(target_sharpe),
            n_source=_validated_n_source(_N_SOURCE_LEDGER_UNAVAILABLE),
            status=_validated_status(ledger_result.status),
            reason=ledger_result.reason,
        )

    n = int(ledger_result.n_for_dsr)
    required = min_btl_years_upper_bound(n_trials=n, target_sharpe=target_sharpe)
    return EligibilityResult(
        eligible=bool(required <= float(t_years)),
        required_years_upper_bound=required,
        available_years=float(t_years),
        trials_budget=budget,
        trials_used=n,
        target_sharpe=float(target_sharpe),
        n_source=_validated_n_source(_N_SOURCE_LEDGER),
        status=_validated_status("ok"),
        reason="",
    )
