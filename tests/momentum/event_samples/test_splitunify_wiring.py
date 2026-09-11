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
from momentum.core.contracts import SplitPlan
from momentum.core.split_preview import holdout_boundary
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
    kw = dict(index_kind="positional", purge_gap=PURGE, embargo=EMBARGO,
              purge_semantic="rows", base_universe_hash="deadbeef", symbol=SYM)
    train = SplitPlan(split_label="train", row_index=b["train_row_index"],
                      time_bounds=(int(index[0]), int(index[b["train_row_index"][-1]])), **kw)
    test = SplitPlan(split_label="test", row_index=b["test_row_index"],
                     time_bounds=(int(index[b["test_row_index"][0]]), int(index[-1])), **kw)
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
@pytest.mark.parametrize("drop", ["train_plan", "test_plan", "feature_index", "selected_timeframe"])
def test_splitunify_wiring_partial_boundary_is_fail_closed(records, bars, spy_split, drop):
    train, test, index = _canonical(records, bars)
    kwargs = {"train_plan": train, "test_plan": test, "feature_index": index, "selected_timeframe": TF}
    kwargs[drop] = None
    with pytest.raises(ValueError, match="必須同時給齊"):
        EventSamplePipeline().run(records, bars, EventPipelineConfig(timeframes=(TF,)), **kwargs)
    assert spy_split == [], "缺參數時退回歷史切分＝呼叫端以為自己用的是統一後的邊界"


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
