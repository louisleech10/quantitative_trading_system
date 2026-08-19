"""GAP-2b 倖存因子輸出契約——loader（Task 1.0）。

契約單一真相源＝``momentum/Analysis/contracts/ic_survivor_contract.json``；
本模組**不**複列任何鍵名／枚舉／reason 字面，只負責 fail-closed 載入與頂層鍵集檢查。
resolver／validator／``build_survivor_output`` 於 Task 3.1 加入本檔。

冷啟動注意：頂層鍵集於本檔以 frozenset 鎖死（與 TODO Task 1.0 步驟 1 一致）；
契約檔多鍵／少鍵一律 ``ContractValidationError``（不 fallback、不吞）。
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional

from momentum.Analysis.ic_config_schema import ContractValidationError

__all__ = [
    "SURVIVOR_CONTRACT_PATH",
    "SURVIVOR_CONTRACT_TOP_KEYS",
    "load_survivor_contract",
]

SURVIVOR_CONTRACT_PATH = Path(__file__).parent / "contracts" / "ic_survivor_contract.json"

# 頂層鍵集（恰為此集合；TODO Task 1.0 步驟 1）。B4 若增鍵須同步本集合與測試 ①（可見）。
SURVIVOR_CONTRACT_TOP_KEYS = frozenset(
    {
        "version",
        "_doc",
        "capability_status_ref",
        "reasons",
        "algorithm_version",
        "survivor_file_keys",
        "sample_scope_keys",
        "sample_scope_kind_values",
        "event_definition_keys",
        "event_identity_keys",
        "split_keys",
        "row_identity_keys",
        "provenance_keys",
        "survivor_record_keys",
        "marginal_ic_section_keys",
        "statistic_values",
        "projection_space_values",
        "weights_method_values",
        "view_values",
        "fit_scope_values",
        "selection_sample_values",
        "oos_semantics_values",
        "independent_oos_validation_allowed",
        "survivor_output_status_keys",
    }
)

_contract_cache: Optional[Dict[str, Any]] = None


def load_survivor_contract(path: Optional[Path] = None) -> Dict[str, Any]:
    """載入倖存者契約 SoT（fail-closed）。

    - ``path`` 預設為 ``SURVIVOR_CONTRACT_PATH``；傳入其他路徑（測試 tamper 用）時不走 cache。
    - 檔缺／JSON 壞／非 mapping ⇒ ``ContractValidationError``。
    - 頂層鍵集必須 **恰等於** ``SURVIVOR_CONTRACT_TOP_KEYS``；多鍵或少鍵皆 raise。
    - ``independent_oos_validation_allowed`` 必須恰為 ``[False]``（version=1 之硬約束）。
    - 回傳 dict **副本**（deepcopy；caller 改寫不影響後續呼叫——A1-7 K1）；不解析 ``capability_status_ref``（resolver 於 Task 3.1）。
    """
    global _contract_cache
    use_cache = path is None
    if use_cache and _contract_cache is not None:
        return copy.deepcopy(_contract_cache)  # A1-7 K1：cache 為內部，回傳副本（禁 mutable singleton 外洩）

    contract_path = SURVIVOR_CONTRACT_PATH if path is None else Path(path)
    if not contract_path.is_file():
        raise ContractValidationError(f"survivor contract missing: {contract_path}")
    try:
        with contract_path.open("r", encoding="utf-8") as file:
            contract = json.load(file)
    except json.JSONDecodeError as exc:
        raise ContractValidationError(
            f"survivor contract is not valid JSON: {contract_path}: {exc}"
        ) from exc
    if not isinstance(contract, dict):
        raise ContractValidationError(
            f"survivor contract must be a mapping: {contract_path}"
        )

    keys = frozenset(contract.keys())
    if keys != SURVIVOR_CONTRACT_TOP_KEYS:
        missing = sorted(SURVIVOR_CONTRACT_TOP_KEYS - keys)
        extra = sorted(keys - SURVIVOR_CONTRACT_TOP_KEYS)
        raise ContractValidationError(
            "survivor contract top-level keys mismatch: "
            f"missing={missing} extra={extra} ({contract_path})"
        )
    if contract.get("independent_oos_validation_allowed") != [False]:
        raise ContractValidationError(
            "survivor contract independent_oos_validation_allowed must be [false] "
            f"(got {contract.get('independent_oos_validation_allowed')!r})"
        )

    if use_cache:
        _contract_cache = contract
    return copy.deepcopy(contract)


# ============================================================================
# Task 3.1 — resolver／event identity／validator／build_survivor_output
# ============================================================================
import hashlib as _hashlib
import math as _math
from typing import Iterable, List, Sequence

import numpy as _np
import pandas as _pd

__all__ += [
    "REPO_ROOT",
    "resolve_ref",
    "compute_event_identity",
    "validate_survivor_output",
    "build_survivor_output",
    "feature_set_hash",
]

REPO_ROOT = Path(__file__).resolve().parents[2]

_TYPE_CHECKS = {
    "str": lambda v: isinstance(v, str),
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: (isinstance(v, (int, float)) and not isinstance(v, bool) and _math.isfinite(float(v))),
    "bool": lambda v: isinstance(v, bool),
    "list": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def resolve_ref(ref: str) -> list:
    """解析 ``<repo 相對路徑>#<a.b.c>`` 為 list（fail-closed：檔缺／鍵路徑缺／非 list ⇒ ``ContractValidationError``）。"""
    if not isinstance(ref, str) or "#" not in ref:
        raise ContractValidationError(f"bad ref (expect '<path>#<key.path>'): {ref!r}")
    rel_path, key_path = ref.split("#", 1)
    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts or not rel_path.strip():
        raise ContractValidationError(f"ref path must be repo-relative without '..': {rel_path!r}")
    target = (REPO_ROOT / rel).resolve()
    try:
        target.relative_to(REPO_ROOT.resolve())
    except ValueError:
        raise ContractValidationError(f"ref path escapes repo root: {rel_path!r}")
    if not target.is_file():
        raise ContractValidationError(f"ref target missing: {target}")
    try:
        with target.open("r", encoding="utf-8") as file:
            node: Any = json.load(file)
    except json.JSONDecodeError as exc:
        raise ContractValidationError(f"ref target is not valid JSON: {target}: {exc}") from exc
    for part in key_path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ContractValidationError(f"ref key path missing: {key_path!r} in {rel_path}")
        node = node[part]
    if not isinstance(node, list):
        raise ContractValidationError(f"ref does not resolve to a list: {ref!r}")
    return list(node)


