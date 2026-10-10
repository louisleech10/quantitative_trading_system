"""PRE-RED Task 2.0（多週期）：跑 _multi_tf_record（BTCUSDT 12h＋1h），攔截 _hash_l7_parquet_table 讀到之逐欄陣列，
輸出逐欄 [dtype, 值 sha, NaN 遮罩 sha]。用法（cwd＝worktree；PYTHONHASHSEED=0）：venv/bin/python <本檔> <out.json>
比對兩版：python full_coldiff.py 不適用（格式不同）；用本檔之 compare 模式：python multi_cols.py compare <a.json> <b.json> [樣式]
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path


def run(out: str) -> None:
    import numpy as np

    root = Path.cwd()
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("freeze_failopen_baseline", root / "scripts/freeze_failopen_baseline.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    for k, v in freeze.FIXED_ENV.items():
        os.environ[k] = v
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    cols = {}
    orig = freeze._hash_l7_parquet_table

    def spy(feature_base, symbol, timeframe, config_hash, index):
        reader = FeatureReader(str(feature_base))
        for _g, df in reader.stream_groups_v2(symbol, timeframe, config_hash, artifact_kind="raw"):
            for c in df.columns:
                v = np.asarray(df[c].to_numpy(copy=False))
                cols[str(c)] = [str(v.dtype), hashlib.sha256(freeze._canonical_array_bytes(v)).hexdigest()[:20],
                                hashlib.sha256(np.packbits(np.isnan(v.astype(np.float64)).astype(np.uint8)).tobytes()).hexdigest()[:20]]
        return orig(feature_base, symbol, timeframe, config_hash, index)

    freeze._hash_l7_parquet_table = spy
    with tempfile.TemporaryDirectory() as tmp:
        rec = freeze._multi_tf_record("BTCUSDT", Path(tmp))
    Path(out).write_text(json.dumps({"feature_count": rec["feature_count"], "cols": cols}), encoding="utf-8")
    print("multi_cols", len(cols), rec["merged_L7"]["canonical_sha256"][:8])


def compare(a_p: str, b_p: str, pattern: str | None) -> None:
    a, b = json.load(open(a_p))["cols"], json.load(open(b_p))["cols"]
    rx = re.compile(pattern) if pattern else None
    only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    common = set(a) & set(b)
    val = sorted(c for c in common if a[c][1] != b[c][1] and a[c][2] == b[c][2])
    mask = sorted(c for c in common if a[c][2] != b[c][2])
    dt = sorted(c for c in common if a[c][0] != b[c][0])
    changed = only_a + only_b + val + mask
    out = {"a": len(a), "b": len(b), "only_a": len(only_a), "only_b": len(only_b), "values_only": len(val),
           "mask_changed": len(mask), "dtype_changed": len(dt)}
    if rx:
        miss = [c for c in changed if not rx.search(c)]
        out["changed_not_matching_pattern"] = len(miss)
        out["miss_sample"] = miss[:20]
    out["only_a_sample"], out["only_b_sample"] = only_a[:20], only_b[:20]
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        assert os.environ.get("PYTHONHASHSEED") == "0"
        run(sys.argv[1])
