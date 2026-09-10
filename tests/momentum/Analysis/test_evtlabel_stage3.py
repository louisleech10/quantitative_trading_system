"""EVTLABEL Task 3.4：stage3 之 effective mode 決策與 0/1 綁定驗證。

SPEC：`docs/EVTLABEL_SPEC.md` Task 3.4　TODO：Task 3.4

## 這批測試在防什麼

三件事，每一件錯了都不會拋例外：

1. **分母用錯**：整批 136 正／29 反看起來很夠，但統計是在**驗證段**上做的。
   驗證段可能只剩 2 個反例——用整批當分母就會放行一個做不出統計的 run。
2. **靜默降級**：使用者明講要用 0/1，卻拿到一份報酬版報告而報告上看不出來。
3. **驗過的那一份被換掉**：stage3 驗完 0/1，stage5 拿到的是另一份。

mutation（`--phase 3b`）：`M-P3-3`（binary 不過 validate_event_given）⇒ 錯位測試紅。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.core.contracts import AlignmentViolationError

MS = 3_600_000


def _orch(min_per_class: int = 10) -> ICFilterOrchestrator:
    return ICFilterOrchestrator(
        ICConfig.model_validate({"event_filter": {"min_events_per_class": min_per_class}})
    )


def _features(n: int) -> pd.DataFrame:
    idx = pd.to_datetime([1_700_000_000_000 + i * MS for i in range(n)], unit="ms")
    return pd.DataFrame({"f1": np.linspace(0.0, 1.0, n)}, index=idx)


def _labels(feats: pd.DataFrame, pattern) -> dict:
    """{feature_cutoff_ms: 0/1}，與 features index 同鍵。"""
    ms = (feats.index.asi8 // 10**6).astype("int64")
    return {int(t): int(v) for t, v in zip(ms, pattern)}


def _owners(feats: pd.DataFrame) -> dict:
    ms = (feats.index.asi8 // 10**6).astype("int64")
    return {int(t): f"e{i}" for i, t in enumerate(ms)}


def _bind(orch, feats, binary, *, requested="auto", test_rows=None, hint=None, info=None,
          test_timestamps=None):
    """`test_rows`＝要當作測試段的**位置**（相對本 fixture）；轉成時間戳交給實作。

    🔴 `CODEX-R1-P1-02`：實作已改吃 canonical 測試段**時間戳**，不再吃位置遮罩——
    因為 `filtered_features` 是事件子集，而遮罩長度是全表，直接套會 IndexError。
    """
    if test_timestamps is None and test_rows is not None:
        test_timestamps = feats.index[np.asarray(test_rows)]
    return orch._resolve_label_mode_and_bind_binary(
        dict(info or {"label_source": "event_label_value"}),
        filtered_features=feats,
        event_binary_labels=binary,
        label_mode_requested=requested,
        label_mode_hint=hint,
        split_context=None if test_timestamps is None else {"test_timestamps": test_timestamps},
        event_label_owners=_owners(feats),
        config=orch._config,
        label_source="event_label_value",
    )


# ══════════════════════════════════════════════════════════════════════════
# ① selection scope：分母是驗證段，不是整批
# ══════════════════════════════════════════════════════════════════════════


def test_denominator_is_the_test_segment_not_the_whole_batch():
    """🔴 承重條：整批很夠但驗證段不夠 ⇒ 必須退回報酬版。

    整批 30 正／30 反（遠超門檻 10），但驗證段（最後 12 列）只有 2 個反例。
    統計是在驗證段上做的，分母就必須是驗證段。
    """
    feats = _features(60)
    pattern = [1] * 30 + [0] * 30
    binary = _labels(feats, pattern)
    test_rows = np.arange(48, 60)              # 最後 12 列
    # 讓驗證段呈 10 正 / 2 反
    pattern2 = [1] * 30 + [0] * 18 + [1] * 10 + [0] * 2
    binary2 = _labels(feats, pattern2)

    out = _bind(_orch(), feats, binary2, test_rows=test_rows)
    lm = out["label_mode"]
    assert lm["selection_scope"] == "test"
    assert (lm["n_pos_selection"], lm["n_neg_selection"]) == (10, 2)
    assert lm["n_pos_batch"] == 40 and lm["n_neg_batch"] == 20, "整批計數仍要揭露供對照"
    assert lm["effective"] == "return_rule" and lm["reason"] == "class_below_min_selection"
    assert len(binary) == 60  # 未被就地改動


def test_no_split_falls_back_to_full_sample_scope():
    """無切分（fallback）⇒ scope=full_sample，並據此判定（不是直接放棄）。"""
    feats = _features(40)
    binary = _labels(feats, [1] * 20 + [0] * 20)
    out = _bind(_orch(), feats, binary, test_rows=None)
    lm = out["label_mode"]
    assert lm["selection_scope"] == "full_sample"
    assert (lm["n_pos_selection"], lm["n_neg_selection"]) == (20, 20)
    assert lm["effective"] == "imported_binary"


def test_one_class_in_selection_gets_its_own_reason():
    """驗證段單類 ⇒ `one_class`（與「有兩類但太少」是不同的原因）。"""
    feats = _features(40)
    binary = _labels(feats, [1] * 20 + [0] * 8 + [1] * 12)
    out = _bind(_orch(), feats, binary, test_rows=np.arange(28, 40))   # 最後 12 列全是 1
    assert out["label_mode"]["effective"] == "return_rule"
    assert out["label_mode"]["reason"] == "one_class"


# ══════════════════════════════════════════════════════════════════════════
# ② 明示模式不得靜默降級
# ══════════════════════════════════════════════════════════════════════════


def test_explicit_mode_raises_instead_of_downgrading():
    """🔴 明示 `imported_binary` 遇不足 ⇒ raise；訊息要說出實際數字與門檻。"""
    feats = _features(40)
    binary = _labels(feats, [1] * 20 + [0] * 8 + [1] * 10 + [0] * 2)
    with pytest.raises(ValueError, match="class_below_min_selection"):
        _bind(_orch(), feats, binary, requested="imported_binary", test_rows=np.arange(28, 40))


def test_auto_records_hint_when_no_binary_available():
    """`auto` 且這批根本沒有 0/1 ⇒ 退回報酬版，reason 用 staging 給的 hint。"""
    feats = _features(20)
    out = _bind(_orch(), feats, None, hint="label_invalid_domain")
    assert out["label_mode"]["effective"] == "return_rule"
    assert out["label_mode"]["reason"] == "label_invalid_domain"


def test_return_rule_request_never_binds_binary():
    """使用者明講只用報酬版 ⇒ 即使 0/1 充足也不綁。"""
    feats = _features(40)
    binary = _labels(feats, [1] * 20 + [0] * 20)
    orch = _orch()
    out = _bind(orch, feats, binary, requested="return_rule")
    assert out["label_mode"]["effective"] == "return_rule"
    assert out["label_mode"]["reason"] is None
    assert orch._ic_cache["event_binary_label"] is None


def test_abandoned_conditional_ic_marks_unavailable():
    """事件不足已棄條件 IC ⇒ 標 `binary_discrimination_unavailable`，不假裝可用。"""
    feats = _features(40)
    binary = _labels(feats, [1] * 20 + [0] * 20)
    out = _bind(_orch(), feats, binary,
                info={"label_source": "event_label_value", "conditional_ic_abandoned": True})
    assert out["label_mode"]["effective"] == "return_rule"
    assert out["label_mode"]["reason"] == "conditional_ic_abandoned"
    assert out["statistic_kind"] == "binary_discrimination_unavailable"


# ══════════════════════════════════════════════════════════════════════════
# ③ 綁定：過同一條契約、封成不可變、留下可回綁的三元組
# ══════════════════════════════════════════════════════════════════════════


def test_binding_writes_source_kind_and_digest():
    feats = _features(40)
    binary = _labels(feats, [1] * 20 + [0] * 20)
    orch = _orch()
    out = _bind(orch, feats, binary)
    assert out["label_source"] == "imported_binary_label"
    assert out["statistic_kind"] == "binary_discrimination"
    assert out["secondary_statistic"] == "conditional_ic", "報酬版 IC 留第二欄"
    assert len(out["binary_label_digest"]) == 64
    vb = orch._ic_cache["event_binary_label"]
    assert vb.n_pos == 20 and vb.n_neg == 20
    assert vb.digest == out["binary_label_digest"]
    assert len(vb.rows_frozenset) == 40


def test_bound_series_is_immutable():
    """🔴 驗過的那一份不得被就地改：stage5 若 `iloc[...]=` 會 ValueError。"""
    feats = _features(40)
    orch = _orch()
    _bind(orch, feats, _labels(feats, [1] * 20 + [0] * 20))
    vb = orch._ic_cache["event_binary_label"]
    with pytest.raises(ValueError):
        vb.series.iloc[0] = 999.0


def test_consumed_rows_carry_timestamp_not_just_value():
    """🔴 回綁必須含時間戳——多個事件共用同一個值時，只有值比不出對調。"""
    feats = _features(40)
    orch = _orch()
    out = _bind(orch, feats, _labels(feats, [1] * 20 + [0] * 20))
    rows = out["consumed_event_binary_rows"]
    assert len(rows) == 40
    ms0 = int(feats.index[0].value // 10**6)
    assert rows["e0"] == (ms0, 1)
    assert all(isinstance(v, tuple) and len(v) == 2 for v in rows.values())


def test_missing_key_for_a_selected_row_raises():
    """邊界②：被選中的列在 0/1 map 裡查不到 ⇒ raise（不得以 NaN 補）。"""
    feats = _features(40)
    binary = _labels(feats, [1] * 20 + [0] * 20)
    binary.pop(sorted(binary)[5])
    with pytest.raises(AlignmentViolationError, match="missing"):
        _bind(_orch(), feats, binary)


def test_binary_vector_goes_through_the_shared_contract():
    """🔴 `M-P3-3`：0/1 向量必須**真的**走 `validate_consumed_label` 的 event_given 分派。

    怎麼證明「有走」：挑一個**只有那條契約會抓**的違規——兩個被消費的列綁到同一個
    `event_id`。值域、缺鍵、長度都正常，唯一不對的是事件綁定。
    契約沒被呼叫（例如 `label_kind` 被改成 None）⇒ 不會 raise ⇒ 本條紅。

    🔴 為什麼不用「值被掉包」當反例：`bvals` 就是從 `event_binary_labels` 建的，
    而契約比對的 `expected_values` 也是同一份 ⇒ 那條「逐值相等」在本路徑**結構上不可達**。
    mutation 首跑正是因為用了不可達的反例而漏掉這條。
    """
    feats = _features(40)
    binary = _labels(feats, [1] * 20 + [0] * 20)
    ms = (feats.index.asi8 // 10**6).astype("int64")
    dup_owners = {int(t): "same-event" for t in ms}      # 全部綁到同一個事件
    orch = _orch()
    with pytest.raises(AlignmentViolationError, match="more than one consumed row"):
        orch._resolve_label_mode_and_bind_binary(
            {"label_source": "event_label_value"},
            filtered_features=feats,
            event_binary_labels=binary,
            label_mode_requested="auto",
            label_mode_hint=None,
            split_context=None,
            event_label_owners=dup_owners,
            config=orch._config,
            label_source="event_label_value",
        )


def test_binary_vector_missing_owner_is_caught_by_the_contract():
    """同一條契約的另一道：被消費的列沒有任何事件綁得上 ⇒ raise。"""
    feats = _features(40)
    binary = _labels(feats, [1] * 20 + [0] * 20)
    owners = _owners(feats)
    owners.pop(sorted(owners)[0])
    orch = _orch()
    with pytest.raises(AlignmentViolationError, match="no event_id bound"):
        orch._resolve_label_mode_and_bind_binary(
            {"label_source": "event_label_value"},
            filtered_features=feats,
            event_binary_labels=binary,
            label_mode_requested="auto",
            label_mode_hint=None,
            split_context=None,
            event_label_owners=owners,
            config=orch._config,
            label_source="event_label_value",
        )


def test_return_rule_info_keys_unchanged():
    """報酬版路徑之既有鍵一字不動（只多 `label_mode` 揭露）。"""
    feats = _features(40)
    before = {"label_source": "event_label_value", "statistic_kind": "conditional_ic",
              "consumed_event_labels": {"e0": 0.05}}
    out = _bind(_orch(), feats, None, requested="return_rule", info=before)
    for key, value in before.items():
        assert out[key] == value, f"{key} 被改動"
    assert set(out) - set(before) == {"label_mode"}


def test_sparse_event_subset_with_full_frame_test_segment():
    """🔴 `CODEX-R1-P1-02`：事件子集只有 3 列，而全表測試段有 10 列。

    舊實作把**全表長度**的布林遮罩套在稀疏子集上 ⇒
    `IndexError: Boolean index has wrong length`（codex 實跑 10 vs 3）。
    現在兩邊都以時間戳表達、取交集，長度不匹配的問題結構上不存在。
    """
    full = _features(40)                       # 全表 40 列
    events = full.iloc[[30, 34, 38]]           # 事件只有 3 列，全都落在測試段內
    binary = {int(t): int(v) for t, v in
              zip((events.index.asi8 // 10**6).astype("int64"), [1, 0, 1])}
    test_timestamps = full.index[30:40]        # 全表測試段 10 列
    orch = _orch(min_per_class=1)
    out = orch._resolve_label_mode_and_bind_binary(
        {"label_source": "event_label_value"},
        filtered_features=events,
        event_binary_labels=binary,
        label_mode_requested="auto",
        label_mode_hint=None,
        split_context={"test_timestamps": test_timestamps},
        event_label_owners={int(t): f"e{i}" for i, t in
                            enumerate((events.index.asi8 // 10**6).astype("int64"))},
        config=orch._config,
        label_source="event_label_value",
    )
    lm = out["label_mode"]
    assert lm["selection_scope"] == "test"
    assert (lm["n_pos_selection"], lm["n_neg_selection"]) == (2, 1)
    assert lm["effective"] == "imported_binary"


def test_events_outside_the_test_segment_are_not_counted():
    """事件落在訓練段 ⇒ 不算進 selection（交集語意的另一面）。"""
    full = _features(40)
    events = full.iloc[[2, 5, 34]]             # 前兩個在訓練段，只有一個在測試段
    binary = {int(t): int(v) for t, v in
              zip((events.index.asi8 // 10**6).astype("int64"), [1, 0, 1])}
    orch = _orch(min_per_class=1)
    out = orch._resolve_label_mode_and_bind_binary(
        {"label_source": "event_label_value"},
        filtered_features=events, event_binary_labels=binary,
        label_mode_requested="auto", label_mode_hint=None,
        split_context={"test_timestamps": full.index[30:40]},
        event_label_owners={int(t): f"e{i}" for i, t in
                            enumerate((events.index.asi8 // 10**6).astype("int64"))},
        config=orch._config, label_source="event_label_value",
    )
    lm = out["label_mode"]
    assert (lm["n_pos_selection"], lm["n_neg_selection"]) == (1, 0)
    assert lm["reason"] == "one_class"
