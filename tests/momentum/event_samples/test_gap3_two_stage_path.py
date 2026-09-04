"""GAP-3 `G3-D2` **Task D3.1** 後端驗收——two_stage 之未標籤路徑與去重政策。

選擇器：`pytest tests/momentum/event_samples/test_gap3_two_stage_path.py -q -k d31`

覆蓋 SPEC D-001 D3.1 之後端半邊（前端半邊在 `frontend/src/lib/twoStageExport.test.ts`）：
- **三態匯入**（原 D2.1 之 `search_unlabeled` 定義移至 D3.1）：
  ① `/search` two_stage 匯出檔**直接匯入** ⇒ reasons 集合恰為
     `{missing_required_field, label_origin_not_importable}`；
  ② 補 `label` 但仍帶 `search_unlabeled` ⇒ 仍拒（`label_origin_not_importable`）；
  ③ 補 `label` ＋ `label_origin='user_csv'` ⇒ 通過，且 record 之 `label_origin == 'user_csv'`。
- **去重政策**：two_stage 批之 `policy_primary == 'all_with_uniqueness'`（既有語意，本 Task 釘住）。
- **深度 0** ⇒ `scenario_depth_inconsistent`（與前端阻擋同名 reason；兩端都擋）。

🔴 本檔測**真的** `validate_event_import` 與 `build_event_manifest`，不 mock。
🔴 三態之「匯出檔」形狀由前端 `buildEventContractRecords` 產生；本檔以**同形狀**之 dict
   重現（`label` 鍵缺席、`label_origin='search_unlabeled'`），並在第一條測試裡逐字對證
   契約之 `not_importable` 清單——避免這裡自己寫一份與前端漂移的形狀。
"""

from __future__ import annotations

import pytest

from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.dedupe import build_event_manifest
from momentum.Analysis.event_samples.import_contract import (
    ContractValidationError,
    load_event_import_contract,
    validate_event_import,
)
from momentum.Analysis.event_samples.types import AlignmentConfig, DedupePolicyConfig
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000


def reasons_of(err: ContractValidationError) -> set:
    return {f["reason"] for f in err.failures}


def two_stage_export_row(n: int = 0, **over) -> dict:
    """`/search` 之 two_stage 匯出列（前端 `buildEventContractRecords` 之同形狀）。

    🔴 `label` **鍵缺席**（不是 `None`）——這正是前端那條路徑的形狀，
    也是本三態測試第一態要打的東西。
    """
    fields = {
        "t0": BASE + n * H12,
        "scenario": "two_stage",
        "label_origin": "search_unlabeled",
        "lookahead_bars_declared": {"12h": 2},
    }
    fields.update(over)          # 呼叫端之 override 蓋過預設（含 lookahead_bars_declared）
    row = make_event(n, **fields)
    row.pop("label", None)
    return row


# ══════════════════════════════════════════════════════════════════════════
# 三態匯入
# ══════════════════════════════════════════════════════════════════════════

def test_d31_state1_direct_import_of_unlabeled_export_is_rejected():
    """態①：two_stage 匯出檔**直接匯入** ⇒ 恰兩個 reason。

    🔴 集合**相等**而非 `in`：多一個 reason 代表還有別的東西壞了，
    少一個代表某一道閘沒生效——兩種都該紅。
    """
    contract = load_event_import_contract()
    assert "search_unlabeled" in contract["optional_fields"]["label_origin"]["not_importable"], (
        "前提：契約把 search_unlabeled 列為 not_importable（D1.1 已落地）"
    )
    batch = [two_stage_export_row(i) for i in range(2)]
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert reasons_of(ei.value) == {"missing_required_field", "label_origin_not_importable"}


def test_d31_state2_label_filled_but_origin_still_unlabeled_is_rejected():
    """態②：補了 `label`，但 `label_origin` 仍是 `search_unlabeled` ⇒ 仍拒。

    這條擋的是「使用者在 Excel 補了答案卻沒改來源」——那批的 provenance 仍然說
    「這是搜尋頁匯出的未標籤檔」，與事實（使用者自己標的）不符。
    """
    batch = [two_stage_export_row(i) for i in range(2)]
    for i, row in enumerate(batch):
        row["label"] = i % 2
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    rs = reasons_of(ei.value)
    assert "label_origin_not_importable" in rs
    assert "missing_required_field" not in rs, "label 已補，不該再報缺必填"


