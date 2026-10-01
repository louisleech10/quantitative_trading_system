"""FF-STAT Task 2.3／2.4：逐欄穩定點遮罩、死欄純函式與欄集合差異（docs/FFSTAT_SPEC.md v43 §C）。

本模組只放純函式：不讀檔、不算指標、不記 log。呼叫端（L1 輸出點、L6.5、L3／L7 死欄過濾、收據）
以本模組之結果套用遮罩或判定；遮罩只作用於輸出，不改任何計算本身（SPEC §C「逐欄穩定點」、R6）。
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

# 設定 hash 納入之預熱政策版本（SPEC §C「公開域預熱」；改前快取一律未命中）
WARMUP_POLICY = "per_column_stable_v1"

# `output_start_source` 之封閉值（SPEC §C「未填起始日」紀錄與顯示）
OUTPUT_START_SOURCES: Tuple[str, ...] = ("user", "per_column")

# 欄集合差異原因之封閉值（SPEC Task 2.3 ⑦；其他值於 digest 與核可比對前即拒收）
DELTA_REASONS: Tuple[str, ...] = ("nan_rate_rule", "stable_samples_below_min", "warmup_restored")  # v49 增第三值

# 死欄門檻（SPEC §C：門檻為呼叫端參數，各保原值）
L3_DEAD_NAN_RATE = 0.9
L3_MIN_EFFECTIVE_N = 30
L7_MIN_VALID_SAMPLES_DEFAULT = 100


class StableMaskError(ValueError):
    """輸出點契約不成立（缺參數字典、缺 period_keys、宣告與回傳欄集合不符）：輸出前 fail-closed。

    訊息須列引擎、輸出欄與缺少之鍵（SPEC §C「L1 輸出點契約」）。"""


class DeltaReasonError(ValueError):
    """欄集合差異之原因值不在 `DELTA_REASONS`（SPEC Task 2.3 ⑦）。"""


@dataclass(frozen=True)
class OutputPointSpec:
    """L1 輸出點契約之一欄（SPEC §C v38／v39）。

    params：產生該欄之那次計算呼叫之已解析參數字典（多輸出指標之各欄共用同一字典）。
    period_keys：倍數表對該指標登記之封閉鍵集合（完整遞移週期集合）；無參數指標為空。
    upstream：同一引擎內由其他輸出再算出之欄，其上游輸出欄名（無則空）。
    window：同引擎衍生步驟之窗長（逐點聚合為 None）。
    """

    engine: str
    indicator: str
    column: str
    params: Mapping[str, Any]
    period_keys: Tuple[str, ...]
    upstream: Tuple[str, ...] = ()
    window: Optional[int] = None


@dataclass(frozen=True)
class DeadDecision:
    """死欄純函式之判定結果（SPEC §C 死欄判定）。"""

    dead: bool
    reason: Optional[str]
    nan_rate: float
    valid_count: int
    constant: Any = None  # 有限值之相異值數 < 2（含無有限值）；獨立於 reason 之判定順序，供診斷分類


def first_finite_index(values: np.ndarray) -> Optional[int]:
    """第一個有限值之列索引；全非有限值回 None。"""
    finite = np.isfinite(np.asarray(values, dtype=np.float64))
    if not finite.any():
        return None
    return int(np.argmax(finite))


def l1_origin(inputs: np.ndarray) -> Optional[int]:
    """L1 遮罩之 origin：該指標全部輸入欄（二維：列×輸入欄）皆為有限值之第一列；無則 None（SPEC §C L1 遮罩）。"""
    arr = np.asarray(inputs, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr[:, None]
    all_finite = np.isfinite(arr).all(axis=1)
    return int(np.argmax(all_finite)) if all_finite.any() else None


def _k_error(spec: OutputPointSpec, detail: str) -> StableMaskError:
    return StableMaskError(f"L1 輸出點契約不成立：engine={spec.engine} column={spec.column} "
                           f"indicator={spec.indicator}：{detail}")


def instance_k(spec: OutputPointSpec, table: Mapping[str, Mapping[str, Any]],
               upstream_k: Optional[Mapping[str, int]] = None) -> int:
    """逐計算呼叫之 K（SPEC §C v37／v39）。

    L1 原始輸出：ceil(max(params[k] for k in period_keys) × 表之採用係數)；無參數者取表內登記之 K。
    同引擎衍生輸出：上游 K 之最大者＋window−1（窗型）或上游 K 之最大者（逐點聚合）。
    倍數表缺條目、參數字典缺任一登記鍵、衍生輸出缺上游 K ⇒ StableMaskError（列引擎、欄、缺鍵）。
    累積型（warmup_class＝cumulative）回 0：無收斂點、不另遮（SPEC §C「累積型」）。
    """
    if spec.upstream:
        known = dict(upstream_k or {})
        lacking = [name for name in spec.upstream if name not in known]
        if lacking:
            raise _k_error(spec, f"缺上游輸出之 K：{lacking}")
        base = max(int(known[name]) for name in spec.upstream)
        return base + (int(spec.window) - 1 if spec.window is not None else 0)
    entry = table.get(spec.indicator)
    if entry is None:
        raise _k_error(spec, "倍數表查無此指標（不得套後備係數）")
    if entry.get("warmup_class") == "cumulative":
        return 0
    keys = tuple(spec.period_keys)
    lacking = [key for key in keys if key not in spec.params]
    if lacking:
        raise _k_error(spec, f"參數字典缺 period_keys：{lacking}")
    try:
        if not keys:
            check_variant(entry, spec.params, keys)  # v47：無參數指標之非週期參數（如 MAMA fastlimit）亦須已量測
            k = entry.get("k")
            if not isinstance(k, int) or k <= 0:
                raise _k_error(spec, "無參數指標缺表內登記之 k")
            return k
        k = k_for_params(entry, spec.params, keys)
    except UnmeasuredVariantError as exc:
        raise UnmeasuredVariantError(
            f"L1 輸出點契約不成立：engine={spec.engine} column={spec.column} indicator={spec.indicator}：{exc}"
        ) from exc
    if k is None:
        raise _k_error(spec, "倍數表條目缺 recommended_factor")
    return k


class UnmeasuredVariantError(StableMaskError):
    """呼叫之非週期參數組合（如 MA 之 matype、MAMA 之 fastlimit）未經量測（SPEC v47，R5 精神：不以推估值放行）。"""


def _fmt_param(value: Any) -> str:
    if isinstance(value, (list, tuple, np.ndarray)):
        return "[" + "|".join(_fmt_param(v) for v in list(value)) + "]"  # r32 codex P2-03：序列參數（MAVP periods）
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number.is_integer() else repr(number)


def _period_value(value: Any) -> float:
    """週期參數之數值：序列（如 MAVP 之 periods 陣列）取最大者（SPEC §C：K 取 period_keys 各值之最大）。"""
    if isinstance(value, (list, tuple, np.ndarray)):
        return max(float(v) for v in list(value))
    return float(value)


def canonical_params(params: Mapping[str, Any], defaults: Optional[Mapping[str, Any]] = None) -> str:
    """參數之正規鍵（SPEC v47）：條目登記之預設值（``param_defaults``）疊上呼叫參數，依鍵名升序以 ``鍵=值``
    逗號連接（整數值寫整數字面）。v46 只取 period_keys ⇒ 非週期參數不同之組合共用同一鍵（r31 codex P1-02）。"""
    merged = {**dict(defaults or {}), **dict(params)}
    return ",".join(f"{k}={_fmt_param(merged[k])}" for k in sorted(merged))


def variant_key(params: Mapping[str, Any], keys: Sequence[str], defaults: Optional[Mapping[str, Any]] = None) -> str:
    """非週期參數之正規鍵（量測變體）：預設值疊上呼叫之非週期參數。"""
    merged = {**dict(defaults or {}), **{k: v for k, v in params.items() if k not in set(keys)}}
    return canonical_params({k: v for k, v in merged.items() if k not in set(keys)})


def check_variant(entry: Mapping[str, Any], params: Mapping[str, Any], keys: Sequence[str]) -> None:
    """呼叫之非週期參數組合須在條目之 ``variants``（已量測者）內，否則 ``UnmeasuredVariantError``。"""
    variants = entry.get("variants")
    if variants is None:
        return
    key = variant_key(params, keys, entry.get("param_defaults"))
    if key not in variants:
        raise UnmeasuredVariantError(f"非週期參數組合 {{{key}}} 未量測（已量測：{list(variants)}）")


def k_for_params(entry: Mapping[str, Any], params: Mapping[str, Any], keys: Sequence[str]) -> Optional[int]:
    """有參數條目之 K（SPEC v46／v47，R10 實測根數優先）：先驗非週期參數組合已量測（否則拋錯）；
    ``k_by_params``（全參數正規鍵）查得者取其值；查無才 ceil(max(period_keys 值) × recommended_factor)；
    條目無係數回 None。"""
    check_variant(entry, params, keys)
    measured = (entry.get("k_by_params") or {}).get(canonical_params(params, entry.get("param_defaults")))
    if measured is not None:
        return int(measured)
    factor = entry.get("recommended_factor")
    if factor is None:
        return None
    return int(math.ceil(max(_period_value(params[k]) for k in keys) * float(factor)))


def apply_l1_mask(values: np.ndarray, origin: Optional[int], k: int) -> np.ndarray:
    """回傳新陣列：origin 之前與 `[origin, origin+k)` 設為 NaN；origin 為 None 則全 NaN。不改輸入。"""
    out = np.array(values, dtype=np.float64, copy=True)
    if origin is None:
        out[:] = np.nan
        return out
    out[: int(origin) + max(int(k), 0)] = np.nan
    return out


def mask_incomplete_window(output: np.ndarray, input_values: np.ndarray, window: int) -> np.ndarray:
    """第①類（固定窗而以不完整窗出值，如 L6.5 縮尾）：輸出自輸入首個有限值起 `window−1` 列設 NaN（只遮罩）。"""
    out = np.array(output, dtype=np.float64, copy=True)
    first = first_finite_index(input_values)
    if first is None:
        out[:] = np.nan
        return out
    out[: first + max(int(window) - 1, 0)] = np.nan
    return out


def mask_incomplete_window_by_input_2d(output: np.ndarray, step_input: np.ndarray, window: int) -> np.ndarray:
    """ICPOSTLEAK Task 1.1（docs/ICPOSTLEAK_SPEC.md §C）：rank／zscore／gaussian 之第①類遮罩，錨點＝**步驟輸入**。

    逐欄 `cut = step_input 該欄首個有限值列 + window − 1`，回傳 `output` 之副本並將 `[0, cut)` 設 NaN；
    `step_input` 該欄全無有限值 ⇒ 該欄全 NaN；`cut` 超過列數 ⇒ 全欄 NaN。`output`／`step_input` 須同形二維。
    不改 `output` 本身（回傳新陣列，dtype 同 `output`）。"""
    raise NotImplementedError("ICPOSTLEAK Task 1.1")


def mask_incomplete_window_inplace(values: np.ndarray, window: int) -> np.ndarray:
    """第①類之二維（列×欄）就地形：逐欄自首個有限值起 `window−1` 列（及其前）設 NaN；回傳同一陣列。

    用於縮尾：其輸出之 NaN 位置＝輸入之 NaN 位置（界線未定之列保留原值、NaN 寫回），故以輸出本身之首個
    有限值即輸入之首個有限值。全無有限值之欄不變（已全 NaN）。"""
    arr = values if values.ndim == 2 else values.reshape(-1, 1)
    if arr.size == 0 or int(window) <= 1:
        return values
    finite = np.isfinite(arr)
    has = finite.any(axis=0)
    first = np.where(has, np.argmax(finite, axis=0), arr.shape[0])
    cut = np.minimum(first + int(window) - 1, arr.shape[0])
    arr[np.arange(arr.shape[0])[:, None] < cut[None, :]] = np.nan
    return values


def mask_pointwise_prefix(output: np.ndarray, inputs: Sequence[np.ndarray]) -> np.ndarray:
    """第④類（逐點或跨欄運算對 NaN 給有限值）：輸出於各輸入首個有限值之最大者之前設 NaN；之後不動。"""
    out = np.array(output, dtype=np.float64, copy=True)
    firsts = [first_finite_index(values) for values in inputs]
    if not firsts or any(first is None for first in firsts):
        out[:] = np.nan
        return out
    out[: max(firsts)] = np.nan
    return out


def calibration_rows_no_start(values: np.ndarray, n: int) -> Optional[Tuple[int, int]]:
    """無起始日時該欄之校準列：最早 N 個有限值所在之 (首列, 第 N 個有限值之列)（含兩端）；不足 N 回 None。"""
    idx = np.flatnonzero(np.isfinite(np.asarray(values, dtype=np.float64)))
    if n <= 0 or idx.size < n:
        return None
    return int(idx[0]), int(idx[n - 1])


def dead_column_decision(values: np.ndarray, *, nan_rate_threshold: Optional[float], min_valid: int) -> DeadDecision:
    """L3 與 L7、frame 與 CGSA 共用之死欄純函式（SPEC §C v33／v34）。

    NaN 率之分母＝自首個有限值起之列數（開頭 NaN 段不計，與遮罩長度無關）；有效樣本數＝有限值個數；
    常數＝有限值之相異值數 < 2。`nan_rate_threshold` 為 None 表不判 NaN 率（L7）。

    `values` 為二維（列×欄）時逐欄向量化判定：回傳之 DeadDecision 各欄位為長度＝欄數之陣列
    （dead：bool、reason：object〔None 或原因字串〕、nan_rate：float、valid_count：int），判定規則同一維。
    """
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim == 2:
        return _dead_columns_2d(arr, nan_rate_threshold, int(min_valid))
    finite = np.isfinite(arr)
    valid = int(finite.sum())
    first = first_finite_index(arr)
    span = 0 if first is None else arr.size - first
    nan_rate = 1.0 if span == 0 else float(span - valid) / float(span)
    constant = bool(np.unique(arr[finite]).size < 2)
    if nan_rate_threshold is not None and nan_rate > float(nan_rate_threshold):
        return DeadDecision(True, "nan_rate_rule", nan_rate, valid, constant)
    if valid < int(min_valid):
        return DeadDecision(True, "stable_samples_below_min", nan_rate, valid, constant)
    if constant:
        return DeadDecision(True, "constant", nan_rate, valid, constant)
    return DeadDecision(False, None, nan_rate, valid, constant)


def _dead_columns_2d(arr: np.ndarray, nan_rate_threshold: Optional[float], min_valid: int) -> DeadDecision:
    """``dead_column_decision`` 之二維向量化形（逐欄同一規則與同一判定順序）。"""
    n_rows, n_cols = arr.shape
    finite = np.isfinite(arr)
    valid = finite.sum(axis=0).astype(np.int64)
    first = np.where(valid > 0, np.argmax(finite, axis=0), n_rows)
    span = n_rows - first
    with np.errstate(invalid="ignore", divide="ignore"):
        nan_rate = np.where(span > 0, (span - valid) / np.maximum(span, 1), 1.0).astype(np.float64)
        masked = np.where(finite, arr, np.nan)
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            col_min = np.nanmin(masked, axis=0) if n_rows else np.full(n_cols, np.nan)
            col_max = np.nanmax(masked, axis=0) if n_rows else np.full(n_cols, np.nan)
    constant = ~(col_min < col_max)  # 無有限值（NaN）或全同值
    reason = np.full(n_cols, None, dtype=object)
    dead = np.zeros(n_cols, dtype=bool)
    rules = []
    if nan_rate_threshold is not None:
        rules.append(("nan_rate_rule", nan_rate > float(nan_rate_threshold)))
    rules += [("stable_samples_below_min", valid < min_valid), ("constant", constant)]
    for name, hit in rules:
        new = hit & ~dead
        reason[new] = name
        dead |= hit
    return DeadDecision(dead, reason, nan_rate, valid, constant)


def _utf8_sorted(names: Sequence[str]) -> list:
    return sorted(set(names), key=lambda s: s.encode("utf-8"))


def column_set_sha256(columns: Sequence[str]) -> str:
    """欄集合 sha256：欄名依 UTF-8 位元組升序去重、以 `\\n` 連接之 UTF-8 位元組（無結尾換行）（SPEC Task 2.3 ⑦）。"""
    return hashlib.sha256("\n".join(_utf8_sorted(columns)).encode("utf-8")).hexdigest()


def column_set_delta(before: Sequence[str], after: Sequence[str], reasons: Mapping[str, str]) -> Dict[str, Any]:
    """欄集合差異物件 `{"added":[…],"removed":[…],"reasons":{欄名:原因}}`（兩陣列依欄名 UTF-8 位元組升序）。

    每個差異欄皆須有原因且原因 ∈ `DELTA_REASONS`，否則 DeltaReasonError；無差異時三者皆空。
    """
    before_set, after_set = set(before), set(after)
    added = _utf8_sorted(after_set - before_set)
    removed = _utf8_sorted(before_set - after_set)
    out_reasons: Dict[str, str] = {}
    for name in added + removed:
        reason = reasons.get(name)
        if reason not in DELTA_REASONS:
            raise DeltaReasonError(f"欄集合差異欄 {name!r} 之原因 {reason!r} 不在 {DELTA_REASONS}")
        out_reasons[name] = reason
    return {"added": added, "removed": removed, "reasons": out_reasons}


def canonical_delta_bytes(delta: Mapping[str, Any]) -> bytes:
    """`json.dumps(delta, sort_keys=True, ensure_ascii=False, separators=(',', ':'))` 之 UTF-8 位元組（無結尾換行）。"""
    return json.dumps(delta, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def delta_sha256(delta: Mapping[str, Any]) -> str:
    """`canonical_delta_bytes` 之 sha256 十六進位字串。"""
    return hashlib.sha256(canonical_delta_bytes(delta)).hexdigest()


__all__ = [
    "WARMUP_POLICY", "OUTPUT_START_SOURCES", "DELTA_REASONS", "L3_DEAD_NAN_RATE", "L3_MIN_EFFECTIVE_N",
    "L7_MIN_VALID_SAMPLES_DEFAULT", "StableMaskError", "DeltaReasonError", "OutputPointSpec", "DeadDecision",
    "first_finite_index", "l1_origin", "instance_k", "canonical_params", "variant_key", "check_variant", "k_for_params", "UnmeasuredVariantError", "apply_l1_mask",
    "mask_incomplete_window",
    "mask_incomplete_window_inplace",
    "mask_pointwise_prefix", "calibration_rows_no_start", "dead_column_decision", "column_set_sha256",
    "column_set_delta", "canonical_delta_bytes", "delta_sha256",
]
