"""EVTALIGN Task 3.1：期間自動對齊＋丟失事件之揭露（`票 UAT-4`）。

SPEC：`docs/GAP3_EVENT_ALIGNMENT_SPEC.md` Task 3.1　TODO：Task 3.1

使用者原話④「還要手動重新生成特徵，手動K線對齊，這太蠢了，是缺陷吧」⇒
- orchestrator：feature ∩ K 線期間自動裁切，`period_alignment.trimmed_bars`／`used` 揭露；交集為空 fail-closed 含各期間
- service：feature run 未涵蓋之事件**逐一剔除並揭露 ID**（不再整批擋）；全部超出才 fail-closed
- 零裁切且零丟事件 ⇒ 報告**不新增鍵**（§G-1 golden 逐位元組不變）

mutation（`--phase 3`）：A7 ids 只回 count ⇒ `dropped_ids` 紅；A8 算了 trimmed 沒裁 ⇒ `trimmed` 紅；A9 全丟仍放行 ⇒ `all_dropped` 紅。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from api.services.ic_analysis_service import (
    FeatureRunCoverageError,
    _inject_period_alignment,
    check_feature_run_coverage,
)
from momentum.Analysis.ic_config_schema import load_ic_config
from momentum.Analysis.ic_filter_orchestrator import (
    ICFilterOrchestrator,
    _intersect_features_with_kline_period,
)
from momentum.core.contracts import AlignmentViolationError
from momentum.Analysis.event_samples.label_value_from_case import WindowRow

TF_SECONDS = {"1h": 3600, "12h": 43200}
DAY = 86400_000
T0 = 1704067200000
BASE_S, STEP_S, N_FEAT = 1_704_067_200, 43_200, 157
META = {"symbol": "BTCUSDT", "timeframe": "12h", "f1": {"name": "f1", "category": "trend", "layer": 1}}


def win(eid: str, *, tf: str = "12h", decision: int, end: int) -> WindowRow:
    return WindowRow(event_id=eid, symbol="ETHUSDT", timeframe=tf, decision_at_ms=decision,
                     entry_at_ms=decision, label_start_ms=T0, label_end_ms=end)


def secs(ms: int) -> str:
    return str(ms // 1000)


# ───────────── service：逐事件涵蓋＋丟失 ID 揭露 ─────────────

def test_partial_coverage_drops_events_and_discloses_dropped_ids_exactly():
    run = {"start": secs(T0 - DAY), "end": secs(T0 + 2 * DAY)}
    cov = check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS, feature_manifest_time_range=run,
        event_windows=[
            win("ev-in-1", decision=T0, end=T0 + DAY),
            win("ev-out-late", decision=T0, end=T0 + 5 * DAY),           # 右界超出
            win("ev-in-2", decision=T0 + DAY, end=T0 + 2 * DAY),
            win("ev-out-early", decision=T0 - 2 * DAY, end=T0 + DAY),    # 左界超出（decision_at）
        ],
    )
    assert cov.evaluated and cov.covered_event_ids == ("ev-in-1", "ev-in-2")
    assert cov.dropped == (("ev-out-late", "outside_feature_run"), ("ev-out-early", "outside_feature_run"))
    d = cov.disclosure()
    # 🔴 不是只看 count：ids 非空且逐值正確（`COMPOSER-R1-P2-01`／`GROK-R1-P1-02`）
    assert d["dropped_events"]["count"] == 2
    assert d["dropped_events"]["ids"] == ["ev-out-early", "ev-out-late"]
    assert d["dropped_events"]["reason"] == "outside_feature_run" and d["covered_event_count"] == 2
    assert d["feature_run"] == {"start_ms": T0 - DAY, "end_ms": T0 + 2 * DAY}


def test_all_dropped_is_fail_closed_with_periods_in_message():
    run = {"start": secs(T0 + 10 * DAY), "end": secs(T0 + 20 * DAY)}
    with pytest.raises(FeatureRunCoverageError) as ei:
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS, feature_manifest_time_range=run,
            event_windows=[win("ev0", decision=T0, end=T0 + DAY), win("ev1", decision=T0 + DAY, end=T0 + 2 * DAY)],
        )
    assert ei.value.reason == "feature_coverage_insufficient"
    msg = str(ei.value)
    assert str(T0 + 10 * DAY) in msg and str(T0) in msg and "ev0" in msg and "全部" in msg
    # over 向：全涵蓋 ⇒ 零丟、不 raise
    cov = check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS, feature_manifest_time_range={"start": secs(T0 - DAY), "end": secs(T0 + 3 * DAY)},
        event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
    )
    assert cov.dropped == () and cov.covered_event_ids == ("ev0",)
    assert check_feature_run_coverage(timeframe_seconds=TF_SECONDS, feature_manifest_time_range=run, event_windows=[]).evaluated is False


def test_inject_period_alignment_only_when_something_dropped():
    report = {"metadata": {}}
    staged_none = {"period_alignment": {"dropped_events": {"count": 0, "ids": []}, "feature_run": {}}}
    _inject_period_alignment(staged_none, report)
    assert "period_alignment" not in report["metadata"]          # 零丟 ⇒ 不新增鍵（§G-1）
    staged = {"period_alignment": {"dropped_events": {"count": 1, "ids": ["evX"], "reason": "outside_feature_run"}, "feature_run": {}}}
    report = {"metadata": {"period_alignment": {"trimmed_bars": {"head": 0, "tail": 3}}}}
    _inject_period_alignment(staged, report)
    pa = report["metadata"]["period_alignment"]
    assert pa["dropped_events"]["ids"] == ["evX"] and pa["trimmed_bars"] == {"head": 0, "tail": 3}  # 合併不覆蓋


def test_live_event_stages_drop_out_of_range_event_and_shrink_allowed_set(monkeypatch):
    """live 路徑（`_run_event_label_stages`）：run 區間只涵蓋 ev0 ⇒ ev1 被剔除且 ID 進 staged.period_alignment；
    `event_label_values` 只剩 ev0（R2 `CODEX-R2-P1-06`：原 batch-level gate 在交集前 raise，需求到不了）。"""
    from api.services import ic_analysis_service as svc
    from momentum.Analysis.event_samples import pipeline as pipeline_mod
    from tests.momentum.event_samples.helpers import load_bars, make_event

    H12_MS = 43_200_000
    bars = load_bars("ETHUSDT", ("12h",))
    monkeypatch.setattr(pipeline_mod.EventSamplePipeline, "bars_from_kline_cache",
                        staticmethod(lambda symbols, timeframes, **kw: bars))
    t0a, t0b = T0 + 100 * H12_MS, T0 + 400 * H12_MS
    # run 區間：涵蓋 ev0（含其 label 窗），不涵蓋 ev1
    monkeypatch.setattr(svc, "_feature_run_time_range",
                        lambda *c: {"start": secs(t0a - 10 * H12_MS), "end": secs(t0a + 10 * H12_MS)})

    class _Req:
        event_import_id = "imp-evtalign-31"
        event_timestamps = None
        timeframe = "12h"
        symbol = "ETHUSDT"

    staged = svc.ICAnalysisService._run_event_label_stages(
        _Req(),
        {
            "records": [make_event(0, t0=t0a, label=1, direction="long", label_value=0.02),
                        make_event(1, t0=t0b, label=0, direction="long", label_value=-0.01)],
            "event_label_spec": {"horizon_bars": 2, "entry_price_semantic": "trigger_close",
                                 "label_return_mode": "close_to_close", "decision_offset_bars": 0},
            "lookahead_bars_declared": {"12h": 0},
        },
        features_path="data_cache/features/ETHUSDT/12h/x/x.h5", meta_path=None,
    )
    pa = staged["period_alignment"]
    assert pa["dropped_events"]["count"] == 1 and pa["dropped_events"]["ids"] == ["ev1"]
    assert staged["prepared"].allowed_event_ids == frozenset({"ev0"})
    assert set(staged["event_label_by_id"]) == {"ev0"} and len(staged["event_label_values"]) == 1


# ───────────── orchestrator：feature ∩ K 線期間自動裁切 ─────────────

class _Reader:
    """K 線只涵蓋 feature 列 [lo, hi]。"""

    def __init__(self, lo: int, hi: int):
        self.lo, self.hi = lo, hi

    def read_klines(self, _s, _t):
        n = self.hi - self.lo + 1
        idx = pd.Index(BASE_S + (self.lo + np.arange(n, dtype=np.int64)) * STEP_S, name="timestamp")
        return pd.DataFrame({"close": np.linspace(100.0, 200.0, n)}, index=idx)


def _features() -> pd.DataFrame:
    idx = pd.Index(BASE_S + np.arange(N_FEAT, dtype=np.int64) * STEP_S, name="timestamp")
    return pd.DataFrame({"f1": np.arange(N_FEAT, dtype=np.float64)}, index=idx)


def test_features_trimmed_to_kline_period_with_exact_head_tail_disclosure():
    out, pa = _intersect_features_with_kline_period(_features(), META, _Reader(10, 140), event_period_ms=(T0, T0 + DAY))
    assert pa["trimmed_bars"] == {"head": 10, "tail": 16} and pa["used"]["bars"] == 131
    assert len(out) == 131 and int(out.index[0]) == BASE_S + 10 * STEP_S and int(out.index[-1]) == BASE_S + 140 * STEP_S
    assert pa["feature_period"]["bars"] == N_FEAT and pa["kline_period"]["bars"] == 131 and "event_period" in pa
    # 同頭同尾 ⇒ 零裁切、原物件不動
    same, pa0 = _intersect_features_with_kline_period(_features(), META, _Reader(0, N_FEAT - 1))
    assert pa0["trimmed_bars"] == {"head": 0, "tail": 0} and len(same) == N_FEAT
    # K 線比 feature 長（兩端）⇒ 零裁切（K 線多出的部分交 _coterminalize_close）
    _, pa1 = _intersect_features_with_kline_period(_features(), META, _Reader(-20, N_FEAT + 40))
    assert pa1["trimmed_bars"] == {"head": 0, "tail": 0}
    # 無 K 線來源 ⇒ 不裁、None
    assert _intersect_features_with_kline_period(_features(), META, None)[1] is None


def test_empty_intersection_is_fail_closed_with_all_periods():
    with pytest.raises(AlignmentViolationError, match="無交集") as ei:
        _intersect_features_with_kline_period(_features(), META, _Reader(500, 600), event_period_ms=(T0, T0 + DAY))
    msg = str(ei.value)
    assert "feature 期間" in msg and "K 線期間" in msg and "事件期間" in msg and "不是要你重生特徵" in msg


def test_stage0_applies_trim_before_split_and_stage2_generates_on_trimmed_features(monkeypatch):
    """stage0 裁切 → stage2 在裁後 feature 上生成 label（同尾化）⇒ 守衛通過；裁切紀錄在 orchestrator 上。"""
    config = load_ic_config()
    o = ICFilterOrchestrator(config)
    monkeypatch.setattr(o, "_load_features_hdf5", lambda _p: (_features(), {}))
    monkeypatch.setattr(o, "_load_labels_hdf5", lambda _p: None)
    monkeypatch.setattr(o, "_load_meta_json", lambda _p: dict(META))
    reader = _Reader(5, 150)
    feats, _, meta, _ = o._stage0_ingestion("f", "", "m", config=config, kline_reader=reader)
    assert len(feats) == 146 and o._period_alignment["trimmed_bars"] == {"head": 5, "tail": 6}
    label, _ = o._stage2_label_generation(None, meta, config, reader, features_df=feats)
    assert len(label) == 146 and label.index.equals(pd.to_datetime(feats.index, unit="s"))


def test_report_metadata_key_present_only_when_trimmed_real_fixture(monkeypatch):
    """真實 la0 fixture：K 線涵蓋 feature ⇒ 報告無 `period_alignment`（golden 不變）；
    feature 尾端補 30 根超出 K 線末端 ⇒ 報告 `period_alignment.trimmed_bars.tail == 30`。"""
    from momentum.factories import create_kline_storage_manager
    from momentum.Analysis.ic_filter_orchestrator import _normalize_frame_time_index
    from tests.momentum.helpers.ichc_run import KLINE_CACHE_DIR, run_analyze

    report = run_analyze(None)
    assert "period_alignment" not in report["metadata"]

    raw = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR).read_klines("ETHUSDT", "12h")
    kline_end_s = int(_normalize_frame_time_index(raw, "raw")[-1].value // 10**9)
    real = ICFilterOrchestrator._load_features_hdf5

    def padded(self_o, path):
        df, m = real(self_o, path)
        step = int(df.index[1]) - int(df.index[0])
        last = int(df.index[-1])
        start = max(last + step, kline_end_s + step)
        extra_idx = pd.Index(start + step * np.arange(30, dtype=np.int64), name=df.index.name)
        extra = pd.DataFrame(np.nan, index=extra_idx, columns=df.columns).astype(df.dtypes.to_dict())
        return pd.concat([df, extra]), m

    monkeypatch.setattr(ICFilterOrchestrator, "_load_features_hdf5", padded)
    report2 = run_analyze(None)
    pa = report2["metadata"]["period_alignment"]
    assert pa["trimmed_bars"]["tail"] >= 30 and pa["trimmed_bars"]["head"] == 0
    assert pa["used"]["end"] == pa["kline_period"]["end"] or pa["used"]["bars"] == pa["feature_period"]["bars"] - pa["trimmed_bars"]["tail"]
