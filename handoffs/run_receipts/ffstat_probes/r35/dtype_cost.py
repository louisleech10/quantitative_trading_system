"""實量：預設全設定落盤之 float16／float32 欄數與位元組、全改 float32 之大小、寫檔耗時差。
用法：venv/bin/python dtype_cost.py <tf> <out.json>"""
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest

REPO = Path("/Users/louis/Desktop/quantitative_trading_system")
sys.path.insert(0, str(REPO))
from tests.feature_engineering import ffstat_helpers as h  # noqa: E402
from momentum.factories import create_feature_factory  # noqa: E402
from momentum.FeatureEngineering.feature_storage import FeatureStorage  # noqa: E402

tf, out = sys.argv[1], Path(sys.argv[2])
real_select = FeatureStorage.__dict__["_select_parquet_storage_array"]


def run(tmp: Path, label: str, force32: bool):
    root = tmp / f"features_{label}"
    factory = create_feature_factory(cache_dir=str(REPO / "data_cache/feature_klines"), validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    timing = {"select_s": 0.0}

    def timed(cls, data):
        t0 = time.perf_counter()
        if force32:
            res = (np.ascontiguousarray(data, dtype=np.float32), "float32")
        else:
            res = real_select.__func__(cls, data)
        timing["select_s"] += time.perf_counter() - t0
        return res

    FeatureStorage._select_parquet_storage_array = classmethod(timed)
    t0 = time.perf_counter()
    try:
        factory.generate_features(h.SYMBOL, tf, config_override={"timeframes": {"primary": tf, "training": [tf]}},
                                  force_regenerate=True, start_date=None, end_date=None, persist=True)
    finally:
        FeatureStorage._select_parquet_storage_array = real_select
    total_s = time.perf_counter() - t0
    n16 = n32 = 0
    for p in root.rglob("*.parquet"):
        for f in pq.read_schema(p):
            t = str(f.type)
            if t == "halffloat":
                n16 += 1
            elif t == "float":
                n32 += 1
    size = sum(p.stat().st_size for p in root.rglob("*.parquet"))
    return {"columns_float16": n16, "columns_float32": n32, "parquet_bytes": size,
            "total_seconds": round(total_s, 1), "dtype_select_seconds": round(timing["select_s"], 2)}


mp = pytest.MonkeyPatch()
with tempfile.TemporaryDirectory(prefix=f"dtype_cost_{tf}_") as t:
    tmp = Path(t)
    h.prepare_stat_env(mp, tmp)
    try:
        auto = run(tmp, "auto", False)
        f32 = run(tmp, "f32", True)
    finally:
        mp.undo()
rep = {"timeframe": tf, "auto": auto, "all_float32": f32,
       "size_ratio": round(f32["parquet_bytes"] / auto["parquet_bytes"], 3)}
out.write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(rep, ensure_ascii=False))
