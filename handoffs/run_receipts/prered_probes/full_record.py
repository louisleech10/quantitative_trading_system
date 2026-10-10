"""PRE-RED 探針：於 cwd 之 repo 版本跑凍結腳本之 _single_tf_record（BTCUSDT/12h），輸出各層五分量＋逐欄雜湊。

用法（須 PYTHONHASHSEED=0）：venv/bin/python <本檔> <輸出 json> [symbol] [timeframe]
與 tests/feature_engineering/test_failopen_layers.py::_assert_layer_golden_matches_baseline 同流程（凍結腳本本體）；
逐欄雜湊另以 registry 讀回計算，供跨 commit 定位改變之欄。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))


def main(out: str, symbol: str = "BTCUSDT", timeframe: str = "12h") -> int:
    assert os.environ.get("PYTHONHASHSEED") == "0"
    import numpy as np

    spec = importlib.util.spec_from_file_location("freeze_failopen_baseline", ROOT / "scripts/freeze_failopen_baseline.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    for k, v in freeze.FIXED_ENV.items():
        os.environ[k] = v

    captured = {}
    orig_hash = freeze._hash_registry_table

    def _spy(registry, groups, index):
        rec = orig_hash(registry, groups, index)
        per_col = []
        for g in freeze._ordered_groups(registry, groups):
            data = np.asarray(registry.load_data_native(g.group_id))
            for i, name in enumerate(g.columns):
                v = data[:, i]
                per_col.append([str(name),
                                hashlib.sha256(freeze._canonical_array_bytes(v)).hexdigest()[:16],
                                hashlib.sha256(np.packbits(np.isnan(v).astype(np.uint8), bitorder="little").tobytes()).hexdigest()[:16]])
        captured.setdefault("tables", []).append(per_col)
        return rec

    freeze._hash_registry_table = _spy
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        record = freeze._single_tf_record(symbol, timeframe, Path(tmp))
    elapsed = time.perf_counter() - t0
    tables = captured.get("tables", [])
    names = ["L1", "L2", "L3", "L4", "L5", "L6", "final_L7"]
    keys = ("canonical_sha256", "column_order_sha256", "dtypes_sha256", "index_sha256", "values_sha256",
            "nan_mask_sha256", "rows", "columns", "groups", "nan_count")
    summary = {
        "elapsed_seconds": round(elapsed, 1),
        "config_hash": record.get("config_hash"),
        "feature_count": record.get("feature_count"),
        "group_set_sha256": record.get("group_set_sha256"),
        "layers": {n: {k: (record["layers"][n] if n != "final_L7" else record["final_L7"]).get(k) for k in keys}
                   for n in names},
        "per_column": {n: tables[i] for i, n in enumerate(names) if i < len(tables)},
    }
    Path(out).write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    print("elapsed", summary["elapsed_seconds"], "L1-L6+final", " ".join(summary["layers"][n]["canonical_sha256"][:8] for n in names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
