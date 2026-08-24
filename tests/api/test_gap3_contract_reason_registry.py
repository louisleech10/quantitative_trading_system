"""GAP-3 UX Task 1.1 — 契約先行之驗收（SPEC L1350–1401 之 ①–⑧）。

驗收字面之唯一來源＝`docs/GAP3_EVENT_UX_SPEC.md` Task 1.1「驗證」欄；本檔只把它機械化，
**不重列 reason 字面**——一律以「對凍結 baseline fixture 之差集」表述
（SPEC R8：計數字面與其所計之物在同一批內被改過兩次，已全面改為差集）。

baseline fixture＝`tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json`
（動工前之位元組拷貝，immutable；runtime loader 不得讀它）。
"""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from momentum.Analysis.event_samples import import_contract
from momentum.Analysis.event_samples.import_contract import (
    ContractValidationError,
    flatten_receipt_schema,
    load_event_import_contract,
    receipt_type_ok,
    validate_receipt_namespace,
)

_REPO = Path(__file__).resolve().parents[2]
_BASELINE = _REPO / "tests" / "momentum" / "event_samples" / "fixtures" / "event_import_contract.pre_gap3.json"

# 動工前之 baseline fixture sha256；與 commit message 所記之值相同（SPEC ⑥）。
_BASELINE_SHA256 = "7111b2d7060eb38e8e35d72dc759f6c2b5f41315dd5d98ec34067e9f118c801c"


