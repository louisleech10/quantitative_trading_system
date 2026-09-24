"""FF-STAT Task 4.1 成本收據（docs/FFSTAT_SPEC.md Task 4.1；使用者 2026-09-24「先實測再定」窗長）。

3 標的 × 2 週期 × N＝500／1000／2000 之真實冷 run（各自子程序、隔離 tmp 與 d* 快取），記耗時、峰值記憶體
（子程序 RUSAGE_SELF＋RUSAGE_CHILDREN）、各 N 與 N=2000 之決策一致率；另於 FFACT_MEMORY_TIER=8gb 跑一次多週期平行
（含封包交接之父＋子峰值）。輸出 `handoffs/run_receipts/<日期>-ffstat-cost.json`，交使用者裁決 N 之最終預設。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/cost_probe.py
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONTRACT = json.loads((REPO / "tests" / "_golden" / "ffstat" / "contract.json").read_text(encoding="utf-8"))


def child(symbol: str, timeframe: str, n: int, multi: bool) -> None:
    import resource
    import time

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(REPO))
    from _isolate import isolate  # noqa: E402

    root = isolate("ffstat_cost_")
    from _isolate import isolate_dstar_cache  # noqa: E402
    from momentum.factories import create_feature_factory  # noqa: E402
    from momentum.FeatureEngineering.feature_storage import FeatureStorage  # noqa: E402
    from tests.feature_engineering import ffstat_helpers as h  # noqa: E402

    isolate_dstar_cache(root)
    tfs = ["1h", "12h"] if multi else [timeframe]
    payload = h.stat_payload(tfs)
    payload["timeframes"]["primary"] = timeframe
    payload["preprocessing"]["calibration_bars"] = n
    factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root / "features"))
    t0 = time.time()
    result = factory.generate_features(symbol, timeframe, config_override=payload, force_regenerate=True,
                                       start_date="2025-10-01", end_date="2025-12-31", persist=True)
    elapsed = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss + resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    dec = h.decisions(result)
    print("RESULT " + json.dumps({"seconds": round(elapsed, 1), "peak_rss_bytes": int(rss),
                                  "decisions": {c: [bool(d["fracdiff"]), int(d["adf_differenced"] or 0)]
                                                for c, d in dec.items()}}))


def run_child(args: list, env: dict) -> dict:
    r = subprocess.run([sys.executable, __file__, "--child", *args], capture_output=True, text=True,
                       env={**os.environ, **env}, cwd=str(REPO))
    line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), None)
    if r.returncode != 0 or line is None:
        return {"rc": r.returncode, "error": r.stderr[-800:]}
    return {"rc": 0, **json.loads(line[len("RESULT "):])}


def main() -> int:
    rows = []
    for symbol in CONTRACT["cost_measure_symbols"]:
        for tf in CONTRACT["cost_measure_timeframes"]:
            by_n = {n: run_child([symbol, tf, str(n), "single"], {}) for n in CONTRACT["cost_measure_n"]}
            ref = by_n[max(by_n)].get("decisions", {})
            for n, res in by_n.items():
                dec = res.pop("decisions", {})
                common = [c for c in dec if c in ref]
                agree = sum(dec[c] == ref[c] for c in common) / len(common) if common else None
                rows.append({"symbol": symbol, "timeframe": tf, "n": n, **res,
                             "agreement_vs_max_n": None if agree is None else round(agree, 4)})
    tier = run_child([CONTRACT["cost_measure_symbols"][0], "1h", str(CONTRACT["calibration_n_default"]), "multi"],
                     {"FFACT_MEMORY_TIER": f"{CONTRACT['min_memory_tier_gb']}gb", "FFACT_MULTI_TF_PARALLEL": "1"})
    tier.pop("decisions", None)
    out = REPO / "handoffs" / "run_receipts" / f"{_dt.date.today():%Y%m%d}-ffstat-cost.json"
    out.write_text(json.dumps({"spec": "docs/FFSTAT_SPEC.md Task 4.1", "rows": rows, "min_tier_multi_tf": tier},
                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(out)
    return 0 if all(r.get("rc") == 0 for r in rows) and tier.get("rc") == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5] == "multi")
    else:
        raise SystemExit(main())
