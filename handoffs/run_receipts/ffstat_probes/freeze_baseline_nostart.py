"""FF-STAT §G②（v32）：無起始日全史之凍結基準（逐欄 256 列區塊 sha256）。

必於 FF-STAT 動工前之 commit（02350721 之父）所建之獨立 git worktree 內執行（不動主工作區 tracked 檔）：
  git worktree add /tmp/ffstat-prebase 02350721^
  cd /tmp/ffstat-prebase && <主 repo>/venv/bin/python <主 repo>/handoffs/run_receipts/ffstat_probes/freeze_baseline_nostart.py \
      --kline-dir <主 repo>/data_cache/feature_klines --out <主 repo>/tests/_golden/ffstat/baseline_nostart.json
設定：與 tests/feature_engineering/ffstat_helpers.stat_payload(fracdiff=False, adf=False) 相同之輕量真實設定
（close、L1 trend、L2 Ratio／Cross、L3 5／13、L4 關閉），BTCUSDT 1h、無起始日、無結束日。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

BLOCK_ROWS = 256


def payload() -> dict:
    from tests.feature_engineering.fftfmeta_golden_helpers import HEALTHY, PRIMARY_TF, fast_payload

    body = fast_payload([PRIMARY_TF], **HEALTHY)
    body["operators"] = {"enabled": True, "distance": {"enabled": False}, "cross": {"enabled": True},
                         "momentum": {"enabled": False}, "ratio": {"enabled": True},
                         "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}}
    body["lag_features"] = {"enabled": False}
    body["preprocessing"]["fractional_differencing"] = {"enabled": False, "apply_to": "non_stationary"}
    body["preprocessing"]["adf_differencing"] = {"enabled": False, "apply_to": "non_stationary"}
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kline-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.path.insert(0, os.getcwd())
    import pandas as pd
    import pyarrow.parquet as pq

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    work = Path(tempfile.mkdtemp(prefix="ffstat_prebase_"))
    factory = create_feature_factory(cache_dir=args.kline_dir, validate_continuity=False)
    factory._storage = FeatureStorage(str(work / "features"))
    factory.generate_features("BTCUSDT", "1h", config_override=payload(), force_regenerate=True,
                              start_date=None, end_date=None, persist=True)
    columns = {}
    rows = None
    for p in sorted((work / "features").rglob("*.parquet")):
        if p.name.endswith("_L65.parquet"):
            continue
        frame = pq.read_table(p).to_pandas()
        rows = len(frame)
        for n in frame.columns:
            if n in ("timestamp", "__index_level_0__", "index"):
                continue
            values = frame[n].to_numpy(dtype=np.float64)
            columns[n] = [hashlib.sha256(values[i:i + BLOCK_ROWS].tobytes()).hexdigest()
                          for i in range(0, len(values), BLOCK_ROWS)]
    head = os.popen("git rev-parse HEAD").read().strip()
    doc = {"commit": head, "block_rows": BLOCK_ROWS, "rows": rows, "symbol": "BTCUSDT", "timeframe": "1h",
           "chain_has_class_2_or_3": [], "columns": columns}
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"FROZEN commit={head} rows={rows} columns={len(columns)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
