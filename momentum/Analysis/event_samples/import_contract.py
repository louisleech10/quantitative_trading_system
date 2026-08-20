"""GAP-3 事件匯入契約 validator（docs/GAP3_EVENT_TODO.md Task B1.0；SPEC D1/D2/AR-1）。

純函式、fail-closed：任一 failure 即 raise ContractValidationError（附逐列 reason），
不回部分結果、無 silent skip。欄位名/枚舉/reason 字面唯一住
`momentum/Analysis/contracts/event_import_contract.json`，本檔不複列（只經 contract dict 取用）。
"""

from __future__ import annotations

import hashlib
import json
import numbers
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from momentum.core.constants import TIMEFRAME_SECONDS

_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts" / "event_import_contract.json"
_HEX_CHARS = set("0123456789abcdef")


class ContractValidationError(ValueError):
    """匯入驗證失敗（fail-closed）。failures: list[dict{row, event_id, field, reason}]。"""

    def __init__(self, failures: List[Dict[str, Any]]):
        self.failures = failures
        super().__init__(
            "event import validation failed: "
            + json.dumps(failures[:20], ensure_ascii=False)
            + ("" if len(failures) <= 20 else f" …(+{len(failures) - 20})")
        )


def load_event_import_contract() -> dict:
    """讀取契約 JSON SoT；版本不符即 raise。"""
    with open(_CONTRACT_PATH, "r", encoding="utf-8") as f:
        contract = json.load(f)
    if contract.get("version") != 1:
        raise ValueError(f"unsupported event_import_contract version: {contract.get('version')!r}")
    return contract


def allowed_top_level_keys(contract: dict) -> set:
    """匯入檔頂層合法鍵集（closed set）＝ required ∪ optional ∪ conditional 容器。"""
    return (
        set(contract["required_fields"])
        | set(contract["optional_fields"])
        | set(contract["conditional_required"])
    )


def _is_int(v: Any) -> bool:
    return isinstance(v, numbers.Integral) and not isinstance(v, bool)


def _is_num(v: Any) -> bool:
    return isinstance(v, numbers.Real) and not isinstance(v, bool)


