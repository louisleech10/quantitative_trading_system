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
from typing import Any, Dict, List, Mapping, Optional, Union

import pandas as pd

from momentum.core.constants import TIMEFRAME_SECONDS

_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts" / "event_import_contract.json"
_HEX_CHARS = set("0123456789abcdef")

# mutation-guard seam（M12）：T9 availability 檢查之開關。正式路徑恆 True；
# test_mutation_guard.py 以 monkeypatch 置 False 證明「檢查移除 ⇒ B1.0 條件必填斷言紅」。
_T9_AVAILABILITY_ENFORCED = True


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


def flatten_receipt_schema(schema: Mapping[str, Any]) -> List[str]:
    """把 namespace-aware 之 `receipt_schema` 攤成保序之 `["<namespace>.<欄名>", ...]`。

    GAP-3 UX Task 1.1（SPEC R11 ⑧(a)）：**唯一** exported traversal——runtime validator
    與驗收共用同一函式參考，不得各寫一份。改前（欄名 list）與改後（{欄名: 型別} dict）
    兩種形態皆吃，故「改前 vs 改後」之 prefix 相等斷言可用同一 traversal 產生兩側。

    順序＝namespace 之插入序 × 該 namespace 內欄名之插入序（Python 3.7+ dict 保序）。
    """
    out: List[str] = []
    for ns, fields in schema.items():
        if isinstance(fields, Mapping):
            names: List[str] = list(fields.keys())
        elif isinstance(fields, (list, tuple)):
            names = [str(n) for n in fields]
        else:
            raise ValueError(
                f"receipt_schema['{ns}'] 須為 Mapping（改後）或 list（改前），實得 {type(fields).__name__}"
            )
        out.extend(f"{ns}.{n}" for n in names)
    return out


def receipt_type_ok(type_decl: str, value: Any) -> bool:
    """依契約之型別字面判定 receipt 欄位值是否合法（封閉集合；未知字面 ⇒ raise，fail-closed）。

    GAP-3 UX Task 1.1（SPEC R11 ⑧(c)(e)）：判定一律 `type(v) is int`，**不用 `isinstance`**
    ——`bool ⊂ int`，`True` 會通過 `isinstance` 檢查卻序列化成 `true` 而非 `1`，
    使 §G S-9 之位元組綁定失效（CODEX-R17-P1-02）。
    本函式為 validator 與驗收之**同一函式參考**，不得複製其邏輯。
    """
    if type_decl == "str":
        return type(value) is str
    if type_decl == "bool":
        return type(value) is bool
    if type_decl == "int":
        return type(value) is int
    if type_decl == "int>=0":
        return type(value) is int and value >= 0
    if type_decl == "Mapping[str,int>=0]":
        if type(value) is not dict:
            return False
        return all(
            type(k) is str and type(v) is int and v >= 0
            for k, v in value.items()
        )
    raise ValueError(f"receipt_schema 出現未知型別字面: {type_decl!r}（fail-closed，不得放行）")


def validate_receipt_namespace(
    namespace: str,
    values: Mapping[str, Any],
    *,
    contract: Optional[dict] = None,
) -> None:
    """驗證某個 receipt namespace 之落檔值；任一不合即 raise ContractValidationError（fail-closed）。

    GAP-3 UX Task 1.1：型別登記若沒有 runtime 生效點，就只是「登記了但沒生效」。
    本函式即該生效點，與驗收共用 `flatten_receipt_schema` / `receipt_type_ok`。
    """
    c = contract if contract is not None else load_event_import_contract()
    schema = c["receipt_schema"]
    if namespace not in schema:
        raise ContractValidationError(
            [{"row": None, "event_id": None, "field": namespace, "reason": "unknown_field"}]
        )
    declared = schema[namespace]
    if not isinstance(declared, Mapping):
        raise ValueError(
            f"receipt_schema['{namespace}'] 尚未升為 typed dict（migration 未完成，fail-closed）"
        )

    failures: List[Dict[str, Any]] = []
    for name in declared:
        if name not in values:
            failures.append(
                {"row": None, "event_id": None, "field": f"{namespace}.{name}",
                 "reason": "missing_required_field"}
            )
        elif not receipt_type_ok(declared[name], values[name]):
            failures.append(
                {"row": None, "event_id": None, "field": f"{namespace}.{name}", "reason": "type_error"}
            )
    for name in values:
        if name not in declared:
            failures.append(
                {"row": None, "event_id": None, "field": f"{namespace}.{name}", "reason": "unknown_field"}
            )
    if failures:
        raise ContractValidationError(failures)


