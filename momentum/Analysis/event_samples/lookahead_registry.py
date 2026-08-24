"""GAP-3 UX Task 1.10 — 欄位級 lookahead 契約之讀取與解析（D-7 之 L1）。

欄名／深度／單位之字面唯一住 `momentum/Analysis/contracts/future_column_lookahead.json`，
本檔**不複列**任何欄名或深度常數，只做讀取、正規化與換算。

🔴 兩件事必須分開，混在一起就是本 epic 要防的洩漏：
  1. **深度**（這個欄看多遠）——由 registry 給，**不得由欄名字串樣式推測**。
  2. **信任邊界**（這個欄名可不可信）——由該批之 **provenance** 決定，**不是**欄名。
     欄名可被改寫：把引用 20 根未來資料之自訂欄改名為 `future_4bar_return`，
     若只比對欄名就會把 purge 低估到 4 根（CODEX-R4-P1-07）。

Task 1.9／1.11／1.12／2.1b 皆呼叫本檔之 `resolve_lookahead_bars()`，禁各自實作換算。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Set

from momentum.core.constants import TIMEFRAME_SECONDS

_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "contracts" / "future_column_lookahead.json"

#: provenance 之封閉取值集合（語意見 registry 之 provenance_trust_boundary）。
PROVENANCE_SYSTEM_GENERATED = "system_generated"
PROVENANCE_EXTERNAL_UPLOAD = "external_upload"
_PROVENANCE_KINDS = (PROVENANCE_SYSTEM_GENERATED, PROVENANCE_EXTERNAL_UPLOAD)


def load_lookahead_registry() -> dict:
    """讀取 future 欄 lookahead 契約 SoT；版本不符即 raise（fail-closed）。"""
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    if registry.get("version") != 1:
        raise ValueError(f"unsupported future_column_lookahead version: {registry.get('version')!r}")
    if registry.get("hours_to_bars_rounding") != "ceil":
        raise ValueError(
            "future_column_lookahead.hours_to_bars_rounding 只支援 'ceil'（向下取整會把 sub-bar 深度讀成 0＝放水）"
        )
    return registry


def lookahead_columns(registry: Optional[Mapping[str, Any]] = None) -> Dict[str, dict]:
    """registry 之欄位對映（`{欄名: {kind, lookahead_bars|lookahead_hours|lookahead_unknown}}`）。"""
    r = registry if registry is not None else load_lookahead_registry()
    return r["columns"]


def normalize_future_column(column: str, registry: Optional[Mapping[str, Any]] = None) -> str:
    """把 CSV 標題形正規化為契約蛇形。

    涵蓋三形態（SPEC Task 1.10 ③）：`Future_4Bar_Return_%`／`future_4bar_return`／`FUTURE_4BAR_RETURN`。
    只做**形態**正規化（大小寫、`%` 後綴、封閉 alias 表），**不推測深度**。
    """
    r = registry if registry is not None else load_lookahead_registry()
    s = column.strip().lower()
    while s.endswith("%") or s.endswith("_") or s.endswith(" "):
        s = s[:-1]
    aliases = r["aliases"]
    return aliases.get(s, s) if not s.startswith("_") else s


def hours_to_bars(hours: int, timeframe: str) -> int:
    """小時 → 根數（向上取整；timeframe 未知即 raise，不猜）。"""
    tf_seconds = TIMEFRAME_SECONDS.get(timeframe)
    if tf_seconds is None:
        raise ValueError(f"未知 timeframe: {timeframe!r}（fail-closed，不得以預設值代替）")
    total = int(hours) * 3600
    return -(-total // tf_seconds)  # ceil division，見 registry.hours_to_bars_rounding_doc


def resolve_lookahead_bars(
    column: str,
    timeframe: str,
    registry: Optional[Mapping[str, Any]] = None,
) -> Optional[int]:
    """純 registry 解析：回傳該欄在該 timeframe 之前視根數；不可解析回 `None`。

    「不可解析」有兩種：未登記之欄、以及顯式標 `lookahead_unknown` 之 legacy 欄
    ——兩者都**不得**給預設深度，一律交由 L2（Task 1.11）強制宣告。

    🔴 本函式**不看 provenance**；信任邊界請用 `lookahead_resolution()`。
    """
    r = registry if registry is not None else load_lookahead_registry()
    entry = lookahead_columns(r).get(normalize_future_column(column, r))
    if entry is None:
        return None
    kind = entry["kind"]
    if kind == "bar":
        return int(entry["lookahead_bars"])
    if kind == "hour":
        return hours_to_bars(int(entry["lookahead_hours"]), timeframe)
    if kind == "unknown":
        return None
    raise ValueError(f"registry 出現未知 kind: {kind!r}（fail-closed）")


def lookahead_resolution(
    column: str,
    timeframe: str,
    *,
    provenance: str,
    registry: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """信任邊界之單欄判定（D-7 L1 → L2 交界）。

    回傳 `{"lookahead_bars": int|None, "requires_declaration": bool, "reason": str}`。

    - `provenance == "system_generated"`：可依 registry 直接解析；解析不出 ⇒ 仍須宣告。
    - `provenance == "external_upload"`：**無論欄名是否命中 registry**，一律 `requires_declaration=True`
      且 `lookahead_bars=None`——欄名對外部來源不具證據力（改名攻擊）。
    """
    if provenance not in _PROVENANCE_KINDS:
        raise ValueError(f"未知 provenance: {provenance!r}（封閉集合 {_PROVENANCE_KINDS}，fail-closed）")
    if provenance != PROVENANCE_SYSTEM_GENERATED:
        return {
            "lookahead_bars": None,
            "requires_declaration": True,
            "reason": "external_upload_column_name_not_evidence",
        }
    bars = resolve_lookahead_bars(column, timeframe, registry)
    if bars is None:
        return {
            "lookahead_bars": None,
            "requires_declaration": True,
            "reason": "depth_not_derivable_from_registry",
        }
    return {"lookahead_bars": bars, "requires_declaration": False, "reason": "resolved_from_registry"}


def unregistered_future_columns(
    columns: Iterable[str],
    registry: Optional[Mapping[str, Any]] = None,
) -> Set[str]:
    """回傳「看起來是未來欄、但沒登記」之集合；fail-closed 之判定依據（驗證②）。

    未登記即紅為**預期行為**——新增未來欄之 PR 須先登記，
    不得以放寬本函式或加白名單消紅。
    """
    r = registry if registry is not None else load_lookahead_registry()
    known = lookahead_columns(r)
    out: Set[str] = set()
    for c in columns:
        if not str(c).lower().startswith("future"):
            continue
        if normalize_future_column(str(c), r) not in known:
            out.add(str(c))
    return out