def test_d31_state3_label_filled_and_origin_user_csv_passes():
    """態③：補 `label` ＋ 改 `label_origin='user_csv'` ⇒ **通過**，且落檔為 `user_csv`。

    🔴 這是本路徑的**目標狀態**：兩段式匯出故意匯不進去，逼使用者補標後宣告
    「這是我自己標的」。沒有這條，前兩條的拒收就可能是「把整條路擋死」而非「擋對地方」。
    """
    batch = [two_stage_export_row(i) for i in range(2)]
    for i, row in enumerate(batch):
        row["label"] = i % 2
        row["label_origin"] = "user_csv"
    df = validate_event_import(batch)
    assert len(df) == 2
    assert set(df["label_origin"]) == {"user_csv"}


def test_d31_state3_over_direction_scenario_still_two_stage():
    """🔴 **over 向**：態③通過之後，`scenario` 仍是 `two_stage`。

    沒有這條，「把 scenario 一併改成 B 才通過」的實作也會讓態③綠——
    那等於偷偷把使用者的情境改掉。
    """
    batch = [two_stage_export_row(i) for i in range(2)]
    for i, row in enumerate(batch):
        row["label"] = i % 2
        row["label_origin"] = "user_csv"
    df = validate_event_import(batch)
    assert set(df["scenario"]) == {"two_stage"}


# ══════════════════════════════════════════════════════════════════════════
# 深度 0
# ══════════════════════════════════════════════════════════════════════════

def test_d31_depth_zero_two_stage_is_rejected():
    """深度 0 ＋ two_stage ⇒ `scenario_depth_inconsistent`（與前端阻擋同名 reason）。

    兩端都擋是刻意的：前端擋讓使用者當場看得懂，後端擋讓繞過前端的檔也進不來。
    """
    batch = [two_stage_export_row(i, lookahead_bars_declared={"12h": 0}) for i in range(2)]
    for i, row in enumerate(batch):
        row["label"] = i % 2
        row["label_origin"] = "user_csv"
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "scenario_depth_inconsistent" in reasons_of(ei.value)


def test_d31_depth_one_two_stage_is_accepted():
    """🔴 **over 向**：深度 1 通過——證明上一條擋的是「深度 0」，不是「two_stage」。"""
    batch = [two_stage_export_row(i, lookahead_bars_declared={"12h": 1}) for i in range(2)]
    for i, row in enumerate(batch):
        row["label"] = i % 2
        row["label_origin"] = "user_csv"
    assert len(validate_event_import(batch)) == 2


# ══════════════════════════════════════════════════════════════════════════
# 去重政策
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def bars():
    """🔴 真實 kline（`data_cache/feature_klines/kline_cache.h5`）——禁合成 fixture。"""
    return load_bars("ETHUSDT", ("12h",))


def _manifest_for(bars, scenario: str):
    """走**真實**對齊路徑取得該 scenario 之 dedupe 政策。

    🔴 `build_event_manifest` 收的是 `AlignmentReceipts`（有 `.event_level`），
    不是 DataFrame——本檔第一版直接餵 DataFrame 而 `AttributeError`。
    改走與 `test_tables.py::pipeline` 相同的真實路徑，不自造 receipts 形狀。
    """
    events = [
        make_event(
            i, t0=BASE + n * H12, label=i % 2, scenario=scenario,
            lookahead_bars_declared={"12h": 2},
            **({"label_origin": "user_csv"} if scenario in ("A", "B", "two_stage") else {}),
        )
        for i, n in enumerate((300, 600))
    ]
    df = validate_event_import(events)
    rec, fail = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
    assert fail.empty
    return build_event_manifest(rec, DedupePolicyConfig(scenario=scenario), events=df)


def test_d31_two_stage_dedupe_policy_is_all_with_uniqueness(bars):
    """two_stage 批之 `policy.primary == 'all_with_uniqueness'`（SPEC D3.1 驗證第二條）。

    🔴 這條**不是**本 Task 新做的行為（`_POLICY_BY_SCENARIO` 早有 two_stage），
    但在 two_stage 解灰之前它從未被走到過——解灰即等於把它推上線，故本 Task 釘住它。
    """
    man = _manifest_for(bars, "two_stage")
    assert man.policy["primary"] == "all_with_uniqueness"
    # 全留政策**必配** cluster-robust（下游顯著性據此強制），否則 raw-all 會被當成獨立樣本
    assert man.policy["requires_cluster_robust"] is True


def test_d31_dedupe_policy_over_direction_c_is_cluster_first(bars):
    """🔴 **over 向**：C 仍是 `cluster_first`。

    沒有這條，「一律回 all_with_uniqueness」的實作也會讓上一條綠。
    """
    man = _manifest_for(bars, "C")
    assert man.policy["primary"] == "cluster_first"
    assert man.policy["requires_cluster_robust"] is False
