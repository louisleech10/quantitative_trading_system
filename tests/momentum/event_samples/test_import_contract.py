"""Task B1.0 驗證：契約鍵集閉合、枚舉閉集、fail-closed、ms 閘、digest 篡改、批內單值。

對應 docs/GAP3_EVENT_TODO.md Task B1.0 驗證①–⑦與邊界①–④。
"""

from __future__ import annotations

import copy
import hashlib

import pytest

from momentum.Analysis.event_samples.import_contract import (
    ContractValidationError,
    allowed_top_level_keys,
    load_event_import_contract,
    validate_event_import,
)

T0 = 1704067200000  # 2024-01-01 00:00 UTC，12h bar open（真實 kline 網格）
TF_MS = 43200000


def make_event(n: int = 0, **over) -> dict:
    """平台／單元層 fixture：`event_id` 用短名 `ev{n}`。

    🔴 **使用者匯入路徑**（API 端點）另有 D-2 canonical 約束（Task 1.3），
    那一層之 fixture 請用 `canonical_event()`——本函式刻意不改，
    因為 `validate_event_import` 直呼與 `pipeline.run` 皆**不**強制該約束。
    """
    e = {
        "event_id": f"ev{n}",
        "symbol": "ETHUSDT",
        "timeframe": "12h",
        "t0": T0 + n * TF_MS,
        "decision_offset_bars": 0,
        "entry_price_semantic": "trigger_open",
        "direction": "long",
        "scenario": "C",
        "label": 1,
        "label_definition": {
            "rule_id": "rule-x",
            "canonical_digest": "c" * 64,
            "window": {"horizon_bars": 2},
            "label_return_mode": "close_to_close",
        },
        "control_kind": "user_labeled_same_trigger",
        "source_file_digest": "a" * 64,
        "data_snapshot_digest": "b" * 64,
    }
    e.update(over)
    return e


def canonical_event(n: int = 0, **over) -> dict:
    """使用者匯入路徑之 fixture：`event_id` 依契約 `event_id_template` 產生（Task 1.3／D-2）。

    公式**不在此重寫**——直接呼叫 `import_contract.canonical_event_id`（唯一實作），
    否則測試自己就成了第二份副本（CODEX-R1-P1-01 之同型病）。
    """
    from momentum.Analysis.event_samples.import_contract import canonical_event_id

    e = make_event(n, **over)
    e["event_id"] = canonical_event_id(e["symbol"], e["timeframe"], e["t0"])
    if "event_id" in over:
        e["event_id"] = over["event_id"]
    # 🔴 R 重開（SPEC D-8／Task 1.11）：全部批次一律須宣告答案窗。`/search` 匯出（Task 1.9′）之每列
    #    都攜帶 `lookahead_bars_declared`（逐 tf map），匯入端視之為宣告；使用者匯入路徑之 fixture
    #    因此預設帶上（值＝該列 `window.horizon_bars`，與投影 `max(1, ·)` 自洽）。要測「缺宣告」者
    #    以 `lookahead_bars_declared=None` 覆寫後 `pop`。
    if "lookahead_bars_declared" not in over:
        horizon = int((e.get("label_definition") or {}).get("window", {}).get("horizon_bars", 1))
        e["lookahead_bars_declared"] = {str(e["timeframe"]): horizon}
    elif over["lookahead_bars_declared"] is None:
        e.pop("lookahead_bars_declared", None)
    return e


def valid_batch() -> list:
    return [make_event(0, label=1), make_event(1, label=0)]


def reasons_of(exc: ContractValidationError) -> set:
    return {f["reason"] for f in exc.failures}


def test_valid_batch_passes_and_normalizes():
    df = validate_event_import(valid_batch())
    assert len(df) == 2
    assert df["decision_offset_bars"].tolist() == [0, 0]
    assert all(ld["label_return_mode"] == "close_to_close" for ld in df["label_definition"])


