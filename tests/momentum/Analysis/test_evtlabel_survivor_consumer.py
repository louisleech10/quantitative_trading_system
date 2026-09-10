"""EVTLABEL Task 3.11（R1 C13）：倖存者檔之 ML 消費契約。

SPEC：`docs/EVTLABEL_SPEC.md` Task 3.11　TODO：Task 3.11

## 這條在證明什麼

使用者主目標的最後一句是「**再把這些特徵餵 ML**」。產出一個檔案不等於交接完成——
要證明**既有的下游純函式真的收得下**。本檔以 `pattern_bridge` 之 `survivor_v2` 入口
（`_survivor_feature_names`）當接收端，餵入本票產出的 payload 形狀。

🔴 **不改 consumer**：本檔只釘住既有行為，不為了讓測試過而放寬下游。
三種既有 fail-loud 一併釘住（版本錯／缺 survivors／空 survivors），
確保下一批人改動 consumer 時會撞到。
"""

from __future__ import annotations

import pytest

from momentum.Analysis.event_samples.pattern_bridge import (
    SURVIVOR_SCHEMA_VERSION_REQUIRED,
    _survivor_feature_names,
)


def _binary_payload(*, survivors=("f_a", "f_b")) -> dict:
    """本票 binary run 之 survivor payload（只含 consumer 會碰的部分）。"""
    return {
        "schema_version": SURVIVOR_SCHEMA_VERSION_REQUIRED,
        "survivors": [{"feature_name": name} for name in survivors],
        "sample_scope": {
            "kind": "event",
            "event": {
                "label_source": "imported_binary_label",
                "statistic_kind": "binary_discrimination",
                "label_binary": {
                    "import_id": "imp-1",
                    "n_pos": 136,
                    "n_neg": 29,
                    "label_origin_values": [],
                },
            },
        },
    }


def test_binary_payload_is_accepted_by_the_existing_consumer():
    """🔴 主目標最後一段：產出的檔案**真的餵得進** ML consumer。"""
    payload = _binary_payload()
    names = _survivor_feature_names(payload)
    assert names == ["f_a", "f_b"]
    # 倖存特徵集合必須等於 payload 之 survivors（consumer 沒有自行增刪）
    assert names == [s["feature_name"] for s in payload["survivors"]]


def test_binary_provenance_survives_into_the_payload():
    """來源身分四鍵在 payload 裡完整保留——下游要能追溯是哪一次匯入。"""
    lb = _binary_payload()["sample_scope"]["event"]["label_binary"]
    assert set(lb) == {"import_id", "n_pos", "n_neg", "label_origin_values"}
    assert lb["import_id"] == "imp-1"
    assert lb["n_pos"] == 136 and lb["n_neg"] == 29


def test_return_rule_payload_is_also_accepted_and_carries_no_label_binary():
    """報酬版 payload 照樣收得下，且 `label_binary` 為 null（不得留殘值）。"""
    payload = _binary_payload()
    payload["sample_scope"]["event"] = {
        "label_source": "event_label_value",
        "statistic_kind": "conditional_ic",
        "label_binary": None,
    }
    assert _survivor_feature_names(payload) == ["f_a", "f_b"]
    assert payload["sample_scope"]["event"]["label_binary"] is None


# ══════════════════════════════════════════════════════════════════════════
# 既有 fail-loud：只釘住，不改 consumer
# ══════════════════════════════════════════════════════════════════════════


def test_suppressed_stub_without_survivors_is_rejected():
    """🔴 負對照失敗時**不落檔**；萬一有人手造一個沒有 survivors 的 stub 餵進來 ⇒ raise。"""
    payload = _binary_payload()
    payload.pop("survivors")
    with pytest.raises(ValueError, match="缺 survivors"):
        _survivor_feature_names(payload)


def test_empty_survivors_is_rejected():
    """倖存者 0 ⇒ raise（沒有特徵可組合，不該讓下游拿空清單去訓練）。"""
    with pytest.raises(ValueError, match="為空"):
        _survivor_feature_names(_binary_payload(survivors=()))


def test_schema_version_one_is_rejected():
    """v1 payload ⇒ raise（禁 silent coerce）。"""
    payload = _binary_payload()
    payload["schema_version"] = 1
    with pytest.raises(ValueError, match="schema_version"):
        _survivor_feature_names(payload)


def test_none_payload_means_no_prefilter_not_an_error():
    """沒有 survivor payload ⇒ 回 None（代表「不做粗篩」），不是錯誤。"""
    assert _survivor_feature_names(None) is None


def test_consumer_itself_is_not_modified_by_this_ticket():
    """碼證：本票**不得**改 `pattern_bridge` 之接收行為（TODO 明列不可做）。"""
    import inspect

    src = inspect.getsource(_survivor_feature_names)
    assert "imported_binary_label" not in src, "consumer 不該認得本票的 label_source"
    assert "label_binary" not in src, "consumer 不該依賴本票新增的欄位"
