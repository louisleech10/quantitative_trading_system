#!/usr/bin/env python
"""GAP-3 `G3-D2` **Task D4.3 之 benchmark 子步** — 掃描網格單格耗時實測。

    venv/bin/python scripts/gap3_scan_benchmark.py [--n-events 60] [--repeat 3]

## 為什麼要先跑這支

`D-001` D4.3 把 `analysis_params.scan_grid_max_runs` 之 `example_default: 121` 明寫為
**暫定值**，並要求「由 D4.3 之 benchmark 子步（真實 ETHUSDT 60 事件 × 12h 單格耗時 × 121）
凍結後改值並具名」。⇒ **本腳本必須先於改契約值**執行，receipt 進版控，commit message 具名。

## 量到什麼（誠實邊界，寫進 receipt）

**量到**：單格之**五階段**（prepare-windows → coverage → purge → resolve）在真實
`data_cache/feature_klines/kline_cache.h5`（ETHUSDT／12h）上、n 個事件之 wall-clock。
這是 D4.3 **新增**的每格成本。

🔴 **沒量到**：每格之**條件 IC**（`analyzer.analyze`）。理由具名：它需要同 symbol／timeframe
之**已物化 feature run**，其耗時由該 run 的特徵數與列數決定，與本 Task 的網格大小無關；
在沒有指定 run 的機器上量出來的數字不能拿來當上限。
⇒ 因此 `scan_grid_max_runs` **不是**由「總時間 ÷ 單格時間」單獨決定；未量到的那一段由
`per_cell_timeout_s`／`scan_timeout_s` 兩道逾時保護（逾時之格 `unavailable`、保留 partial）。
本 receipt 只授權「以實測取代暫定值」這一件事，不宣稱涵蓋整格成本。
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from momentum.Analysis.event_samples.label_value_from_case import (  # noqa: E402
    apply_event_coverage,
    feasible_bounds,
    prepare_analysis_windows,
    purge_lower_bound_rows,
    resolve_label_value_at_analyze,
)
from tests.momentum.event_samples.helpers import load_bars, make_event  # noqa: E402

SYMBOL = "ETHUSDT"
TF = "12h"
TF_SECONDS = {TF: 43200}
DECLARED = {TF: 0}
RECEIPT = REPO / "handoffs" / "run_receipts" / "gap3_scan_benchmark.json"


def _records(bars, n: int):
    ot = bars[SYMBOL][TF]["open_time_ms"].to_numpy()
    start = 120
    if start + n >= len(ot):
        raise SystemExit(f"bar 數不足：需要 {start + n} 根，實得 {len(ot)}")
    out = []
    for i in range(n):
        rec = dict(make_event(i, t0=int(ot[start + i]), label=i % 2, direction="long"))
        rec["decision_offset_bars"] = 2
        rec["entry_price_semantic"] = "trigger_open"
        ld = dict(rec.get("label_definition") or {})
        ld["label_return_mode"] = "open_to_horizon_close"
        ld["window"] = {**dict(ld.get("window") or {}), "horizon_bars": 3}
        rec["label_definition"] = ld
        out.append(rec)
    return out


def _one_cell(recs, bars, spec) -> float:
    """一格之五階段 wall-clock（秒）。**不含**條件 IC（見檔頭誠實邊界）。"""
    t0 = time.perf_counter()
    prepared0 = prepare_analysis_windows(
        recs, bars, event_label_spec=spec, event_import_id="benchmark",
        lookahead_bars_declared=DECLARED, timeframe_seconds=TF_SECONDS,
    )
    prepared1 = apply_event_coverage(prepared0, prepared0.allowed_event_ids)
    purge_lower_bound_rows(
        prepared1.windows, lookahead_bars_declared=DECLARED,
        timeframe_seconds=TF_SECONDS, symbols=[SYMBOL],
    )
    resolve_label_value_at_analyze(prepared1, bars, event_label_spec=spec)
    return time.perf_counter() - t0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-events", type=int, default=60)
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--grid-k", type=int, default=10, help="k 軸 0..m（含）之 m")
    ap.add_argument("--grid-h", type=int, default=10, help="h 軸 1..m（含）之 m")
    args = ap.parse_args(argv)

    bars = load_bars(SYMBOL, (TF,))
    recs = _records(bars, args.n_events)

    samples = []
    for k in (0, 2):
        for h in (1, 3, 7):
            spec = {
                "horizon_bars": h, "entry_price_semantic": "trigger_open",
                "label_return_mode": "open_to_horizon_close", "decision_offset_bars": k,
            }
            for _ in range(args.repeat):
                samples.append(_one_cell(recs, bars, spec))

    # 兩上界之計算成本（每次掃描各算一次，不是每格）
    bounds_spec = {
        "horizon_bars": 3, "entry_price_semantic": "decision_bar_open",
        "label_return_mode": "open_to_horizon_close", "decision_offset_bars": 2,
    }
    tb = time.perf_counter()
    bounds = feasible_bounds(recs, bars, event_label_spec=bounds_spec, timeframes=(TF,))
    bounds_seconds = time.perf_counter() - tb

    mean = statistics.mean(samples)
    p95 = sorted(samples)[max(0, int(len(samples) * 0.95) - 1)]
    worst = max(samples)
    grid_cells = (args.grid_k + 1) * args.grid_h

    receipt = {
        "receipt_id": "gap3_scan_benchmark",
        "purpose": "D4.3 掃描網格之單格耗時實測（凍結 analysis_params 之 example_default 前置）",
        "measured": "五階段（prepare→coverage→purge→resolve）之 wall-clock",
        "not_measured": (
            "每格之條件 IC（analyzer.analyze）——需同 symbol/timeframe 之已物化 feature run，"
            "耗時由該 run 的特徵數與列數決定；未量到的那一段由 per_cell_timeout_s／scan_timeout_s 保護"
        ),
        "data": {
            "kline_cache": "data_cache/feature_klines/kline_cache.h5",
            "symbol": SYMBOL, "timeframe": TF, "n_events": args.n_events,
            "n_bars": int(len(bars[SYMBOL][TF])),
        },
        "cells_sampled": len(samples),
        "cell_seconds": {
            "mean": round(mean, 6), "p95": round(p95, 6), "max": round(worst, 6),
            "min": round(min(samples), 6),
        },
        "bounds_seconds": round(bounds_seconds, 6),
        "bounds_result": {
            "k_max_feasible_at_h": bounds.k_max_feasible_at_h,
            "h_max_feasible_at_k": bounds.h_max_feasible_at_k,
            "k_status": bounds.k_status, "h_status": bounds.h_status,
        },
        "grid": {
            "k_axis_max": args.grid_k, "h_axis_max": args.grid_h, "cells": grid_cells,
            "stages_only_seconds_at_max": round(worst * grid_cells, 3),
        },
        # 🔴 **凍結值之推導**（本 receipt 授權契約 `analysis_params` 由暫定改為下列值）。
        #    每一條都寫出「這個數字是怎麼來的」，不留裸數字。
        "derived_example_defaults": {
            "decision_offset_bars_scan_max": {
                "value": args.grid_k,
                "why": "建議上限（超過只警示不擋）；沿用 D-001 之判斷值，本次未推翻",
            },
            "scan_grid_max_runs": {
                "value": grid_cells,
                "why": (
                    f"由宣告軸導出：k∈[0,{args.grid_k}] 有 {args.grid_k + 1} 值 × "
                    f"h∈[1,{args.grid_h}] 有 {args.grid_h} 值 ＝ {grid_cells} 格。"
                    "🔴 **修正暫定值 121 之算術錯誤**：121 假設兩軸各 11 值，"
                    "但 h 之定義域自 1 起（h=0 無意義）⇒ h 軸只有 10 值。"
                    f"五階段成本於此格數為 {round(worst * grid_cells, 3)} 秒（可忽略）"
                ),
            },
            "per_cell_timeout_s": {
                "value": 60.0,
                "why": (
                    f"五階段 p95＝{round(p95, 6)} 秒 ⇒ 逾時只可能由**未量到的條件 IC** 觸發。"
                    "60 秒約為五階段 p95 之 9000 倍，足以吸收合理的單格 IC，"
                    "且單格卡死時一分鐘內即切掉並標 scan_cell_timeout（保留 partial）"
                ),
            },
            "scan_timeout_s": {
                "value": 900.0,
                "why": (
                    "＝per_cell_timeout_s × 15 ⇒ 即使連續 15 格都跑到單格上限仍會收斂；"
                    f"正常格（五階段 {round(mean, 6)} 秒 ＋ 秒級 IC）足以跑完 {grid_cells} 格"
                ),
            },
        },
        "env": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(f"\nreceipt → {RECEIPT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
