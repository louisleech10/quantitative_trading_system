"""SPLITUNIFY `Task 10.4`／`R5-C8`：逐事件處置帳。

驗的是什麼：兩端差集與剔除揭露只有一個來源；`ic_disposition` 是**入口之預測**，
不得讀 stage3（讀了就是拿自己比自己，`Task 10.7` 的對證會恆真）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from momentum.Analysis.event_samples.event_disposition import (
    build_event_disposition_ledger,
    disposition_values,
    excluded_by_symbol,
)

REPO = Path(__file__).resolve().parents[3]
CONTRACT = REPO / "momentum/Analysis/contracts/split_unify.json"
RUN_SYM = "ETHUSDT"
H1 = 3_600_000
BASE = 1_700_000_000_000


def _ev(eid, sym=RUN_SYM):
    return {"event_id": eid, "symbol": sym}


def test_disposition_values_read_from_contract() -> None:
    """🔴 值集自契約讀，**手打即紅**（`R5-C8` 2.）。

    本條同時擋兩種退化：①程式內手打字面；②契約鍵被刪掉而程式回退到內建預設。
    """
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    vals = contract["event_disposition_values"]
    got = disposition_values()
    assert set(got) == set(vals), f"值集之欄不符：{sorted(got)} vs {sorted(vals)}"
    for k in vals:
        assert list(got[k]) == list(vals[k]), f"{k} 之值集與契約不逐值相符"
    # 手打一個不在契約內的值 ⇒ 必須被擋
    with pytest.raises(ValueError, match="封閉值集"):
        build_event_disposition_ledger(
            events=[_ev("e0")], run_symbol=RUN_SYM,
            aligned_event_ids={"e0"}, coverage_ok_event_ids={"e0"},
            feature_row_key_by_id={"e0": BASE}, post_trim_index_ms={BASE},
            label_value_by_id={"e0": 0.1},
        ) if False else _force_invalid()


def _force_invalid():
    """以契約外之字面直呼內部檢查，證明封閉值集真的會擋（不是只寫在註解裡）。"""
    from momentum.Analysis.event_samples.event_disposition import _check

    return _check("totally_made_up", "ic_disposition")


def test_each_event_exactly_one_row() -> None:
    """`R5-C8` 1.：每個通過匯入驗證之 `event_id` 恰一列；重複即 fail-closed。"""
    rows = build_event_disposition_ledger(
        events=[_ev("a"), _ev("b")], run_symbol=RUN_SYM,
        aligned_event_ids={"a", "b"}, coverage_ok_event_ids={"a", "b"},
        feature_row_key_by_id={"a": BASE, "b": BASE + H1},
        post_trim_index_ms={BASE, BASE + H1}, label_value_by_id={"a": 0.1, "b": -0.2},
    )
    assert [r.event_id for r in rows] == ["a", "b"]
    assert all(r.ic_disposition == "ic_consumed" for r in rows)
    with pytest.raises(ValueError, match="恰一列"):
        build_event_disposition_ledger(
            events=[_ev("a"), _ev("a")], run_symbol=RUN_SYM,
            aligned_event_ids={"a"}, coverage_ok_event_ids={"a"},
            feature_row_key_by_id={"a": BASE}, post_trim_index_ms={BASE},
            label_value_by_id={"a": 0.1},
        )


def test_scan_disposition_outside_post_trim_index() -> None:
    """🔴 錨點在 manifest 區間內、在 **post-trim 索引外** ⇒ `outside_post_trim_index`。

    鑑別力（`M-SU-R5-13`）：略過 post-trim 首尾剔除（改以 manifest 區間判定）⇒ 本條轉紅。
    """
    rows = build_event_disposition_ledger(
        events=[_ev("trimmed")], run_symbol=RUN_SYM,
        aligned_event_ids={"trimmed"}, coverage_ok_event_ids={"trimmed"},
        feature_row_key_by_id={"trimmed": BASE},          # 錨點存在
        post_trim_index_ms={BASE + H1, BASE + 2 * H1},    # 但已被裁掉
        label_value_by_id={"trimmed": 0.1},
    )
    assert rows[0].scan_disposition == "outside_post_trim_index"
    assert rows[0].ic_disposition == "feature_row_not_in_feature_index"


def test_boundary_event_ledger_predicts_feature_row_not_in_feature_index() -> None:
    """🔴 邊界事件：`feature_cutoff_ms ∈ post-trim 索引` 但 `last_bar_open_ms ∉` ⇒ 預測為
    `feature_row_not_in_feature_index`。

    這正是換錨之後才會出現的一類——以**收盤**判會說「在索引內」，以**開盤**（實際消費之列）
    判才看得出不在。fixture 前提不成立即 fail（擋空心通過）。
    """
    cutoff, anchor = BASE + H1, BASE          # 開盤在前、收盤在後
    post_trim = {cutoff, cutoff + H1}         # 只含收盤那根，不含錨點那根
    assert cutoff in post_trim and anchor not in post_trim, "fixture 前提不成立，本條空心"
    rows = build_event_disposition_ledger(
        events=[_ev("bnd")], run_symbol=RUN_SYM,
        aligned_event_ids={"bnd"}, coverage_ok_event_ids={"bnd"},
        feature_row_key_by_id={"bnd": anchor},   # `R5-C9` 之鍵＝開盤
        post_trim_index_ms=post_trim, label_value_by_id={"bnd": 0.1},
    )
    assert rows[0].ic_disposition == "feature_row_not_in_feature_index", (
        "以收盤判會誤判為在索引內——本條就是要擋那個"
    )


def test_decision_order_is_align_symbol_coverage_label_row() -> None:
    """`R5-C8` 3.：判定順序不可調。前一段成立才輪到後一段。"""
    # 對齊失敗優先於 symbol 不符
    rows = build_event_disposition_ledger(
        events=[_ev("x", sym="BTCUSDT")], run_symbol=RUN_SYM,
        aligned_event_ids=set(), coverage_ok_event_ids=set(),
        feature_row_key_by_id={}, post_trim_index_ms=set(),
    )
    assert rows[0].ic_disposition == "align_failed", "對齊失敗須優先於 symbol 判定"

    # symbol 不符優先於 coverage
    rows = build_event_disposition_ledger(
        events=[_ev("y", sym="BTCUSDT")], run_symbol=RUN_SYM,
        aligned_event_ids={"y"}, coverage_ok_event_ids=set(),
        feature_row_key_by_id={}, post_trim_index_ms=set(),
    )
    assert rows[0].ic_disposition == "symbol_not_run_symbol"

    # label 值缺席優先於特徵列判定
    rows = build_event_disposition_ledger(
        events=[_ev("z")], run_symbol=RUN_SYM,
        aligned_event_ids={"z"}, coverage_ok_event_ids={"z"},
        feature_row_key_by_id={"z": BASE}, post_trim_index_ms=set(),
        label_value_by_id={"z": None},
    )
    assert rows[0].ic_disposition == "label_value_unavailable"


def test_excluded_by_symbol_is_derived_not_recomputed() -> None:
    """`R5-C8` 4.：`excluded_by_symbol` 由處置帳導出，不另算。"""
    rows = build_event_disposition_ledger(
        events=[_ev("a"), _ev("b", sym="BTCUSDT"), _ev("c", sym="BCHUSDT")],
        run_symbol=RUN_SYM,
        aligned_event_ids={"a", "b", "c"}, coverage_ok_event_ids={"a", "b", "c"},
        feature_row_key_by_id={"a": BASE}, post_trim_index_ms={BASE},
        label_value_by_id={"a": 0.1},
    )
    assert excluded_by_symbol(rows) == ["b", "c"]


def test_ledger_does_not_read_stage3() -> None:
    """🔴 `R5-C8` 6.：`ic_disposition` 為**預測**，簽名內不得出現 stage3 之觀測面。

    以函式簽名為機械判準：出現 `observed`／`stage3` 一類參數即代表讀了觀測，
    那會讓 `Task 10.7` 的預測-觀測對證變成拿自己比自己。
    """
    import inspect

    sig = inspect.signature(build_event_disposition_ledger)
    bad = [p for p in sig.parameters if "observ" in p.lower() or "stage3" in p.lower()]
    assert not bad, f"處置帳簽名混入觀測面參數：{bad}"


def test_observed_values_come_from_contract_not_hardcoded() -> None:
    """🔴 `CODEX-R41-P1-02`：stage3 之 `observed` 字面由契約出口取得，不得手打。

    鑑別力：契約改名後，producer 仍吐舊字面即紅（本條以出口回傳值直接對證契約）。
    """
    from momentum.Analysis.event_samples.event_disposition import observed_values

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    observed = contract["event_disposition_values"]["observed"]
    # 🔴 `CODEX-R42-P1-01`：契約已改為**具名 mapping**——以順序定語意時，值集重排即靜默反語意。
    assert isinstance(observed, dict), f"observed 須為具名 mapping，實得 {type(observed).__name__}"
    assert set(observed) == {"consumed", "row_missing"}, f"observed 之鍵不符：{sorted(observed)}"
    got = observed_values()
    assert got == {"consumed": observed["consumed"], "row_missing": observed["row_missing"]}, (
        f"出口之值與契約不符：{got} vs {observed}"
    )


def test_observed_semantics_survive_contract_reordering() -> None:
    """🔴 `CODEX-R42-P1-01` 之回歸：契約鍵順序調換時，語意**不得**跟著反轉。

    鑑別力：把 `observed` 改回 list 並以第一／第二值定義語意 ⇒ 本條轉紅。
    """
    import json as _json

    from momentum.Analysis.event_samples.event_disposition import (
        disposition_values,
        observed_values,
    )

    base = observed_values()
    raw = _json.loads(CONTRACT.read_text(encoding="utf-8"))
    ov = raw["event_disposition_values"]["observed"]
    # 以相反插入順序重建同一組具名對應——語意由鍵決定，結果必須不變。
    reordered = {"row_missing": ov["row_missing"], "consumed": ov["consumed"]}
    assert list(reordered) != list(ov), "fixture 未真的調換順序，本條空心"

    raw["event_disposition_values"]["observed"] = reordered
    orig = CONTRACT.read_text(encoding="utf-8")
    try:
        CONTRACT.write_text(_json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        disposition_values.cache_clear()
        assert observed_values() == base, "契約鍵順序調換後語意被反轉——順序依賴未消除"
    finally:
        CONTRACT.write_text(orig, encoding="utf-8")
        disposition_values.cache_clear()


def test_stage3_producer_has_no_hardcoded_observed_literal() -> None:
    """producer 內不得出現 `observed` 之手打字面（機械判準）。"""
    import inspect

    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    src = inspect.getsource(ICFilterOrchestrator)
    # 🔴 錨到**組裝處**而非建構期預設／入口歸零——後兩者同樣是 `= {}`，
    #    用第一個命中會抓到空 dict 那行，整條測試就變成空心的。
    idx = src.find('"feature_row_open_ms"')
    assert idx > 0, "找不到 stage3 收據之組裝處（feature_row_open_ms）"
    block = src[max(0, idx - 400): idx + 400]
    assert '"ic_consumed"' not in block and '"feature_row_not_in_feature_index"' not in block, (
        "stage3 收據仍手打 observed 字面——契約改名時不會在 producer 邊界 fail-closed"
    )
    assert "observed_values()" in block, "未經契約出口取值"


def test_contract_change_takes_effect_without_manual_cache_clear() -> None:
    """🔴 `CODEX-R42-P2-02`：契約改檔後同一行程內須**立即**生效，不靠手動清快取。

    前版 `@lru_cache(maxsize=1)` 鎖在函式上 ⇒ warm cache 後改契約不生效：
    長生命週期行程（API server）會一直用舊值，同行程內之 mutation 覆核也會假綠。
    現改以檔案 `mtime_ns` 當快取鍵。
    鑑別力：把快取鍵改回無參數之 `@lru_cache(maxsize=1)` ⇒ 本條轉紅。
    """
    import json as _json
    import time

    from momentum.Analysis.event_samples.event_disposition import observed_values

    warm = observed_values()          # 先 warm cache（**不**清）
    orig = CONTRACT.read_text(encoding="utf-8")
    raw = _json.loads(orig)
    raw["event_disposition_values"]["ic_disposition"].append("probe_only_value")
    raw["event_disposition_values"]["observed"]["row_missing"] = "probe_only_value"
    try:
        time.sleep(0.01)              # 確保 mtime_ns 真的前進
        CONTRACT.write_text(_json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        got = observed_values()       # 🔴 不清快取
        assert got["row_missing"] == "probe_only_value", (
            f"契約已改但 accessor 仍回舊值（warm cache 假綠）：{got} vs warm={warm}"
        )
    finally:
        CONTRACT.write_text(orig, encoding="utf-8")
    assert observed_values() == warm, "還原後未回到原值"


def test_duplicate_json_key_in_contract_is_fail_closed() -> None:
    """🔴 `CODEX-R43-P1-01`：契約含重複 JSON 成員 ⇒ fail-closed。

    `json.loads` 對重複鍵是 **last-wins 且靜默**：契約若在合併／生成／部署時長出第二個
    `consumed`，accessor 會把後者當語意值，而 exact-key／subset／不重複三道檢查**全過**
    （提出方實跑得到 `{'consumed': 'align_failed', ...}`）。
    更糟的是既有測試以同一個 `json.loads` 結果對證 ⇒ parser、accessor、測試三方共因假綠。
    鑑別力：移除 `object_pairs_hook` 即轉綠（＝本條失效），故本條同時釘住該鉤子存在。
    """
    from momentum.Analysis.event_samples.event_disposition import (
        disposition_values,
        observed_values,
    )

    orig = CONTRACT.read_text(encoding="utf-8")
    # 直接以文字插入第二個 `consumed` 成員（json.dumps 造不出重複鍵）
    dup = orig.replace(
        '"consumed": "ic_consumed",',
        '"consumed": "ic_consumed",\n      "consumed": "align_failed",',
        1,
    )
    assert dup != orig, "fixture 未真的插入重複鍵，本條空心"
    try:
        CONTRACT.write_text(dup, encoding="utf-8")
        disposition_values.cache_clear()
        with pytest.raises(ValueError, match="重複 JSON 鍵"):
            observed_values()
    finally:
        CONTRACT.write_text(orig, encoding="utf-8")
        disposition_values.cache_clear()


def test_contract_change_with_preserved_mtime_still_takes_effect() -> None:
    """🔴 `CODEX-R43-P2-02`：內容變更而 **mtime 被保留**時，快取仍須失效。

    以 `mtime_ns` 為快取鍵時，同奈秒寫入／`cp -p`／`os.utime` 還原都會讓 accessor
    回舊值（提出方實跑：`content_changed=True mtime_same=True stale=True`）。
    改以**內容雜湊**為鍵後，mtime 是否前進與快取無關。
    鑑別力：把鍵改回 `st_mtime_ns` ⇒ 本條轉紅。
    """
    import json as _json
    import os

    from momentum.Analysis.event_samples.event_disposition import observed_values

    warm = observed_values()                      # warm cache（**不**清）
    orig = CONTRACT.read_text(encoding="utf-8")
    st = CONTRACT.stat()
    raw = _json.loads(orig)
    raw["event_disposition_values"]["ic_disposition"].append("probe_mtime_value")
    raw["event_disposition_values"]["observed"]["row_missing"] = "probe_mtime_value"
    try:
        CONTRACT.write_text(_json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        os.utime(CONTRACT, ns=(st.st_atime_ns, st.st_mtime_ns))   # 還原 mtime
        assert CONTRACT.stat().st_mtime_ns == st.st_mtime_ns, "fixture 未保留 mtime，本條空心"
        got = observed_values()                   # 不清快取
        assert got["row_missing"] == "probe_mtime_value", (
            f"mtime 被保留時快取回舊值（stale）：{got} vs warm={warm}"
        )
    finally:
        CONTRACT.write_text(orig, encoding="utf-8")
        os.utime(CONTRACT, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert observed_values() == warm, "還原後未回到原值"


def test_returned_values_are_defensive_copy_not_cache_alias() -> None:
    """🔴 `CODEX-R44-P1-01`／`COMPOSER-R44-P2-01`：公共邊界須回**深複本**。

    前版把 `lru_cache` 持有之 dict 原樣交出 ⇒ 呼叫端一改就污染後續所有呼叫，
    而契約 bytes 與其 sha **都沒變** ⇒ 前四層守衛（手打字面、順序、重複鍵、快取陳舊）
    全部繞過。這是本票同型缺陷的第五層：守衛都在「讀進來」那一側，
    污染卻發生在「交出去之後」。
    鑑別力：把 `copy.deepcopy` 拿掉 ⇒ 本條轉紅（巢狀與頂層兩種突變各驗一次；
    淺複製只會讓頂層那段轉綠、巢狀那段仍紅）。
    """
    from momentum.Analysis.event_samples.event_disposition import (
        _check,
        disposition_values,
        observed_values,
    )

    base_observed = observed_values()
    vals = disposition_values()
    # ① 巢狀 mapping 就地改
    vals["observed"]["consumed"] = "align_failed"
    # ② 頂層序列就地換
    vals["ic_disposition"] = tuple(vals["ic_disposition"]) + ("probe_only_value",)

    assert observed_values() == base_observed, (
        f"巢狀突變污染了快取：{observed_values()} vs {base_observed}"
    )
    with pytest.raises(ValueError, match="封閉值集"):
        _check("probe_only_value", "ic_disposition")
    assert disposition_values()["observed"]["consumed"] == base_observed["consumed"], (
        "再次取得之值集仍帶有前次突變"
    )