def test_top_level_keyset_equals_contract_enumeration():
    """驗證①：validator 之合法鍵集 == 契約列舉（required ∪ optional ∪ conditional）。"""
    c = load_event_import_contract()
    expected = set(c["required_fields"]) | set(c["optional_fields"]) | set(c["conditional_required"])
    assert allowed_top_level_keys(c) == expected
    # 契約檔本身鍵不重疊
    assert not (set(c["required_fields"]) & set(c["optional_fields"]))


def test_unknown_key_rejected():
    batch = valid_batch()
    batch[0]["decision_at_ms"] = 123  # derived 欄混入匯入檔
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "unknown_field" in reasons_of(ei.value)


def test_missing_required_rejected():
    batch = valid_batch()
    del batch[0]["control_kind"]
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "missing_required_field" in reasons_of(ei.value)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("entry_price_semantic", "open"),
        ("direction", "both"),
        ("scenario", "D"),
        ("control_kind", "user_x"),
        ("counterexample_kind", "d_other"),
        ("kind_source", "guess"),
    ],
)
def test_enum_closed_sets(field, bad):
    """驗證②：枚舉值閉集，集合外值一律拒。"""
    batch = valid_batch()
    batch[0][field] = bad
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "enum_violation" in reasons_of(ei.value)


def test_label_return_mode_enum_and_default():
    batch = valid_batch()
    batch[0]["label_definition"] = dict(batch[0]["label_definition"], label_return_mode="close_to_open")
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "enum_violation" in reasons_of(ei.value)
    # 缺 mode ⇒ 預設 close_to_close（白話閘②：open_to_* 顯式宣告才合法）
    batch2 = valid_batch()
    ld = dict(batch2[0]["label_definition"])
    del ld["label_return_mode"]
    batch2[0]["label_definition"] = ld
    df = validate_event_import(batch2)
    assert df["label_definition"].iloc[0]["label_return_mode"] == "close_to_close"


def test_single_class_missing_control_group():
    """驗證④：二元任務單類別 ⇒ missing_control_group。"""
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import([make_event(0, label=1), make_event(1, label=1)])
    assert "missing_control_group" in reasons_of(ei.value)


def test_ms_magnitude_gate():
    """驗證⑤：t0 量級像秒（<10^12）宣告 ms ⇒ 拒。"""
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import([make_event(0, t0=1704067200), make_event(1, label=0)])
    assert "invalid_timestamp_unit" in reasons_of(ei.value)


def test_digest_tamper_negative_fixture():
    """驗證⑥（W4／§G-4）：source_file_digest 與實際 bytes 不符 ⇒ digest_mismatch。"""
    payload = b"symbol,timestamp,label\nETHUSDT,1704067200000,1\n"
    good = hashlib.sha256(payload).hexdigest()
    batch = [make_event(0, label=1, source_file_digest=good), make_event(1, label=0, source_file_digest=good)]
    assert len(validate_event_import(batch, source_bytes=payload)) == 2
    tampered = copy.deepcopy(batch)
    tampered[0]["source_file_digest"] = "f" * 64  # 篡改
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(tampered, source_bytes=payload)
    assert "digest_mismatch" in reasons_of(ei.value)


def test_direction_single_value_per_batch():
    """驗證⑦（W12／U1）：同批 long＋short 混值 ⇒ 拒。"""
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import([make_event(0, label=1), make_event(1, label=0, direction="short")])
    assert "direction_mixed_in_batch" in reasons_of(ei.value)


def test_platform_random_bars_always_rejected():
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import([make_event(0, control_kind="platform_random_bars"), make_event(1, label=0)])
    assert "not_implemented_platform_random_bars" in reasons_of(ei.value)


def test_unclassifiable_not_importable():
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import([make_event(0, label=0, counterexample_kind="unclassifiable"), make_event(1, label=1)])
    assert "counterexample_kind_not_importable" in reasons_of(ei.value)


def test_empty_import_loud():
    """邊界①：空列表 ⇒ loud 拒。"""
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import([])
    assert "empty_import" in reasons_of(ei.value)