def _is_int(v: Any) -> bool:
    return isinstance(v, numbers.Integral) and not isinstance(v, bool)


def _is_num(v: Any) -> bool:
    return isinstance(v, numbers.Real) and not isinstance(v, bool)


def _is_hex64(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and set(v.lower()) <= _HEX_CHARS


def _nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and len(v) > 0


class T0UnitUndetectedError(ValueError):
    """t0 單位判不出（GAP-3 UX Task 1.4）。`reason` 字面＝契約既有 `invalid_timestamp_unit`。"""

    reason = "invalid_timestamp_unit"

    def __init__(self, value: Any):
        self.value = value
        super().__init__(f"invalid_timestamp_unit: 無法判定 t0 單位（值={value!r}）；不猜預設值")


def detect_t0_unit_ms(value: Any, *, contract: Optional[dict] = None) -> int:
    """t0 單位偵測（GAP-3 UX Task 1.4）——CSV 與 JSON **兩條路徑共用之唯一 exported 函式**。

    判定只有**一條**門檻來源：契約之 `ms_magnitude_min`（禁另立第二條判定路徑）。
    合法 ms 帶＝``[ms_min, ms_min*1000)``；秒級帶由**同一門檻導出**＝「×1000 後落在 ms 帶」。
    兩帶依建構互斥（``v >= ms_min`` 與 ``v*1000 < ms_min*1000`` 不可能同時成立）
    ⇒ 不存在「同時可解為 ms 與秒」之值，無須猜。

    Args:
        value: t0 原始值（CSV 已由 `_csv_rows_to_records` 之 JSON 解碼轉為 int）。
        contract: 契約 dict（省略則讀 SoT）。

    Returns:
        毫秒整數（ms 帶原樣回傳；秒帶 ×1000）。

    Raises:
        T0UnitUndetectedError: 非整數、或兩帶皆不落入（含落在門檻兩側之模糊值）。**不得猜預設值。**
    """
    c = contract if contract is not None else load_event_import_contract()
    ms_min = int(c["ms_magnitude_min"])
    ms_max = ms_min * 1000  # 量級像 ns 亦拒（D2-3：單位錯即拒）
    if not _is_int(value):
        raise T0UnitUndetectedError(value)
    v = int(value)
    if ms_min <= v < ms_max:
        return v
    if ms_min <= v * 1000 < ms_max:
        return v * 1000
    raise T0UnitUndetectedError(value)


def _digest_matches(actual_hex: str, declared_digest: Any) -> bool:
    """digest 比對之**唯一**判準（大小寫不敏感、非 hex64 一律不符）。"""
    if not _is_hex64(declared_digest):
        return False
    return actual_hex == str(declared_digest).lower()


#: Task 1.2 對映層之 reason 具名出口（鍵＝呼叫端用之語意名，值＝契約字面）。
#: 🔴 值必須落在契約 `import_failure_reasons` 封閉集合內，由 `mapping_failure_reasons()` fail-closed 對證
#: ⇒ api 層只引用鍵，不複列字面（R7）。
_MAPPING_REASON_KEYS = {
    "mapping_missing": "column_mapping_missing",
    "column_not_found": "column_not_found_in_file",
    "label_not_binary": "label_column_not_binary",
}


def mapping_failure_reasons(contract: Optional[dict] = None) -> Dict[str, str]:
    """對映層（Task 1.2）之 reason 字面出口；任一字面不在契約封閉集合內即 raise（漂移 fail-closed）。"""
    c = contract if contract is not None else load_event_import_contract()
    closed = set(c["import_failure_reasons"])
    missing = [v for v in _MAPPING_REASON_KEYS.values() if v not in closed]
    if missing:
        raise ValueError(f"對映層 reason 不在契約 import_failure_reasons 封閉集合內：{missing}")
    return dict(_MAPPING_REASON_KEYS)


def normalize_t0_units(records: List[dict], *, contract: Optional[dict] = None) -> None:
    """就地把**可判定單位**之 `t0` 正規化為毫秒（`detect_t0_unit_ms` 之唯一批次呼叫點）。

    判不出者**原樣保留**，交由 `validate_event_import` 之量級閘以既有 `invalid_timestamp_unit`
    逐列拒（**不猜預設值**）。CSV 與 JSON 兩路徑皆經此函式 ⇒ 單位判定不會各自演化。
    """
    c = contract if contract is not None else load_event_import_contract()
    for rec in records:
        if not isinstance(rec, dict) or rec.get("t0") is None:
            continue
        try:
            rec["t0"] = detect_t0_unit_ms(rec["t0"], contract=c)
        except T0UnitUndetectedError:
            continue


def verify_source_digest(source_bytes: bytes, declared_digest: Any) -> bool:
    """比對宣告之 `source_file_digest` 與來源檔位元組（GAP-3 UX Task 1.3）。

    🔴 **匯入時不重算 canonical 序列化，只比對**——匯入端拿到的是使用者可能已在 Excel 動過的檔，
    重算會把「使用者改過」與「序列化不一致」混為一談（SPEC Task 1.3「時序」定案）。
    """
    return _digest_matches(hashlib.sha256(source_bytes).hexdigest(), declared_digest)


#: Task 1.8 之異質維度（列間須單值，除非 `batch_defaults` 已涵蓋）。
_HETEROGENEITY_DIMENSIONS = ("direction", "scenario", "label_definition")
#: Task 1.8：訊息列出之衝突列號上限（SPEC「列出前 3 個衝突列號與欄名」）。
_HETEROGENEITY_MAX_REPORTED = 3


def _dimension_key(value: Any) -> str:
    """異質比對用之穩定鍵：dict／list 以排序後 JSON 表示，純量以 repr。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=repr)


def validate_event_import(
    records: Union[List[dict], pd.DataFrame],
    *,
    contract: Optional[dict] = None,
    source_bytes: Optional[bytes] = None,
    batch_defaults: Optional[Mapping[str, Any]] = None,
    enforce_batch_homogeneity: bool = False,
) -> pd.DataFrame:
    """驗證匯入事件；全過 ⇒ 回正規化 DataFrame，否則 raise ContractValidationError。

    檢查順序（全部收集後一次 raise）：頂層鍵閉集 → 逐欄型別/枚舉 → ms 量級閘 →
    label_definition 子欄 → 條件必填 T8/T9/T10 → digest 對證（source_bytes 提供時）→
    批次級（空匯入/重複 event_id/direction 批內單值/二元缺類別/異質列）。

    Args:
        batch_defaults: 批次預設（Task 1.8）；已指定之維度視為已涵蓋，不再判異質。
        enforce_batch_homogeneity: 是否啟用 Task 1.8 之異質列拒收。
            🔴 **預設 False，只由使用者匯入路徑（`EventSamplePipeline.validate`）開啟**。
            理由：SPEC Task 1.8 之標的是「**使用者**宣告之一批 CSV／JSON」；
            平台產生器（`generator.py`）之 multi-label 批次**刻意**逐列帶不同 `label_definition`
            （每個 label_id 一組），是另一個 producer，套用同一條會把既有功能整批擋掉。
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

    def fail(row: int, event_id: Any, field: str, reason: str, message: Optional[str] = None) -> None:
        entry: Dict[str, Any] = {"row": row, "event_id": event_id, "field": field, "reason": reason}
        if message is not None:
            entry["message"] = message
        failures.append(entry)

    if len(rows) == 0:
        raise ContractValidationError([{"row": None, "event_id": None, "field": None, "reason": "empty_import"}])

    # ---- 批次預設（Task 1.8）：**只填補缺值，絕不覆蓋列自帶值** ----
    # CSV 與 JSON 兩路徑共用之唯一套用點（V-3 之 AST oracle 涵蓋面）。
    if batch_defaults:
        for k in batch_defaults:
            if k not in allowed:
                fail(None, None, k, "unknown_field")
        for r in rows:
            for k, v in batch_defaults.items():
                if v is None or k not in allowed:
                    continue
                if r.get(k) is None:
                    r[k] = v

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
            # 比對判準唯一實作＝`_digest_matches`（`verify_source_digest` 之同一判準；
            # 此處用已預算之 src_digest，避免逐列重算整份來源檔 sha256）
            if not _digest_matches(src_digest, r["source_file_digest"]):
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
                        v = item.get(sub)
                        if v is None or v == "":
                            fail(i, eid, f"reference_symbols[{j}].{sub}", "conditional_required_missing")
                        elif not _nonempty_str(v):  # 逐欄驗型、禁 coercion（CODEX-R1-P1-03）
                            fail(i, eid, f"reference_symbols[{j}].{sub}", "type_error")

        if r.get("event_origin") == "model":
            sm = r.get("source_model")
            if not isinstance(sm, dict):
                fail(i, eid, "source_model", "conditional_required_missing")
            else:
                ok = True
                for sub in cond["source_model"]["item_fields"]:
                    v = sm.get(sub)
                    if v is None or v == "":
                        fail(i, eid, f"source_model.{sub}", "conditional_required_missing")
                        ok = False
                    elif sub != "available_at" and not _nonempty_str(v):  # 逐欄驗型（CODEX-R1-P1-03）
                        fail(i, eid, f"source_model.{sub}", "type_error")
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
                            if _T9_AVAILABILITY_ENFORCED and int(aa) > decision_at_nominal:
                                fail(i, eid, "source_model.available_at", "research_only")

        if r.get("event_shape") == "interval":
            iv = r.get("event_interval")
            if not isinstance(iv, dict):
                fail(i, eid, "event_interval", "conditional_required_missing")
            else:
                for sub in cond["event_interval"]["item_fields"]:
                    if iv.get(sub) is None:
                        fail(i, eid, f"event_interval.{sub}", "conditional_required_missing")
                # 逐欄驗型（CODEX-R1-P1-03）：start/end int ms＋量級閘＋start<end；endpoints_inclusive={start:bool,end:bool}
                s_, e_ = iv.get("start"), iv.get("end")
                for nm, v in (("start", s_), ("end", e_)):
                    if v is not None:
                        if not _is_int(v):
                            fail(i, eid, f"event_interval.{nm}", "type_error")
                        elif not (ms_min <= int(v) < ms_max):
                            fail(i, eid, f"event_interval.{nm}", "invalid_timestamp_unit")
                if _is_int(s_) and _is_int(e_) and not int(s_) < int(e_):
                    fail(i, eid, "event_interval", "type_error")
                inc = iv.get("endpoints_inclusive")
                if inc is not None and not (
                    isinstance(inc, dict) and set(inc) == {"start", "end"}
                    and all(isinstance(inc[k], bool) for k in ("start", "end"))
                ):
                    fail(i, eid, "event_interval.endpoints_inclusive", "type_error")

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

    # ---- 異質列顯式拒收（GAP-3 UX Task 1.8／A-5′） ----
    # 列間於 direction／scenario／label_definition 不一致 ⇒ 拒收。
    # `batch_defaults` 已於上方**填補缺值**（不覆蓋列自帶值）⇒ 「已涵蓋」之維度在此自然同質；
    # 反之列**自帶**互斥值時 defaults 不得掩蓋（TODO 邊界②：指定 scenario='A' 而列間混 A／B ⇒ 落檔數 0）。
    # 🔴 **不自動分批**、**不靜默取第一列之值套用全批**：只指出衝突並拒。
    # 🔴 比對對象＝**正規化後**之列（`normalized`，與 `rows` 逐列對齊）而非原始列：
    #    原始列之 `label_definition` 可能有的填了 `label_return_mode`、有的沒填（缺者取契約預設），
    #    拿原始列比會把「預設值未寫出」誤判成異質，擋掉完全同質的批次（既有測試抓到）。
    for dim in (_HETEROGENEITY_DIMENSIONS if enforce_batch_homogeneity else ()):
        present = [(i, r[dim]) for i, r in enumerate(normalized) if dim in r and r[dim] is not None]
        if len(present) < 2:
            continue
        baseline_key = _dimension_key(present[0][1])
        conflicts = [i for i, v in present[1:] if _dimension_key(v) != baseline_key]
        if not conflicts:
            continue
        reported = conflicts[:_HETEROGENEITY_MAX_REPORTED]
        msg = (
            f"heterogeneous_rows_in_batch: 欄 {dim!r} 列間不一致；"
            f"前 {len(reported)} 個衝突列號＝{reported}（共 {len(conflicts)} 列與首列 {present[0][0]} 不同）。"
            f"不自動分批、不套用第一列之值；請拆批或以 batch_defaults 指定 {dim!r}"
        )
        for row_idx in reported:
            fail(row_idx, rows[row_idx].get("event_id"), dim, "heterogeneous_rows_in_batch", msg)

    if failures:
        raise ContractValidationError(failures)

    return pd.DataFrame(normalized)
