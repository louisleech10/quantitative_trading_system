"""GAP-3 UX `D-004 A-020` 驗收（`-k gap3_attached_columns_contract`）：Task 4.1 之匯出欄納入契約。

為什麼有這一檔：SPEC Task 4.1 要求 `/search` 匯出記錄帶 `future_{h}bar_return` 與
`lookahead_bars_declared`，而契約 validator **兩者皆以 `unknown_field` 拒收**（實測）。
`/search` 匯出之檔就是拿來匯入的 ⇒ 照 SPEC 字面實作會產出**匯不回去的檔**。
三家 consult 裁定改契約（`D-004 A-020`），本檔為該裁定之七條驗收。

🔴 ⑦ **刻意不驗契約 doc 之字串**——doc 是散文，只驗字串等於把「不進 `ic_feed`」
這條限制降級成宣稱；改為**實跑** `build_event_ic_inputs()` 斷言其回傳不含 `future_` 前綴之鍵。
"""

from __future__ import annotations

import pytest

from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.event_split import split_events
from momentum.Analysis.event_samples.ic_feed import build_event_ic_inputs
from momentum.Analysis.event_samples.import_contract import (
    ContractValidationError,
    load_event_import_contract,
    validate_event_import,
)
from momentum.Analysis.event_samples.types import AlignmentConfig, DedupePolicyConfig, EventSplitConfig
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000
DECLARED = {"12h": 0}


def two_rows(**over) -> list:
    """雙列（label 0/1；契約要求批內有對照組）；`over` 逐列套用。"""
    return [
        make_event(0, t0=BASE + 300 * H12, label=1, **over),
        make_event(1, t0=BASE + 600 * H12, label=0, **over),
    ]


def reasons_of(exc: ContractValidationError) -> set:
    return {(f.get("field"), f.get("reason")) for f in exc.value.failures}


def test_gap3_attached_columns_contract_accepts_declared_and_future_columns():
    """① 帶 `lookahead_bars_declared` 與三個 `future_*` 之雙列事件可通過 validator。

    這一條就是「4.1 之匯出檔匯得回去」本身——改契約前它必然紅（8× `unknown_field`）。
    """
    rows = two_rows(
        lookahead_bars_declared=DECLARED,
        future_1bar_return=0.011,
        future_3bar_return=-0.004,
        future_7bar_return=0.02,
    )
    df = validate_event_import(rows)
    assert len(df) == 2
    # 值須原樣保留（不得被正規化吃掉）
    assert df.iloc[0]["lookahead_bars_declared"] == DECLARED
    assert df.iloc[0]["future_7bar_return"] == 0.02


@pytest.mark.parametrize(
    "bad_value,label",
    [
        (True, "bool"),
        ({"12h": True}, "bool_value"),
        ({"12h": -1}, "negative"),
        ({12: 0}, "non_str_key"),
        ({"12h": 1.5}, "float_value"),
        ("12h=0", "str"),
    ],
    ids=["bool", "bool_value", "negative", "non_str_key", "float_value", "str"],
)
def test_gap3_attached_columns_contract_rejects_bad_declared_map(bad_value, label):
    """② `lookahead_bars_declared` 非 `Mapping[str,int>=0]` ⇒ 拒（`type_error`）。

    🔴 `bool ⊂ int`：`{"12h": True}` 會通過 `isinstance(v, int)` 卻序列化成 `true`——
    判定共用 `receipt_type_ok` 之同一函式參考，這個坑才不會只補一邊。
    """
    with pytest.raises(ContractValidationError) as exc:
        validate_event_import(two_rows(lookahead_bars_declared=bad_value))
    assert ("lookahead_bars_declared", "type_error") in reasons_of(exc)


def test_gap3_attached_columns_contract_rejects_non_float_future_column():
    """③ `future_*` 之值非數值 ⇒ `type_error`（逐欄，非只第一欄）。"""
    with pytest.raises(ContractValidationError) as exc:
        validate_event_import(two_rows(future_3bar_return="0.02", future_7bar_return=True))
    failed = reasons_of(exc)
    assert ("future_3bar_return", "type_error") in failed
    assert ("future_7bar_return", "type_error") in failed


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")], ids=["nan", "inf", "-inf"])
def test_gap3_attached_columns_contract_rejects_non_finite_future_column(bad):
    """③b 🔴 R1 `CODEX-R1-P2-01`：`future_*` 之 NaN／±Inf ⇒ `type_error`。

    codex 實跑反例：初版用 `_is_num` 只排除 `bool`，三種非有限值全部 `accepted; isfinite=False`
    ⇒ 直接寫進事件檔。`CLAUDE.md` 明禁弱化 NaN/inf 閘，而這些欄正是給人拿去 Excel 算統計的。
    """
    with pytest.raises(ContractValidationError) as exc:
        validate_event_import(two_rows(future_3bar_return=bad))
    assert ("future_3bar_return", "type_error") in reasons_of(exc)
    # 對照：有限值照樣通過（否則「全部拒收」也會讓上一行綠）
    assert len(validate_event_import(two_rows(future_3bar_return=0.02))) == 2


def test_gap3_attached_columns_contract_no_double_registration():
    """④ 防雙登記：`lookahead_bars_declared` 不得同時列於 `derived_fields.names` 與 `optional_fields`。

    🔴 讀**契約檔**斷言，不是讀碼——雙登記時 `derived_fields.doc`（「匯入檔出現 ⇒ unknown_field」）
    與 `optional_fields`（合法選填）會同時宣稱兩件互斥的事。
    """
    c = load_event_import_contract()
    derived = set(c["derived_fields"]["names"])
    optional = set(c["optional_fields"])
    assert "lookahead_bars_declared" in optional
    assert "lookahead_bars_declared" not in derived
    assert derived & optional == set()


