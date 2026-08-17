"""ICHC Task 4.1 — 事件誠實化測試（GROK-R3-P1-02 反例矩陣：holdout=ON×insufficient 必含）。

Oracle：真實 kline 衍生 fixture（la0 ETHUSDT/12h）全流程 analyze；
性質斷言（root 紅標/契約 reason/resolver 分支），無凍結期望值。
"""

import pytest

from momentum.Analysis.ic_config_schema import load_report_contract
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from tests.momentum.helpers.ichc_run import feature_index, run_analyze


class TestResolverUnit:
    """M2 target：_resolve_root_status 的 event fallback 分支（單元，無 pipeline）。"""

    def test_event_fallback_forces_degraded_even_with_holdout_applied(self):
        meta = {
            "ic_train_test_split": {"applied": True, "oos_guarantees": True},
            "event_filter": {"fallback": True, "reason": "insufficient_events"},
        }
        status, oos = ICFilterOrchestrator._resolve_root_status(meta)
        assert status == "degraded_full_sample"
        assert oos is False

    def test_no_event_fallback_keeps_holdout_ok(self):
        meta = {"ic_train_test_split": {"applied": True, "oos_guarantees": True}}
        status, oos = ICFilterOrchestrator._resolve_root_status(meta)
        assert status == "ok_oos"
        assert oos is True

    def test_event_filter_without_fallback_not_degrading(self):
        meta = {
            "ic_train_test_split": {"applied": True, "oos_guarantees": True},
            "event_filter": {"mode": "timestamps", "n_events": 500},
        }
        status, _ = ICFilterOrchestrator._resolve_root_status(meta)
        assert status == "ok_oos"


@pytest.mark.slow
class TestHoldoutOnInsufficientFullPath:
    """關鍵反例格：holdout ON × tier=insufficient（10 個 timestamps < min 30）。"""

    @pytest.fixture(scope="class")
    def report(self):
        ts_subset = list(feature_index(10))
        return run_analyze(
            config_override={"event_filter": {"enabled": True}},
            event_timestamps=ts_subset,
        )

    def test_root_is_degraded(self, report):
        assert report["analysis_status"] == "degraded_full_sample"
        assert report.get("oos_guarantees") is not True

    def test_metadata_event_filter_loud(self, report):
        ev = report["metadata"]["event_filter"]
        assert ev["fallback"] is True
        assert ev["tier"] == "insufficient"
        contract = load_report_contract()
        assert ev["reason"] in contract["reasons"]["event_fallback"]
