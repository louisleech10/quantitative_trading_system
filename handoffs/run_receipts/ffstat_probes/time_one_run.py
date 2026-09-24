"""FF-STAT 前置探針：開平穩化之輕量真實 run 單次計時與 L6.5 輸出欄觀測（唯讀量測；docs/FFSTAT_SPEC.md §G）。

用法：venv/bin/python handoffs/run_receipts/ffstat_probes/time_one_run.py <single|multi> [append|replace]
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from _isolate import isolate  # noqa: E402  須先於任何 momentum／helper 匯入

ISOLATED_ROOT = isolate()

import pyarrow.parquet as pq  # noqa: E402

from momentum.factories import create_feature_factory  # noqa: E402
from momentum.FeatureEngineering.feature_storage import FeatureStorage  # noqa: E402
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402
from _isolate import isolate_dstar_cache  # noqa: E402

DSTAR_DIR = isolate_dstar_cache(ISOLATED_ROOT)


def main() -> int:
    tfs = ["1h", "12h"] if sys.argv[1] == "multi" else ["1h"]
    mode = sys.argv[2] if len(sys.argv) > 2 else "append"
    payload = h.stat_payload(tfs)
    payload["preprocessing"]["mode"] = mode
    root = Path(tempfile.mkdtemp(prefix="ffstat_time_"))
    try:
        factory = create_feature_factory(cache_dir=h.KLINE_DIR, validate_continuity=False)
        factory._storage = FeatureStorage(str(root / "features"))
        t0 = time.time()
        result = factory.generate_features(h.SYMBOL, "1h", config_override=payload, force_regenerate=True,
                                           start_date=h.WINDOW[0], end_date=h.WINDOW[1], persist=True)
        print(f"RESULT seconds={time.time() - t0:.1f} mode={mode} status={result.metadata.get('quality_status')}")
        print("RESULT layer_counts", result.layer_counts, "feature_count", result.feature_count)
        l65 = sorted((root / "features").rglob("*_L65.parquet"))
        cols = [c for p in l65 for c in pq.ParquetFile(p).schema_arrow.names]
        print("RESULT l65_files", len(l65), "l65_cols", len(cols))
        print("RESULT suffixes", sorted({c.rsplit("_", 1)[-1] for c in cols if "_" in c})[:20])
        print("RESULT sample", [c for c in cols if "fracdiff" in c or "_diff" in c][:5])
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
