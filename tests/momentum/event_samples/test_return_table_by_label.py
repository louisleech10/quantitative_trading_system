"""GAP-3 UX **Task 7.5** 驗收（`-k return_table_by_label`；SPEC L3029–3046 之①~⑩）。

事件後報酬表由單一組改為**三組**（正例／反例／全體），掛在 `strata.by_label`。

🔴 **不新增第九頂層鍵**——①以八鍵集合相等釘住。
🔴 `control_kind` **只影響 `all`**——⑩以 `positive`／`negative` 在三種 `control_kind` 下
   **byte 級相同**釘住；本檔另加一條同族：`by_label` **以外**的整份輸出亦不受 `control_kind` 影響
   （對應 SPEC 覆蓋風險 (b)「manifest 加欄不應改變輸出 bytes」）。
🔴 兩個 reason 之字面**一律自契約取**（⑨），本檔不硬寫第二份。
"""

from __future__ import annotations

import json

import pytest

from momentum.Analysis.event_samples.canonical_serialize import canonical_event_table_sha256
from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.import_contract import validate_event_import
from momentum.Analysis.event_samples.tables import event_forward_return_table
from momentum.Analysis.event_samples.types import AlignmentConfig, DedupePolicyConfig, EventSplitConfig
from momentum.Analysis.ic_config_schema import load_report_contract
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000

#: §G S-1 之八個頂層鍵（①之集合相等對象）
TOP_LEVEL_KEYS = {
    "statistic_kind", "horizons", "primary_macro", "sensitivity_micro",
    "uniqueness_weighted", "strata", "common", "receipts",
}


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def build(bars, idxs, labels, kinds):
    """`kinds` 可為單一字串（全批同值）或逐列清單（混批）。"""
    ks = [kinds] * len(idxs) if isinstance(kinds, str) else list(kinds)
    events = [
        make_event(i, t0=BASE + n * H12, label=labels[i], control_kind=ks[i])
        for i, n in enumerate(idxs)
    ]
    df = validate_event_import(events)
    rec, fail = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
    assert fail.empty
    man = build_event_manifest(rec, DedupePolicyConfig(scenario="C"), events=df)
    plan = split_events(man, EventSplitConfig(test_fraction=0.4, tier_min_test_events=0))
    return man, rec, plan


CFG = {"horizons": [1, 2], "seed": 11, "n_boot": 50}
IDXS = [300, 600, 900, 1200]
LABELS = [1, 0, 1, 0]


def table(bars, kinds="user_labeled_same_trigger"):
    man, rec, plan = build(bars, IDXS, LABELS, kinds)
    return event_forward_return_table(man, rec, bars, plan, CFG), man


def test_return_table_by_label_01_top_level_still_eight_keys(bars):
    """① 三組**沒有**新增第九頂層鍵。"""
    out, _ = table(bars)
    assert set(out.keys()) == TOP_LEVEL_KEYS


def test_return_table_by_label_02_group_keys_exact(bars):
    """② `strata.by_label` 之鍵集恰為三組（不多不少）。"""
    out, _ = table(bars)
    assert set(out["strata"]["by_label"]) == {"positive", "negative", "all"}


def test_return_table_by_label_03_row_counts_equal_horizons(bars):
    """③ `positive`／`negative` 之列數各 `== len(horizons)`。"""
    out, _ = table(bars)
    for group in ("positive", "negative"):
        assert set(out["strata"]["by_label"][group]) == {str(h) for h in CFG["horizons"]}


def test_return_table_by_label_04_same_trigger_all_computable_and_n_adds_up(bars):
    """④ `user_labeled_same_trigger` ⇒ `all` 可算，且 `positive` n ＋ `negative` n `==` `all` n。"""
    out, _ = table(bars, "user_labeled_same_trigger")
    g = out["strata"]["by_label"]
    assert "status" not in g["all"], "同觸發之全體組須正常計算，不得為 not_computed"
    for h in CFG["horizons"]:
        assert g["positive"][str(h)]["n"] + g["negative"][str(h)]["n"] == g["all"][str(h)]["n"]


def test_return_table_by_label_05_platform_same_trigger_rule_is_computable(bars):
    """⑤ `platform_same_trigger_rule` ⇒ `all` **可算**（本批補齊之第三值）。"""
    out, _ = table(bars, "platform_same_trigger_rule")
    assert "status" not in out["strata"]["by_label"]["all"]


