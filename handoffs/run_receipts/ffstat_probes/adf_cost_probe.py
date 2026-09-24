"""FF-STAT 使用者問題（2026-09-24）：「約 2 萬根 K、L1＋L2 全部做 ADF 檢定要多花多少時間？多幣種多週期會不會時間爆炸或 OOM？」

唯讀讀 reference run（ETHUSDT 1h，d9935491…）之 raw/*_L1*、*_L2* parquet；用生產端同一判定路徑之核心
（`_calibration_series` 前 500 列 → `FeaturePreprocessor._adf_pvalue_for_values`，fast ADF 預設開）計時。
① 以 parquet metadata 數全部 L1／L2 欄數與列數（不載入資料）；② 每檔抽前 K 欄實跑 ADF 計時；③ 記峰值 RSS。
輸出 JSON 至 argv[1]。
"""
from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor  # noqa: E402

RUN = REPO / "data_cache/features/ETHUSDT/1h/d9935491cea49e8cada481a8bf9487d6/raw"
CALIB = 500
PER_FILE = 20


def main(out: str) -> None:
    files = sorted(p for p in RUN.glob("*.parquet") if "_L1_" in p.name or "_L2_" in p.name)
    counts: dict = {}
    for p in files:
        md = pq.ParquetFile(p).metadata
        tf, layer = p.name.split("_")[0], p.name.split("_")[1]
        c = counts.setdefault(f"{tf}_{layer}", {"files": 0, "columns": 0, "rows": 0})
        c["files"] += 1
        c["columns"] += md.num_columns
        c["rows"] = max(c["rows"], md.num_rows)
    fn = FeaturePreprocessor._adf_pvalue_for_values
    fn(np.random.default_rng(0).standard_normal(CALIB), sample_size=CALIB)  # JIT 暖機，不計時
    timed, secs, skipped = 0, 0.0, 0
    for p in files:
        pf = pq.ParquetFile(p)
        names = [n for n in pf.schema_arrow.names if n not in ("timestamp", "index", "__index_level_0__")][:PER_FILE]
        if not names:
            continue
        tbl = pf.read_row_groups([0], columns=names) if pf.num_row_groups else pf.read(columns=names)
        for n in names:
            v = np.asarray(tbl.column(n).to_numpy(zero_copy_only=False), dtype=np.float64)[:CALIB]
            v = v[np.isfinite(v)]
            if v.size < 20:
                skipped += 1
                continue
            t = time.perf_counter()
            fn(v, sample_size=CALIB)
            secs += time.perf_counter() - t
            timed += 1
    per_col = secs / max(timed, 1)
    total_cols = sum(c["columns"] for c in counts.values())
    json.dump({
        "run": str(RUN.relative_to(REPO)), "calibration_values_per_column": CALIB,
        "counts": counts, "total_l1_l2_columns": total_cols,
        "timed_columns": timed, "skipped_lt20_finite": skipped, "timed_seconds": round(secs, 4),
        "seconds_per_column": per_col, "extrapolated_seconds_all_l1_l2": round(per_col * total_cols, 2),
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 1),
    }, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
