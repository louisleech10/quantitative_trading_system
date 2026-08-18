"""Task 3.3 驗證：eligibility 三態 × 三關 ok/非 ok ＝ 24 案例；A1-4 universe_scope 強制降級；dsr/pbo=None 誠實路徑。"""

import itertools
from dataclasses import dataclass
from typing import Optional

import pytest

from momentum.Analysis.strategy_validation.contract import (
    ContractViolation,
    load_strategy_validation_contract,
    validate_against_contract,
)
from momentum.Analysis.strategy_validation.deflated_sharpe import DSRResult
from momentum.Analysis.strategy_validation.min_btl import EligibilityResult
from momentum.Analysis.strategy_validation.report import WARNING_TEXT_KEY, build_validation_section


@dataclass(frozen=True)
class _FakePBO:
    """B4 PBOResult 之 duck type（七欄）。"""

    value: Optional[float]
    n_paths_used: Optional[int]
    n_paths_skipped: Optional[int]
    n_candidates_invalid: Optional[int]
    universe_scope: Optional[str]
    status: str
    reason: str


def _elig(state, *, min_btl_ok=True, n_source="ledger"):
    """eligible 三態 × min_btl 節 ok/非 ok（status 欄）；min_btl 非 ok 以 status='unavailable' 表示。"""
    status, reason = ("ok", "") if min_btl_ok else ("unavailable", "n_unknown")
    if state is True:
        return EligibilityResult(True, 2.0, 5.0, 12, 4, 1.0, n_source, status, reason)
    if state is False:
        return EligibilityResult(False, 9.2, 2.3, 3, 100, 1.0, n_source, status, reason)
    return EligibilityResult(None, None, 2.3, 3, None, 1.0, "ledger_unavailable", status, reason)


def _dsr(ok):
    if ok:
        return DSRResult(0.97, 0.01, 0.05, 10, "explicit", "assumed_independent", "ok", "")
    return DSRResult(float("nan"), float("nan"), float("nan"), 10, "explicit", "assumed_independent", "unavailable", "cross_trial_variance_unavailable")


def _pbo(ok, universe_scope=None):
    if ok:
        return _FakePBO(0.12, 924, 0, 0, universe_scope, "ok", "")
    return _FakePBO(None, 0, 924, 0, universe_scope, "not_computed", "all_paths_degenerate")


def _prov():
    return {
        "status": "ok",
        "reason": "",
        "n_semantics": "exhaustive_grid",
        "t_semantics": "trade_level",
        "annualization_source": "resolved",
        "n_independence": "assumed_independent",
    }


_MATRIX = list(itertools.product([True, False, None], [True, False], [True, False], [True, False]))
assert len(_MATRIX) == 24


@pytest.mark.parametrize("elig_state, min_btl_ok, dsr_ok, pbo_ok", _MATRIX)
def test_downgrade_matrix_24_cases(elig_state, min_btl_ok, dsr_ok, pbo_ok):
    """①②③④：僅「eligible True 且三關 ok」不降級；其餘 23 例降級＋警語鍵非空；輸出鍵 ⊆ allowlist；五節過契約。"""
    elig = _elig(elig_state, min_btl_ok=min_btl_ok)
    out = build_validation_section(eligibility=elig, dsr=_dsr(dsr_ok), pbo=_pbo(pbo_ok), provenance=_prov())
    expect_no_downgrade = elig_state is True and min_btl_ok and dsr_ok and pbo_ok
    if expect_no_downgrade:
        assert out["display_downgrade"] is False
        assert out["warning_text_key"] == ""
        assert out["eligibility"]["display_downgrade"] is False
    else:
        assert out["display_downgrade"] is True
        assert len(out["warning_text_key"]) > 0
        assert out["warning_text_key"] == WARNING_TEXT_KEY
        assert out["eligibility"]["warning_text_key"] == WARNING_TEXT_KEY
    contract = load_strategy_validation_contract()
    allow = set(contract["eligibility_keys"]) | {
        k for k in contract["report_sections"] if not k.startswith("_")
    }
    assert set(out) <= allow, set(out) - allow
    for name in ("eligibility", "min_btl", "dsr", "pbo", "provenance"):
        validate_against_contract(out[name], name)  # 不 raise
    assert out["min_btl"]["status"] == elig.status
    assert out["dsr"]["status"] == ("ok" if dsr_ok else "unavailable")
    assert out["pbo"]["status"] == ("ok" if pbo_ok else "not_computed")