def test_duplicate_event_id_rejected():
    """邊界②。"""
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import([make_event(0, label=1), make_event(0, label=0)])
    assert "duplicate_event_id" in reasons_of(ei.value)


def test_label_value_type_error_but_absent_ok():
    """邊界③：label_value 型別錯拒、缺值容許。"""
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import([make_event(0, label_value="not-a-number"), make_event(1, label=0)])
    assert "label_value_type_error" in reasons_of(ei.value)
    df = validate_event_import([make_event(0, label_value=0.031), make_event(1, label=0)])
    assert df["label_value"].iloc[0] == pytest.approx(0.031)


def test_t9_availability_gate():
    """邊界④（M12 看住）：T9 available_at > decision_at ⇒ research_only 拒；≤ 則收。"""
    sm_ok = {
        "model_id": "m1", "version": "1", "artifact_digest": "d" * 64,
        "split_plan_hash": "e" * 64, "feature_manifest_hash": "f" * 64,
        "available_at": T0 - TF_MS,  # k=1 ⇒ decision_at_nominal = T0 − TF_MS
    }
    ok = [
        make_event(0, event_origin="model", source_model=dict(sm_ok), decision_offset_bars=1),
        make_event(1, label=0),
    ]
    assert len(validate_event_import(ok)) == 2
    bad_sm = dict(sm_ok, available_at=T0 - TF_MS + 1)
    bad = [
        make_event(0, event_origin="model", source_model=bad_sm, decision_offset_bars=1),
        make_event(1, label=0),
    ]
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(bad)
    assert "research_only" in reasons_of(ei.value)


def test_t8_reference_symbols_all_fields_required():
    batch = valid_batch()
    batch[0]["reference_symbols"] = [{"symbol": "BTCUSDT", "timeframe": "12h", "alignment_rule": "", "snapshot_digest": "x" * 64}]
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "conditional_required_missing" in reasons_of(ei.value)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.update(reference_symbols=[{"symbol": 123, "timeframe": "12h", "alignment_rule": "asof", "snapshot_digest": "x" * 64}]),
        lambda e: e.update(event_origin="model", source_model={"model_id": 7, "version": "1", "artifact_digest": "d" * 64,
                                                               "split_plan_hash": "e" * 64, "feature_manifest_hash": "f" * 64,
                                                               "available_at": T0 - TF_MS}, decision_offset_bars=1),
        lambda e: e.update(event_shape="interval", event_interval={"start": "1704067200000", "end": T0 + TF_MS,
                                                                   "endpoints_inclusive": {"start": True, "end": False}}),
        lambda e: e.update(event_shape="interval", event_interval={"start": T0 + TF_MS, "end": T0,
                                                                   "endpoints_inclusive": {"start": True, "end": False}}),
        lambda e: e.update(event_shape="interval", event_interval={"start": T0, "end": T0 + TF_MS, "endpoints_inclusive": [True, False]}),
    ],
)
def test_nested_conditional_types_fail_closed(mutate):
    """CODEX-R1-P1-03：T8/T9/T10 nested 逐欄驗型、禁 coercion（數字當字串／字串當 ms／start≥end／list 當 object 皆拒）。"""
    batch = valid_batch()
    mutate(batch[0])
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert reasons_of(ei.value) & {"type_error"}


def test_t10_interval_trigger():
    batch = valid_batch()
    batch[0]["event_shape"] = "interval"
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "conditional_required_missing" in reasons_of(ei.value)
    batch[0]["event_interval"] = {"start": T0, "end": T0 + TF_MS, "endpoints_inclusive": {"start": True, "end": False}}
    assert len(validate_event_import(batch)) == 2


# ══════════════════════════════════════════════════════════════════════════
# GAP-3 `G3-D2` Task D1.1 — label_origin provenance ／ scenario 深度自洽
#
# 選擇器：`pytest tests/momentum/event_samples/test_import_contract.py -q
#          -k "label_origin or scenario_depth or entry_default"`
# ══════════════════════════════════════════════════════════════════════════

