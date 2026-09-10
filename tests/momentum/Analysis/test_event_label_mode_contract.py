"""EVTLABEL Task 3.1：匯入標籤模式之枚舉單一真相源＋契約。

SPEC：`docs/EVTLABEL_SPEC.md` Task 3.1　TODO：Task 3.1

## 這批測試在防什麼

`label_source`／`statistic_kind`／removed 鍵這類**字面字串**，過去散落在 JSON、Python 常數、
validator 的 tuple 三個地方。加第三個 label_source 時漏改任何一處都不會拋錯，只會讓
匯入標籤模式的 run **靜默走成全域路徑**（門檻、冗餘分數、隔離全部套錯分支）。
故本檔一律「JSON 對證 Python」，不接受任一端自己手打第二份。

mutation（`handoffs/20260910-evtlabel-mutate.py --phase 3`）：
`M-P3-1`（predicate 改回只認 event_label_value）⇒ `test_predicate_accepts_imported_binary` 紅。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ContractValidationError, EventFilterConfig, ThresholdsConfig
from momentum.Analysis.survivor_contract import _load_label_sources, load_survivor_contract
from momentum.core.contracts import (
    LABEL_KIND_BY_SOURCE,
    LABEL_KIND_EVENT_GIVEN,
    ValidatedBinaryLabel,
    binary_label_digest,
    derive_label_kind,
    is_event_label_consumed,
)

REPO = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPO / "momentum/Analysis/contracts/event_label_mode.json"


@pytest.fixture(scope="module")
def contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════════════════
# 枚舉：JSON 是唯一真相源，Python 端逐一對證
# ══════════════════════════════════════════════════════════════════════════


def test_label_sources_json_matches_python_dispatch_table(contract):
    """`label_sources` ⊆ `LABEL_KIND_BY_SOURCE` 鍵集：JSON 新增來源而 Python 沒接 ⇒ 紅。

    反向也檢查：Python 有而 JSON 沒有 ⇒ 契約檔漏登記，下游讀 JSON 的消費端會拒收合法 payload。
    """
    assert set(contract["label_sources"]) == set(LABEL_KIND_BY_SOURCE)


def test_imported_binary_dispatches_to_event_given(contract):
    """0/1 是產生者逐事件給定 ⇒ 走 event_given 契約（套 forward_return 會因 tail_nans=0 誤判）。"""
    assert "imported_binary_label" in contract["label_sources"]
    assert derive_label_kind("imported_binary_label") == LABEL_KIND_EVENT_GIVEN
    assert LABEL_KIND_BY_SOURCE["imported_binary_label"] == LABEL_KIND_EVENT_GIVEN


def test_unknown_label_source_still_raises():
    """邊界②：未知來源仍 fail-closed（本 Task 只加值，不放寬）。"""
    from momentum.core.contracts import AlignmentViolationError

    with pytest.raises(AlignmentViolationError):
        derive_label_kind("some_new_source")
    with pytest.raises(AlignmentViolationError):
        derive_label_kind(None)


def test_survivor_contract_reads_label_sources_from_json(contract):
    """validator 之允許值集**抄** JSON，不自己手打——兩份字面遲早分歧。"""
    assert set(_load_label_sources()) == set(contract["label_sources"])


def test_statistic_kinds_and_reason_enums_are_closed(contract):
    """枚舉集合本身釘住：少一個值代表某條路徑的揭露字面被偷改。"""
    assert set(contract["statistic_kinds"]) == {
        "spearman_ic",
        "binary_discrimination",
        "binary_discrimination_unavailable",
    }
    assert set(contract["label_mode_reasons"]) == {
        "no_label_column",
        "label_invalid_domain",
        "one_class",
        "class_below_min_selection",
    }
    assert set(contract["label_modes"]) == {"auto", "return_rule", "imported_binary"}
    assert set(contract["binary_status_values"]) == {"ok", "unavailable"}
    assert "binary_status" in contract["summary_columns_binary"]


def test_suppressed_reason_registered_in_survivor_contract(contract):
    """負對照失敗之 reason 必須同時活在兩份契約，否則 `_survivor_reason` 會 KeyError。"""
    pool = load_survivor_contract()["reasons"]["survivor_output"]
    assert set(contract["survivor_suppressed_reasons"]) <= set(pool)


def test_config_defaults_match_contract_single_source(contract):
    """`min_events_per_class` 之預設值只准有一份：config 與契約檔不一致 ⇒ 紅。"""
    assert EventFilterConfig().min_events_per_class == contract["min_events_per_class_default"]
    cfg = EventFilterConfig()
    assert cfg.negative_control_n == 50 and cfg.perm_budget_total == 200000 and cfg.oracle_seed == 20260910
    # 🔴 R1 推翻共用 ic_mean_min：分辨力效應量須**獨立**門檻（見 ThresholdsConfig 註解）
    assert ThresholdsConfig().rank_biserial_min == 0.10
    assert ThresholdsConfig().rank_biserial_min != ThresholdsConfig().ic_mean_min


# ══════════════════════════════════════════════════════════════════════════
# predicate：唯一判準
# ══════════════════════════════════════════════════════════════════════════


def test_predicate_accepts_imported_binary():
    """🔴 本條擋的就是 `M-P3-1`：判準漏掉 binary ⇒ 匯入標籤 run 被當全域路徑跑。"""
    assert is_event_label_consumed({"label_source": "imported_binary_label"}) is True
    assert is_event_label_consumed({"label_source": "event_label_value"}) is True
    assert is_event_label_consumed({"label_source": "mainline_return_N"}) is False
    assert is_event_label_consumed({}) is False
    assert is_event_label_consumed(None) is False


def test_orchestrator_has_no_remaining_private_predicate_callsites():
    """判準集合收斂到 contracts 一處 ⇒ orchestrator 內 `self._is_event_conditional_consumed(` 呼叫點＝0。

    薄包裝本身可留（擋外部殘留呼叫），但內部若還有人走舊路徑，加新來源時就會漏掉那一處。
    """
    src = (REPO / "momentum/Analysis/ic_filter_orchestrator.py").read_text(encoding="utf-8")
    assert src.count("self._is_event_conditional_consumed(") == 0
    assert "is_event_label_consumed" in src


# ══════════════════════════════════════════════════════════════════════════
# digest / dataclass
# ══════════════════════════════════════════════════════════════════════════


def test_binary_digest_is_order_independent_and_collision_safe():
    """digest 供 stage5 對證「還是同一份」⇒ 必須與迭代順序無關，且欄位邊界不可相撞。"""
    a = binary_label_digest([("e2", 20, 1), ("e1", 10, 0)])
    b = binary_label_digest([("e1", 10, 0), ("e2", 20, 1)])
    assert a == b and len(a) == 64
    # 沒有分隔符時 ("a1",2) 與 ("a",12) 會拼成同一字串
    assert binary_label_digest([("a1", 2, 0)]) != binary_label_digest([("a", 12, 0)])
    # 值改了就換指紋（否則 stage5 的對證是裝飾）
    assert binary_label_digest([("e1", 10, 0)]) != binary_label_digest([("e1", 10, 1)])


def test_validated_binary_label_is_frozen_and_carries_rows():
    """R2 D1：`rows_frozenset` 必填——只有 digest 無法定位是**哪幾列**被換掉。"""
    rows = frozenset({("e1", 10, 0), ("e2", 20, 1)})
    v = ValidatedBinaryLabel(
        series=pd.Series([0, 1], index=[10, 20]),
        digest=binary_label_digest(rows),
        rows_frozenset=rows,
        n_pos=1,
        n_neg=1,
    )
    assert v.rows_frozenset == rows and v.n_pos == 1 and v.n_neg == 1
    with pytest.raises(Exception):  # frozen dataclass ⇒ 不可就地改
        v.n_pos = 99  # type: ignore[misc]


# ══════════════════════════════════════════════════════════════════════════
# survivor payload：label_binary 與 label_source 綁定
# ══════════════════════════════════════════════════════════════════════════


def _event_obj(label_source: str, label_binary) -> dict:
    """六鍵齊之事件物件（GAP-3 v2 形狀）。"""
    h = "a" * 64
    return {
        "definition_hash": h,
        "timestamps_hash": h,
        "mode": "timestamps",
        "n_events": 2,
        "n_timestamps_requested": 2,
        "event_manifest_hash": h,
        "label_definition_hash": h,
        "decision_time_rule": "t0",
        "feature_cutoff_rule": "t0-1",
        "label_window_rule": "t0..t0+h",
        "control_kind": "user_labeled_same_trigger",
        "label_source": label_source,
        "statistic_kind": "binary_discrimination",
        "label_binary": label_binary,
    }


def _binary_block(**over) -> dict:
    block = {"import_id": "imp-1", "n_pos": 136, "n_neg": 29, "label_origin_values": [0, 1]}
    block.update(over)
    return block


def test_binary_payload_with_full_label_binary_passes():
    from momentum.Analysis.survivor_contract import _check_event_object

    c = load_survivor_contract()
    _check_event_object(_event_obj("imported_binary_label", _binary_block()), c, "ev")


def test_binary_payload_missing_import_id_raises():
    """四子鍵缺一 ⇒ raise（下游無從得知這批 0/1 來自哪一次匯入）。"""
    from momentum.Analysis.survivor_contract import _check_event_object

    c = load_survivor_contract()
    block = _binary_block()
    del block["import_id"]
    with pytest.raises(ContractValidationError):
        _check_event_object(_event_obj("imported_binary_label", block), c, "ev")


def test_binary_payload_without_label_binary_raises():
    from momentum.Analysis.survivor_contract import _check_event_object

    c = load_survivor_contract()
    with pytest.raises(ContractValidationError):
        _check_event_object(_event_obj("imported_binary_label", None), c, "ev")


def test_return_rule_payload_with_label_binary_raises():
    """🔴 反向綁定：報酬版帶著 `label_binary` 殘值 ⇒ raise。

    模式切回報酬版卻留著上一次的正反例計數，下游會拿它當「這次用了 0/1」的證據。
    """
    from momentum.Analysis.survivor_contract import _check_event_object

    c = load_survivor_contract()
    with pytest.raises(ContractValidationError):
        _check_event_object(_event_obj("event_label_value", _binary_block()), c, "ev")


def test_return_rule_payload_with_null_label_binary_passes():
    """既有 caller 不受影響：`label_binary=null` 之報酬版 payload 照樣通過。"""
    from momentum.Analysis.survivor_contract import _check_event_object

    c = load_survivor_contract()
    _check_event_object(_event_obj("event_label_value", None), c, "ev")


def test_negative_counts_rejected():
    from momentum.Analysis.survivor_contract import _check_event_object

    c = load_survivor_contract()
    with pytest.raises(ContractValidationError):
        _check_event_object(_event_obj("imported_binary_label", _binary_block(n_pos=-1)), c, "ev")


def test_contract_missing_key_fails_closed(tmp_path, monkeypatch):
    """邊界①：契約檔缺 `label_sources` ⇒ raise，不預設回舊值集。"""
    import momentum.Analysis.survivor_contract as sc

    broken = tmp_path / "event_label_mode.json"
    broken.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    monkeypatch.setattr(sc, "_EVENT_LABEL_MODE_CONTRACT", broken)
    with pytest.raises(ContractValidationError):
        sc._load_label_sources()
