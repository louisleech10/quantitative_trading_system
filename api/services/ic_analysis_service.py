"""IC analysis service for task management."""

from __future__ import annotations

import asyncio
import json
import math
import threading
import uuid
from io import BytesIO
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import h5py
import numpy as np
import pandas as pd

from api.core.config import settings
from api.core.logging import get_logger
from api.services import ic_result_projection as _proj
from api.models.ic_models import (
    load_ic_result_paging_contract,
    DeepAnalysisRequest,
    ICAnalyzeRequest,
    ICFullAnalysisRequest,
    ICResultV2Response,
)
from momentum.factories import (
    create_feature_library,
    create_feature_reader,
    create_ic_analyzer,
    create_ic_artifact_writer,
    create_ic_reporter,
    create_kline_storage_manager,
    resolve_run_feature_count,
    sanitize_factor_returns,
)
from momentum.core.contracts import ICResult
from momentum.core.exceptions import AnalysisCancelled


logger = get_logger("api.ic_analysis_service")


class ResultRevisionMismatch(Exception):
    """ICRESULT_PAGING §C-7：請求帶 revision 與現行不符（route 409）。"""

    def __init__(self, current_revision: Optional[int], requested: Optional[int]) -> None:
        super().__init__(f"result revision mismatch: current={current_revision} requested={requested}")
        self.current_revision = current_revision
        self.requested = requested


class ResultValidationError(Exception):
    """ICRESULT_PAGING §C-7(b)：refilter 結果未過出口守衛（先驗後寫；route 422）。"""

#: 合理性上界＝2100-01-01（epoch 秒）。超出即判 parse failure（SPEC Task 7.7 ④ 之字面）。
_EPOCH_SECONDS_UPPER_BOUND = 4102444800

#: `G3-D2` D5.3：隨機對照批之 `sample_design` 揭露字面（觸發批為 `case_control`）。
RANDOM_SAMPLE_DESIGN = "unconditional_random"

#: 規則身分閘要求觸發批之報酬量法必須是這個值（隨機批固定 `close_to_close`；CODEX-R3-P1-02）。
_IDENTITY_LABEL_RETURN_MODE = "close_to_close"


@dataclass(frozen=True)
class CompareVerdict:
    """`G3-D2` D5.3：觸發批 vs 隨機對照批之比較結論。

    `status ∈ {"ok", "unavailable"}`；`unavailable` 時 `reason` 取自契約
    `capability_unavailable_reasons` 之封閉集合（四個 `random_control_*`）。
    🔴 **沒有第三種狀態**：比較要嘛成立、要嘛具名不成立。回一個「大概可以參考」
       的中間態等於把判斷推給使用者，而使用者手上沒有判斷所需的資訊。
    """

    status: str
    reason: Optional[str] = None
    message: Optional[str] = None
    trigger_prevalence: Optional[float] = None
    random_prevalence: Optional[float] = None
    lift: Optional[float] = None
    n_trigger: int = 0
    n_random: int = 0
    sample_design: str = RANDOM_SAMPLE_DESIGN
    #: 抽樣缺額之揭露（`n_drawn << n_requested` 時必須看得到；`D-001` D5.3 邊界②）。
    n_requested: Optional[int] = None
    n_drawn: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FeatureRunCoverageError(ValueError):
    """Task 7.7 之 fail-closed 例外。`reason` 取自 `ic_report_contract.reasons.analysis_rejected`。"""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(f"{reason}: {message}")


def _find_event_filter_info(node: Any) -> Optional[Dict[str, Any]]:
    """在報告 metadata 樹中找 `event_filter` dict（stage3 event_info 之落點）。"""
    if isinstance(node, dict):
        hit = node.get("event_filter")
        if isinstance(hit, dict):
            return hit
        for value in node.values():
            found = _find_event_filter_info(value)
            if found is not None:
                return found
    return None


def _binary_label_domain(records: Any) -> tuple:
    """EVTLABEL Task 3.3（R1 C14c）：匯入 0/1 標籤之**值域閘**。

    回 `(ok, reason)`：
    - `(True, None)`：每一筆 `label` 都存在、有限、且整數值 ∈ {0, 1}。
    - `(False, "no_label_column")`：整批都沒有 `label` 欄（legacy 匯入）。
    - `(False, "label_invalid_domain")`：有 `label` 但至少一筆不是 0/1（含 None／NaN／2／−1／0.5）。

    🔴 為什麼要**先擋**而不是事後轉型：`int(0.5)==0`、`bool(2)==True`、`float("nan")` 進了
    Mann-Whitney 會被 `nan_policy="omit"` 默默丟掉。任何一種都會讓「使用者標的 2」
    悄悄變成「反例」，而報告上看不出來。值域不對就不得靜默降級——
    `imported_binary` 明示模式由呼叫端 raise（route 422），`auto` 只記 hint 並改走報酬版。
    `reason` 字面出自 `event_label_mode.json::label_mode_reasons`。
    """
    import math

    seen_any = False
    for rec in records or ():
        if "label" not in rec:
            continue
        seen_any = True
        raw = rec.get("label")
        # 🔴 型別先擋、值再擋。`event_import_contract.json` 已宣告 `label: int, enum [0,1]`
        #    ⇒ 到這裡還是字串就代表上游少做了一次轉型，`float("1")` 會把它**靜默補上**，
        #    那道漏洞往後只會擴大（下一個是 "yes"／"true"）。bool 是 int 的子類，放行。
        if not isinstance(raw, (int, float)) or isinstance(raw, complex):
            return (False, "label_invalid_domain")
        val = float(raw)
        if not math.isfinite(val) or not val.is_integer() or int(val) not in (0, 1):
            return (False, "label_invalid_domain")
    if not seen_any:
        return (False, "no_label_column")
    return (True, None)


def _assert_binary_rows_bound(staged: Dict[str, Any], info: Dict[str, Any]) -> None:
    """EVTLABEL Task 3.3：0/1 標籤那一腿的回綁，fail-closed。

    orchestrator 回報 `consumed_event_binary_rows = {event_id: [ms, label]}`；本函式拿它對
    service 自 records **獨立快照**建的 `event_binary_rows_by_id` 逐筆比三項（id、ms、0/1），
    並要求**鍵集相等**。

    🔴 為什麼要比 `ms` 而不只比 label：165 個事件裡有 136 個正例，光比 label 值時
    「把兩個正例的時間戳對調」是察覺不到的——而那正是最難查的錯（統計還是會跑出數字）。
    """
    produced = staged.get("event_binary_rows_by_id")
    if not isinstance(produced, dict) or not produced:
        raise ValueError(
            "imported_binary_label run 但 service 端沒有 event_binary_rows_by_id 快照"
            "——無法回綁 (event_id, ms, 0/1)，fail-closed"
        )
    consumed = info.get("consumed_event_binary_rows")
    if not isinstance(consumed, dict) or not consumed:
        raise ValueError(
            "imported_binary_label run 之報告缺 consumed_event_binary_rows"
            "——orchestrator 必須回報實際消費的 0/1 三元組"
        )
    missing = sorted(set(produced) - set(consumed))
    extra = sorted(set(consumed) - set(produced))
    if missing or extra:
        raise ValueError(
            f"0/1 標籤之事件鍵集不一致：未被消費={missing[:5]} 多出來={extra[:5]}"
        )
    for eid, pair in consumed.items():
        src_ms, src_lab = produced[str(eid)]
        try:
            got_ms, got_lab = int(pair[0]), int(pair[1])
        except (TypeError, ValueError, IndexError) as exc:
            raise ValueError(f"事件 {eid!r} 之 consumed_event_binary_rows 形狀非 (ms, label)：{pair!r}") from exc
        if got_ms != int(src_ms) or got_lab != int(src_lab):
            raise ValueError(
                f"事件 {eid!r} 之 0/1 三元組不符：消費 (ms={got_ms}, label={got_lab})"
                f" != 產生 (ms={int(src_ms)}, label={int(src_lab)})"
            )


def _assert_event_triple_bound(staged: Dict[str, Any], report: Any) -> None:
    """EVTALIGN Task 2.1（D）：`(event_id, timestamp, label_value)` 三元組之**最後一腿**，fail-closed。

    orchestrator 以 `event_label_owners` 把每個被消費列綁到恰一個 event_id，並回報
    `consumed_event_labels = {event_id: 被消費的 label}`。本函式拿它對本 service **自己**的逐事件
    label 來源（`event_label_by_id`，與 owners 同一迴圈產生）逐筆回比：
    多一個 id／少回報／值不同 ⇒ raise。R2 三家指出「timestamp→value 三檢查容許事件值旋轉或
    event_id 錯配」——旋轉會讓某 id 的被消費值 ≠ 產生值，在此現形。
    事件不足 fallback（`label_source=mainline_return_N`）沒有被消費之事件 label，已由
    `conditional_ic_abandoned` loud 揭露，此處不重複判。
    """
    if not isinstance(report, dict):
        raise ValueError("IC report is not a dict; cannot bind event triple")
    info = _find_event_filter_info(report.get("metadata"))
    if info is None:
        raise ValueError("event-mode report lacks metadata.event_filter; cannot bind event triple")
    # 🔴 EVTLABEL Task 3.3（R1 C5）：依 `label_source` 分派。
    #    `imported_binary_label` 走**兩腿**——報酬那一腿照舊（報酬版 IC 仍算，留第二欄），
    #    再加 0/1 那一腿逐筆回比 `(event_id, ms, 0/1)` 三項。少了第二腿，
    #    orchestrator 把 0/1 換成另一份而報酬沒動時，這裡會全綠。
    label_source = info.get("label_source")
    if label_source == "imported_binary_label":
        _assert_binary_rows_bound(staged, info)
    elif label_source != "event_label_value":
        return
    consumed = info.get("consumed_event_labels")
    if not isinstance(consumed, dict) or not consumed:
        raise ValueError(
            "event-mode report lacks consumed_event_labels; cannot bind (event_id, timestamp, label_value)"
        )
    by_id: Dict[str, float] = staged["event_label_by_id"]
    for eid, val in consumed.items():
        src = by_id.get(str(eid))
        if src is None:
            raise ValueError(f"consumed event_id {eid!r} was not produced by this event batch")
        if float(src) != float(val):
            raise ValueError(f"event {eid!r}: consumed label {val!r} != produced label {src!r}")


def _apply_stage_progress(task_info: Dict[str, Any], payload: Dict[str, Any], message: Any) -> None:
    """EVTALIGN Task 4.1：把 orchestrator 之階段內進度（`sub_*`／ETA）與 WARN 寫進 task_info。

    - `sub_progress`：`{step, done, total, eta_seconds, eta_state, message}`；`eta_state=="estimating"` ⇒ 前端顯示「預估中」，**不填假 ETA**。
    - `warnings`：`{code, detail}` 去重 append；🔴 WARN 只揭露、不改 status、不擋（§C-4）。
    """
    if "sub_total" in payload:
        task_info["sub_progress"] = {
            "step": payload.get("sub_step"), "done": payload.get("sub_done"),
            "total": payload.get("sub_total"), "eta_seconds": payload.get("eta_seconds"),
            "eta_state": payload.get("eta_state"), "message": message,
        }
    if payload.get("warning"):
        warnings_list = task_info.setdefault("warnings", [])
        code = str(payload["warning"])
        if not any(w.get("code") == code for w in warnings_list):
            warnings_list.append({"code": code, "detail": payload.get("warning_detail")})
    if payload.get("fallback_reason"):
        # 降級重跑**當下**就揭露（不等報告）；sub_progress 歸零，避免上一輪的「完成」殘留誤導
        task_info["fallback"] = {"reason": str(payload["fallback_reason"]), "details": payload.get("fallback_details")}
        task_info["sub_progress"] = None


_WS_STAGE_PROGRESS_KEYS = (
    "sub_step", "sub_done", "sub_total", "eta_seconds", "eta_state", "warning", "warning_detail",
    "fallback_reason", "fallback_details",
)


def _ws_stage_progress_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """EVTALIGN Task 4.1：orchestrator progress payload 中要**原樣轉發到 WebSocket** 的階段內進度／WARN 欄位。

    只轉發存在的鍵（沒有就不補 None——前端以 `typeof sub_total === 'number'` 判斷）。與 `_apply_stage_progress`（寫 task_info）
    是同一組來源欄位，兩條通道不得漂移。
    """
    return {k: payload[k] for k in _WS_STAGE_PROGRESS_KEYS if k in payload}


def _inject_label_rule_disclosure(staged: Dict[str, Any], report: Any) -> None:
    """EVTLABEL Task 1.1：事件 run 之報告寫入本次**實際消費**之 label 規則 → `report.metadata.event_label_rule`。

    spec 由 `staged["prepared"].normalized_spec_bytes` 解析（**不讀 request**——route 可能 seed 過）；
    視窗由對齊收據 `windows` 取；`label_source`／`statistic_kind` 抄 orchestrator 已寫之 `event_filter`。
    只在事件路徑（有 staged）呼叫；非事件 run 不寫此鍵 ⇒ G-1 全域 golden 逐位元組不變。
    切分未套用仍寫（邊界③：label 規則與切分無關）。計算在 `momentum/Analysis/event_label_mode.py`（純函式）。
    """
    if not isinstance(report, dict):
        return
    metadata = report.get("metadata")
    if not isinstance(metadata, dict):
        return
    prepared = staged.get("prepared")
    if prepared is None:
        return
    from momentum.factories import create_event_sample_pipeline  # R3：經 factory，不直接 import momentum.Analysis

    pipeline = create_event_sample_pipeline()
    spec = json.loads(bytes(prepared.normalized_spec_bytes).decode("utf-8"))
    info = _find_event_filter_info(report) or {}
    metadata["event_label_rule"] = pipeline.build_event_label_rule(
        normalized_spec=spec,
        windows=prepared.windows,
        records=staged.get("records") or (),
        feature_timeframe=metadata.get("timeframe"),
        timeframe_seconds=staged.get("timeframe_seconds") or {},
        label_source=info.get("label_source"),
        statistic_kind=info.get("statistic_kind"),
        n_events_consumed=len(staged.get("event_label_by_id") or {}),
        # R1 `CODEX-R1-P1-01`：揭露之分母＝**實際被消費**的事件（已排除非本次 run symbol 者）。
        consumed_event_ids=list((staged.get("event_label_by_id") or {}).keys()),
    )


def _inject_isolation_source(staged: Dict[str, Any], report: Any) -> None:
    """EVTALIGN Task 5.1：事件分析之隔離區兩塊來源分開揭露 → `report.metadata.isolation`。

    🔴 **EVTLABEL Task 2.3 起語意已變**（B2 review R1 三家同判 docstring 過期）：
    `purge` 之來源**抄** orchestrator 寫的 `ic_train_test_split.purge_gap_source`
    （唯一判定點；值為 `event_label_window`／`mainline_horizon`，舊報告缺鍵才回退 `global_default_horizon`）；
    `embargo` 之來源由**本函式**判——比較 `lookahead_depth_rows`（挑樣本時偷看多遠）與
    `embargo_before_event`（抬高前之 config 值），只有 service 知道後者。
    答案窗**不再**參與 embargo 之來源判定：它現在歸 purge 管（Task 2.2）。

    以下為 EVTALIGN 時代之原始說明，保留以理解舊報告：
    使用者混淆點（三家 R1 點名）：`purge_gap` 用**全域 default_horizon** 算，與事件 label 設的 h 無關；
    `embargo` 則是本 service 以事件 look-ahead（`purge_rows`）抬高後的值。兩塊**相加**＝總隔離（保守，非洩漏）。
    數字**全部取自** orchestrator 已寫的 `metadata.ic_train_test_split`（單一來源、不重算、不改算法）；本函式只補
    「來源」：`purge_rows > 原 config embargo` ⇒ `event_lookahead`，否則 `config_embargo`。
    🔴 只在事件路徑呼叫（有 staged），且切分未套用（無 `ic_train_test_split.applied`）⇒ 不寫鍵（邊界①：不顯示 0）。
    非事件 run 不寫此鍵 ⇒ 既有 golden（整份報告 canonical sha）逐位元組不變；與 TODO「orchestrator 新增」之落點不同，
    理由即此（golden `test_gap2_golden` 對整份報告取 sha）。
    """
    if not isinstance(report, dict):
        return
    # EVTLABEL Task 1.1：label 規則揭露與切分無關 ⇒ 先寫（邊界③：切分未套用仍寫），再處理 isolation。
    _inject_label_rule_disclosure(staged, report)
    metadata = report.get("metadata")
    split = metadata.get("ic_train_test_split") if isinstance(metadata, dict) else None
    if not isinstance(split, dict) or not split.get("applied"):
        return
    purge_bars = int(split.get("purge_gap") or 0)
    embargo_bars = int(split.get("embargo") or 0)
    purge_rows = int(staged.get("purge_rows") or 0)
    depth_rows = int(staged.get("lookahead_depth_rows") or 0)
    window_rows = int(staged.get("label_window_rows") or 0)
    before = int(staged.get("embargo_before_event") or 0)
    effective_horizon = split.get("effective_horizon")
    # 🔴 EVTLABEL Task 2.3：purge 之來源改抄 orchestrator 寫的 `purge_gap_source`（唯一判定點），
    #    embargo 之來源仍由**本函式**判（R1 C7：只有 service 知道「抬高前的原 config embargo」）。
    purge_source = split.get("purge_gap_source") or "global_default_horizon"
    # 🔴 B2 review R1（三家同提）：W==H 時來源標 `mainline_horizon` 算術正確，但字面易讓使用者
    #    以為「答案窗沒被算進去」。⇒ note 分三種寫法，把「兩者相等」講明白（來源字面不動，
    #    因為它是機器判定值，改成第三個值會讓下游枚舉變大）。
    if purge_source == "event_label_window":
        purge_note = f"由你設的 label 答案窗換算：max(主線 horizon {effective_horizon}, 答案窗 {window_rows} 根)"
    elif window_rows and window_rows == effective_horizon:
        purge_note = f"答案窗（{window_rows} 根）與主線 horizon 相等，兩者都已算進去（max 取同值）"
    else:
        purge_note = f"由主線 horizon 決定（{effective_horizon} 根）；label 答案窗（{window_rows} 根）沒有比它長"
    metadata["isolation"] = {
        "purge": {
            "bars": purge_bars,
            "source": purge_source,
            "effective_horizon": effective_horizon,
            "event_label_window_rows": window_rows,
            "note": purge_note,
        },
        "embargo": {
            "bars": embargo_bars,
            "source": "event_lookahead_depth" if depth_rows > before else "config_embargo",
            "lookahead_depth_rows": depth_rows,
            "event_purge_rows": purge_rows,  # 舊欄保留供對照（＝max(深度, 窗)）
            "config_embargo": before,
        },
        "total_bars": purge_bars + embargo_bars,
        "note": "總隔離＝purge＋embargo（相加，只會偏保守）",
    }


def _inject_period_alignment(staged: Dict[str, Any], report: Any) -> None:
    """EVTALIGN Task 3.1：把 service 端之期間對齊揭露（丟掉的事件 ID）併進 `report.metadata.period_alignment`。

    orchestrator 端（feature ∩ kline 之裁切）若已寫同鍵則合併，不覆蓋。
    🔴 只在**有事件被丟**時寫鍵——沒丟任何事件且 orchestrator 亦未裁切時不新增鍵（§G-1 golden 逐位元組不變）。
    """
    pa = staged.get("period_alignment")
    if not isinstance(report, dict) or not isinstance(pa, dict):
        return
    if int((pa.get("dropped_events") or {}).get("count") or 0) == 0 and "period_alignment" not in (report.get("metadata") or {}):
        return
    metadata = report.setdefault("metadata", {})
    merged = dict(metadata.get("period_alignment") or {})
    merged.update({k: v for k, v in pa.items()})
    metadata["period_alignment"] = merged


