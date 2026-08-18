"""Task 3.3 — 報告區段與降級展示契約（`票 GAP-1/C4`）。

SPEC ref：Task 3.3 ＋ A1-4（`universe_scope` 強制降級）／A1-13（五節必填鍵）／A1-17（組裝寫法受限）。

輸出＝五節（`eligibility`／`min_btl`／`dsr`／`pbo`／`provenance`）＋頂層 `display_downgrade`／`warning_text_key`
（頂層鍵集合 ⊆ 契約 `report_sections` 節名 ∪ `eligibility_keys`；**無**任何推薦類鍵）。
降級規則：`all_ok = eligible is True ∧ min_btl／dsr／pbo 三節 status=="ok"`；`display_downgrade = not all_ok`；
`pbo.universe_scope=="ledger_recorded_only"` ⇒ **強制**降級（即使 all_ok；候選宇宙完整性未經生產者證明，G1-R9）；
`eligibility.n_source=="assumed_not_ledgered"` ⇒ 強制 `eligible=None`。

🔴 A1-17：本檔 `build_validation_section` **必須在自身函式頂層以字面鍵**組裝五節與 `eligibility` 九鍵
（Task 2.4 wiring 閘只認頂層無條件字面鍵）；**禁** helper／迴圈變數鍵／`setattr`／`dict(**kwargs)` 組裝。
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from momentum.Analysis.strategy_validation.contract import validate_against_contract
from momentum.Analysis.strategy_validation.deflated_sharpe import DSRResult
from momentum.Analysis.strategy_validation.min_btl import EligibilityResult

# 唯一定義處（key 非文案；reporter.py 須 import 之，禁第二處字面）
WARNING_TEXT_KEY = "strategy_validation.downgraded"

_STATUS_OK = "ok"
_STATUS_NOT_COMPUTED = "not_computed"
_REASON_N_UNKNOWN = "n_unknown"
_N_SOURCE_ASSUMED = "assumed_not_ledgered"
_UNIVERSE_SCOPE_LEDGER_ONLY = "ledger_recorded_only"


def _finite_or_none(value: Any) -> Optional[float]:
    """數值欄：非有限（NaN／±inf）⇒ None（契約 `float|null`；JSON 不得含 NaN）。"""
    if value is None:
        return None
    v = float(value)
    return v if math.isfinite(v) else None


def build_validation_section(
    *,
    eligibility: EligibilityResult,
    dsr: Optional[DSRResult],
    pbo: Optional[Any],
    provenance: Dict[str, Any],
) -> Dict[str, Any]:
    """組五節＋降級旗標；每節通過 `validate_against_contract`（不通過即 raise `ContractViolation`）。

    Args:
        eligibility: Task 3.1 結果。
        dsr: Task 3.2 結果；`None` ⇒ 節 `status="not_computed"`、`reason="n_unknown"`。
        pbo: Task 4.2 `PBOResult`（duck-typed：`value`／`n_paths_used`／`n_paths_skipped`／`n_candidates_invalid`／
            `universe_scope`／`status`／`reason`）；`None` 同上。
        provenance: `n_semantics`／`t_semantics`／`annualization_source`／`n_independence`／`status`／`reason`
            （缺鍵 ⇒ `None`／`status="not_computed"`）。
    """
    eligible = None if eligibility.n_source == _N_SOURCE_ASSUMED else eligibility.eligible

    min_btl_status = eligibility.status
    dsr_status = _STATUS_NOT_COMPUTED if dsr is None else dsr.status
    pbo_status = _STATUS_NOT_COMPUTED if pbo is None else pbo.status
    pbo_universe_scope = None if pbo is None else pbo.universe_scope

    all_ok = (
        eligible is True
        and min_btl_status == _STATUS_OK
        and dsr_status == _STATUS_OK
        and pbo_status == _STATUS_OK
    )
    forced_by_universe_scope = pbo_universe_scope == _UNIVERSE_SCOPE_LEDGER_ONLY  # A1-4
    display_downgrade = (not all_ok) or forced_by_universe_scope
    warning_text_key = WARNING_TEXT_KEY if display_downgrade else ""

    out = {
        "eligibility": {
            "eligible": eligible,
            "required_years_upper_bound": _finite_or_none(eligibility.required_years_upper_bound),
            "available_years": _finite_or_none(eligibility.available_years),
            "trials_budget": eligibility.trials_budget,
            "trials_used": eligibility.trials_used,
            "target_sharpe": _finite_or_none(eligibility.target_sharpe),
            "n_source": eligibility.n_source,
            "display_downgrade": display_downgrade,
            "warning_text_key": warning_text_key,
            "status": eligibility.status,
            "reason": eligibility.reason,
        },
        "min_btl": {
            "status": min_btl_status,
            "reason": eligibility.reason,
            "required_years_upper_bound": _finite_or_none(eligibility.required_years_upper_bound),
            "available_years": _finite_or_none(eligibility.available_years),
            "trials_budget": eligibility.trials_budget,
            "trials_used": eligibility.trials_used,
            "target_sharpe": _finite_or_none(eligibility.target_sharpe),
        },
        "dsr": {
            "status": dsr_status,
            "reason": _REASON_N_UNKNOWN if dsr is None else dsr.reason,
            "value": None if dsr is None else _finite_or_none(dsr.value),
            "sr0": None if dsr is None else _finite_or_none(dsr.sr0),
            "sr_obs_per_period": None if dsr is None else _finite_or_none(dsr.sr_obs_per_period),
            "n_trials_used": None if dsr is None else dsr.n_trials_used,
            "variance_source": None if dsr is None else dsr.variance_source,
            "n_independence": None if dsr is None else dsr.n_independence,
        },
        "pbo": {
            "status": pbo_status,
            "reason": _REASON_N_UNKNOWN if pbo is None else pbo.reason,
            "value": None if pbo is None else _finite_or_none(pbo.value),
            "n_paths_used": None if pbo is None else pbo.n_paths_used,
            "n_paths_skipped": None if pbo is None else pbo.n_paths_skipped,
            "n_candidates_invalid": None if pbo is None else pbo.n_candidates_invalid,
            "universe_scope": pbo_universe_scope,
        },
        "provenance": {
            "status": provenance.get("status", _STATUS_NOT_COMPUTED),
            "reason": provenance.get("reason", ""),
            "n_semantics": provenance.get("n_semantics"),
            "t_semantics": provenance.get("t_semantics"),
            "annualization_source": provenance.get("annualization_source"),
            "n_independence": provenance.get("n_independence"),
        },
        "display_downgrade": display_downgrade,
        "warning_text_key": warning_text_key,
    }
    validate_against_contract(out["eligibility"], "eligibility")
    validate_against_contract(out["min_btl"], "min_btl")
    validate_against_contract(out["dsr"], "dsr")
    validate_against_contract(out["pbo"], "pbo")
    validate_against_contract(out["provenance"], "provenance")
    return out
