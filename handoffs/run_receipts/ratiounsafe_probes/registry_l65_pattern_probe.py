"""RATIOUNSAFE 預查：主路徑（CGSA registry）L6.5 是否改動 L1 pattern 欄之值。
單週期一次生成（preprocessing 預設開、落盤至暫存目錄），比 raw 與 processed 兩成品之 pattern 欄；真實 kline，不寫 data_cache。
用法：env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python <本檔> > <out.json>
環境：RATIOUNSAFE_TF（預設 12h）、RATIOUNSAFE_DAYS（預設 1000）。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def main() -> int:
    import h5py
    import numpy as np
    import pandas as pd

    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
    from momentum.factories import create_feature_factory

    os.environ["FFACT_LAYER1_PARALLEL"] = "0"
    tf = os.environ.get("RATIOUNSAFE_TF", "12h")
    days = int(os.environ.get("RATIOUNSAFE_DAYS", "1000"))
    with h5py.File("data_cache/feature_klines/kline_cache.h5", "r") as f:
        end = pd.Timestamp(int(np.asarray(f[f"/BTCUSDT/{tf}/data"]["timestamp"]).max()), unit="s", tz="UTC")
    start = (end - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    payload = {
        "timeframes": {"primary": tf, "training": [tf]},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
        "atomic_indicators": {
            "pattern": {"enabled": True},
            **{c: {"enabled": False} for c in ("trend", "momentum", "volatility", "volume", "cycle", "statistics",
                                               "microstructure", "entropy", "tail_risk")},
        },
    }
    tf_keys = set(TimeframeAligner._timeframe_seconds_keys())

    def _is_l1_pattern(col: str) -> bool:  # L1 pattern 欄＝（去第二段週期後）恰三段且第二段為 pattern
        parts = [p for i, p in enumerate(str(col).split("_")) if not (i == 1 and p in tf_keys)]
        return len(parts) == 3 and parts[1] == "pattern"

    def _gen(preprocessing: bool) -> pd.DataFrame:
        cfg = dict(payload, preprocessing={"enabled": preprocessing})
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["FFACT_CGSA_WORK_DIR"] = str(Path(tmp) / "cgsa")
            factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
            factory._storage = FeatureStorage(str(Path(tmp) / "features"))
            factory.generate_features("BTCUSDT", tf, config_override=cfg, force_regenerate=True,
                                      start_date=start, end_date=end.strftime("%Y-%m-%d"), persist=True)
            manifests = sorted(Path(tmp, "features").rglob("feature_manifest.json"))
            if not manifests:
                raise FileNotFoundError("暫存目錄無 feature_manifest.json")
            config_hash = manifests[0].parent.name
            reader = FeatureReader(str(Path(tmp, "features")))
            parts = [df for _, df in reader.stream_groups_v2("BTCUSDT", tf, config_hash, "raw", allow_partial=True)]
            return pd.concat(parts, axis=1) if parts else pd.DataFrame()

    kinds = ["raw（L6.5 經 raw-sink 寫入）"]
    frames = {"raw": _gen(False), "processed": _gen(True)}
    raw = frames.get("raw", pd.DataFrame())
    proc = frames.get("processed", pd.DataFrame())
    pat_raw = [c for c in raw.columns if _is_l1_pattern(c)]
    pat_proc = [c for c in proc.columns if _is_l1_pattern(c)]
    common = sorted(set(pat_raw) & set(pat_proc))
    n = min(len(raw), len(proc))
    rows = []
    for c in common:
        a = raw[c].to_numpy(dtype=float)[-n:]
        b = proc[c].to_numpy(dtype=float)[-n:]
        rows.append({"col": c, "nonzero_raw": int(np.count_nonzero(np.nan_to_num(a))),
                     "nonzero_processed": int(np.count_nonzero(np.nan_to_num(b))),
                     "identical": bool(np.array_equal(a, b, equal_nan=True)),
                     "distinct_processed": sorted({float(x) for x in b if np.isfinite(x)})[:8]})
    out = {
        "schema_version": 1,
        "command": "env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/ratiounsafe_probes/registry_l65_pattern_probe.py",
        "exit_code": 0, "tf": tf, "days": days, "artifact_kinds": kinds, "compare": "preprocessing.enabled=False 之 raw 對 preprocessing.enabled=True 之 raw",
        "rows_raw": len(raw), "rows_processed": len(proc),
        "n_pattern_raw": len(pat_raw), "n_pattern_processed": len(pat_proc),
        "pattern_only_in_raw": sorted(set(pat_raw) - set(pat_proc)),
        "n_identical": sum(r["identical"] for r in rows),
        "nonzero_total_raw": sum(r["nonzero_raw"] for r in rows),
        "nonzero_total_processed": sum(r["nonzero_processed"] for r in rows),
        "n_cols_signal_erased": sum(1 for r in rows if r["nonzero_raw"] > 0 and r["nonzero_processed"] == 0),
        "columns_raw_head": list(raw.columns)[:12], "columns_processed_head": list(proc.columns)[:12],
        "per_column": rows,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