def test_return_table_by_label_06_user_labeled_other_not_computed(bars):
    """⑥ `user_labeled_other` ⇒ `all` 為狀態塊（**恰兩鍵**），reason 取自契約。"""
    out, _ = table(bars, "user_labeled_other")
    node = load_report_contract()["report_sections"]["event_return_table"]
    assert out["strata"]["by_label"]["all"] == {
        "status": "not_computed", "reason": node["not_computed_reasons"][0],
    }
    assert set(out["strata"]["by_label"]["all"]) == set(node["group_status_object_keys"])


def test_return_table_by_label_07_mixed_control_kind_not_majority(bars):
    """⑦ 同批混入兩種 `control_kind` ⇒ reason `== mixed_control_kind_in_batch`，**不取多數決**。"""
    kinds = ["user_labeled_other", "user_labeled_other", "user_labeled_other", "user_labeled_same_trigger"]
    out, _ = table(bars, kinds)
    node = load_report_contract()["report_sections"]["event_return_table"]
    # 多數是 user_labeled_other ⇒ 取多數決會得到 control_kind_not_comparable；正解是 mixed
    assert out["strata"]["by_label"]["all"]["reason"] == node["not_computed_reasons"][1]
    assert out["strata"]["by_label"]["all"]["reason"] == "mixed_control_kind_in_batch"


def test_return_table_by_label_08_control_kind_in_manifest_columns(bars):
    """⑧ `control_kind` 確實出現在 `build_event_manifest` 產出之 `manifest.table.columns`。

    這條擋的是「讀不到就當 `None` 放行」——manifest 沒帶欄時，表格層必須 raise 而不是靜默。
    """
    _, man = table(bars)
    assert "control_kind" in man.table.columns


def test_return_table_by_label_09_contract_registers_reasons(bars):
    """⑨ 兩個 reason 與狀態鍵集**逐字**登記於 `ic_report_contract.json`。"""
    node = load_report_contract()["report_sections"]["event_return_table"]
    assert node["not_computed_reasons"] == ["control_kind_not_comparable", "mixed_control_kind_in_batch"]
    assert node["group_status_object_keys"] == ["status", "reason"]
    assert node["group_keys"] == ["positive", "negative", "all"]


def test_return_table_by_label_10_pos_neg_byte_identical_across_control_kinds(bars):
    """⑩ `positive`／`negative` 在三種 `control_kind` 下 **byte 級相同**（證明只影響 `all`）。"""
    seen = []
    for kind in ("user_labeled_same_trigger", "platform_same_trigger_rule", "user_labeled_other"):
        out, _ = table(bars, kind)
        seen.append(json.dumps(
            {k: out["strata"]["by_label"][k] for k in ("positive", "negative")},
            sort_keys=True, ensure_ascii=False,
        ))
    assert len(set(seen)) == 1, "control_kind 影響到了 positive／negative——它只該影響 all"


def test_return_table_by_label_11_manifest_column_does_not_leak_into_output(bars):
    """🔴 覆蓋風險 (b)：`dedupe.py` 加 `control_kind` 欄**不應**改變輸出 bytes。

    判準：把 `by_label` 拿掉之後的整份輸出，在三種 `control_kind` 下 **S-9 sha256 相同**
    ——若 manifest 的新欄意外進了輸出（或改變了任何統計），本條會紅。
    """
    shas = set()
    for kind in ("user_labeled_same_trigger", "platform_same_trigger_rule", "user_labeled_other"):
        out, _ = table(bars, kind)
        rest = {k: v for k, v in out.items() if k != "strata"}
        rest["strata"] = {k: v for k, v in out["strata"].items() if k != "by_label"}
        shas.add(canonical_event_table_sha256(rest))
    assert len(shas) == 1, "control_kind 改變了 by_label 以外的輸出 ⇒ manifest 的欄漏進了輸出"


