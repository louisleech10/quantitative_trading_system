"""GAP-3 事件揭露 Task 1.3 驗收：`degraded_full_sample` 之**原因與門檻**進 report metadata。

## 出生事故（2026-09-06 UAT B22-9）

使用者對 60／115／219 筆三種事件批都看到
`analysis_status=degraded_full_sample · oos_guarantees=false`，
但畫面**看不出為什麼、也看不出還差多少** ⇒ 無從判斷該加樣本還是改設定。

而 `reason`／`train_rows`／`test_rows`／`min_test_rows` 這四個數字，
orchestrator 在觸發 fallback 時**本來就算出來了**——只是只進了 `logger.warning`。
實跑 log（115 筆批）：
`reason=rolling_warmup_insufficient train_rows=82 test_rows=30 min_test_rows=131`

本檔守的是「那四個數字有沒有真的被帶到 report」，以及「沒有降級時**不得**造一個假的」。
"""

from __future__ import annotations

import inspect

import pytest

from momentum.Analysis import ic_filter_orchestrator as orch


def test_oos_downgrade_has_exactly_two_write_sites_with_precedence():
    """🔴 **本條之前提於 R1 被我自己的修法改掉，已誠實改寫。**

    改寫前：斷言「寫出點恰為一處」。
    改寫後：`CODEX-R1-P1-01` 的修法需要**第二個**寫出點（root 紅標處補寫非 fallback 分支），
    所以「唯一寫出點」不再是對的不變式。真正該守的是**優先序**：
    fallback 的四數字版**先寫**，補寫端**只在缺席時**動作。

    ⚠️ 舊式在改寫後其實仍會綠（補寫用的是 `meta[...]` 而非 `report_meta[...]`，字串計數仍為 1）
    ——那是靠技術細節矇混，不是真的在守那條規則。故整條換掉。
    """
    src = inspect.getsource(orch)
    # 兩個寫出點：fallback 的富版 ＋ root 紅標處的補寫
    assert src.count('"oos_downgrade"] = ') == 2
    # 補寫端必須有「缺席才寫」的守衛（否則會蓋掉富版）
    annotate_src = inspect.getsource(
        orch.ICFilterOrchestrator._annotate_root_status_and_pass_class)
    assert 'not isinstance(meta.get("oos_downgrade"), dict)' in annotate_src
    # 行為面之保證見 `test_annotate_does_not_overwrite_fallback_rich_version`


def test_oos_downgrade_carries_the_four_numbers_from_details():
    """四個鍵齊全且型別正確——缺任一個，畫面就講不出「還差多少」。"""
    src = inspect.getsource(orch)
    block_start = src.index('report_meta["oos_downgrade"]')
    block = src[block_start:block_start + 500]
    for key in ("reason", "train_rows", "test_rows", "min_test_rows"):
        assert f'"{key}"' in block, f"oos_downgrade 缺 {key}"
    # 三個數字一律 int（details 可能帶 numpy 型別；序列化前必須是純 int）
    assert block.count("int(details.get(") == 3


def test_resolve_root_status_unchanged_by_this_task():
    """🔴 **判定規則一字未動**：`_resolve_root_status` 不得讀本票新增的鍵。

    本票只做投影。若判定開始依賴 `oos_downgrade`，那就變成「顯示欄回頭影響判定」，
    而顯示欄是為人看的、判定是為 gate 用的——兩者耦合之後，改文案會改 gate 結果。
    """
    status_src = inspect.getsource(orch.ICFilterOrchestrator._resolve_root_status)
    assert "oos_downgrade" not in status_src


@pytest.mark.parametrize(
    ("meta", "expect_status"),
    [
        ({"oos_guarantees": False}, "degraded_full_sample"),
        ({"fit_mode": "full_sample"}, "degraded_full_sample"),
        ({"ic_train_test_split": {"applied": True, "oos_guarantees": True}}, "ok_oos"),
        ({"oos_guarantees": True}, "ok_oos"),
    ],
    ids=["oos_false", "full_sample", "split_applied", "oos_true"],
)
def test_resolve_root_status_behaviour_is_baseline(meta, expect_status):
    """判定規則之**行為**基線（本票前後必須一致）。

    這四格是 `_resolve_root_status` 的既有分支；本票若不慎動到它，這裡會紅。
    """
    status, _ = orch.ICFilterOrchestrator._resolve_root_status(meta)
    assert status == expect_status


