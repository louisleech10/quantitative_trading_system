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