def _to_epoch_ms_utc(timestamps: Iterable[Any]) -> List[int]:
    """timestamps → int64 epoch ms UTC → sorted unique（數值：max|·|>=1e12 視為 ms 否則 s，沿 ic_engine 原語）。"""
    values = list(timestamps)
    if not values:
        return []
    arr = _pd.Series(values)
    if _pd.api.types.is_numeric_dtype(arr.dtype) and not _pd.api.types.is_datetime64_any_dtype(arr.dtype):
        if arr.isna().any():
            raise ContractValidationError("event timestamps contain NaN")
        max_abs = float(_np.nanmax(_np.abs(arr.to_numpy(dtype=float))))
        unit = "ms" if max_abs >= 1e12 else "s"
        parsed = _pd.to_datetime(arr.to_numpy(), unit=unit, utc=True, errors="raise")
    else:
        parsed = _pd.to_datetime(arr, utc=True, errors="raise")
    ms = (_pd.DatetimeIndex(parsed).asi8 // 1_000_000).astype("int64")
    return sorted(set(int(v) for v in ms))


def compute_event_identity(query: Optional[str], timestamps: Optional[Iterable[Any]]) -> Dict[str, Any]:
    """事件身分（契約 ``event_identity_keys``；序列化規格見契約 ``_doc``）。

    - timestamps 非空 ⇒ ``mode="timestamps"``：``definition_hash=timestamps_hash=sha256(json.dumps(sorted_unique_ms, separators=(",",":")))``；
      ``n_events=len(unique)``、``n_timestamps_requested=len(raw)``。
    - 否則 query 非空 ⇒ ``mode="query"``：``definition_hash=sha256(query.strip().encode("utf-8"))``、``timestamps_hash=None``、計數 None。
    - 皆無 ⇒ ``mode="none"``、兩 hash None、計數 None。
    """
    raw = list(timestamps) if timestamps is not None else []
    if raw:
        uniq = _to_epoch_ms_utc(raw)
        payload = json.dumps(uniq, separators=(",", ":")).encode("utf-8")
        digest = _hashlib.sha256(payload).hexdigest()
        return {"mode": "timestamps", "definition_hash": digest, "timestamps_hash": digest,
                "n_events": int(len(uniq)), "n_timestamps_requested": int(len(raw))}
    if query is not None and str(query).strip():
        digest = _hashlib.sha256(str(query).strip().encode("utf-8")).hexdigest()
        return {"mode": "query", "definition_hash": digest, "timestamps_hash": None,
                "n_events": None, "n_timestamps_requested": None}
    return {"mode": "none", "definition_hash": None, "timestamps_hash": None,
            "n_events": None, "n_timestamps_requested": None}


def feature_set_hash(feature_names: Sequence[str]) -> str:
    return _hashlib.sha256(json.dumps(list(feature_names), separators=(",", ":")).encode("utf-8")).hexdigest()


def _check_object(obj: Any, schema: Dict[str, Any], label: str) -> None:
    """依 ``{additional_properties:false, keys:{k:{type,required,nullable}}}`` 驗一物件層（不遞迴）。"""
    if not isinstance(obj, dict):
        raise ContractValidationError(f"{label}: expected object, got {type(obj).__name__}")
    keys = schema["keys"]
    if schema.get("additional_properties") is False:
        unknown = sorted(set(obj.keys()) - set(keys.keys()))
        if unknown:
            raise ContractValidationError(f"{label}: unknown keys {unknown}")
    for key, spec in keys.items():
        if key not in obj:
            if spec.get("required", True):
                raise ContractValidationError(f"{label}: missing required key {key!r}")
            continue
        value = obj[key]
        if value is None:
            if not spec.get("nullable", False):
                raise ContractValidationError(f"{label}.{key}: null not allowed")
            continue
        checker = _TYPE_CHECKS[spec["type"]]
        if not checker(value):
            raise ContractValidationError(f"{label}.{key}: type mismatch (expect {spec['type']}, got {type(value).__name__})")


def validate_survivor_output(payload: Dict[str, Any], *, report_meta: Optional[Dict[str, Any]] = None, report_ref_path: Optional[str] = None) -> None:
    """倖存者輸出檔 fail-closed 驗證（詳見 TODO Task 3.1 步驟 2；任一不成立 ⇒ ``ContractValidationError``）。"""
    c = load_survivor_contract()
    sec = c["marginal_ic_section_keys"]
    _check_object(payload, c["survivor_file_keys"], "survivor_file")
    if payload["schema_version"] != c["version"]:
        raise ContractValidationError(f"schema_version {payload['schema_version']!r} != contract version {c['version']!r}")

    # ---- 枚舉 ----
    cap = frozenset(resolve_ref(c["capability_status_ref"]))
    if payload["status"] not in cap:
        raise ContractValidationError(f"status {payload['status']!r} not in capability_status")
    if payload["status"] != "ok" and not payload.get("reason"):
        raise ContractValidationError("status != ok requires non-empty reason")
    if payload["reason"] is not None and payload["reason"] not in c["reasons"]["marginal_ic"]:
        raise ContractValidationError(f"reason {payload['reason']!r} not in reasons.marginal_ic")
    if payload["statistic"] not in c["statistic_values"]:
        raise ContractValidationError("statistic not in statistic_values")
    if payload["projection_space"] not in c["projection_space_values"]:
        raise ContractValidationError("projection_space not in projection_space_values")
    if payload["selection_sample"] not in c["selection_sample_values"]:
        raise ContractValidationError("selection_sample not in selection_sample_values")
    if payload["oos_semantics"] not in c["oos_semantics_values"]:
        raise ContractValidationError("oos_semantics not the contract literal")
    if payload["independent_oos_validation"] not in c["independent_oos_validation_allowed"]:
        raise ContractValidationError("independent_oos_validation not allowed")
    if payload["algorithm_version"] != c["algorithm_version"]:
        raise ContractValidationError("algorithm_version mismatch")

    # ---- OOS 四欄互斥 ----
    st, oos, pc = payload["analysis_status"], payload["oos_guarantees"], payload["pass_class"]
    if st == "ok_oos":
        if oos is not True or pc != "oos":
            raise ContractValidationError("ok_oos requires oos_guarantees=true and pass_class=oos")
    elif st == "degraded_full_sample":
        if oos is not False or pc != "full_sample_research_only":
            raise ContractValidationError("degraded_full_sample requires oos_guarantees=false and pass_class=full_sample_research_only")
    else:
        raise ContractValidationError(f"analysis_status {st!r} not in {{ok_oos, degraded_full_sample}}")

    # ---- sample_scope ----
    scope = payload["sample_scope"]
    _check_object(scope, c["sample_scope_keys"], "sample_scope")
    if scope["kind"] not in c["sample_scope_kind_values"]:
        raise ContractValidationError(f"sample_scope.kind {scope['kind']!r} not allowed")
    if scope["kind"] == "event" and scope["event"] is None:
        raise ContractValidationError("sample_scope.kind=event requires event object")
    if scope["event"] is not None:
        _check_event_object(scope["event"], c, "sample_scope.event")

    # ---- split / provenance ----
    split = payload["split"]
    _check_object(split, c["split_keys"], "split")
    _check_object(split["row_identity"], c["row_identity_keys"], "split.row_identity")
    prov = payload["provenance"]
    _check_object(prov, c["provenance_keys"], "provenance")
    if prov["contract_version"] != c["version"]:
        raise ContractValidationError("provenance.contract_version mismatch")
    if prov["algorithm_version"] != c["algorithm_version"]:
        raise ContractValidationError("provenance.algorithm_version mismatch")
    if not str(prov["fit_mode"]).strip():
        raise ContractValidationError("provenance.fit_mode must be non-empty (orchestrator preprocessing fit_mode 原值)")

    # ---- feature_names / feature_set_hash / survivors ----
    names = payload["feature_names"]
    if not all(isinstance(n, str) for n in names):
        raise ContractValidationError("feature_names must be list[str]")
    if len(set(names)) != len(names):
        raise ContractValidationError("feature_names contains duplicates")
    if payload["feature_set_hash"] != feature_set_hash(names):
        raise ContractValidationError("feature_set_hash mismatch")
    survivors = payload["survivors"]
    for i, rec in enumerate(survivors):
        _check_object(rec, c["survivor_record_keys"], f"survivors[{i}]")
    if [r["feature_name"] for r in survivors] != list(names):
        raise ContractValidationError("survivors[].feature_name sequence != feature_names")

    # ---- composite / removed_candidates ----
    comp = payload["composite"]
    if "method" in comp:  # 完整 composite（非 status 物件）
        _check_object(comp, sec["composite_keys"], "composite")
        if comp["method"] not in c["weights_method_values"]:
            raise ContractValidationError("composite.method not allowed")
        if comp["fit_scope"] is not None and comp["fit_scope"] not in c["fit_scope_values"]:
            raise ContractValidationError("composite.fit_scope not allowed")
    else:
        _check_object(comp, sec["view_status_keys"], "composite(status object)")
    if comp["status"] not in cap:
        raise ContractValidationError("composite.status not in capability_status")
    for name, rec in payload["removed_candidates"].items():
        _check_object(rec, sec["removed_candidate_keys"], f"removed_candidates[{name}]")

    # ---- 身分 ----
    if report_meta is not None:
        for key in ("symbol", "timeframe"):
            if key not in report_meta or report_meta[key] is None:
                raise ContractValidationError(f"report_meta missing {key} (identity check requires it)")
            if payload[key] != report_meta[key]:
                raise ContractValidationError(f"{key} mismatch: payload {payload[key]!r} != report {report_meta[key]!r}")
    expected_ref = f"ic_report_{payload['case_id']}.json"
    if report_ref_path is not None and Path(report_ref_path).name != expected_ref:
        raise ContractValidationError(f"report_ref_path name {Path(report_ref_path).name!r} != {expected_ref!r}")
    if Path(prov["report_ref"]).name != expected_ref:
        raise ContractValidationError(f"provenance.report_ref {prov['report_ref']!r} != {expected_ref!r}")


def _is_sha256_hex(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(ch in "0123456789abcdef" for ch in v)


def _check_event_object(ev: Dict[str, Any], c: Dict[str, Any], label: str) -> None:
    """event 物件依 mode 驗不變式（R18 CODEX-R18-P1-03）：
    timestamps ⇒ 兩 hash 皆 64-hex 且相等、n_events≥1、n_timestamps_requested≥n_events；
    query ⇒ definition_hash 64-hex、timestamps_hash None、計數 None；none ⇒ 全 None。"""
    _check_object(ev, c["event_definition_keys"], label)
    mode = ev["mode"]
    if mode == "timestamps":
        if not (_is_sha256_hex(ev["definition_hash"]) and _is_sha256_hex(ev["timestamps_hash"])):
            raise ContractValidationError(f"{label}: timestamps mode requires 64-hex definition_hash and timestamps_hash")
        if ev["definition_hash"] != ev["timestamps_hash"]:
            raise ContractValidationError(f"{label}: timestamps mode requires definition_hash == timestamps_hash")
        if not (isinstance(ev["n_events"], int) and ev["n_events"] >= 1):
            raise ContractValidationError(f"{label}: timestamps mode requires n_events >= 1")
        if not (isinstance(ev["n_timestamps_requested"], int) and ev["n_timestamps_requested"] >= ev["n_events"]):
            raise ContractValidationError(f"{label}: n_timestamps_requested must be >= n_events")
    elif mode == "query":
        if not _is_sha256_hex(ev["definition_hash"]) or ev["timestamps_hash"] is not None:
            raise ContractValidationError(f"{label}: query mode requires 64-hex definition_hash and null timestamps_hash")
        if ev["n_events"] is not None or ev["n_timestamps_requested"] is not None:
            raise ContractValidationError(f"{label}: query mode requires null counts")
    elif mode == "none":
        if any(ev[k] is not None for k in ("definition_hash", "timestamps_hash", "n_events", "n_timestamps_requested")):
            raise ContractValidationError(f"{label}: none mode requires all-null identity")
    else:
        raise ContractValidationError(f"{label}: mode {mode!r} invalid")


def _status_object(status: str, reason: Optional[str]) -> Dict[str, Any]:
    return {"status": status, "reason": reason}


def build_survivor_output(
    *,
    report_meta: Dict[str, Any],
    filtered_features: List[str],
    marginal_ic_result: Any,
    composite_result: Any,
    summary_by_feature: Dict[str, Dict[str, Any]],
    root_analysis_status: str,
    event_identity: Dict[str, Any],
    split_context: Optional[Dict[str, Any]],
    config_hash: str,
    features_source_hash: str,
    features_path: Optional[str],
    labels_content_hash: str,
    symbol: str,
    timeframe: str,
    case_id: str,
    generated_at: str,
    fit_mode: str,
    pit_stats_version: Optional[str],
    ic_method: str,
    label_horizon: Optional[int],
    label_return_type: Optional[str],
    report_ref: str,
) -> Dict[str, Any]:
    """純組裝（不寫檔、不 log）：依契約鍵集組出 ``ic_survivors_{case_id}.json`` payload。

    - OOS 四欄由 ``root_analysis_status`` 單一來源導出（``ok_oos`` ⇒ True／``oos``；否則 False／``full_sample_research_only``）。
    - ``sample_scope``：``event_identity.mode ∈ {query,timestamps}`` 且非 fallback ⇒ ``kind=event``；否則 ``kind=full``；
      ``degraded = bool(report_meta.event_filter.fallback)``；``event`` 於 mode≠none 時帶身分物件（fallback 仍保留供追溯）。
    - ``n_samples_total`` 取 ``report_meta["n_samples"]``（orchestrator 於 report 組裝寫入）；缺則 ``marginal.n_train+n_test``；再缺則 split 列數和；皆缺 ⇒ raise；並與 marginal／split 列數對帳（≥；test 列數 exact）。
    - ``provenance.fit_mode``＝orchestrator 前處理 fit_mode **原值**（``full_sample|train_mask|pit_expanding``），與 ``composite.fit_scope`` 語意不同、不映射（A1-9）。
    - 無 split（fallback）⇒ ``split_context["full_index"]`` 必傳（row_identity 用真實 index；禁 arange 冒充）。
    - ``survivors[]`` IC 快照自 ``summary_by_feature[name]``（``ic_mean``／``icir``／``p_value_adj``／``pass_class``；缺欄 ⇒ null）；
      marginal 欄自 ``marginal_ic_result.per_feature[name]``（loo 視角；不可算 ⇒ null）。
    """
    from momentum.core.contracts import canonical_idx_hash  # 既有原語

    c = load_survivor_contract()
    names = list(filtered_features)
    if len(set(names)) != len(names):
        raise ContractValidationError("filtered_features contains duplicates")

    st = str(root_analysis_status)
    if st == "ok_oos":
        oos, pc = True, "oos"
    elif st == "degraded_full_sample":
        oos, pc = False, "full_sample_research_only"
    else:  # R18 CODEX-R18-P1-05：未知 root status fail-closed（禁靜默降級）
        raise ContractValidationError(f"root_analysis_status {st!r} not in {{ok_oos, degraded_full_sample}}")

    marg = marginal_ic_result.to_dict() if marginal_ic_result is not None and hasattr(marginal_ic_result, "to_dict") else (dict(marginal_ic_result) if isinstance(marginal_ic_result, dict) else None)
    comp = composite_result.to_dict() if composite_result is not None and hasattr(composite_result, "to_dict") else (dict(composite_result) if isinstance(composite_result, dict) else None)

    # ---- sample_scope ----
    ev = dict(event_identity or {})
    ev_mode = ev.get("mode", "none")
    ef = report_meta.get("event_filter") if isinstance(report_meta, dict) else None
    fallback = bool(isinstance(ef, dict) and ef.get("fallback") is True)
    kind = "event" if (ev_mode in ("query", "timestamps") and not fallback) else "full"
    event_obj = None
    if ev_mode in ("query", "timestamps"):
        event_obj = {k: ev.get(k) for k in c["event_definition_keys"]["keys"].keys()}
    n_total = report_meta.get("n_samples") if isinstance(report_meta, dict) else None
    if n_total is None and marg is not None and marg.get("n_train") is not None and marg.get("n_test") is not None:
        n_total = int(marg["n_train"]) + int(marg["n_test"])
    train_plan = split_context.get("train_plan") if split_context else None
    test_plan = split_context.get("test_plan") if split_context else None
    if n_total is None and train_plan is not None and test_plan is not None:
        n_total = int(len(train_plan.row_index)) + int(len(test_plan.row_index))
    if n_total is None:
        raise ContractValidationError("n_samples_total unavailable (report_meta.n_samples / marginal n_train+n_test / split rows)")
    if not (isinstance(n_total, int) and not isinstance(n_total, bool) and n_total >= 1):
        raise ContractValidationError(f"n_samples_total must be positive int, got {n_total!r}")
    # R18 CODEX-R18-P1-06：與 marginal／split 列數對帳（purge/embargo 使 train+test ≤ total，故為 ≥ 而非 ==；test 列數兩源須 exact）
    if marg is not None and marg.get("n_train") is not None and marg.get("n_test") is not None:
        n_tr, n_te = int(marg["n_train"]), int(marg["n_test"])
        if marg.get("fit_scope") == "full_sample":  # 全樣本 fallback：兩 mask 皆全 True（重疊）⇒ 以 max 對帳
            if max(n_tr, n_te) > int(n_total):
                raise ContractValidationError("n_samples_total < marginal max(n_train, n_test) (full_sample)")
        elif n_tr + n_te > int(n_total):
            raise ContractValidationError("n_samples_total < marginal n_train+n_test")
    if train_plan is not None and test_plan is not None:
        if int(len(train_plan.row_index)) + int(len(test_plan.row_index)) > int(n_total):
            raise ContractValidationError("n_samples_total < split train_rows+test_rows")
        if marg is not None and marg.get("n_test") is not None and int(marg["n_test"]) != int(len(test_plan.row_index)):
            raise ContractValidationError("marginal n_test != split test_rows")
    n_test = None
    if marg is not None and marg.get("n_test") is not None:
        n_test = int(marg["n_test"])
    elif test_plan is not None:
        n_test = int(len(test_plan.row_index))
    sample_scope = {"kind": kind, "event": event_obj, "n_samples_total": int(n_total), "n_samples_test": n_test, "degraded": fallback}

    # ---- split ----
    split_meta = report_meta.get("ic_train_test_split") if isinstance(report_meta, dict) else None
    split_meta = split_meta if isinstance(split_meta, dict) else {}
    if train_plan is not None and test_plan is not None:
        row_identity = {
            "train_index_hash": canonical_idx_hash(train_plan.row_index),
            "test_index_hash": canonical_idx_hash(test_plan.row_index),
        }
        split = {
            "split_method": str(report_meta.get("split_method") or "holdout"),
            "train_time_bounds": [str(v) for v in train_plan.time_bounds] if getattr(train_plan, "time_bounds", None) else None,
            "test_time_bounds": [str(v) for v in test_plan.time_bounds] if getattr(test_plan, "time_bounds", None) else None,
            "train_rows": int(len(train_plan.row_index)),
            "test_rows": int(len(test_plan.row_index)),
            "embargo": int(train_plan.embargo) if getattr(train_plan, "embargo", None) is not None else None,
            "purge_gap": int(train_plan.purge_gap) if getattr(train_plan, "purge_gap", None) is not None else None,
            "base_universe_hash": getattr(train_plan, "base_universe_hash", None) or None,
            "selection_scope_id": (report_meta.get("selection_scope") or {}).get("scope_id") if isinstance(report_meta.get("selection_scope"), dict) else None,
            "row_identity": row_identity,
        }
    else:
        full_index = split_context.get("full_index") if split_context else None
        if full_index is None:  # R18 CODEX-R18-P1-04：禁以 positional arange 冒充 row identity
            raise ContractValidationError("fallback/no-split requires split_context['full_index'] for row_identity")
        idx_hash = canonical_idx_hash(full_index)
        split = {
            "split_method": str(report_meta.get("split_method") or "full_sample_fallback"),
            "train_time_bounds": None,
            "test_time_bounds": None,
            "train_rows": int(n_total),
            "test_rows": int(n_total),
            "embargo": None,
            "purge_gap": None,
            "base_universe_hash": None,
            "selection_scope_id": (report_meta.get("selection_scope") or {}).get("scope_id") if isinstance(report_meta.get("selection_scope"), dict) else None,
            "row_identity": {"train_index_hash": idx_hash, "test_index_hash": idx_hash},
        }

    provenance = {
        "config_hash": str(config_hash),
        "features_source_hash": str(features_source_hash),
        "features_path": str(features_path) if features_path is not None else None,
        "labels_content_hash": str(labels_content_hash),
        "pit_stats_version": str(pit_stats_version) if pit_stats_version is not None else None,
        "fit_mode": str(fit_mode),
        "ic_method": str(ic_method),
        "label_horizon": int(label_horizon) if label_horizon is not None else None,
        "label_return_type": str(label_return_type) if label_return_type is not None else None,
        "report_ref": str(report_ref),
        "producer": "ic_filter_orchestrator",
        "contract_version": int(c["version"]),
        "algorithm_version": c["algorithm_version"],
    }

    # ---- survivors[] ----
    per_feature = (marg or {}).get("per_feature") or {}
    train_ic_map = (marg or {}).get("train_ic") or {}
    survivors_out = []
    for name in names:
        snap = summary_by_feature.get(name, {}) if isinstance(summary_by_feature, dict) else {}
        pf = per_feature.get(name) or {}
        ok = pf.get("status") == "ok"

        def _f(v):
            try:
                fv = float(v)
            except (TypeError, ValueError):
                return None
            return fv if _math.isfinite(fv) else None

        survivors_out.append({
            "feature_name": name,
            "ic_mean": _f(snap.get("ic_mean")),
            "icir": _f(snap.get("icir")),
            "p_value_adj": _f(snap.get("p_value_adj")),
            "pass_class": str(snap["pass_class"]) if snap.get("pass_class") is not None else None,
            "train_ic": _f(train_ic_map.get(name)),
            "gross_ic": _f(pf.get("gross_ic")) if ok else None,
            "marginal_ic_loo": _f(pf.get("marginal_ic")) if ok else None,
            "marginal_ic_loo_ci95": list(pf["ci95"]) if ok and pf.get("ci95") is not None else None,
            "marginal_ic_train_insample": _f(pf.get("marginal_ic_train_insample")) if ok else None,
            "redundancy_kept": True,
        })

    # ---- 頂層 status ----
    if not names:
        status, reason = "not_applicable", "no_survivors"
    elif marg is not None:
        status, reason = str(marg["status"]), marg.get("reason")
    else:
        status, reason = "not_computed", "disabled_by_config"
    if reason is not None and reason not in c["reasons"]["marginal_ic"]:
        raise ContractValidationError(f"reason {reason!r} not in contract")

    payload = {
        "schema_version": int(c["version"]),
        "generated_at": str(generated_at),
        "case_id": str(case_id),
        "symbol": str(symbol),
        "timeframe": str(timeframe),
        "analysis_status": st,
        "oos_guarantees": oos,
        "pass_class": pc,
        "independent_oos_validation": False,
        "selection_sample": c["selection_sample_values"][0],
        "oos_semantics": c["oos_semantics_values"][0],
        "statistic": c["statistic_values"][0],
        "projection_space": c["projection_space_values"][0],
        "algorithm_version": c["algorithm_version"],
        "sample_scope": sample_scope,
        "split": split,
        "provenance": provenance,
        "feature_names": names,
        "feature_set_hash": feature_set_hash(names),
        "survivors": survivors_out,
        "composite": comp if comp is not None else _status_object("not_computed", "disabled_by_config"),
        "removed_candidates": dict((marg or {}).get("removed_candidates") or {}),
        "status": status,
        "reason": reason,
    }
    return payload
