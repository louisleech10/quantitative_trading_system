"""FF-STAT 研究（使用者 2026-09-24：「只拿最前500根，這樣會不會有抽樣誤差？」）：校準窗長度對 ADF 判定之影響，真實資料。

唯讀讀既有 run 之 raw parquet（BTC／ETH／BCH × 1h（1h run 之 1h_ 檔）與 12h（原生 12h run 之 12h_ 檔））之 L1＋L2 欄。
每 (標的, 週期) 分層抽欄（每檔前 PER_FILE 欄），逐欄以生產端同一 ADF 核心（`_adf_pvalue_for_values`，fast ADF）判定：
- 校準判定：前 n 個有限值（n ∈ WINDOWS），p>0.05 ⇒ 判「不平穩」（生產語意）。
- 後段參考：校準窗之後之資料（1h：第 2000 列起、至多 LATE_CAP 值；12h：第 1000 列起）以同核心、sample_size=全長檢定。
指標：各 n 與後段之一致率、危險方向（校準判平穩 ⇒ 不處理，但後段不平穩）比例、相鄰不重疊窗之判定 Jaccard。
輸出 JSON 至 argv[1]。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor  # noqa: E402

FC = REPO / "data_cache" / "features"
RUNS = {
    ("BTCUSDT", "1h"): FC / "BTCUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/raw",
    ("ETHUSDT", "1h"): FC / "ETHUSDT/1h/d9935491cea49e8cada481a8bf9487d6/raw",
    ("BCHUSDT", "1h"): FC / "BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/raw",
    ("BTCUSDT", "12h"): FC / "BTCUSDT/12h/e53e22906c35363757f4cd49d27f973e/raw",
    ("ETHUSDT", "12h"): FC / "ETHUSDT/12h/e53e22906c35363757f4cd49d27f973e/raw",
    ("BCHUSDT", "12h"): FC / "BCHUSDT/12h/e53e22906c35363757f4cd49d27f973e/raw",
}
PER_FILE = 3
LATE_CAP = 8000
ALPHA = 0.05
P = FeaturePreprocessor._adf_pvalue_for_values


def nonstat(v: np.ndarray) -> bool:
    return P(v, sample_size=len(v)) > ALPHA


def study(sym: str, tf: str, raw: Path) -> dict:
    windows = (500, 1000, 2000) if tf == "1h" else (500, 1000)
    late_start = 2000 if tf == "1h" else 1000
    files = sorted(p for p in raw.glob(f"{tf}_L[12]_*.parquet"))
    rows = []
    for p in files:
        pf = pq.ParquetFile(p)
        names = [n for n in pf.schema_arrow.names if n not in ("timestamp", "index", "__index_level_0__")][:PER_FILE]
        if not names:
            continue
        tbl = pf.read(columns=names)
        for n in names:
            v = np.asarray(tbl.column(n).to_numpy(zero_copy_only=False), dtype=np.float64)
            fin = v[np.isfinite(v)]
            if fin.size < late_start + 200 or np.nanstd(fin[:500]) == 0:
                continue
            late = fin[late_start:late_start + LATE_CAP]
            if np.std(late) == 0:
                continue
            r = {"col": n, "layer": p.name.split("_")[1], "late_ns": nonstat(late)}
            for w in windows:
                r[f"ns_{w}"] = nonstat(fin[:w])
            # 相鄰不重疊 500 窗：[0,500) vs [500,1000)
            r["ns_w2"] = nonstat(fin[500:1000])
            rows.append(r)
    out = {"symbol": sym, "tf": tf, "columns": len(rows), "late_start": late_start,
           "late_nonstationary_rate": round(float(np.mean([r["late_ns"] for r in rows])), 4) if rows else None}
    for w in windows:
        agree = np.mean([r[f"ns_{w}"] == r["late_ns"] for r in rows])
        danger = np.mean([(not r[f"ns_{w}"]) and r["late_ns"] for r in rows])  # 判平穩（不處理）但後段不平穩
        out[f"n{w}"] = {"nonstationary_rate": round(float(np.mean([r[f"ns_{w}"] for r in rows])), 4),
                        "agree_with_late": round(float(agree), 4), "danger_rate": round(float(danger), 4)}
    a = {r["col"] for r in rows if r["ns_500"]}
    b = {r["col"] for r in rows if r["ns_w2"]}
    out["jaccard_nonstat_w1_w2"] = round(len(a & b) / len(a | b), 4) if (a | b) else None
    return out


def main(dst: str) -> None:
    t = time.time()
    res = [study(s, tf, raw) for (s, tf), raw in RUNS.items()]
    json.dump({"alpha": ALPHA, "per_file": PER_FILE, "late_cap": LATE_CAP, "results": res,
               "seconds": round(time.time() - t, 1)}, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
