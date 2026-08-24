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
    assert contract["version"] == 2  # GAP-3 Task B2.4 升版（v1→v2：event 物件擴六鍵）


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
    assert sc.load_survivor_contract(copy)["version"] == 2  # 基線綠
    data = json.loads(copy.read_text(encoding="utf-8"))
    del data["sample_scope_kind_values"]
    copy.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContractValidationError):
        sc.load_survivor_contract(copy)


# ---------------------------------------------------------------- A1-7 K1：回傳副本，caller 改寫不外洩
def test_load_returns_copy_not_shared_singleton():
    a = sc.load_survivor_contract()
    a["version"] = 999
    a["reasons"]["marginal_ic"].append("tampered")
    b = sc.load_survivor_contract()
    assert b["version"] == 2
    assert "tampered" not in b["reasons"]["marginal_ic"]
    assert a is not b


# ============================================================================
# Task 3.1 — resolver／event identity／validator／build_survivor_output（B3；名稱不含 load）
# ============================================================================
import copy as _copy
import hashlib as _hashlib
from types import SimpleNamespace as _NS

import numpy as _np
import pandas as _pd

from momentum.Analysis.factor_combiner import combine_factors as _combine
from momentum.Analysis.marginal_ic import MarginalICParams as _P, compute_marginal_ic as _cmi
from momentum.core.contracts import canonical_idx_hash as _cih


def _o2():
    rng = _np.random.default_rng(20260803)
    n = 5000
    s1, s2, f = rng.standard_normal(n), rng.standard_normal(n), rng.standard_normal(n)
    eps = rng.normal(0.0, 0.812, n)
    y = 0.3 * s1 + 0.3 * s2 + 0.4 * f + eps
    df = _pd.DataFrame({"s1": s1, "s2": s2, "f": f, "z": rng.standard_normal(n)})
    tr = _np.zeros(n, dtype=bool)
    tr[:3000] = True
    return df, _pd.Series(y), tr, ~tr


def _build_kwargs(*, event=None, fallback=False, root="ok_oos", extra=("z",)):
    df, y, tr, te = _o2()
    p = _P(n_bootstrap=10, block_len=5)
    surv = ["s1", "s2", "f"]
    marg = _cmi(df, y, train_mask=tr, test_mask=te, survivors=surv, extra_candidates=list(extra), params=p, fit_scope="train")
    comp = _combine(df, y, train_mask=tr, test_mask=te, survivors=surv, params=p, fit_scope="train")
    idx = _np.arange(len(df))
    train_plan = _NS(row_index=idx[tr], time_bounds=("2024-01-01", "2024-06-30"), embargo=2, purge_gap=3, base_universe_hash="u" * 8)
    test_plan = _NS(row_index=idx[te], time_bounds=("2024-07-01", "2024-12-31"), embargo=2, purge_gap=3, base_universe_hash="u" * 8)
    report_meta = {
        "symbol": "ETHUSDT", "timeframe": "12h", "n_samples": len(df),
        "event_filter": ({"fallback": True} if fallback else {"applied": True}) if event is not None else None,
        "ic_train_test_split": {"applied": True}, "split_method": "holdout",
        "selection_scope": {"scope_id": "scope-1"},
    }
    ev = sc.compute_event_identity(None, None) if event is None else event
    return dict(
        report_meta=report_meta, filtered_features=surv, marginal_ic_result=marg, composite_result=comp,
        summary_by_feature={n: {"ic_mean": 0.1, "icir": 1.2, "p_value_adj": 0.01, "pass_class": "oos"} for n in surv},
        root_analysis_status=root, event_identity=ev,
        split_context={"train_plan": train_plan, "test_plan": test_plan}, config_hash="c" * 8, features_source_hash="f" * 64,
        features_path="/tmp/x.h5", labels_content_hash="l" * 64, symbol="ETHUSDT", timeframe="12h", case_id="ic_gatekeeper",
        generated_at="2026-08-19T00:00:00Z", fit_mode="train", pit_stats_version="v1", ic_method="spearman",
        label_horizon=12, label_return_type="log", report_ref="ic_report_ic_gatekeeper.json",
    ), test_plan