def _pred(scen: str, **over):
    """預測型／兩段式之二元批（label 含 0 與 1）。`over` 逐列覆寫。"""
    return [make_event(i, label=i % 2, scenario=scen, **over) for i in range(2)]


# ── (i) A ＋ 深度全 0 ⇒ scenario_depth_inconsistent ────────────────────────

def test_scenario_depth_inconsistent_when_A_declares_zero_depth():
    """A（事件相對決策為未來）卻宣告深度 0 ⇒ 自相矛盾，拒收。

    🔴 reason 須**恰為** `scenario_depth_inconsistent`，不是「有拒收就算過」——
    reason 字面是下游 UI 與 registry 的判斷依據。
    """
    batch = _pred("A", label_origin="user_csv", lookahead_bars_declared={"12h": 0})
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "scenario_depth_inconsistent" in reasons_of(ei.value)


def test_scenario_depth_inconsistent_applies_to_two_stage_as_well():
    """two_stage 與 A 同組（兩段之較大者仍須 ≥ 1）。"""
    batch = _pred("two_stage", label_origin="user_csv", lookahead_bars_declared={"1h": 0, "12h": 0})
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "scenario_depth_inconsistent" in reasons_of(ei.value)


def test_scenario_depth_ok_when_A_declares_positive_depth():
    """🔴 **over 向對照**：A ＋ 深度 ≥ 1 須**通過**——證明上兩條不是「A 一律拒」。"""
    batch = _pred("A", label_origin="user_csv", lookahead_bars_declared={"12h": 3})
    df = validate_event_import(batch)
    assert len(df) == 2


# ── (ii) B ＋ 深度 0 ⇒ 通過 ────────────────────────────────────────────────

def test_scenario_depth_allows_zero_for_B():
    """B 允許深度 0（裁定①：A 已併入 B，有無用未來根**由深度宣告區分**，不由 scenario 區分）。"""
    df = validate_event_import(_pred("B", label_origin="search_positive_case",
                                     lookahead_bars_declared={"12h": 0}))
    assert len(df) == 2


def test_scenario_depth_rule_skipped_when_declaration_absent():
    """邊界①：`lookahead_bars_declared` **缺欄** ⇒ 本規則不判（reason 留給 D-7 L2 之缺宣告拒收）。

    🔴 這條防的是「搶報 reason」：若本規則對缺宣告也報 `scenario_depth_inconsistent`，
    真正的問題（沒宣告深度）就被蓋掉，使用者會照著錯的 reason 去改。
    """
    df = validate_event_import(_pred("A", label_origin="user_csv"))
    assert len(df) == 2
    # 空 map 同視為「未宣告」
    df2 = validate_event_import(_pred("A", label_origin="user_csv", lookahead_bars_declared={}))
    assert len(df2) == 2


# ── (iii) 預測型缺 label_origin ⇒ conditional_required_missing ─────────────

@pytest.mark.parametrize("scen", ["A", "B", "two_stage"])
def test_label_origin_conditional_required_for_predictive_scenarios(scen):
    """A／B／two_stage 缺 `label_origin` ⇒ `conditional_required_missing`。"""
    batch = _pred(scen, lookahead_bars_declared={"12h": 3})
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "conditional_required_missing" in reasons_of(ei.value)


def test_label_origin_not_required_for_scenario_C_legacy_batches():
    """🔴 **舊批通則**：`scenario == "C"` 且無 `label_origin` ⇒ **通過**（不補值、不拒收）。

    這是 D-001 §N 之通則（不只針對 9/1 那九批）：讀路徑對缺欄回 `null`。
    沒有這條，既有 C 批全部匯不進來。
    """
    df = validate_event_import([make_event(i, label=i % 2, scenario="C") for i in range(2)])
    assert len(df) == 2


# ── (iv) not_importable ⇒ label_origin_not_importable ─────────────────────

