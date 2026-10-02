"""FF-STAT 收案前之本機縮小版全鏈截斷 MR——可行性實測（主委 2026-10-02；諮詢 r4 收斂之較嚴版）。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/small_mr_probe.py <候選名> <輸出.json>
候選名見 CANDIDATES；每次只跑一個候選之 full＋trunc 成對生成並執行原 `_assert_truncation_invariants`，
記錄窗長、欄數（依層）、耗時、成敗。峰值記憶體由外層 `/usr/bin/time -l` 量。須單獨占用機器執行。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _isolate import isolate, isolate_dstar_cache  # noqa: E402

ROOT = isolate("ffstat_small_mr_")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402

from momentum.factories import create_kline_storage_manager  # noqa: E402
from tests.feature_engineering import ff_truncation_mr_helpers as h  # noqa: E402

isolate_dstar_cache(ROOT)


def _small_values_payload(categories, sources, windows, training_tfs=None):
    payload = (h._values_gate_mr_config_payload(training_tfs=training_tfs) if training_tfs
               else h._values_gate_mr_config_payload())
    payload["atomic_indicators"] = {c: {"enabled": c in categories} for c in h._ALL_ATOMIC_CATEGORIES}
    payload["data_sources"] = {"enabled_sources": list(sources), "synthetic_sources": []}
    payload["rolling_aggregation"] = {"enabled": True, "windows": list(windows)}
    payload["operators"] = {"enabled": True, "worldquant": {"enabled": False}}
    payload["lag_features"] = {"enabled": True}
    return payload


CANDIDATES = {
    "trend_momentum_cv": lambda: _small_values_payload(("trend", "momentum"), ("close", "volume"), (5, 13)),
    "trend_momentum_vol_cv": lambda: _small_values_payload(("trend", "momentum", "volatility"), ("close", "volume"), (5, 13, 21)),
    "mtf_trend_momentum_cv": lambda: _small_values_payload(("trend", "momentum"), ("close", "volume"), (5, 13),
                                                           ["1h", "4h", "12h"]),
    "mtf_1h4h_trend_momentum_cv": lambda: _small_values_payload(("trend", "momentum"), ("close", "volume"), (5, 13),
                                                                ["1h", "4h"]),
}


def main(name: str, out: Path) -> None:
    payload = CANDIDATES[name]()
    storage = create_kline_storage_manager(cache_dir=h.KLINE_CACHE_DIR)
    kline = storage.read_klines(h.SYMBOL, h.TIMEFRAME, validate_continuity=False)
    tfs = payload["timeframes"]["training"]
    multi = len(tfs) > 1
    margin = h.ALIGN_MARGIN if multi else 0
    window_bars = h._required_window_bars(payload, training_tfs=tfs, align_margin=margin)
    t0 = time.perf_counter()
    status, err = "pass", None
    try:
        pair = h._build_truncation_pair(
            ROOT / "features", kline, config_payload=payload, window_bars=window_bars, training_tfs=tfs,
            align_margin=margin,
            window_date_fn=h._bar_window_dates_at_12h_boundary if multi else h._bar_window_dates)
        t_gen = time.perf_counter() - t0
        h._assert_truncation_invariants(pair)
    except AssertionError as exc:  # 基線不綠亦要記錄
        status, err, t_gen = "assert_fail", str(exc)[:2000], time.perf_counter() - t0
        pair = None
    t_all = time.perf_counter() - t0
    layers = {}
    if pair is not None:
        for fname, frame in h._iter_raw_parquet_frames(pair.full.raw_dir):
            layer = h._layer_from_stem(h._parquet_stem(fname))
            layers[layer] = layers.get(layer, 0) + int(frame.shape[1])
    rec = {"schema_version": 1, "command": f"small_mr_probe.py {name}", "exit_code": 0 if status == "pass" else 1,
           "candidate": name, "payload": payload, "window_bars": int(window_bars), "status": status, "error": err,
           "seconds_generation_pair": round(t_gen, 1), "seconds_total": round(t_all, 1),
           "full_columns_by_layer": layers, "full_rows": int(pair.full.row_count) if pair else None,
           "warmup": int(pair.warmup) if pair else None, "n_trunc": int(pair.n_trunc) if pair else None}
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("candidate", "status", "window_bars", "seconds_total", "full_columns_by_layer")}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
