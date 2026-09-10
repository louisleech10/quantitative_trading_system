"""EVTLABEL Task 3.6：binary 統計進 summary_table、門檻分流、消費前三守衛。

SPEC：`docs/EVTLABEL_SPEC.md` Task 3.6　TODO：Task 3.6

## 這批測試在防什麼

1. **驗過的那一份被換掉**：stage3 驗完 0/1，stage5 用的是另一份。不會拋例外——
   統計照樣跑出數字，只是那些數字對應到別的列。
2. **強反向特徵被誤殺**：rank-biserial 為負代表「反向但一樣能分」。
   不取絕對值的門檻會把它砍掉，而使用者永遠不知道。
3. **報酬版門檻誤套**：`ic_mean`／`icir` 那幾道在匯入標籤模式下沒有意義，
   誤套會讓倖存者空無一人，而且看起來像是「特徵都不好」。

mutation（`--phase 3b`）：`M-P3-2`（p 閘讀報酬版 q）、`M-P3-5`（rows_frozenset 守衛拿掉）、
`M-P3-7`（效應量閘去 abs）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.core.contracts import AlignmentViolationError, ValidatedBinaryLabel, binary_label_digest

MS = 3_600_000
BINARY_INFO = {"label_source": "imported_binary_label"}


def _orch(rank_biserial_min: float = 0.10, min_per_class: int = 5) -> ICFilterOrchestrator:
    return ICFilterOrchestrator(ICConfig.model_validate({
        "event_filter": {"min_events_per_class": min_per_class},
        "thresholds": {"rank_biserial_min": rank_biserial_min},
    }))


def _fixture(n_pos: int = 20, n_neg: int = 20):
    """雙特徵：`good` 完全可分（正向）、`bad` 完全不可分。"""
    n = n_pos + n_neg
    idx = pd.to_datetime([1_700_000_000_000 + i * MS for i in range(n)], unit="ms")
    y = np.array([1] * n_pos + [0] * n_neg, dtype=int)
    rng = np.random.default_rng(3)
    feats = pd.DataFrame(
        {"good": y * 10.0 + rng.standard_normal(n) * 0.01, "bad": rng.standard_normal(n)},
        index=idx,
    )
    return feats, y


def _bind(orch, feats, y):
    ms = (feats.index.asi8 // 10**6).astype("int64")
    rows = frozenset((f"e{i}", int(t), int(v)) for i, (t, v) in enumerate(zip(ms, y)))
    series = pd.Series(y.astype(float), index=feats.index)
    frozen = series.copy()
    frozen.to_numpy().flags.writeable = False
    orch._ic_cache = {"event_binary_label": ValidatedBinaryLabel(
        series=frozen, digest=binary_label_digest(rows), rows_frozenset=rows,
        n_pos=int((y == 1).sum()), n_neg=int((y == 0).sum()),
    )}


def _table(feats):
    return [{"feature_name": c, "ic_mean": 0.001, "icir": 0.01, "p_value": 0.9,
             "p_value_adj": 0.9, "ic_hit_rate": 0.1, "monotonicity_score": 0.1,
             "coverage": 0.1} for c in feats.columns]


def _merge(orch, feats, y, table=None):
    table = _table(feats) if table is None else table
    is_binary = orch._merge_binary_statistics(
        table, feats, BINARY_INFO, orch._config, alpha_effective=0.05, fdr_method="fdr_bh",
    )
    return table, is_binary


# ══════════════════════════════════════════════════════════════════════════
# ① 統計進表
# ══════════════════════════════════════════════════════════════════════════


def test_binary_columns_are_added_with_standard_names():
    """表頭一律統計學標準名（使用者 2026-09-10），且報酬版欄位仍在（第二欄）。"""
    orch = _orch()
    feats, y = _fixture()
    _bind(orch, feats, y)
    table, is_binary = _merge(orch, feats, y)
    assert is_binary is True
    good = next(r for r in table if r["feature_name"] == "good")
    # 🔴 欄名以契約 `summary_columns_binary` 為準（前端 vitest 抓到我原本寫成 n_pos／n_neg）
    import json
    from pathlib import Path as _P

    contract = json.loads(
        (_P(__file__).resolve().parents[3] / "momentum/Analysis/contracts/event_label_mode.json")
        .read_text(encoding="utf-8")
    )
    for col in contract["summary_columns_binary"]:
        assert col in good, f"缺欄 {col}"
    assert good["auc"] == pytest.approx(1.0, abs=1e-12)
    assert good["rank_biserial"] == pytest.approx(1.0, abs=1e-12)
    assert good["ic_mean"] == 0.001, "報酬版 IC 必須原樣保留為第二欄"


def test_return_rule_run_is_untouched():
    """非 binary run ⇒ 回 False、表一字不動（全域與報酬版路徑逐位元組不變）。"""
    orch = _orch()
    feats, y = _fixture()
    table = _table(feats)
    before = [dict(r) for r in table]
    is_binary = orch._merge_binary_statistics(
        table, feats, {"label_source": "event_label_value"}, orch._config,
        alpha_effective=0.05, fdr_method="fdr_bh",
    )
    assert is_binary is False and table == before


def test_missing_validated_label_fails_closed():
    """宣稱 binary 卻沒有 stage3 交付的物件 ⇒ raise（不得靜默跳過統計）。"""
    orch = _orch()
    feats, y = _fixture()
    orch._ic_cache = {}
    with pytest.raises(AlignmentViolationError, match="沒有交付"):
        _merge(orch, feats, y)


# ══════════════════════════════════════════════════════════════════════════
# ② 消費前三守衛
# ══════════════════════════════════════════════════════════════════════════


def test_swapped_cache_is_caught(monkeypatch):
    """🔴 `M-P3-5`：把 cache 換成另一份向量 ⇒ 必須 raise。

    這是「驗過的 ≠ 用掉的」之直接反例。
    """
    orch = _orch()
    feats, y = _fixture()
    _bind(orch, feats, y)
    flipped = 1 - y
    series = pd.Series(flipped.astype(float), index=feats.index)
    vb = orch._ic_cache["event_binary_label"]
    orch._ic_cache["event_binary_label"] = ValidatedBinaryLabel(
        series=series, digest=vb.digest, rows_frozenset=vb.rows_frozenset,
        n_pos=vb.n_pos, n_neg=vb.n_neg,
    )
    with pytest.raises(AlignmentViolationError, match="consumed != validated"):
        _merge(orch, feats, y)


def test_row_not_in_validated_set_is_caught():
    """某一列的值不在驗過的三元組集合裡 ⇒ raise，並指出是哪一列。"""
    orch = _orch()
    feats, y = _fixture()
    _bind(orch, feats, y)
    vb = orch._ic_cache["event_binary_label"]
    trimmed = frozenset(r for r in vb.rows_frozenset if r[1] != int(feats.index[0].value // 10**6))
    orch._ic_cache["event_binary_label"] = ValidatedBinaryLabel(
        series=vb.series, digest=vb.digest, rows_frozenset=trimmed, n_pos=vb.n_pos, n_neg=vb.n_neg,
    )
    with pytest.raises(AlignmentViolationError, match="不在驗過的集合"):
        _merge(orch, feats, y)


def test_selection_row_missing_from_validated_vector_is_caught():
    """selection 有列不在驗過的向量裡（reindex 出 NaN）⇒ raise。"""
    orch = _orch()
    feats, y = _fixture()
    _bind(orch, feats, y)
    extra_idx = feats.index.append(pd.to_datetime([1_700_000_000_000 + 999 * MS], unit="ms"))
    wider = feats.reindex(extra_idx).fillna(0.0)
    # 🔴 `M-P3-5b`：必須由**守衛①**（index 對齊）擋下，訊息要指名「有列不在驗過的向量裡」。
    #    只斷言「有 raise」是不夠的——守衛③（逐列子集）也會擋下同一個輸入，
    #    於是拿掉守衛① 仍然綠。mutation 首跑正是這樣漏掉的。
    with pytest.raises(AlignmentViolationError, match="有列不在驗過的 0/1 向量裡"):
        orch._merge_binary_statistics(
            _table(wider), wider, BINARY_INFO, orch._config,
            alpha_effective=0.05, fdr_method="fdr_bh",
        )


def test_guard_uses_row_subset_not_digest_equality():
    """碼證：守衛是**子集檢查**不是 digest 相等——digest 說不出是哪幾列被換掉。"""
    import inspect

    src = inspect.getsource(ICFilterOrchestrator._merge_binary_statistics)
    assert "rows_frozenset" in src
    assert "vb.digest ==" not in src and "digest !=" not in src


# ══════════════════════════════════════════════════════════════════════════
# ③ 門檻分流
# ══════════════════════════════════════════════════════════════════════════


def _thresholds(orch, table):
    """回 (passed, removed)——`removed` 住在 threshold_log["removed_features"]。"""
    passed, log = orch._apply_thresholds(table, orch._config.thresholds, 0.05,
                                         fdr_enabled=True, icir_gate=False, binary_mode=True)
    return passed, log["removed_features"]


def test_return_rule_gates_are_skipped_not_applied():
    """🔴 報酬版門檻在 binary 模式下**記錄但不剔除**。

    fixture 刻意把 ic_mean／icir／coverage 全設成遠低於門檻——若誤套，倖存者會是 0，
    而使用者看到的會是「特徵都不好」而不是「門檻套錯了」。
    """
    orch = _orch()
    feats, y = _fixture()
    _bind(orch, feats, y)
    table, _ = _merge(orch, feats, y)
    passed, log = _thresholds(orch, table)
    assert "good" in passed, "完全可分之特徵不得被報酬版門檻砍掉"
    for gate in ("ic_mean", "icir", "ic_hit_rate", "monotonicity", "coverage", "long_short_spread"):
        assert "good" in log[f"{gate}_skipped_binary_mode"], f"{gate} 應記錄而非剔除"
        assert "good" not in log[gate]


def test_effect_gate_reads_absolute_rank_biserial():
    """🔴 `M-P3-7`：反向但一樣能分（rank-biserial ≈ −1）**必須**通過。"""
    orch = _orch()
    feats, y = _fixture()
    _bind(orch, feats, 1 - y)                      # 標籤翻轉 ⇒ good 變成強反向
    table, _ = _merge(orch, feats, 1 - y)
    good = next(r for r in table if r["feature_name"] == "good")
    assert good["rank_biserial"] < -0.9, "fixture 應產生強反向"
    passed, log = _thresholds(orch, table)
    assert "good" in passed and "good" not in log["rank_biserial"]


def test_weak_feature_removed_by_effect_gate():
    """效應量不足 ⇒ 進 `removed["rank_biserial"]`（門檻確實在作用，不是裝飾）。"""
    orch = _orch(rank_biserial_min=0.9)
    feats, y = _fixture()
    _bind(orch, feats, y)
    table, _ = _merge(orch, feats, y)
    passed, log = _thresholds(orch, table)
    assert "bad" in log["rank_biserial"] and "bad" not in passed


def test_p_gate_reads_mann_whitney_q_not_return_q():
    """🔴 `M-P3-2`：p 閘必須讀 `mw_p_value_adj`。

    fixture 把報酬版 q 設成 0.9（會被砍），MW 的 q 極小（應通過）。
    讀錯欄位 ⇒ 完全可分的特徵被砍，而數字看起來都很正常。
    """
    orch = _orch()
    feats, y = _fixture()
    _bind(orch, feats, y)
    table, _ = _merge(orch, feats, y)
    good = next(r for r in table if r["feature_name"] == "good")
    assert good["p_value_adj"] == 0.9 and good["mw_p_value_adj"] < 0.05
    passed, log = _thresholds(orch, table)
    assert "good" in passed and "good" not in log["p_value"]


def test_unavailable_status_is_removed_with_its_own_key():
    """`binary_status != ok` ⇒ 進 `removed["binary_unavailable"]`，不與效應量閘混為一談。"""
    orch = _orch(min_per_class=999)                # 逼出 class_below_min
    feats, y = _fixture()
    _bind(orch, feats, y)
    table, _ = _merge(orch, feats, y)
    passed, log = _thresholds(orch, table)
    assert passed == []
    assert set(log["binary_unavailable"]) == {"good", "bad"}
    assert log["rank_biserial"] == []


def test_return_rule_thresholds_unchanged_without_kwarg():
    """既有呼叫不傳 `binary_mode` ⇒ 行為一字不變（全域路徑不受影響）。"""
    orch = _orch()
    table = [{"feature_name": "f", "ic_mean": 0.5, "icir": 5.0, "p_value_adj": 0.001,
              "ic_hit_rate": 0.9, "monotonicity_score": 0.9, "coverage": 0.9}]
    passed, log = orch._apply_thresholds(table, orch._config.thresholds, 0.05)
    removed = log["removed_features"]
    assert passed == ["f"]
    assert "rank_biserial" not in removed and "binary_unavailable" not in removed


# ══════════════════════════════════════════════════════════════════════════
# ④ 冗餘分數與揭露（Task 3.6 要點 5；B4 brief 曾具名為「未實作」，本批補上）
# ══════════════════════════════════════════════════════════════════════════


def test_redundancy_score_uses_abs_rank_biserial_in_binary_mode():
    """🔴 匯入標籤模式下，冗餘挑選必須用**主統計**當分數。

    兩個高度相關的特徵只能留一個。若仍用報酬版 `ic_mean` 當分數，留下來的會是
    「報酬版 IC 較高」那一個——而使用者要的是**分辨力**較強的那一個。
    """
    orch = _orch()
    stage5 = {"summary_table": [
        {"feature_name": "strong_reverse", "ic_mean": 0.001, "rank_biserial": -0.90},
        {"feature_name": "weak_forward", "ic_mean": 0.500, "rank_biserial": 0.10},
    ]}
    scores, tiebreaker = orch._redundancy_scores(BINARY_INFO, stage5, {"strong_reverse": 9.9})
    assert tiebreaker == "abs_rank_biserial"
    assert scores["strong_reverse"] == pytest.approx(0.90)
    assert scores["weak_forward"] == pytest.approx(0.10)
    assert scores["strong_reverse"] > scores["weak_forward"], "強反向必須贏過弱正向"


def test_redundancy_score_unchanged_for_return_rule_event_run():
    """報酬版事件 run 之行為一字不變（仍用 ic_mean）。"""
    orch = _orch()
    stage5 = {"summary_table": [{"feature_name": "f", "ic_mean": 0.3, "rank_biserial": -0.9}]}
    scores, tiebreaker = orch._redundancy_scores(
        {"label_source": "event_label_value"}, stage5, {"f": 1.0})
    assert tiebreaker == "ic_mean" and scores["f"] == 0.3


def test_redundancy_score_unchanged_for_global_run():
    """全域 run：原樣回 icir_scores、不寫 tiebreaker 鍵。"""
    orch = _orch()
    scores, tiebreaker = orch._redundancy_scores(None, {"summary_table": []}, {"f": 2.0})
    assert scores == {"f": 2.0} and tiebreaker is None


def test_non_finite_rank_biserial_sinks_to_bottom():
    """算不出 rank-biserial 的欄不得在冗餘挑選裡勝出 ⇒ 沉到 -inf。"""
    orch = _orch()
    stage5 = {"summary_table": [{"feature_name": "dead", "ic_mean": 0.9, "rank_biserial": float("nan")}]}
    scores, _ = orch._redundancy_scores(BINARY_INFO, stage5, {})
    assert scores["dead"] == float("-inf")


def test_third_guard_verifies_the_full_triple_including_owner():
    """🔴 `CODEX-R1-P2-01`：第三道守衛原本只比 `(ts, label)`，`owners` 建了卻沒用。

    事件 id 被換掉但 (ts, label) 還對得上時，舊版仍會放行。現在以 ts 反查所屬事件，
    三項全等才算同一份；訊息要指名是哪個事件。
    """
    import inspect

    src = inspect.getsource(ICFilterOrchestrator._merge_binary_statistics)
    assert "by_ts" in src and "entry[0]" in src, "守衛未使用 event id"
    assert "assert owners is not None" not in src, "不得再留沒用到的 owners"

    orch = _orch()
    feats, y = _fixture()
    _bind(orch, feats, y)
    vb = orch._ic_cache["event_binary_label"]
    # 值被翻轉但時間戳仍在集合裡 ⇒ 必須被抓到，且訊息指名事件
    flipped = frozenset((eid, ts, 1 - val) for eid, ts, val in vb.rows_frozenset)
    orch._ic_cache["event_binary_label"] = ValidatedBinaryLabel(
        series=vb.series, digest=vb.digest, rows_frozenset=flipped,
        n_pos=vb.n_pos, n_neg=vb.n_neg,
    )
    with pytest.raises(AlignmentViolationError, match="事件"):
        _merge(orch, feats, y)


def test_every_row_gets_binary_keys_even_when_unavailable():
    """🔴 前端以「第一列有無 `rank_biserial`」判是不是 binary 模式。

    若 `binary_status != ok` 的欄不寫該鍵，而它剛好排第一列，整張表就會退回報酬版版面
    ——使用者會看不到主統計。故**每一列都要有這幾個鍵**，不分 status。
    （B5 review brief 必答 5 之自我驗證。）
    """
    orch = _orch(min_per_class=999)          # 逼出 class_below_min ⇒ 全部 unavailable
    feats, y = _fixture()
    _bind(orch, feats, y)
    table, _ = _merge(orch, feats, y)
    assert all(str(r["binary_status"]) != "ok" for r in table), "fixture 應全部不可用"
    for row in table:
        assert "rank_biserial" in row, f"{row['feature_name']} 不可用但仍須有主統計鍵"
        assert "auc" in row and "mw_p_value_adj" in row
