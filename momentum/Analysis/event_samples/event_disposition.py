"""SPLITUNIFY `Task 10.4`／`R5-C8`：逐事件處置帳（兩端差集與剔除揭露之唯一來源）。

每個通過匯入驗證之 `event_id` **恰一列**，欄＝`event_id`、`symbol`、`scan_disposition`、
`ic_disposition`。事件掃描回應之 `period_alignment` 與 `excluded_by_symbol` 由本帳導出，
不另算（`R5-C8` 4.）。

🔴 **預測與觀測分離**（`R5-C8` 6.）：`ic_disposition` 是**入口之預測**——
`feature_row_not_in_feature_index` 以事件之 `R5-C9` 特徵列鍵是否屬 post-trim `feature_index`
判定，**不得**讀取 IC stage3 之結果或其觀測收據。讀了就變成「拿自己比自己」，
`Task 10.7` 的對證會恆真而失去意義。

🔴 **值集封閉且自契約讀**（`R5-C8` 2.）：手打字面即與前端脫節；測試以手打值即紅釘住。

🔴 **誠實邊界**（`R5-C8` 9.）：兩端共用之上游（`align_events` 之截止列選取、run symbol 過濾、
coverage）若本身有錯，預測與觀測會**同錯**而對證仍相等。該面由既有對齊測試、
`R5-C9` 5. 之產出端 PIT 守衛與 mutation 守，不由本帳擔保。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

_CONTRACT = Path(__file__).resolve().parents[2] / "Analysis/contracts/split_unify.json"


@lru_cache(maxsize=1)
def disposition_values() -> Dict[str, tuple]:
    """封閉值集（自契約讀；`R5-C8` 2.）。"""
    data = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    vals = data.get("event_disposition_values")
    if not isinstance(vals, dict) or not vals:
        raise ValueError(
            f"{_CONTRACT} 缺 event_disposition_values——處置帳之值集不得手打（fail-closed）"
        )
    return {k: tuple(v) for k, v in vals.items()}


@dataclass(frozen=True)
class DispositionRow:
    event_id: str
    symbol: str
    scan_disposition: str
    ic_disposition: str


def _check(value: str, field: str) -> str:
    allowed = disposition_values().get(field, ())
    if value not in allowed:
        raise ValueError(
            f"{field}={value!r} 不在契約之封閉值集 {list(allowed)} 內（fail-closed）"
        )
    return value


def build_event_disposition_ledger(
    *,
    events: Sequence[Mapping[str, Any]],
    run_symbol: str,
    aligned_event_ids: Set[str],
    coverage_ok_event_ids: Set[str],
    feature_row_key_by_id: Mapping[str, int],
    post_trim_index_ms: Set[int],
    label_value_by_id: Optional[Mapping[str, Any]] = None,
) -> List[DispositionRow]:
    """產出逐事件處置帳。

    參數之語意（皆為**入口可得**之資訊，不含 stage3 結果）：
      `events`：通過匯入驗證之事件（需有 `event_id` 與 `symbol`）。
      `aligned_event_ids`：對齊成功者。
      `coverage_ok_event_ids`：通過 `check_feature_run_coverage` 者。
      `feature_row_key_by_id`：`R5-C9` 之特徵列鍵（`last_bar_open_ms`）。
      `post_trim_index_ms`：post-trim `feature_index` 之毫秒集合。
      `label_value_by_id`：分析用 label 值；`None` 或值為 `None` ⇒ `label_value_unavailable`。

    判定順序（`R5-C8` 3.，**不可調**）：對齊 → run symbol → coverage → label 值 → 特徵列。
    掃描端另於 coverage 之後判 `outside_post_trim_index`。
    """
    rows: List[DispositionRow] = []
    seen: Set[str] = set()
    for ev in events:
        eid = str(ev.get("event_id"))
        if eid in seen:
            raise ValueError(f"處置帳要求每個 event_id 恰一列，但 {eid!r} 重複（fail-closed）")
        seen.add(eid)
        sym = str(ev.get("symbol"))

        # ① 對齊
        if eid not in aligned_event_ids:
            rows.append(DispositionRow(eid, sym, _check("align_failed", "scan_disposition"),
                                       _check("align_failed", "ic_disposition")))
            continue
        # ② run symbol
        if sym != str(run_symbol):
            rows.append(DispositionRow(
                eid, sym, _check("symbol_not_run_symbol", "scan_disposition"),
                _check("symbol_not_run_symbol", "ic_disposition")))
            continue
        # ③ coverage
        if eid not in coverage_ok_event_ids:
            rows.append(DispositionRow(
                eid, sym, _check("outside_feature_run_coverage", "scan_disposition"),
                _check("outside_feature_run_coverage", "ic_disposition")))
            continue

        key = feature_row_key_by_id.get(eid)
        in_index = key is not None and int(key) in post_trim_index_ms
        # 掃描端：coverage 之後再判 post-trim 首尾剔除（`R5-C4` 1.(b)）。
        scan = "projected" if in_index else "outside_post_trim_index"

        # ④ label 值（IC 端專有；掃描端不需要 label 即可投影）
        if label_value_by_id is not None and label_value_by_id.get(eid) is None:
            ic = "label_value_unavailable"
        # ⑤ 特徵列是否在 post-trim 索引內（**預測**，不讀 stage3）
        elif not in_index:
            ic = "feature_row_not_in_feature_index"
        else:
            ic = "ic_consumed"
        rows.append(DispositionRow(eid, sym, _check(scan, "scan_disposition"),
                                   _check(ic, "ic_disposition")))
    return rows


def excluded_by_symbol(rows: Sequence[DispositionRow]) -> List[str]:
    """`R5-C8` 4.：由處置帳導出，**不另算**。"""
    return sorted(r.event_id for r in rows if r.scan_disposition == "symbol_not_run_symbol")


__all__ = [
    "DispositionRow",
    "build_event_disposition_ledger",
    "disposition_values",
    "excluded_by_symbol",
]
