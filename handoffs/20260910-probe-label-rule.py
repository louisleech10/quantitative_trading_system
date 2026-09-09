"""EVTLABEL ASSUME-1 探針：分析層實際套用的 label 視窗 vs 分析 spec（非匯入檔 label_definition）。

用法：venv/bin/python handoffs/20260910-probe-label-rule.py [import_json]
rc=0 ⇔ 每事件 label_end_ms − label_start_ms == 依分析 spec 換算之視窗（c2c: h×bar；open_to_horizon_close: (h+1)×bar，t₀ open→t₀+h close；open_to_close: 1×bar）；並印 label_window_feature_bars。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from momentum.Analysis.event_samples.pipeline import EventSamplePipeline

path = Path(sys.argv[1] if len(sys.argv) > 1 else "data_cache/events/20260909T130533Z-7f73e4c7.json")
doc = json.loads(path.read_text())
records = tuple(doc["records"])
lookahead = doc["lookahead_declaration"]["lookahead_bars_declared"]
# route 對 depth>=1 之 seed（api/routes/ic_analysis.py:242-289）：trigger_open / open_to_horizon_close / h=depth；
# 但受理 run 之 consumed label == CSV future_1bar_return ⇒ 實際 h=1。這裡兩組都跑，印出各自視窗。
specs = {
    "h1_c2c": {"horizon_bars": 1, "entry_price_semantic": "trigger_close", "label_return_mode": "close_to_close", "decision_offset_bars": 0},
    "h12_seed": {"horizon_bars": 12, "entry_price_semantic": "trigger_open", "label_return_mode": "open_to_horizon_close", "decision_offset_bars": 0},
}
pipeline = EventSamplePipeline()
tfs = sorted({r["timeframe"] for r in records})
symbols = sorted({r["symbol"] for r in records})
tf_seconds = pipeline.timeframe_seconds_for(sorted(set(tfs) | {"1h"}))
bars = pipeline.bars_from_kline_cache(symbols, tfs)
feature_bar_ms = tf_seconds["1h"] * 1000
rc = 0
for name, spec in specs.items():
    prepared = pipeline.prepare_analysis_windows(
        records, bars, event_label_spec=spec, event_import_id=doc["import_id"],
        lookahead_bars_declared=lookahead, timeframe_seconds=tf_seconds,
    )
    normalized = json.loads(prepared.normalized_spec_bytes)
    windows = prepared.windows
    ev_bar_ms = tf_seconds[windows[0].timeframe] * 1000
    h = normalized["horizon_bars"]; mode = normalized["label_return_mode"]
    expect = (h * ev_bar_ms) if mode == "close_to_close" else ((h + 1) * ev_bar_ms if mode == "open_to_horizon_close" else ev_bar_ms)
    bad = [w.event_id for w in windows if (w.label_end_ms - w.label_start_ms) != expect]
    win_ms = max(w.label_end_ms - w.label_start_ms for w in windows)
    depth_ms = max(int(lookahead[w.timeframe]) * tf_seconds[w.timeframe] * 1000 for w in windows)
    purge = prepared.purge_lower_bound_ms_by_symbol
    print(f"[{name}] normalized_spec={normalized} n_windows={len(windows)} window_ms={win_ms} "
          f"label_window_feature_bars={-(-win_ms // feature_bar_ms)} depth_ms={depth_ms} "
          f"lookahead_depth_rows={-(-depth_ms // feature_bar_ms)} purge_lower_bound={[(p.symbol, p.purge_lower_bound_ms) for p in purge]} "
          f"mismatch={len(bad)}")
    if bad or len(windows) == 0:
        rc = 1
sys.exit(rc)
