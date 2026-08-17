"""Task 2.1 驗證：策略驗證契約（16 頂層鍵、ref 真解析、drift 偵測、型別/額外鍵）。"""

import json
import subprocess
from pathlib import Path

import pytest

from momentum.Analysis import ic_config_schema
from momentum.Analysis.strategy_validation.contract import (
    ContractViolation,
    contract_top_level_keys,
    load_strategy_validation_contract,
    validate_against_contract,
)

_CONTRACT_FILE = Path("momentum/Analysis/contracts/strategy_validation_contract.json")

_EXPECTED_TOP_LEVEL = {
    "version",
    "capability_status_ref",
    "ledger_record_keys",
    "n_fields",
    "report_sections",
    "eligibility_keys",
    "annualization_source_values",
    "t_semantics_values",
    "n_semantics_values",
    "selection_metric_values",
    "universe_source_values",
    "variance_source_values",
    "metric_unit_values",
    "universe_scope_values",
    "reasons",
    "reason_conditions",
}


def test_capability_status_ref_is_really_dereferenced():
    """① 解析結果與 IC 契約逐值相等（證 ref 真的被 dereference，非複製貼上）。"""
    got = load_strategy_validation_contract()["capability_status"]
    assert got == ic_config_schema.load_report_contract()["capability_status"]


def test_six_status_values_do_not_appear_literally_in_strategy_contract():
    """② 六值不在策略契約字面出現（防兩處列舉）。"""
    text = _CONTRACT_FILE.read_text(encoding="utf-8")
    for value in ic_config_schema.load_report_contract()["capability_status"]:
        assert f'"{value}"' not in text, f"策略契約不得複列 capability_status 值: {value}"


def test_ref_pointing_to_missing_key_raises(tmp_path):
    """③ drift 偵測：ref 指向不存在之鍵 ⇒ raise（禁 fallback）。"""
    payload = json.loads(_CONTRACT_FILE.read_text(encoding="utf-8"))
    payload["capability_status_ref"] = (
        "momentum/Analysis/contracts/ic_report_contract.json#no_such_key"
    )
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ContractViolation):
        load_strategy_validation_contract(broken)


def test_ref_pointing_to_missing_file_raises(tmp_path):
    payload = json.loads(_CONTRACT_FILE.read_text(encoding="utf-8"))
    payload["capability_status_ref"] = "momentum/Analysis/contracts/nope.json#capability_status"
    broken = tmp_path / "broken2.json"
    broken.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ContractViolation):
        load_strategy_validation_contract(broken)


def test_invalid_json_raises(tmp_path):
    broken = tmp_path / "syntax.json"
    broken.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ContractViolation):
        load_strategy_validation_contract(broken)


def test_no_key_named_n_or_capital_n():
    """④ 無鍵名為 `n` 或 `N`（N 語意須具名，禁裸 n）。"""
    text = _CONTRACT_FILE.read_text(encoding="utf-8")
    assert '"n":' not in text and '"N":' not in text
    contract = load_strategy_validation_contract()
    assert "n" not in contract and "N" not in contract


def test_exactly_sixteen_top_level_keys():
    """⑤ 16 鍵齊備（逐字集合相等，非只數個數）。"""
    assert contract_top_level_keys() == _EXPECTED_TOP_LEVEL


def test_enumerations_and_reason_conditions():
    """⑥⑦⑧ metric_unit／reasons 12 值／n_fields 六值／universe_scope_values。"""
    contract = load_strategy_validation_contract()
    assert contract["metric_unit_values"] == ["per_period", "annualized"]
    assert set(contract["reason_conditions"]) == set(contract["reasons"])
    assert len(contract["reasons"]) == 12
    assert "reporter_failed" in contract["reasons"]
    assert len(contract["n_fields"]) == 6
    assert "n_rows_rejected" in contract["n_fields"]
    assert contract["universe_scope_values"] == ["ledger_recorded_only"]