@pytest.fixture(scope="module")
def pre() -> dict:
    with open(_BASELINE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def now() -> dict:
    return load_event_import_contract()


# ── ① 新增 reason 之差集集合相等 ────────────────────────────────────────────
def test_gap3_contract_reason_registry_01_import_failure_added(pre: dict, now: dict) -> None:
    added = set(now["import_failure_reasons"]) - set(pre["import_failure_reasons"])
    assert added == {
        "column_mapping_missing",
        "column_not_found_in_file",
        "label_column_not_binary",
        "heterogeneous_rows_in_batch",
    }


# ── ② 既有字面與順序皆不變（不靠計數） ──────────────────────────────────────
def test_gap3_contract_reason_registry_02_existing_prefix_unchanged(pre: dict, now: dict) -> None:
    assert set(pre["import_failure_reasons"]) - set(now["import_failure_reasons"]) == set()
    n = len(pre["import_failure_reasons"])
    assert now["import_failure_reasons"][:n] == pre["import_failure_reasons"]


# ── ③ label_producer_… 不進 import_failure_reasons（§F-2′ 改掛層次） ────────
def test_gap3_contract_reason_registry_03_producer_reason_not_in_import_list(now: dict) -> None:
    assert "label_producer_unsupported_for_declared_semantics" not in now["import_failure_reasons"]


# ── ④ capability_unavailable_reasons 之差集集合相等 ────────────────────────
def test_gap3_contract_reason_registry_04_capability_reasons_added(pre: dict, now: dict) -> None:
    added = set(now["capability_unavailable_reasons"]) - set(pre["capability_unavailable_reasons"])
    assert added == {
        "split_blocked_unverifiable_lookahead",
        "label_producer_unsupported_for_declared_semantics",
    }
    assert set(pre["capability_unavailable_reasons"]) - set(now["capability_unavailable_reasons"]) == set()


# ── ⑤ label_definition.fields 增 filters ───────────────────────────────────
def test_gap3_contract_reason_registry_05_filters_field_registered(now: dict) -> None:
    fields = now["required_fields"]["label_definition"]["fields"]
    assert "filters" in fields
    assert fields["filters"]["type"] == "object"
    assert fields["filters"].get("_doc") or fields["filters"].get("doc")


# ── ⑥ baseline fixture 存在、byte-faithful、且 runtime loader 不讀 tests/ ──
def test_gap3_contract_reason_registry_06_baseline_fixture_byte_faithful() -> None:
    assert _BASELINE.is_file()
    digest = hashlib.sha256(_BASELINE.read_bytes()).hexdigest()
    assert digest == _BASELINE_SHA256

    # runtime loader 之搜尋路徑不得含 tests/（斷言設定值與源碼，不靠註解宣稱）
    assert "tests" not in import_contract._CONTRACT_PATH.parts
    src = inspect.getsource(load_event_import_contract)
    assert "tests" not in src


# ── ⑦ 兩個新登記欄（derived 欄 vs batch receipt 欄，名稱已由 R12 正名） ─────
def test_gap3_contract_reason_registry_07_new_registered_fields(pre: dict, now: dict) -> None:
    assert set(now["derived_fields"]["names"]) - set(pre["derived_fields"]["names"]) == {
        "lookahead_bars_declared"
    }
    assert "analysis_alignment_receipt_hash" not in now["derived_fields"]["names"]
    flat = set(flatten_receipt_schema(now["receipt_schema"]))
    assert {"batch.lookahead_bars_declared", "batch.analysis_alignment_receipt_hash"} <= flat


# ── ⑧(a) 同一 traversal 產生兩側；既有欄名與順序一個不差且排在新欄之前 ─────
def test_gap3_contract_reason_registry_08a_flatten_prefix_preserved(pre: dict, now: dict) -> None:
    pre_names = flatten_receipt_schema(pre["receipt_schema"])
    now_names = flatten_receipt_schema(now["receipt_schema"])
    assert now_names[:len(pre_names)] == pre_names
    assert len(now_names) > len(pre_names)


def test_gap3_contract_reason_registry_08a2_baseline_side_has_independent_oracle(pre: dict) -> None:
    """🔴 CODEX-R3-P2-06：⑧(a) 兩側都由**同一支** `flatten_receipt_schema` 產生。

    共用 traversal 是 SPEC ⑧(e) 要求的（validator 與驗收須同一函式參考），但它有個副作用：
    若 list 分支壞掉（例如回空），`pre_names` 與 `now_names` 會**一起**變形而自我配對，
    baseline 根本沒被驗到（codex 實跑：把 list 分支改回 `[]` 後仍 16 passed）。

    ⇒ 本條為 **baseline 側之獨立 oracle**：不呼叫 `flatten_receipt_schema`，
    直接以 fixture 之原始結構逐鍵展開，再與共用 traversal 之輸出比對。
    兩者不一致即紅——共用 traversal 壞掉時，本條會抓到。
    """
    schema = pre["receipt_schema"]
    independent = []
    for ns, fields in schema.items():
        assert isinstance(fields, list), f"baseline 之 {ns} 應為欄名 list（改前形態）"
        for name in fields:
            independent.append(f"{ns}.{name}")

    assert independent == flatten_receipt_schema(schema)
    assert len(independent) > 0  # 防「兩邊都空也算相等」
    # 幾個 baseline 欄名之字面錨點（改前語意；fixture 被動過即紅）
    assert independent[0] == "event_level.event_id"
    assert "per_tf.row_id" in independent
    assert not any(n.startswith("batch.") for n in independent)


# ── ⑧(b) 每個 namespace 為 {欄名: 型別}（非 list）；batch 兩欄之型別字面 ────
def test_gap3_contract_reason_registry_08b_namespaces_are_typed_dicts(now: dict) -> None:
    schema = now["receipt_schema"]
    for ns, fields in schema.items():
        assert isinstance(fields, dict), f"receipt_schema['{ns}'] 仍是 list（migration 未完成）"
        assert all(isinstance(v, str) for v in fields.values())
    assert schema["batch"]["lookahead_bars_declared"] == "Mapping[str,int>=0]"
    assert schema["batch"]["analysis_alignment_receipt_hash"] == "str"


# ── ⑧(c) runtime validator 真的擋得住：五個反例各自 fail-closed ────────────
@pytest.mark.parametrize(
    "bad_value",
    [
        {"1h": -1},      # map 內負數
        {"1h": 1.5},     # map 內非 int
        72,              # root scalar（R9 形態）——「是個整數」不得放行
        {"1h": "3"},     # map 內字串
        {"1h": True},    # bool ⊂ int（R17）——type(v) is int 才擋得住
    ],
    ids=["neg", "float", "root_scalar", "str", "bool"],
)
def test_gap3_contract_reason_registry_08c_validator_rejects(now: dict, bad_value) -> None:
    with pytest.raises(ContractValidationError) as ei:
        validate_receipt_namespace(
            "batch",
            {"lookahead_bars_declared": bad_value, "analysis_alignment_receipt_hash": "deadbeef"},
            contract=now,
        )
    # 🔴 不得只驗「有 raise」——那對「整個 namespace 不存在」這種壞法也會綠（假綠）。
    #    須逐字命中該欄位與該 reason。
    assert {"field": "batch.lookahead_bars_declared", "reason": "type_error"} in [
        {"field": f["field"], "reason": f["reason"]} for f in ei.value.failures
    ]


# ── ⑧(d) 正例對照（防「恆紅型假保證」） ────────────────────────────────────
def test_gap3_contract_reason_registry_08d_validator_accepts_valid(now: dict) -> None:
    validate_receipt_namespace(
        "batch",
        {"lookahead_bars_declared": {"1h": 0, "12h": 6}, "analysis_alignment_receipt_hash": "deadbeef"},
        contract=now,
    )


# ── ⑧(e) validator 與驗收呼叫同一 exported traversal／型別判定函式 ─────────
def test_gap3_contract_reason_registry_08e_same_function_reference() -> None:
    g = validate_receipt_namespace.__globals__
    assert g["receipt_type_ok"] is receipt_type_ok
    assert import_contract.flatten_receipt_schema is flatten_receipt_schema
    # 型別判定之唯一入口：未知型別字面 fail-closed，不得靜默放行
    with pytest.raises(ValueError):
        receipt_type_ok("NoSuchType", 1)