def _parse_time_range_endpoint(value: Any) -> int:
    """`time_range` 之單一端點字串 → epoch ms。**解析順序寫死：先數字後 ISO**（SPEC 7.7 ④）。

    🔴 為什麼順序不能反：現存非 legacy manifest 的 `time_range` 是 **epoch 秒之數字字串**
    （實測 12/14 份如此，例 `{"start": "1704067200", ...}`）。先試 `fromisoformat` 會對它直接
    raise ⇒ **全部現存 run 都會被判成 parse failure**。R5 版就是這樣寫的，三家全員以真實
    manifest 打穿。

    🔴 tz-naive ISO ⇒ fail-closed，**不當成 UTC**：把 naive 當 UTC 是個假設，
    假設錯了整個覆蓋判斷會偏移，而偏移多少取決於使用者的時區——看不出來也修不掉。
    """
    if not isinstance(value, str):
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_timestamp_format",
            f"time_range 端點須為字串，實得 {type(value).__name__}",
        )
    s = value.strip()
    body = s[1:] if s.startswith("-") else s
    if body.isdigit():
        seconds = int(s)
        if not (0 < seconds < _EPOCH_SECONDS_UPPER_BOUND):
            raise FeatureRunCoverageError(
                "feature_coverage_unknown_timestamp_format",
                f"epoch 秒 {seconds} 落在合理範圍外（0, {_EPOCH_SECONDS_UPPER_BOUND}）",
            )
        return seconds * 1000
    try:
        parsed = datetime.fromisoformat(s)
    except ValueError as exc:
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_timestamp_format",
            f"既非十進位數字字串亦非 ISO 格式：{s!r}（{exc}）",
        ) from exc
    if parsed.tzinfo is None:
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_timestamp_format",
            f"ISO 字串 {s!r} 為 tz-naive——不得假設為 UTC（假設錯誤會使覆蓋判斷整體偏移）",
        )
    return int(parsed.timestamp() * 1000)


@dataclass(frozen=True)
class FeatureRunCoverage:
    """`check_feature_run_coverage` 之結果（EVTALIGN Task 3.1）。

    `evaluated=False` ⇒ 沒有窗、什麼都沒判（呼叫端沿用 prepared 之全集）。
    `covered_event_ids`／`dropped`：逐事件分類；`dropped` 為 `(event_id, reason)`，
    reason 目前只有 `outside_feature_run`。
    """

    evaluated: bool
    run_start_ms: Optional[int]
    run_end_ms: Optional[int]
    covered_event_ids: tuple
    dropped: tuple

    def disclosure(self) -> Dict[str, Any]:
        """`metadata.period_alignment` 之 service 端部分——🔴 丟掉的事件**必列 ID**（`COMPOSER-R1-P2-01`／`GROK-R1-P1-02`：只報數不等價）。"""
        dropped_ids = sorted(str(eid) for eid, _ in self.dropped)
        return {
            "feature_run": {"start_ms": self.run_start_ms, "end_ms": self.run_end_ms},
            "dropped_events": {
                "count": len(dropped_ids),
                "ids": sorted(dropped_ids),
                "reason": "outside_feature_run",
            },
            "covered_event_count": len(self.covered_event_ids),
        }


def check_feature_run_coverage(
    *,
    timeframe_seconds: Dict[str, int],
    feature_manifest_time_range: Optional[Dict[str, Optional[str]]],
    event_windows,
) -> FeatureRunCoverage:
    """Task 7.7 ③ → EVTALIGN Task 3.1：特徵 run 對事件期之涵蓋，**逐事件**判定。

    🔴 語意變更（2026-09-08，R2 `CODEX-R2-P1-06`＋使用者原話④「還要手動重新生成特徵…太蠢了，是缺陷吧」）：
    原本是**批次級** pass/fail——任一事件超出 run 區間就整批 raise，使用者得回頭重生特徵。
    現在：超出 run 區間的事件**逐一剔除並揭露 ID**（呼叫端以 `apply_event_coverage` 縮集合、
    `period_alignment.dropped_events` 進報告），只有**全部**事件都不在區間內才 fail-closed。
    legacy run（無 time_range）與未知 timeframe 仍 fail-closed（無區間可對證，不能靜默放行）。

    🔴 **唯一入口、keyword-only**：禁 `args[N]`、禁第二入口、禁掛在 pipeline 上當替身。
    🔴 `timeframe_seconds` 是**注入之 map**——SPEC 明禁在本函式內直讀
    `momentum/core/constants.py::TIMEFRAME_SECONDS`。呼叫端建構一次、以**同一物件**
    同時傳給 purge 與本 gate，驗收以 `is` 比對。

    containment（批內全部列皆須成立）：
    ```
    run_start_ms <= min_e decision_at_ms(e)   且   max_e label_end_ms(e) <= run_end_ms
    ```
    🔴 左界用 `decision_at_ms` **而非** `min(t0)`：IC 之特徵截止規則是
    `max_close_ms <= decision_at`，`decision_offset_bars = k > 0` 時 `decision_at < t0`
    ⇒ 用 `min(t0)` 會放行「run 根本沒涵蓋決策時點」的批次，那是個 fail-open 窗口。
    """
    windows = tuple(event_windows)
    if not windows:
        # 沒有窗就沒有東西要涵蓋。這不是錯誤——上游已對「全部對齊失敗」有自己的 loud 路徑。
        return FeatureRunCoverage(False, None, None, (), ())

    # ② 逐列用**該列自己的** timeframe；批內多 TF 允許，但任一列不在注入之鍵集 ⇒ 整批擋。
    for w in windows:
        if w.timeframe not in timeframe_seconds:
            raise FeatureRunCoverageError(
                "feature_coverage_unknown_timeframe",
                f"事件 {w.event_id} 之 timeframe {w.timeframe!r} 不在注入之 timeframe_seconds 鍵集"
                f"（{sorted(timeframe_seconds)}）",
            )

    # ⑤ legacy run：`{"start": None, "end": None}`。
    # 🔴 **缺鍵與 `None` 同等處置**（`D-005` 之偵察輪裁定 1）：實掃 14 份 manifest 有 2 份
    #    完全沒有 `time_range` 鍵，而 SPEC ⑤ 只裁定了 `{None, None}`。兩者資訊量相同
    #    （都拿不到區間），分成兩個 reason 只會讓前端多一種要處理的字面；
    #    且 §C0 只能更嚴，缺鍵放行才是弱化。
    if not isinstance(feature_manifest_time_range, dict):
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_legacy_run",
            "feature run manifest 無 time_range（缺鍵或非 dict）——無法對證涵蓋範圍",
        )
    start_raw = feature_manifest_time_range.get("start")
    end_raw = feature_manifest_time_range.get("end")
    if start_raw is None or end_raw is None:
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_legacy_run",
            f"feature run 之 time_range 為 legacy 形（start={start_raw!r} end={end_raw!r}）"
            "——不得視為『涵蓋全部』而放行",
        )

    run_start_ms = _parse_time_range_endpoint(start_raw)
    run_end_ms = _parse_time_range_endpoint(end_raw)

    # 逐事件：左界比 decision_at、右界比含答案窗之 label_end（閉區間）
    covered: list = []
    dropped: list = []
    for w in windows:
        if run_start_ms <= int(w.decision_at_ms) and int(w.label_end_ms) <= run_end_ms:
            covered.append(str(w.event_id))
        else:
            dropped.append((str(w.event_id), "outside_feature_run"))
    if not covered:
        required_start = min(int(w.decision_at_ms) for w in windows)
        required_end = max(int(w.label_end_ms) for w in windows)
        raise FeatureRunCoverageError(
            "feature_coverage_insufficient",
            f"特徵 run 之區間 [{run_start_ms}, {run_end_ms}] 與事件期 "
            f"[{required_start}, {required_end}] 無交集——{len(windows)} 筆事件全部落在 run 之外"
            f"（左界比 decision_at、右界比含答案窗之 label_end；被丟 ID 前 5 筆：{[e for e, _ in dropped[:5]]}）",
        )
    return FeatureRunCoverage(True, run_start_ms, run_end_ms, tuple(covered), tuple(dropped))