def test_roundtrip_build_then_validate():  # ①
    kw, test_plan = _build_kwargs()
    payload = sc.build_survivor_output(**kw)
    sc.validate_survivor_output(payload, report_meta=kw["report_meta"], report_ref_path="/x/ic_report_ic_gatekeeper.json")
    assert payload["feature_names"] == ["s1", "s2", "f"]
    assert payload["sample_scope"]["kind"] == "full" and payload["sample_scope"]["event"] is None
    assert payload["split"]["row_identity"]["test_index_hash"] == _cih(test_plan.row_index)  # ⑬（合成 plan）
    assert payload["survivors"][2]["marginal_ic_loo"] is not None and payload["survivors"][2]["redundancy_kept"] is True
    assert payload["composite"]["method"] == "equal" and set(payload["removed_candidates"]) == {"z"}
    assert payload["status"] == "ok" and payload["reason"] is None
    assert payload["independent_oos_validation"] is False and payload["pass_class"] == "oos"
    # 空 survivors 亦可組裝
    kw2 = dict(kw); kw2["filtered_features"] = []; kw2["marginal_ic_result"] = None; kw2["composite_result"] = None
    empty = sc.build_survivor_output(**kw2)
    sc.validate_survivor_output(empty)
    assert (empty["status"], empty["reason"]) == ("not_applicable", "no_survivors") and empty["survivors"] == []


def _valid_payload():
    kw, _ = _build_kwargs()
    return sc.build_survivor_output(**kw), kw


@pytest.mark.parametrize("path", [("schema_version",), ("sample_scope",), ("provenance", "config_hash"), ("split", "row_identity", "train_index_hash"), ("survivors", 0, "feature_name")])
def test_missing_required_key_raises(path):  # ②
    payload, _ = _valid_payload()
    node = payload
    for p in path[:-1]:
        node = node[p]
    del node[path[-1]]
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(payload)


@pytest.mark.parametrize("path", [(), ("sample_scope",), ("split",), ("provenance",), ("composite",), ("survivors", 0), ("split", "row_identity"), ("removed_candidates", "z"), ("composite", "weights_dummy_parent")])
def test_unknown_key_raises(path):  # ③ ⑩（含 nested composite／removed_candidates tamper）
    if path == ("composite", "weights_dummy_parent"):
        payload, _ = _valid_payload()
        payload["composite"]["__extra__"] = 1  # composite 物件層加鍵
        with pytest.raises(ContractValidationError):
            sc.validate_survivor_output(payload)
        return
    payload, _ = _valid_payload()
    node = payload
    for p in path:
        node = node[p]
    node["__extra__"] = 1
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(payload)


def test_kind_enum_and_event_null_raise():  # ④ ⑤
    payload, _ = _valid_payload()
    bad = _copy.deepcopy(payload); bad["sample_scope"]["kind"] = "panel"
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(bad)
    bad2 = _copy.deepcopy(payload); bad2["sample_scope"]["kind"] = "event"; bad2["sample_scope"]["event"] = None
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(bad2)


def test_oos_four_field_consistency():  # ⑥ ⑪ ⑯ ⑰
    payload, _ = _valid_payload()
    b = _copy.deepcopy(payload); b["analysis_status"] = "degraded_full_sample"  # oos 仍 True
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["oos_guarantees"] = False  # ok_oos + False
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["pass_class"] = "full_sample_research_only"
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["independent_oos_validation"] = True
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["oos_semantics"] = "independent_oos"
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["analysis_status"] = "research_only"
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    # degraded 組合合法
    kw, _ = _build_kwargs(root="degraded_full_sample")
    d = sc.build_survivor_output(**kw)
    sc.validate_survivor_output(d)
    assert (d["oos_guarantees"], d["pass_class"]) == (False, "full_sample_research_only")


def test_resolve_ref_and_capability_status():  # ⑧
    c = sc.load_survivor_contract()
    assert frozenset(sc.resolve_ref(c["capability_status_ref"])) == contract_enum("capability_status")
    with pytest.raises(ContractValidationError):
        sc.resolve_ref("momentum/Analysis/contracts/nope.json#capability_status")
    with pytest.raises(ContractValidationError):
        sc.resolve_ref("momentum/Analysis/contracts/ic_report_contract.json#no_such_key")
    with pytest.raises(ContractValidationError):
        sc.resolve_ref("momentum/Analysis/contracts/ic_report_contract.json#reasons")  # dict 非 list
    with pytest.raises(ContractValidationError):
        sc.resolve_ref("garbage")


def test_section_key_sets_match_dataclasses():  # ⑨
    payload, kw = _valid_payload()
    c = sc.load_survivor_contract()["marginal_ic_section_keys"]
    assert set(kw["marginal_ic_result"].to_dict().keys()) == set(c["section_keys"]["keys"])
    assert set(kw["composite_result"].to_dict().keys()) == set(c["composite_keys"]["keys"])
    for e in kw["marginal_ic_result"].to_dict()["sequential"]:
        assert set(e.keys()) == set(c["sequential_keys"]["keys"])


