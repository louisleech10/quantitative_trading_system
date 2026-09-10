"""SPLITUNIFY Task 4.1 驗證（-k splitunify_disclosure）：報告只暴露**一個**驗證段數字。

判準字面之唯一來源＝`docs/SPLITUNIFY_TODO.md` Task 4.1／SPEC C-6；本檔只把它機械化。

出生理由（本票的原始症狀）：同一批事件、同一次 UAT 會看到**兩個互相矛盾的驗證段數字**
（實測 31 vs 33）——一個來自事件側自己的切分，一個來自 K 線 holdout。

🔴 「哪些鍵帶『驗證段列數』語意」**不由本檔判斷**，而是讀
`momentum/Analysis/contracts/split_unify.json` 之 `test_segment_count_keys` 封閉登記
（`canonical` 恰一個；`diagnostic_only` 只在降級時出現且**值必須等於** canonical；
`row_semantics_not_event_count` 是 K 線列數，語意不同）。
散文判準會漂，封閉登記不會——這是本專案「文字問題用白名單機械卡」的既有紀律。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from momentum.Analysis.event_samples.split_projection import build_split_unify_disclosure
from momentum.core.split_preview import boundary_hash
from tests.momentum.helpers.ichc_run import feature_index, run_analyze

REPO = Path(__file__).resolve().parents[2]
CONTRACT = json.loads(
    (REPO / "momentum" / "Analysis" / "contracts" / "split_unify.json").read_text(encoding="utf-8")
)
KEYS = CONTRACT["test_segment_count_keys"]
CTX = {"event_manifest_hash": "1" * 64, "label_definition_hash": "2" * 64,
       "decision_time_rule": "t0_open_minus_k_bars",
       "feature_cutoff_rule": "max_close_ms_le_decision_at",
       "label_window_rule": "close_to_close:horizon_bars=2",
       "control_kind": "user_labeled_same_trigger"}


def _event_inputs(n: int):
    idx = feature_index(n)
    rng = np.random.default_rng(20260911 + n)
    lv = {int(t.value // 10 ** 6): float(v) for t, v in zip(idx, rng.normal(0, 0.02, len(idx)))}
    owners = {t: f"ev{i:03d}" for i, t in enumerate(lv)}
    return lv, owners


def _dig(node: dict, dotted: str):
    """依 dotted path 取值；缺任一層回 `_MISSING`（不回 None——None 是合法值）。"""
    cur = node
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


_MISSING = object()


@pytest.fixture(scope="module")
def event_report():
    """真實事件路徑 run（80 事件；`min_test_events=0` ⇒ 不降級，走正常 OOS 路徑）。"""
    lv, owners = _event_inputs(80)
    return run_analyze(
        {"event_filter": {"enabled": True, "min_events": 30, "min_test_events": 0}},
        event_timestamps=list(lv), event_label_values=lv,
        event_label_owners=owners, event_context=CTX,
    )


@pytest.fixture(scope="module")
def global_report():
    """全域（非事件）run——G-2：**不得**出現 `split_unify` 這些鍵。"""
    return run_analyze({"event_filter": {"enabled": False}})


# ── 契約自身之不變式（防「登記被改壞」）──────────────────────────────────
def test_splitunify_disclosure_contract_registry_is_wellformed():
    assert KEYS["canonical"] == "split_unify.n_test"
    overlap = set(KEYS["diagnostic_only"]) & set(KEYS["row_semantics_not_event_count"])
    assert overlap == set(), f"同一個鍵不能同時兩種語意：{overlap}"
    assert KEYS["canonical"] not in KEYS["diagnostic_only"]
    assert set(CONTRACT["split_unify_keys"]) == {
        "n_test", "split_authority", "boundary_hash", "per_symbol_counts", "reason"
    }


# ── ① 報告中帶「驗證段事件數」語意之鍵**恰 1 個** ──────────────────────────
def test_splitunify_disclosure_exactly_one_test_count_key(event_report):
    m = event_report["metadata"]
    present = [p for p in [KEYS["canonical"], *KEYS["diagnostic_only"]] if _dig(m, p) is not _MISSING]
    assert present == [KEYS["canonical"]], (
        f"帶『驗證段事件數』語意的鍵不只一個：{present}"
        "——這正是本票要消滅的症狀（同一批事件兩個互相矛盾的數字）"
    )


# ── ② canonical 揭露之鍵集與值 ────────────────────────────────────────────
def test_splitunify_disclosure_canonical_block_shape(event_report):
    su = event_report["metadata"]["split_unify"]
    assert set(su) == set(CONTRACT["split_unify_keys"])
    assert su["split_authority"] == CONTRACT["split_authority_values"][0] == "kline_holdout"
    assert su["reason"] is None
    assert isinstance(su["n_test"], int) and su["n_test"] > 0
    assert len(su["boundary_hash"]) == 64
    assert sum(su["per_symbol_counts"].values()) == su["n_test"]


# ── ③ 與 K 線列數語意之鍵並存時，不得矛盾 ─────────────────────────────────
def test_splitunify_disclosure_row_semantics_keys_are_a_different_quantity(event_report):
    """🔴 `test_rows` 是 **K 線列數**、`n_test` 是**事件數**——兩個不同的量，不是兩個矛盾的答案。

    實測（本 fixture）：`test_rows=335`、`n_test=13`——同一個 canonical 測試段裡有 335 根 K 線，
    其中 13 根上有事件。**這正是必須把語意講清楚的理由**：兩個數字都對，但只有一個是
    「驗證段事件數」。C-6 禁的是「同一個問題兩個答案」，不是禁止報告同時有列數與事件數。

    可證偽的不變式：事件是測試段列的**子集** ⇒ `0 < n_test <= test_rows`。
    若哪天 `n_test > test_rows`，代表兩者不再指同一段——本條會紅。
    """
    m = event_report["metadata"]
    su = m["split_unify"]
    rows = _dig(m, "ic_train_test_split.test_rows")
    assert rows is not _MISSING
    assert 0 < su["n_test"] <= int(rows), (
        f"split_unify.n_test={su['n_test']} 不是 ic_train_test_split.test_rows={rows} 的子集大小"
        "——兩者應指同一個 canonical 測試段"
    )
    # 且登記檔必須把 `test_rows` 歸在「列數語意」那一欄（不是診斷用事件數）
    assert "ic_train_test_split.test_rows" in KEYS["row_semantics_not_event_count"]


# ── ④ G-2：全域 run 不寫這些鍵 ────────────────────────────────────────────
def test_splitunify_disclosure_absent_on_global_run(global_report):
    assert "split_unify" not in global_report["metadata"], (
        "全域 run 寫了事件路徑專屬的鍵 ⇒ 全域報告不再逐位元組不變（G-2）"
    )


# ── ⑤ fail-closed 時 `n_test` 為 null 而非 0（純函式層，直接餵） ───────────
def test_splitunify_disclosure_fail_closed_is_null_not_zero():
    out = build_split_unify_disclosure(
        n_test=None, test_timestamps_ms=[], reason="multi_symbol_projection_unsupported"
    )
    assert out["n_test"] is None, "0 讀起來是『算過，結果是零個』——那是假數字"
    assert out["boundary_hash"] is None and out["per_symbol_counts"] == {}
    assert out["reason"] == "multi_symbol_projection_unsupported"
    assert out["split_authority"] == "kline_holdout"


def test_splitunify_disclosure_rejects_unregistered_reason():
    with pytest.raises(ValueError, match="不在契約封閉集合內"):
        build_split_unify_disclosure(n_test=None, test_timestamps_ms=[], reason="i_made_this_up")


def test_splitunify_disclosure_rejects_contradicting_per_symbol_counts():
    with pytest.raises(ValueError, match="per_symbol_counts 合計"):
        build_split_unify_disclosure(
            n_test=3, test_timestamps_ms=[1_700_000_000_000], per_symbol_counts={"ETHUSDT": 2}
        )


def test_splitunify_disclosure_requires_reason_when_n_test_missing():
    with pytest.raises(ValueError, match="必須指名原因"):
        build_split_unify_disclosure(n_test=None, test_timestamps_ms=[])


# ── ⑥ boundary_hash 之三個約束逐條可證偽 ──────────────────────────────────
def test_splitunify_disclosure_boundary_hash_is_order_insensitive():
    a = [1_700_000_000_000, 1_700_003_600_000, 1_700_007_200_000]
    assert boundary_hash(a) == boundary_hash(list(reversed(a))), "比的是集合，不是列舉順序"


def test_splitunify_disclosure_boundary_hash_changes_with_membership():
    a = [1_700_000_000_000, 1_700_003_600_000]
    b = [1_700_000_000_000, 1_700_007_200_000]
    assert boundary_hash(a) != boundary_hash(b), "換掉一個時刻卻同雜湊 ⇒ 這個雜湊沒有鑑別力"


def test_splitunify_disclosure_boundary_hash_rejects_seconds():
    with pytest.raises(ValueError, match="epoch seconds"):
        boundary_hash([1_700_000_000, 1_700_003_600])