def test_label_origin_search_unlabeled_not_importable():
    """`search_unlabeled` 屬契約 `not_importable` ⇒ 專屬 reason（不是 `enum_violation`）。"""
    batch = _pred("B", label_origin="search_unlabeled", lookahead_bars_declared={"12h": 0})
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    rs = reasons_of(ei.value)
    assert "label_origin_not_importable" in rs
    assert "enum_violation" not in rs, "not_importable 之值本身合法，不得同時報 enum_violation"


def test_label_origin_enum_violation_for_unknown_value():
    """枚舉外之值（含空字串，邊界③）⇒ `enum_violation`。"""
    for bad in ("nope", ""):
        batch = _pred("B", label_origin=bad, lookahead_bars_declared={"12h": 0})
        with pytest.raises(ContractValidationError) as ei:
            validate_event_import(batch)
        assert "enum_violation" in reasons_of(ei.value), f"{bad!r} 應為 enum_violation"


def test_label_origin_importable_values_all_accepted():
    """🔴 **over 向**：契約 enum 中**非** not_importable 之值全部須可匯入。

    證明上面兩條不是「label_origin 一律拒」；同時讓日後往 enum 加值時，
    若忘了讓它可匯入，本條會紅。
    """
    from momentum.Analysis.event_samples.import_contract import load_event_import_contract
    spec = load_event_import_contract()["optional_fields"]["label_origin"]
    ok = [v for v in spec["enum"] if v not in spec["not_importable"]]
    assert len(ok) >= 4, "非 not_importable 之值應有四個以上（防 enum 被縮小而本條失去覆蓋）"
    for v in ok:
        df = validate_event_import(_pred("B", label_origin=v, lookahead_bars_declared={"12h": 0}))
        assert len(df) == 2, f"{v!r} 應可匯入"


# ── (v) validator 不讀 entry_price_semantic.default ───────────────────────

def test_entry_default_declared_in_contract_but_not_used_by_validator():
    """契約有 `entry_price_semantic.default`（前端誠實預設之唯一來源），
    但 validator **不得**拿它補缺欄——缺欄仍是 `missing_required_field`。

    🔴 這條同時守兩件事：字面存在（前端讀得到）＋validator 不因此放寬必填。
    """
    from momentum.Analysis.event_samples.import_contract import load_event_import_contract
    node = load_event_import_contract()["required_fields"]["entry_price_semantic"]
    assert node["default"] == "trigger_close"
    assert node["default"] in node["enum"]

    batch = [make_event(i, label=i % 2) for i in range(2)]
    for r in batch:
        r.pop("entry_price_semantic")
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "missing_required_field" in reasons_of(ei.value)


# ── 邊界②：批內 scenario 混值 ⇒ 既有拒收優先，新規則不疊 reason ─────────────

def test_mixed_scenario_batch_does_not_add_new_reasons():
    """混值批之 reason **不得**含本票兩條新規則（Task 1.8／下游之混值拒收先於它們）。

    🔴 沒有這條，混值批會同時報 `conditional_required_missing`，
    使用者會去補 `label_origin` 而真正的問題是「這批不該混」。
    """
    batch = [
        make_event(0, label=1, scenario="A", lookahead_bars_declared={"12h": 0}),
        make_event(1, label=0, scenario="C"),
    ]
    try:
        validate_event_import(batch, enforce_batch_homogeneity=True)
    except ContractValidationError as e:
        rs = reasons_of(e)
        assert "heterogeneous_rows_in_batch" in rs
        assert "conditional_required_missing" not in rs
        assert "scenario_depth_inconsistent" not in rs
    else:
        pytest.fail("混值批須被拒收")


# ══════════════════════════════════════════════════════════════════════════
# B-D1 R2 閉合輪 — 三家 review 命中之缺陷之負向測試
#
# 選擇器：`pytest tests/momentum/event_samples/test_import_contract.py -q -k "r2_closure"`
# ══════════════════════════════════════════════════════════════════════════

