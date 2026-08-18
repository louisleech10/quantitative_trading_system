"""GAP-2b 倖存者契約測試（Task 1.0 loader：全部 test 名含 ``load``，供 B1 gate ``-k load``）。

Task 3.1 之 resolver／validator／build 測試於 B3 加入本檔（名稱不含 ``load``）。
契約鍵名一律由 ``load_survivor_contract()`` 讀出，本檔不複列鍵表（只在頂層鍵集斷言 ① 逐字比對，
與 ``survivor_contract.SURVIVOR_CONTRACT_TOP_KEYS`` 雙鎖）。
"""
from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import pytest

from momentum.Analysis import survivor_contract as sc
from momentum.Analysis.ic_config_schema import ContractValidationError, contract_enum

REPO_ROOT = Path(__file__).resolve().parents[3]

_ALLOWED_TYPES = {"str", "int", "float", "bool", "list", "object", "null"}


def _iter_key_schemas(contract: dict):
    """遍歷所有 ``*_keys`` 物件層（含 marginal_ic_section_keys 之子層），yield (label, schema_obj)。"""
    for name, value in contract.items():
        if not name.endswith("_keys"):
            continue
        if name == "marginal_ic_section_keys":
            for sub, obj in value.items():
                if sub == "_doc":
                    continue
                yield f"{name}.{sub}", obj
        else:
            yield name, value


# ---------------------------------------------------------------- ① 頂層鍵集 exact
def test_load_top_level_keys_exact():
    contract = sc.load_survivor_contract()
    expected = {
        "version", "_doc", "capability_status_ref", "reasons", "algorithm_version",
        "survivor_file_keys", "sample_scope_keys", "sample_scope_kind_values",
        "event_definition_keys", "event_identity_keys", "split_keys", "row_identity_keys",
        "provenance_keys", "survivor_record_keys", "marginal_ic_section_keys",
        "statistic_values", "projection_space_values", "weights_method_values",
        "view_values", "fit_scope_values", "selection_sample_values",
        "oos_semantics_values", "independent_oos_validation_allowed",
        "survivor_output_status_keys",
    }
    assert set(contract.keys()) == expected
    assert sc.SURVIVOR_CONTRACT_TOP_KEYS == frozenset(expected)
    assert contract["version"] == 1


# ---------------------------------------------------------------- ② capability_status_ref
def test_load_capability_status_ref_matches_report_contract():
    contract = sc.load_survivor_contract()
    ref = contract["capability_status_ref"]
    rel_path, key = ref.split("#", 1)
    with (REPO_ROOT / rel_path).open("r", encoding="utf-8") as file:
        report_contract = json.load(file)
    assert frozenset(report_contract[key]) == contract_enum("capability_status")


# ---------------------------------------------------------------- ③ ④ 值集硬約束
def test_load_independent_oos_validation_allowed_is_false_only():
    contract = sc.load_survivor_contract()
    assert contract["independent_oos_validation_allowed"] == [False]


def test_load_oos_semantics_single_value_and_reasons_nonempty():
    contract = sc.load_survivor_contract()
    assert len(contract["oos_semantics_values"]) == 1
    reasons = contract["reasons"]
    assert set(reasons.keys()) == {"marginal_ic", "marginal_ic_feature", "survivor_output"}
    for group, values in reasons.items():
        assert isinstance(values, list) and values, group
        assert len(set(values)) == len(values), f"duplicate reason in {group}"
    assert contract["algorithm_version"]
    assert contract["statistic_values"] and contract["projection_space_values"]
    assert set(contract["fit_scope_values"]) == {"train", "full_sample"}


