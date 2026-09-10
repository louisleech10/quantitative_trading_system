"""EVTLABEL Task 3.7：區塊置換自檢與整批負對照。

SPEC：`docs/EVTLABEL_SPEC.md` Task 3.7　TODO：Task 3.7

## 這批測試在防什麼

事件之間**不是獨立的**——相隔很近的事件，label 視窗會重疊，等於在看同一段未來。
把標籤逐筆洗開會破壞這個相依結構，讓「隨機也能篩出東西」的機率被**低估**，
於是置換檢定過度樂觀、篩出一堆其實是雜訊的特徵。這種錯不會拋例外，
它只會讓你拿一份看起來很漂亮的倖存者名單去餵 ML。

故本檔釘住三件事：①區塊怎麼綁（密集段不得被 median 稀釋）②置換真的有發生
③隨機也能篩出同樣多時，倖存者必須被標成不可消費。

mutation（`--phase 3b`）：`M-P3-4`（置換恆等）、`M-P3-6`（負對照改 warning-only）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis import binary_discrimination as bd
from momentum.Analysis.binary_discrimination import (
    BINARY_STATUS_OK,
    block_ids_for_events,
    block_permutation_oracle,
    rank_biserial_stat,
)
from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.core.contracts import ValidatedBinaryLabel, binary_label_digest

HOUR = 3_600_000
BASE = 1_700_000_000_000


# ══════════════════════════════════════════════════════════════════════════
# ① 區塊怎麼綁
# ══════════════════════════════════════════════════════════════════════════


def test_block_len_covers_the_answer_window():
    """視窗 W 根、事件每根一個 ⇒ 每 W 個事件綁一塊。"""
    ms = np.array([BASE + i * HOUR for i in range(60)])
    _, block_len, n_blocks = block_ids_for_events(ms, 12, HOUR)
    assert block_len == 12 and n_blocks == 5


def test_dense_cluster_block_len():
    """🔴 承重條：前段密集、後段稀疏 ⇒ 區塊長度必須被**密集段**決定，不能被 median 稀釋。

    只看 median（這裡是 20 根）會算出 L=1，等於對密集段完全沒有保護。
    """
    dense = [BASE + i * HOUR for i in range(10)]                     # gap = 1
    sparse = [dense[-1] + (i + 1) * 20 * HOUR for i in range(20)]    # gap = 20
    _, block_len, _ = block_ids_for_events(np.array(dense + sparse), 12, HOUR)
    assert block_len >= 12, f"密集段被稀釋，L={block_len}"


def test_single_event_block_len_is_one():
    _, block_len, n_blocks = block_ids_for_events(np.array([BASE]), 12, HOUR)
    assert block_len == 1 and n_blocks == 1


def test_zero_window_means_no_grouping():
    """答案窗 0 根（當根事件）⇒ 事件之間沒有視窗重疊 ⇒ 不必綁。"""
    ms = np.array([BASE + i * HOUR for i in range(30)])
    _, block_len, n_blocks = block_ids_for_events(ms, 0, HOUR)
    assert block_len == 1 and n_blocks == 30


# ══════════════════════════════════════════════════════════════════════════
# ② 置換本身
# ══════════════════════════════════════════════════════════════════════════


def _sparse_setup(n: int = 120, block_w: int = 2):
    ms = np.array([BASE + i * HOUR for i in range(n)])
    block_ids, block_len, n_blocks = block_ids_for_events(ms, block_w, HOUR)
    y = np.array(([1] * 10 + [0] * 10) * (n // 20), dtype=int)
    return ms, block_ids, block_len, n_blocks, y


def test_permutation_keeps_block_members_adjacent():
    """區塊內的成員在置換後仍相鄰——這正是「相依結構被保留」的可觀察形式。"""
    _, block_ids, block_len, _, y = _sparse_setup(60, 3)
    assert block_len == 3
    tagged = np.arange(60)
    out = bd._permute_blocks(np.random.default_rng(5), tagged, block_ids)
    for start in range(0, 60, 3):
        chunk = out[start: start + 3]
        assert np.all(np.diff(chunk) == 1), f"區塊被拆散：{chunk}"


def test_permutation_preserves_class_counts():
    """洗的是位置不是內容 ⇒ 正反數量必須完全不變。"""
    _, block_ids, _, _, y = _sparse_setup()
    out = bd._permute_blocks(np.random.default_rng(1), y, block_ids)
    assert out.sum() == y.sum() and len(out) == len(y)


def test_planted_feature_is_outside_the_band():
    """完全可分之特徵 ⇒ 觀測值落在置換帶**外**（不是隨機能做到的）。"""
    _, block_ids, _, _, y = _sparse_setup()
    values = y * 10.0 + np.arange(len(y)) * 1e-6
    out = block_permutation_oracle(values, y, block_ids, rank_biserial_stat, seed=1, n_perm=200)
    assert out["status"] == BINARY_STATUS_OK
    assert out["in_band"] is False and out["p_value"] < 0.05


def test_pure_noise_sits_inside_the_band():
    """純雜訊 ⇒ 落在帶內 ⇒ 會被移出倖存者（這就是本檢定的用途）。"""
    _, block_ids, _, _, y = _sparse_setup()
    values = np.random.default_rng(0).standard_normal(len(y))
    out = block_permutation_oracle(values, y, block_ids, rank_biserial_stat, seed=1, n_perm=200)
    assert out["in_band"] is True


def test_identity_permutation_raises(monkeypatch):
    """🔴 `M-P3-4`：把置換換成恆等 ⇒ 硬檢 (ii) 必須 raise。

    封死「觀測值∈觀測值」那種假綠——恆等置換會讓每一次都算出同一個數字。
    """
    _, block_ids, _, _, y = _sparse_setup()
    values = y * 10.0 + np.arange(len(y)) * 1e-6
    monkeypatch.setattr(bd, "_permute_blocks", lambda rng, yy, ids: yy.copy())
    with pytest.raises(ValueError, match="硬檢"):
        block_permutation_oracle(values, y, block_ids, rank_biserial_stat, seed=1, n_perm=50)


def test_insufficient_blocks_is_unavailable_not_a_fake_p():
    """🔴 邊界③：答案窗很長 ⇒ 區塊太少 ⇒ 誠實回「做不了」，**不給**一個沒意義的 p。"""
    ms = np.array([BASE + i * HOUR for i in range(40)])
    block_ids, block_len, n_blocks = block_ids_for_events(ms, 156, HOUR)
    assert n_blocks < 10
    y = np.array([1] * 20 + [0] * 20)
    out = block_permutation_oracle(y * 1.0, y, block_ids, rank_biserial_stat, seed=1, n_perm=50)
    assert out["status"] == "unavailable:insufficient_blocks"
    assert "p_value" not in out and "in_band" not in out


# ══════════════════════════════════════════════════════════════════════════
# ③ 整批負對照
# ══════════════════════════════════════════════════════════════════════════


def _orch(n_control: int = 8, rb_min: float = 0.10) -> ICFilterOrchestrator:
    return ICFilterOrchestrator(ICConfig.model_validate({
        "event_filter": {"min_events_per_class": 5, "negative_control_n": n_control, "oracle_seed": 7},
        "thresholds": {"rank_biserial_min": rb_min},
    }))


def _bind(orch, feats, y, window_bars: int = 2):
    ms = (feats.index.asi8 // 10**6).astype("int64")
    rows = frozenset((f"e{i}", int(t), int(v)) for i, (t, v) in enumerate(zip(ms, y)))
    series = pd.Series(y.astype(float), index=feats.index)
    orch._ic_cache = {"event_binary_label": ValidatedBinaryLabel(
        series=series, digest=binary_label_digest(rows), rows_frozenset=rows,
        n_pos=int((y == 1).sum()), n_neg=int((y == 0).sum()),
    )}
    orch._binary_label_window_bars = window_bars


def _frame(n: int, cols: dict) -> pd.DataFrame:
    idx = pd.to_datetime([BASE + i * HOUR for i in range(n)], unit="ms")
    return pd.DataFrame(cols, index=idx)


def test_planted_survivor_passes_and_is_not_suppressed():
    """植入一個真訊號 ⇒ 通過置換自檢，且實測倖存數應高於隨機（不 suppressed）。"""
    n = 120
    y = np.array(([1] * 10 + [0] * 10) * 6, dtype=int)
    rng = np.random.default_rng(11)
    cols = {"planted": y * 10.0 + rng.standard_normal(n) * 0.01}
    cols.update({f"n{i}": rng.standard_normal(n) for i in range(20)})
    feats = _frame(n, cols)
    orch = _orch()
    _bind(orch, feats, y)
    removed: dict = {}
    survivors, receipt = orch._run_binary_permutation_and_negative_control(
        ["planted"], removed, feats, orch._config, alpha_effective=0.05, fdr_method="fdr_bh",
    )
    assert survivors == ["planted"]
    assert orch._survivor_suppressed_reason is None
    nc = receipt["negative_control"]
    assert nc["n_observed"] == 1 and nc["n_observed"] > nc["q95"]
    assert receipt["block_len"] >= 1 and receipt["first_permutation_digest"]


def test_noise_only_survivor_is_removed_by_the_oracle():
    """雜訊特徵即使過了門檻，也會被置換自檢移出（特徵級 fail-closed）。"""
    n = 120
    y = np.array(([1] * 10 + [0] * 10) * 6, dtype=int)
    feats = _frame(n, {"noise": np.random.default_rng(0).standard_normal(n)})
    orch = _orch()
    _bind(orch, feats, y)
    removed: dict = {}
    survivors, _ = orch._run_binary_permutation_and_negative_control(
        ["noise"], removed, feats, orch._config, alpha_effective=0.05, fdr_method="fdr_bh",
    )
    assert survivors == []
    assert removed["permutation_oracle_disagree"] == ["noise"]


def test_no_survivors_skips_negative_control_without_red_banner():
    """🔴 邊界①：0 倖存者 ⇒ **不跑**負對照、不設 suppressed。

    「沒有倖存者」與「跑了負對照而且失敗」是兩件事，不得共用同一個紅燈。
    """
    n = 120
    y = np.array(([1] * 10 + [0] * 10) * 6, dtype=int)
    feats = _frame(n, {"noise": np.random.default_rng(0).standard_normal(n)})
    orch = _orch()
    _bind(orch, feats, y)
    survivors, receipt = orch._run_binary_permutation_and_negative_control(
        [], {}, feats, orch._config, alpha_effective=0.05, fdr_method="fdr_bh",
    )
    assert survivors == []
    assert receipt["negative_control"] == {"status": "skipped:no_survivors"}
    assert orch._survivor_suppressed_reason is None


def test_negative_control_q95_is_an_integer_order_statistic():
    """🔴 計數是離散的：q95 必須是實際出現過的整數，不得插值出 12.4 這種值。"""
    n = 120
    y = np.array(([1] * 10 + [0] * 10) * 6, dtype=int)
    rng = np.random.default_rng(2)
    cols = {"planted": y * 10.0 + rng.standard_normal(n) * 0.01}
    cols.update({f"n{i}": rng.standard_normal(n) for i in range(10)})
    feats = _frame(n, cols)
    orch = _orch()
    _bind(orch, feats, y)
    _, receipt = orch._run_binary_permutation_and_negative_control(
        ["planted"], {}, feats, orch._config, alpha_effective=0.05, fdr_method="fdr_bh",
    )
    nc = receipt["negative_control"]
    assert isinstance(nc["q95"], int)
    assert nc["q95"] in set(nc["shuffled_counts"])
    assert len(nc["shuffled_counts"]) == 8 and nc["seed_base"] == 7


def test_budget_floor_hit_is_disclosed():
    """置換次數被預算壓到地板 ⇒ 必須揭露（否則使用者不知道解析度被砍了）。"""
    n = 120
    y = np.array(([1] * 10 + [0] * 10) * 6, dtype=int)
    feats = _frame(n, {f"f{i}": np.random.default_rng(i).standard_normal(n) for i in range(3)})
    orch = ICFilterOrchestrator(ICConfig.model_validate({
        "event_filter": {"min_events_per_class": 5, "negative_control_n": 2,
                         "perm_budget_total": 100, "oracle_seed": 7},
    }))
    _bind(orch, feats, y)
    _, receipt = orch._run_binary_permutation_and_negative_control(
        ["f0", "f1"], {}, feats, orch._config, alpha_effective=0.05, fdr_method="fdr_bh",
    )
    assert receipt["budget_floor_hit"] is True
    assert receipt["n_perm"] == 200, "地板是 200，不得低於它"


def test_suppressed_not_consumable_when_random_matches_observed():
    """🔴 `M-P3-6`：隨機也能篩出跟實測一樣多 ⇒ 倖存者必須標 `negative_control_failed`。

    構造方式是把門檻放到最寬（效應量 0、alpha 1.0），此時每一次置亂都會「篩出」一堆特徵，
    q95 遠高於實測的 1 個 ⇒ 整批結果與雜訊無法區分。
    改成 warning-only（不設 suppressed）⇒ 本條紅。
    """
    n = 120
    y = np.array(([1] * 10 + [0] * 10) * 6, dtype=int)
    rng = np.random.default_rng(4)
    cols = {"planted": y * 10.0 + rng.standard_normal(n) * 0.01}
    cols.update({f"n{i}": rng.standard_normal(n) for i in range(15)})
    feats = _frame(n, cols)
    orch = _orch(n_control=6, rb_min=0.0)
    _bind(orch, feats, y)
    _, receipt = orch._run_binary_permutation_and_negative_control(
        ["planted"], {}, feats, orch._config, alpha_effective=1.0, fdr_method="fdr_bh",
    )
    nc = receipt["negative_control"]
    assert nc["n_observed"] <= nc["q95"], f"fixture 未觸發：observed={nc['n_observed']} q95={nc['q95']}"
    assert orch._survivor_suppressed_reason == "negative_control_failed"
