"""ICHC Task 4.2 — event_timestamps 接線測試。

行為實測（orchestrator 級，真實 kline 衍生 fixture）＋service 傳導 wiring
原始碼斷言（repo 慣例：NetICChart.test page-wiring 先例之後端版）。
M3 mutation（stage3 強制 None）由驗收步驟實跑，本檔 T2 即其紅色 oracle。
"""

import re
from pathlib import Path

import pytest

from tests.momentum.helpers.ichc_run import canonical_sha, feature_index, run_analyze

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.slow
class TestTimestampsBehavior:
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "🔴 已知**產品**缺陷（2026-08-24 診斷，非測試過時）：event_filter 開啟時 "
            "`report_meta.n_samples` 記的是**過濾後之事件數**，而 split plan 之 row_index 仍是"
            "**全量索引**；`survivor_contract.build_survivor_output` 之 "
            "`n_samples_total < split train_rows+test_rows` 檢查把兩者當同一母體比較，遂 raise，"
            "且例外一路傳出 `analyze()`——不是只有 survivor 輸出失敗，是整個分析掛掉。\n"
            "實測（fixture 全長 1696、split train/test = 1356/335 = 1691）："
            "n_events=100 成功（走事件數不足之 fallback）、800 失敗、1695 失敗。\n"
            "🔴 **可從正式 API 觸及**：`api/services/ic_analysis_service.py` 於 "
            "`elif request.event_timestamps:` 分支設 `event_filter.enabled=True`"
            "（GAP-3 B5.2 之「匯入案例→選事件→跑 IC」流程），輸入形狀與本測試相同。\n"
            "本測試**未改為期望 raise**——那等於把缺陷寫成正規行為。"
            "使用者 2026-08-24 裁定「以現行程式碼為準、修測試不修產品碼」，"
            "故本條標 xfail(strict) 待修：**產品修好後本條會因 XPASS 而紅**，不會靜默腐爛。\n"
            "診斷探針：handoffs/probe_t2_inputs.py、handoffs/probe_t2_boundary.py"
        ),
    )
    def test_t2_large_subset_effective_and_oos(self):
        """R5 裁決正例（codex 必答 3）：n=800 → mode=timestamps、n_events==800<full_n、
        無 fallback、ok_oos（holdout 可行）。"""
        full_n = len(feature_index())
        subset = list(feature_index(800))
        report = run_analyze(
            config_override={"event_filter": {"enabled": True}},
            event_timestamps=subset,
        )
        ev = report["metadata"]["event_filter"]
        assert ev["mode"] == "timestamps"
        assert ev["n_events"] == 800
        assert ev["n_events"] < full_n  # 嚴格小於（CODEX-R3-P1-04）
        assert ev.get("fallback") is not True
        assert report["analysis_status"] == "ok_oos"

    def test_t2b_small_subset_keeps_events_through_fallback(self):
        """R5 裁決 A′ 核心：n=400 觸發 warmup fallback，但事件語意保留——
        重跑仍帶 timestamps（mode=timestamps、n_events==400）、root degraded。"""
        subset = list(feature_index(400))
        report = run_analyze(
            config_override={"event_filter": {"enabled": True}},
            event_timestamps=subset,
        )
        ev = report["metadata"]["event_filter"]
        assert ev["mode"] == "timestamps"
        assert ev["n_events"] == 400
        assert report["analysis_status"] == "degraded_full_sample"

    def test_t3_absent_is_deterministic_and_empty_list_equals_absent(self, tmp_path):
        """未帶＝決定性（同 config 兩跑 canonical sha 相等）；空 list ≡ 未帶。

        兩跑共用 sidefx_dir（filtered_features_path 為 harness 路徑非產品輸出）；
        時鐘鍵排除清單見 ichc_run.canonical_sha docstring。
        """
        shared = tmp_path / "sidefx"
        base_a = run_analyze(
            config_override={"event_filter": {"enabled": True}}, sidefx_dir=shared
        )
        base_b = run_analyze(
            config_override={"event_filter": {"enabled": True}},
            event_timestamps=[],
            sidefx_dir=shared,
        )
        assert canonical_sha(base_a) == canonical_sha(base_b)

    def test_t4_all_outside_index_falls_back_loud(self):
        """全部 timestamps 落 index 外 → n=0 → insufficient tier → loud fallback。

        （TODO 原寫 AlignmentViolationError；實碼路徑 n=0 先命中 insufficient
        fallback——loud 回退即誠實行為，AVE 僅在 n>=30 且零交集時觸發。具名修正。）
        """
        report = run_analyze(
            config_override={"event_filter": {"enabled": True}},
            event_timestamps=[1, 2, 3],
        )
        ev = report["metadata"]["event_filter"]
        assert ev["fallback"] is True
        assert report["analysis_status"] == "degraded_full_sample"


class TestServiceWiringSource:
    """service 傳導鏈五節點的原始碼斷言（不起 API server）。"""

    def _src(self, rel: str) -> str:
        return (REPO / rel).read_text(encoding="utf-8")

    def test_service_passes_event_timestamps_kwarg(self):
        src = self._src("api/services/ic_analysis_service.py")
        assert re.search(r"event_timestamps=request\.event_timestamps or None", src)
        # CODEX-R5-P1-01：full-analysis path 同型漏接已補
        assert re.search(r'event_timestamps=getattr\(request, "event_timestamps", None\) or None', src)
        assert "not supported in API yet" not in src  # warning 已移除

    def test_fallback_preserves_event_timestamps(self):
        """R5 裁決 A′ wiring：fallback 簽名帶參＋呼叫點透傳＋one-shot guard 存在。"""
        src = self._src("momentum/Analysis/ic_filter_orchestrator.py")
        assert re.search(
            r"def _run_full_sample_fallback\([\s\S]{0,400}?event_timestamps: Optional\[list\] = None", src
        )
        # R6 修補（三家同判）：兩個 fallback 呼叫點皆須透傳
        assert re.search(r"reason=\"rolling_warmup_insufficient\",[\s\S]{0,120}?event_timestamps=event_timestamps", src)
        assert re.search(r"reason=\"insufficient_data\",[\s\S]{0,120}?event_timestamps=event_timestamps", src)
        assert "one-shot fallback guard" in src

    def test_orchestrator_chain_complete(self):
        src = self._src("momentum/Analysis/ic_filter_orchestrator.py")
        assert re.search(r"def analyze\([\s\S]{0,400}?event_timestamps: Optional\[list\] = None", src)
        assert re.search(r"_stage3_event_filter\([\s\S]{0,200}?event_timestamps=event_timestamps", src)
        assert re.search(r"def _stage3_event_filter\([\s\S]{0,300}?event_timestamps: Optional\[list\] = None", src)
        assert re.search(r"timestamps = event_timestamps", src)
        assert not re.search(r"^\s+timestamps = None$", src, re.MULTILINE)
