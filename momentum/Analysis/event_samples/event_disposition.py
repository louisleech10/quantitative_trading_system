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

import copy
import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

_CONTRACT = Path(__file__).resolve().parents[2] / "Analysis/contracts/split_unify.json"


def _no_duplicate_keys(pairs):
    """JSON 物件解析鉤子：同名成員即 fail-closed（`CODEX-R43-P1-01`）。

    🔴 `json.loads` 對重複鍵是 **last-wins 且靜默**。契約若在合併、生成或部署時長出
    第二個 `consumed`，accessor 會把後者當成語意值——該家實跑得到
    `{'consumed': 'align_failed', ...}`，且 exact-key／subset／不重複三道檢查**全部通過**。
    更糟的是既有測試以同一個 `json.loads` 結果對證 ⇒ parser、accessor、測試三方共因而假綠。
    """
    seen = set()
    for k, _v in pairs:
        if k in seen:
            raise ValueError(f"契約含重複 JSON 鍵：{k!r}——last-wins 會靜默改語意（fail-closed）")
        seen.add(k)
    return dict(pairs)


@lru_cache(maxsize=4)
def _load_values(_content_sha: str) -> Dict[str, Any]:
    """實際讀檔；以**內容雜湊**為快取鍵。

    🔴 `CODEX-R42-P2-02`：最初 `@lru_cache(maxsize=1)` 鎖在函式上，warm cache 後改契約
    不生效（長生命週期行程一直用舊值、同行程之 mutation 覆核假綠）。
    🔴 `CODEX-R43-P2-02`：改以 `mtime_ns` 為鍵仍不足——該家實跑證實「內容變更而 mtime
    被保留」（同奈秒寫入、`cp -p`、`os.utime` 還原）時快取仍回舊值。
    ⇒ 鍵改為內容之 sha256：內容變了就換鍵，與 mtime 無關。
    """
    data = json.loads(_CONTRACT.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)
    vals = data.get("event_disposition_values")
    if not isinstance(vals, dict) or not vals:
        raise ValueError(
            f"{_CONTRACT} 缺 event_disposition_values——處置帳之值集不得手打（fail-closed）"
        )
    # 🔴 `observed` 是具名 mapping（語意不由順序決定），其餘欄為封閉值集之 list。
    #    一律 `tuple(v)` 會把 mapping 壓成鍵的 tuple ⇒ 語意消失（`CODEX-R42-P1-01` 之修補面）。
    return {
        k: (dict(v) if isinstance(v, dict) else tuple(v))
        for k, v in vals.items()
    }


def disposition_values() -> Dict[str, Any]:
    """封閉值集（自契約讀；`R5-C8` 2.）。快取以**內容雜湊**為鍵，內容變了即失效。

    🔴 **回傳深複本**（`CODEX-R44-P1-01`／`COMPOSER-R44-P2-01` 兩家撞題）：
    前版把 `lru_cache` 持有的 dict **原樣**交出去，呼叫端一改就污染後續所有呼叫，
    而契約 bytes 與其 sha 都沒變 ⇒ 前四層守衛（手打字面、順序、重複鍵、快取陳舊）
    **全部繞過**。提出方實跑：改 `vals["observed"]["consumed"]` 後
    `observed_values()` 回被污染值、`_check("probe_only_value", …)` 通過。
    🔴 淺複製不夠——`observed` 是巢狀 mapping，淺複製仍共用同一個內層 dict。
    """
    cached = _load_values(hashlib.sha256(_CONTRACT.read_bytes()).hexdigest())
    return copy.deepcopy(cached)


#: 相容既有測試之顯式清快取入口（內容雜湊鍵已使其非必要，保留以免呼叫端壞掉）。
disposition_values.cache_clear = _load_values.cache_clear  # type: ignore[attr-defined]


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


def observed_values() -> Dict[str, str]:
    """stage3 觀測收據之 `observed` 值——**唯一取值出口**（`CODEX-R41-P1-02`）。

    🔴 出生理由：stage3 producer 原本手打 `ic_consumed`／`feature_row_not_in_feature_index`，
    契約若改名，producer 仍會吐舊字面而不在 producer 邊界 fail-closed
    （提出方實跑：改契約後真實 run 之收據值落在新封閉集合之外）。
    ⇒ 由本出口依**語意鍵**取值；契約缺鍵、欄位形狀不符或語意映射不全即擲錯。

    回傳 `{"consumed": <字面>, "row_missing": <字面>}`。
    """
    vals = disposition_values()
    observed = vals.get("observed")
    # 🔴 **語意由具名鍵固定，不由順序**（`CODEX-R42-P1-01`）：前版以 list 之第一／第二值
    #    定義「被消費／列不在索引內」，值集不變而**順序調換**時 producer 會靜默吐反的語意
    #    （提出方實跑：反轉後 accessor 回傳之兩個語意值互換，rc=0、無人擋）。
    #    ⇒ 契約改為 mapping，accessor 只按固定鍵讀。
    if not isinstance(observed, dict):
        raise ValueError(
            f"契約之 event_disposition_values.observed 須為具名 mapping，實得 {type(observed).__name__}"
            "——以順序定語意會在值集重排時靜默反轉（fail-closed）"
        )
    want = {"consumed", "row_missing"}
    if set(observed) != want:
        raise ValueError(
            f"observed 之鍵須恰為 {sorted(want)}，實得 {sorted(observed)}（fail-closed）"
        )
    ic_vals = set(vals.get("ic_disposition", ()))
    missing = [v for v in observed.values() if v not in ic_vals]
    if missing:
        raise ValueError(
            f"observed 之值 {missing} 不在 ic_disposition 值集內"
            "——預測與觀測必須可逐值對證（fail-closed）"
        )
    if len(set(observed.values())) != 2:
        raise ValueError(
            f"observed 之兩個語意不得映射到同一值：{observed}（fail-closed）"
        )
    return {"consumed": str(observed["consumed"]), "row_missing": str(observed["row_missing"])}


def excluded_by_symbol(rows: Sequence[DispositionRow]) -> List[str]:
    """`R5-C8` 4.：由處置帳導出，**不另算**。"""
    return sorted(r.event_id for r in rows if r.scan_disposition == "symbol_not_run_symbol")


__all__ = [
    "DispositionRow",
    "build_event_disposition_ledger",
    "disposition_values",
    "excluded_by_symbol",
]