def test_report_sections_required_keys_match_a1_13_literally():
    """⑨ 五節 required_keys 與 A1-13 逐字相等（缺一即紅）。"""
    sections = load_strategy_validation_contract()["report_sections"]
    expected = {
        "eligibility": {
            "eligible",
            "required_years_upper_bound",
            "available_years",
            "trials_budget",
            "trials_used",
            "target_sharpe",
            "n_source",
            "display_downgrade",
            "warning_text_key",
            "status",
            "reason",
        },
        "min_btl": {
            "status",
            "reason",
            "required_years_upper_bound",
            "available_years",
            "trials_budget",
            "trials_used",
            "target_sharpe",
        },
        "dsr": {
            "status",
            "reason",
            "value",
            "sr0",
            "sr_obs_per_period",
            "n_trials_used",
            "variance_source",
            "n_independence",
        },
        "pbo": {
            "status",
            "reason",
            "value",
            "n_paths_used",
            "n_paths_skipped",
            "n_candidates_invalid",
            "universe_scope",
        },
        "provenance": {
            "status",
            "reason",
            "n_semantics",
            "t_semantics",
            "annualization_source",
            "n_independence",
        },
    }
    for name, keys in expected.items():
        assert set(sections[name]["required_keys"]) == keys, name
    # eligibility 節之 required 應涵蓋 eligibility_keys 九鍵
    assert set(load_strategy_validation_contract()["eligibility_keys"]) <= expected["eligibility"]


def test_ledger_record_keys_schema():
    keys = load_strategy_validation_contract()["ledger_record_keys"]["keys"]
    assert len(keys) == 12
    assert keys["metric_unit"] == {"type": "str", "required": True}
    assert all(v["required"] for v in keys.values())


def _valid_pbo_section():
    return {
        "status": "ok",
        "reason": "",
        "value": 0.42,
        "n_paths_used": 924,
        "n_paths_skipped": 0,
        "n_candidates_invalid": 0,
        "universe_scope": "ledger_recorded_only",
    }


def test_validate_against_contract_accepts_valid_section():
    validate_against_contract(_valid_pbo_section(), "pbo")


def test_validate_rejects_missing_required_key():
    payload = _valid_pbo_section()
    del payload["universe_scope"]
    with pytest.raises(ContractViolation, match="缺必填鍵"):
        validate_against_contract(payload, "pbo")


def test_validate_rejects_extra_key():
    payload = _valid_pbo_section()
    payload["recommended"] = True  # 推薦類鍵一律不得存在
    with pytest.raises(ContractViolation, match="未列鍵"):
        validate_against_contract(payload, "pbo")


def test_validate_rejects_wrong_type():
    payload = _valid_pbo_section()
    payload["n_paths_used"] = "924"
    with pytest.raises(ContractViolation, match="型別不符"):
        validate_against_contract(payload, "pbo")


def test_validate_rejects_bool_masquerading_as_int():
    """bool 是 int 子類；型別清單未含 bool 時不得放行 True。"""
    payload = _valid_pbo_section()
    payload["n_paths_used"] = True
    with pytest.raises(ContractViolation, match="型別不符"):
        validate_against_contract(payload, "pbo")


def test_validate_rejects_status_outside_capability_enum():
    payload = _valid_pbo_section()
    payload["status"] = "totally_fine"
    with pytest.raises(ContractViolation, match="capability_status"):
        validate_against_contract(payload, "pbo")


def test_validate_rejects_invented_reason():
    payload = _valid_pbo_section()
    payload["status"] = "not_computed"
    payload["reason"] = "made_up_reason"
    with pytest.raises(ContractViolation, match="reasons"):
        validate_against_contract(payload, "pbo")


def test_validate_rejects_unknown_section():
    with pytest.raises(ContractViolation, match="未知 report section"):
        validate_against_contract({}, "no_such_section")


def test_contract_module_is_importable_without_run_api():
    """R6：新模組須可獨立 import，不需 run_api.py／FastAPI app。"""
    completed = subprocess.run(
        [
            "venv/bin/python",
            "-c",
            "from momentum.Analysis.strategy_validation.contract import "
            "load_strategy_validation_contract as f; "
            "assert len(f()['reasons']) == 12; print('ok')",
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "ok" in completed.stdout
