"""GAP-3 UX Task 7.6 驗收（`-k event_batch_detail_dims`）：事件批 detail 之**批次事實欄**。

SPEC L3133–3140 之①②③：
- ① 批次事實欄鍵集**集合相等**於 `{scenario, control_kind, direction, label_origin, t0, label}`
  （🔴 `label_origin` 由 `D-001` Task D1.6 於 2026-09-04 加入，覆寫原五鍵）
  （🔴 明列鍵名、不用計數字面——R4 版寫「含六個鍵」，維度六改五時該字面沒同步，三家全員命中）；
  並驗 R11 定死之 wire shape：三個 scalar ＋ 兩個各自兩鍵之陣列、`event_id` 集合相等且升冪。
- ② detail **另含** F-0 種子三鍵，且**不**計入①之集合相等。
- ③ 各值 `==` 該批落檔記錄之**實際值**（非預設值）。

🔴 本檔亦釘住兩條 over 向（不該擋的沒被擋）：混 `control_kind` 之批仍可讀 detail（不 4xx）、
   非預設值之批其種子照實回傳（不被規範成 F-1′ 之預設）。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services import case_import_service as svc_mod
from tests.momentum.event_samples.test_import_contract import canonical_event as make_event

client = TestClient(app)

#: SPEC Task 7.6 三分表之**批次事實欄**封閉集合（本檔唯一一份字面；驗收①明令列鍵名）
#: 批次事實欄之封閉鍵集。
#: 🔴 `D-001` Task D1.6（2026-09-04）**覆寫** Task 7.6 之原五鍵：加入 `label_origin`。
#: 集合相等**未放寬**——少一鍵（`response_model` 漏宣告而被靜默過濾）或多一鍵皆紅。
BATCH_FACT_KEYS = {"scenario", "control_kind", "direction", "t0", "label", "label_origin"}
#: 批次宣告種子（F-0）三鍵
SEED_KEYS = {"entry_price_semantic", "label_return_mode", "decision_offset_bars"}


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    svc = svc_mod.EventImportService(storage_dir=tmp_path / "events")
    monkeypatch.setattr(svc_mod, "_event_import_service", svc)
    return svc


def _import(records: list[dict]) -> str:
    r = client.post("/api/v1/case/import-events/json", json={"records": records, "source_name": "unit"})
    assert r.status_code == 200, r.text
    return r.json()["import_id"]


def _detail(import_id: str) -> dict:
    r = client.get(f"/api/v1/case/events/{import_id}")
    assert r.status_code == 200, r.text
    return r.json()


def test_event_batch_detail_dims_01_fact_keyset_is_exactly_five(_isolated_storage):
    """①(a) 批次事實欄鍵集集合相等於**六**鍵；三個 scalar 欄為 scalar。

    🔴 `D-001` D1.6：`label_origin` 為第六鍵。本 fixture 是 `scenario=C` 之**舊批形態**
    （不帶 `label_origin`）⇒ 該欄須為 `None`（不補值、不猜），這正是舊批通則。
    """
    d = _detail(_import([make_event(i, label=i % 2) for i in range(3)]))
    assert set(d["batch_facts"].keys()) == BATCH_FACT_KEYS
    for key in ("scenario", "control_kind", "direction"):
        assert isinstance(d["batch_facts"][key], str), f"{key} 須為 scalar"
    assert d["batch_facts"]["label_origin"] is None, "舊批（C 且無宣告）須回 null"


def test_event_batch_detail_dims_02_row_arrays_shape_and_order(_isolated_storage):
    """①(b)(c) `t0`／`label` 各為陣列、元素鍵集**互不含對方**、`event_id` 集合相等且升冪。"""
    n = 4
    d = _detail(_import([make_event(i, label=i % 2) for i in range(n)]))
    t0_rows, label_rows = d["batch_facts"]["t0"], d["batch_facts"]["label"]
    assert len(t0_rows) == n == d["summary"]["n_events"]
    assert len(label_rows) == n
    # 元素鍵集恰為自己那兩鍵——`t0` 之元素不得含 `label`，反之亦然
    assert {frozenset(r) for r in t0_rows} == {frozenset({"event_id", "t0_ms"})}
    assert {frozenset(r) for r in label_rows} == {frozenset({"event_id", "label"})}
    # 兩陣列之 event_id 集合相等，且各自按 event_id UTF-8 升冪
    ids_t0 = [r["event_id"] for r in t0_rows]
    ids_label = [r["event_id"] for r in label_rows]
    assert set(ids_t0) == set(ids_label)
    assert ids_t0 == sorted(ids_t0)
    assert ids_label == sorted(ids_label)
    assert all(isinstance(r["t0_ms"], int) for r in t0_rows)
    assert all(r["label"] in (0, 1) for r in label_rows)


def test_event_batch_detail_dims_03_no_scalar_impersonating_batch(_isolated_storage):
    """①禁止以 scalar 冒充整批：兩列 `t0` 不同 ⇒ 陣列裡真的有兩個不同值（非只回第一列）。"""
    recs = [make_event(i, label=i % 2) for i in range(3)]
    d = _detail(_import(recs))
    expected = sorted((r["event_id"], r["t0"]) for r in recs)
    actual = sorted((r["event_id"], r["t0_ms"]) for r in d["batch_facts"]["t0"])
    assert actual == expected
    assert len({t for _, t in actual}) == 3, "三列各有自己的 t0，不得塌成單一值"


def test_event_batch_detail_dims_04_seeds_present_and_not_counted(_isolated_storage):
    """② 種子三鍵另外回傳，且**不**在批次事實欄之鍵集內。"""
    # 🔴 兩列且正反例各一：單一 label 之批會被契約以 `missing_control_group` fail-closed（二元任務缺類別）
    d = _detail(_import([make_event(0, label=1), make_event(1, label=0)]))
    assert set(d["declaration_seeds"].keys()) == SEED_KEYS
    assert SEED_KEYS.isdisjoint(set(d["batch_facts"].keys()))


def test_event_batch_detail_dims_05_values_equal_stored_records(_isolated_storage):
    """③ 各值 `==` 落檔記錄之實際值（**非預設值**）——用非預設之三元組匯入。"""
    recs = [
        make_event(
            i, label=i % 2, scenario="A", control_kind="user_labeled_other",
            entry_price_semantic="next_open", decision_offset_bars=2,
            # `G3-D2` D1.1：`scenario ∈ {A,B,two_stage}` ⇒ `label_origin` 條件必填。
            # 本 fixture 走使用者匯入路徑 ⇒ `user_csv`。
            label_origin="user_csv",
            # 同票：A／two_stage 須深度 ≥ 1，否則 `scenario_depth_inconsistent`。
            lookahead_bars_declared={"12h": 2},
            label_definition={
                "rule_id": "rule-x", "canonical_digest": "c" * 64,
                "window": {"horizon_bars": 2}, "label_return_mode": "open_to_close",
            },
        )
        for i in range(2)
    ]
    d = _detail(_import(recs))
    assert d["batch_facts"]["scenario"] == "A"
    assert d["batch_facts"]["control_kind"] == "user_labeled_other"
    assert d["batch_facts"]["direction"] == recs[0]["direction"]
    assert d["declaration_seeds"]["entry_price_semantic"] == "next_open"
    assert d["declaration_seeds"]["label_return_mode"] == "open_to_close"
    assert d["declaration_seeds"]["decision_offset_bars"] == 2
    # 逐列欄以集合相等比對 event_id，並抽驗任兩列之 t0_ms／label
    assert {r["event_id"] for r in d["batch_facts"]["label"]} == {r["event_id"] for r in recs}
    by_id = {r["event_id"]: r for r in recs}
    for row in d["batch_facts"]["label"][:2]:
        assert row["label"] == by_id[row["event_id"]]["label"]
    for row in d["batch_facts"]["t0"][:2]:
        assert row["t0_ms"] == by_id[row["event_id"]]["t0"]


def test_event_batch_detail_dims_06_mixed_control_kind_is_null_not_majority(_isolated_storage):
    """🔴 主委裁定：批內 `control_kind` distinct > 1 ⇒ scalar 回 `null`，**不取第一列／多數決**。

    為什麼不是「取第一列」：Task 1.8 之同質檢查**不涵蓋 `control_kind`**
    （`_HETEROGENEITY_DIMENSIONS` 只有 direction／scenario／label_definition），
    而 Task 7.5 明文允許混批且**明禁多數決** ⇒ 取第一列即隱性多數決之更差版本。
    混批與「該批沒這個欄」之區分由 `batch_fact_notes.control_kind_values` 承接（不進封閉五鍵）。
    """
    recs = [
        make_event(0, label=1, control_kind="user_labeled_same_trigger"),
        make_event(1, label=0, control_kind="user_labeled_other"),
        make_event(2, label=1, control_kind="user_labeled_other"),
    ]
    d = _detail(_import(recs))
    assert d["batch_facts"]["control_kind"] is None
    assert d["batch_fact_notes"]["control_kind_values"] == ["user_labeled_other", "user_labeled_same_trigger"]
    # 🔴 over 向：混批**不得**因此被擋（detail 仍 200、其餘四個事實欄照常）
    assert d["batch_facts"]["direction"] == recs[0]["direction"]
    assert len(d["batch_facts"]["t0"]) == 3


def test_event_batch_detail_dims_07_single_control_kind_is_not_nulled(_isolated_storage):
    """🔴 over 向對照：單值批**不得**被誤判為混批（`null` 只屬於混批與缺欄）。"""
    d = _detail(_import([make_event(i, label=i % 2) for i in range(3)]))
    assert d["batch_facts"]["control_kind"] == "user_labeled_same_trigger"
    assert d["batch_fact_notes"]["control_kind_values"] == ["user_labeled_same_trigger"]


# ══════════════════════════════════════════════════════════════════════════
# `D-001` Task D1.6 — label_origin 入批次事實六鍵；分析揭露 event_known_at_decision
#
# 選擇器：`pytest tests/api -q -k "event_batch_detail_dims or event_known"`
# ══════════════════════════════════════════════════════════════════════════

def test_event_batch_detail_dims_d16_label_origin_scalar_round_trip(_isolated_storage):
    """(i) 宣告了 `label_origin` 之批 ⇒ detail 回**同一個 scalar**（不是陣列、不是猜測值）。"""
    recs = [
        make_event(i, label=i % 2, scenario="B", label_origin="user_csv",
                   lookahead_bars_declared={"12h": 2})
        for i in range(3)
    ]
    d = _detail(_import(recs))
    assert set(d["batch_facts"].keys()) == BATCH_FACT_KEYS
    assert d["batch_facts"]["label_origin"] == "user_csv"
    assert isinstance(d["batch_facts"]["label_origin"], str), "須為 scalar，不得以陣列冒充"


def test_event_batch_detail_dims_d16_label_origin_null_for_legacy_batch(_isolated_storage):
    """(ii) 舊批（`scenario=C`、無宣告）⇒ `label_origin is None`。

    🔴 **不補值**是通則：補一個值等於替使用者宣告 provenance。
    """
    d = _detail(_import([make_event(i, label=i % 2) for i in range(2)]))
    assert d["batch_facts"]["label_origin"] is None


def test_event_batch_detail_dims_d16_label_origin_not_in_declaration_seeds(_isolated_storage):
    """🔴 `label_origin` 是**事實**不是**參數**：不得出現在分析參數區之種子裡。

    沒有這條，把它誤放進 `declaration_seeds` 會讓 IC 頁把它顯示成「可改的參數」。
    """
    recs = [
        make_event(i, label=i % 2, scenario="B", label_origin="user_csv",
                   lookahead_bars_declared={"12h": 2})
        for i in range(2)
    ]
    d = _detail(_import(recs))
    assert "label_origin" not in d["declaration_seeds"]
    assert set(d["declaration_seeds"].keys()) == SEED_KEYS