def _hand_group_stats(bars, idxs, horizon, sign=1.0):
    """🔴 **§G S-8 獨立 oracle**：直接讀 bars 手算，**不呼叫任何被測函式**。

    entry＝t0 根之 `open`（`entry_price_semantic='trigger_open'` 之 D1-6 映射）、
    exit＝entry 根之後第 h 根 `close`；`ret_label_anchor` 之錨改為 t0 根之 `close`。
    尾端不足（`n + h >= len(bars)`）⇒ **該筆排除**（不灌 0），回傳之 `n` 反映排除。
    """
    b = bars["ETHUSDT"]["12h"]
    entry_rets, anchor_rets = [], []
    for n in idxs:
        if n + horizon >= len(b):
            continue                      # 尾端資料不足 ⇒ omission
        entry = float(b["open"].iloc[n])
        t0_close = float(b["close"].iloc[n])
        exit_close = float(b["close"].iloc[n + horizon])
        entry_rets.append(sign * (exit_close - entry) / entry)
        anchor_rets.append(sign * (exit_close - t0_close) / t0_close)
    n = len(entry_rets)
    return {
        "n": n,
        "mean": sum(entry_rets) / n if n else float("nan"),
        "label_anchor_mean": sum(anchor_rets) / n if n else float("nan"),
    }


def test_return_table_by_label_12_independent_hand_oracle(bars):
    """🔴 **§G S-8 oracle 獨立性**：三組之 expected 由獨立手算產生，禁以被測函式自產。

    涵蓋 S-8 明列之三項：`horizons=[1,3,7]`、`ret_entry` 與 `ret_label_anchor` 兩種 return、
    **尾端資料不足之 omission**（最後一筆事件在 h=7 時算不出來 ⇒ 該格 n 少一）。
    """
    tail = 1692                       # ETHUSDT/12h 共 1696 根 ⇒ h=7 時 1692+7 超界
    idxs, labels = [300, 600, 900, tail], [1, 0, 1, 0]
    man, rec, plan = build(bars, idxs, labels, "user_labeled_same_trigger")
    # 前置條件：本 fixture 之事件彼此不重疊 ⇒ 權重全為 1、全入 primary
    #          ⇒ 加權平均等於簡單平均，手算才成立（不成立時本條會先紅，而不是靜默算錯）
    assert set(man.table["uniqueness_weight"].tolist()) == {1.0}
    assert bool(man.table["in_primary"].all())

    out = event_forward_return_table(
        man, rec, bars, plan, {"horizons": [1, 3, 7], "seed": 11, "n_boot": 50},
    )
    g = out["strata"]["by_label"]
    pos_idxs = [300, 900]             # label == 1
    neg_idxs = [600, tail]            # label == 0
    for h in (1, 3, 7):
        for name, group_idxs in (("positive", pos_idxs), ("negative", neg_idxs), ("all", idxs)):
            want = _hand_group_stats(bars, group_idxs, h)
            got = g[name][str(h)]
            assert got["n"] == want["n"], f"{name} h={h} 之 n"
            assert got["mean"] == pytest.approx(want["mean"], abs=1e-12), f"{name} h={h} 之 mean"
            assert got["label_anchor_mean"] == pytest.approx(want["label_anchor_mean"], abs=1e-12), \
                f"{name} h={h} 之 label_anchor_mean"
    # omission 真的發生了（否則上面的相等是「兩邊都沒排除」之空洞通過）
    assert g["negative"]["7"]["n"] == 1 and g["negative"]["1"]["n"] == 2
    assert g["all"]["7"]["n"] == 3 and g["all"]["1"]["n"] == 4


def test_return_table_by_label_13_g2_golden_byte_frozen(bars):
    """🔴 **G-2 事件路徑專屬 golden**（SPEC L916–921；本 Task 之 D-4 合法輸出變更後之凍結值）。

    固定 fixture（真實 kline 切片）＋固定 horizons ⇒ `event_forward_return_table` 之輸出
    以 **§G S-9 之參考實作**算 sha256。
    🔴 **本值不是「跑一次抄下來」**：同一份實作之數值已由上一條 `_12_independent_hand_oracle`
       以獨立手算逐格驗過（S-8 明禁「以被測函式自產 golden 後回頭比自己」），
       本條只再加一層**位元組級**回歸——改了任何數值／鍵／順序都會轉紅。
    合法變更須**在 commit message 說明並同批更新本值**，不得靜默重凍。
    """
    out, _ = table(bars, "user_labeled_same_trigger")
    assert canonical_event_table_sha256(out) == G2_GOLDEN_SHA256


#: 由本檔之固定 fixture（`IDXS`／`LABELS`／`CFG`）產生；數值面由 `_12_independent_hand_oracle` 獨立驗證。
#: 更新時須在 commit message 說明改了什麼、為什麼（§G G-2）。
G2_GOLDEN_SHA256 = "2652b94a082e56dd15a9f4939e907a0b4993573c692357b3d379f4d41c14b00b"