def test_feature_set_hash_and_survivor_sequence():  # ⑫
    payload, _ = _valid_payload()
    b = _copy.deepcopy(payload); b["feature_set_hash"] = "0" * 64
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["survivors"][0], b["survivors"][1] = b["survivors"][1], b["survivors"][0]
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    assert payload["feature_set_hash"] == _hashlib.sha256(json.dumps(payload["feature_names"], separators=(",", ":")).encode()).hexdigest()


def test_checklist_subset_of_contract_keys():  # ⑭
    c = sc.load_survivor_contract()
    checklist = {
        "survivor_file_keys": ["symbol", "timeframe", "case_id", "sample_scope", "provenance", "split", "feature_names", "feature_set_hash", "survivors", "composite",
                               "analysis_status", "oos_guarantees", "pass_class", "independent_oos_validation", "selection_sample", "oos_semantics", "statistic"],
        "sample_scope_keys": ["kind", "event", "n_samples_total", "n_samples_test", "degraded"],
        "event_definition_keys": ["definition_hash", "timestamps_hash", "mode", "n_events", "n_timestamps_requested"],
        "provenance_keys": ["config_hash", "features_source_hash", "labels_content_hash", "features_path", "pit_stats_version", "fit_mode", "ic_method", "label_horizon", "label_return_type", "report_ref", "producer", "contract_version", "algorithm_version"],
        "split_keys": ["split_method", "train_time_bounds", "test_time_bounds", "train_rows", "test_rows", "embargo", "purge_gap", "base_universe_hash", "selection_scope_id", "row_identity"],
        "row_identity_keys": ["train_index_hash", "test_index_hash"],
        "survivor_record_keys": ["feature_name", "ic_mean", "icir", "p_value_adj", "pass_class", "train_ic", "gross_ic", "marginal_ic_loo", "marginal_ic_loo_ci95", "marginal_ic_train_insample", "redundancy_kept"],
    }
    for schema_name, items in checklist.items():
        assert set(items) <= set(c[schema_name]["keys"].keys()), schema_name
    # R18 CODEX-R18-P1-07：nested composite／removed_candidate 義務項（SPEC L179「composite＝B2 結果去序列」／removed_candidates）
    nested = {
        "composite_keys": ["method", "weights", "signs", "composite_ic", "composite_ic_train_insample", "top_train_single", "top_train_single_test_ic", "delta_vs_top_train_single", "delta_ci95", "fit_scope", "oos_guarantees"],
        "removed_candidate_keys": ["status", "reason", "conditioning_set", "marginal_ic", "gross_ic", "ci95"],
        "view_status_keys": ["status", "reason"],
    }
    sec = c["marginal_ic_section_keys"]
    for schema_name, items in nested.items():
        assert set(items) <= set(sec[schema_name]["keys"].keys()), schema_name


def test_identity_three_fields():  # ⑮
    payload, kw = _valid_payload()
    meta = kw["report_meta"]
    # 三欄由參數帶入（非寫死）：換值重組後 payload 必反映（V-19 三 case 之 oracle）
    kw_b = dict(kw); kw_b.update(symbol="BTCUSDT", timeframe="1h", case_id="alt_case", report_ref="ic_report_alt_case.json")
    kw_b["report_meta"] = {**meta, "symbol": "BTCUSDT", "timeframe": "1h"}
    pb = sc.build_survivor_output(**kw_b)
    assert (pb["symbol"], pb["timeframe"], pb["case_id"]) == ("BTCUSDT", "1h", "alt_case")
    sc.validate_survivor_output(pb, report_meta=kw_b["report_meta"], report_ref_path="/r/ic_report_alt_case.json")
    sc.validate_survivor_output(payload, report_meta=meta, report_ref_path="/r/ic_report_ic_gatekeeper.json")  # 正常
    # symbol 篡改／缺失
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(payload, report_meta={**meta, "symbol": "BTCUSDT"})
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(payload, report_meta={k: v for k, v in meta.items() if k != "symbol"})
    # timeframe 篡改／缺失
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(payload, report_meta={**meta, "timeframe": "1h"})
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(payload, report_meta={**meta, "timeframe": None})
    # case_id vs report_ref_path 檔名段
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(payload, report_ref_path="/r/ic_report_other.json")
    b = _copy.deepcopy(payload); b["provenance"]["report_ref"] = "ic_report_other.json"
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["case_id"] = "other"
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b, report_ref_path="/r/ic_report_ic_gatekeeper.json")


