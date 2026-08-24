"""GAP-3 UX §G S-9 — dict → bytes 之**唯一**位元組 encoder（G-2 sha256 之唯一計算規則）。

S-1..S-8 定義了欄位語意與排序，但沒定義 **dict → bytes** 這一步
⇒ 不同實作者選不同 `separators`／escaping／尾端 newline，仍各自「符合 S-1..S-8」
卻得到不同 sha256。本檔即該步之唯一規則。

🔴 **任何實作不得自行約定 `json.dumps` 參數**；G-2 之凍結與比對腳本、以及前端匯出鏈，
**只准 import 本檔之 `canonical_event_table_bytes`，禁複製邏輯**（S-9 第 7 條）
——複製即第二份副本，副本必然漂移。

規則（逐條對應 S-9）::

  1. 輸入＝已依 S-1..S-7 組好之 dict（鍵序已符合 S-2，**不得再 sort**）
  2. 型別白名單：bool／int／有限 float／str／list／dict／None；
     其他（Decimal、numpy 純量、datetime…）一律先轉為上列型別，禁依賴 encoder 隱式轉換
  3. 正規化：NaN／±Inf → None；`-0.0` **保留**（不得正規化為 0.0——JSON lexeme 不同）；
     缺席鍵保持缺席（不得補 null）；list 順序原樣保留
  4. `json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False, sort_keys=False)`
  5. **不得**附加尾端 `\\n` 或任何 whitespace（三家分歧之裁決點，採 2:1 之「禁」）
  6. `.encode('utf-8')`（禁 BOM）→ `hashlib.sha256(bytes).hexdigest()`
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

#: S-9 第 2 條之型別白名單（順序無意義；`bool` 須在 `int` 之前判，因 `bool ⊂ int`）。
_ALLOWED_SCALARS = (bool, int, float, str)


def _json_dumps(obj: Any) -> str:
    """S-9 第 4 條之**唯一** `json.dumps` 呼叫點。參數不得在別處重寫。

    `allow_nan=False` 是刻意的：若正規化被跳過，這裡會 **raise**，
    而不是靜默輸出 `NaN` 字面（那會產出非法 JSON 且雜湊隨實作漂移）。
    """
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False, sort_keys=False)


def normalize_for_canonical(obj: Any) -> Any:
    """S-9 第 2–3 條：型別白名單檢查 ＋ 非有限浮點正規化。**不排序、不補鍵**。"""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        # NaN／±Inf → None（與 S-5 一致）；-0.0 原樣保留（repr 為 '-0.0'，與 0.0 之 lexeme 不同）
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"S-9 只接受 str 鍵，實得 {type(k).__name__}: {k!r}")
            out[k] = normalize_for_canonical(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [normalize_for_canonical(v) for v in obj]
    raise TypeError(
        f"S-9 型別白名單不含 {type(obj).__name__}（{obj!r}）"
        "——須由呼叫端先轉為 bool/int/float/str/list/dict/None，禁依賴 encoder 隱式轉換"
    )


def canonical_event_table_bytes(obj: Any) -> bytes:
    """S-9 參考實作：已依 S-1..S-7 組好之 dict → canonical bytes（無尾端 newline、無 BOM）。"""
    return _json_dumps(normalize_for_canonical(obj)).encode("utf-8")


def canonical_event_table_sha256(obj: Any) -> str:
    """S-9 第 6 條：canonical bytes 之 sha256 hexdigest（G-2 凍結與比對之唯一計算規則）。"""
    return hashlib.sha256(canonical_event_table_bytes(obj)).hexdigest()