def test_oos_downgrade_never_initialised_as_empty_dict():
    """🔴 不得寫空 dict——空 dict 與「沒有降級」在前端分不出來。

    （R1 後本條之標題與敘述已修正：本鍵**不再**只在 fallback 段被寫，
    非 fallback 分支由 root 紅標處補寫；不變的是「不得無條件初始化」。
    「`ok_oos` 不寫本欄」之行為由 `test_annotate_writes_nothing_when_ok_oos` 守。）
    """
    src = inspect.getsource(orch)
    assert 'setdefault("oos_downgrade"' not in src
    assert '"oos_downgrade": {}' not in src


def test_frontend_reads_metadata_not_task_status():
    """🔴 前端讀 `report.metadata.oos_downgrade`，**不**經 task status。

    本票刻意不開 task_info 投影：`DegradedBanner` 已經在讀 `report.metadata`
    （同 `event_filter` 那條路），再開一條會是沒有消費端的死表面。
    本條把那個決定釘住——日後若有人加了 task_status 投影卻沒有消費端，這裡會紅。
    """
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    svc = (repo / "api" / "services" / "ic_analysis_service.py").read_text(encoding="utf-8")
    assert '"oos_downgrade": task_info.get("oos_downgrade")' not in svc
    banner = (repo / "frontend" / "src" / "components" / "ic-analysis"
              / "DegradedBanner.tsx").read_text(encoding="utf-8")
    assert "metadata?.oos_downgrade" in banner


def test_fallback_actually_writes_oos_downgrade_into_metadata(monkeypatch):
    """🔴 **行為測試**（不是掃字串）：真的呼叫 `_run_full_sample_fallback`，
    看 `oos_downgrade` 有沒有真的落進 `report["metadata"]`。

    上面幾條是結構斷言（`B1-WEAKTEST-1` 那種形態，等價改寫就會誤紅）。
    本條把 `self.analyze` 換成一個最小假回應，讓 fallback 的**其餘整段真的跑一遍**
    ——metadata 組裝、root 紅標、寫出點全部走到，只有重跑分析被短路。
    """
    inst = orch.ICFilterOrchestrator.__new__(orch.ICFilterOrchestrator)
    inst._suppress_persist = True          # 不落檔（本條只驗 metadata）
    inst._in_fallback_rerun = False
    inst._ic_cache = {}
    inst._filtered_features_df = None
    inst._event_identity = None
    inst._features_path = None

    def _fake_analyze(*_args, **_kwargs):
        return {"metadata": {"scope": "should_be_popped"}, "marginal_ic": None}

    monkeypatch.setattr(inst, "analyze", _fake_analyze, raising=False)

    report = orch.ICFilterOrchestrator._run_full_sample_fallback(
        inst,
        features_path="f.h5",
        labels_path="l.h5",
        meta_path=None,
        config_override=None,
        progress_callback=None,
        kline_reader=None,
        reason="rolling_warmup_insufficient",
        details={"train_rows": 82, "test_rows": 30, "min_test_rows": 131},
    )

    meta = report["metadata"]
    assert meta["oos_downgrade"] == {
        "reason": "rolling_warmup_insufficient",
        "train_rows": 82,
        "test_rows": 30,
        "min_test_rows": 131,
    }
    # 既有行為未被本票改動（同一次呼叫一併驗，避免「加了新欄卻弄壞舊欄」）
    assert meta["fit_mode"] == "full_sample"
    assert meta["oos_guarantees"] is False
    assert "scope" not in meta
    assert report["analysis_status"] == "degraded_full_sample"


def test_fallback_downgrade_defaults_to_zero_when_details_incomplete(monkeypatch):
    """`details` 缺鍵 ⇒ 三個數字為 0（**不炸**），但 `reason` 照實帶。

    邊界：呼叫端若沒帶齊 details，畫面會顯示「0 列 / 0 列 / 需要 0 列」——
    那看得出來是壞的；若改成整段不寫，使用者只會回到「不知道為什麼」的原點。
    """
    inst = orch.ICFilterOrchestrator.__new__(orch.ICFilterOrchestrator)
    inst._suppress_persist = True
    inst._in_fallback_rerun = False
    inst._ic_cache = {}
    inst._filtered_features_df = None
    inst._event_identity = None
    inst._features_path = None
    monkeypatch.setattr(inst, "analyze", lambda *a, **k: {"metadata": {}}, raising=False)

    report = orch.ICFilterOrchestrator._run_full_sample_fallback(
        inst, features_path="f.h5", labels_path="l.h5", meta_path=None,
        config_override=None, progress_callback=None, kline_reader=None,
        reason="some_other_reason", details={},
    )
    assert report["metadata"]["oos_downgrade"] == {
        "reason": "some_other_reason", "train_rows": 0, "test_rows": 0, "min_test_rows": 0,
    }