def test_only_the_all_ok_case_is_not_downgraded_exactly_once():
    """矩陣中恰 1 例不降級（機械數）。"""
    n_ok = 0
    for elig_state, mb_ok, dsr_ok, pbo_ok in _MATRIX:
        out = build_validation_section(
            eligibility=_elig(elig_state, min_btl_ok=mb_ok), dsr=_dsr(dsr_ok), pbo=_pbo(pbo_ok), provenance=_prov()
        )
        n_ok += out["display_downgrade"] is False
    assert n_ok == 1


def test_universe_scope_ledger_recorded_only_forces_downgrade_even_when_all_ok():
    """⑤ A1-4：三關皆 ok、eligible True，pbo.universe_scope=='ledger_recorded_only' ⇒ 仍降級＋警語鍵。"""
    out = build_validation_section(
        eligibility=_elig(True), dsr=_dsr(True), pbo=_pbo(True, universe_scope="ledger_recorded_only"), provenance=_prov()
    )
    assert out["display_downgrade"] is True
    assert len(out["warning_text_key"]) > 0
    assert out["pbo"]["universe_scope"] == "ledger_recorded_only"
    validate_against_contract(out["pbo"], "pbo")
    # 對照：同一組但 universe_scope=None ⇒ 不降級（證明是 universe_scope 觸發）
    base = build_validation_section(eligibility=_elig(True), dsr=_dsr(True), pbo=_pbo(True), provenance=_prov())
    assert base["display_downgrade"] is False


def test_dsr_and_pbo_none_are_honest_not_computed():
    """⑥ dsr=None, pbo=None ⇒ 兩節 status not_computed、reason n_unknown、數值 None、universe_scope None；過契約；降級。"""
    out = build_validation_section(eligibility=_elig(True), dsr=None, pbo=None, provenance=_prov())
    for name in ("dsr", "pbo"):
        assert out[name]["status"] == "not_computed"
        assert out[name]["reason"] == "n_unknown"
        validate_against_contract(out[name], name)
    assert out["dsr"]["value"] is None and out["dsr"]["sr0"] is None and out["dsr"]["variance_source"] is None
    assert out["pbo"]["value"] is None and out["pbo"]["universe_scope"] is None
    assert out["display_downgrade"] is True


def test_assumed_not_ledgered_forces_eligible_none():
    """要點 5：eligibility.n_source=='assumed_not_ledgered' ⇒ 強制 eligible None（即使傳 True）。"""
    out = build_validation_section(eligibility=_elig(True, n_source="assumed_not_ledgered"), dsr=_dsr(True), pbo=_pbo(True), provenance=_prov())
    assert out["eligibility"]["eligible"] is None
    assert out["eligibility"]["n_source"] == "assumed_not_ledgered"
    assert out["display_downgrade"] is True


def test_nan_numeric_fields_become_none_not_nan():
    """數值欄 NaN ⇒ None（契約 float|null；JSON 不得含 NaN）。"""
    out = build_validation_section(eligibility=_elig(True), dsr=_dsr(False), pbo=_pbo(True), provenance=_prov())
    assert out["dsr"]["value"] is None and out["dsr"]["sr0"] is None


def test_no_recommendation_keys_anywhere():
    """要點 4：結構任一層不得含推薦類鍵。"""
    out = build_validation_section(eligibility=_elig(True), dsr=_dsr(True), pbo=_pbo(True), provenance=_prov())
    banned = {"recommended", "recommendation", "score", "overfitting_score", "verdict", "rank"}
    seen = set(out)
    for sec in ("eligibility", "min_btl", "dsr", "pbo", "provenance"):
        seen |= set(out[sec])
    assert not (seen & banned)


def test_provenance_missing_keys_default_and_bad_enum_raises():
    """provenance 缺鍵 ⇒ None／not_computed；枚舉外值 ⇒ ContractViolation（機械枚舉對映）。"""
    out = build_validation_section(eligibility=_elig(True), dsr=None, pbo=None, provenance={})
    assert out["provenance"]["status"] == "not_computed" and out["provenance"]["n_semantics"] is None
    with pytest.raises(ContractViolation):
        build_validation_section(eligibility=_elig(True), dsr=None, pbo=None, provenance={**_prov(), "t_semantics": "weekly"})
