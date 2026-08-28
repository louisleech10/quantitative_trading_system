"""GAP-3 PIT 對齊純函式＋兩層收據（docs/GAP3_EVENT_TODO.md Task B1.1；SPEC D2 全節）。

純函式：吃已載入之 bar 表（不讀 HDF5，kline 隔離）。逐事件推導六時間欄與 per-TF
feature_cutoff；任一不變式違反 ⇒ 該事件入 failures（reason＝契約檔
alignment_failure_reasons 枚舉），**無 silent skip**——記帳守恆
n_input == n_receipts + n_failures（M1 看住）。

bars_by_tf 形狀：{symbol: {timeframe: DataFrame}}，DataFrame 必含欄
open_time_ms / close_time_ms / open / close（epoch ms UTC；bar open_time 排序）。
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from momentum.Analysis.event_samples.keys import event_scope_key, event_trigger_timeframe
from momentum.Analysis.event_samples.types import AlignmentConfig, AlignmentReceipts

#: 🔴 **GAP-3 UX Task 7.0b 擴充 `symbol`／`timeframe`**（SPEC L2487–2500，先改契約 D-6）。
#  為什麼收據本身要帶這兩欄：`WindowRow` 之 scope 必須與 `event_split` 之 `groupby("symbol")`
#  同源，而 purge 下界是 per-symbol 的。若讓下游各自回頭去 events 表查一次，
#  「alignment 成功的那一列」與「查表拿到的那一列」在 coverage 過濾後就可能不是同一批
#  ——那正是 §D-3′-a（ii) 禁止的 per-scope 冒充。值一律經 `keys.py` 之兩個 accessor 取得。
#  🔴 **兩欄一律 append 在尾端，不得插進中間**：`flatten_receipt_schema` 之驗收
#  （`tests/api/test_gap3_contract_reason_registry.py::…_08a_flatten_prefix_preserved`）
#  斷言新 schema 之攤平名單須**前綴保留** migration 前的順序。插中間會直接弄紅它——
#  實際踩過一次，不是推測。
_EVENT_COLS = [
    "event_id", "t0_ms", "decision_offset_bars", "decision_at_ms", "entry_at_ms",
    "entry_price_source_bar_open_ms", "entry_price_source_field",
    "label_start_ms", "label_end_ms", "entry_after_label_start",
    "symbol", "timeframe",
]
_PER_TF_COLS = ["event_id", "timeframe", "feature_cutoff_ms", "last_bar_open_ms", "last_bar_close_ms", "row_id"]


class _EventFailure(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _validate_bar_table(bars: pd.DataFrame) -> str:
    """回傳 '' 表示合法，否則對應 alignment failure reason。"""
    for col in ("open_time_ms", "close_time_ms", "open", "close"):
        if col not in bars.columns:
            return "missing_bar"
    ot = bars["open_time_ms"].to_numpy()
    ct = bars["close_time_ms"].to_numpy()
    for arr in (ot, ct):  # CODEX-R1-P1-04：close_time 同受守護（cutoff searchsorted 依賴其排序）
        if len(arr) and arr.dtype.kind not in ("i", "u"):
            return "invalid_timestamp_unit"
        if len(arr) and arr.dtype.kind == "u" and int(arr.max()) > np.iinfo(np.int64).max:
            return "invalid_timestamp_unit"
        arr = arr.astype(np.int64)  # CODEX-R2-P1-01：uint64 差分下溢會讓降序看似升序，一律轉有號再差分
        if len(arr) and int(arr.min()) < 10**12:
            return "invalid_timestamp_unit"  # 量級像秒（D2-3）
        if len(arr) > 1 and (np.diff(arr) < 0).any():
            return "unsorted_bar"
        if len(arr) != len(np.unique(arr)):
            return "duplicate_bar"
    if len(ot) and (ct.astype(np.int64) <= ot.astype(np.int64)).any():
        return "tf_boundary_ambiguous"  # close_time 須嚴格晚於 open_time
    return ""


def _append_failure(fail_rows: List[dict], event_id, reason: str) -> None:
    """失敗記帳唯一寫入點（CODEX-R1-P1-01：M1 production seam——monkeypatch 吞記帳
    即破記帳守恆 n_input == n_receipts + n_failures，測試必紅）。"""
    fail_rows.append({"event_id": event_id, "reason": reason})


def _decision_idx(t0_idx: int, k: int) -> int:
    """decision bar index＝t0 往前第 k 根實際 bar（AR-1）。

    獨立小函式以供 mutation guard（M9 offset 竄改／W11 decision>t0 守衛）monkeypatch 驗證可證偽。
    """
    return t0_idx - k


def _select_cutoff_idx(close_ms: np.ndarray, decision_at_ms: int) -> int:
    """feature_cutoff 選列規則＝max{bar.close_ms ≤ decision_at}（as-of）；無 ⇒ -1。

    獨立小函式以供 mutation guard（M2 cutoff_shift_one_bar）monkeypatch 驗證可證偽。
    """
    idx = int(np.searchsorted(close_ms, decision_at_ms, side="right")) - 1
    return idx


def _entry_mapping(semantic: str, anchor: pd.DataFrame, t0_idx: int, decision_idx: int) -> Tuple[int, str]:
    """D1-6 entry 語意 → (bar_idx, price_field)。bar 不存在 ⇒ raise missing_bar。"""
    if semantic == "trigger_open":
        return t0_idx, "open"
    if semantic == "trigger_close":
        return t0_idx, "close"
    if semantic == "next_open":
        if t0_idx + 1 >= len(anchor):
            raise _EventFailure("missing_bar")
        return t0_idx + 1, "open"
    if semantic == "decision_bar_open":
        return decision_idx, "open"
    if semantic == "decision_bar_close":
        return decision_idx, "close"
    raise _EventFailure("no_boundary_match")


def align_events(
    events: pd.DataFrame,
    bars_by_tf: Dict[str, Dict[str, pd.DataFrame]],
    config: AlignmentConfig,
) -> Tuple[AlignmentReceipts, pd.DataFrame]:
    """逐事件推導兩層收據；失敗事件入 failures{event_id, reason}（單一 reason，fail-closed）。"""
    ev_rows: List[dict] = []
    tf_rows: List[dict] = []
    fail_rows: List[dict] = []

    # bar 表健檢結果快取：(symbol, tf) -> reason（'' 合法）
    bar_status: Dict[Tuple[str, str], str] = {}

    def bars_of(symbol: str, tf: str) -> pd.DataFrame:
        sym = bars_by_tf.get(symbol)
        if sym is None or tf not in sym:
            raise _EventFailure("missing_bar")
        key = (symbol, tf)
        if key not in bar_status:
            bar_status[key] = _validate_bar_table(sym[tf])
        if bar_status[key]:
            raise _EventFailure(bar_status[key])
        return sym[tf]

    for rec in events.to_dict("records"):
        eid = rec["event_id"]
        try:
            # 🔴 Task 7.0b：scope／觸發 TF 一律經 `keys.py` 之唯一取值點，不在此自寫第二份。
            tf = event_trigger_timeframe(rec)
            symbol = event_scope_key(rec)
            t0 = int(rec["t0"])
            k = int(rec.get("decision_offset_bars", 0))
            anchor = bars_of(symbol, tf)
            ot = anchor["open_time_ms"].to_numpy()
            ct = anchor["close_time_ms"].to_numpy()

            pos = int(np.searchsorted(ot, t0))
            if pos >= len(ot) or int(ot[pos]) != t0:
                raise _EventFailure("no_boundary_match")  # t0 必為錨定 TF bar open_time
            t0_idx = pos

            decision_idx = _decision_idx(t0_idx, k)
            if decision_idx < 0:
                raise _EventFailure(f"warmup_insufficient_{tf}")
            decision_at = int(ot[decision_idx])
            # D2-2／AR-1 獨立不變式（W11；三段鏈之外）
            if decision_at > t0:
                raise _EventFailure("no_boundary_match")

            entry_idx, field = _entry_mapping(rec["entry_price_semantic"], anchor, t0_idx, decision_idx)
            entry_at = int(ot[entry_idx]) if field == "open" else int(ct[entry_idx])
            entry_price = float(anchor[field].to_numpy()[entry_idx])
            if not np.isfinite(entry_price) or entry_price <= 0:
                raise _EventFailure("nonpositive_reference_price")

            ld = rec["label_definition"]
            mode = ld["label_return_mode"]
            horizon = int(ld["window"]["horizon_bars"])
            if mode == "close_to_close":
                label_start = int(ct[t0_idx])
                end_idx = t0_idx + horizon
            elif mode == "open_to_close":
                label_start = entry_at
                end_idx = entry_idx
            elif mode == "open_to_horizon_close":
                label_start = entry_at
                end_idx = entry_idx + horizon
            else:  # 契約層已擋；防禦
                raise _EventFailure("no_boundary_match")
            if end_idx >= len(ct):
                raise _EventFailure("label_window_incomplete")
            label_end = int(ct[end_idx])
            end_close = float(anchor["close"].to_numpy()[end_idx])
            if not np.isfinite(end_close) or end_close <= 0:
                raise _EventFailure("nonpositive_reference_price")

            # 三段鏈（D2-1；R4 W1：entry_at 對 label_start 無強制順序）
            if entry_at < decision_at:
                raise _EventFailure("entry_before_decision")
            if not (decision_at <= label_start < label_end):
                raise _EventFailure("no_boundary_match")
            if not (entry_at < label_end):
                raise _EventFailure("label_window_incomplete")

            # per-TF feature_cutoff（as-of；非整點邊界不報錯）
            tfs = tuple(config.timeframes) or (tf,)
            tf_batch: List[dict] = []
            for sub_tf in tfs:
                sub = bars_of(symbol, sub_tf)
                sub_ct = sub["close_time_ms"].to_numpy()
                idx = _select_cutoff_idx(sub_ct, decision_at)
                if idx < 0:
                    raise _EventFailure(f"warmup_insufficient_{sub_tf}")
                cutoff = int(sub_ct[idx])
                if cutoff > decision_at:  # PIT 鏈：feature_cutoff ≤ decision_at
                    raise _EventFailure("feature_after_decision")
                tf_batch.append({
                    "event_id": eid, "timeframe": sub_tf, "feature_cutoff_ms": cutoff,
                    "last_bar_open_ms": int(sub["open_time_ms"].to_numpy()[idx]),
                    "last_bar_close_ms": cutoff, "row_id": int(idx),
                })

            ev_rows.append({
                # 🔴 Task 7.0b：`symbol`／`timeframe` 與下游 groupby／purge 同源（見 `keys.py`）。
                "event_id": eid, "symbol": symbol, "timeframe": tf,
                "t0_ms": t0, "decision_offset_bars": k,
                "decision_at_ms": decision_at, "entry_at_ms": entry_at,
                "entry_price_source_bar_open_ms": int(ot[entry_idx]),
                "entry_price_source_field": field,
                "label_start_ms": label_start, "label_end_ms": label_end,
                # 語意＝entry 不早於 label 錨（>=）：連續 crypto 網格下 next_open 之 entry_at
                # 恰等於 t0 close（=label_start），SPEC D2-1 明定該組合 ⇒ true，故用 >= 非 >。
                "entry_after_label_start": bool(entry_at >= label_start),
            })
            tf_rows.extend(tf_batch)
        except _EventFailure as ef:
            _append_failure(fail_rows, eid, ef.reason)

    receipts = AlignmentReceipts(
        event_level=pd.DataFrame(ev_rows, columns=_EVENT_COLS),
        per_tf=pd.DataFrame(tf_rows, columns=_PER_TF_COLS),
    )
    failures = pd.DataFrame(fail_rows, columns=["event_id", "reason"])
    return receipts, failures


def n_dropped_by_reason(failures: pd.DataFrame) -> Dict[str, int]:
    """失敗摘要（M1 記帳守恆之輔助；空 ⇒ {}）。"""
    if failures.empty:
        return {}
    return failures.groupby("reason")["event_id"].count().to_dict()
