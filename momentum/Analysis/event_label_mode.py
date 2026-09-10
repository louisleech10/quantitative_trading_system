"""EVTLABEL 契約載入與 label 規則揭露（純函式；`docs/EVTLABEL_SPEC.md` Task 1.1／3.1）。

單一真相源＝`momentum/Analysis/contracts/event_label_mode.json`；本模組只讀不寫。
`build_event_label_rule` 由**實際套用**之分析 spec（`PreparedAnalysisWindows.normalized_spec_bytes`）
與對齊收據（`WindowRow.label_start_ms/label_end_ms`）機械導出「本次 label 怎麼算」，
**不重算 label、不讀 request**（route 可能 seed 過）。
"""

from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

_CONTRACT_PATH = Path(__file__).resolve().parent / "contracts" / "event_label_mode.json"


@lru_cache(maxsize=1)
def load_event_label_mode_contract() -> Dict[str, Any]:
    """讀 JSON SoT；缺必要鍵 ⇒ import 期即 raise（fail-closed）。"""
    data = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    for key in ("event_label_rule_keys", "imported_binary_label_keys", "return_formula_by_mode", "h_unit_value"):
        if key not in data:
            raise ValueError(f"event_label_mode.json 缺必要鍵 {key!r}（fail-closed）")
    return data


def event_label_rule_keys() -> frozenset:
    return frozenset(load_event_label_mode_contract()["event_label_rule_keys"])


def return_formula(mode: Optional[str], entry: Optional[str]) -> Optional[str]:
    """查表組字串；mode 未知 ⇒ None（前端顯示「未揭露」，不得空白）。"""
    table = load_event_label_mode_contract()["return_formula_by_mode"]
    tpl = table.get(str(mode)) if mode is not None else None
    if not isinstance(tpl, str):
        return None
    return tpl.replace("{entry}", str(entry))