# ---------------------------------------------------------------- ⑤ 每 *_keys 之鍵皆帶 type/required
def test_load_every_keys_schema_has_type_required_nullable():
    contract = sc.load_survivor_contract()
    seen = 0
    for label, obj in _iter_key_schemas(contract):
        assert obj.get("additional_properties") is False, label
        keys = obj["keys"]
        assert isinstance(keys, dict) and keys, label
        for key, spec in keys.items():
            assert set(spec.keys()) == {"type", "required", "nullable"}, f"{label}.{key}"
            assert spec["type"] in _ALLOWED_TYPES, f"{label}.{key}"
            assert isinstance(spec["required"], bool), f"{label}.{key}"
            assert isinstance(spec["nullable"], bool), f"{label}.{key}"
            seen += 1
    assert seen > 50
    # survivor_output 五鍵＋nullable 清單與 keys 一致
    so = contract["survivor_output_status_keys"]
    assert set(so["keys"].keys()) == {"status", "reason", "path", "sha256", "case_id"}
    assert set(so["nullable"]) == {k for k, s in so["keys"].items() if s["nullable"]}


# ---------------------------------------------------------------- ⑥ kind_values ⊆ RowMaskPlan.source Literal（AST）
def _row_mask_plan_source_literal_values() -> set:
    src = (REPO_ROOT / "momentum" / "core" / "contracts.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "RowMaskPlan":
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and getattr(stmt.target, "id", None) == "source":
                    ann = stmt.annotation
                    assert isinstance(ann, ast.Subscript), "RowMaskPlan.source annotation is not Literal[...]"
                    inner = ann.slice
                    elts = inner.elts if isinstance(inner, ast.Tuple) else [inner]
                    values = set()
                    for elt in elts:
                        assert isinstance(elt, ast.Constant), "Literal 值須為常數"
                        values.add(elt.value)
                    return values
    raise AssertionError("RowMaskPlan.source not found via AST")


def test_load_sample_scope_kind_values_subset_of_row_mask_plan_source():
    contract = sc.load_survivor_contract()
    literal_values = _row_mask_plan_source_literal_values()
    assert literal_values, "AST 未解析出任何 Literal 值"
    assert set(contract["sample_scope_kind_values"]) <= literal_values
    assert set(contract["sample_scope_kind_values"]) == {"full", "event"}


# ---------------------------------------------------------------- 邊界：檔缺／JSON 壞／多鍵／allowed≠[false]
def test_load_missing_file_raises(tmp_path):
    with pytest.raises(ContractValidationError):
        sc.load_survivor_contract(tmp_path / "nope.json")


def test_load_broken_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ContractValidationError):
        sc.load_survivor_contract(bad)


def test_load_extra_top_key_raises(tmp_path):
    copy = tmp_path / "extra.json"
    data = json.loads(sc.SURVIVOR_CONTRACT_PATH.read_text(encoding="utf-8"))
    data["reasons_ref"] = "x"
    copy.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractValidationError):
        sc.load_survivor_contract(copy)


def test_load_allowed_not_false_raises(tmp_path):
    copy = tmp_path / "allowed.json"
    data = json.loads(sc.SURVIVOR_CONTRACT_PATH.read_text(encoding="utf-8"))
    data["independent_oos_validation_allowed"] = [False, True]
    copy.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractValidationError):
        sc.load_survivor_contract(copy)


# ---------------------------------------------------------------- ⑦ tamper 探針（同時是 mutation probe）
def test_mutation_missing_top_key_raises(tmp_path):
    """tmp 複本刪一頂層鍵 ⇒ loader 必 raise（改壞 loader 之鍵集檢查 ⇒ 本測試紅）。

    自證基線：未刪鍵之複本可載入（綠）；刪 ``sample_scope_kind_values`` 後 raise（紅）。
    """
    copy = tmp_path / "ic_survivor_contract.json"
    shutil.copy(sc.SURVIVOR_CONTRACT_PATH, copy)
    assert sc.load_survivor_contract(copy)["version"] == 1  # 基線綠
    data = json.loads(copy.read_text(encoding="utf-8"))
    del data["sample_scope_kind_values"]
    copy.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractValidationError):
        sc.load_survivor_contract(copy)
