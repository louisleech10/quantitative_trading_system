"""FF-STAT Task 2.3／2.4：逐欄穩定點遮罩、死欄純函式與欄集合差異（docs/FFSTAT_SPEC.md v43 §C）。

本模組只放純函式：不讀檔、不算指標、不記 log。呼叫端（L1 輸出點、L6.5、L3／L7 死欄過濾、收據）
以本模組之結果套用遮罩或判定；遮罩只作用於輸出，不改任何計算本身（SPEC §C「逐欄穩定點」、R6）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

# 設定 hash 納入之預熱政策版本（SPEC §C「公開域預熱」；改前快取一律未命中）
WARMUP_POLICY = "per_column_stable_v1"

# `output_start_source` 之封閉值（SPEC §C「未填起始日」紀錄與顯示）
OUTPUT_START_SOURCES: Tuple[str, ...] = ("user", "per_column")

# 欄集合差異原因之封閉值（SPEC Task 2.3 ⑦；其他值於 digest 與核可比對前即拒收）
DELTA_REASONS: Tuple[str, ...] = ("nan_rate_rule", "stable_samples_below_min")

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


def first_finite_index(values: np.ndarray) -> Optional[int]:
    """第一個有限值之列索引；全非有限值回 None。"""
    raise NotImplementedError("FFSTAT Task 2.3")


def l1_origin(inputs: np.ndarray) -> Optional[int]:
    """L1 遮罩之 origin：該指標全部輸入欄（二維：列×輸入欄）皆為有限值之第一列；無則 None（SPEC §C L1 遮罩）。"""
    raise NotImplementedError("FFSTAT Task 2.3")


def instance_k(spec: OutputPointSpec, table: Mapping[str, Mapping[str, Any]],
               upstream_k: Optional[Mapping[str, int]] = None) -> int:
    """逐計算呼叫之 K（SPEC §C v37／v39）。

    L1 原始輸出：ceil(max(params[k] for k in period_keys) × 表之採用係數)；無參數者取表內登記之 K。
    同引擎衍生輸出：上游 K 之最大者＋window−1（窗型）或上游 K 之最大者（逐點聚合）。
    倍數表缺條目、參數字典缺任一登記鍵、衍生輸出缺上游 K ⇒ StableMaskError（列引擎、欄、缺鍵）。
    """
    raise NotImplementedError("FFSTAT Task 2.3")


def apply_l1_mask(values: np.ndarray, origin: Optional[int], k: int) -> np.ndarray:
    """回傳新陣列：origin 之前與 `[origin, origin+k)` 設為 NaN；origin 為 None 則全 NaN。不改輸入。"""
    raise NotImplementedError("FFSTAT Task 2.3")


def mask_incomplete_window(output: np.ndarray, input_values: np.ndarray, window: int) -> np.ndarray:
    """第①類（固定窗而以不完整窗出值，如 L6.5 縮尾）：輸出自輸入首個有限值起 `window−1` 列設 NaN（只遮罩）。"""
    raise NotImplementedError("FFSTAT Task 2.3")


def mask_pointwise_prefix(output: np.ndarray, inputs: Sequence[np.ndarray]) -> np.ndarray:
    """第④類（逐點或跨欄運算對 NaN 給有限值）：輸出於各輸入首個有限值之最大者之前設 NaN；之後不動。"""
    raise NotImplementedError("FFSTAT Task 2.3")


def calibration_rows_no_start(values: np.ndarray, n: int) -> Optional[Tuple[int, int]]:
    """無起始日時該欄之校準列：最早 N 個有限值所在之 (首列, 第 N 個有限值之列)（含兩端）；不足 N 回 None。"""
    raise NotImplementedError("FFSTAT Task 2.3")


def dead_column_decision(values: np.ndarray, *, nan_rate_threshold: Optional[float], min_valid: int) -> DeadDecision:
    """L3 與 L7、frame 與 CGSA 共用之死欄純函式（SPEC §C v33／v34）。

    NaN 率之分母＝自首個有限值起之列數（開頭 NaN 段不計，與遮罩長度無關）；有效樣本數＝有限值個數；
    常數＝有限值之相異值數 < 2。`nan_rate_threshold` 為 None 表不判 NaN 率（L7）。
    """
    raise NotImplementedError("FFSTAT Task 2.3")


def column_set_sha256(columns: Sequence[str]) -> str:
    """欄集合 sha256：欄名依 UTF-8 位元組升序去重、以 `\\n` 連接之 UTF-8 位元組（無結尾換行）（SPEC Task 2.3 ⑦）。"""
    raise NotImplementedError("FFSTAT Task 2.3")


def column_set_delta(before: Sequence[str], after: Sequence[str], reasons: Mapping[str, str]) -> Dict[str, Any]:
    """欄集合差異物件 `{"added":[…],"removed":[…],"reasons":{欄名:原因}}`（兩陣列依欄名 UTF-8 位元組升序）。

    每個差異欄皆須有原因且原因 ∈ `DELTA_REASONS`，否則 DeltaReasonError；無差異時三者皆空。
    """
    raise NotImplementedError("FFSTAT Task 2.3")


def canonical_delta_bytes(delta: Mapping[str, Any]) -> bytes:
    """`json.dumps(delta, sort_keys=True, ensure_ascii=False, separators=(',', ':'))` 之 UTF-8 位元組（無結尾換行）。"""
    raise NotImplementedError("FFSTAT Task 2.3")


def delta_sha256(delta: Mapping[str, Any]) -> str:
    """`canonical_delta_bytes` 之 sha256 十六進位字串。"""
    raise NotImplementedError("FFSTAT Task 2.3")


__all__ = [
    "WARMUP_POLICY", "OUTPUT_START_SOURCES", "DELTA_REASONS", "L3_DEAD_NAN_RATE", "L3_MIN_EFFECTIVE_N",
    "L7_MIN_VALID_SAMPLES_DEFAULT", "StableMaskError", "DeltaReasonError", "OutputPointSpec", "DeadDecision",
    "first_finite_index", "l1_origin", "instance_k", "apply_l1_mask", "mask_incomplete_window",
    "mask_pointwise_prefix", "calibration_rows_no_start", "dead_column_decision", "column_set_sha256",
    "column_set_delta", "canonical_delta_bytes", "delta_sha256",
]