def test_event_identity_serialization():  # ⑱
    ts_a = ["2024-01-03T00:00:00Z", "2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z", "2024-01-01T00:00:00Z"]
    ts_b = ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z", "2024-01-03T00:00:00Z"]
    a = sc.compute_event_identity(None, ts_a)
    b = sc.compute_event_identity(None, ts_b)
    assert a["mode"] == "timestamps" and a["timestamps_hash"] == b["timestamps_hash"] == a["definition_hash"]
    assert a["n_events"] == 3 and a["n_timestamps_requested"] == 4 and b["n_timestamps_requested"] == 3
    # 數值 epoch（ms 與 s 自動判別）與字串同值
    ms = [1704067200000, 1704153600000, 1704240000000]
    s = [1704067200, 1704153600, 1704240000]
    assert sc.compute_event_identity(None, ms)["timestamps_hash"] == b["timestamps_hash"]
    assert sc.compute_event_identity(None, s)["timestamps_hash"] == b["timestamps_hash"]
    q = sc.compute_event_identity("  SELECT * FROM events  ", None)
    assert q["mode"] == "query" and q["timestamps_hash"] is None and q["definition_hash"] == _hashlib.sha256(b"SELECT * FROM events").hexdigest()
    assert q["n_events"] is None
    none = sc.compute_event_identity("", [])
    assert none == {"mode": "none", "definition_hash": None, "timestamps_hash": None, "n_events": None, "n_timestamps_requested": None}
    # 事件模式與 fallback 之 sample_scope
    kw, _ = _build_kwargs(event=b)
    p_ev = sc.build_survivor_output(**kw)
    sc.validate_survivor_output(p_ev)
    assert p_ev["sample_scope"]["kind"] == "event" and p_ev["sample_scope"]["event"]["definition_hash"] == b["definition_hash"]
    kw2, _ = _build_kwargs(event=b, fallback=True, root="degraded_full_sample")
    p_fb = sc.build_survivor_output(**kw2)
    sc.validate_survivor_output(p_fb)
    assert p_fb["sample_scope"]["kind"] == "full" and p_fb["sample_scope"]["degraded"] is True


def test_view_status_object_composite_and_type_checks():
    payload, _ = _valid_payload()
    b = _copy.deepcopy(payload); b["composite"] = {"status": "disabled", "reason": "disabled_by_config"}
    sc.validate_survivor_output(b)
    b["composite"] = {"status": "disabled", "reason": "disabled_by_config", "x": 1}
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["split"]["train_rows"] = "3000"
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["oos_guarantees"] = 1  # bool 欄不得為 int
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(payload); b["survivors"][0]["ic_mean"] = float("nan")
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)


def test_mutation_validator_skips_feature_set_hash(monkeypatch):
    """探針：validator 若略過 feature_set_hash 重算 ⇒ ⑫ 篡改案例不再 raise ⇒ 紅。"""
    payload, _ = _valid_payload()
    b = _copy.deepcopy(payload); b["feature_set_hash"] = "0" * 64
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)  # 基線：會 raise
    monkeypatch.setattr(sc, "feature_set_hash", lambda names: b["feature_set_hash"])  # mutant：重算被繞過（恆等於 payload 值）
    try:
        sc.validate_survivor_output(b)
        mutant_raised = False
    except ContractValidationError:
        mutant_raised = True
    with pytest.raises(AssertionError):
        assert mutant_raised, "oracle ⑫ 於 mutant 下應失效（篡改 hash 未被抓）"


# ---------------------------------------------------------------- R18 修補（CODEX-R18-P0-01／P1-02..06／P2-08）
def test_provenance_fit_mode_raw_orchestrator_values_accepted():
    """P0-01：provenance.fit_mode 為 orchestrator 前處理 fit_mode 原值（train_mask／pit_expanding／full_sample），不映射、不受 fit_scope 枚舉限制。"""
    for fm in ("train_mask", "pit_expanding", "full_sample"):
        kw, _ = _build_kwargs()
        kw["fit_mode"] = fm
        p = sc.build_survivor_output(**kw)
        sc.validate_survivor_output(p)
        assert p["provenance"]["fit_mode"] == fm
    b, _ = _valid_payload(); b["provenance"]["fit_mode"] = "  "
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)


def test_resolve_ref_rejects_escape(tmp_path):
    """P1-02：絕對路徑／`..`／逃出 repo root 一律 raise。"""
    outside = tmp_path / "o.json"
    outside.write_text(json.dumps({"k": [1]}), encoding="utf-8")
    with pytest.raises(ContractValidationError):
        sc.resolve_ref(f"{outside}#k")
    with pytest.raises(ContractValidationError):
        sc.resolve_ref("../etc/passwd#k")
    with pytest.raises(ContractValidationError):
        sc.resolve_ref("momentum/../../outside.json#k")