def _feature_run_time_range(*candidates: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
    """由 feature run 之路徑找出 `feature_manifest.json` 並原樣取出 `time_range`。

    🔴 **為什麼在 service 自己讀，而不是由 route 傳進來**：Task 7.7 要對證的是
    「**這次分析實際會載入的那個 run**」是否涵蓋事件期。若由外層先猜一個 run 再傳進來，
    就得複製一份 service 的 run 選擇邏輯——那正是 B9 花了五輪才修完的病
    （閘門與 loader 各算各的，於是每一輪冒出一種新的不一致）。
    這裡直接吃 service 自己已經解析完的 `features_path`／`meta_path`，**沒有第二份選擇邏輯**。

    🔴 **原樣取出、不轉型別**（Task 7.7 ①）：manifest 實測為 epoch 秒之數字字串。
    找不到 manifest ⇒ 回 `None`，由 gate 判 `feature_coverage_unknown_legacy_run`（fail-closed）。
    """
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        for base in (path if path.is_dir() else path.parent, path.parent.parent):
            manifest = base / "feature_manifest.json"
            if not manifest.is_file():
                continue
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            raw = payload.get("time_range") if isinstance(payload, dict) else None
            if isinstance(raw, dict):
                return {"start": raw.get("start"), "end": raw.get("end")}
            return None
    return None


def _resolve_feature_count(request, *, entrypoint: str = "analyze") -> Optional[int]:
    """GAP-3 UX Task 6.3：取這個 run 的特徵數。

    🔴 `CODEX-R4-P2-01`：本函式原本只呼叫 `resolve_run_feature_count`（只認顯式 hash）
      ⇒ **隱式 latest 與所有 `/full-analysis`** 的任務一律回 `None`，
      Task 6.3 的欄位在最常見的兩種用法下都是空的。
      改為委派 `ICAnalysisService.resolve_planned_feature_count`——
      **與止血閘、與實際載入路徑同一支解析**。

    🔴 解析失敗仍回 `None`——**不填假值**。UAT 已證實填充值比沒有更誤導
    （`progress==0.12` 卡 15 分鐘，使用者以為還在動）。
    """
    return ic_analysis_service.resolve_planned_feature_count(request, entrypoint=entrypoint)

FEATURE_KLINE_CACHE_DIR = "data_cache/feature_klines"


class ICAnalysisService:
    """IC analysis service for async task execution."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()
        self._last_task_id: Optional[str] = None
        self._feature_library = create_feature_library()

    @staticmethod
    def _plan_cross_sectional_load(request):
        """橫截面模式下**實際會餵給 `load_multi` 的 `(symbols, config_hashes)`**。

        🔴 **本方法是止血閘與實際載入的唯一共用來源**。R5 兩家各自打出一條反例，
          證明「把選擇規則在兩處各推導一次」即使搬進同一個 class 也不夠：

          | ID | 方向 | 原因 |
          |---|---|---|
          | `COMPOSER-R5-P1-01` | 該擋沒擋 | 逐筆 `config_hash` 為**空字串**時，解析器 `get_entry(…, "")` 回 `None` 放行；而 `load_multi` 看到 falsy hash 會走 `find_latest` ⇒ 實際載入 161,031 |
          | `CODEX-R5-P1-01` | 不該擋卻擋 | 同一 symbol 出現兩次時，loader 以 **symbol 為 dict key**（後者覆蓋前者），而解析器對每一筆取 max ⇒ 誤擋 |

          兩者都是「重新推導」而非「共用」的必然結果。改成本方法之後，
          兩條規則（**dict 去重、後者勝** ／ **空 hash 視同未指定**）各只存在一份。
        """
        runs = list(getattr(request, "cross_sectional_runs", None) or [])
        if runs:
            # 🔴 逐字沿用 loader 原本的 dict comprehension 語意：同 symbol **後者覆蓋前者**
            config_hashes = {item.symbol: item.config_hash for item in runs}
            symbols_resolved = [item.symbol for item in runs]
            return symbols_resolved, config_hashes
        if getattr(request, "symbols", None):
            return list(request.symbols), None
        return None, None

    def resolve_planned_feature_count(self, request, *, entrypoint: str = "analyze") -> Optional[int]:
        """GAP-3 UX Task 6.1／6.3：**這次分析實際會載入的那些 run** 有幾個特徵。

        🔴 **本方法存在的理由＝B9 四輪 review 的共同根因**。
          止血閘原本在 `api/routes/ic_analysis.py` 裡**手抄了一份與本 service 平行的解析**：
          閘門把候選塞成一袋取 `max()`，而本 service 走的是**互斥分支**；
          閘門每次請求 `FeatureRegistry()` 重讀磁碟，而本 service 的 `_feature_library`
          在**行程啟動時**建好、registry 只讀一次。兩份邏輯、兩份快照，於是四輪抓到四種不同步：

          | 輪次 | 形態 | finding |
          |---|---|---|
          | R1 | 袋子少一味（`features_path`）⇒ **該擋沒擋** | `CODEX-R1-P1-01`／`GROK-R1-P1-01` |
          | R2 | 袋子少一味（`cross_sectional_runs`）⇒ 該擋沒擋 | `CODEX-R2-P1-01` |
          | R3 | 袋子少一味（隱式 latest ×2）⇒ 該擋沒擋 | 三家一致 |
          | R4 | 袋子**多**一味 ⇒ **不該擋卻擋**；且兩份 registry 不同步 | `CODEX-R4-P1-01`／`P1-03` |

          修法不是再補一味，是**刪掉那份手抄邏輯**：由「決定要載入什麼的人」回答「它有多大」。
          鏡像因此成為**結構性質**，不再需要人工維護。

        🔴 **分支必須與 `_run_analysis`／`_run_full_analysis` 逐條對齊**（見下方逐段註解）；
          改動其一未改另一，等於把本方法退化回手抄副本。
        🔴 解析不出來回 `None`——**呼叫端自己決定要擋還是要放**，本方法不替它決定。
        🔴 全程只讀 registry（記憶體）與 manifest（數 KB JSON），**不開 HDF5**
          （Task 6.4 之硬性要求：止血閘擋下時不得已載入大矩陣）。
        """
        from momentum.factories import (
            feature_count_from_features_file,
            feature_count_from_registry_entry,
        )

        timeframe = getattr(request, "timeframe", None)

        # ── `/full-analysis`：對齊 `_run_full_analysis` ──
        #    🔴 **它與 `/analyze` 走的不是同一條載入路徑**：`_run_full_analysis` 直接把
        #    `request.features_path` 餵給 `analyzer.analyze`，**從不碰 registry**
        #    （沒有 `get_entry`／`find_latest_materialized`／`load_multi`）。
        #    因此對它去查 latest 會擋掉一個根本不會載入任何 registry run 的請求——
        #    那正是 `CODEX-R4-P1-01` 那一族的誤擋，只是換我自己在結構修正時犯。
        #    **主委自攻抓到，未進 review**；記在這裡是因為它示範了本方法的維護風險：
        #    「鏡像 service」只有在**逐個入口**對齊時才成立，多一個入口就多一份對齊責任。
        if entrypoint == "full_analysis":
            return feature_count_from_features_file(
                getattr(request, "features_path", None),
                symbol=getattr(request, "symbol", None), timeframe=timeframe,
            )

        # ── 橫截面：對齊 `_run_analysis` 之 `mode == "cross_sectional"` 分支 ──
        #    該分支走 `load_multi`，**完全不看**頂層 `features_path`／`config_hash`
        #    ⇒ 閘門也不得把它們算進來（`CODEX-R4-P1-01` 之後半）。
        if getattr(request, "mode", "longitudinal") == "cross_sectional":
            if not timeframe:
                return None
            symbols_resolved, config_hashes = self._plan_cross_sectional_load(request)
            if symbols_resolved is None:
                return None
            # 🔴 **逐字鏡像 `load_multi` 的行為**（`CODEX-R5-P1-01`＋`COMPOSER-R5-P1-01`）：
            #    ① 以 symbol 去重（dict key 語意；同 symbol 只會被載入一次、且用最後那筆 hash）
            #    ② hash 為 falsy（含**空字串**）⇒ 該標的走 `find_latest_materialized`，
            #       與 `feature_library.load(config_hash=None)` 之 `if config_hash:` 一致
            entries = []
            self._feature_library.reload_registry()
            for sym in dict.fromkeys(symbols_resolved):
                raw = (config_hashes or {}).get(sym)
                run_hash = raw.strip() if isinstance(raw, str) else ""
                entries.append(
                    self._feature_library.get_entry(sym, timeframe, run_hash)
                    if run_hash
                    else self._feature_library.find_latest_materialized(sym, timeframe)
                )
            counts = [c for c in (feature_count_from_registry_entry(e) for e in entries)
                      if isinstance(c, int)]
            # 任一標的超標即擋整組——橫截面本來就把它們一起載入，擋掉一筆不會降低峰值
            return max(counts) if counts else None

        # ── longitudinal：對齊 `_run_analysis` 之 else 分支 ──
        #    該分支的最終載入對象是 `features_path`；呼叫端**明確給了** `features_path` 時，
        #    entry 只用來補 meta、**不參與載入** ⇒ 閘門不得再把 latest 算進來
        #    （`CODEX-R4-P1-01`：小 `features_path` 被不相干的大 latest 誤擋）。
        features_path = getattr(request, "features_path", None)
        symbol = getattr(request, "symbol", None)
        if features_path:
            return feature_count_from_features_file(
                features_path, symbol=symbol, timeframe=timeframe,
            )
        if not (symbol and timeframe):
            return None
        config_hash = (getattr(request, "config_hash", None) or "").strip()
        self._feature_library.reload_registry()
        entry = (
            self._feature_library.get_entry(symbol, timeframe, config_hash)
            if config_hash
            else self._feature_library.find_latest_materialized(symbol, timeframe)
        )
        return feature_count_from_registry_entry(entry)

    @staticmethod
    def _run_event_label_stages(
        request: ICAnalyzeRequest,
        event_batch: Dict[str, Any],
        *,
        features_path: Optional[str],
        meta_path: Optional[str],
        feature_manifest_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GAP-3 UX Task 7.0b ④ ＋ 7.7 ③ 之**五階段編排**（§D-3′-a（iii）之落地點）。

        `feature_manifest_path`：registry 條目之 `hdf5_relative_path`（＝該 run 的 `feature_manifest.json`）。
        🔴 UAT B15（2026-09-02，票 `G3-D10`）：註冊 run 之 `features_path` 是物化暫存檔
        `data_cache/reports/ic_ingest_cache/*.h5`，附近沒有 manifest ⇒ coverage 閘一律誤判為 legacy run 而擋掉
        **所有**註冊 run。故 manifest 路徑由 registry 條目直接給，列為第一候選；`features_path`／`meta_path` 仍保留
        供 artifact 重放（呼叫端自帶 h5 者）。

        🔴 **本方法是事件分支的唯一入口**，只在 `request.event_import_id` 存在時被呼叫
        ⇒ cross-sectional 與純特徵 longitudinal **不會**經過這裡（over 向：不得誤擋）。

        🔴 **`timeframe_seconds` 在這裡建構一次**，並以**同一物件**傳給 purge 與 feature-run gate
        （驗收以 `is` 比對）。禁各自建構、禁 gate 內直讀 `momentum/core/constants.py`。

        階段（逐字對應 §D-3′-a（iii)）：
        2. `prepare_analysis_windows` — 唯一產生 receipt 與 hash 之處，**只呼叫一次**
        3a. `check_feature_run_coverage` — 批次級 pass/fail，**不產生 event-id 子集**
        3b. `apply_event_coverage` — 回**新**物件（`replace`），同 token 同 hash
        4. `project_purge` — tuple → read-only Mapping，用完即棄
        5. `resolve_label_value_at_analyze` — 吃階段 2 之**物件**，不重跑 `align_events`

        回純資料 dict：`event_timestamps`／`event_label_values`／`prepared`／`purge`／`reason`。
        """
        from momentum.factories import create_event_sample_pipeline

        pipeline = create_event_sample_pipeline()
        records = tuple(event_batch.get("records") or ())
        if not records:
            raise ValueError(
                f"event_import_id={request.event_import_id!r} 之批次沒有任何 records（fail-closed）"
            )
        spec = event_batch.get("event_label_spec")
        symbols = sorted({str(r["symbol"]) for r in records})
        timeframes = sorted({str(r["timeframe"]) for r in records})

        # 🔴 **建構一次**：下面兩個 consumer 拿到的是**同一個** dict 物件。
        # 🔴 UAT（2026-09-07）：鍵集必須含**分析用 timeframe**，不能只有事件批宣告的那些。
        #    使用者拿 12h 的事件批配 1h 的特徵 run 分析，被
        #    「分析用 timeframe '1h' 不在注入之 timeframe_seconds 鍵集（['12h']）」擋死。
        #    那是過嚴：`purge_ms` 是**時間長度**（與 timeframe 無關），
        #    換算成 1h 的列數只是「同樣一段時間等於幾根 1h」——完全合法，
        #    而且對齊層在這之前就已經把事件成功映射到 1h 的特徵列上了。
        #    跨週期分析（粗週期事件 × 細週期特徵）本來就是這個系統支援的用法。
        #    fail-closed 不變：不認得的 timeframe 仍由 `timeframe_seconds_for` raise，
        #    這裡只是把「要換算的那個 tf」也放進待建構清單，不是補預設值。
        # `getattr` 而非直取：本函式的既有測試用最小假 request（無 `timeframe` 屬性），
        # 直取會把那些測試變成 AttributeError——那不是行為變更，是我打破了它們的前提。
        analysis_tf = str(getattr(request, "timeframe", None) or "").strip()
        tf_inputs = sorted(set(timeframes) | ({analysis_tf} if analysis_tf else set()))
        timeframe_seconds = pipeline.timeframe_seconds_for(tf_inputs)
        bars_by_tf = pipeline.bars_from_kline_cache(symbols, timeframes)

        prepared0 = pipeline.prepare_analysis_windows(          # 階段 2（spy: call_count == 1）
            records, bars_by_tf,
            event_label_spec=spec,
            event_import_id=request.event_import_id,
            lookahead_bars_declared=event_batch.get("lookahead_bars_declared") or {},
            timeframe_seconds=timeframe_seconds,
        )
        coverage = check_feature_run_coverage(                   # 階段 3a（EVTALIGN Task 3.1：逐事件）
            timeframe_seconds=timeframe_seconds,                 # 🔴 同一物件
            feature_manifest_time_range=_feature_run_time_range(feature_manifest_path, features_path, meta_path),
            event_windows=prepared0.windows,
        )
        # 階段 3b：落在 run 區間外的事件在此剔除（縮集合），ID 進 period_alignment 揭露；
        # 沒有窗（evaluated=False）⇒ 沿用全集（`replace` 仍產生新身分）。
        allowed = (
            frozenset(coverage.covered_event_ids) & prepared0.allowed_event_ids
            if coverage.evaluated else prepared0.allowed_event_ids
        )
        prepared1 = pipeline.apply_event_coverage(prepared0, allowed)
        period_alignment = coverage.disclosure() if coverage.evaluated else None
        purge = pipeline.project_purge(prepared1.purge_lower_bound_ms_by_symbol)  # 階段 4
        # 🔴 **`CODEX-R1-P1-02`：階段 4 原本只算不用**——`purge` 存進 local 就沒人消費，
        #    `split_events` 也從未被呼叫 ⇒ **per-symbol purge 對本次分析完全沒有作用**。
        #    根因是單位與粒度都對不上：IC 切分器用的是**列數之全域 scalar** embargo
        #    （`ic_filter_orchestrator._split_rows` 之 `purge_gap`／`embargo`），
        #    而這裡算出來的是**毫秒之 per-symbol** 下界。
        #    🔴 取 max 折成 scalar **正是 §D-3′-a(ii) 明令禁止**的 per-scope 冒充
        #    （本 epic 在 B3／B5 各犯過一次）⇒ 採 B3 之既有先例：
        #    **能表達就套用、不能表達就拒絕**，不默默取 max。
        distinct = {row.purge_lower_bound_ms for row in prepared1.purge_lower_bound_ms_by_symbol}
        if len(distinct) > 1:
            raise ValueError(
                "各 symbol 之 purge 下界不一致（"
                f"{sorted(distinct)}）——IC 切分器只接受全域 scalar embargo，"
                "取 max 會對窗較小之 symbol 過度 purge、取 min 會洩漏，兩者皆為 §D-3′-a(ii) 所禁。"
                "請依 timeframe 拆批後再分析（殘留 R-B10-1）。"
            )
        result = pipeline.resolve_label_value_at_analyze(         # 階段 5
            prepared1, bars_by_tf, event_label_spec=spec,
        )
        if not result.supported:
            # 🔴 支援域字面**不在此硬寫**（`G3-D2` D1.3）：原本寫死
            #    「(trigger_close, close_to_close, k=0)」，D1.3 把矩陣擴成四對之後那句就是
            #    **過期的錯誤訊息**——使用者照它去改設定會改錯。
            #    🔴 走 pipeline 之 R3 出口取字面，**不直接 import `momentum`**
            #    （`scripts/check_decoupling_imports.py` 當場擋下過一次，不是推測）。
            raise ValueError(
                f"事件分析不支援本批之報酬語意（reason={result.reason}）"
                f"——目前支援之組合：{pipeline.supported_matrix_text()}"
            )
        # 🔴 **對齊後一個窗都不剩 ⇒ loud**（`CODEX-R1-P1-03`）：靜默出一張空表，
        #    使用者會看到一份「分析完成但什麼都沒有」的報告，而真正的原因是全批對齊失敗。
        if not prepared1.windows:
            raise ValueError(
                f"事件批 {request.event_import_id!r} 對齊後沒有任何可用窗"
                "（全批對齊失敗或全被 coverage 剔除）——不產出空表"
            )

        # 🔴 `label_value is None`（尾端不足）之 eid **不進 IC**，且**不填 0**。
        # 🔴 UAT（2026-09-02，票 `G3-D17`）：IC 分析對象是**單一 feature run**（`request.symbol`/`timeframe`），
        #    多 symbol 事件批（例：BTCUSDT＋ETHUSDT 同 t0）若一律以時間戳映射，BTC 事件會被拿 ETH 的特徵列來算
        #    ——跨 symbol 污染；同一時間戳兩個 symbol 還會撞成「映射到同一列」的誤導訊息。
        #    規則：只餵 **symbol == run symbol** 的事件；其他 symbol 之事件**具名排除**（計數與 symbol 清單進 receipt／task_info，
        #    log 警告），一筆都不剩 ⇒ loud。跨 symbol 合併分析屬 registry #4（Pooled/Panel IC）之範圍，本路徑不做。
        run_symbol = str(getattr(request, "symbol", "") or "") or None
        excluded_by_symbol: Dict[str, int] = {}
        per_tf = {(p.event_id, p.timeframe): p.feature_cutoff_ms for p in prepared1.per_tf}
        ts_map: Dict[int, float] = {}
        owner: Dict[int, str] = {}
        by_id: Dict[str, float] = {}  # EVTALIGN Task 2.1：逐事件 label 來源，供 analyze 後三元組回綁
        # ── EVTLABEL Task 3.3：匯入 0/1 標籤之向量（與 ts_map **同鍵**：feature_cutoff_ms）──
        # 🔴 `bin_rows_by_id` 由 records **獨立快照**建，不是從 bin_map 反推——它的用途是
        #    analyze 之後回比「orchestrator 消費的那份，還是我送出去的那份嗎」。
        #    若兩者同源，回比就是拿自己比自己（假綠）。
        # 🔴 B3 review R1（`COMPOSER-R1-P1-02`／`GROK-R1-P1-04`，兩家獨立同判）：
        #    值域閘原本掃**全批** records，但 IC 只消費 `symbol == run_symbol` 的事件
        #    ⇒ 混 symbol 批裡「另一個 symbol 的事件 label 壞掉」會擋掉本次 run。
        #    這正是 B1 review 抓過的**同一個錯**（分母用全批），我在 brief 必答 4 自己列為
        #    可疑處、兩家實跑反例確認成立（recs=[ETH 0/1 + BTC label=2] ⇒ 誤判 invalid）。
        #    修法同 B1：先算出**本次真正會被消費**的事件集合，值域閘只掃那些。
        consumed_event_ids = {
            str(w.event_id)
            for w in prepared1.windows
            if (run_symbol is None or str(w.symbol) == run_symbol)
            and result.label_values.get(w.event_id) is not None
        }
        rec_by_id = {str(r.get("event_id")): r for r in records}
        label_ok, label_hint = _binary_label_domain(
            [rec_by_id[eid] for eid in sorted(consumed_event_ids) if eid in rec_by_id]
        )
        bin_map: Dict[int, int] = {}
        bin_rows_by_id: Dict[str, tuple] = {}
        for w in prepared1.windows:
            if run_symbol is not None and str(w.symbol) != run_symbol:
                excluded_by_symbol[str(w.symbol)] = excluded_by_symbol.get(str(w.symbol), 0) + 1
                continue
            value = result.label_values.get(w.event_id)
            if value is None:
                continue
            cutoff = per_tf.get((w.event_id, w.timeframe))
            if cutoff is None:
                raise ValueError(
                    f"事件 {w.event_id} 無 {w.timeframe} 之 per-TF 收據——不得靜默略過"
                )
            key = int(cutoff)
            # 🔴 **兩事件映射到同一個 feature 列 ⇒ raise**（`CODEX-R1-P1-03`）：
            #    原本這裡是 `ts_map[key] = value`，後到的會**靜默覆蓋**先到的
            #    ——那等於默默丟掉一個事件，而且丟哪一個取決於迭代順序。
            #    `ic_feed.py:79-81` 對同一情形本來就 raise（`禁默默覆蓋；請先 dedupe`），
            #    我這條路徑繞過了 `ic_feed` 就把那道保護一起繞掉了。
            if key in owner:
                raise ValueError(
                    f"事件 {owner[key]} 與 {w.event_id}（同 symbol {run_symbol or w.symbol}）映射到同一個 feature 列 {key}"
                    "（禁默默覆蓋；請先 dedupe）"
                )
            owner[key] = w.event_id
            ts_map[key] = float(value)
            by_id[str(w.event_id)] = float(value)
            # EVTLABEL Task 3.3：值域過關才建 0/1 向量；不過關 ⇒ 整個不建（由 hint 揭露原因）。
            if label_ok:
                rec = rec_by_id.get(str(w.event_id))
                if rec is None or "label" not in rec:
                    # 值域閘掃的是整批 records；被消費的事件卻查不到自己那一筆 ⇒ 兩份資料對不上，
                    # 不得靜默略過（略過會讓 bin_map 比 ts_map 短，兩者分母不同即統計失真）。
                    raise ValueError(
                        f"事件 {w.event_id} 有 label_value 卻在 records 找不到對應 label 欄——"
                        "兩份資料對不上，禁靜默略過"
                    )
                lab = int(float(rec["label"]))
                bin_map[key] = lab
                bin_rows_by_id[str(w.event_id)] = (key, lab)
        if excluded_by_symbol:
            logger.warning(
                "事件批 %s：%d 筆事件之 symbol 不是本次 run 的 %s，已排除（%s）——跨 symbol 合併分析屬 Pooled/Panel IC 票，本路徑不做",
                request.event_import_id, sum(excluded_by_symbol.values()), run_symbol, excluded_by_symbol,
            )
        if not ts_map:
            raise ValueError(
                f"事件批 {request.event_import_id!r} 沒有任何 symbol == {run_symbol!r} 且有 label_value 的事件可餵進 IC"
                f"（排除之 symbol：{excluded_by_symbol or '無'}）——請選同 symbol 的 feature run 或拆批"
            )

        # ── EVTLABEL Task 3.3：明示 `imported_binary` 之 fail-closed（`auto` 一律不 raise）──
        # 🔴 明示與 auto 的差別就是「說不行的時候會不會出聲」：使用者明講要用 0/1，
        #    卻因值域壞掉／沒有 label 欄而拿到一份報酬版報告，是最糟的靜默降級。
        requested_mode = str(event_batch.get("event_label_mode") or "auto")
        if requested_mode == "imported_binary":
            if not label_ok:
                raise ValueError(
                    f"{label_hint}: 事件批 {request.event_import_id!r} 的 label 欄"
                    "不是每一筆都為 0 或 1（明示 imported_binary 模式不接受靜默降級）"
                )
            if event_batch.get("event_label_scan"):
                raise ValueError(
                    "scan_not_applicable_in_imported_binary_mode：掃描是對 k×h 逐格重算報酬，"
                    "匯入標籤模式不用 h 算 label，每一格會得到同一份 0/1"
                )

        # 階段 4 之**實際套用**：各 symbol 下界一致（上面已 fail-closed 擋掉不一致），
        # 換算成 IC 切分器要的**列數**（無條件進位——不足一列也要整列擋住）。
        purge_ms = distinct.pop() if distinct else 0
        tf = str(request.timeframe or (prepared1.windows[0].timeframe if prepared1.windows else ""))
        seconds = timeframe_seconds.get(tf)
        if seconds is None:
            raise ValueError(
                f"分析用 timeframe {tf!r} 不在注入之 timeframe_seconds 鍵集"
                f"（{sorted(timeframe_seconds)}）——無法把 purge 下界換算成列數"
            )
        purge_rows = -(-int(purge_ms) // (int(seconds) * 1000))  # ceil division
        # 🔴 survivor v2 六鍵（UAT B17 2026-09-02，票 `G3-D14`）：條件 IC run 之 `build_survivor_output` 對此 fail-closed；
        #    B10 五階段路徑繞過 `ic_feed.build_event_ic_inputs` 也繞掉了它的 event_context ⇒ 補由同一模組之
        #    `event_context_from_windows`（經 pipeline 出口）產生，不在 service 自寫 hash。
        event_context = pipeline.event_context_for_analysis(prepared1, records)
        # 🔴 EVTLABEL Task 2.1：把隔離區兩項**分開**換算成特徵列數。
        #    `purge_rows`（＝max(深度, 窗)）保留供對照與既有揭露欄，但不再是 embargo 的唯一來源。
        isolation_rows = pipeline.isolation_terms_rows(
            prepared1.windows,
            lookahead_bars_declared=event_batch.get("lookahead_bars_declared") or {},
            timeframe_seconds=timeframe_seconds,
            feature_timeframe=tf,
        )
        # ── EVTLABEL Task 3.3：明示模式之選樣預檢（`auto` **不呼叫**）──────────────
        # `auto` 不預檢是刻意的：auto 本來就允許退回報酬版，提前算一次只是白花 I/O；
        # 真正的決策仍在 stage3（Task 3.4），那裡看得到切分後的實際列。
        # 🔴 B3 review R1：選樣預檢**已搬進 orchestrator**（切分計畫做完的那一刻），
        #    service 端不再重建一份「測試段」。三家（codex P1-01／P1-02、composer P1-01、
        #    grok P1-01／P1-02／P1-03）實測證明 service 端的重建必然分歧：
        #    ①`create_ic_analyzer(None)` 拿不到本次 `config_override`
        #    ②`purge=label_window_rows` 而 orchestrator 用 `max(H, W)`；embargo 同理
        #    ③`read_hdf(columns=[])` 對本專案真實 h5（h5py CArray，非 pandas table）**恆失敗**
        #      ⇒ 這段預檢從未真正執行過（grok 對 14 個真實路徑抽樣驗證）。
        #    orchestrator 那裡有 `test_plan.row_index`＝實際測試段，沒有第二份算術可漂，
        #    而且一樣在 preprocessing 之前 ⇒「不必跑完才知道不足」的目的照樣達成。
        return {
            # ── EVTLABEL Task 3.3：匯入標籤模式之 staging 產物 ──────────────────
            # `event_binary_labels` 與 `event_label_values` **同鍵**（feature_cutoff_ms）；
            # `event_binary_rows_by_id` 是 records 之獨立快照，供 analyze 後回比。
            # 三者皆恆存在（值可為空 dict／None），不是「有才寫」——下游硬取，缺鍵即 KeyError。
            "event_binary_labels": dict(bin_map),
            "event_binary_rows_by_id": dict(bin_rows_by_id),
            "label_mode_requested": requested_mode,
            "label_mode_hint": label_hint,
            "purge_ms": int(purge_ms),
            "purge_rows": int(purge_rows),
            "label_window_rows": int(isolation_rows.label_window_rows),
            "lookahead_depth_rows": int(isolation_rows.lookahead_depth_rows),
            "event_isolation": isolation_rows,
            "event_timestamps": sorted(ts_map),
            "event_label_values": ts_map,
            # EVTALIGN Task 2.1（D）：(event_id, timestamp, label_value) 三元組之產生者側資料。
            # owners 讓 orchestrator 把每個被消費列綁到恰一個事件；by_id 讓本 service 在 analyze 後
            # 對 orchestrator 回報之 {event_id: 被消費 label} 逐筆回比（_assert_event_triple_bound）。
            "event_label_owners": dict(owner),
            "event_label_by_id": by_id,
            # EVTALIGN Task 3.1：service 端期間對齊揭露（丟掉的事件 ID）；analyze 後併入 report.metadata
            "period_alignment": period_alignment,
            "event_context": event_context,
            "events_excluded_by_symbol": dict(excluded_by_symbol),
            "prepared": prepared1,
            # EVTLABEL Task 1.1：label 規則揭露需要原始 records（0/1 標籤存在與否）與同一份 timeframe_seconds。
            "records": tuple(records),
            "timeframe_seconds": timeframe_seconds,
            "purge": purge,
            "analysis_alignment_receipt_hash": prepared1.analysis_alignment_receipt_hash,
            "prepared_token": prepared1.prepared_token,
            # 🔴 `G3-D2` D1.6：批內「事件於決策當下是否已知」之相異值集合。
            #    值由對齊層機械導出（`decision_at >= t₀ close`），本層**只投影不重算**。
            #    D2-2 單一表示法下恆為 `[False]`；空清單代表對齊層沒寫這欄（loud，非正常值）。
            "event_known_at_decision_values": list(prepared1.event_known_at_decision_values),
            # 🔴 `G3-D2` D5.3（R1 三家命中）：本批之**抽樣設計**揭露。
            #    `D-001` D5.3 邊界④：「隨機批單獨分析允許（其 IC＝無條件 IC 估計，**揭露**）」
            #    ——沒有這一欄，使用者看不出手上這份 IC 是條件估計還是無條件估計，
            #    而兩者的解讀完全相反。值由 `control_kind` 機械導出，不由使用者宣告。
            "event_sample_design": ICAnalysisService._sample_design_of(records),
        }

    @staticmethod
    def _sample_design_of(records) -> str:
        """批之抽樣設計（`G3-D2` D5.3）：全批 `platform_random_bars` ⇒ 無條件隨機。

        🔴 **全批一致才算**——混批不存在（`validate_event_import` 已 fail-closed 拒
        `platform_random_bars` 與其他 kind 同批），故此處不需多數決，也不得取第一列。

        🔴 **不以「不是全隨機就當 case_control」收尾**（R2 `CODEX-R2-P2-01`）：
        那條 fallback 依賴的是**別處**的不變式（validator 的混批拒收）。哪天那條被放寬，
        本函式會把混批**靜默**標成條件樣本，而抽樣設計標錯的症狀是「IC 數字看起來很正常、
        解讀完全相反」。⇒ 混到 `platform_random_bars` 的批一律 raise，讓它在這裡就爆，
        不要等到有人拿著錯的標籤去解讀。
        """
        kinds = {str(r.get("control_kind")) for r in records if r.get("control_kind") is not None}
        if kinds == {"platform_random_bars"}:
            return RANDOM_SAMPLE_DESIGN
        if "platform_random_bars" in kinds:
            raise ValueError(
                f"批內 control_kind={sorted(kinds)} 同時含 platform_random_bars 與其他值；"
                "抽樣設計無單一答案（匯入層本應已拒收混批——若這裡爆了，代表那道閘被放寬了）"
            )
        return "case_control"

    @staticmethod
    def compare_random_control(trigger_detail: Any, random_detail: Any) -> CompareVerdict:
        """`G3-D2` D5.3：觸發批 vs 隨機對照批之 prevalence 並排——**四段規則身分閘**。

        🔴 **本方法是這件事的唯一 owner**（`D-006` D5.3 R4 CODEX-R4-P2-01）：
        輸入為兩份 `EventImportDetailResponse` DTO，**不 import `case_import_service`**
        （解耦 Rule 4：服務不互 import）。呼叫端負責把兩份 detail 撈好交進來。

        ## 為什麼要有這道閘

        「觸發樣本的正例率 25%、隨機樣本 10%」這句話只有在**兩邊用同一把尺**時才有意義。
        兩批若各自用不同的門檻或不同的答案窗長度，數字仍然可以並排、仍然可以相減，
        但那個差值不代表任何東西——而它看起來跟真的一模一樣。這是最貴的一種錯：
        **不會報錯、不會是 NaN、只會給出一個有說服力的錯誤結論**。

        ## 四段（`D-001` D5.3 ①–④，順序即優先序）

        ① 觸發批之 `receipt.batch.label_rule` 缺 ⇒ `random_control_rule_identity_unverifiable`。
           既有批（人工標註／`/search` 匯出）**通常都缺**，這是通則不是例外——
           `label_rule` 的唯一 wire 是匯入 envelope，舊批當時沒有這個欄位。
        ② 任一葉不等／`direction` 不同／觸發批之 `label_return_mode != close_to_close`
           ⇒ `random_control_rule_mismatch`。身分 tuple＝
           `(threshold, horizon_bars, direction, label_return_mode)`。
        ③ 相等時**以同一 `label_rule` 重評觸發批每列 label**，一致率 `!= 1.0` ⇒ mismatch。
           這一段擋的是「宣告的規則」與「實際落檔的答案」不符——宣告是可以亂寫的。
        ④ 缺任一 prevalence ⇒ `random_control_prevalence_missing`。

        🔴 `label_definition.canonical_digest` **不參與**比較（`D-001` D5.3 邊界①）：
        隨機批之 digest＝S-9(label_rule)、產生器批之 digest 含 `label_id`／mode／direction，
        兩者本就不相等，拿來比會恆假。
        """
        from momentum.factories import create_event_sample_pipeline

        pipeline = create_event_sample_pipeline()

        def _rb(detail: Any) -> Any:
            return getattr(detail, "receipt_batch", None)

        trig_rb, rand_rb = _rb(trigger_detail), _rb(random_detail)
        trig_rule = getattr(trig_rb, "label_rule", None) if trig_rb is not None else None
        rand_spec = getattr(rand_rb, "random_control_spec", None) if rand_rb is not None else None

        # ── ① 觸發批之規則身分缺席 ────────────────────────────────────────
        if trig_rule is None:
            return CompareVerdict(
                status="unavailable",
                reason="random_control_rule_identity_unverifiable",
                # 🔴 UAT B23（2026-09-07）：原文只說「以 label_rule 帶入規則」，使用者回
                #    「匯入裡面都有 label_rule 啊」——他看到的是樣本檔的 `_label_rule`，
                #    那是**底線開頭的散文說明**（同 `_readme`，被忽略）。名字像、作用完全不同。
                #    而且當時**沒有任何路由傳這個參數**，照著做也做不到。兩者皆已修。
                #    ⇒ 訊息改成講清楚「要放哪裡、長什麼樣、跟你看到的那個差在哪」。
                message=("觸發批沒有落檔 receipt.batch.label_rule（既有批通常如此）——"
                         "無從確認兩批用的是同一條標籤規則，故不並排 prevalence。"
                         "補法＝重新匯入該批，在**事件檔最外層**（與 records 同層）加一個結構化欄位："
                         'label_rule = {"threshold": 0.0, "horizon_bars": 3}'
                         "（threshold 是門檻、horizon_bars 是答案窗長度，依你這批實際的規則填）。"
                         "🔴 注意與 `_label_rule` 不同：底線開頭那個是給人看的文字說明，"
                         "系統一律忽略；要有作用的是**沒有底線**的 label_rule。"
                         "範例見 uat_samples/events_ok.json"),
                sample_design=RANDOM_SAMPLE_DESIGN,
            )
        if rand_spec is None or rand_spec.get("label_rule") is None:
            return CompareVerdict(
                status="unavailable",
                reason="random_control_rule_identity_unverifiable",
                message="隨機批沒有 receipt.batch.random_control_spec.label_rule（抽樣契約缺席）",
                sample_design=RANDOM_SAMPLE_DESIGN,
            )

        rand_rule = dict(rand_spec["label_rule"])
        trig_leaves = {"threshold": float(trig_rule.threshold), "horizon_bars": int(trig_rule.horizon_bars)}
        rand_leaves = {"threshold": float(rand_rule["threshold"]), "horizon_bars": int(rand_rule["horizon_bars"])}
        trig_dir = getattr(getattr(trigger_detail, "batch_facts", None), "direction", None)
        rand_dir = str(rand_spec.get("strata", {}).get("direction")) if rand_spec.get("strata") else None
        trig_mode = getattr(getattr(trigger_detail, "declaration_seeds", None), "label_return_mode", None)
        n_requested = rand_spec.get("n_requested")
        n_drawn = rand_spec.get("n_drawn")

        # ── ② 身分 tuple 逐項比對 ────────────────────────────────────────
        diffs: List[str] = []
        if trig_leaves != rand_leaves:
            diffs.append(f"label_rule 觸發批={trig_leaves} 隨機批={rand_leaves}")
        if trig_dir is None or rand_dir is None or str(trig_dir) != str(rand_dir):
            diffs.append(f"direction 觸發批={trig_dir!r} 隨機批={rand_dir!r}")
        if str(trig_mode) != _IDENTITY_LABEL_RETURN_MODE:
            diffs.append(
                f"觸發批 label_return_mode={trig_mode!r}，隨機批固定 {_IDENTITY_LABEL_RETURN_MODE!r}")
        if diffs:
            return CompareVerdict(
                status="unavailable", reason="random_control_rule_mismatch",
                message="兩批之規則身分不同，prevalence 不可並排：" + "；".join(diffs),
                sample_design=RANDOM_SAMPLE_DESIGN,
                n_requested=n_requested, n_drawn=n_drawn,
            )

        # ── ③ 以同一規則重評觸發批 label（宣告 vs 落檔） ──────────────────
        trig_recs = list(getattr(trigger_detail, "records", None) or ())
        threshold = trig_leaves["threshold"]
        horizon = trig_leaves["horizon_bars"]
        # 🔴 **從真實 bar 表重算**（R1 `COMPOSER-R1-P1-02`）：舊版拿落檔之 `label_value`
        #    當 signed return，只證明「`label` 與 `label_value` 內部自洽」，**不證明**
        #    `label_value` 本身是這條規則算出來的。反例：`label_value=0.03`／`label=1`
        #    （threshold=0.02）而真實 bar 報酬 `-0.01` ⇒ 閘③放行、prevalence 不可比，
        #    且契約對 `label_value` 只驗「是數字」，不會有任何東西報錯。
        symbols = sorted({str(r["symbol"]) for r in trig_recs if r.get("symbol")})
        timeframes = sorted({str(r["timeframe"]) for r in trig_recs if r.get("timeframe")})
        if not symbols or not timeframes:
            return CompareVerdict(
                status="unavailable", reason="random_control_rule_identity_unverifiable",
                message="觸發批之列缺 symbol／timeframe，無法回 bar 表重評",
                sample_design=RANDOM_SAMPLE_DESIGN, n_requested=n_requested, n_drawn=n_drawn,
            )
        try:
            bars = pipeline.bars_from_kline_cache(symbols, timeframes)
        except (KeyError, FileNotFoundError, ValueError) as exc:
            return CompareVerdict(
                status="unavailable", reason="random_control_rule_identity_unverifiable",
                message=f"讀不到觸發批之 kline（{exc}），無法以 bar 表重評規則",
                sample_design=RANDOM_SAMPLE_DESIGN, n_requested=n_requested, n_drawn=n_drawn,
            )
        recomputed = pipeline.recompute_close_to_close(
            trig_recs, bars, threshold=threshold, horizon=horizon, direction=str(trig_dir))
        n_checked = 0
        n_agree = 0
        for r in trig_recs:
            eid = str(r.get("event_id"))
            lab = r.get("label")
            got = recomputed.get(eid)
            if lab is None or got is None:
                return CompareVerdict(
                    status="unavailable",
                    reason="random_control_rule_identity_unverifiable",
                    message=(f"觸發批之事件 {eid!r} 缺 label 或無法在 bar 表上定位"
                             "（t0 不在網格上／答案窗不完整）——不以算不出來當成一致"),
                    sample_design=RANDOM_SAMPLE_DESIGN,
                    n_requested=n_requested, n_drawn=n_drawn,
                )
            n_checked += 1
            # 兩項都要對：①落檔 label ②落檔 label_value（若有）皆須等於 bar 表重算值。
            lv = r.get("label_value")
            lv_ok = lv is None or float(lv) == got["signed_return"]
            if got["label"] == int(lab) and lv_ok:
                n_agree += 1
        if n_checked == 0:
            return CompareVerdict(
                status="unavailable", reason="random_control_prevalence_missing",
                message="觸發批沒有任何事件，無 prevalence 可比",
                sample_design=RANDOM_SAMPLE_DESIGN, n_requested=n_requested, n_drawn=n_drawn,
            )
        if n_agree != n_checked:
            return CompareVerdict(
                status="unavailable", reason="random_control_rule_mismatch",
                message=(f"以宣告之 label_rule 重評觸發批，一致率 {n_agree}/{n_checked} != 1.0"
                         "——落檔的 label 不是這條規則產出的"),
                sample_design=RANDOM_SAMPLE_DESIGN, n_requested=n_requested, n_drawn=n_drawn,
            )

        # ── ④ prevalence ────────────────────────────────────────────────
        rand_recs = list(getattr(random_detail, "records", None) or ())
        trig_labels = [int(r["label"]) for r in trig_recs if r.get("label") is not None]
        rand_labels = [int(r["label"]) for r in rand_recs if r.get("label") is not None]
        if not trig_labels or not rand_labels:
            return CompareVerdict(
                status="unavailable", reason="random_control_prevalence_missing",
                message=(f"prevalence 缺（觸發批 {len(trig_labels)} 筆、隨機批 {len(rand_labels)} 筆"
                         "有 label）——空的一側沒有基率"),
                sample_design=RANDOM_SAMPLE_DESIGN, n_requested=n_requested, n_drawn=n_drawn,
            )
        p_trig = sum(trig_labels) / len(trig_labels)
        p_rand = sum(rand_labels) / len(rand_labels)
        return CompareVerdict(
            status="ok",
            trigger_prevalence=float(p_trig),
            random_prevalence=float(p_rand),
            # 🔴 基準為 0 ⇒ lift 無定義，回 None 而**不**回 inf／0（兩者都會被讀成一個數字）。
            lift=float(p_trig / p_rand) if p_rand > 0 else None,
            n_trigger=len(trig_labels), n_random=len(rand_labels),
            sample_design=RANDOM_SAMPLE_DESIGN,
            n_requested=n_requested, n_drawn=n_drawn,
        )

    @staticmethod
    def _event_k_disclosure(
        request: ICAnalyzeRequest, event_batch: Dict[str, Any],
    ) -> Dict[str, Any]:
        """`G3-D2` D4.2／D4.3 之揭露欄：k 雙值 ＋ 兩個條件上界。

        🔴 **雙值分開講**（D4.3）：`decision_offset_bars_record_values` 是**這批當初記錄了什麼**
        （事實，可能是空清單或多值），`decision_offset_bars_analysis` 是**這次分析用了什麼**
        （參數）。合成一個數字就會出現「批次寫 1、分析用 0，畫面只寫一個 0」這種誤導。
        🔴 **缺任一欄 ⇒ `unavailable`**（reason 已登記契約）：揭露缺席時，使用者無從判斷
        自己看到的 IC 是用哪個 k 算的——那比沒有分析更糟。
        🔴 上界之公式與誠實邊界住 producer（`feasible_bounds`）；本層**只投影不重算**。
        """
        from momentum.factories import create_event_sample_pipeline

        spec = dict(event_batch.get("event_label_spec") or {})
        records = list(event_batch.get("records") or ())
        record_values = event_batch.get("decision_offset_bars_record_values")
        analysis_k = event_batch.get("decision_offset_bars_analysis")
        if record_values is None or analysis_k is None:
            return {
                "decision_offset_bars_capability": "unavailable",
                "decision_offset_bars_reason": (
                    ICAnalysisService.SCAN_REASON_MISSING_K_DISCLOSURE
                ),
            }
        pipeline = create_event_sample_pipeline()
        # 🔴 **`CODEX-R1-P2-04`（R1 閉合）：bounds 之母體須與實際 IC 母體同源**。
        #    首版對**全批** records 算上界，但 longitudinal IC 只餵 `symbol == request.symbol`
        #    的事件（他 symbol 於 `_run_event_label_stages` 具名排除）⇒ 另一個 symbol 的
        #    尾端事件會把 `min_e` 壓低，畫面顯示的上界比使用者這次真正跑的母體更嚴。
        #    codex 實跑：ETH-only `k_max=119`，混入一筆 BTC 尾端事件後變 `no_feasible_k`。
        #    ⇒ 依 run symbol 過濾；並把**過濾範圍**一併揭露（不讓「上界是對誰算的」變成暗知識）。
        run_symbol = str(getattr(request, "symbol", "") or "") or None
        scoped = [r for r in records if run_symbol is None or str(r.get("symbol")) == run_symbol]
        excluded = len(records) - len(scoped)
        if not scoped:
            return {
                "decision_offset_bars_capability": "unavailable",
                "decision_offset_bars_reason": (
                    ICAnalysisService.SCAN_REASON_MISSING_K_DISCLOSURE
                ),
            }
        timeframes = sorted({str(r.get("timeframe")) for r in scoped if r.get("timeframe")})
        bars_by_tf = pipeline.bars_from_kline_cache(
            sorted({str(r.get("symbol")) for r in scoped if r.get("symbol")}), timeframes,
        )
        bounds = pipeline.feasible_bounds(
            scoped, bars_by_tf, event_label_spec=spec, timeframes=timeframes,
        )
        return {
            "decision_offset_bars_capability": "available",
            "decision_offset_bars_reason": None,
            "decision_offset_bars_record_values": list(record_values),
            "decision_offset_bars_analysis": int(analysis_k),
            # 🔴 建議上限亦由**後端**交出：前端硬編會在契約改值時安靜地繼續用舊值。
            "decision_offset_bars_scan_max": int(
                pipeline.analysis_params()["decision_offset_bars_scan_max"]
            ),
            # 🔴 上界是**對誰**算的：run symbol 之子集，以及被排除的筆數。
            #    `None` ⇒ 未指定 run symbol（全批）；`0` ⇒ 有指定但沒東西被排除。
            "bounds_scope_symbol": run_symbol,
            "bounds_scope_excluded_events": int(excluded),
            **bounds,
        }

    # ── `G3-D2` **D4.3**：k／h 掃描網格（裁定③「填 m 就掃 0～m」）─────────────
    #
    # 🔴 **為什麼在 service 而不是 route**：每一格都要跑完整的五階段＋條件 IC，
    #    是十秒到分鐘級的工作 ⇒ 必須在既有的**背景 task** 內、以 `asyncio.to_thread`
    #    逐格執行。放在 route 會把 event loop 綁住整個網格的時間。

    #: 掃描格之 capability 字面（皆登記於契約 `capability_unavailable_reasons`）。
    SCAN_REASON_TOO_LARGE = "scan_grid_too_large"
    SCAN_REASON_CELL_TIMEOUT = "scan_cell_timeout"
    SCAN_REASON_MISSING_K_DISCLOSURE = "missing_decision_offset_disclosure"

    @staticmethod
    def _scan_axes(spec: Dict[str, Any], scan: Optional[Dict[str, Any]]) -> tuple:
        """`(K, H)` 兩軸。未給該軸之上界 ⇒ 該軸只有 `spec` 的單值（**不是**整條掃）。"""
        scan = scan or {}
        mk = scan.get("decision_offset_bars_max")
        mh = scan.get("horizon_bars_max")
        k_axis = list(range(0, int(mk) + 1)) if mk is not None else [int(spec["decision_offset_bars"])]
        h_axis = list(range(1, int(mh) + 1)) if mh is not None else [int(spec["horizon_bars"])]
        return k_axis, h_axis

    @staticmethod
    def _scan_cell_summary(report: Any) -> Optional[Dict[str, Any]]:
        """單格之 IC 摘要**投影**（只取存在的鍵，不發明指標）。

        🔴 **誠實邊界**：本 dict 是給矩陣格子顯示用的摘要，**不是**權威分析結果；
        權威值仍在該格自己的分析報告裡。不在此計算任何新統計量。

        🔴 **`GROK-R1-P2-02`（R1 閉合）**：首版於 report **根**取 `n_features`／`n_samples`，
        但真實 `ICFilterOrchestrator.analyze` 把計數放在 `metadata`（見
        `ic_filter_orchestrator.py` 之 `metadata.n_samples`／`total_features_*`）
        ⇒ 那兩個根鍵**恆不存在**，格子永遠只有 status。而測試之 fake analyzer 在根上
        捏造 `n_features` ⇒ 掩蓋這個洞。**修法＝逐層取**：根優先、退到 `metadata`；
        兩處皆無就是沒有（不填假值）。
        """
        if not isinstance(report, dict):
            return None
        meta = report.get("metadata")
        meta = meta if isinstance(meta, dict) else {}
        out: Dict[str, Any] = {}
        for key in ("analysis_status", "oos_guarantees"):
            if key in report:
                out[key] = report[key]
        # 計數類：真實形狀住 `metadata`；根層是舊 fake 的形狀，兩者都收但**不造值**。
        for key in ("n_samples", "n_features", "total_features_evaluated"):
            if key in report:
                out[key] = report[key]
            elif key in meta:
                out[key] = meta[key]
        # 🔴 B3 review R1 `CODEX-R1-P1-03`：掃描格**恆為報酬版**（0/1 與 k、h 無關，
        #    每格會得到同一份標籤 ⇒ 整張網格是假的變化），但這個決定原本只寫在註解裡，
        #    格子、payload、前端都看不到。使用者選了 `auto` 跑掃描時，會以為結果是用他的
        #    0/1 算的。⇒ 每一格都揭露 effective mode，不靠使用者自己推。
        info = _find_event_filter_info(meta)
        if isinstance(info, dict) and info.get("label_source"):
            out["label_source"] = info["label_source"]
        out["label_mode_effective"] = "return_rule"
        return out or None

    async def _run_scan_grid(
        self,
        task_id: str,
        analyzer_factory: Any,
        request: ICAnalyzeRequest,
        event_batch: Dict[str, Any],
        *,
        features_path: Optional[str],
        meta_path: Optional[str],
        feature_manifest_path: Optional[str],
        labels_path: Optional[str],
        kline_reader: Any,
        config_override: Optional[Dict[str, Any]],
        progress_callback: Any,
        original_embargo: int = 0,
    ) -> Dict[str, Any]:
        """逐格跑五階段＋條件 IC，回 `{"scan_results": [...], "scan_total": n, ...}`。

        `original_embargo`（B2 review R1 `CODEX-R1-P2-01`）：**抬高前**的 config embargo。
        外層在進入本函式前已把 `config_override["embargo"]` 抬到 look-ahead 深度，
        每格若直接讀它當「原始設定」，隔離區來源會全部誤標成 `config_embargo`。

        🔴 **每格獨立 `prepared_token`／`analysis_alignment_receipt_hash`**：格與格之間
        不得重用 prepare 之產物——重用會讓「用 k=0 對齊、用 k=2 算值」這種錯配全綠。
        驗收以「各格 hash 互異」釘住。
        🔴 **逾時之格 `unavailable` 並保留 partial**：整個網格不因一格慢而全滅。
        🔴 **超出可行域之格 `unavailable` 不影響他格**：那是資料事實，不是請求錯誤。

        🔴 **`CODEX-R1-P1-01`（R1 閉合）：每格用自己的 analyzer**。
        首版把**同一個** `analyzer` 逐格丟進 `to_thread`；而 `asyncio.wait_for` 的取消
        **只取消 await，不會停掉已在跑的 thread**（Python 無法從外部殺 thread）。
        `ICFilterOrchestrator` 持有 `_ic_cache`／`_report`／`_filtered_features_df`／
        `_current_config` 等**可變欄位** ⇒ 逾時之格仍在背景改那些欄位，而下一格與
        **網格之後的主分析**用的是同一個物件 ⇒ 跨 k/h 污染，且值合法、不會紅。
        **修法＝所有權隔離**：本方法收 `analyzer_factory`（而非 analyzer 實例），
        每格自己造一個、用完即棄。
        🔴 **誠實邊界**：被遺棄的 worker **仍會跑完**（只是它改的是自己那份、隨後被丟掉）；
        隔離消除的是**污染**，不是「逾時就真的停下來」。CPU 仍被它佔用到自然結束。
        """
        from momentum.factories import create_event_sample_pipeline

        params = create_event_sample_pipeline().analysis_params()
        max_runs = int(params["scan_grid_max_runs"])
        per_cell_timeout = float(params["per_cell_timeout_s"])
        total_timeout = float(params["scan_timeout_s"])

        base_spec = dict(event_batch.get("event_label_spec") or {})
        k_axis, h_axis = self._scan_axes(base_spec, event_batch.get("event_label_scan"))
        total = len(k_axis) * len(h_axis)
        if total > max_runs:
            return {
                "scan_total": total,
                "scan_done": 0,
                "scan_results": [],
                "capability": "unavailable",
                "reason": self.SCAN_REASON_TOO_LARGE,
                "message": (
                    f"掃描網格 {len(k_axis)}×{len(h_axis)}＝{total} 格，超過上限 {max_runs}"
                    "（契約 analysis_params.scan_grid_max_runs）——請縮小 k／h 之上界"
                ),
            }

        deadline = asyncio.get_running_loop().time() + total_timeout
        results: List[Dict[str, Any]] = []
        done = 0
        for k in k_axis:
            for h in h_axis:
                # 🔴 逐格剝離成**恰四鍵** spec（normalizer 對多一鍵 fail-closed）。
                cell_spec = {
                    "horizon_bars": int(h),
                    "entry_price_semantic": base_spec["entry_price_semantic"],
                    "label_return_mode": base_spec["label_return_mode"],
                    "decision_offset_bars": int(k),
                }
                cell_batch = {**event_batch, "event_label_spec": cell_spec}
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    results.append({
                        "k": int(k), "h": int(h), "capability": "unavailable",
                        "reason": self.SCAN_REASON_CELL_TIMEOUT, "n_events": 0,
                        "analysis_alignment_receipt_hash": None, "ic_summary": None,
                    })
                    continue
                try:
                    cell = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._run_scan_cell, analyzer_factory, request, cell_batch,
                            features_path=features_path, meta_path=meta_path,
                            feature_manifest_path=feature_manifest_path,
                            labels_path=labels_path, kline_reader=kline_reader,
                            config_override=config_override,
                            original_embargo=original_embargo,
                        ),
                        timeout=min(per_cell_timeout, remaining),
                    )
                except asyncio.TimeoutError:
                    cell = {
                        "capability": "unavailable", "reason": self.SCAN_REASON_CELL_TIMEOUT,
                        "n_events": 0, "analysis_alignment_receipt_hash": None, "ic_summary": None,
                    }
                except Exception as exc:  # noqa: BLE001  逐格 loud，不讓一格炸掉整個網格
                    logger.warning("scan cell (k=%s, h=%s) 失敗：%s", k, h, exc)
                    cell = {
                        "capability": "unavailable", "reason": str(exc)[:200],
                        "n_events": 0, "analysis_alignment_receipt_hash": None, "ic_summary": None,
                    }
                results.append({"k": int(k), "h": int(h), **cell})
                done += 1
                progress_callback({
                    "stage": "event_label_scan",
                    "stage_name": "event_label_scan",
                    "progress": done / max(total, 1),
                    "message": f"掃描網格 {done}/{total}（k={k}, h={h}）",
                    "scan_done": done,
                    "scan_total": total,
                })
        # 🔴 `SCANCUBE` Task 2.3：**三步驟，順序不可調換**。
        #    ① 落檔（此時還需要 report）② 立刻剝除 ③ 只把摘要放進回傳
        cube = self._build_scan_cube(task_id, request, results)
        for cell in results:
            cell.pop("report", None)  # ← 少這行，GB 級 report 會進 HTTP status

        return {
            "scan_total": total,
            "scan_done": done,
            "scan_results": results,
            "capability": "available",
            "reason": None,
            # 🔴 只有摘要：**不含** rows／sections（那是 GB 級，走 /scan-cube 端點）
            "cube": cube,
        }

    def _build_scan_cube(
        self, task_id: str, request: ICAnalyzeRequest, results: list[dict],
    ) -> Dict[str, Any]:
        """把每格的 report 落成立方體；回傳給前端的**摘要**（不含資料本體）。

        🔴 落檔失敗**不得**讓掃描結果消失：掃描本身已經跑完了，
        把它一起丟掉是拿使用者的計算時間去賠一個寫檔錯誤。
        """
        # 🔴 走 factory（Rule 3）——直接 `from momentum.Analysis.scan_cube import …`
        #    會被 `check_decoupling_imports.py` 判為**新增** R3 違反。
        #    本檔既有那幾條 `momentum.Analysis.ic_reporter` 直 import 在 baseline 裡是技術債，
        #    不是可以照抄的先例。
        from momentum.factories import create_event_sample_pipeline, create_scan_cube_store

        scan_cube = create_scan_cube_store()
        try:
            params = create_event_sample_pipeline().analysis_params()
            manifest = scan_cube.build_cube(
                task_id,
                getattr(request, "symbol", None),
                getattr(request, "timeframe", None),
                results,
                max_rows=int(params["scan_cube_max_rows"]),
                max_rows_per_cell=int(params["scan_cube_max_rows_per_cell"]),
                chart_max_bytes=int(params["scan_cube_chart_max_bytes"]),
                keep_tasks=int(params["scan_cube_keep_tasks"]),
            )
        except Exception as exc:  # noqa: BLE001  落檔失敗 loud 但不吃掉掃描結果
            logger.error("scan cube 落檔失敗 task=%s: %s", task_id, exc, exc_info=True)
            return {"status": "failed", "reason": str(exc)[:200]}

        return {
            "status": "ok",
            "created_at": manifest["created_at"],
            "metrics": manifest["metrics"],
            "chart_sections": manifest["chart_sections"],
            "excluded_sections": manifest["excluded_sections"],
            "tier_a": manifest["tier_a"],
            "tier_b": manifest["tier_b"],
        }

    def _run_scan_cell(
        self,
        analyzer_factory: Any,
        request: ICAnalyzeRequest,
        cell_batch: Dict[str, Any],
        *,
        features_path: Optional[str],
        meta_path: Optional[str],
        feature_manifest_path: Optional[str],
        labels_path: Optional[str],
        kline_reader: Any,
        config_override: Optional[Dict[str, Any]],
        original_embargo: Optional[int] = None,
    ) -> Dict[str, Any]:
        """單格：五階段 ＋ 條件 IC（**同步**；由 `_run_scan_grid` 以 `to_thread` 呼叫）。

        `original_embargo`（B2 review R1 `CODEX-R1-P2-01`）：抬高前之 config embargo；
        `None` ⇒ 回退讀 `config_override`（單格直呼之相容路徑）。

        🔴 `CODEX-R1-P1-01`：analyzer **由本格自己造**（`analyzer_factory(cell_override)`），
        用完即棄。逾時之格即使仍在背景跑，改的也只是它自己那一份。
        """
        staged = self._run_event_label_stages(
            request, cell_batch,
            features_path=features_path, meta_path=meta_path,
            feature_manifest_path=feature_manifest_path,
        )
        cell_override = dict(config_override or {})
        # 🔴 B2 review R1 `CODEX-R1-P2-01`：`config_override["embargo"]` 在**進掃描格之前**
        #    已被外層抬高（主路徑 :1651-1657）⇒ 在此讀它當「原始設定」會把每一格的來源
        #    誤標成 `config_embargo`（實跑：incoming=144 ⇒ 誤標）。原始值由外層以**顯式參數**
        #    `original_embargo` 傳入（不塞 config_override）；`None` 才回退讀 override（單格直呼之相容路徑）。
        staged["embargo_before_event"] = int(
            original_embargo if original_embargo is not None else (cell_override.get("embargo") or 0)
        )
        # 🔴 EVTLABEL Task 2.1：embargo 只承載**批次宣告之 look-ahead 深度**（挑樣本時看了多遠），
        #    答案窗改由 `event_isolation.label_window_rows` 抬 purge。舊版用 `purge_rows`
        #    （＝max(深度, 窗)）抬 embargo ⇒ 答案窗的身分在下游消失。
        cell_override["embargo"] = max(
            int(cell_override.get("embargo") or 0), int(staged["lookahead_depth_rows"]),
        )
        analyzer = analyzer_factory(cell_override)
        # 🔴 `SCANCUBE` Task 1.1：掃描格是**研究掃描**，不是決策產物 ⇒ 不寫 survivor artifact。
        #    實跑證明（`handoffs/20260906-probe-scan-overwrite.py`，rc=0）：
        #    `_resolve_filtered_path` 只用 symbol+timeframe、**不含 k/h**
        #    ⇒ 4 組不同 (k,h) 落到同一路徑，N 格覆蓋同一檔、最後一格獲勝；
        #    且逾時之格的 thread 仍會跑完（`_run_scan_grid` docstring 自陳），
        #    它跑完時也會寫 ⇒ 並行寫競態。每格自己造 analyzer 的隔離**擋不到**這個，
        #    因為落檔路徑是行程全域的。
        #    🔴 停寫而非「路徑帶 k/h」：該 h5 是 survivor artifact，有 export 消費者
        #    （`assert_filtered_export_fresh` 比對 provenance）；寫 110 份競爭性 artifact
        #    比覆蓋更糟——下游無從知道該讀哪一份。每格的**數據**改由立方體保存。
        analyzer._suppress_persist = True
        report = analyzer.analyze(
            features_path=features_path,
            labels_path=labels_path or "",
            meta_path=meta_path,
            config_override=cell_override,
            progress_callback=None,
            kline_reader=kline_reader,
            event_timestamps=staged["event_timestamps"],
            event_label_values=staged["event_label_values"],
            event_label_owners=staged["event_label_owners"],
            event_context=staged["event_context"],
            # EVTLABEL Task 2.2：purge 由答案窗抬（顯式 kwarg；禁走 config_override）
            event_isolation=staged.get("event_isolation"),
            # 🔴 EVTLABEL Task 3.3：掃描格**恆為報酬版**，不送 0/1。
            #    掃描的整個意義是「k×h 換一組就換一組報酬」；匯入的 0/1 與 k、h 無關，
            #    每一格會得到同一份標籤、同一組統計 ⇒ 整張網格是假的變化。
            #    明示 `imported_binary` ＋ 掃描已在請求層與 staging 各擋一次；
            #    這裡處理的是 `auto` ＋ 掃描——**不讓 auto 在掃描格裡解析成 binary**。
            event_binary_labels=None,
            label_mode_requested="return_rule",
            label_mode_hint=staged.get("label_mode_hint"),
        )
        _assert_event_triple_bound(staged, report)
        _inject_period_alignment(staged, report)
        _inject_isolation_source(staged, report)
        return {
            "capability": "available",
            "reason": None,
            "n_events": len(staged["event_timestamps"]),
            "analysis_alignment_receipt_hash": staged["analysis_alignment_receipt_hash"],
            "ic_summary": self._scan_cell_summary(report),
            # 🔴 `SCANCUBE` Task 2.3：**只在行程內傳遞**，供 `build_cube` 落檔用。
            #    `_run_scan_grid` 在 `build_cube` 之後**立刻 pop 掉**——
            #    `_run_analysis` 會把整個 `scan` 放進 `info["event_label_scan"]`，
            #    而 `get_task_status` 逐鍵放進 HTTP payload
            #    ⇒ 不剝除就會把 GB 級 report 推進 status API
            #    （`CODEX-R1-P1-02`／`GROK-R1-P1-01` 兩家獨立命中）。
            "report": report,
        }

    async def start_analysis(
        self,
        request: ICAnalyzeRequest,
        *,
        event_batch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Start IC analysis task.

        🔴 `event_batch`（GAP-3 Task 7.0b）由 **route 層**以 `request.event_import_id` 查出
        並傳入——**不是** service 自己查。理由：Rule 4 禁 service 互相 import，
        而事件批住在 `api/services/case_import_service.py`。route 不在 R4 掃描範圍。
        形狀＝`{"records": [...], "lookahead_bars_declared": {...}, "event_label_spec": {...}}`。
        """
        task_id = str(uuid.uuid4())
        config_override = self._build_config_override(request)
        analyzer = create_ic_analyzer(config_override)

        task_info = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.0,
            "current_stage": None,
            "current_step": None,
            "error": None,
            "result": None,
            "deep_analysis_result": None,
            "analyzer": analyzer,
            "applied_tier": (request.feature_tiers.active_preset if request.feature_tiers else "intermediate"),
            "created_at": datetime.now().isoformat(),
            # store source info for apply_transforms
            "req_features_path": request.features_path,
            "req_symbol": request.symbol,
            "req_timeframe": request.timeframe,
            "req_config_hash": (request.config_hash or "").strip() or None,
            # GAP-3 UX Task 6.3：這個 run 有幾個特徵（只讀 registry；解析不出來就是 None，不填假值）。
            "feature_count": _resolve_feature_count(request),
        }

        with self._lock:
            self._tasks[task_id] = task_info
            self._last_task_id = task_id

        logger.info("IC analysis task started: %s", task_id)
        asyncio.create_task(
            self._run_analysis(task_id, analyzer, request, config_override, event_batch=event_batch)
        )

        return {"task_id": task_id, "status": "running"}

    async def _run_analysis(
        self,
        task_id: str,
        analyzer: Any,
        request: ICAnalyzeRequest,
        config_override: Optional[Dict[str, Any]],
        *,
        event_batch: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Run IC analysis in background."""

        loop = asyncio.get_running_loop()

        def progress_callback(payload: Dict[str, Any]) -> None:
            if loop.is_closed():
                # 伺服器已關閉（Ctrl+C）：不再推送、不再洗版，讓分析執行緒在此回報點協作式中止
                raise AnalysisCancelled("server event loop closed; aborting analysis at progress checkpoint")
            with self._lock:
                if (self._tasks.get(task_id) or {}).get("cancel_requested"):
                    # 使用者按了取消：協作式，在下一個回報點停（預處理每 100 欄一點；其餘為階段邊界）
                    raise AnalysisCancelled("cancelled by user")
            stage_name = payload.get("stage_name") or payload.get("stage")
            progress = float(payload.get("progress", 0.0))
            message = payload.get("message")
            current_step = payload.get("module_name") or payload.get("current_step") or stage_name

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["current_stage"] = stage_name
                task_info["current_step"] = current_step
                task_info["progress"] = progress
                task_info["status"] = "running"
                # 🔴 `G3-D2` D4.3：掃描網格之格數進度。**沿用既有 progress 事件**，
                #    不另開一條通道（前端已有一套訂閱邏輯，兩套必然漂移）。
                if "scan_total" in payload:
                    task_info["scan_done"] = payload.get("scan_done")
                    task_info["scan_total"] = payload.get("scan_total")
                # EVTALIGN Task 4.1：階段內進度（done/total＋ETA）沿用同一通道；記憶體 WARN 進 warnings（去重）
                _apply_stage_progress(task_info, payload, message)

            notify_payload = {
                "task_id": task_id,
                "stage": stage_name,
                "current_step": current_step,
                "progress": progress,
                "message": message,
                "status": "running",
            }
            if "scan_total" in payload:
                notify_payload["scan_done"] = payload.get("scan_done")
                notify_payload["scan_total"] = payload.get("scan_total")
            # EVTALIGN Task 4.1（UAT B29 實機抓到）：WS 是前端正常路徑的唯一來源，sub_*／warning 不轉發 ⇒ 畫面永遠看不到
            notify_payload.update(_ws_stage_progress_fields(payload))
            loop.call_soon_threadsafe(self._notify_callbacks, task_id, notify_payload)

        try:
            if request.mode == "cross_sectional":
                if not request.timeframe:
                    raise ValueError("timeframe is required for cross_sectional mode")

                symbols_resolved, config_hashes = self._plan_cross_sectional_load(request)
                if symbols_resolved is None:
                    raise ValueError("cross_sectional mode requires cross_sectional_runs or symbols")

                if len(symbols_resolved) < 2:
                    raise ValueError("cross_sectional mode requires at least 2 symbols")

                multi_features = self._feature_library.load_multi(
                    symbols_resolved,
                    request.timeframe,
                    config_hashes=config_hashes,
                )
                frames: List[pd.DataFrame] = []
                for symbol, frame in multi_features.items():
                    if frame is None or frame.empty:
                        raise ValueError(f"Feature data is empty for {symbol}/{request.timeframe}")
                    symbol_frame = frame.copy()
                    symbol_frame["_symbol"] = symbol
                    frames.append(symbol_frame)

                cross_df = pd.concat(frames, axis=0)
                cross_df = cross_df.set_index("_symbol", append=True)

                labels_path = request.labels_path
                if not labels_path:
                    cross_df = self._append_cross_sectional_labels(
                        cross_df,
                        symbols_resolved,
                        request.timeframe,
                    )

                report = await asyncio.to_thread(
                    analyzer.analyze_cross_sectional,
                    features=cross_df,
                    labels_path=labels_path,
                    config_override=config_override,
                    progress_callback=progress_callback,
                    timeframe=request.timeframe,
                )
            else:
                symbol = request.symbol
                timeframe = request.timeframe
                config_hash = (request.config_hash or "").strip() or None
                features_path = request.features_path
                meta_path = request.meta_path
                resolved_config_hash: Optional[str] = config_hash
                feature_manifest_hint: Optional[str] = None   # registry 條目之 manifest 路徑（G3-D10）

                if symbol and timeframe:
                    # UAT 2026-09-09：service 之 registry 為啟動時快照 ⇒ 啟動後生成的 run 一律 run not found；解析前重讀
                    self._feature_library.reload_registry()
                    if config_hash:
                        entry = self._feature_library.get_entry(symbol, timeframe, config_hash)
                        # fail-closed 僅在需要由 registry 解析/物化資料時才強制——這才是 run-selector
                        # 消歧保證的作用點(features_path 缺席→避免靜默挑到別的 run)。呼叫端已明確
                        # 提供 features_path(如 golden replay/artifact 重放)時,不因該 run 未註冊而擋。
                        # 注意:此時 entry 不餵給 analyzer(分析改用 features_path),僅在 meta_path
                        # 亦缺席時用於補寫 meta(見下方 materialize/meta 分支);故 replay 呼叫端應一併
                        # 提供 meta_path 或 labels_path,否則未註冊 run 會缺 meta(下游 label 生成需之)。
                        if entry is None and not features_path:
                            raise ValueError(f"run not found: {symbol}/{timeframe}/{config_hash}")
                    else:
                        entry = self._feature_library.find_latest_materialized(
                            symbol,
                            timeframe,
                        )
                        if entry is None:
                            entry = None
                        else:
                            logger.warning(
                                "未指定 config_hash，回退最新 run %s/%s",
                                symbol,
                                timeframe,
                            )
                            resolved_config_hash = str(entry.get("config_hash") or "")

                    if entry:
                        feature_manifest_hint = str(entry.get("hdf5_relative_path") or "") or None
                    if entry and not features_path:
                        features_path, meta_path = self._materialize_features_for_ic(
                            symbol,
                            timeframe,
                            resolved_config_hash,
                        )
                    elif entry and not meta_path:
                        meta_path = self._write_ic_meta_json(
                            symbol,
                            timeframe,
                            resolved_config_hash,
                        )

                if not features_path:
                    raise ValueError("features_path is required when FeatureLibrary symbol/timeframe is unavailable")

                labels_path = request.labels_path
                kline_reader = None
                if not labels_path:
                    kline_reader = create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR)

                # ── GAP-3 UX Task 7.0b ④：事件分支之五階段編排（唯一取得點） ──────
                # 🔴 **只在 `event_import_id` 存在時進入**——這個 guard 就是 over 向的保護：
                #    cross-sectional（上方分支）與純特徵 longitudinal 都不會走到這裡。
                event_label_values = None
                event_label_owners = None
                event_context = None
                event_timestamps = request.event_timestamps or None
                # EVTLABEL Task 2.2：非事件 run 不進下方分支 ⇒ 先給空 dict，
                # 讓後面 `staged.get("event_isolation")` 在全域路徑安全回 None（不是 NameError）。
                staged: Dict[str, Any] = {}
                if request.event_import_id:
                    if event_batch is None:
                        raise ValueError(
                            f"event_import_id={request.event_import_id!r} 但未取得該批 records"
                            "——route 層須先查出並傳入（Rule 4 禁 service 互相 import）"
                        )
                    staged = self._run_event_label_stages(
                        request, event_batch,
                        features_path=features_path, meta_path=meta_path,
                        feature_manifest_path=feature_manifest_hint,
                    )
                    event_timestamps = staged["event_timestamps"]
                    event_label_values = staged["event_label_values"]
                    event_label_owners = staged["event_label_owners"]
                    event_context = staged["event_context"]
                    # 🔴 階段 4 **真的套用**（`CODEX-R1-P1-02`：原本只算不用）：
                    #    把 per-symbol purge 下界換算成列數後注入 IC 切分器之 `embargo`。
                    #    只在**現行值較小**時提高——不得因為事件分析而放寬既有設定。
                    config_override = dict(config_override or {})
                    staged["embargo_before_event"] = int(config_override.get("embargo") or 0)  # EVTALIGN Task 5.1
                    # 🔴 B2 review R1 `CODEX-R1-P2-01`：**抬高前**的原始 embargo 另存，
                    #    以顯式參數傳給掃描格（不塞進 config_override——那正是本票剛擋掉的通道）。
                    original_embargo = int(config_override.get("embargo") or 0)
                    # 🔴 EVTLABEL Task 2.1（同掃描格路徑）：embargo 只承載 look-ahead 深度；
                    #    答案窗改由 `event_isolation.label_window_rows` 抬 purge（Task 2.2）。
                    config_override["embargo"] = max(
                        int(config_override.get("embargo") or 0), int(staged["lookahead_depth_rows"]),
                    )
                    # 🔴 `G3-D2` **D4.2／D4.3**：k 之雙值揭露 ＋ 兩個條件上界。
                    #    兩者都是**給 UI 看的事實**，不是輸入鎖；缺任一欄 ⇒ capability
                    #    `missing_decision_offset_disclosure`（fail-closed：沒揭露就不算數）。
                    k_disclosure = self._event_k_disclosure(request, event_batch)
                    if request.event_label_scan is not None:
                        # 🔴 `CODEX-R1-P1-01`：傳 **factory** 不傳實例——每格自己造 analyzer，
                        #    逾時之格的殘存 worker 因此碰不到他格與網格後之主分析。
                        scan = await self._run_scan_grid(
                            task_id, create_ic_analyzer, request, event_batch,
                            features_path=features_path, meta_path=meta_path,
                            feature_manifest_path=feature_manifest_hint,
                            labels_path=labels_path, kline_reader=kline_reader,
                            config_override=config_override,
                            progress_callback=progress_callback,
                            original_embargo=original_embargo,
                        )
                    else:
                        scan = None
                    with self._lock:
                        info = self._tasks.get(task_id)
                        if info:
                            # 揭露本次分析用的 receipt 身分（Task 7.0b ⑩ 之可追溯性）
                            info["analysis_alignment_receipt_hash"] = staged[
                                "analysis_alignment_receipt_hash"
                            ]
                            info["prepared_token"] = staged["prepared_token"]
                            # G3-D17：被排除的他 symbol 事件計數（loud，不靜默）
                            info["events_excluded_by_symbol"] = staged["events_excluded_by_symbol"]
                            # 🔴 `G3-D2` D5.3：抽樣設計揭露（無條件隨機 vs case-control）。
                            info["event_sample_design"] = staged["event_sample_design"]
                            info.update(k_disclosure)
                            if scan is not None:
                                info["event_label_scan"] = scan

                report = await asyncio.to_thread(
                    analyzer.analyze,
                    features_path=features_path,
                    labels_path=labels_path or "",
                    meta_path=meta_path,
                    config_override=config_override,
                    progress_callback=progress_callback,
                    kline_reader=kline_reader,
                    event_timestamps=event_timestamps,
                    event_label_values=event_label_values,
                    event_label_owners=event_label_owners,
                    event_context=event_context,
                    # EVTLABEL Task 2.2：主路徑同樣以顯式 kwarg 傳隔離區列數（非事件 run ⇒ None）
                    event_isolation=staged.get("event_isolation"),
                    # EVTLABEL Task 3.3：匯入 0/1 標籤與**請求**模式，皆以顯式 kwarg 傳。
                    #    空 map ⇒ None（orchestrator 據此知道「這批根本沒有 0/1 可用」，
                    #    與「有但被判不可用」是兩件事，reason 不同）。
                    event_binary_labels=(staged.get("event_binary_labels") or None),
                    label_mode_requested=staged.get("label_mode_requested") or "auto",
                    label_mode_hint=staged.get("label_mode_hint"),
                )
                if request.event_import_id:
                    _assert_event_triple_bound(staged, report)
                    _inject_period_alignment(staged, report)
                    _inject_isolation_source(staged, report)

            with self._lock:
                task_info = self._tasks.get(task_id)
            if task_info:
                self._set_result(task_info, report)  # lock 外 normalize＋守衛（raise ⇒ 由下方 except 標 failed，status 不會先變 completed）
            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["sub_progress"] = None  # 終態後不留上一子步驟的殘影（UAT 2026-09-09：跑完仍顯示 grouped_ic 5/5）
                    task_info["progress"] = 1.0

            # LA-1 B3-TASK-01：completion callback 必含 root 紅標
            completed_payload: Dict[str, Any] = {
                "task_id": task_id,
                "stage": "completed",
                "progress": 1.0,
                "message": "completed",
                "status": "completed",
            }
            if isinstance(report, dict):
                from momentum.Analysis.ic_reporter import normalize_analysis_status
                from momentum.core.contracts import deny_factor_in_ok_oos

                completed_payload["analysis_status"] = normalize_analysis_status(
                    report.get("analysis_status")
                )
                if "oos_guarantees" in report:
                    completed_payload["oos_guarantees"] = bool(report.get("oos_guarantees"))
                else:
                    completed_payload["oos_guarantees"] = (
                        completed_payload["analysis_status"] == "ok_oos"
                    )
                # LA-2 B3：root ok_oos + nested factor loud → deny
                try:
                    deny_factor_in_ok_oos(report)
                    deny_factor_in_ok_oos(completed_payload)
                except ValueError as deny_exc:
                    logger.error("deny_factor_in_ok_oos: %s", deny_exc)
                    completed_payload["analysis_status"] = "degraded_full_sample"
                    completed_payload["oos_guarantees"] = False
                    completed_payload["factor_deny_reason"] = str(deny_exc)
            else:
                completed_payload["analysis_status"] = "degraded_full_sample"
                completed_payload["oos_guarantees"] = False
            self._notify_callbacks(task_id, completed_payload)

            logger.info("IC analysis task completed: %s", task_id)

        except AnalysisCancelled as exc:
            logger.info("IC analysis task cancelled: %s (%s)", task_id, exc)
            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "cancelled"
                    task_info["sub_progress"] = None  # 終態後不留上一子步驟的殘影（UAT 2026-09-09：跑完仍顯示 grouped_ic 5/5）
                    task_info["current_stage"] = "cancelled"
                    task_info["error"] = f"已取消：{exc}"
            self._notify_callbacks(task_id, {
                "task_id": task_id, "stage": "cancelled", "progress": task_info.get("progress", 0.0) if task_info else 0.0,
                "message": f"已取消：{exc}", "status": "cancelled",
            })
            return
        except Exception as exc:
            logger.error("IC analysis task failed: %s", exc, exc_info=True)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["sub_progress"] = None  # 終態後不留上一子步驟的殘影（UAT 2026-09-09：跑完仍顯示 grouped_ic 5/5）
                    task_info["progress"] = 1.0
                    task_info["current_stage"] = "failed"
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "failed",
                "progress": 1.0,
                "message": str(exc),
                "status": "failed",
            })

    def cancel_task(self, task_id: str) -> Optional[str]:
        """要求協作式取消：回傳 None（無此任務）／"already_terminal"／"cancel_requested"。

        Python 殺不掉正在算的執行緒，只能在下一個進度回報點停（預處理每 100 欄一點、其餘為階段邊界）；
        取消後狀態變 `cancelled`（非 failed）。
        """
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            if task_info.get("status") in ("completed", "failed", "cancelled"):
                return "already_terminal"
            task_info["cancel_requested"] = True
            return "cancel_requested"

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            payload = {
                "task_id": task_info["task_id"],
                "status": task_info["status"],
                "progress": task_info.get("progress", 0.0),
                "current_stage": task_info.get("current_stage"),
                "current_step": task_info.get("current_step"),
                "applied_tier": task_info.get("applied_tier", "intermediate"),
                "error": task_info.get("error"),
                # GAP-3 UX Task 6.3：這個 run 的特徵數。
                # 🔴 沒有就給 None，**不填假值**——UAT 已證實「progress==0.12 卡 15 分鐘」
                #    這種填充值比沒有更誤導（使用者以為在動）。
                "feature_count": task_info.get("feature_count"),
                # 🔴 `G3-D2` D4.3：掃描格數進度（未掃 ⇒ None，**不填 0**——0 會被讀成
                #    「掃了 0 格」，而事實是「這次沒有掃描」）。
                "scan_done": task_info.get("scan_done"),
                "scan_total": task_info.get("scan_total"),
                # EVTALIGN Task 4.1：階段內進度與 WARN（未到／沒有 ⇒ None／[]，不填假值）
                "sub_progress": task_info.get("sub_progress"),
                "warnings": list(task_info.get("warnings") or []),
                # 降級重跑之原因（進行中即有；沒有降級 ⇒ None）
                "fallback": task_info.get("fallback"),
                "cancel_requested": bool(task_info.get("cancel_requested")),
                "result_revision": task_info.get("result_revision"),
            }
            # 🔴 `GAP3_EVENT_DISCLOSURE` Task 1.3：降級原因**刻意不進 task status**。
            #    它住 `report.metadata.oos_downgrade`（orchestrator 之單一寫出點），
            #    前端之 `DegradedBanner` 已經在讀 `report.metadata`（同 `event_filter` 那條路）
            #    ⇒ 再開一條 task_info 投影會是沒有消費端的死表面。
            # 🔴 `G3-D2` D4.2／D4.3 之揭露欄：只在事件分析路徑存在時才出現
            #    （非事件分析沒有 k 可言，填 None 會讓 UI 以為有這件事）。
            for key in (
                "decision_offset_bars_capability", "decision_offset_bars_reason",
                "decision_offset_bars_record_values", "decision_offset_bars_analysis",
                "decision_offset_bars_scan_max",
                "bounds_scope_symbol", "bounds_scope_excluded_events",
                "k_max_feasible_at_h", "h_max_feasible_at_k",
                "k_bound_status", "h_bound_status", "event_label_scan",
            ):
                if key in task_info:
                    payload[key] = task_info[key]
            # LA-1 B3-ENUM-01：completed 時鏡像 root 紅標（fail-closed normalize）
            result = task_info.get("result")
            if isinstance(result, dict) and task_info.get("status") == "completed":
                from momentum.Analysis.ic_reporter import normalize_analysis_status

                payload["analysis_status"] = normalize_analysis_status(
                    result.get("analysis_status")
                )
                if "oos_guarantees" in result:
                    payload["oos_guarantees"] = bool(result.get("oos_guarantees"))
                else:
                    payload["oos_guarantees"] = (
                        payload["analysis_status"] == "ok_oos"
                    )
            return payload

    # ── ICRESULT_PAGING（docs/ICRESULT_PAGING_SPEC.md §C-7／§C-9）────────────────────────────
    def _set_result(self, task_info: Dict[str, Any], report: Any) -> int:
        """唯一的 result 寫點：寫入時一次 `_to_json_compatible`＋`deny_factor_in_ok_oos`，**只保留一棵 normalized 樹**，遞增 revision。

        守衛 raise ⇒ 不寫入、revision 不變（初次完成由背景 try 標 failed；refilter 由呼叫端轉 422）。
        🔴 呼叫端**不得**持 `self._lock`（B1 review `GROK-R1-P1-01`）：39k 報告 normalize＋守衛 ≈4 s，須在 lock 外做，
        lock 內只做賦值／遞增 revision／快取失效（O(1)），否則寫入期間所有 /task／/result／/summary 讀取被擋。
        """
        from momentum.core.contracts import deny_factor_in_ok_oos

        normalized = self._to_json_compatible(report)  # lock 外
        if isinstance(normalized, dict):
            deny_factor_in_ok_oos(normalized)  # lock 外
        with self._lock:
            task_info["result"] = normalized
            task_info["result_revision"] = (task_info.get("result_revision") or 0) + 1
        try:
            _proj.sort_index_cache(load_ic_result_paging_contract()).invalidate_task(str(task_info.get("task_id") or ""))
        except Exception:  # noqa: BLE001 — 快取失效不得影響寫入
            pass
        return int(task_info["result_revision"])

    def _snapshot_result(self, task_id: str) -> Optional[Tuple[Any, Optional[int]]]:
        """lock 內同時取 `(result, result_revision)`；投影只吃此 snapshot（不可變）。"""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info or task_info.get("result") is None:
                return None
            return task_info.get("result"), task_info.get("result_revision")

    def _require_snapshot(self, task_id: str, revision: Optional[int]) -> Optional[Tuple[Any, Optional[int]]]:
        """取 snapshot；呼叫端帶 `revision` 且不符 ⇒ ResultRevisionMismatch（route 409）。"""
        snap = self._snapshot_result(task_id)
        if snap is None:
            return None
        if revision is not None and snap[1] != revision:
            raise ResultRevisionMismatch(current_revision=snap[1], requested=revision)
        return snap

    def get_result_summary_page(self, task_id: str, *, sort_by: str, sort_order: str, offset: int, limit: int, pass_class: Optional[str] = None, search: Optional[str] = None, revision: Optional[int] = None) -> Optional[Dict[str, Any]]:
        snap = self._require_snapshot(task_id, revision)
        if snap is None:
            return None
        report, rev = snap
        rows = report.get("summary_table") if isinstance(report, dict) else None
        page = _proj.paginate_summary(
            list(rows or []), sort_by=sort_by, sort_order=sort_order, offset=offset, limit=limit,
            pass_class=pass_class, search=search, contract=load_ic_result_paging_contract(),
            task_id=task_id, revision=rev,
        )
        page["result_revision"] = rev
        return page

    def get_result_feature_detail(self, task_id: str, feature_name: str, *, revision: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """回 None ⇒ task／result 缺席（404）；回 {"_missing": True} ⇒ 特徵不存在（404，由 route 區分）。"""
        snap = self._require_snapshot(task_id, revision)
        if snap is None:
            return None
        report, rev = snap
        if not isinstance(report, dict):
            return None
        detail = _proj.project_feature(report, feature_name, load_ic_result_paging_contract())
        if detail is None:
            return {"_missing": True}
        detail["result_revision"] = rev
        return detail

    def get_result(self, task_id: str, schema_version: Optional[int] = None, view: Optional[str] = None) -> Optional[Any]:
        """Get task result.

        ICRESULT_PAGING：`view="light"` 走投影（只讀 `_snapshot_result`，不再全樹正規化／守衛——已於 `_set_result` 做過）；
        無 `view` ⇒ 既有路徑逐位元組不變（G-1）。`view=light` 與 `schema_version=2` 互斥 ⇒ ValueError（route 400）。
        """
        if view is not None and view != "light":
            raise ValueError(f"unknown view: {view}")
        if view == "light":
            if schema_version == 2:
                raise ValueError("view=light and schema_version=2 are mutually exclusive")
            snap = self._require_snapshot(task_id, None)
            if snap is None:
                return None
            report, revision = snap
            if not isinstance(report, dict):
                raise ValueError("light view requires a dict report")
            return _proj.project_light_view(report, load_ic_result_paging_contract(), task_id=task_id, revision=revision)
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            result = task_info.get("result")

        if result is None:
            return None

        normalized = self._to_json_compatible(result)
        if isinstance(normalized, dict):
            # LA-2 B3-F2：回傳出口 deny root ok_oos + factor/diagnostic loud
            from momentum.core.contracts import deny_factor_in_ok_oos

            deny_factor_in_ok_oos(normalized)
            if not settings.ic_response_v2 or schema_version != 2:
                return normalized
            return self._build_v2_result(task_id, task_info, normalized)
        if not settings.ic_response_v2 or schema_version != 2:
            return {"raw": normalized}
        return self._build_v2_result(task_id, task_info, {})

    def _build_v2_result(
        self,
        task_id: str,
        task_info: Dict[str, Any],
        normalized_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build schema_version=2 response from the artifact as the single source of truth."""
        artifact_path = self._resolve_ic_v2_artifact_path(task_id, task_info, normalized_result)
        if artifact_path is None or not artifact_path.exists():
            response = ICResultV2Response(schema_version=2, artifact_uri=None, total_features=0)
            return response.model_dump()

        rows = create_ic_artifact_writer().read(artifact_path)
        sorted_rows = self._sort_artifact_rows(rows, "icir")
        top_n = self._resolve_v2_top_n(task_info)
        response = ICResultV2Response(
            schema_version=2,
            top_n_summary=sorted_rows[:top_n],
            artifact_uri=str(artifact_path),
            total_features=len(rows),
        )
        return response.model_dump()

    def _resolve_ic_v2_artifact_path(
        self,
        task_id: str,
        task_info: Dict[str, Any],
        normalized_result: Dict[str, Any],
    ) -> Optional[Path]:
        """Resolve the idempotent v2 artifact path for a task."""
        explicit = task_info.get("ic_response_v2_artifact_path")
        if explicit:
            return Path(str(explicit))

        config_hash = self._resolve_result_config_hash(task_info, normalized_result)
        if not config_hash:
            return None

        artifact_dir = Path(
            str(task_info.get("ic_artifact_dir") or settings.results_output_path / "ic_artifacts")
        )
        return artifact_dir / f"{task_id}_{config_hash}_v2.parquet"

    @staticmethod
    def _resolve_result_config_hash(
        task_info: Dict[str, Any],
        normalized_result: Dict[str, Any],
    ) -> Optional[str]:
        """Read config_hash from task metadata without guessing a replacement."""
        direct = task_info.get("req_config_hash")
        if direct:
            return str(direct)

        metadata = normalized_result.get("metadata")
        if isinstance(metadata, dict):
            config_hash = metadata.get("config_hash")
            if config_hash:
                return str(config_hash)
        return None

    @staticmethod
    def _sort_artifact_rows(rows: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """Sort artifact rows for top-N derivation using artifact values only."""
        descending = sort_by != "p_value"

        def key(row: Dict[str, Any]) -> tuple[int, float]:
            value = row.get(sort_by)
            if value is None:
                return (1, 0.0)
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return (1, 0.0)
            if math.isnan(numeric):
                return (1, 0.0)
            return (0, -numeric if descending else numeric)

        return sorted(rows, key=key)

    @staticmethod
    def _resolve_v2_top_n(task_info: Dict[str, Any]) -> int:
        """Resolve top-N from stored deep-analysis request metadata, defaulting to API contract."""
        raw_top_n = task_info.get("deep_analysis_top_n")
        if raw_top_n is None:
            request = task_info.get("deep_analysis_request")
            if isinstance(request, DeepAnalysisRequest):
                raw_top_n = request.top_n
            elif isinstance(request, dict):
                raw_top_n = request.get("top_n")
        if raw_top_n is None:
            return DeepAnalysisRequest().top_n
        return int(raw_top_n)

    def export_analysis(self, task_id: str, format_type: str, module_name: Optional[str] = None) -> Dict[str, Any]:
        """Export IC analysis result into requested format."""

        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                raise ValueError(f"Task not found: {task_id}")
            report = task_info.get("result")
            deep_report = task_info.get("deep_analysis_result")

        if not isinstance(report, dict):
            raise ValueError(f"Result not found: {task_id}")

        # LA-2 B3-F2：匯出出口一律 deny ok_oos + factor/diagnostic loud
        from momentum.core.contracts import deny_factor_in_ok_oos

        deny_factor_in_ok_oos(report)
        if isinstance(deep_report, dict):
            # deep nested under root-like envelope for walk
            deny_factor_in_ok_oos(
                {
                    "analysis_status": report.get("analysis_status"),
                    "deep_analysis_report": deep_report,
                }
            )

        normalized_format = (format_type or "").strip().lower()
        if normalized_format not in {"json", "ai_json", "csv_summary", "csv_detailed", "markdown", "hdf5"}:
            raise TypeError(f"Unsupported format: {format_type}")

        if normalized_format == "hdf5":
            metadata = report.get("metadata", {}) if isinstance(report, dict) else {}
            export_path = self._resolve_filtered_path(metadata)
            # LA-1 B3-H5-01：拒 stale stable-path
            from momentum.Analysis.ic_reporter import assert_filtered_export_fresh

            fresh_path = assert_filtered_export_fresh(report, export_path)
            return {
                "type": "file",
                "path": fresh_path,
                "filename": fresh_path.name,
                "media_type": "application/x-hdf5",
            }

        reporter = create_ic_reporter(config={})
        payload_for_export = dict(report)
        if isinstance(deep_report, dict):
            payload_for_export.setdefault("deep_analysis_report", deep_report)

        if normalized_format == "json":
            # F2: raw JSON 出口 sanitizer(ok §U 放行 / legacy 裸 map 擋)
            safe_report = (
                sanitize_factor_returns(report) if isinstance(report, dict) else report
            )
            content = json.dumps(safe_report, ensure_ascii=False, indent=2).encode("utf-8")
            return {
                "type": "bytes",
                "content": BytesIO(content),
                "filename": f"ic_report_{task_id}.json",
                "media_type": "application/json; charset=utf-8",
            }

        if normalized_format == "ai_json":
            payload = reporter.generate_ai_json(payload_for_export, deep_report=deep_report)
            content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            return {
                "type": "bytes",
                "content": BytesIO(content),
                "filename": f"ic_ai_{task_id}.json",
                "media_type": "application/json; charset=utf-8",
            }

        if normalized_format == "csv_summary":
            csv_text = reporter.generate_summary_csv(payload_for_export, deep_report=deep_report)
            return {
                "type": "bytes",
                "content": BytesIO(csv_text.encode("utf-8")),
                "filename": f"ic_summary_{task_id}.csv",
                "media_type": "text/csv; charset=utf-8",
            }

        if normalized_format == "csv_detailed":
            if not module_name:
                raise ValueError("module query parameter is required for csv_detailed")
            csv_text = reporter.generate_detailed_csv(payload_for_export, module_name)
            return {
                "type": "bytes",
                "content": BytesIO(csv_text.encode("utf-8")),
                "filename": f"ic_{module_name}_{task_id}.csv",
                "media_type": "text/csv; charset=utf-8",
            }

        markdown = reporter.generate_enhanced_markdown(payload_for_export, deep_report=deep_report)
        return {
            "type": "bytes",
            "content": BytesIO(markdown.encode("utf-8")),
            "filename": f"ic_report_{task_id}.md",
            "media_type": "text/markdown; charset=utf-8",
        }

    def list_features(
        self,
        features_path: Optional[str] = None,
        meta_path: Optional[str] = None,
        *,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        config_hash: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read available feature list from V7 Parquet or legacy HDF5.

        V2 query: (symbol, timeframe, config_hash) → FeatureReader.list_features_v2.
        V7 path: features_path = 'parquet:{symbol}:{config_hash}' → FeatureReader.
        Legacy: features_path = '/path/to/file.h5' → h5py.
        """
        metadata = self._load_meta(meta_path)

        if symbol and timeframe and config_hash:
            reader = create_feature_reader()
            names = reader.list_features_v2(symbol, timeframe, config_hash)
            return self._build_feature_items(names, metadata)

        if not features_path:
            raise ValueError("features_path or (symbol, timeframe, config_hash) is required")

        # V7 Parquet path via FeatureReader
        if features_path.startswith("parquet:"):
            parts = features_path.split(":")
            if len(parts) != 3:
                raise ValueError("Invalid Parquet source format, expected parquet:{symbol}:{config_hash}")
            _, symbol, config_hash = parts
            reader = create_feature_reader()
            names = reader.list_features(symbol, config_hash)
            return self._build_feature_items(names, metadata)

        # Legacy HDF5 path
        path = Path(features_path)
        if not path.exists():
            raise FileNotFoundError(f"features_path not found: {features_path}")

        with h5py.File(path, "r") as h5_file:
            if "data" not in h5_file:
                raise ValueError("Invalid features HDF5: missing 'data' group")
            group = h5_file["data"]

            if "feature_names" in group:
                raw_names = group["feature_names"][:]
                names = [
                    item.decode("utf-8") if isinstance(item, bytes) else str(item)
                    for item in raw_names
                ]
            elif "features" in group and len(group["features"].shape) == 2:
                names = [f"feature_{i}" for i in range(group["features"].shape[1])]
            else:
                raise ValueError("Invalid features HDF5: missing feature_names/features")

        return self._build_feature_items(names, metadata)

    def compute_ic_from_l7_raw(
        self,
        symbol: str,
        timeframe: str,
        config_hash: str,
        label: pd.Series,
        *,
        feature_base_path: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        ic_threshold: Optional[float] = None,
        allow_partial_ic: bool = False,
        method: Optional[str] = None,
        label_horizon: Optional[str] = None,
        selection_window: Optional[Dict[str, Any]] = None,
        split_id: Optional[str] = None,
        ic_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run IC-First raw streaming selection through momentum factories."""

        analyzer = create_ic_analyzer(config_override)
        ic_engine = getattr(analyzer, "_ic_engine", None)
        if ic_engine is None:
            raise RuntimeError("IC analyzer does not expose an IC engine")

        reader = create_feature_reader(feature_base_path)
        result = ic_engine.compute_ic_from_l7_raw(
            symbol=symbol,
            tf=timeframe,
            config_hash=config_hash,
            label=label,
            feature_reader=reader,
            ic_threshold=ic_threshold,
            allow_partial_ic=allow_partial_ic,
            method=method,
            label_horizon=label_horizon,
            selection_window=selection_window,
            split_id=split_id,
            ic_params=ic_params,
        )
        return self._to_json_compatible(result.to_dict())

    @staticmethod
    def _build_feature_items(
        names: List[str],
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build feature item list from names + optional metadata."""
        feature_items: List[Dict[str, Any]] = []
        for name in names:
            meta_item = metadata.get(name, {}) if isinstance(metadata.get(name, {}), dict) else {}
            feature_items.append({
                "feature_name": name,
                "category": meta_item.get("category"),
                "data_source": meta_item.get("data_source") or meta_item.get("source"),
                "family": meta_item.get("family"),
                "layer": meta_item.get("layer"),
            })
        return feature_items

    async def start_deep_analysis(self, task_id: str, request: DeepAnalysisRequest) -> Dict[str, str]:
        """Start deep analysis as a background task for an existing IC task."""
        analyzer = self.get_analyzer(task_id)
        if analyzer is None:
            raise ValueError(f"Task not found: {task_id}")

        status = self.get_task_status(task_id)
        if not status:
            raise ValueError(f"Task not found: {task_id}")
        if status.get("status") != "completed":
            raise ValueError(f"Task {task_id} is not ready for deep analysis")

        with self._lock:
            task_info = self._tasks.get(task_id)
            if task_info:
                task_info["status"] = "running"
                task_info["current_stage"] = "deep_analysis"
                task_info["current_step"] = None
                task_info["progress"] = 0.0
                task_info["error"] = None

        logger.info("Deep analysis started for task: %s", task_id)
        self._start_background_coroutine(
            lambda: self._run_deep_analysis(task_id, analyzer, request)
        )
        return {"task_id": task_id, "status": "running"}

    async def _run_deep_analysis(self, task_id: str, analyzer: Any, request: DeepAnalysisRequest) -> None:
        override = self._build_deep_module_override(request)

        def progress_callback(payload: Dict[str, Any]) -> None:
            progress = max(0.0, min(1.0, float(payload.get("progress", 0.0))))
            current_step = payload.get("module_name") or payload.get("current_step")
            message = payload.get("message")

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["status"] = "running"
                task_info["current_stage"] = "deep_analysis"
                task_info["current_step"] = current_step
                task_info["progress"] = progress

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "deep_analysis",
                "current_step": current_step,
                "progress": progress,
                "message": message,
                "status": "running",
            })

        try:
            selected_features = self._resolve_selected_features(
                analyzer=analyzer,
                selected_features=request.selected_features,
                top_n=request.top_n,
            )

            deep_report = await asyncio.to_thread(
                analyzer.run_deep_analysis,
                selected_features,
                override,
                progress_callback,
                None,
            )
            serialized = self._serialize_deep_report(deep_report)
            serialized = self._attach_cross_symbol_context(serialized, analyzer)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["sub_progress"] = None  # 終態後不留上一子步驟的殘影（UAT 2026-09-09：跑完仍顯示 grouped_ic 5/5）
                    task_info["current_stage"] = "deep_analysis"
                    task_info["current_step"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["deep_analysis_result"] = serialized

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "deep_analysis",
                "current_step": "completed",
                "progress": 1.0,
                "message": "deep analysis completed",
                "status": "completed",
            })
        except Exception as exc:
            logger.error("Deep analysis task failed: %s", exc, exc_info=True)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["sub_progress"] = None  # 終態後不留上一子步驟的殘影（UAT 2026-09-09：跑完仍顯示 grouped_ic 5/5）
                    task_info["current_stage"] = "deep_analysis"
                    task_info["current_step"] = "failed"
                    task_info["progress"] = 1.0
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "deep_analysis",
                "current_step": "failed",
                "progress": 1.0,
                "message": str(exc),
                "status": "failed",
            })

    def get_deep_analysis_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get deep analysis result."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            deep_result = task_info.get("deep_analysis_result")

        if deep_result is None:
            return None

        normalized = self._to_json_compatible(deep_result)
        if isinstance(normalized, dict):
            # F2: 讀出端 sanitize(ok 放行 / legacy 擋)
            return sanitize_factor_returns(normalized)
        return {"raw": normalized}

    async def start_full_analysis(self, request: ICFullAnalysisRequest) -> Dict[str, str]:
        """Start full analysis task (main + optional deep analysis)."""
        task_id = str(uuid.uuid4())
        config_override = self._build_config_override(request)
        analyzer = create_ic_analyzer(config_override)

        task_info = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.0,
            "current_stage": None,
            "current_step": None,
            "error": None,
            "result": None,
            "deep_analysis_result": None,
            "analyzer": analyzer,
            "applied_tier": (request.feature_tiers.active_preset if request.feature_tiers else "intermediate"),
            "created_at": datetime.now().isoformat(),
            # 🔴 `CODEX-R4-P2-01`：`/full-analysis` 的 task_info 原本**沒有這個欄位**
            #    ⇒ Task 6.3 的特徵數在整個 full-analysis 路徑上一律回 None。
            "feature_count": _resolve_feature_count(request, entrypoint="full_analysis"),
        }

        with self._lock:
            self._tasks[task_id] = task_info
            self._last_task_id = task_id

        logger.info("IC full analysis task started: %s", task_id)
        self._start_background_coroutine(
            lambda: self._run_full_analysis(task_id, analyzer, request, config_override)
        )
        return {"task_id": task_id, "status": "running"}

    async def _run_full_analysis(
        self,
        task_id: str,
        analyzer: Any,
        request: ICFullAnalysisRequest,
        config_override: Optional[Dict[str, Any]],
    ) -> None:
        def progress_callback(payload: Dict[str, Any]) -> None:
            stage_name = payload.get("stage_name") or payload.get("stage")
            current_step = payload.get("module_name") or payload.get("current_step") or stage_name
            progress = max(0.0, min(1.0, float(payload.get("progress", 0.0))))
            message = payload.get("message")

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["status"] = "running"
                task_info["current_stage"] = stage_name
                task_info["current_step"] = current_step
                task_info["progress"] = progress

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": stage_name,
                "current_step": current_step,
                "progress": progress,
                "message": message,
                "status": "running",
            })

        try:
            report = await asyncio.to_thread(
                analyzer.analyze,
                request.features_path,
                request.labels_path,
                request.meta_path,
                config_override,
                progress_callback,
                None,
                event_timestamps=getattr(request, "event_timestamps", None) or None,
            )

            deep_result: Optional[Dict[str, Any]] = None
            if request.deep_analysis:
                deep_request = request.deep_analysis_config or DeepAnalysisRequest()
                selected_features = self._resolve_selected_features(
                    analyzer=analyzer,
                    selected_features=deep_request.selected_features,
                    top_n=deep_request.top_n,
                )
                deep_override = self._build_deep_module_override(deep_request)
                deep_report = await asyncio.to_thread(
                    analyzer.run_deep_analysis,
                    selected_features,
                    deep_override,
                    progress_callback,
                    None,
                )
                deep_result = self._serialize_deep_report(deep_report)
                deep_result = self._attach_cross_symbol_context(deep_result, analyzer)
                if isinstance(report, dict):
                    report["deep_analysis_enabled"] = True
                    report["deep_analysis_report"] = deep_result

            with self._lock:
                task_info = self._tasks.get(task_id)
            if task_info:
                self._set_result(task_info, report)  # lock 外 normalize＋守衛
            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["sub_progress"] = None  # 終態後不留上一子步驟的殘影（UAT 2026-09-09：跑完仍顯示 grouped_ic 5/5）
                    task_info["current_stage"] = "completed"
                    task_info["current_step"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["deep_analysis_result"] = deep_result

            # LA-1 B3-TASK-01：full-analysis completion callback 必含 root 紅標
            full_completed_payload: Dict[str, Any] = {
                "task_id": task_id,
                "stage": "completed",
                "current_step": "completed",
                "progress": 1.0,
                "message": "full analysis completed",
                "status": "completed",
            }
            if isinstance(report, dict):
                from momentum.Analysis.ic_reporter import normalize_analysis_status
                from momentum.core.contracts import deny_factor_in_ok_oos

                full_completed_payload["analysis_status"] = normalize_analysis_status(
                    report.get("analysis_status")
                )
                if "oos_guarantees" in report:
                    full_completed_payload["oos_guarantees"] = bool(
                        report.get("oos_guarantees")
                    )
                else:
                    full_completed_payload["oos_guarantees"] = (
                        full_completed_payload["analysis_status"] == "ok_oos"
                    )
                # LA-2 B3-F2：full-analysis completion 亦 deny factor/diagnostic loud
                try:
                    deny_factor_in_ok_oos(report)
                    deny_factor_in_ok_oos(full_completed_payload)
                    if isinstance(deep_result, dict):
                        deny_factor_in_ok_oos(
                            {
                                "analysis_status": report.get("analysis_status"),
                                "deep_analysis_report": deep_result,
                            }
                        )
                except ValueError as deny_exc:
                    logger.error("deny_factor_in_ok_oos (full): %s", deny_exc)
                    full_completed_payload["analysis_status"] = "degraded_full_sample"
                    full_completed_payload["oos_guarantees"] = False
                    full_completed_payload["factor_deny_reason"] = str(deny_exc)
            else:
                full_completed_payload["analysis_status"] = "degraded_full_sample"
                full_completed_payload["oos_guarantees"] = False
            self._notify_callbacks(task_id, full_completed_payload)
        except Exception as exc:
            logger.error("IC full analysis task failed: %s", exc, exc_info=True)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["sub_progress"] = None  # 終態後不留上一子步驟的殘影（UAT 2026-09-09：跑完仍顯示 grouped_ic 5/5）
                    task_info["current_stage"] = "failed"
                    task_info["current_step"] = "failed"
                    task_info["progress"] = 1.0
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "failed",
                "current_step": "failed",
                "progress": 1.0,
                "message": str(exc),
                "status": "failed",
            })

    def get_analyzer(self, task_id: Optional[str]) -> Optional[Any]:
        """Get analyzer for task."""
        if not task_id:
            return None
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            return task_info.get("analyzer")

    def get_last_task_id(self) -> Optional[str]:
        """Get last task id."""
        with self._lock:
            return self._last_task_id

    async def apply_transforms(
        self,
        task_id: str,
        selected_features: List[str],
        rank: bool,
        zscore: bool,
        gaussian: bool,
        rank_window: int = 252,
        zscore_windows: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Apply rank/zscore/gaussian to IC-selected features and persist the result.

        Intended for the IC-First workflow:
          Feature Factory (IC-First mode) → IC Gatekeeper → *here* → downstream ML

        Transform order: rank → zscore → gaussian (Gaussian always last).
        """
        return await asyncio.to_thread(
            self._apply_transforms_sync,
            task_id,
            selected_features,
            rank,
            zscore,
            gaussian,
            rank_window,
            zscore_windows or [100, 252],
        )

    def _apply_transforms_sync(
        self,
        task_id: str,
        selected_features: List[str],
        rank: bool,
        zscore: bool,
        gaussian: bool,
        rank_window: int,
        zscore_windows: List[int],
    ) -> Dict[str, Any]:
        import numpy as np
        import pandas as pd

        if not selected_features:
            raise ValueError("selected_features must not be empty")
        if not (rank or zscore or gaussian):
            raise ValueError("At least one transform (rank / zscore / gaussian) must be enabled")

        # --- 1. Get task info ---
        with self._lock:
            task_info = self._tasks.get(task_id)
        if task_info is None:
            raise ValueError(f"IC analysis task not found: {task_id}")

        symbol: Optional[str] = task_info.get("req_symbol")
        timeframe: Optional[str] = task_info.get("req_timeframe")
        features_path: Optional[str] = task_info.get("req_features_path")
        config_hash: Optional[str] = task_info.get("req_config_hash")

        # --- 2. Load feature DataFrame ---
        df = self._load_features_for_transforms(
            symbol,
            timeframe,
            features_path,
            config_hash=config_hash,
        )
        logger.info("[apply_transforms] Loaded features: %d rows x %d cols", len(df), len(df.columns))

        # --- 3. Filter to selected_features (only those actually present) ---
        valid_cols = [c for c in selected_features if c in df.columns]
        missing = set(selected_features) - set(valid_cols)
        if missing:
            logger.warning("[apply_transforms] %d requested features not found: %s…", len(missing), list(missing)[:5])
        if not valid_cols:
            raise ValueError("None of the selected_features exist in the loaded feature data")
        df = df[valid_cols].copy()

        transforms_applied: List[str] = []

        # --- 4a. Rank Transform ---
        if rank:
            df = df.rolling(rank_window, min_periods=max(rank_window // 2, 1)).rank(pct=True)
            transforms_applied.append("rank")
            logger.info("[apply_transforms] Applied rank transform (window=%d)", rank_window)

        # --- 4b. Adaptive Z-Score ---
        if zscore:
            primary_window = min(zscore_windows)
            rolling = df.rolling(primary_window, min_periods=max(primary_window // 2, 1))
            mu = rolling.mean()
            sigma = rolling.std().fillna(0.0).clip(lower=1e-8)
            df = (df - mu) / sigma
            transforms_applied.append("zscore")
            logger.info("[apply_transforms] Applied adaptive zscore (window=%d)", primary_window)

        # --- 4c. Gaussian Normalize (always last) ---
        if gaussian:
            try:
                from scipy.stats import norm as _norm
                clip_lo, clip_hi = 0.001, 0.999
                # Gaussian is meaningful only if input is already rank-like (0-1).
                # If rank was not applied, coerce to empirical CDF first.
                if not rank:
                    df = df.rank(pct=True, axis=0)
                df = df.clip(lower=clip_lo, upper=clip_hi).apply(lambda col: _norm.ppf(col))
                transforms_applied.append("gaussian")
                logger.info("[apply_transforms] Applied gaussian normalize")
            except ImportError:
                logger.error("[apply_transforms] scipy not available, skipping gaussian")

        # --- 5. Persist result（含 LA-1 B3 analysis_status attr）---
        result_report = task_info.get("result") if isinstance(task_info, dict) else None
        from momentum.Analysis.ic_reporter import normalize_analysis_status

        # B3-ENUM-01：非字面 ok_oos 一律 degraded（禁 default ok_oos）
        raw_status = None
        oos_guarantees: Optional[bool] = None
        if isinstance(result_report, dict):
            raw_status = result_report.get("analysis_status")
            if "oos_guarantees" in result_report:
                oos_guarantees = bool(result_report.get("oos_guarantees"))
        analysis_status = normalize_analysis_status(raw_status)
        if oos_guarantees is None:
            oos_guarantees = analysis_status == "ok_oos"

        output_dir = Path("data_cache/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"post_ic_transforms_{task_id}.h5"
        df.to_hdf(str(output_path), key="features", mode="w", complevel=5)
        # oracle ⑤ / B3-XFORM-01：analysis_status attr 必寫；失敗 raise（禁吞回 success）
        from momentum.Analysis.ic_reporter import DegradedOOSViolation

        try:
            import h5py

            with h5py.File(str(output_path), "a") as handle:
                status_s = str(analysis_status)
                handle.attrs["analysis_status"] = status_s
                handle.attrs["oos_guarantees"] = bool(oos_guarantees)
                if "features" in handle:
                    handle["features"].attrs["analysis_status"] = status_s
        except DegradedOOSViolation:
            raise
        except Exception as exc:  # noqa: BLE001 — 轉唯一 gate exception
            logger.error(
                "[apply_transforms] failed to write analysis_status attr: %s",
                exc,
                exc_info=True,
            )
            raise DegradedOOSViolation(
                f"transforms HDF5 analysis_status attr write failed: {exc}"
            ) from exc
        logger.info("[apply_transforms] Saved %d x %d to %s", len(df), len(df.columns), output_path)

        return {
            "task_id": task_id,
            "selected_feature_count": len(valid_cols),
            "transforms_applied": transforms_applied,
            "output_path": str(output_path),
            "output_rows": len(df),
            "output_cols": len(df.columns),
            "analysis_status": analysis_status,
            "oos_guarantees": oos_guarantees,
        }

    def _load_features_for_transforms(
        self,
        symbol: Optional[str],
        timeframe: Optional[str],
        features_path: Optional[str],
        config_hash: Optional[str] = None,
    ):
        """Load feature DataFrame from FeatureLibrary (symbol/timeframe) or HDF5 path."""
        import pandas as pd

        if features_path:
            p = Path(features_path)
            if not p.exists():
                raise FileNotFoundError(f"Features path not found: {features_path}")
            if features_path.endswith(".h5") or features_path.endswith(".hdf5"):
                return pd.read_hdf(features_path)
            if features_path.endswith(".parquet"):
                return pd.read_parquet(features_path)
            raise ValueError(f"Unsupported features file format: {features_path}")

        if symbol and timeframe:
            try:
                return self._feature_library.load(
                    symbol,
                    timeframe,
                    config_hash=config_hash,
                )
            except Exception as exc:
                logger.warning("[apply_transforms] FeatureLibrary.load failed: %s; trying path fallback", exc)

        raise ValueError(
            "Cannot load features: no symbol/timeframe or features_path stored in task. "
            "Re-run IC analysis with a valid symbol+timeframe or features_path."
        )

    async def refilter(self, task_id: str, thresholds: Dict[str, Any], view: Optional[str] = None) -> Dict[str, Any]:
        """Refilter using cached IC results."""
        analyzer = self.get_analyzer(task_id)
        if analyzer is None:
            raise ValueError(f"task not found: {task_id}")

        report = analyzer.refilter(thresholds)
        with self._lock:
            task_info = self._tasks.get(task_id)
        if task_info:
            # ICRESULT_PAGING §C-7(b)：先驗後寫——守衛 raise ⇒ 舊 result／revision 不變、task 仍 completed、route 422
            # （normalize＋守衛在 lock 外，GROK-R1-P1-01）
            try:
                self._set_result(task_info, report)
            except ValueError as exc:
                raise ResultValidationError(str(exc)) from exc

        # 🔴 UAT B16（2026-09-02，票 `G3-D12`）：原本直接回 analyzer 的原始 dict，內含 NaN／inf（例如 decay 擬合失敗、
        #    survivors=0 時的統計）⇒ JSONResponse 500「Out of range float values」⇒ 瀏覽器只看到 Failed to fetch。
        #    `/result` 走 `get_result()`（`_to_json_compatible` 把非有限值轉 null＋F2 sanitizer）而沒事；
        #    refilter 必須走**同一出口**，不得另一份序列化規則。
        if view is not None:  # route 已驗只准 light
            return self.get_result(task_id, view="light")
        return self.get_result(task_id)

    def register_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Register notification callback."""
        with self._lock:
            self._callbacks.setdefault(task_id, []).append(callback)

    def unregister_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Unregister notification callback."""
        with self._lock:
            callbacks = self._callbacks.get(task_id, [])
            if callback in callbacks:
                callbacks.remove(callback)
            if not callbacks and task_id in self._callbacks:
                del self._callbacks[task_id]

    def _notify_callbacks(self, task_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            callbacks = list(self._callbacks.get(task_id, []))
        for callback in callbacks:
            try:
                callback(payload)
            except Exception as exc:
                logger.error("IC notification callback failed: %s", exc, exc_info=True)

    def _build_config_override(self, request: ICAnalyzeRequest) -> Optional[Dict[str, Any]]:
        override = request.config_override or {}
        if not isinstance(override, dict):
            raise ValueError("config_override must be a dict")

        if request.event_query:
            override = self._deep_merge(override, {
                "event_filter": {
                    "enabled": True,
                    "query": request.event_query,
                }
            })
        elif request.event_timestamps or getattr(request, "event_import_id", None):
            # GAP-3 B5.2（CODEX-R1-P1-01）：只給 timestamps（從已匯入案例選事件）亦須啟用 event filter，
            # 否則 orchestrator 因 enabled=False 直接回 mode=none、事件被靜默丟棄。
            # 🔴 UAT B17（2026-09-02，票 `G3-D13`）：B10 把前端改成只送 `event_import_id`（與 timestamps 互斥）後，
            #    這裡沒跟著加 ⇒ 五階段編排算出 timestamps／label 也餵進 analyzer，但 stage3 因 enabled=False
            #    回 `mode=none`——整份「事件模式」報告其實是全樣本 IC（只多了 purge embargo），
            #    `statistic_kind` 等條件 IC 標記全部不存在，畫面與 `analysis_status=ok_oos` 卻看不出來。
            override = self._deep_merge(override, {"event_filter": {"enabled": True}})

        if request.feature_filter:
            override = self._deep_merge(override, {
                "feature_filter": request.feature_filter.model_dump(exclude_none=True)
            })

        if request.deep_analysis_config and request.deep_analysis_config.config_override:
            override = self._deep_merge(override, request.deep_analysis_config.config_override)

        if request.feature_tiers:
            override = self._deep_merge(
                override,
                {"feature_tiers": request.feature_tiers.model_dump(exclude_none=True)},
            )

        if request.deep_analysis_config:
            override = self._deep_merge(
                override,
                self._build_deep_module_override(request.deep_analysis_config),
            )

        return override or None

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _build_deep_module_override(self, request: DeepAnalysisRequest) -> Dict[str, Any]:
        """組 deep 模組 override;typed net_ic 欄最後注入,override 不得蓋 typed。

        注意:request 欄名 `net_ic`,config/模組鍵 `net_ic_analysis`——此處映射。
        config_override.net_ic_analysis 已於 Pydantic 層整節 reject(T-F12)。
        """
        modules = request.modules
        # 先吃 config_override(其他節仍允許);防禦性剔除 net_ic_analysis
        base: Dict[str, Any] = dict(request.config_override or {})
        base.pop("net_ic_analysis", None)

        net_ic = request.net_ic
        typed: Dict[str, Any] = {
            "factor_return": {"enabled": modules.factor_return},
            "factor_centrality": {"enabled": modules.factor_centrality},
            "trend_analysis": {"enabled": modules.trend_analysis},
            "parameter_sensitivity": {"enabled": modules.parameter_sensitivity},
            "rolling_oos": {"enabled": modules.rolling_oos},
            "factor_orthogonalization": {"enabled": modules.factor_orthogonalization},
            "factor_exposure": {"enabled": modules.factor_exposure},
            "long_short_analysis": {"enabled": modules.long_short_analysis},
            "feature_quality_diagnostics": {"enabled": modules.feature_quality_diagnostics},
            # typed 最後:enabled + cost 三鍵(T-F16 union 序列化由 _to_json_compatible 保形)
            "net_ic_analysis": {
                "enabled": modules.net_ic_analysis,
                "cost_enabled": bool(net_ic.cost_enabled),
                "cost_bps": net_ic.cost_bps,
            },
        }
        # merge 順序:base 先、typed 後 → typed 覆蓋同鍵
        return self._deep_merge(base, typed)

    def _resolve_selected_features(
        self,
        analyzer: Any,
        selected_features: Optional[List[str]],
        top_n: int,
    ) -> Optional[List[str]]:
        if selected_features:
            return selected_features

        top_features = analyzer.get_top_features(n=top_n)
        if not top_features:
            return None

        return [
            item.get("feature_name")
            for item in top_features
            if isinstance(item, dict) and item.get("feature_name")
        ]

    def _serialize_deep_report(self, deep_report: Any) -> Dict[str, Any]:
        if is_dataclass(deep_report):
            raw = asdict(deep_report)
        elif hasattr(deep_report, "model_dump"):
            raw = deep_report.model_dump()
        elif isinstance(deep_report, dict):
            raw = deep_report
        else:
            raw = {"raw": str(deep_report)}

        normalized = self._to_json_compatible(raw)
        if isinstance(normalized, dict):
            # F2: serializer + task storage 出口 sanitizer(ok 放行 / legacy 擋)
            return sanitize_factor_returns(normalized)
        return {"raw": normalized}

    def _attach_cross_symbol_context(self, deep_payload: Dict[str, Any], analyzer: Any) -> Dict[str, Any]:
        if not isinstance(deep_payload, dict):
            return deep_payload

        report = None
        if hasattr(analyzer, "get_report"):
            try:
                report = analyzer.get_report()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unable to read analyzer report for deep payload merge: %s", exc)

        if not isinstance(report, dict):
            return deep_payload

        for key in ("cross_symbol_validation", "cross_sectional_symbol_ic"):
            if key in report and key not in deep_payload:
                deep_payload[key] = self._to_json_compatible(report.get(key))

        return deep_payload

    # conditional metric 三鍵(T-F16 / F2 ⑯):§U 形狀守恆,序列化時原樣保留禁扁平化
    _CONDITIONAL_METRIC_KEYS: frozenset[str] = frozenset(
        {"net_factor_return", "breakeven_cost_bps", "profitable_after_cost"}
    )
    _UNION_SHAPE_KEYS: frozenset[str] = frozenset({"status", "value", "reason"})

    def _to_json_compatible(self, value: Any, ic_response_v2: bool = False) -> Any:
        """Recursively normalize nested values for FastAPI/Pydantic serialization.

        T-F16:conditional metric 三鍵物件({status,value,reason})原樣保留禁扁平化。
        """

        if value is None:
            return value

        if isinstance(value, float):
            return value if math.isfinite(value) else None

        if isinstance(value, (str, int, bool)):
            return value

        if isinstance(value, np.generic):
            scalar = value.item()
            if isinstance(scalar, float):
                return scalar if math.isfinite(scalar) else None
            return scalar

        if isinstance(value, np.ndarray):
            return [
                self._to_json_compatible(item, ic_response_v2=ic_response_v2)
                for item in value.tolist()
            ]

        if is_dataclass(value):
            payload = asdict(value)
            if isinstance(value, ICResult) and not ic_response_v2:
                payload.pop("eval_status", None)
            return self._to_json_compatible(payload, ic_response_v2=ic_response_v2)

        if hasattr(value, "model_dump"):
            return self._to_json_compatible(
                value.model_dump(),
                ic_response_v2=ic_response_v2,
            )

        if isinstance(value, dict):
            # discriminated union 形狀:{status, value, reason} — 遞迴保形,不抽 value
            if set(value.keys()) == self._UNION_SHAPE_KEYS:
                return {
                    "status": self._to_json_compatible(
                        value.get("status"), ic_response_v2=ic_response_v2
                    ),
                    "value": self._to_json_compatible(
                        value.get("value"), ic_response_v2=ic_response_v2
                    ),
                    "reason": self._to_json_compatible(
                        value.get("reason"), ic_response_v2=ic_response_v2
                    ),
                }
            out: Dict[str, Any] = {}
            for key, item in value.items():
                sk = str(key)
                # 三鍵在父 dict 層確保仍為物件(若誤傳裸值則包回 unavailable 形不在此;僅保 dict)
                if sk in self._CONDITIONAL_METRIC_KEYS and isinstance(item, dict):
                    out[sk] = self._to_json_compatible(item, ic_response_v2=ic_response_v2)
                else:
                    out[sk] = self._to_json_compatible(item, ic_response_v2=ic_response_v2)
            return out

        if isinstance(value, (list, tuple, set)):
            return [
                self._to_json_compatible(item, ic_response_v2=ic_response_v2)
                for item in value
            ]

        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass

        return str(value)

    def _materialize_features_for_ic(
        self,
        symbol: str,
        timeframe: str,
        config_hash: Optional[str],
    ) -> tuple[str, str]:
        """透過 FeatureLibrary 載入特徵並 materialize 成 orchestrator 可讀的 HDF5。"""
        features_df = self._feature_library.load(
            symbol,
            timeframe,
            config_hash=config_hash,
        )
        cache_dir = Path("data_cache/reports/ic_ingest_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        hash_key = config_hash or "latest"
        safe_key = f"{symbol}_{timeframe}_{hash_key}".replace("/", "_")
        h5_path = cache_dir / f"{safe_key}.h5"
        meta_path = cache_dir / f"{safe_key}_meta.json"

        if not h5_path.exists():
            self._write_features_h5(h5_path, symbol, timeframe, features_df)
        if not meta_path.exists():
            meta_payload = self._build_ic_metadata_from_run(
                symbol,
                timeframe,
                config_hash,
                list(features_df.columns),
            )
            meta_path.write_text(
                json.dumps(meta_payload, ensure_ascii=False),
                encoding="utf-8",
            )
        return str(h5_path.resolve()), str(meta_path.resolve())

    @staticmethod
    def _write_features_h5(
        path: Path,
        symbol: str,
        timeframe: str,
        features_df: pd.DataFrame,
    ) -> None:
        """將 DataFrame 寫入 IC orchestrator 可讀的 HDF5 格式。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        group_key = f"{symbol}/{timeframe}"
        index_values = features_df.index
        if isinstance(index_values, pd.DatetimeIndex):
            timestamps = index_values.view("int64") // 10**9
        else:
            timestamps = np.arange(len(features_df), dtype=np.int64)

        with h5py.File(path, "w") as file:
            group = file.create_group(group_key)
            group.create_dataset(
                "features",
                data=features_df.to_numpy(dtype=np.float32),
                compression="gzip",
            )
            group.create_dataset("timestamps", data=timestamps, compression="gzip")
            str_dtype = h5py.string_dtype(encoding="utf-8")
            group.create_dataset(
                "feature_names",
                data=np.array(features_df.columns.tolist(), dtype=object),
                dtype=str_dtype,
            )

    def _write_ic_meta_json(
        self,
        symbol: str,
        timeframe: str,
        config_hash: Optional[str],
        feature_names: Optional[List[str]] = None,
    ) -> str:
        """寫入 IC 分析用的 metadata JSON（symbol/timeframe 供 label 生成）。"""
        cache_dir = Path("data_cache/reports/ic_ingest_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        hash_key = config_hash or "latest"
        safe_key = f"{symbol}_{timeframe}_{hash_key}".replace("/", "_")
        meta_path = cache_dir / f"{safe_key}_meta.json"
        meta_payload = self._build_ic_metadata_from_run(
            symbol,
            timeframe,
            config_hash,
            feature_names or [],
        )
        meta_path.write_text(
            json.dumps(meta_payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(meta_path.resolve())

    def _build_ic_metadata_from_run(
        self,
        symbol: str,
        timeframe: str,
        config_hash: Optional[str],
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """從 run catalog 建立 IC orchestrator 需要的 per-feature metadata。"""
        metadata: Dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "config_hash": config_hash,
        }
        catalog_path: Optional[Path] = None
        if config_hash:
            catalog_path = (
                Path("data_cache/features")
                / symbol
                / timeframe
                / config_hash
                / "feature_catalog_cache.parquet"
            )
        if catalog_path and catalog_path.exists():
            catalog_df = pd.read_parquet(catalog_path)
            for _, row in catalog_df.iterrows():
                name = str(row.get("name"))
                if not name:
                    continue
                metadata[name] = {
                    "name": name,
                    "category": row.get("category") or "unknown",
                    "layer": row.get("layer") or 1,
                }
        for feature_name in feature_names:
            if feature_name not in metadata:
                metadata[feature_name] = {
                    "name": feature_name,
                    "category": "unknown",
                    "layer": 1,
                }
        return metadata

    def _append_cross_sectional_labels(
        self,
        cross_df: pd.DataFrame,
        symbols: List[str],
        timeframe: str,
    ) -> pd.DataFrame:
        """從 kline 為橫截面特徵附加 return_1 標籤欄。"""
        from momentum.factories import create_label_generator

        kline_reader = create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR)
        label_generator = create_label_generator()
        working_df = cross_df.copy()

        if not isinstance(working_df.index, pd.MultiIndex):
            raise ValueError("cross-sectional features must use MultiIndex")

        index_names = list(working_df.index.names)
        symbol_level_idx = working_df.index.nlevels - 1
        if "_symbol" in index_names:
            symbol_level_idx = index_names.index("_symbol")

        for symbol in symbols:
            raw_data = kline_reader.read_klines(symbol, timeframe)
            if raw_data is None or raw_data.empty or "close" not in raw_data.columns:
                raise ValueError(f"kline data unavailable for {symbol}/{timeframe}")
            if "timestamp" not in raw_data.columns:
                raise ValueError(f"kline data missing timestamp for {symbol}/{timeframe}")
            ts_raw = raw_data["timestamp"]
            if not np.issubdtype(ts_raw.dtype, np.integer):
                raise ValueError(
                    f"kline timestamp for {symbol}/{timeframe} must be integer epoch seconds, "
                    f"got {ts_raw.dtype}"
                )
            ts_values = ts_raw.to_numpy()
            if ts_values.size > 0 and np.any(ts_values < 0):
                raise ValueError(
                    f"kline timestamp for {symbol}/{timeframe} contains negative values"
                )
            if ts_values.size > 1 and np.any(np.diff(ts_values) <= 0):
                raise ValueError(
                    f"kline timestamp for {symbol}/{timeframe} must be strictly "
                    "increasing without duplicates"
                )
            kline_index = pd.DatetimeIndex(pd.to_datetime(ts_raw, unit="s"))
            close = raw_data["close"].copy()
            close.index = kline_index
            label_series = label_generator.generate_returns_by_type(
                close,
                1,
                "log",
            )
            symbol_mask = working_df.index.get_level_values(symbol_level_idx) == symbol
            if not symbol_mask.any():
                continue
            symbol_index = working_df.index[symbol_mask].droplevel(symbol_level_idx)
            if not isinstance(symbol_index, pd.DatetimeIndex):
                symbol_index = pd.DatetimeIndex(pd.to_datetime(symbol_index))
            aligned = label_series.reindex(symbol_index)
            matched_mask = symbol_index.isin(kline_index)
            if bool(matched_mask.any()):
                matched_index = symbol_index[matched_mask]
                direct = label_series.reindex(matched_index)
                reindexed = aligned.reindex(matched_index)
                valid = direct.notna().to_numpy() & reindexed.notna().to_numpy()
                if bool(valid.any()):
                    np.testing.assert_allclose(
                        reindexed.to_numpy(dtype=np.float64)[valid],
                        direct.to_numpy(dtype=np.float64)[valid],
                        rtol=1e-5,
                        atol=1e-5,
                        err_msg=(
                            f"label misalignment for {symbol}/{timeframe} at matched timestamps"
                        ),
                    )
            working_df.loc[symbol_mask, "return_1"] = aligned.to_numpy()

        return working_df

    def _load_meta(self, meta_path: Optional[str]) -> Dict[str, Any]:
        if not meta_path:
            return {}

        path = Path(meta_path)
        if not path.exists():
            raise FileNotFoundError(f"meta_path not found: {meta_path}")

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid meta JSON: {meta_path}") from exc

    def _resolve_filtered_path(self, metadata: Dict[str, Any]) -> Path:
        symbol = metadata.get("symbol") if isinstance(metadata, dict) else None
        timeframe = metadata.get("timeframe") if isinstance(metadata, dict) else None
        if symbol and timeframe:
            name = f"{symbol}_{timeframe}_filtered.h5"
        else:
            name = "filtered_features.h5"
        return Path("data_cache/features") / name

    def _start_background_coroutine(self, coroutine_factory: Callable[[], Any]) -> None:
        """Run async workflow in a daemon thread to avoid request-loop cancellation."""

        def runner() -> None:
            try:
                asyncio.run(coroutine_factory())
            except Exception as exc:
                logger.error("Background coroutine crashed: %s", exc, exc_info=True)

        threading.Thread(target=runner, daemon=True).start()


ic_analysis_service = ICAnalysisService()