def test_gap3_attached_columns_contract_receipt_batch_key_preserved():
    """⑤ `receipt_schema.batch.lookahead_bars_declared` 仍在（型別字面不變）。

    🔴 這是**第三處**、不在雙登記之禁止範圍：三家 consult 皆明列「移出 `derived_fields`
    但**保留** receipt batch schema，對齊後複製至該處」。沒有這一條，④ 會誘導把三處都清掉。
    """
    c = load_event_import_contract()
    assert c["receipt_schema"]["batch"]["lookahead_bars_declared"] == "Mapping[str,int>=0]"


def test_gap3_attached_columns_contract_rejects_batch_inconsistent_declared():
    """⑥ 同批各列 `lookahead_bars_declared` 值不同 ⇒ 拒（批內一致性）。

    🔴 該欄是**批次層**屬性（逐列同值只為滿足 SPEC 4.1 驗收④之 `records[0].…` 字面）；
    列間不同值時「這批的深度是多少」沒有定義。
    🔴 本檢查**不受 `enforce_batch_homogeneity` 約束**——該旗標預設 `False`，
    掛上去等於預設不檢查。本測試刻意**不傳**該旗標，就是在釘這件事。
    """
    rows = [
        make_event(0, t0=BASE + 300 * H12, label=1, lookahead_bars_declared={"12h": 0}),
        make_event(1, t0=BASE + 600 * H12, label=0, lookahead_bars_declared={"12h": 6}),
    ]
    with pytest.raises(ContractValidationError) as exc:
        validate_event_import(rows)
    assert ("lookahead_bars_declared", "heterogeneous_rows_in_batch") in reasons_of(exc)


def test_gap3_attached_columns_contract_rejects_partially_present_declared():
    """⑥b 🔴 R2 `CODEX-R2-P1-02`：`lookahead_bars_declared` **只出現在部分列** ⇒ 拒。

    codex 實跑反例：一列帶 `{"12h":0}`、另一列省略 ⇒ 舊版 `ACCEPTED`，第二列在 DataFrame 裡是 `nan`。
    那不是「這批沒宣告深度」，是**假裝有宣告的批**——下游讀到 `nan` 會當成缺值靜默處理。
    🔴 判準＝**全有全無**：整批都帶（值須相同，見⑥）或整批都不帶（`optional_fields` 之語意）。
    """
    rows = [
        make_event(0, t0=BASE + 300 * H12, label=1, lookahead_bars_declared=DECLARED),
        make_event(1, t0=BASE + 600 * H12, label=0),          # 刻意省略
    ]
    with pytest.raises(ContractValidationError) as exc:
        validate_event_import(rows)
    assert ("lookahead_bars_declared", "heterogeneous_rows_in_batch") in reasons_of(exc)

    # 對照①：**整批都不帶** ⇒ 合法（`optional_fields` 省略本來就允許）
    assert len(validate_event_import(two_rows())) == 2
    # 對照②：**整批都帶且同值** ⇒ 合法
    assert len(validate_event_import(two_rows(lookahead_bars_declared=DECLARED))) == 2


def test_gap3_attached_columns_contract_future_columns_never_reach_ic_feed():
    """⑦ `ic_feed` 隔離之**執行期**斷言：附帶欄不進條件 IC 的餵入。

    🔴 判準刻意不是「契約 doc 有沒有寫那句話」——doc 是散文，驗字串等於把限制降級成宣稱。
    這裡實跑整條 `validate → align → manifest → split → build_event_ic_inputs`，
    斷言回傳裡**任何層級**都不出現 `future_` 前綴之鍵，且 label 值逐一來自 `label_value`。

    🔴 誠實邊界：本斷言目前**恆綠**（`build_event_ic_inputs` 結構上只讀 `label_value`）。
    它的價值在**日後有人改壞會轉紅**——配套 mutation ＝ 把 label 值改成取 `future_1bar_return`。
    """
    bars = load_bars("ETHUSDT", ("12h",))
    label_values = [0.021, -0.013]
    rows = [
        make_event(
            0, t0=BASE + 300 * H12, label=1, label_value=label_values[0],
            lookahead_bars_declared=DECLARED, future_1bar_return=0.9, future_7bar_return=-0.9,
        ),
        make_event(
            1, t0=BASE + 600 * H12, label=0, label_value=label_values[1],
            lookahead_bars_declared=DECLARED, future_1bar_return=0.8, future_7bar_return=-0.8,
        ),
    ]
    df = validate_event_import(rows)
    receipts, failed = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
    assert failed.empty
    manifest = build_event_manifest(receipts, DedupePolicyConfig(scenario="C"), events=df)
    plan = split_events(manifest, EventSplitConfig(test_fraction=0.4, tier_min_test_events=0))
    out = build_event_ic_inputs(manifest, plan, df, receipts, timeframe="12h")

    assert out["capability_status"] != "unavailable", out.get("reason")
    # 任何層級都不得出現附帶欄（含 dict 之鍵與巢狀 dict 之鍵）
    def keys_deep(obj) -> set:
        found: set = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                found.add(str(k))
                found |= keys_deep(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                found |= keys_deep(v)
        return found

    leaked = {k for k in keys_deep(out) if k.startswith("future_")}
    assert leaked == set(), f"附帶欄洩漏進 ic_feed 之回傳：{sorted(leaked)}"
    # label 值逐一來自 label_value——不是 future_1bar_return（0.9／0.8）
    assert sorted(out["event_label_values"].values()) == sorted(label_values)
