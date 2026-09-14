"""SPLITUNIFY Task 3.1 接線驗證（-k splitunify_wiring）：`pipeline.run` 的兩條路。

判準字面之唯一來源＝`docs/SPLITUNIFY_TODO.md` Task 3.1；本檔只把它機械化。

覆蓋：
  `-k canonical_boundary`      給齊 canonical 邊界 ⇒ 走**投影**、`split_events` 一次都沒被呼叫
  `-k partial_boundary`        只給一半 ⇒ raise（不得靜默走回歷史切分）
  `-k embargo_must_be_none`    投影路徑帶著毫秒 embargo ⇒ raise（兩套隔離不得同時生效）
  `-k legacy_path`             一個都不給 ⇒ 走既有 `split_events`（歷史路徑仍活著）

🔴 全部採**執行期探針**（monkeypatch `pipeline.split_events` 計數）而非原始碼形狀斷言——
   形狀 oracle 在本 epic 已被繞過三次。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples import pipeline as pipeline_mod
from momentum.Analysis.event_samples.pipeline import EventPipelineConfig, EventSamplePipeline
from momentum.Analysis.event_samples.types import EventSplitConfig
from momentum.core.contracts import AlignmentViolationError, SplitPlan
from momentum.core.split_preview import build_row_time_fingerprint, holdout_boundary
from tests.momentum.event_samples.helpers import load_bars, make_event

TF = "12h"
H12 = 43200000
BASE = 1704067200000
SYM = "ETHUSDT"
OOS, PURGE, EMBARGO = 0.3, 2, 2


@pytest.fixture(scope="module")
def bars():
    return load_bars(SYM, (TF,))


@pytest.fixture(scope="module")
def records():
    return [make_event(i, t0=BASE + n * H12, label=i % 2) for i, n in enumerate((300, 600, 900, 1200))]


@pytest.fixture
def spy_split(monkeypatch):
    calls = []
    real = pipeline_mod.split_events

    def counting(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(pipeline_mod, "split_events", counting)
    return calls


def _canonical(records, bars):
    """由**事件所在的真實 bar 網格**造出 canonical 邊界與 plan（不是憑空造 index）。

    feature_index 取該 TF 的 `open_time_ms`（epoch 毫秒），與事件的 `feature_cutoff_ms`
    落在同一組刻度上——這正是投影之集合成員判定所要求的「同一個 universe」。
    """
    index = pd.Index(bars[SYM][TF]["open_time_ms"].to_numpy(dtype=np.int64), dtype="int64")
    b = holdout_boundary(index, oos_test_size=OOS, purge_gap=PURGE, embargo=EMBARGO)
    # 🔴 D-002 `Task 9.2b` 步驟 0 揭出的既有 fixture 缺陷：本 fixture 宣告
    #    `purge_semantic="rows"` 卻沒給 `expected_freq`，而 `validate_split_integrity`
    #    （`momentum/core/contracts.py:632-635`）對這組合直接 `TimestampDiscontinuityError`。
    #    生產端（`ic_filter_orchestrator.py:631`）本來就有帶 ⇒ 這是**測試替身落後於生產**，
    #    不是新閘過嚴。值取本 TF 之真實 bar 間距（與 `holdout_boundary` 用的同一組刻度）。
    _freq = str(pd.Timedelta(milliseconds=int(np.diff(np.asarray(index, dtype="int64"))[0])))
    kw = dict(index_kind="positional", purge_gap=PURGE, embargo=EMBARGO,
              purge_semantic="rows", expected_freq=_freq,
              base_universe_hash="deadbeef", symbol=SYM)
    # 🔴 SPLITUNIFY D-001 (4.3)：本 fixture 之 index 即該 symbol 自己的索引，
    #    故 row_index_local 逐值等於 row_index；指紋用共用序列化器（與 producer 同一支）。
    _ms = np.asarray(index, dtype="int64")

    def _fp(rows):
        _loc = np.asarray(rows, dtype=int)
        return build_row_time_fingerprint(
            positions=_loc, feature_ts_ms=_ms[_loc], symbol=SYM, base_universe_hash="deadbeef"
        )

    train = SplitPlan(split_label="train", row_index=b["train_row_index"],
                      time_bounds=(int(index[0]), int(index[b["train_row_index"][-1]])),
                      row_index_local=np.asarray(b["train_row_index"], dtype=int),
                      row_time_fingerprint=_fp(b["train_row_index"]), **kw)
    test = SplitPlan(split_label="test", row_index=b["test_row_index"],
                     time_bounds=(int(index[b["test_row_index"][0]]), int(index[-1])),
                     row_index_local=np.asarray(b["test_row_index"], dtype=int),
                     row_time_fingerprint=_fp(b["test_row_index"]), **kw)
    return train, test, index


# ── 給齊 ⇒ 走投影，`split_events` 零呼叫 ────────────────────────────────────
def test_splitunify_wiring_canonical_boundary_uses_projection(records, bars, spy_split):
    train, test, index = _canonical(records, bars)
    res = EventSamplePipeline().run(
        records, bars, EventPipelineConfig(timeframes=(TF,)),
        train_plan=train, test_plan=test, feature_index=index, selected_timeframe=TF,
    )
    assert spy_split == [], "給了 canonical 邊界卻仍呼叫歷史切分（兩套切分同時活著）"
    assert res.split_plan is not None
    # 🔴 歸屬**逐事件**與 canonical 邊界對證（不是只看「有沒有產出 plan」）：
    #    事件的 `feature_cutoff_ms` 落在 train 段的列上 ⇒ 該事件必在 train，test 亦然。
    #    這是投影的定義；若接線退回歷史切分（依事件數自己切），這個對應會直接不成立。
    train_ms = set(index[train.row_index].tolist())
    test_ms = set(index[test.row_index].tolist())
    cutoffs = dict(zip(res.receipts.per_tf["event_id"], res.receipts.per_tf["feature_cutoff_ms"]))
    labels = dict(zip(res.split_plan.assignments["event_id"], res.split_plan.assignments["split_label"]))
    checked = 0
    for eid, label in labels.items():
        cut = int(cutoffs[eid])
        assert (cut in train_ms) if label == "train" else (cut in test_ms), (
            f"事件 {eid} 標為 {label}，但其 cutoff {cut} 不在該段的列上（歸屬與 canonical 邊界不符）"
        )
        checked += 1
    assert checked > 0, "沒有任何事件進 assignments ⇒ 上面的迴圈是空洞通過"
    assert res.summary["n_train"] + res.summary["n_test"] + res.summary["n_purged"] == len(records)
    assert set(res.split_plan.summary) >= {"n_symbols", "per_symbol_n", "n_purged", "bucket_ms"}


# ── 只給一半 ⇒ fail-closed（最容易靜默退回歷史切分的形態） ──────────────────
@pytest.mark.parametrize("drop", ["train_plan", "test_plan", "feature_index"])
def test_splitunify_wiring_partial_boundary_is_fail_closed(records, bars, spy_split, drop):
    """🔴 **D-002 `Task 9.2` 起 `selected_timeframe` 已移出必填集合**，故該參數化案例
    由本檔之 `test_partial_boundary_gate_accepts_none_selected_timeframe` **取代**
    （TODO 明文：**替換**，不得只新增而留著舊的——留著會與新行為互斥）。
    """
    train, test, index = _canonical(records, bars)
    kwargs = {"train_plan": train, "test_plan": test, "feature_index": index, "selected_timeframe": TF}
    kwargs[drop] = None
    with pytest.raises(ValueError, match="必須同時給齊"):
        EventSamplePipeline().run(records, bars, EventPipelineConfig(timeframes=(TF,)), **kwargs)
    assert spy_split == [], "缺參數時退回歷史切分＝呼叫端以為自己用的是統一後的邊界"


def test_partial_boundary_gate_accepts_none_selected_timeframe(records, bars, spy_split):
    """`selected_timeframe=None` 不再 raise，且**仍走投影**（不得退回歷史切分）。

    🔴 這是 `Task 9.2` 之「四參數閘改三」的直接驗收：只把 caller 改成傳 `None`
    而不動這道閘，會**在抵達 `build_event_keys` 之前**就 fail-closed，核心目標等於沒改。
    """
    train, test, index = _canonical(records, bars)
    res = EventSamplePipeline().run(
        records, bars, EventPipelineConfig(timeframes=(TF,)),
        train_plan=train, test_plan=test, feature_index=index, selected_timeframe=None,
    )
    assert spy_split == [], "selected_timeframe=None 竟退回歷史切分 ⇒ 三參數閘沒生效"
    assert res.split_plan is not None
    # 🔴 D-002 `Task 9.3`：原斷言「`feature_timeframe` 在 assignments 欄內」已隨退回刪除——
    #    切分表回到事件級（一事件恰一列、無該欄），複合鍵只留在 `receipts.per_tf` 稽核層。
    assert res.split_plan.assignments["event_id"].is_unique


# ── 🔴 D-002 `Task 9.3`：pipeline 計數之事件級前提（去重斷言之接線） ─────────────
def test_pipeline_rejects_split_plan_that_is_not_event_level(monkeypatch, records, bars, spy_split):
    """`EventSamplePipeline.run` 之 `n_train`／`n_test`／`n_purged` 以列數計——唯有切分表一事件恰一列時才等於事件數。

    🔴 投影端已保證事件級輸出（合法路徑上本閘不可達），故以 spy 讓投影回傳「`assignments` 同事件兩列」之計畫，
    斷言 pipeline 之去重斷言 fail-closed；拔掉該斷言 ⇒ 計數靜默膨脹成列數、本條轉紅。
    """
    real = pipeline_mod.derive_event_split_from_plans

    def _dup_rows(*args, **kwargs):
        plan = real(*args, **kwargs)
        assert not plan.assignments.empty, "fixture 前提變了：須有 assignments 才造得出重複列"
        # 🔴 不新增 import 行：本檔 `:110-111` 是 register `C5-23` 之 ANCHOR，檔頭增行會使其位移。
        return type(plan)(
            assignments=pd.concat([plan.assignments, plan.assignments], ignore_index=True),
            purged=plan.purged, clusters=plan.clusters, summary=plan.summary,
        )

    monkeypatch.setattr(pipeline_mod, "derive_event_split_from_plans", _dup_rows)
    train, test, index = _canonical(records, bars)
    with pytest.raises(AlignmentViolationError, match="assignments"):
        EventSamplePipeline().run(
            records, bars, EventPipelineConfig(timeframes=(TF,)),
            train_plan=train, test_plan=test, feature_index=index, selected_timeframe=TF,
        )


# ── 投影路徑不得同時帶毫秒 embargo（Task 3.1 要點 4） ───────────────────────
@pytest.mark.parametrize(
    "split_kwargs",
    [{"embargo_ms": 3600000}, {"embargo_ms_by_symbol": {SYM: 3600000}}],
    ids=["scalar", "by_symbol"],
)
def test_splitunify_wiring_embargo_must_be_none_on_projection_path(records, bars, spy_split, split_kwargs):
    train, test, index = _canonical(records, bars)
    cfg = EventPipelineConfig(timeframes=(TF,), split=EventSplitConfig(**split_kwargs))
    with pytest.raises(ValueError, match="embargo_ms"):
        EventSamplePipeline().run(
            records, bars, cfg,
            train_plan=train, test_plan=test, feature_index=index, selected_timeframe=TF,
        )
    assert spy_split == []


# ── B2b R1 之 H6：使用者設定的測試段事件數下限必須真的傳到投影 ──────────────
def test_splitunify_wiring_tier_min_test_events_reaches_projection(records, bars, spy_split):
    """原本 `pipeline.run` 走投影時**沒傳** `tier_min_test_events` ⇒ 設定被靜默換成 1。

    （該條在 B2b R1 被我寫成「列入 B3 Task 3.1」延後，之後就消失了；2026-09-11 回溯稽核撈回。）
    """
    train, test, index = _canonical(records, bars)
    cfg = EventPipelineConfig(timeframes=(TF,), split=EventSplitConfig(tier_min_test_events=1000))
    res = EventSamplePipeline().run(
        records, bars, cfg,
        train_plan=train, test_plan=test, feature_index=index, selected_timeframe=TF,
    )
    assert res.split_plan.summary["insufficient_events_in_test"] == [SYM], (
        "下限設 1000 卻沒被判為不足 ⇒ 設定沒傳到投影"
    )


# ── 一個都不給 ⇒ 歷史路徑仍然活著（`split_events` 保留為 G-3a 對照） ────────
def test_splitunify_wiring_legacy_path_still_calls_split_events(records, bars, spy_split):
    res = EventSamplePipeline().run(records, bars, EventPipelineConfig(timeframes=(TF,)))
    assert len(spy_split) == 1, "歷史路徑被刪掉了——G-3a 遷移對照會失去對照組"
    assert res.split_plan is not None


# ── D-002 Task 9.1（B9A）：生產接線之丟棄記帳 ────────────────────────────────
# 🔴 R18 `CODEX-R18-P1-01`：Task 9.1 的四條具名測試全在 `derive_*` 層，
#    唯一**生產**呼叫點（`pipeline.py` 之投影分支）若忘了把 `discarded_rows_by_feature_tf`
#    傳下去，那四條與既有 wiring 測試**全部仍綠**——記帳可在生產路徑靜默失效。
#    本測試把斷言掛在 `EventSamplePipeline.run` 上，補掉那個缺口。


@pytest.fixture(scope="module")
def bars_multi_tf():
    """兩個 feature TF 的真實 kline——單 TF 之下 `discarded` 恆為 {}，無鑑別力。"""
    return load_bars(SYM, ("4h", TF))


def test_splitunify_wiring_discarded_rows_reaches_summary(records, bars_multi_tf):
    """選 `12h` ⇒ 被丟掉的 `4h` 列數須沿 summary 帶出（值不得為空）。

    🔴 本測試之鑑別力來源：`pipeline.py` 若省略
    `discarded_rows_by_feature_tf=discarded_rows`，summary 會退回 `{}` ⇒ 本測試轉紅。
    """
    train, test, index = _canonical(records, bars_multi_tf)
    cfg = EventPipelineConfig(timeframes=("4h", TF), split=EventSplitConfig())
    res = EventSamplePipeline().run(
        records, bars_multi_tf, cfg,
        train_plan=train, test_plan=test, feature_index=index, selected_timeframe=TF,
    )
    summary = res.split_plan.summary
    assert "discarded_rows_by_feature_tf" in summary, "生產路徑之 summary 缺記帳鍵"
    discarded = summary["discarded_rows_by_feature_tf"]
    # 🔴 值不得為空——空 dict 正是「caller 忘了傳」時的樣子。
    assert discarded, (
        "選 12h 卻沒記到任何被丟棄的 4h 列 ⇒ 生產呼叫點沒把 discarded 傳下去"
    )
    assert set(discarded) == {"4h"}, f"只該記到被丟掉的 4h，實得 {sorted(discarded)}"
    assert all(isinstance(v, int) and v > 0 for v in discarded.values()), (
        f"列數須為正整數，實得 {discarded}"
    )


def test_run_without_selected_timeframe_emits_all_feature_tf_rows(records, bars_multi_tf, spy_split):
    """🔴 `Task 9.2` 之**端到端**驗收（schema 斷言不算）：斷言標的逐字為 `split_plan.assignments`。

    經 `EventSamplePipeline.run` **不傳** `selected_timeframe` ⇒ 兩個 feature TF 皆須在
    `assignments` 裡，且列數等於 `per_tf` 列數（沒有任何一列被靜默丟掉）。
    🔴 只要 caller 仍必傳、或門檻仍擋 `None`、或 merge 仍是 `1:1`，本測試就會紅——
    這三層是 `Task 9.2` 的實質內容，schema 層的斷言抓不到其中任何一層。
    """
    train, test, index = _canonical(records, bars_multi_tf)
    cfg = EventPipelineConfig(timeframes=("4h", TF), split=EventSplitConfig())
    res = EventSamplePipeline().run(
        records, bars_multi_tf, cfg,
        train_plan=train, test_plan=test, feature_index=index, selected_timeframe=None,
    )
    assert spy_split == [], "全量模式竟退回歷史切分"
    assign = res.split_plan.assignments
    purged = res.split_plan.purged
    s = res.split_plan.summary
    # 🔴 D-002 `Task 9.3`：切分表退回事件級 ⇒ 兩表列數合計＝**事件數**（不再是 per_tf 列數）。
    n_events = int(res.receipts.per_tf["event_id"].nunique())
    assert len(assign) + len(purged) == n_events, (
        f"切分表列數 {len(assign) + len(purged)} != 事件數 {n_events} ⇒ 未退回一事件一列或有事件被丟掉"
    )
    # 全量保留改由**稽核層**證明：兩個 feature TF 皆在 per_tf，且稽核列數＝per_tf 列數（沒有列被靜默丟掉）。
    seen = set(res.receipts.per_tf["timeframe"])
    assert seen == {"4h", TF}, f"兩個 feature TF 須皆在稽核層，實得 {sorted(seen)}"
    assert s["n_event_tf_rows"] == len(res.receipts.per_tf), (
        f"稽核列數 {s['n_event_tf_rows']} != per_tf 列數 {len(res.receipts.per_tf)} ⇒ 仍有列被靜默丟掉"
    )
    # 事件數與列數是兩個量（D-002-C6），且全量下列數嚴格大於事件數。
    assert s["n_events"] == n_events
    assert s["n_event_tf_rows"] > s["n_events"]


def _run_multi_tf_full(records, bars_multi_tf):
    train, test, index = _canonical(records, bars_multi_tf)
    cfg = EventPipelineConfig(timeframes=("4h", TF), split=EventSplitConfig())
    res = EventSamplePipeline().run(
        records, bars_multi_tf, cfg,
        train_plan=train, test_plan=test, feature_index=index, selected_timeframe=None,
    )
    return res, train, test, index


def test_event_count_conservation(records, bars_multi_tf, spy_split):
    """D-002 `Task 9.4`／`D-002-C6`：`n_train+n_test+n_purged == n_events`（**事件數守恆，非列數**）。

    走真實 `EventSamplePipeline.run`、兩個 feature TF（列數＞事件數時才有鑑別力）。
    `M-SU-D2-13`：`n_train` 改取稽核層 TF 列數 ⇒ 合計超過事件數而轉紅。
    """
    res, _, _, _ = _run_multi_tf_full(records, bars_multi_tf)
    assert spy_split == []
    s, sp = res.summary, res.split_plan.summary
    assert sp["n_event_tf_rows"] > sp["n_events"], "fixture 前提變了：須多 feature TF 使列數大於事件數"
    assert s["n_train"] + s["n_test"] + s["n_purged"] == sp["n_events"]
    assert s["n_train"] > 0 and s["n_test"] > 0, "fixture 前提變了：train／test 皆須有事件，否則 n_train 之膨脹測不到"


def test_multi_feature_tf_split_labels_match_decision_anchor_per_event(records, bars_multi_tf, spy_split):
    """D-002 `Task 9.4`（`M-SU-D2-12`）：多 feature TF 案例之**逐事件值**比對，不得以集合相等冒充逐列相等。

    每個被指派之事件：`train` ⇒ 其事件級 `decision_at_ms` ≤ train 段最後一根；`test` ⇒ ≥ test 段第一根。
    破壞面＝`event_id` 集合與 membership 集合不變、但對調兩事件之標籤——集合斷言全綠，本條逐事件轉紅。
    """
    res, train, test, index = _run_multi_tf_full(records, bars_multi_tf)
    ms = np.asarray(index, dtype="int64")
    train_last = int(ms[np.asarray(train.row_index)[-1]])
    test_start = int(ms[np.asarray(test.row_index)[0]])
    anchors = dict(zip(res.manifest.table["event_id"], res.manifest.table["decision_at_ms"].astype("int64")))
    # 🔴 不寫成 `dict(zip(...assignments...))`：該整行是 register `C5-23` 之 ANCHOR（`:111`），錨點閘要求全檔唯一。
    labels = res.split_plan.assignments.set_index("event_id")["split_label"].to_dict()
    assert {"train", "test"} <= set(labels.values()), "fixture 前提變了：須同時有 train 與 test 事件，對調才測得到"
    wrong = {
        eid: (label, int(anchors[eid])) for eid, label in labels.items()
        if (label == "train" and not int(anchors[eid]) <= train_last)
        or (label == "test" and not int(anchors[eid]) >= test_start)
    }
    assert wrong == {}, f"事件之標籤與其決策錨點所在段不符（train_last={train_last}, test_start={test_start}）：{wrong}"


# ── 🔴 D-002 `Task 9.2b` 步驟 0：`validate_split_pair_integrity` 之**接線** ──────────


def test_validate_split_pair_integrity_is_called_before_derive(monkeypatch, records, bars) -> None:
    """🔴 `EventSamplePipeline.run` 必須在呼叫 `derive_event_split_from_plans` **之前**
    呼叫 `validate_split_pair_integrity`（TODO `Task 9.2b` 實作要點 1；`M-SU-D2-30`）。

    出生理由（本批 mutation 自證當場抓到）：`M-SU-D2-30a`（把那行呼叫刪掉）跑出來是
    **11 passed**——步驟 0 完全沒有接線保護。與 `M-SU-D2-14` 同型（R18 之 `A1` 第三次）。
    ⇒ 本測試同時斷言**有呼叫**與**順序在前**，兩者缺一都會讓缺陷溜過。
    """
    from momentum.Analysis.event_samples import pipeline as _pl

    order = []
    _real_validate = _pl.validate_split_pair_integrity
    _real_derive = _pl.derive_event_split_from_plans

    def _v(*a, **kw):
        order.append("validate")
        return _real_validate(*a, **kw)

    def _d(*a, **kw):
        order.append("derive")
        return _real_derive(*a, **kw)

    monkeypatch.setattr(_pl, "validate_split_pair_integrity", _v)
    monkeypatch.setattr(_pl, "derive_event_split_from_plans", _d)
    train, test, index = _canonical(records, bars)
    cfg = EventPipelineConfig(timeframes=(TF,), split=EventSplitConfig())
    EventSamplePipeline().run(
        records, bars, cfg,
        train_plan=train, test_plan=test, feature_index=index, selected_timeframe=TF,
    )
    assert "validate" in order, (
        "步驟 0 之 validate_split_pair_integrity 沒被呼叫——空段與 purge/embargo 踩線全無人擋"
    )
    assert order.index("validate") < order.index("derive"), (
        f"順序錯：{order}——驗在 derive 之後等於事後補救，derive 已用髒 plan 算完了"
    )


def test_validate_receives_millisecond_clock_not_raw_ints(monkeypatch, records, bars) -> None:
    """🔴 餵給 validator 的 `ts` 必須是**已轉好的 datetime**，不得是原始 epoch 毫秒整數。

    `_coerce_timestamp_array`（`momentum/core/contracts.py:450-451`）把**數值**一律當
    **epoch 秒** ⇒ 直接餵毫秒會被解讀成西元五萬年而 `OutOfBoundsDatetime`。
    本測試釘住這個單位邊界（本批實際踩到過一次）。
    """
    from momentum.Analysis.event_samples import pipeline as _pl

    seen = {}
    _real = _pl.validate_split_pair_integrity

    def _v(train_plan, test_plan, ts, symbols, **kw):
        seen["ts"] = ts
        return _real(train_plan, test_plan, ts, symbols, **kw)

    monkeypatch.setattr(_pl, "validate_split_pair_integrity", _v)
    train, test, index = _canonical(records, bars)
    cfg = EventPipelineConfig(timeframes=(TF,), split=EventSplitConfig())
    EventSamplePipeline().run(
        records, bars, cfg,
        train_plan=train, test_plan=test, feature_index=index, selected_timeframe=TF,
    )
    ts = seen["ts"]
    assert np.issubdtype(np.asarray(ts).dtype, np.datetime64), (
        f"ts 必須是 datetime64（實得 dtype={np.asarray(ts).dtype}）——餵原始整數會被當成秒"
    )
    assert getattr(ts, "tz", None) is None, (
        "不得帶 tz：tz-aware 會讓 _coerce_timestamp_array 回 object dtype，"
        "validate_split_integrity:657 之 np.timedelta64 比較會 TypeError"
    )


def test_mapping_plans_are_rejected_with_named_error(records, bars) -> None:
    """🔴 把多標的 Mapping 塞進本入口 ⇒ **具名** fail-closed，不得是裸 `AttributeError`
    （`CODEX-R27-P1-04`）。

    出生理由：步驟 0 上線後，Mapping 會先被餵給單標的 validator，該家實跑得到
    `AttributeError: 'dict' object has no attribute 'row_index'`——**沒有病名**的錯誤，
    呼叫端分不出「本入口不支援」與「壞掉了」。
    🔴 多標的**本來就到不了**這條路（`derive_event_split_from_plans` 之 Mapping 形式是
    `(plans, event_keys, feature_index_by_symbol)`，與本入口的位置參數對不上），
    所以正確處置是具名拒絕，不是在此造第二份多標的邏輯。
    """
    train, test, index = _canonical(records, bars)
    cfg = EventPipelineConfig(timeframes=(TF,), split=EventSplitConfig())
    with pytest.raises(ValueError, match="只支援單標的") as ei:
        EventSamplePipeline().run(
            records, bars, cfg,
            train_plan={SYM: (train, test)}, test_plan={SYM: (train, test)},
            feature_index=index, selected_timeframe=TF,
        )
    assert not isinstance(ei.value, AttributeError)
    assert "train_plan" in str(ei.value), "訊息須指名是哪一個參數不合格"
