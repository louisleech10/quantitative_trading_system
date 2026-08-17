"""ICHC Task 5.3 — turnover gate（方案 A）2×2 語意測試＋M7 target。

金字塔配置（重格單元直測、輕格 pipeline 一跑、ON 回歸由 B2 golden/A-B 基準承擔）：
- turnover=false pipeline → report 節=契約 status 物件、summary turnover_rate 缺席
- turnover=false ∧ net_ic=true → `_run_net_ic` 單元：typed unavailable reason=turnover_disabled
- 預設 config → enabled=True（「驗過就別預設關閉」回歸）
"""

import pytest

from momentum.Analysis.ic_config_schema import (
    ICConfig,
    contract_enum,
    load_ic_config,
)
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from tests.momentum.helpers.ichc_run import run_analyze


class TestDefaults:
    def test_default_turnover_enabled_true(self):
        assert ICConfig().turnover.enabled is True


@pytest.mark.slow
class TestTurnoverDisabledPipeline:
    @pytest.fixture(scope="class")
    def report(self):
        return run_analyze(config_override={"turnover": {"enabled": False}})

    def test_report_section_is_contract_status(self, report):
        node = report["turnover_analysis"]
        assert node.get("status") == "disabled"
        assert node.get("status") in contract_enum("capability_status")
        assert node.get("reason") == "turnover_disabled"
        # 無殘留數值鍵（僅 status/reason）
        assert set(node.keys()) == {"status", "reason"}

    def test_summary_turnover_rate_absent(self, report):
        """R6 修補（CODEX-R6）：key 缺席斷言（非值為 None——那是假綠形態）。"""
        rows = report.get("summary_table") or []
        assert rows, "summary 不應為空"
        for row in rows:
            assert "turnover_rate" not in row


class TestNetICDisabledUnit:
    def test_m7_net_ic_typed_unavailable_when_turnover_disabled(self):
        orch = ICFilterOrchestrator(load_ic_config())
        orch._report = {
            "turnover_analysis": {"status": "disabled", "reason": "turnover_disabled"}
        }
        result = orch._run_net_ic([], ICConfig())
        assert result == {"status": "unavailable", "reason": "turnover_disabled"}
        contract_reasons = __import__(
            "momentum.Analysis.ic_config_schema", fromlist=["load_report_contract"]
        ).load_report_contract()["reasons"]["net_ic_unavailable"]
        assert result["reason"] in contract_reasons