def test_event_object_mode_invariants():
    """P1-03：mode=timestamps 缺 hash／計數、query 帶 timestamps_hash、none 帶 hash ⇒ raise。"""
    ident = sc.compute_event_identity(None, ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"])
    kw, _ = _build_kwargs(event=ident)
    p = sc.build_survivor_output(**kw)
    sc.validate_survivor_output(p)
    b = _copy.deepcopy(p); b["sample_scope"]["event"].update({"definition_hash": None, "timestamps_hash": None, "n_events": None, "n_timestamps_requested": None})
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(p); b["sample_scope"]["event"]["timestamps_hash"] = "0" * 64
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(p); b["sample_scope"]["event"]["n_timestamps_requested"] = 1
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(p); b["sample_scope"]["event"].update({"mode": "query"})
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    b = _copy.deepcopy(p); b["sample_scope"]["event"].update({"mode": "none"})
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(b)
    q = sc.compute_event_identity("q", None)
    kwq, _ = _build_kwargs(event=q)
    pq = sc.build_survivor_output(**kwq)
    sc.validate_survivor_output(pq)
    assert pq["sample_scope"]["kind"] == "event"


def test_fallback_requires_full_index_and_uses_real_index():
    """P1-04：無 split 時 full_index 必傳（缺 ⇒ raise）；row_identity 用真實 index（timestamp index 與 arange 不同）。"""
    kw, _ = _build_kwargs()
    kw["split_context"] = None
    kw["root_analysis_status"] = "degraded_full_sample"
    with pytest.raises(ContractValidationError):
        sc.build_survivor_output(**kw)
    idx = _pd.date_range("2024-01-01", periods=5000, freq="12h")
    kw["split_context"] = {"full_index": idx}
    p = sc.build_survivor_output(**kw)
    sc.validate_survivor_output(p)
    assert p["split"]["row_identity"]["train_index_hash"] == _cih(idx) != _cih(_np.arange(5000))
    assert p["split"]["train_rows"] == p["split"]["test_rows"] == 5000


def test_unknown_root_status_raises():
    """P1-05：未知 root status fail-closed。"""
    kw, _ = _build_kwargs(root="research_only")
    with pytest.raises(ContractValidationError):
        sc.build_survivor_output(**kw)


def test_n_samples_total_reconciliation():
    """P1-06：n_samples_total 須 ≥ marginal／split 列數和；marginal n_test 與 split test_rows exact；非正整數 raise。"""
    kw, _ = _build_kwargs()
    kw["report_meta"] = {**kw["report_meta"], "n_samples": 1}
    with pytest.raises(ContractValidationError):
        sc.build_survivor_output(**kw)
    kw["report_meta"] = {**kw["report_meta"], "n_samples": 0}
    with pytest.raises(ContractValidationError):
        sc.build_survivor_output(**kw)
    kw2, test_plan = _build_kwargs()
    kw2["report_meta"] = {**kw2["report_meta"], "n_samples": 6000}  # purge/embargo 情境：total > train+test 合法
    p = sc.build_survivor_output(**kw2)
    assert p["sample_scope"]["n_samples_total"] == 6000 and p["sample_scope"]["n_samples_test"] == 2000
    kw3, _ = _build_kwargs()
    kw3["split_context"]["test_plan"] = _NS(**{**vars(kw3["split_context"]["test_plan"]), "row_index": _np.arange(10)})
    with pytest.raises(ContractValidationError):
        sc.build_survivor_output(**kw3)


def test_event_identity_naive_string_matches_aware():
    """P2-08：naive 字串與 aware／ms／s 同 hash。"""
    aware = sc.compute_event_identity(None, ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"])
    naive = sc.compute_event_identity(None, ["2024-01-01 00:00:00", "2024-01-02 00:00:00"])
    ms = sc.compute_event_identity(None, [1704067200000, 1704153600000])
    assert aware["timestamps_hash"] == naive["timestamps_hash"] == ms["timestamps_hash"]


# ============================================================================
# GAP-3 Task B2.4：survivor contract v2（event 物件擴六鍵；v1 顯式拒；鍵集斷言）
# ============================================================================
_V2_KEYS = ("event_manifest_hash", "label_definition_hash", "decision_time_rule", "feature_cutoff_rule", "label_window_rule", "control_kind")


def _event_kwargs(event_context=None):
    ev = sc.compute_event_identity(None, [1704067200000 + i * 43200000 for i in range(40)])
    kw, _ = _build_kwargs(event=ev)
    if event_context is not None:
        kw["event_context"] = event_context
    return kw


def _ctx():
    return {
        "event_manifest_hash": "1" * 64, "label_definition_hash": "2" * 64,
        "decision_time_rule": "t0_open_minus_k_bars", "feature_cutoff_rule": "max_close_le_decision_at",
        "label_window_rule": "close_to_close:horizon_bars=2", "control_kind": "user_labeled_same_trigger",
    }


def test_v2_event_keyset_and_nulls_when_no_context():
    c = sc.load_survivor_contract()
    assert set(_V2_KEYS) <= set(c["event_definition_keys"]["keys"])
    payload = sc.build_survivor_output(**_event_kwargs())
    assert payload["schema_version"] == 2 and payload["sample_scope"]["kind"] == "event"
    assert all(payload["sample_scope"]["event"][k] is None for k in _V2_KEYS)  # GAP-2 語意不變：全 null
    sc.validate_survivor_output(payload)


def test_v2_event_context_filled_and_validated():
    payload = sc.build_survivor_output(**_event_kwargs(_ctx()))
    assert {k: payload["sample_scope"]["event"][k] for k in _V2_KEYS} == _ctx()
    sc.validate_survivor_output(payload)


@pytest.mark.parametrize("mutate", [
    lambda e: e.update(event_manifest_hash=None),                 # 半套
    lambda e: e.update(label_definition_hash="g" * 64),           # 非 hex
    lambda e: e.update(decision_time_rule=""),                    # 空字串
    lambda e: e.update(control_kind="platform_whatever"),         # 閉集外
    lambda e: e.update(control_kind="platform_random_bars"),      # enum 內但 accepted 外（CODEX-R1-P2-04）
])
def test_v2_event_keys_fail_closed(mutate):
    payload = sc.build_survivor_output(**_event_kwargs(_ctx()))
    mutate(payload["sample_scope"]["event"])
    with pytest.raises(ContractValidationError):
        sc.validate_survivor_output(payload)


def test_conditional_ic_requires_event_context_fail_closed():
    """CODEX-R1-P1-03：conditional_ic run（event_filter.label_source=event_label_value）缺六鍵 ⇒ build 與 validate 皆拒。"""
    kw = _event_kwargs()
    kw["report_meta"] = {**kw["report_meta"], "event_filter": {"applied": True, "label_source": "event_label_value"}}
    with pytest.raises(ContractValidationError, match="event_context"):
        sc.build_survivor_output(**kw)
    kw2 = _event_kwargs(_ctx())
    kw2["report_meta"] = {**kw2["report_meta"], "event_filter": {"applied": True, "label_source": "event_label_value"}}
    payload = sc.build_survivor_output(**kw2)
    sc.validate_survivor_output(payload, report_meta=kw2["report_meta"])
    payload["sample_scope"]["event"]["event_manifest_hash"] = None
    payload["sample_scope"]["event"]["label_definition_hash"] = None
    for k in ("decision_time_rule", "feature_cutoff_rule", "label_window_rule", "control_kind"):
        payload["sample_scope"]["event"][k] = None
    with pytest.raises(ContractValidationError, match="non-null"):
        sc.validate_survivor_output(payload, report_meta=kw2["report_meta"])


def test_partial_event_context_rejected_and_validator_independent_of_report_meta():
    """CODEX-R2-P1-03：builder 對半套 context 拒；validator 以 payload 自述 label_source 判 conditional IC（不需 report_meta）。"""
    kw = _event_kwargs({k: v for k, v in _ctx().items() if k != "control_kind"})  # 半套
    with pytest.raises(ContractValidationError, match="exactly the six"):
        sc.build_survivor_output(**kw)
    kw2 = _event_kwargs(_ctx())
    kw2["report_meta"] = {**kw2["report_meta"], "event_filter": {"applied": True, "label_source": "event_label_value"}}
    payload = sc.build_survivor_output(**kw2)
    assert payload["sample_scope"]["event"]["label_source"] == "event_label_value"
    sc.validate_survivor_output(payload)                                   # 不帶 report_meta 亦驗
    for k in ("event_manifest_hash", "label_definition_hash"):
        payload["sample_scope"]["event"][k] = None
    for k in ("decision_time_rule", "feature_cutoff_rule", "label_window_rule", "control_kind"):
        payload["sample_scope"]["event"][k] = None
    with pytest.raises(ContractValidationError, match="non-null"):
        sc.validate_survivor_output(payload)                               # 不帶 report_meta 仍拒
    payload2 = sc.build_survivor_output(**_event_kwargs())
    assert payload2["sample_scope"]["event"]["label_source"] is None       # 無事件 label ⇒ null


def test_v1_payload_explicitly_rejected_no_silent_coerce():
    payload, _ = _valid_payload()
    payload["schema_version"] = 1
    with pytest.raises(ContractValidationError, match="legacy"):
        sc.validate_survivor_output(payload)
    payload["schema_version"] = 3
    with pytest.raises(ContractValidationError, match="schema_version"):
        sc.validate_survivor_output(payload)


# ════════════════════════════════════════════════════════════════════════════
# 事件模式之對帳母體（20260825-SURVIVORNSAMPLES-X-CONSULT-R1；三家一致）
#
# 🔴 修法前之缺陷：`kind == "event"` 時 `n_samples` 是**過濾後**列數，而
#    `train_plan`／`test_plan` 之 `row_index` 是**全時間軸**索引；契約拿兩者對帳
#    ⇒ 必假陽 ⇒ 例外一路傳出 `analyze()`，整段分析中止。
#    三個落點：①split 和對帳 ②`marginal n_test` exact 對帳 ③`n_samples_test` fallback。
# 本節每一條各鎖一個落點；改壞任一處都要有一條轉紅。
# ════════════════════════════════════════════════════════════════════════════

_EV_N = 800          # 過濾後之事件列數
_EV_TRAIN = 600      # 落在訓練區之事件數
_EV_TEST = 197       # 落在測試區之事件數（600+197=797 < 800：3 個落在 purge／embargo 帶）
_FULL_TRAIN = 3000   # 全時間軸切分列數（與事件數無關，故意遠大於 _EV_N）
_FULL_TEST = 2000


def _build_event_kwargs(*, with_masks=True, mask_len=None, marginal=True):
    """事件模式之 kwargs：n_samples 為過濾後列數，plan 為全時間軸列數（原缺陷之形態）。"""
    rng = _np.random.default_rng(20260825)
    df = _pd.DataFrame({k: rng.standard_normal(_EV_N) for k in ("s1", "s2", "f", "z")})
    y = _pd.Series(0.3 * df["s1"] + 0.3 * df["s2"] + 0.4 * df["f"] + rng.normal(0, 0.8, _EV_N))
    tr = _np.zeros(_EV_N, dtype=bool)
    te = _np.zeros(_EV_N, dtype=bool)
    tr[:_EV_TRAIN] = True
    te[_EV_TRAIN + 3:] = True          # 中間 3 列＝purge／embargo 帶，兩側皆 False
    assert int(tr.sum()) == _EV_TRAIN and int(te.sum()) == _EV_TEST

    surv = ["s1", "s2", "f"]
    marg = None
    if marginal:
        marg = _cmi(df, y, train_mask=tr, test_mask=te, survivors=surv,
                    extra_candidates=["z"], params=_P(n_bootstrap=10, block_len=5), fit_scope="train")
    comp = _combine(df, y, train_mask=tr, test_mask=te, survivors=surv,
                    params=_P(n_bootstrap=10, block_len=5), fit_scope="train")

    train_plan = _NS(row_index=_np.arange(_FULL_TRAIN), time_bounds=("2024-01-01", "2024-06-30"),
                     embargo=2, purge_gap=3, base_universe_hash="u" * 8)
    test_plan = _NS(row_index=_np.arange(_FULL_TRAIN, _FULL_TRAIN + _FULL_TEST),
                    time_bounds=("2024-07-01", "2024-12-31"),
                    embargo=2, purge_gap=3, base_universe_hash="u" * 8)

    split_context = {"train_plan": train_plan, "test_plan": test_plan}
    if with_masks:
        n = _EV_N if mask_len is None else mask_len
        split_context["train_mask"] = tr[:n] if n <= _EV_N else _np.concatenate([tr, _np.zeros(n - _EV_N, bool)])
        split_context["test_mask"] = te[:n] if n <= _EV_N else _np.concatenate([te, _np.zeros(n - _EV_N, bool)])

    return dict(
        report_meta={
            "symbol": "ETHUSDT", "timeframe": "12h", "n_samples": _EV_N,
            "event_filter": {"applied": True, "mode": "timestamps", "n_events": _EV_N},
            "ic_train_test_split": {"applied": True}, "split_method": "holdout",
            "selection_scope": {"scope_id": "scope-1"},
        },
        filtered_features=surv, marginal_ic_result=marg, composite_result=comp,
        summary_by_feature={n: {"ic_mean": 0.1, "icir": 1.2, "p_value_adj": 0.01, "pass_class": "oos"} for n in surv},
        root_analysis_status="ok_oos",
        event_identity=sc.compute_event_identity(None, list(range(_EV_N))),
        split_context=split_context, config_hash="c" * 8, features_source_hash="f" * 64,
        features_path="/tmp/x.h5", labels_content_hash="l" * 64, symbol="ETHUSDT", timeframe="12h",
        case_id="ic_gatekeeper", generated_at="2026-08-25T00:00:00Z", fit_mode="train",
        pit_stats_version="v1", ic_method="spearman", label_horizon=12, label_return_type="log",
        report_ref="ic_report_ic_gatekeeper.json",
    )


def test_event_mode_reconciles_on_filtered_masks():
    """落點①②：事件模式以過濾後 mask 對帳 ⇒ 可產出（修法前此處必 raise）。"""
    payload = sc.build_survivor_output(**_build_event_kwargs())
    scope = payload["sample_scope"]
    assert scope["kind"] == "event"
    assert scope["n_samples_total"] == _EV_N
    # 🔴 逐字：測試列數必須是**事件側**的 197，不是全軸的 2000
    assert scope["n_samples_test"] == _EV_TEST
    assert scope["n_samples_test"] != _FULL_TEST


def test_event_mode_allows_purge_gap_le_not_eq():
    """關係為 `≤` 非 `==`：落在 purge／embargo 帶之事件兩側皆不算，797 < 800 須放行。"""
    assert _EV_TRAIN + _EV_TEST < _EV_N            # 前提本身受測（否則本條打空氣）
    sc.build_survivor_output(**_build_event_kwargs())


def test_event_mode_without_masks_fails_closed_when_ambiguous():
    """事件模式缺 mask **且** plan 列數和 > n_samples ⇒ 無法判斷是算錯還是跨母體 ⇒ 具名 fail-closed。

    🔴 不得靜默把跨母體之不等式當成錯誤（那就是原缺陷），也不得靜默放行。
    正式路徑不會走到這裡：orchestrator 只要有 split_context 就必寫入兩 mask。
    """
    with pytest.raises(ContractValidationError, match="lacks train_mask/test_mask"):
        sc.build_survivor_output(**_build_event_kwargs(with_masks=False))


def test_event_mode_mask_length_must_equal_n_samples():
    """mask 與 n_samples 不同長 ⇒ 兩者不是同一批列 ⇒ fail-closed。"""
    with pytest.raises(ContractValidationError, match="mask length"):
        sc.build_survivor_output(**_build_event_kwargs(mask_len=_EV_N - 1))


def test_event_mode_n_samples_test_no_full_axis_fallback():
    """落點③（GROK-R1-P2-02）：marginal 缺席時，n_samples_test 仍須取事件側，不得退回全軸。"""
    payload = sc.build_survivor_output(**_build_event_kwargs(marginal=False))
    assert payload["sample_scope"]["n_samples_test"] == _EV_TEST
    assert payload["sample_scope"]["n_samples_test"] != _FULL_TEST


def test_non_event_split_row_guard_preserved():
    """非事件模式之原保護不得被弱化：plan train+test > n_samples 仍須 raise。"""
    kw, _ = _build_kwargs()                 # event=None ⇒ kind=full
    kw["report_meta"] = dict(kw["report_meta"])
    kw["report_meta"]["n_samples"] = 1      # 人為讓 plan 列數遠大於總數
    kw["marginal_ic_result"] = None         # 排除 marginal 那條先命中
    with pytest.raises(ContractValidationError, match="split train_rows\\+test_rows"):
        sc.build_survivor_output(**kw)


def test_event_mode_no_masks_no_marginal_leaves_n_samples_test_null():
    """GROK-R1-P2-01：事件模式缺 mask 又無 marginal ⇒ n_samples_test 須為 null。

    🔴 不得靜默寫入**全軸** `len(test_plan.row_index)`——那與 n_samples_total（過濾後）
    又是跨母體，與原缺陷同型，只是靜默而非 raise。寧可誠實留 null（schema nullable）。
    前提：本形態須不觸發「有歧義」之 raise ⇒ plan 列數和必須 ≤ n_samples。
    """
    kw = _build_event_kwargs(with_masks=False, marginal=False)
    # 讓 plan 列數和 ≤ n_total（否則會先命中具名 fail-closed，測不到本條）
    kw["report_meta"] = dict(kw["report_meta"])
    kw["report_meta"]["n_samples"] = _FULL_TRAIN + _FULL_TEST + 1
    payload = sc.build_survivor_output(**kw)
    scope = payload["sample_scope"]
    assert scope["kind"] == "event"
    assert scope["n_samples_test"] is None
    assert scope["n_samples_test"] != _FULL_TEST
