"""GAP-3 UX Task 5.0 — 指標詞彙 SoT 與其 loader。

邊界①：頂層鍵集 `>=` SPEC L2059 之八鍵（**成員資格非等值**——Task 7.5 還會加鍵）。
邊界②：任一指標鍵缺 `definition` ⇒ loader fail-closed（raise），不回半套詞彙表。

🔴 本檔**不複列** definition 字面：那會變成第二份副本，正是 Task 5.0「不可做」所禁的東西。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from momentum.Analysis.event_samples import metrics_glossary as mg

REPO = Path(__file__).resolve().parents[3]
GLOSSARY_PATH = REPO / "momentum" / "Analysis" / "contracts" / "event_metrics_glossary.json"

#: SPEC L2059 之八鍵（驗收字面之唯一來源＝SPEC 該 Task 之「驗證」欄）
SPEC_REQUIRED_KEYS = {
    "macro_mean", "micro_mean", "n_eff", "lift_threshold",
    "prevalence_full", "prevalence_learn", "signal_frequency", "tail_excluded",
}


@pytest.fixture()
def restore_glossary_cache():
    """loader 有 module 級快取；動 `_GLOSSARY_PATH` 的測試跑完須還原，否則污染後續測試。"""
    saved_cache, saved_path = mg._GLOSSARY_CACHE, mg._GLOSSARY_PATH
    yield
    mg._GLOSSARY_CACHE, mg._GLOSSARY_PATH = saved_cache, saved_path


def test_gap3_metrics_glossary_covers_spec_keys():
    """邊界①：**SPEC 驗收那一行的字面形式**——直接對 JSON 頂層鍵取 `set(g) >=`。"""
    g = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8"))
    assert set(g) >= SPEC_REQUIRED_KEYS, f"glossary 缺鍵：{sorted(SPEC_REQUIRED_KEYS - set(g))}"


def test_gap3_metrics_glossary_loader_covers_spec_keys():
    """邊界①（loader 側）：後設欄被排除之後，八鍵仍在。"""
    terms = mg.load_metrics_glossary()
    assert set(terms) >= SPEC_REQUIRED_KEYS, f"loader 回傳缺鍵：{sorted(SPEC_REQUIRED_KEYS - set(terms))}"
    assert not [k for k in terms if k.startswith("_")], "後設欄不得混進指標鍵"


def test_gap3_metrics_glossary_entries_are_text_only():
    """邊界（只放文案與公式指標，不放數值）：每個指標鍵只有三個**非空字串**欄。"""
    terms = mg.load_metrics_glossary()
    for key, entry in sorted(terms.items()):
        assert set(entry) == set(mg.REQUIRED_TERM_FIELDS), f"{key} 之欄位集不符：{sorted(entry)}"
        for field, value in sorted(entry.items()):
            assert isinstance(value, str) and value.strip(), f"{key}.{field} 須為非空字串（不放數值）"


def test_gap3_metrics_glossary_loader_fail_closed_on_missing_definition(tmp_path, restore_glossary_cache):
    """邊界②：缺 `definition` ⇒ raise。

    正向對照同時做：把 `definition` 補回去之後同一份檔要能讀出來——否則「恆 raise」也會讓本條綠。
    """
    broken = {"_doc": "test", "macro_mean": {"term": "t", "formula_ref": "r"}}
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
    mg._GLOSSARY_PATH, mg._GLOSSARY_CACHE = path, None
    with pytest.raises(ValueError, match="definition"):
        mg.load_metrics_glossary()

    fixed = {"_doc": "test", "macro_mean": {"term": "t", "definition": "d", "formula_ref": "r"}}
    path.write_text(json.dumps(fixed, ensure_ascii=False), encoding="utf-8")
    mg._GLOSSARY_CACHE = None
    assert set(mg.load_metrics_glossary()) == {"macro_mean"}


# ---------------------------------------------------------------------------
# R1 群集 A（`GROK-R1-P1-01`／`CODEX-R1-P1-02`／`CODEX-R1-P2-03`）之閉合閘
#
# 病根：首版 definition 是**讀算式推論**寫出來的，沒有實跑驗證，於是三條都描述了
# 「算式其實沒做的事」。光改文字不算閉合——算式日後再變，文字又會悄悄變成錯的。
# 以下把 definition 所宣稱的事實**釘在真實算式上**：算式一改，這裡先紅。
# ---------------------------------------------------------------------------
def test_gap3_metrics_glossary_n_eff_claim_binds_to_equal_weight_micro():
    """`n_eff` 之 definition 宣稱「本表 micro 區等權 ⇒ 恆等於 n」——用真實 kline 釘住。

    反例（`GROK-R1-P1-01`）：首版寫的是 uniqueness 降權語意，而 UI 綁的是等權欄
    ⇒ 使用者被教去讀一個在本欄永遠不會出現的訊號。
    """
    from tests.momentum.event_samples.helpers import load_bars
    from tests.momentum.event_samples.test_gap3_horizon_curve import _pipeline, _table

    bars = load_bars("ETHUSDT", ("12h",))
    # 🔴 fixture 之事件**刻意相鄰**（300／301／302）以製造時間重疊。
    #    用不重疊的事件（如 300／600／900）時 uniqueness 權重全為 1 ⇒ 加權與等權結果相同，
    #    本條對「把 micro 改成加權」這個變異**完全失明**（mutation 5.0-M3 實跑錄到空紅集合才發現）。
    rec, man, plan = _pipeline(bars, [300, 301, 302], [1, 0, 1])
    rep = _table(bars, man, rec, plan, [1, 2, 4])

    for h in ("1", "2", "4"):
        micro, uniq = rep["sensitivity_micro"][h], rep["uniqueness_weighted"][h]
        assert micro["n"] > 0                                   # 前置：真的有事件，否則下面退化成 0==0
        assert float(micro["n_effective"]) == float(micro["n"]), (
            f"micro 之 n_effective 不再等於 n（h={h}）——glossary 之 n_eff 定義已失效，請一併更新")
        # 對照組：definition 宣稱「降權後的值另存於 uniqueness_weighted」——那個欄**真的降了權**，
        # 否則「本欄是等權」這句話沒有鑑別力（兩欄一樣時，改成加權也不會被察覺）。
        assert float(uniq["n_effective"]) < float(uniq["n"]), (
            f"uniqueness_weighted 沒有降權（h={h}）⇒ 本 fixture 無重疊事件，本條失去鑑別力")


def test_gap3_metrics_glossary_prevalence_full_denominator_is_labeled_not_total():
    """`prevalence_full` 之 definition 宣稱「分母是 n_labeled、不是 n_total」——用真實 kline 釘住。

    反例（`CODEX-R1-P1-02`）：首版寫「全 K 線這個固定分母」，實際 `yv.mean()` 只取已標記列。
    """
    import numpy as np
    import pandas as pd

    from momentum.Analysis.event_samples.all_bars_eval import evaluate_all_bars
    from tests.momentum.event_samples.helpers import load_bars

    seg = {"ETHUSDT": load_bars("ETHUSDT", ("12h",))["ETHUSDT"]["12h"].iloc[1000:1100].reset_index(drop=True)}
    ot = seg["ETHUSDT"]["open_time_ms"].to_numpy()
    scores = pd.Series(np.random.default_rng(3).uniform(0, 1, len(ot)),
                       index=pd.MultiIndex.from_product([["ETHUSDT"], ot]))
    rep = evaluate_all_bars(scores, seg, {
        "horizon_bars": 2, "label_threshold": 0.01, "direction": "long", "decision_offset_bars": 0,
        "score_threshold": 0.5, "top_q": 0.1, "prevalence_learn": 0.5, "sample_design": "case_control",
        "seed": 1, "n_boot": 20, "entry_price_semantic": "trigger_open", "timeframe": "12h"})

    counts, prev = rep["counts"], float(rep["overall"]["prevalence_full"])
    # 前置：這兩個分母**確實不同**，否則本條分不出實作用了哪一個
    assert counts["n_labeled"] != counts["n_total"], "本 fixture 之兩個分母相同 ⇒ 本條無鑑別力，請換區段"
    n_pos = prev * counts["n_labeled"]
    assert abs(n_pos - round(n_pos)) < 1e-9, "prevalence_full × n_labeled 不是整數 ⇒ 分母不是 n_labeled"
    assert prev != pytest.approx(round(n_pos) / counts["n_total"], abs=1e-12), "分母疑似變成 n_total"


def test_gap3_metrics_glossary_eligibility_terms_match_manifest():
    """`n_eligible` 之 definition 須逐條含 manifest `eligibility` 字串裡的**每一個**條件名。

    反例（`CODEX-R1-P2-03`）：首版寫「通過 PIT 檢查」，漏了 warmup 與 grid 連續性。
    🔴 條件名取自 manifest 字串**當場切出來**，不是在這裡另列一份清單（黑名單列不完）。
    """
    import numpy as np
    import pandas as pd

    from momentum.Analysis.event_samples.all_bars_eval import evaluate_all_bars
    from tests.momentum.event_samples.helpers import load_bars

    seg = {"ETHUSDT": load_bars("ETHUSDT", ("12h",))["ETHUSDT"]["12h"].iloc[1000:1100].reset_index(drop=True)}
    ot = seg["ETHUSDT"]["open_time_ms"].to_numpy()
    scores = pd.Series(np.random.default_rng(3).uniform(0, 1, len(ot)),
                       index=pd.MultiIndex.from_product([["ETHUSDT"], ot]))
    rep = evaluate_all_bars(scores, seg, {
        "horizon_bars": 2, "label_threshold": 0.01, "direction": "long", "decision_offset_bars": 0,
        "score_threshold": 0.5, "top_q": 0.1, "prevalence_learn": 0.5, "sample_design": "case_control",
        "seed": 1, "n_boot": 20, "entry_price_semantic": "trigger_open", "timeframe": "12h"})

    eligibility = str(rep["manifest"]["eligibility"])
    terms = [t.strip() for t in eligibility.split("∧") if t.strip()]
    assert len(terms) >= 2, f"manifest eligibility 解析不出條件名：{eligibility!r}"
    definition = mg.load_metrics_glossary()["n_eligible"]["definition"]
    missing = [t for t in terms if t not in definition]
    assert not missing, f"n_eligible 之 definition 少了 manifest 列的條件：{missing}"


def test_gap3_metrics_glossary_duplicate_bars_reject_batch_not_counted_in_unknown():
    """`n_unknown` 之 definition 宣稱「整批含重複 K 線 ⇒ 直接拒收整批，不會計進這裡」——釘住它。

    反例（`CODEX-R2-P2-01`）：首版寫「K 線缺根**或重複**」，但重複 `open_time_ms` 在任何計數之前
    就整批 `raise` ⇒ 那個原因永遠不可能出現在 `n_unknown` 裡，definition 描述了不存在的行為。
    """
    import numpy as np
    import pandas as pd

    from momentum.Analysis.event_samples.all_bars_eval import evaluate_all_bars
    from tests.momentum.event_samples.helpers import load_bars

    base = load_bars("ETHUSDT", ("12h",))["ETHUSDT"]["12h"].iloc[1000:1100].reset_index(drop=True)
    config = {"horizon_bars": 2, "label_threshold": 0.01, "direction": "long", "decision_offset_bars": 0,
              "score_threshold": 0.5, "top_q": 0.1, "prevalence_learn": 0.5, "sample_design": "case_control",
              "seed": 1, "n_boot": 20, "entry_price_semantic": "trigger_open", "timeframe": "12h"}

    def scores_for(frame):
        ot = frame["ETHUSDT"]["open_time_ms"].to_numpy()
        return pd.Series(np.random.default_rng(3).uniform(0, 1, len(ot)),
                         index=pd.MultiIndex.from_product([["ETHUSDT"], ot]))

    # 正向對照：沒有重複時算得出來（否則下面的 raises 也可能只是別的錯）
    clean = {"ETHUSDT": base}
    assert evaluate_all_bars(scores_for(clean), clean, config)["counts"]["n_total"] == len(base)

    # 把某一根複製一份 ⇒ 整批拒收，**不是**把它算進 n_unknown
    duped = {"ETHUSDT": pd.concat([base, base.iloc[[10]]], ignore_index=True)}
    with pytest.raises(ValueError, match="duplicate_bar"):
        evaluate_all_bars(scores_for(duped), duped, config)


def test_gap3_metrics_glossary_purge_removes_train_side_only():
    """`n_test` 之 definition 宣稱「purge／embargo 拿掉的是**訓練側**，不會讓測試段變小」——釘住它。

    🔴 本條是**主委自查**加的（非委員抓）：R2 之 `CODEX-R2-P2-01` 揭露 R1 的修補涵蓋面小於宣稱
    ——`n_unknown` 只改字沒綁。之後把 21 條 definition 對算式重掃一遍，發現 `n_test` 原句
    「已在切分、purge 與 embargo 之後」會讓人以為測試段也被 purge 篩過，屬同一種不精確。
    """
    from tests.momentum.event_samples.helpers import load_bars
    from tests.momentum.event_samples.test_gap3_horizon_curve import _pipeline

    bars = load_bars("ETHUSDT", ("12h",))
    _rec, _man, plan = _pipeline(bars, [300, 301, 302], [1, 0, 1])

    assignments = plan.assignments
    test_ids = set(assignments[assignments["split_label"] == "test"]["event_id"])
    purged_ids = set(plan.purged["event_id"])
    assert test_ids, "本 fixture 沒有測試段事件 ⇒ 下面的交集斷言退化成 0，本條失去鑑別力"
    assert test_ids & purged_ids == set(), "purge 動到了測試側 ⇒ n_test 之 definition 已失效"
    # 正向對照：purge 名單真的只可能落在 train 側（train ∪ test ∪ purged 覆蓋全部事件）
    train_ids = set(assignments[assignments["split_label"] == "train"]["event_id"])
    assert purged_ids <= (purged_ids | train_ids) and not (purged_ids & test_ids)


def test_gap3_metrics_glossary_horizon_counts_from_entry_bar():
    """`horizon` 之 definition 宣稱「從**進場那根**往後推 h 根」——用手算 oracle 釘住。

    反例（`CODEX-R3-P1-01`）：首版寫「自事件錨定的那根 K 線起算」，而
    `exit_idx = entry_idx + h`；`entry_idx` 由 `entry_price_semantic` 決定，未必等於 t0 那根。
    """
    import numpy as np

    from momentum.Analysis.event_samples.alignment import align_events
    from momentum.Analysis.event_samples.dedupe import build_event_manifest
    from momentum.Analysis.event_samples.event_split import split_events
    from momentum.Analysis.event_samples.import_contract import validate_event_import
    from momentum.Analysis.event_samples.tables import event_forward_return_table
    from momentum.Analysis.event_samples.types import AlignmentConfig, DedupePolicyConfig, EventSplitConfig
    from tests.momentum.event_samples.helpers import load_bars
    from tests.momentum.event_samples.test_import_contract import make_event

    bars = load_bars("ETHUSDT", ("12h",))
    frame = bars["ETHUSDT"]["12h"]
    ot = frame["open_time_ms"].to_numpy()

    # 🔴 fixture **刻意用 `next_open`**：預設的 `trigger_open` 會讓進場根 ＝ t0 根，
    #    「從進場根起算」與「從 t0 起算」算出同一個數 ⇒ 本條對該變異完全失明
    #    （mutation `5.0-M6` 首次錄到空紅集合才發現；同型第三次，見 §4.2 第 9 條）。
    # 契約要求批內兩類皆有（單一 label ⇒ missing_control_group），故兩個事件。
    events = [make_event(i, t0=int(ot[idx]), label=lab, entry_price_semantic="next_open")
              for i, (idx, lab) in enumerate(((300, 1), (320, 0)))]
    df = validate_event_import(events)
    rec, fail = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
    assert fail.empty
    man = build_event_manifest(rec, DedupePolicyConfig(scenario="C"), events=df)
    plan = split_events(man, EventSplitConfig(test_fraction=0.4, tier_min_test_events=0))

    horizon = 3
    rep = event_forward_return_table(man, rec, bars, plan,
                                     {"horizons": [horizon], "seed": 1, "n_boot": 20})

    ev = rec.event_level.set_index("event_id")
    from_entry, from_t0 = [], []
    for eid in ev.index:
        row = ev.loc[eid]
        entry_idx = int(np.searchsorted(ot, int(row["entry_price_source_bar_open_ms"])))
        t0_idx = int(np.searchsorted(ot, int(row["t0_ms"])))
        # 前置（fail-loud，非靜默略過）：進場根必須**不等於** t0 根，本條才分得出兩種起點
        assert entry_idx != t0_idx, "fixture 之進場根等於 t0 根 ⇒ 本條失去鑑別力，請改 entry_price_semantic"
        entry_price = float(frame[row["entry_price_source_field"]].iloc[entry_idx])
        from_entry.append((float(frame["close"].iloc[entry_idx + horizon]) - entry_price) / entry_price)
        from_t0.append((float(frame["close"].iloc[t0_idx + horizon]) - entry_price) / entry_price)

    got = float(rep["sensitivity_micro"][str(horizon)]["mean"])
    assert len(from_entry) == 2
    # 手算 oracle：窗末＝**entry_idx + h**（micro 等權 ⇒ 兩筆之算術平均）
    assert got == pytest.approx(float(np.mean(from_entry)), abs=1e-12), "報酬表之窗末不是從進場那根往後推 h 根"
    # 對照組：改由 t0 起算會是**不同**的數字
    assert got != pytest.approx(float(np.mean(from_t0)), abs=1e-12)


def test_gap3_metrics_glossary_macro_uses_primary_retained_set():
    """`macro_mean` 之 definition 宣稱「只算主要保留集、且以 uniqueness 權重」——釘住它。

    反例（`CODEX-R3-P2-02`）：首版只說「各 symbol 先各自算平均」，漏了保留集與加權
    ⇒ 使用者無法由 tooltip 重現實際公式，也不知道 macro 的筆數少於 micro。
    """
    from tests.momentum.event_samples.helpers import load_bars
    from tests.momentum.event_samples.test_gap3_horizon_curve import _pipeline, _table

    bars = load_bars("ETHUSDT", ("12h",))
    # 相鄰事件 ⇒ 同一去重叢集；scenario C 之 primary＝cluster_first ⇒ 只留最早那筆
    rec, man, plan = _pipeline(bars, [300, 301, 302], [1, 0, 1])
    rep = _table(bars, man, rec, plan, [1])

    micro_n = int(rep["sensitivity_micro"]["1"]["n"])
    per_symbol_n = int(rep["strata"]["by_symbol"]["ETHUSDT"]["1"]["n"])
    assert micro_n == 3, f"fixture 應有三個事件，實得 {micro_n}"
    assert per_symbol_n < micro_n, (
        f"macro 之 per-symbol 區塊未套用保留集（n={per_symbol_n} 應少於 micro 的 {micro_n}）")
    assert rep["primary_macro"]["1"]["n_symbols"] == 1


def test_gap3_metrics_glossary_n_test_is_three_way_intersection():
    """`n_test` 之 definition 宣稱「測試段 ∩ 有分數 ∩ 有標記」——抽掉一筆分數釘住它。

    反例（`CODEX-R3-P2-03`）：R2 修正後仍寫「也就是決策時間落在切分點之後的事件數」，
    而 `binary_discrimination_table` 取的是三者交集 ⇒ 少一個分數就不成立。
    """
    import numpy as np
    import pandas as pd

    from momentum.Analysis.event_samples.tables import binary_discrimination_table
    from tests.momentum.event_samples.helpers import load_bars
    from tests.momentum.event_samples.test_gap3_horizon_curve import _pipeline

    bars = load_bars("ETHUSDT", ("12h",))
    rec, _man, plan = _pipeline(bars, [300, 320, 340, 360, 380], [1, 0, 1, 0, 1])
    assignments = plan.assignments
    test_ids = list(assignments[assignments["split_label"] == "test"]["event_id"])
    assert len(test_ids) >= 2, f"fixture 之測試段太小（{len(test_ids)}），本條會退化"

    # 標記交錯給（兩類皆有即可）——本條驗的是**交集大小**，與標記從哪來無關
    labels = pd.Series({eid: i % 2 for i, eid in enumerate(test_ids)})
    scores = pd.Series({eid: float(i) / len(test_ids) for i, eid in enumerate(test_ids)})
    strata = pd.DataFrame({"counterexample_kind_effective": [None] * len(test_ids)}, index=pd.Index(test_ids))
    cfg = {"seed": 1, "n_perm": 20, "threshold": 0.5, "top_q": 0.5}

    full = binary_discrimination_table(scores, labels, plan, strata, cfg)["overall"]
    dropped = binary_discrimination_table(scores.iloc[1:], labels, plan, strata, cfg)["overall"]
    assert int(full["n"]) == len(test_ids)
    assert int(dropped["n"]) == len(test_ids) - 1, (
        "抽掉一筆分數後 n 沒有變小 ⇒ n_test 不是三者交集，definition 已失效")
    assert not np.isnan(float(full.get("prevalence", 0.0)))


def test_gap3_metrics_glossary_formula_ref_paths_exist():
    """每個 `formula_ref` 開頭的 repo 路徑須真的存在（防指向已搬走／打錯的檔）。"""
    for key, entry in sorted(mg.load_metrics_glossary().items()):
        rel = entry["formula_ref"].split("::")[0].split("（")[0].strip()
        assert (REPO / rel).exists(), f"{key}.formula_ref 指向不存在的路徑：{rel}"


def test_gap3_metrics_glossary_loader_returns_deep_copy():
    """caller 改寫回傳值不得污染 SoT（沿契約 loader 慣例）。"""
    first = mg.load_metrics_glossary()
    first["macro_mean"]["definition"] = "MUTATED"
    assert mg.load_metrics_glossary()["macro_mean"]["definition"] != "MUTATED"
