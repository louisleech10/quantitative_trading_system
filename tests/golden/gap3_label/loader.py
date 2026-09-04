"""GAP-3 `G3-D2` — `label_value` golden 之 **typed loader**（`D-001` §G／Task D1.4）。

## 為什麼要外部凍結檔

producer 的正確性有兩種壞法：①公式錯 ②**取價座標錯**。②之特徵是「值仍是合法數字」，
所以 assert-式測試很容易在錯的前提下全綠（`D-001` D4.1 之別名錯價正是此類）。
外部凍結檔把「這一批、這個 spec、這份 bar 表 ⇒ 這些值」釘成位元組，任何一項變動都要
**顯式重凍並在 commit message 具名**。

## 內容（逐項 exact，`atol=0`）

`data_snapshot_digest`、t0 清單、`event_label_spec`、`direction`、逐 event
`label_value`／`label_start_ms`／`label_end_ms`／`decision_at_ms`／`entry_at_ms`／
`entry_price_ref{bar_open_ms, field}`、NaN mask、`analysis_alignment_receipt_hash`、
逐 scope `purge_lower_bound_ms`。

## 手算法（唯一）

`check` **不另寫報酬公式**：它重跑五階段之生產函式，逐項與凍結值比對。
「手算」發生在**凍結那一次**（見 `scripts/gap3_label_golden.py --freeze` 之 docstring
與 `test_gap3_analysis_label_producer.py` D0 段之獨立手算斷言）。

## 🔴 `matrix_pending`（Phase D0 專用，D1.3 必須移除）

`SUPPORTED_MATRIX` 之開放是 `D-001` Task D1.3 的交付；Phase D0 只交付取價路徑。
⇒ D0 凍結 `open_to_*` 案例時，`spec_is_supported` 仍為 `False`，需要 `matrix_pending: true`
把 `supported` 旗標翻開（**其餘全部是真實 prepare 之產物**）。
**反向 fail-closed**：`matrix_pending` 為真而該 spec 已被矩陣支援 ⇒ 直接 FAIL
（「override 已無必要，請移除並重凍」）——這條保證 D1.3 開矩陣後這個旗標不能留著。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from momentum.Analysis.event_samples.canonical_serialize import (
    canonical_event_table_sha256,
)
from momentum.Analysis.event_samples.label_value_from_case import (
    apply_event_coverage,
    normalize_event_label_spec,
    prepare_analysis_windows,
    purge_lower_bound_rows,
    resolve_label_value_at_analyze,
    spec_is_supported,
)

#: golden JSON 之**必要鍵**（缺一即 loader raise；型別不符亦 raise）。
_REQUIRED: Tuple[str, ...] = (
    "case_id", "symbol", "timeframe", "direction", "event_import_id",
    "event_label_spec", "t0_ms", "lookahead_bars_declared", "timeframe_seconds",
    "data_snapshot_digest", "events", "nan_event_ids",
    "analysis_alignment_receipt_hash", "purge_lower_bound_ms_by_symbol",
)


class GoldenError(AssertionError):
    """golden 之 fail-closed 例外（載入層與比對層共用）。"""


@dataclass(frozen=True)
class GoldenCase:
    """一個凍結案例。欄集＝`_REQUIRED` ＋兩個 D0 旗標。"""

    path: Path
    case_id: str
    symbol: str
    timeframe: str
    direction: str
    event_import_id: str
    event_label_spec: Mapping[str, Any]
    t0_ms: Tuple[int, ...]
    lookahead_bars_declared: Mapping[str, int]
    timeframe_seconds: Mapping[str, int]
    data_snapshot_digest: str
    events: Mapping[str, Mapping[str, Any]]
    nan_event_ids: Tuple[str, ...]
    analysis_alignment_receipt_hash: str
    purge_lower_bound_ms_by_symbol: Mapping[str, int]
    matrix_pending: bool
    matrix_pending_reason: Optional[str]


@dataclass(frozen=True)
class Report:
    """比對結果。`ok` 為真 ⇔ `diffs` 為空（無「大致相符」）。"""

    case_id: str
    ok: bool
    diffs: Tuple[str, ...]


def bar_table_digest(bars: Mapping[str, Mapping[str, Any]], symbol: str, timeframe: str) -> str:
    """bar 表之 S-9 位元組 sha256。**同一 encoder**（禁另寫序列化）。

    只取 label 計算真正用到的四欄；`float` 原樣進 S-9（`-0.0` 保留，NaN → None）。
    """
    df = bars[symbol][timeframe]
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "n_rows": int(len(df)),
        "rows": [
            [int(o), int(c), float(op), float(cl)]
            for o, c, op, cl in zip(
                df["open_time_ms"].to_numpy(), df["close_time_ms"].to_numpy(),
                df["open"].to_numpy(), df["close"].to_numpy(),
            )
        ],
    }
    return canonical_event_table_sha256(payload)


def load_golden(path) -> GoldenCase:
    """讀 golden JSON → `GoldenCase`。**缺鍵／型別不符 ⇒ raise**（不補預設、不靜默跳過）。"""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise GoldenError(f"{p}: golden 頂層須為 object")
    missing = [k for k in _REQUIRED if k not in raw]
    if missing:
        raise GoldenError(f"{p}: golden 缺必要鍵 {missing}")
    pending = raw.get("matrix_pending", False)
    if type(pending) is not bool:
        raise GoldenError(f"{p}: matrix_pending 須為 bool")
    reason = raw.get("matrix_pending_reason")
    if pending and not (type(reason) is str and reason.strip()):
        raise GoldenError(f"{p}: matrix_pending 為真時 matrix_pending_reason 須為非空字串")
    return GoldenCase(
        path=p,
        case_id=str(raw["case_id"]),
        symbol=str(raw["symbol"]),
        timeframe=str(raw["timeframe"]),
        direction=str(raw["direction"]),
        event_import_id=str(raw["event_import_id"]),
        event_label_spec=dict(raw["event_label_spec"]),
        t0_ms=tuple(int(t) for t in raw["t0_ms"]),
        lookahead_bars_declared={str(k): int(v) for k, v in raw["lookahead_bars_declared"].items()},
        timeframe_seconds={str(k): int(v) for k, v in raw["timeframe_seconds"].items()},
        data_snapshot_digest=str(raw["data_snapshot_digest"]),
        events={str(k): dict(v) for k, v in raw["events"].items()},
        nan_event_ids=tuple(str(e) for e in raw["nan_event_ids"]),
        analysis_alignment_receipt_hash=str(raw["analysis_alignment_receipt_hash"]),
        purge_lower_bound_ms_by_symbol={
            str(k): int(v) for k, v in raw["purge_lower_bound_ms_by_symbol"].items()
        },
        matrix_pending=pending,
        matrix_pending_reason=reason if reason is None else str(reason),
    )


def records_of(case: GoldenCase) -> List[Dict[str, Any]]:
    """t0 清單 → records（二元 label：`i % 2`，`direction` 為批次常數）。

    🔴 `event_id` 之產生規則須與凍結時**逐字相同**（`ev{i}`），否則鍵集對不上。
    """
    from tests.momentum.event_samples.helpers import make_event

    return [
        make_event(
            i,
            t0=int(t0),
            label=i % 2,
            direction=case.direction,
            symbol=case.symbol,
            timeframe=case.timeframe,
        )
        for i, t0 in enumerate(case.t0_ms)
    ]


def run_case(case: GoldenCase, bars) -> Dict[str, Any]:
    """跑五階段（prepare → coverage(全集) → purge → resolve），回傳**可比對之扁平結構**。

    🔴 `apply_event_coverage` 以全集呼叫**不是**裝飾：它證明 golden 走的是與 live 相同的
    三階段串接（`prepared0 → prepared1`），而非直接 prepare→resolve 的捷徑。
    """
    prepared0 = prepare_analysis_windows(
        records_of(case), bars,
        event_label_spec=case.event_label_spec,
        event_import_id=case.event_import_id,
        lookahead_bars_declared=case.lookahead_bars_declared,
        timeframe_seconds=case.timeframe_seconds,
    )
    normalized = normalize_event_label_spec(case.event_label_spec)
    supported_now = spec_is_supported(normalized)
    if case.matrix_pending:
        if supported_now:
            raise GoldenError(
                f"{case.case_id}: matrix_pending 為真但 spec 已被 SUPPORTED_MATRIX 支援"
                "——override 已無必要，請移除 matrix_pending 並重凍（D1.3）"
            )
        prepared0 = replace(prepared0, supported=True, reason=None)
    prepared1 = apply_event_coverage(prepared0, prepared0.allowed_event_ids)
    result = resolve_label_value_at_analyze(
        prepared1, bars, event_label_spec=case.event_label_spec
    )
    refs = {e.event_id: e for e in prepared1.entry_price_refs}
    events: Dict[str, Dict[str, Any]] = {}
    for w in prepared1.windows:
        ref = refs.get(w.event_id)
        events[w.event_id] = {
            "label_value": result.label_values.get(w.event_id),
            "label_start_ms": int(w.label_start_ms),
            "label_end_ms": int(w.label_end_ms),
            "decision_at_ms": int(w.decision_at_ms),
            "entry_at_ms": int(w.entry_at_ms),
            "entry_price_ref": None if ref is None else {
                "bar_open_ms": int(ref.bar_open_ms), "field": ref.field,
            },
        }
    purge = purge_lower_bound_rows(
        prepared1.windows,
        lookahead_bars_declared=case.lookahead_bars_declared,
        timeframe_seconds=case.timeframe_seconds,
        symbols=[case.symbol],
    )
    return {
        "data_snapshot_digest": bar_table_digest(bars, case.symbol, case.timeframe),
        "events": events,
        "nan_event_ids": sorted(
            eid for eid, v in events.items() if v["label_value"] is None
        ),
        "analysis_alignment_receipt_hash": prepared1.analysis_alignment_receipt_hash,
        "purge_lower_bound_ms_by_symbol": {r.symbol: int(r.purge_lower_bound_ms) for r in purge},
        "supported": result.supported,
        "reason": result.reason,
    }


def check_golden(case: GoldenCase, bars) -> Report:
    """重跑後逐項 `==`。任一不等 ⇒ 列出 event_id 與 diff（**不聚合、不容差**）。"""
    diffs: List[str] = []
    actual = run_case(case, bars)

    if actual["data_snapshot_digest"] != case.data_snapshot_digest:
        # 🔴 直接 FAIL，**不得靜默跳過**：bar 表換了就沒有「同一批」可言。
        diffs.append(
            f"data_snapshot_digest: golden={case.data_snapshot_digest[:16]} "
            f"actual={actual['data_snapshot_digest'][:16]}（bar 表已變，值比對無意義）"
        )
        return Report(case_id=case.case_id, ok=False, diffs=tuple(diffs))

    if actual["analysis_alignment_receipt_hash"] != case.analysis_alignment_receipt_hash:
        diffs.append(
            f"analysis_alignment_receipt_hash: golden={case.analysis_alignment_receipt_hash[:16]} "
            f"actual={actual['analysis_alignment_receipt_hash'][:16]}"
        )

    exp_ids, act_ids = set(case.events), set(actual["events"])
    if exp_ids != act_ids:
        diffs.append(f"event 鍵集不等：golden−actual={sorted(exp_ids - act_ids)} "
                     f"actual−golden={sorted(act_ids - exp_ids)}")
    for eid in sorted(exp_ids & act_ids):
        exp, act = case.events[eid], actual["events"][eid]
        for key in ("label_value", "label_start_ms", "label_end_ms",
                    "decision_at_ms", "entry_at_ms", "entry_price_ref"):
            if exp.get(key) != act.get(key):
                diffs.append(f"{eid}.{key}: golden={exp.get(key)!r} actual={act.get(key)!r}")

    if sorted(case.nan_event_ids) != actual["nan_event_ids"]:
        diffs.append(f"nan mask: golden={sorted(case.nan_event_ids)} actual={actual['nan_event_ids']}")

    if case.purge_lower_bound_ms_by_symbol != actual["purge_lower_bound_ms_by_symbol"]:
        diffs.append(f"purge: golden={case.purge_lower_bound_ms_by_symbol} "
                     f"actual={actual['purge_lower_bound_ms_by_symbol']}")

    return Report(case_id=case.case_id, ok=not diffs, diffs=tuple(diffs))


def freeze_payload(case_meta: Mapping[str, Any], bars) -> Dict[str, Any]:
    """以 `case_meta`（不含期望值之骨架）跑一次五階段 → 完整 golden payload。"""
    skeleton = dict(case_meta)
    skeleton.setdefault("data_snapshot_digest", "")
    skeleton.setdefault("events", {})
    skeleton.setdefault("nan_event_ids", [])
    skeleton.setdefault("analysis_alignment_receipt_hash", "")
    skeleton.setdefault("purge_lower_bound_ms_by_symbol", {})
    tmp = Path("/dev/null")
    case = GoldenCase(
        path=tmp,
        case_id=str(skeleton["case_id"]),
        symbol=str(skeleton["symbol"]),
        timeframe=str(skeleton["timeframe"]),
        direction=str(skeleton["direction"]),
        event_import_id=str(skeleton["event_import_id"]),
        event_label_spec=dict(skeleton["event_label_spec"]),
        t0_ms=tuple(int(t) for t in skeleton["t0_ms"]),
        lookahead_bars_declared={str(k): int(v) for k, v in skeleton["lookahead_bars_declared"].items()},
        timeframe_seconds={str(k): int(v) for k, v in skeleton["timeframe_seconds"].items()},
        data_snapshot_digest="",
        events={},
        nan_event_ids=(),
        analysis_alignment_receipt_hash="",
        purge_lower_bound_ms_by_symbol={},
        matrix_pending=bool(skeleton.get("matrix_pending", False)),
        matrix_pending_reason=skeleton.get("matrix_pending_reason"),
    )
    actual = run_case(case, bars)
    out = {
        "case_id": case.case_id,
        "symbol": case.symbol,
        "timeframe": case.timeframe,
        "direction": case.direction,
        "event_import_id": case.event_import_id,
        "event_label_spec": dict(case.event_label_spec),
        "t0_ms": list(case.t0_ms),
        "lookahead_bars_declared": dict(case.lookahead_bars_declared),
        "timeframe_seconds": dict(case.timeframe_seconds),
        "data_snapshot_digest": actual["data_snapshot_digest"],
        "events": actual["events"],
        "nan_event_ids": actual["nan_event_ids"],
        "analysis_alignment_receipt_hash": actual["analysis_alignment_receipt_hash"],
        "purge_lower_bound_ms_by_symbol": actual["purge_lower_bound_ms_by_symbol"],
    }
    if case.matrix_pending:
        out["matrix_pending"] = True
        out["matrix_pending_reason"] = case.matrix_pending_reason
    return out