def test_r2_closure_label_origin_mixed_batch_rejected():
    """`CODEX-R2-P1-01`／`COMPOSER-R2-P1-01`／`GROK-R2-P2-01`（三家全員命中）：
    批內 `label_origin` **混值** ⇒ `heterogeneous_rows_in_batch`。

    🔴 修正前：混值可落檔，`_single_value` 回 `None`，UI 顯示「（未宣告）」，
    與「舊批從未宣告」**不可區分**——使用者以為沒 provenance，實際是兩種來源混在一起。
    """
    batch = [
        make_event(0, label=1, scenario="B", label_origin="user_csv",
                   lookahead_bars_declared={"12h": 0}),
        make_event(1, label=0, scenario="B", label_origin="platform_generator",
                   lookahead_bars_declared={"12h": 0}),
    ]
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "heterogeneous_rows_in_batch" in reasons_of(ei.value)


def test_r2_closure_label_origin_partial_declaration_rejected():
    """同上之另一半：**部分列有、部分列沒有** ⇒ 亦拒。

    🔴 修正前：`[None, "user_csv"]` 之 `_single_value` 回 `"user_csv"`
    ⇒ **一列的宣告被當成整批的宣告**（codex 實跑 receipt）。
    """
    batch = [
        make_event(0, label=1, scenario="C"),                      # 無 label_origin
        make_event(1, label=0, scenario="C", label_origin="user_csv"),
    ]
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch)
    assert "heterogeneous_rows_in_batch" in reasons_of(ei.value)


def test_r2_closure_label_origin_all_absent_still_accepted():
    """🔴 **over 向**：整批都沒有 `label_origin`（舊批）**仍須通過**。

    沒有這條，上兩條的修正會把所有既有 C 批擋在門外——那不是修好，是弄壞。
    """
    df = validate_event_import([make_event(i, label=i % 2, scenario="C") for i in range(2)])
    assert len(df) == 2


def test_r2_closure_label_origin_uniform_accepted():
    """🔴 **over 向**：整批同一個 `label_origin` 通過（證明不是「有這欄就拒」）。"""
    df = validate_event_import([
        make_event(i, label=i % 2, scenario="B", label_origin="user_csv",
                   lookahead_bars_declared={"12h": 0})
        for i in range(2)
    ])
    assert len(df) == 2


def test_r2_closure_new_rules_apply_when_homogeneity_not_enforced():
    """`COMPOSER-R2-P2-01`／`GROK-R2-P2-02`：`enforce_batch_homogeneity=False` 時，
    混 scenario **不得**成為「掩護」——本票兩條新規則照判。

    🔴 修正前：`_batch_scenario_mixed` 無條件為真即跳過兩條規則，而該旗標**預設 False**
    ⇒ 走預設之 caller 上，混批同時掩護掉 provenance 與深度兩條規則，且混值本身也沒人擋。
    """
    batch = [
        make_event(0, label=1, scenario="A", lookahead_bars_declared={"12h": 0}),  # 缺 label_origin 且深度 0
        make_event(1, label=0, scenario="C", lookahead_bars_declared={"12h": 0}),
    ]
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch, enforce_batch_homogeneity=False)
    rs = reasons_of(ei.value)
    assert "conditional_required_missing" in rs, "缺 label_origin 須被判"
    assert "scenario_depth_inconsistent" in rs, "A＋深度 0 須被判"


def test_r2_closure_mixed_scenario_still_deferred_when_homogeneity_enforced():
    """🔴 **對照（裁定 1 之原意保留）**：旗標為 `True` 時仍讓 Task 1.8 先擋，
    新規則不疊 reason——證明上一條不是把裁定 1 整個推翻。
    """
    batch = [
        make_event(0, label=1, scenario="A", lookahead_bars_declared={"12h": 0}),
        make_event(1, label=0, scenario="C", lookahead_bars_declared={"12h": 0}),
    ]
    with pytest.raises(ContractValidationError) as ei:
        validate_event_import(batch, enforce_batch_homogeneity=True)
    rs = reasons_of(ei.value)
    assert "heterogeneous_rows_in_batch" in rs
    assert "conditional_required_missing" not in rs
    assert "scenario_depth_inconsistent" not in rs