def _ceil_div(a: int, b: int) -> int:
    return -(-int(a) // int(b))


def uniqueness_from_windows(windows: Sequence[Any]) -> Dict[str, Any]:
    """R-1 不重工預留（使用者 2026-09-10）：每事件 w＝1／(與其 label 視窗 `[start,end)` 相交之事件數，含自己)。

    同 `event_samples/dedupe.py:86` 之「label 窗兩兩相交」定義；`n_eff=Σw`。**只揭露不參與計算**。

    🔴 **O(n log n)**（R1 `CODEX-R1-P1-02`／`COMPOSER-R1-P2-01`／`GROK-R1-P2-01` 三家同判）：
    初版寫成 O(n²) 兩兩比對，而事件匯入**沒有筆數硬上限**（僅 50MiB 檔頂 ≈1.5 萬筆）
    ⇒ 萬級批次光是「揭露」就在 API 執行緒阻塞數秒。改法保留**完全相同**的半開區間語意：
    以排序陣列二分搜尋取「完全在前」「完全在後」之補集（同座標時 `[a,b)` 與 `[b,c)` 不算相交）。
    `counts[i]`＝與 i 相交之區間數（含自己）；`pairs`＝相交配對數（掃描時累加「加入時的現存數」）。
    windows 空 ⇒ 全 None。
    """
    win = [(int(w.label_start_ms), int(w.label_end_ms)) for w in windows]
    n = len(win)
    if n == 0:
        return {"mean": None, "min": None, "n_eff": None, "n_overlapping_pairs": None}

    # counts[i] = n − |{j: end_j ≤ start_i}|（完全在 i 之前） − |{j: start_j ≥ end_i}|（完全在 i 之後）
    # 兩個補集皆以排序陣列二分搜尋取得 ⇒ 每筆 O(log n)，不需列舉相交對（高度重疊時仍不退化成 O(n²)）。
    starts = sorted(s for s, _ in win)
    ends = sorted(e for _, e in win)
    counts = [
        max(1, n - bisect_right(ends, start) - (n - bisect_left(starts, end)))
        for start, end in win
    ]
    # 每對相交被兩端各數一次；扣掉自己那 n 次後折半。
    pairs = (sum(counts) - n) // 2

    weights = [1.0 / c for c in counts]
    return {
        "mean": float(sum(weights) / n),
        "min": float(min(weights)),
        "n_eff": float(sum(weights)),
        "n_overlapping_pairs": int(pairs),
    }


def build_event_label_rule(
    *,
    normalized_spec: Mapping[str, Any],
    windows: Sequence[Any],
    records: Iterable[Mapping[str, Any]],
    feature_timeframe: Optional[str],
    timeframe_seconds: Mapping[str, int],
    label_source: Optional[str],
    statistic_kind: Optional[str],
    n_events_consumed: int,
    consumed_event_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """組 `metadata.event_label_rule`（鍵集恰等於契約 `event_label_rule_keys`，不等 ⇒ raise）。

    🔴 `consumed_event_ids`（R1 `CODEX-R1-P1-01`）：**揭露的分母必須＝實際被 IC 消費的那批事件**。
    service 會排除「symbol 不是本次 feature run」的事件（`_stage_event_batch` 之 `excluded_by_symbol`），
    初版卻拿**全批** windows／records 算 0/1 計數、視窗與重疊度 ⇒ 混 symbol 批之揭露與 `n_events_consumed`
    分母不一致（報告自己跟自己打架）。給定時一律先裁到該集合；`None` ⇒ 沿用全批（單 symbol 批等價）。

    - `label_window_feature_bars`＝ceil(max(label_end_ms − label_start_ms) / feature_bar_ms)：
      一律由收據取，**不由 h 重算**（SPEC ASSUME-1：視窗公式依 mode，o2hc 為 (h+1)×bar）。
    - 批內事件週期不一 ⇒ `event_timeframe="mixed"`、`feature_bars_per_event_bar=None`、`ratio_integral=False`。
    - `imported_binary_label.present`＝所有 records 皆帶 `label` 欄；P1 一律 `used=False`（Task 3.4 才翻）。
    """
    contract = load_event_label_mode_contract()
    recs = list(records)
    win = list(windows)
    if consumed_event_ids is not None:
        keep = {str(eid) for eid in consumed_event_ids}
        kept_win = [w for w in win if str(getattr(w, "event_id", "")) in keep]
        # 🔴 fail-closed：給了 id 集合卻一筆都對不上 ⇒ 呼叫端的 id 語意與 windows 不同源（bug），
        #    **不得**靜默產出空揭露（那會讓報告顯示 0 事件卻仍宣稱分析成功）。
        if keep and win and not kept_win:
            raise ValueError(
                "event_label_rule: consumed_event_ids 與 windows 之 event_id 無交集"
                f"（consumed={len(keep)} windows={len(win)}）——兩者必須同源"
            )
        win = kept_win
        recs = [r for r in recs if str(r.get("event_id", "")) in keep]

    event_tfs = sorted({str(getattr(w, "timeframe")) for w in win})
    feature_tf = str(feature_timeframe) if feature_timeframe else None
    feature_bar_s = timeframe_seconds.get(feature_tf) if feature_tf else None

    window_ms = max((int(w.label_end_ms) - int(w.label_start_ms) for w in win), default=0)
    label_window_feature_bars: Optional[int]
    if feature_bar_s:
        label_window_feature_bars = _ceil_div(window_ms, int(feature_bar_s) * 1000) if window_ms > 0 else 0
    else:
        label_window_feature_bars = None

    if len(event_tfs) == 1 and feature_bar_s:
        event_bar_s = timeframe_seconds.get(event_tfs[0])
        if event_bar_s and int(event_bar_s) % int(feature_bar_s) == 0:
            ratio: Optional[int] = int(event_bar_s) // int(feature_bar_s)
            ratio_integral = True
        else:
            ratio = None
            ratio_integral = False
        event_timeframe: Optional[str] = event_tfs[0]
    else:
        ratio = None
        ratio_integral = False
        event_timeframe = contract["event_timeframe_mixed_value"] if len(event_tfs) > 1 else (event_tfs[0] if event_tfs else None)

    labels = [r.get("label") for r in recs]
    present = bool(recs) and all(lab is not None for lab in labels)
    n_pos = sum(1 for lab in labels if lab is not None and int(lab) == 1) if present else 0
    n_neg = sum(1 for lab in labels if lab is not None and int(lab) == 0) if present else 0

    entry = normalized_spec.get("entry_price_semantic")
    mode = normalized_spec.get("label_return_mode")
    out: Dict[str, Any] = {
        "label_source": label_source,
        "statistic_kind": statistic_kind,
        "horizon_bars": normalized_spec.get("horizon_bars"),
        "decision_offset_bars": normalized_spec.get("decision_offset_bars"),
        "entry_price_semantic": entry,
        "label_return_mode": mode,
        "h_unit": contract["h_unit_value"],
        "event_timeframe": event_timeframe,
        "feature_timeframe": feature_tf,
        "feature_bars_per_event_bar": ratio,
        "ratio_integral": ratio_integral,
        "label_window_feature_bars": label_window_feature_bars,
        "return_formula": return_formula(mode, entry),
        "imported_binary_label": {"present": present, "n_pos": int(n_pos), "n_neg": int(n_neg), "used": False},
        "n_events_consumed": int(n_events_consumed),
        "uniqueness": uniqueness_from_windows(win),
    }
    expected = set(contract["event_label_rule_keys"])
    if set(out) != expected:
        raise ValueError(
            f"event_label_rule 鍵集與契約不符：missing={sorted(expected - set(out))} extra={sorted(set(out) - expected)}"
        )
    if set(out["imported_binary_label"]) != set(contract["imported_binary_label_keys"]):
        raise ValueError("imported_binary_label 子鍵集與契約不符")
    return out
