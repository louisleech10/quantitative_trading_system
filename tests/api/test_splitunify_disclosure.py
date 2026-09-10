"""SPLITUNIFY Task 4.1 驗證（-k splitunify_disclosure）：報告只暴露**一個**驗證段數字。

判準字面之唯一來源＝`docs/SPLITUNIFY_TODO.md` Task 4.1／SPEC C-6；本檔只把它機械化。

出生理由（本票的原始症狀）：同一批事件、同一次 UAT 會看到**兩個互相矛盾的驗證段數字**
（實測 31 vs 33）——一個來自事件側自己的切分，一個來自 K 線 holdout。

🔴 判準是 **deny-by-default**（B4 review R1 三家獨立命中後改強）：
掃**整份 report**（不只 `metadata`）中「鍵名含 `test` 且值為整數」的鍵，每一個都必須落在
`momentum/Analysis/contracts/split_unify.json` 之 `test_segment_count_keys` 四個桶之一，
否則紅 ⇒ **新鍵得先進契約才寫得出去**。
原版只掃 `metadata` 且只做正向計數，codex 實測注入
`summary_table[0].verification_test_event_count` 與 `validation.test_event_count` **未被抓到**。

🔴 「恰一個」之實作形式：canonical 恰一個（`metadata.split_unify.n_test`），
其餘同語意鍵**必須逐值等於** canonical。實測顯示同一個數字在報告裡本來就出現在 **7 處**
（`marginal_ic.n_test`、`event_filter.split_mask.test_rows`、`filter_log…` 等），
逐一刪除會波及本票以外的消費者；真正要禁的是**同一個問題兩個不同答案**（症狀 31 vs 33）。
此偏離（C-6 字面寫「恰一個鍵」）已具名記錄於契約 `_test_segment_count_keys_doc` 並送 R2 審。
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

#: 🔴 deny-by-default 掃描之候選判準（B4 review R1 三家獨立命中）：
#: 鍵名含 `test`（大小寫不拘）且值為**整數**（`bool` 不算）者，一律是候選。
#: 用「含 test」而不是列舉鍵名——黑名單永遠列不完（本專案既有紀律），
#: 而候選必須落進契約四個桶之一，否則紅 ⇒ **新鍵得先進契約才寫得出去**。
def _scan_test_int_paths(node, prefix: str = ""):
    """回 {正規化 dotted path: 值}。list 索引與 per-feature 名一律正規化為 `*`。"""
    out: dict = {}
    if isinstance(node, dict):
        for k, v in node.items():
            key = str(k)
            path = f"{prefix}.{key}" if prefix else key
            if "test" in key.lower() and isinstance(v, int) and not isinstance(v, bool):
                out[_normalize_path(path)] = v
            out.update(_scan_test_int_paths(v, path))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.update(_scan_test_int_paths(v, f"{prefix}[{i}]"))
    return out


def _normalize_path(path: str) -> str:
    """`marginal_ic.per_feature.<名>.n_used_test` → `marginal_ic.per_feature.*.n_used_test`；
    `marginal_ic.sequential[0]...` → `marginal_ic.sequential[*]...`；
    `summary_table[3]...` → `summary_table[*]...`。"""
    import re

    normalized = re.sub(r"\[\d+\]", "[*]", path)
    return re.sub(r"(per_feature)\.[^.]+\.", r"\1.*.", normalized)


def _registry_paths() -> set:
    return {
        KEYS["canonical"],
        *KEYS["must_equal_canonical_on_event_path"],
        *KEYS["row_semantics_not_event_count"],
        *KEYS["not_a_segment_count"],
    }


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
def degraded_report():
    """降級 run（`min_test_events` 拉到 10000 ⇒ `insufficient_test_events`）。

    🔴 出生理由（`GROK-R1-P1-01`）：`oos_downgrade.*` 與 `ic_train_test_split.test_events`
    **只在這條路徑才寫**——只驗 happy path 的話，那三個孿生鍵永遠不會被掃到。
    """
    lv, owners = _event_inputs(80)
    return run_analyze(
        {"event_filter": {"enabled": True, "min_events": 30, "min_test_events": 10000}},
        event_timestamps=list(lv), event_label_values=lv,
        event_label_owners=owners, event_context=CTX,
    )


@pytest.fixture(scope="module")
def global_report():
    """全域（非事件）run——G-2：**不得**出現 `split_unify` 這些鍵。"""
    return run_analyze({"event_filter": {"enabled": False}})


# ── 契約自身之不變式（防「登記被改壞」）──────────────────────────────────
def test_splitunify_disclosure_contract_registry_is_wellformed():
    assert KEYS["canonical"] == "metadata.split_unify.n_test"
    buckets = ("must_equal_canonical_on_event_path", "row_semantics_not_event_count", "not_a_segment_count")
    seen: dict = {}
    for b in buckets:
        for p in KEYS[b]:
            assert p not in seen, f"{p} 同時列在 {seen[p]} 與 {b}——一個鍵只能有一種語意"
            seen[p] = b
        assert KEYS["canonical"] not in KEYS[b], f"canonical 不得同時列在 {b}"
    assert set(CONTRACT["split_unify_keys"]) == {
        "n_test", "split_authority", "boundary_hash", "per_symbol_counts", "reason"
    }


# ── ①-a 🔴 deny-by-default：整份 report 的候選鍵都必須已登記 ─────────────────
@pytest.mark.parametrize("fixture_name", ["event_report", "degraded_report", "global_report"])
def test_splitunify_disclosure_no_unregistered_test_count_key(fixture_name, request):
    """未登記的「含 test 之整數鍵」一律紅——**新鍵得先進契約才寫得出去**。

    出生理由（`CODEX-R1-P1-01`／`COMPOSER-R1-P1-01`／`GROK-R1-P2-03` 三家獨立命中）：
    原版只掃 `metadata` 且只做**正向計數**，codex 實測把
    `summary_table[0].verification_test_event_count` 與 `validation.test_event_count`
    注入報告後，測試**照樣綠**。正向計數擋不住新增的鍵；deny-by-default 才擋得住。
    """
    report = request.getfixturevalue(fixture_name)
    unregistered = sorted(set(_scan_test_int_paths(report)) - _registry_paths())
    assert unregistered == [], (
        f"報告出現未登記的『含 test 之整數鍵』：{unregistered}——"
        "請先到 momentum/Analysis/contracts/split_unify.json 的 test_segment_count_keys 歸類語意"
    )


def test_splitunify_disclosure_denylist_catches_injected_key(event_report):
    """🔴 可證偽：把 codex 的注入原樣重放一次，掃描**必須**抓到它。

    沒有這條，上面那條「未登記為空」可能只是因為掃描器根本沒在掃。
    """
    injected = {
        **event_report,
        "summary_table": [{"verification_test_event_count": 999}],
        "validation": {"test_event_count": 999},
    }
    found = set(_scan_test_int_paths(injected)) - _registry_paths()
    assert found == {"summary_table[*].verification_test_event_count", "validation.test_event_count"}, found


# ── ① canonical 恰一個，且所有同語意鍵**逐值等於**它 ────────────────────────
@pytest.mark.parametrize("fixture_name", ["event_report", "degraded_report"])
def test_splitunify_disclosure_exactly_one_test_count_key(fixture_name, request):
    """canonical 是唯一的答案；其餘同語意鍵出現時**必須是同一個數字**。

    🔴 本條之判準在 B4 review R1 後**改強**：原版只檢查「其他鍵沒出現」，
    但實測顯示同一個數字在報告裡本來就出現在 7 處（`marginal_ic.n_test`、
    `event_filter.split_mask.test_rows`、`filter_log...` 等），逐一刪除會波及本票以外的消費者。
    真正要禁的是**同一個問題兩個不同答案**（實測症狀 31 vs 33）⇒ 改為逐值對帳。
    `GROK-R1-P1-01` 另證明 `oos_downgrade.test_rows` 在事件路徑其實是**事件數**，
    原本被我誤登記成列語意——已改列入本對帳集合。
    """
    report = request.getfixturevalue(fixture_name)
    canonical = _dig(report, KEYS["canonical"])
    assert canonical is not _MISSING and isinstance(canonical, int)
    mismatched = {
        p: v for p in KEYS["must_equal_canonical_on_event_path"]
        if (v := _dig(report, p)) is not _MISSING and v != canonical
    }
    assert mismatched == {}, (
        f"同語意鍵與 canonical n_test={canonical} 不一致：{mismatched}"
        "——這正是本票要消滅的症狀（同一批事件兩個互相矛盾的數字）"
    )


def test_splitunify_disclosure_degraded_path_actually_writes_the_twins(degraded_report):
    """防空洞通過：降級路徑**確實**寫出了那三個孿生鍵（否則上面的對帳是在對空氣）。"""
    for path in ("metadata.ic_train_test_split.test_events",
                 "metadata.oos_downgrade.test_events",
                 "metadata.oos_downgrade.test_rows"):
        assert _dig(degraded_report, path) is not _MISSING, f"{path} 未出現在降級報告中"


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
    assert "metadata.ic_train_test_split.test_rows" in KEYS["row_semantics_not_event_count"]


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


# ── 🔴 B4 review R1 之型別／值域閘（三家各自實跑命中）────────────────────────
@pytest.mark.parametrize(
    "bad, expect",
    [
        (-1, "為負"),
        (2.5, "型別為 float"),
        (3.0, "型別為 float"),          # 即使是整數值的 float 也拒——能給 3.0 的也能給 3.7
        (True, "為 bool"),
    ],
    ids=["negative", "float_fraction", "float_whole", "bool"],
)
def test_splitunify_disclosure_rejects_bad_n_test(bad, expect):
    """實測（codex）：`n_test=-1 ACCEPTED -1`、`n_test=2.5 ACCEPTED 2`——截斷是靜默改答案。"""
    with pytest.raises(ValueError, match=expect):
        build_split_unify_disclosure(
            n_test=bad, test_timestamps_ms=[1_700_000_000_000], per_symbol_counts={"ETHUSDT": 1}
        )


def test_splitunify_disclosure_accepts_numpy_integer():
    """`np.integer` 是正規化不是猜測——orchestrator 送進來的就是它。"""
    out = build_split_unify_disclosure(
        n_test=np.int64(1), test_timestamps_ms=[1_700_000_000_000],
        per_symbol_counts={"ETHUSDT": np.int64(1)},
    )
    assert out["n_test"] == 1 and isinstance(out["n_test"], int)


def test_splitunify_disclosure_rejects_empty_counts_with_positive_n_test():
    """實測（codex）：`empty_counts_n_test=3 ACCEPTED 3`——有事件就必然屬於某個標的。"""
    with pytest.raises(ValueError, match="沒有 per_symbol_counts"):
        build_split_unify_disclosure(n_test=3, test_timestamps_ms=[1_700_000_000_000])


def test_splitunify_disclosure_boundary_hash_rejects_duplicates():
    """實測（codex）：重複時刻被接受 ⇒ 同一個集合因來源重複與否得到不同雜湊。"""
    with pytest.raises(ValueError, match="有重複"):
        boundary_hash([1_700_000_000_000, 1_700_000_000_000])


def test_splitunify_disclosure_boundary_hash_rejects_datetime_like():
    """🔴 實測（codex）：`same_instants_same_hash False`——DatetimeIndex 會以**奈秒**入雜湊。"""
    import pandas as pd

    idx = pd.to_datetime([1_700_000_000_000, 1_700_003_600_000], unit="ms")
    with pytest.raises(ValueError, match="datetime-like"):
        boundary_hash(idx)


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
