"""ICHC Task 1.1 — report 契約 SoT 載入與 validator 測試（T-1a/T-1b/T-1c）。

Oracle 分級：性質檢驗（契約規則本身即斷言，無凍結期望值）。
"""

import json

import pytest

from momentum.Analysis.ic_config_schema import (
    ContractValidationError,
    contract_enum,
    load_report_contract,
    validate_report_against_contract,
)


class TestT1aLoad:
    def test_contract_loads_and_has_required_nodes(self):
        contract = load_report_contract()
        assert isinstance(contract, dict)
        assert "capability_status" in contract
        assert "report_sections" in contract
        assert "reasons" in contract

    def test_contract_enum_returns_frozenset(self):
        statuses = contract_enum("capability_status")
        assert isinstance(statuses, frozenset)
        assert len(statuses) >= 2

    def test_contract_enum_unknown_node_raises(self):
        with pytest.raises(KeyError):
            contract_enum("no_such_enum_node")


class TestT1bValidator:
    def test_unknown_status_value_raises(self):
        report = {"turnover_analysis": {"status": "definitely_not_in_enum", "reason": "x"}}
        with pytest.raises(ContractValidationError):
            validate_report_against_contract(report)

    def test_non_ok_status_without_reason_raises(self):
        report = {"ic_decay": {"status": "disabled"}}
        with pytest.raises(ContractValidationError):
            validate_report_against_contract(report)

    def test_quantile_payload_missing_required_keys_raises(self):
        report = {"quantile_returns": {"featA": {"quantile_mean_returns": {"Q1": 0.1}}}}
        with pytest.raises(ContractValidationError):
            validate_report_against_contract(report)

    def test_valid_status_object_passes(self):
        statuses = contract_enum("capability_status")
        assert "disabled" in statuses
        report = {"turnover_analysis": {"status": "disabled", "reason": "turnover_disabled"}}
        validate_report_against_contract(report)  # 不 raise 即過

    def test_complete_quantile_payload_passes(self):
        contract = load_report_contract()
        required = contract["report_sections"]["quantile_returns"][
            "per_feature_required_keys"
        ]
        payload = {key: {} for key in required}
        validate_report_against_contract({"quantile_returns": {"featA": payload}})

    def test_legacy_empty_dict_tolerated(self):
        # Phase 3 前 xsec 遺留裸空 dict：v1 契約明文容忍（notes.legacy_empty_allowed）
        validate_report_against_contract({"grouped_ic": {}})

    def test_non_dict_report_raises(self):
        with pytest.raises(ContractValidationError):
            validate_report_against_contract(["not", "a", "dict"])


class TestT1cBadFile:
    def test_bad_json_raises(self, tmp_path, monkeypatch):
        import momentum.Analysis.ic_config_schema as schema_mod

        bad = tmp_path / "bad_contract.json"
        bad.write_text("{ not valid json", encoding="utf-8")
        monkeypatch.setattr(schema_mod, "_REPORT_CONTRACT_PATH", bad)
        monkeypatch.setattr(schema_mod, "_report_contract_cache", None)
        with pytest.raises(json.JSONDecodeError):
            load_report_contract()

    def test_missing_file_raises(self, tmp_path, monkeypatch):
        import momentum.Analysis.ic_config_schema as schema_mod

        monkeypatch.setattr(
            schema_mod, "_REPORT_CONTRACT_PATH", tmp_path / "nope.json"
        )
        monkeypatch.setattr(schema_mod, "_report_contract_cache", None)
        with pytest.raises(FileNotFoundError):
            load_report_contract()