# ══════════════════════════════════════════════════════════════════════════
# R1 閉合：CODEX-R1-P1-01／COMPOSER-R1-P2-02
#   ——**任何**降級分支都要有具名原因，不只 full-sample fallback 那一條
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize(
    ("meta", "expect_branch"),
    [
        ({"oos_guarantees": False}, "meta_oos_guarantees_false"),
        ({"fit_mode": "full_sample"}, "fit_mode_full_sample"),
        ({"event_filter": {"fallback": True}}, "event_filter_fallback"),
        ({"ic_train_test_split": {"applied": False}}, "split_not_applied"),
        ({"ic_train_test_split": {"oos_guarantees": False}}, "split_not_applied"),
        ({}, "no_holdout_evidence"),
        ({"ic_train_test_split": {"applied": True, "oos_guarantees": True}}, None),
        ({"oos_guarantees": True}, None),
    ],
    ids=["oos_false", "full_sample", "event_fallback", "split_not_applied",
         "split_oos_false", "empty", "split_ok", "oos_true"],
)
def test_downgrade_branch_covers_every_path(meta, expect_branch):
    """🔴 每一條降級分支都要回一個**具名**代號（`None` 只留給真的沒降級）。

    出生事故（`CODEX-R1-P1-01`）：首版只有 full-sample fallback 那條路寫 `oos_downgrade`，
    其餘四條分支降級了卻沒有原因 ⇒ 畫面退回籠統警語，而那正是本票要修的病。
    """
    assert orch.ICFilterOrchestrator._downgrade_branch(meta) == expect_branch


def test_resolve_root_status_is_thin_wrapper_of_single_judgment():
    """🔴 判定只有**一份**實作：`_resolve_root_status` 之結果必須恆等於
    「`_downgrade_branch` 是否為 None」。

    兩份條件必然漂移；本條把「薄包裝」這件事釘成可證偽的等式。
    """
    metas = [
        {"oos_guarantees": False}, {"fit_mode": "full_sample"},
        {"event_filter": {"fallback": True}}, {"ic_train_test_split": {"applied": False}},
        {"ic_train_test_split": {"applied": True, "oos_guarantees": True}},
        {"oos_guarantees": True}, {}, {"ic_train_test_split": "not-a-dict"},
    ]
    for m in metas:
        status, oos = orch.ICFilterOrchestrator._resolve_root_status(m)
        branch = orch.ICFilterOrchestrator._downgrade_branch(m)
        assert (status == "ok_oos") is (branch is None), m
        assert oos is (branch is None), m


def test_annotate_backfills_downgrade_for_non_fallback_paths():
    """🔴 非 fallback 之降級路徑，在 root 紅標寫出點被**補上**具名原因。

    列數為 `None`（**不是 0**）——0 會被讀成「訓練 0 列」這種假事實。
    """
    report = {"metadata": {"event_filter": {"fallback": True}}}
    orch.ICFilterOrchestrator._annotate_root_status_and_pass_class(
        report, analysis_status="degraded_full_sample", oos_guarantees=False)
    dg = report["metadata"]["oos_downgrade"]
    assert dg["reason"] == "event_filter_fallback"
    assert dg["train_rows"] is None and dg["test_rows"] is None and dg["min_test_rows"] is None


def test_annotate_does_not_overwrite_fallback_rich_version():
    """🔴 **只在缺席時補**：fallback 已寫入的四數字版不得被無數字版蓋掉。"""
    rich = {"reason": "rolling_warmup_insufficient",
            "train_rows": 82, "test_rows": 30, "min_test_rows": 131}
    report = {"metadata": {"fit_mode": "full_sample", "oos_downgrade": dict(rich)}}
    orch.ICFilterOrchestrator._annotate_root_status_and_pass_class(
        report, analysis_status="degraded_full_sample", oos_guarantees=False)
    assert report["metadata"]["oos_downgrade"] == rich


def test_annotate_writes_nothing_when_ok_oos():
    """正向對照：`ok_oos` ⇒ 不得補寫本欄（否則 banner 會顯示不該有的降級說明）。"""
    report = {"metadata": {"oos_guarantees": True}}
    orch.ICFilterOrchestrator._annotate_root_status_and_pass_class(
        report, analysis_status="ok_oos", oos_guarantees=True)
    assert "oos_downgrade" not in report["metadata"]
