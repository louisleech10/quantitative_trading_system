"""FF-STAT b5（SPEC v57）：倍數表量測之 ±inf 判定修正是否影響現行表——真實資料逐 catalog case 全史計算，掃 ±inf。

評測（gpt-5.6-luna max）指出：評估窗內 ±inf 曾可被 NaN 遮除或 std 捷徑吞下而判收斂。修正後 ±inf 一律未收斂。
若全部 (標的, 週期, case) 之全史輸出皆無 ±inf ⇒ 修正對現行表之量測不可能有影響（修正只在出現 ±inf 時改變判定）。
純窗口型（`WINDOW_ONLY_ANALYTIC`）K＝窗口長度、不依量測誤差，不掃。
全史輸出為評估窗 ground truth 之代理（評估窗之 ground truth 為其前史全部或 `gt_history` 之計算；有 ±inf 之 case
另列，交主委以量測原窗重驗）。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/warmup_inf_scan.py <輸出 json> [workers]
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO))

SYMBOLS = ("BTCUSDT", "ETHUSDT", "ADAUSDT")
TIMEFRAMES = ("5m", "1h", "4h", "12h", "1d")


def _scan(tf: str, sym: str) -> dict:
    from _isolate import isolate

    isolate("ffstat_inf_scan_")
    import numpy as np

    from scripts import verify_l1_warmup_requirements as v

    frame = v.load_frame(sym, tf)
    hits, cases, errors = [], 0, []
    t0 = time.time()
    for entry in v.build_catalog():
        if entry.name in v.WINDOW_ONLY_ANALYTIC:
            continue
        for case in entry.cases:
            cases += 1
            try:
                outs = case.fn(frame)
            except Exception as exc:  # noqa: BLE001 — 記錄不中斷
                errors.append(f"{entry.name} {case.params} {case.source}: {type(exc).__name__}")
                continue
            n_inf = int(sum(np.isinf(np.asarray(a, dtype=np.float64)).sum() for a in outs))
            if n_inf:
                hits.append({"indicator": entry.name, "params": case.params, "source": case.source, "inf": n_inf})
    return {"timeframe": tf, "symbol": sym, "rows": len(frame), "cases": cases, "inf_hits": hits,
            "errors": errors, "seconds": round(time.time() - t0, 1)}


def main() -> int:
    out = Path(sys.argv[1])
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_scan, tf, sym): (tf, sym) for tf in TIMEFRAMES for sym in SYMBOLS}
        for fut in as_completed(futs):
            res = fut.result()
            results.append(res)
            print(f"[progress] {len(results)}/{len(futs)} {res['timeframe']} {res['symbol']} cases={res['cases']} "
                  f"inf_hits={len(res['inf_hits'])} errors={len(res['errors'])} {res['seconds']}s", flush=True)
    results.sort(key=lambda r: (TIMEFRAMES.index(r["timeframe"]), r["symbol"]))
    total_hits = sum(len(r["inf_hits"]) for r in results)
    out.write_text(json.dumps({"spec": "docs/FFSTAT_SPEC.md v57（倍數表 ±inf 判定）", "total_inf_hits": total_hits,
                               "results": results}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"[FINAL] total_inf_hits={total_hits} → {out}")
    return 0 if all(not r["errors"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