def _is_hex64(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and set(v.lower()) <= _HEX_CHARS


def _nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and len(v) > 0


def validate_event_import(
    records: Union[List[dict], pd.DataFrame],
    *,
    contract: Optional[dict] = None,
    source_bytes: Optional[bytes] = None,
) -> pd.DataFrame:
    """驗證匯入事件；全過 ⇒ 回正規化 DataFrame，否則 raise ContractValidationError。

    檢查順序（全部收集後一次 raise）：頂層鍵閉集 → 逐欄型別/枚舉 → ms 量級閘 →
    label_definition 子欄 → 條件必填 T8/T9/T10 → digest 對證（source_bytes 提供時）→
    批次級（空匯入/重複 event_id/direction 批內單值/二元缺類別）。
    """
    c = contract if contract is not None else load_event_import_contract()
    reasons = c["import_failure_reasons"]  # noqa: F841 —— 字面出處；本函式僅使用其中值
    req = c["required_fields"]
    opt = c["optional_fields"]
    cond = c["conditional_required"]
    allowed = allowed_top_level_keys(c)
    ms_min = int(c["ms_magnitude_min"])
    ms_max = ms_min * 1000  # 量級像 ns 亦拒（D2-3：單位錯即拒）

    if isinstance(records, pd.DataFrame):
        rows: List[dict] = records.to_dict("records")
    else:
        rows = [dict(r) for r in records]

    failures: List[Dict[str, Any]] = []

    def fail(row: int, event_id: Any, field: str, reason: str) -> None:
        failures.append({"row": row, "event_id": event_id, "field": field, "reason": reason})

    if len(rows) == 0:
        raise ContractValidationError([{"row": None, "event_id": None, "field": None, "reason": "empty_import"}])

    src_digest = hashlib.sha256(source_bytes).hexdigest() if source_bytes is not None else None

    normalized: List[dict] = []
    for i, r in enumerate(rows):
        eid = r.get("event_id")

        for k in r:
            if k not in allowed:
                fail(i, eid, k, "unknown_field")

        for name in req:
            if name not in r or r[name] is None:
                fail(i, eid, name, "missing_required_field")

        # ---- 逐欄型別/枚舉（缺欄者上面已記，這裡跳過缺值） ----
        def has(name: str) -> bool:
            return name in r and r[name] is not None

        for name in ("event_id", "symbol", "timeframe"):
            if has(name) and not _nonempty_str(r[name]):
                fail(i, eid, name, "type_error")

        if has("t0"):
            if not _is_int(r["t0"]):
                fail(i, eid, "t0", "type_error")
            elif not (ms_min <= int(r["t0"]) < ms_max):
                fail(i, eid, "t0", "invalid_timestamp_unit")

        k_off = 0
        if has("decision_offset_bars"):
            if not _is_int(r["decision_offset_bars"]) or int(r["decision_offset_bars"]) < req["decision_offset_bars"]["min"]:
                fail(i, eid, "decision_offset_bars", "type_error")
            else:
                k_off = int(r["decision_offset_bars"])
        else:
            k_off = int(req["decision_offset_bars"]["default"])

        for name in ("entry_price_semantic", "direction", "scenario"):
            if has(name) and r[name] not in req[name]["enum"]:
                fail(i, eid, name, "enum_violation")

        if has("label") and (not _is_int(r["label"]) or int(r["label"]) not in req["label"]["enum"]):
            fail(i, eid, "label", "enum_violation")

        ld_spec = req["label_definition"]["fields"]
        ld = None
        if has("label_definition"):
            if not isinstance(r["label_definition"], dict):
                fail(i, eid, "label_definition", "type_error")
            else:
                ld = dict(r["label_definition"])
                for sub in ("rule_id", "canonical_digest"):
                    if not _nonempty_str(ld.get(sub)):
                        fail(i, eid, f"label_definition.{sub}", "missing_required_field")
                w = ld.get("window")
                if not isinstance(w, dict) or not _is_int(w.get("horizon_bars")) or int(w["horizon_bars"]) < 1:
                    fail(i, eid, "label_definition.window", "missing_required_field")
                mode = ld.get("label_return_mode", ld_spec["label_return_mode"]["default"])
                if mode not in ld_spec["label_return_mode"]["enum"]:
                    fail(i, eid, "label_definition.label_return_mode", "enum_violation")
                ld["label_return_mode"] = mode

        ck_spec = req["control_kind"]
        if has("control_kind"):
            v = r["control_kind"]
            if v not in ck_spec["enum"]:
                fail(i, eid, "control_kind", "enum_violation")
            elif v not in ck_spec["accepted"]:
                fail(i, eid, "control_kind", ck_spec["rejected_with_reason"][v])

        if has("source_file_digest") and not _is_hex64(r["source_file_digest"]):
            fail(i, eid, "source_file_digest", "type_error")
        if has("data_snapshot_digest") and not _nonempty_str(r["data_snapshot_digest"]):
            fail(i, eid, "data_snapshot_digest", "type_error")
        if src_digest is not None and has("source_file_digest") and _is_hex64(r["source_file_digest"]):
            if r["source_file_digest"].lower() != src_digest:
                fail(i, eid, "source_file_digest", "digest_mismatch")

        # ---- 選填欄 ----
        if has("label_value") and not _is_num(r["label_value"]):
            fail(i, eid, "label_value", "label_value_type_error")
        if has("counterexample_kind"):
            v = r["counterexample_kind"]
            if v == "unclassifiable":
                fail(i, eid, "counterexample_kind", "counterexample_kind_not_importable")
            elif v not in opt["counterexample_kind"]["enum"]:
                fail(i, eid, "counterexample_kind", "enum_violation")
        if has("kind_source") and r["kind_source"] not in opt["kind_source"]["enum"]:
            fail(i, eid, "kind_source", "enum_violation")
        if has("meta") and not isinstance(r["meta"], dict):
            fail(i, eid, "meta", "type_error")

        # ---- 條件必填 ----
        if has("reference_symbols"):
            rs = r["reference_symbols"]
            if not isinstance(rs, list) or len(rs) == 0:
                fail(i, eid, "reference_symbols", "conditional_required_missing")
            else:
                for j, item in enumerate(rs):
                    if not isinstance(item, dict):
                        fail(i, eid, f"reference_symbols[{j}]", "conditional_required_missing")
                        continue
                    for sub in cond["reference_symbols"]["item_fields"]:
                        if not _nonempty_str(str(item.get(sub) or "")):
                            fail(i, eid, f"reference_symbols[{j}].{sub}", "conditional_required_missing")

        if r.get("event_origin") == "model":
            sm = r.get("source_model")
            if not isinstance(sm, dict):
                fail(i, eid, "source_model", "conditional_required_missing")
            else:
                ok = True
                for sub in cond["source_model"]["item_fields"]:
                    if sm.get(sub) in (None, ""):
                        fail(i, eid, f"source_model.{sub}", "conditional_required_missing")
                        ok = False
                if ok:
                    aa = sm.get("available_at")
                    if not _is_int(aa) or not (ms_min <= int(aa) < ms_max):
                        fail(i, eid, "source_model.available_at", "invalid_timestamp_unit")
                    elif has("t0") and _is_int(r["t0"]) and has("timeframe") and _nonempty_str(r["timeframe"]):
                        tf_s = TIMEFRAME_SECONDS.get(r["timeframe"])
                        if tf_s is None:
                            fail(i, eid, "timeframe", "type_error")
                        else:
                            # 名目 decision_at＝t0 − k×TF_ms（誠實邊界 c；對齊層以實際 bar 複驗）
                            decision_at_nominal = int(r["t0"]) - k_off * tf_s * 1000
                            if int(aa) > decision_at_nominal:
                                fail(i, eid, "source_model.available_at", "research_only")

        if r.get("event_shape") == "interval":
            iv = r.get("event_interval")
            if not isinstance(iv, dict):
                fail(i, eid, "event_interval", "conditional_required_missing")
            else:
                for sub in cond["event_interval"]["item_fields"]:
                    if iv.get(sub) is None:
                        fail(i, eid, f"event_interval.{sub}", "conditional_required_missing")

        out = dict(r)
        out["decision_offset_bars"] = k_off
        if ld is not None:
            out["label_definition"] = ld
        normalized.append(out)

    # ---- 批次級 ----
    ids = [r.get("event_id") for r in rows if r.get("event_id") is not None]
    seen: set = set()
    for i, e in enumerate(ids):
        if e in seen:
            fail(i, e, "event_id", "duplicate_event_id")
        seen.add(e)

    directions = {r.get("direction") for r in rows if r.get("direction") in req["direction"]["enum"]}
    if len(directions) > 1:
        fail(None, None, "direction", "direction_mixed_in_batch")

    labels = {int(r["label"]) for r in rows if _is_int(r.get("label")) and int(r.get("label")) in (0, 1)}
    if labels and labels != {0, 1}:
        fail(None, None, "label", "missing_control_group")

    if failures:
        raise ContractValidationError(failures)

    return pd.DataFrame(normalized)
